#!/usr/bin/env python3
"""Credential scanner — block public commits that contain secrets.

Foundation for SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20. Runs:
  1. as `.git/hooks/pre-commit` against staged files
  2. inside `tools/git_push_split.sh` before pushing to GitHub public
  3. in CI on the public GitHub repo (defense-in-depth)

Exit codes:
  0 — all clean
  1 — at least one credential pattern matched in a file destined for public
  2 — usage error / file not readable

Usage:
  python3 tools/scan_credentials.py <path> [<path>...]
  python3 tools/scan_credentials.py --staged           # scan git-staged files
  python3 tools/scan_credentials.py --all-public       # scan every PUBLIC-classified file in repo
  python3 tools/scan_credentials.py --self-test        # run built-in positive+negative cases

A path classified PRIVATE (e.g., `pages/legal/`, `pages/tenants/`) is skipped:
the scanner only blocks when a public-destined file contains secrets. This
keeps `pages/legal/smartbridge-vshp-client-credentials-*.md` legal —
that file is supposed to contain credentials, just not on GitHub.

Public/private classification mirrors SPEC-NOUS-PUBLIC-PRIVATE-SPLIT-2026-05-20.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ----------------------------------------------------------------------
# Public/private classification (mirrors the spec)
# ----------------------------------------------------------------------

PUBLIC_GLOBS = (
    "agents/**",
    "laws/**",
    "pages/skills/**",
    "pages/laws/**",
    "pages/concepts/**",
    "pages/lessons/**",
    "pages/specs/**",
    "pages/systems/**",
    "pages/dashboards/**",
    "pages/aliases/**",
    "pages/schemas/**",
    "pages/tools/**",
    "pages/prompts/**",
    "pages/roadmap/**",
    "templates/**",
    "tools/**",
    "CLAUDE.md",
    "README.md",
    "index.md",
)

PRIVATE_GLOBS = (
    "pages/legal/**",
    "pages/personal/**",
    "pages/team/**",
    "pages/tenants/**",
    "pages/projects/**",
    "pages/inbox/**",
    "pages/proof-pack/**",
    "pages/exports/**",
    "pages/goals/**",
    "pages/mercury/**",
    "pages/sources/**",
    "pages/task-results/**",
    "pages/progress/**",
    "pages/audits/**",
    "pages/decisions/**",
    "pages/plans/**",
    "pages/communications/**",
    "raw/**",
    "briefs/**",
    "tenants/**",
    "projects/**",
    "test-results/**",
    "logs/**",
    ".env*",
    "*.key",
    "*.pem",
    "secrets/**",
)


def _glob_match(rel_path: str, patterns: tuple[str, ...]) -> bool:
    """fnmatch with ** semantics: ** matches any sequence of path segments."""
    for pat in patterns:
        # Convert ** to a regex that matches anything (including slashes)
        regex = fnmatch.translate(pat).replace(r"(?s:", r"(?s:", 1)
        # fnmatch.translate handles * as [^/]*; ** is treated the same.
        # To get ** semantics, we manually translate the pattern first.
        pat_regex = (
            re.escape(pat)
            .replace(r"\*\*", ".*")
            .replace(r"\*", "[^/]*")
            .replace(r"\?", ".")
        )
        if re.fullmatch(pat_regex, rel_path):
            return True
    return False


def classify(rel_path: str, frontmatter_visibility: str | None = None) -> str:
    """Return 'public' or 'private' for a vault-relative path.

    Order:
      1. Explicit frontmatter `visibility:` overrides all path defaults.
      2. PRIVATE globs match → private (fail-safe wins ties).
      3. PUBLIC globs match → public.
      4. Default → private (unclassified paths fail-safe to private).
    """
    if frontmatter_visibility in ("public", "private"):
        return frontmatter_visibility
    if _glob_match(rel_path, PRIVATE_GLOBS):
        return "private"
    if _glob_match(rel_path, PUBLIC_GLOBS):
        return "public"
    return "private"


# ----------------------------------------------------------------------
# Credential patterns
# ----------------------------------------------------------------------

CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("telegram-bot-token", re.compile(r"\b\d{8,11}:[A-Za-z0-9_-]{30,}\b")),
    ("openai-or-openrouter-key", re.compile(r"\bsk-[A-Za-z0-9_-]{30,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{30,}\b")),
    ("xai-key", re.compile(r"\bxai-[A-Za-z0-9_-]{30,}\b")),
    ("google-api-key", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("gcp-service-account", re.compile(r'"private_key"\s*:\s*"-----BEGIN')),
    ("ssh-private-key", re.compile(r"-----BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b")),
    ("github-pat", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("slack-bot-token", re.compile(r"\bxox[bp]-[A-Za-z0-9-]{30,}\b")),
    # Generic high-entropy assignment: `password: ABC123...` or `token=...`
    # 28+ chars of base64-ish content right after a credential-shaped key.
    (
        "generic-secret-assignment",
        re.compile(
            r"\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|bearer)\b"
            r"\s*[:=]\s*[\"']?([A-Za-z0-9+/=_-]{28,})[\"']?",
            re.IGNORECASE,
        ),
    ),
    # ERAP-specific credential markers from pages/legal/*credentials*.md
    ("erap-client-id", re.compile(r"\bclient_id\s*[:=]\s*[\"']?[A-Za-z0-9-]{16,}[\"']?")),
    ("erap-client-secret", re.compile(r"\bclient_secret\s*[:=]\s*[\"']?[A-Za-z0-9-]{20,}[\"']?")),
]

# Patterns that are credential-shaped but allowed in documentation
# (e.g., "AKIAEXAMPLE12345678" used as a doc placeholder, common test fixtures
# that are obviously fake, redaction-test inputs that the redactor uses to
# demonstrate it's working).
ALLOWLIST_SUBSTRINGS = (
    "EXAMPLE",
    "ExampleTestSecret",
    "ExampleProdSecret",
    "AKIAXXXXXXXXXXXXXXXX",
    "<your-",
    "<YOUR_",
    "REDACTED",
    "your_api_key_here",
    "PLACEHOLDER",
    "x" * 16,  # placeholder runs of x
    # Common test-fixture markers (used by redactor tests + scanner self-tests)
    "abcdefghij",
    "ABCDEFGHIJ",
    "should_not_show",
    "should_be_hidden",
    "should be hidden",
    "lsv2_should",
    "scanner:fixture",
    "scanner_fixture",
)


# Line-level override: if a line contains any of these markers, skip ALL
# credential pattern matching on that line. Use sparingly — meant for test
# fixtures and documentation that intentionally embed credential-shaped
# strings (regex examples in spec pages, redaction-test fixtures, etc.).
_LINE_ALLOW_MARKERS = (
    "# scanner:allow",        # python / shell / yaml
    "<!-- scanner:allow -->", # markdown / html
    "// scanner:allow",       # js / c-family
    "scanner:fixture",        # generic fixture marker
)


def _is_allowlisted(matched_text: str) -> bool:
    upper = matched_text.upper()
    return any(allow.upper() in upper for allow in ALLOWLIST_SUBSTRINGS)


# ----------------------------------------------------------------------
# Frontmatter parsing (minimal — just `visibility`)
# ----------------------------------------------------------------------

_VISIBILITY_RE = re.compile(r"^visibility\s*:\s*(public|private)\s*$", re.MULTILINE)


def parse_visibility(text: str) -> str | None:
    """Read the `visibility:` field from YAML frontmatter, if present."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    front = text[4:end]
    m = _VISIBILITY_RE.search(front)
    return m.group(1) if m else None


# ----------------------------------------------------------------------
# Scanner core
# ----------------------------------------------------------------------


def scan_file(repo_root: Path, abs_path: Path) -> list[dict]:
    """Return a list of finding dicts; empty list means clean.

    Each finding: {file, line, pattern, snippet, classification}
    """
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        rel = abs_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        rel = abs_path.as_posix()

    visibility = parse_visibility(text)
    classification = classify(rel, visibility)

    if classification == "private":
        # Private files are allowed to contain credentials — that's their job.
        return []

    findings: list[dict] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in _LINE_ALLOW_MARKERS):
            continue
        for name, pattern in CREDENTIAL_PATTERNS:
            for m in pattern.finditer(line):
                matched = m.group(0)
                if _is_allowlisted(matched):
                    continue
                # Mask the middle of the matched string in the snippet
                masked = (
                    matched[:6] + "..." + matched[-4:]
                    if len(matched) > 14
                    else matched[:4] + "..."
                )
                findings.append(
                    {
                        "file": rel,
                        "line": line_no,
                        "pattern": name,
                        "snippet": masked,
                        "classification": classification,
                    }
                )
    return findings


def _list_staged_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [
        repo_root / line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def _list_all_public_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for p in repo_root.rglob("*.md"):
        rel = p.relative_to(repo_root).as_posix()
        # Quick path classification (skip frontmatter parse for the full-vault sweep)
        if classify(rel) == "public":
            files.append(p)
    for p in (repo_root / "tools").rglob("*.py"):
        files.append(p)
    for p in (repo_root / "tools").rglob("*.sh"):
        files.append(p)
    return files


# ----------------------------------------------------------------------
# Self-test (positive + negative dogfood)
# ----------------------------------------------------------------------


def self_test() -> int:
    """Run built-in cases. Exit 0 if all pass, 1 if any fail."""
    failures: list[str] = []

    # Construct test-fixture credential strings at runtime so they don't
    # appear literally in source (otherwise the scanner would flag itself).
    # Avoid long single-character runs (XXX...) — those hit the "x"*16
    # placeholder-runs allowlist and the fixture would silently pass.
    _alpha = "QwErTyZxCvBnMaSdFgHjKlPoIuYt0987"
    fake_tg = "{:08d}:{}".format(12345678, _alpha + "1A2B3C4D")
    fake_sk_ant = "sk-" + "ant-" + "fix" + _alpha + "9Z8Y7W6V"
    fake_sk = "sk-" + "fix" + _alpha + "5K4J3H2G"

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "pages" / "skills" / "demo").mkdir(parents=True)
        (repo / "pages" / "legal").mkdir(parents=True)

        # POSITIVE 1: public file with a Telegram token must trip
        f = repo / "pages" / "skills" / "demo" / "SKILL.md"
        f.write_text(f"---\ntype: skill\n---\n# demo\nbot_token={fake_tg}\n")
        if not scan_file(repo, f):
            failures.append("POS1: scanner missed a Telegram bot token in a public file")

        # POSITIVE 2: public file with anthropic key
        f2 = repo / "pages" / "skills" / "demo" / "key.md"
        f2.write_text(f"# anthropic\n{fake_sk_ant}\n")
        if not scan_file(repo, f2):
            failures.append("POS2: scanner missed sk-ant- key in a public file")

        # NEGATIVE 1: private file with same content must not trip
        f3 = repo / "pages" / "legal" / "secrets.md"
        f3.write_text(f"# legal creds\nbot_token={fake_tg}\n")
        if scan_file(repo, f3):
            failures.append("NEG1: scanner flagged a private file (false positive)")

        # NEGATIVE 2: public file with EXAMPLE placeholder must not trip
        f4 = repo / "pages" / "skills" / "demo" / "example.md"
        f4.write_text("# usage\nbot_token=12345678:AAaabbExampleTestSecretddEEffGGhhiijjkkll\n")
        if scan_file(repo, f4):
            failures.append("NEG2: scanner flagged an EXAMPLE placeholder (false positive)")

        # POSITIVE 3: visibility:public override on a normally-private path
        f5 = repo / "pages" / "legal" / "promoted.md"
        f5.write_text(f"---\nvisibility: public\n---\n# promoted to public\nbot_token={fake_tg}\n")
        if not scan_file(repo, f5):
            failures.append("POS3: scanner missed creds in a file with visibility:public override")

        # NEGATIVE 3: visibility:private override on a normally-public path
        f6 = repo / "pages" / "skills" / "demo" / "private-skill.md"
        f6.write_text(f"---\nvisibility: private\n---\n# tenant skill\napi_key: {fake_sk}\n")
        if scan_file(repo, f6):
            failures.append("NEG3: scanner flagged a file with visibility:private override")

        # NEGATIVE 4: line-level allow marker skips scanning that line
        f7 = repo / "pages" / "skills" / "demo" / "allowed.md"
        f7.write_text(f"# doc\nbot_token={fake_tg}  # scanner:allow\n")
        if scan_file(repo, f7):
            failures.append("NEG4: scanner ignored the # scanner:allow line marker")

    if failures:
        print("self-test FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("self-test OK (7 cases: 3 positive + 4 negative)")
    return 0


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Credential scanner for the Nous AGaaS public substrate.")
    parser.add_argument("paths", nargs="*", help="Files to scan (vault-relative or absolute).")
    parser.add_argument("--staged", action="store_true", help="Scan currently-staged files.")
    parser.add_argument("--all-public", action="store_true", help="Scan every public-classified file in the repo.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in positive + negative cases.")
    parser.add_argument("--repo-root", default=None, help="Repo root (default: cwd).")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    repo_root = Path(args.repo_root or ".").resolve()

    if args.staged:
        targets = _list_staged_files(repo_root)
    elif args.all_public:
        targets = _list_all_public_files(repo_root)
    else:
        if not args.paths:
            parser.print_help()
            return 2
        targets = [Path(p).resolve() if Path(p).is_absolute() else (repo_root / p) for p in args.paths]

    all_findings: list[dict] = []
    for target in targets:
        if not target.exists() or not target.is_file():
            continue
        all_findings.extend(scan_file(repo_root, target))

    if not all_findings:
        return 0

    print(f"🔴 credential scanner: {len(all_findings)} finding(s) in PUBLIC-classified files:\n")
    for f in all_findings:
        print(f"  {f['file']}:{f['line']}  [{f['pattern']}]  {f['snippet']}")
    print()
    print("Fix options:")
    print("  1. Redact the credential and replace with a placeholder (EXAMPLE_*, REDACTED, <your-key>).")
    print("  2. Move the file to a PRIVATE-classified path (pages/legal/, pages/tenants/, etc.).")
    print("  3. Add `visibility: private` to the file's frontmatter to override path classification.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
