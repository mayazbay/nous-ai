#!/usr/bin/env python3
"""
llm_judge_routing.py — Tan/Karpathy/Musk skillify Step 5 + 7 (LLM-as-judge for resolver routing)

The naive Jaccard token-overlap matcher in trigger_eval.py is a proxy. The runtime
context_injector_v2.py uses keyword-match-then-top-2 + LLM reasoning. This script
is the actual judge: for each test case in trigger_eval.TEST_CASES, asks an LLM
"given this RESOLVER and this input, which skill should fire?" and compares to
expected.

Closes audit AP-23 (queued session 67): audit-tool METHOD must equal runtime
METHOD. AP-22 (audit-tool source-must-equal-runtime source) is the path-level
sister; this is the algorithm-level sister.

Uses LiteLLM proxy at http://localhost:4000 with default model glm-5.1
(unlimited via ZAI plan; cost ~0). Falls back to direct Anthropic API if
LITELLM_BASE_URL is unset.

Usage:
    python3 llm_judge_routing.py
    python3 llm_judge_routing.py --resolver /path/to/RESOLVER.md
    python3 llm_judge_routing.py --model glm-5.1 --max-cases 10
    python3 llm_judge_routing.py --json

Exit 0 if all pass, 1 if any fail.

Session 67, 2026-04-23.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# Re-use TEST_CASES from trigger_eval to keep one source-of-truth for test data.
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from trigger_eval import TEST_CASES
except ImportError:
    print("ERROR: cannot import TEST_CASES from trigger_eval.py", file=sys.stderr)
    sys.exit(2)


def load_default_env() -> None:
    """Load local runtime env files when the tool is run directly by an agent."""
    for env_path in [
        Path.home() / "nous-agaas/.env",
        Path.home() / "nous-agaas/litellm/.env",
    ]:
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def load_resolver(resolver_path: str) -> str:
    """Load RESOLVER.md content as string."""
    return Path(resolver_path).read_text(encoding="utf-8")


def get_skill_slugs(resolver_text: str) -> set[str]:
    """Extract all skill slugs referenced in RESOLVER for downstream validation."""
    slugs = set()
    pattern = re.compile(r"`(skills/[^`]+)/SKILL\.md`")
    for m in pattern.finditer(resolver_text):
        path = m.group(1)
        slug = path.replace("skills/", "")
        slugs.add(slug)
    return slugs


def call_litellm(
    prompt: str,
    model: str,
    base_url: str,
    api_key: str,
    timeout: int = 30,
    max_tokens: int | None = None,
) -> str:
    """Call LiteLLM /chat/completions with a single user-prompt; return reply text."""
    token_budget = max_tokens or int(os.environ.get("JUDGE_MAX_TOKENS", "1024"))
    last_finish = "?"

    for attempt in range(2):
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": token_budget,
            "temperature": 0.0,
        }
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
        msg = body.get("choices", [{}])[0].get("message", {})
        content = msg.get("content")
        if content and content.strip():
            return content.strip()

        last_finish = body.get("choices", [{}])[0].get("finish_reason", "?")
        if last_finish == "length" and attempt == 0:
            token_budget *= 2
            continue
        break

    return f"__EMPTY_REPLY__(finish_reason={last_finish})"


def build_prompt(input_text: str, resolver_text: str, known_slugs: set[str]) -> str:
    """Build the routing-decision prompt."""
    slug_list = "\n".join(f"  - {s}" for s in sorted(known_slugs))
    return f"""You are a routing decision engine. Given the user's input and the RESOLVER table below, decide which ONE skill should fire.

# RESOLVER (canonical routing table)

{resolver_text}

# Known skill slugs (your answer MUST be one of these)

{slug_list}

# User input

"{input_text}"

# Instructions

Routing algorithm:
1. Choose the narrowest resolver row that directly names the user's verb/object.
2. Do not choose broad always-on rows such as `_gbrain/brain-ops` when a specific row matches.
3. Project-specific AGaaS rows beat generic rows when both mention the same literal.
4. `/ask` routes to `ceo-hierarchy`; `/status`, `/health`, `/handoff`, `/code`, and outbound Telegram commands route to `command-center`.
5. Brain write/capture/idea/link/article requests route to `_gbrain/idea-ingest`; brain lookup/search/citation requests route to `_gbrain/query`; task add/remove/complete/defer/review routes to `_gbrain/daily-task-manager`.
6. Air + SSH/Tailscale reachability routes to `air-ssh-access`; Mac Tailscale logged-out/version-mismatch/dual-install routes to `tailscale-stability`.
7. Task-execution planning such as "plan the task" or "what should I do next?" routes to `planning-discipline`; calendar/morning/meeting/day prep routes to `_gbrain/daily-task-prep`.

Return ONLY the slug of the single best-matching skill. Examples:
- For "check camera health" → camera-management
- For "deploy the website" → website-deploy
- For "/ask what's happening" → ceo-hierarchy

Reply with the slug only. No prose. No quotes. No markdown."""


def parse_skill_from_reply(reply: str, known_slugs: set[str]) -> str | None:
    """Extract a known skill slug from the LLM reply."""
    cleaned = reply.strip().strip("`'\" ").lower()

    # Direct match
    for slug in known_slugs:
        if slug.lower() == cleaned:
            return slug

    # Substring match (the LLM sometimes wraps)
    for slug in known_slugs:
        if slug.lower() in cleaned or cleaned in slug.lower():
            return slug

    # Try splitting on whitespace/newline
    for token in re.split(r"[\s\n,]+", cleaned):
        for slug in known_slugs:
            if slug.lower() == token:
                return slug

    return None


def run_judge(resolver_path: str, model: str, max_cases: int | None,
              base_url: str, api_key: str, json_output: bool) -> int:
    resolver_text = load_resolver(resolver_path)
    known_slugs = get_skill_slugs(resolver_text)

    if not known_slugs:
        print(f"ERROR: no skill slugs parsed from {resolver_path}", file=sys.stderr)
        return 2

    cases = TEST_CASES if max_cases is None else TEST_CASES[:max_cases]
    if not json_output:
        print(f"LLM judge: {len(cases)} test cases through {model} via {base_url}")
        print(f"Known skills: {len(known_slugs)}\n")

    passed = 0
    failed = []
    errors = []

    for i, (input_text, expected_skill, category) in enumerate(cases, 1):
        prompt = build_prompt(input_text, resolver_text, known_slugs)
        try:
            reply = call_litellm(prompt, model, base_url, api_key)
            chosen = parse_skill_from_reply(reply, known_slugs)
        except Exception as exc:
            chosen = None
            errors.append((input_text, expected_skill, f"{type(exc).__name__}: {exc}"))
            if not json_output:
                print(f"  [{i}/{len(cases)}] ERROR \"{input_text}\" → {exc}")
            continue

        if chosen == expected_skill:
            passed += 1
            if not json_output:
                print(f"  [{i}/{len(cases)}] PASS \"{input_text}\" → {chosen}")
        else:
            failed.append((input_text, expected_skill, chosen, reply))
            if not json_output:
                print(f"  [{i}/{len(cases)}] FAIL \"{input_text}\"")
                print(f"        expected: {expected_skill}")
                print(f"        got:      {chosen} (raw: {reply[:80]!r})")

    total = len(cases)
    rate = round(passed / total * 100, 1) if total else 0.0

    if json_output:
        print(json.dumps({
            "model": model,
            "total": total,
            "passed": passed,
            "failed": len(failed),
            "errors": len(errors),
            "rate": rate,
            "failures": [{"input": i, "expected": e, "got": g} for i, e, g, _ in failed],
            "errors_detail": [{"input": i, "expected": e, "error": err} for i, e, err in errors],
        }, indent=2))
    else:
        print(f"\n{'=' * 70}")
        print(f"LLM judge ({model}): {passed}/{total} = {rate}% pass")
        if errors:
            print(f"  Errors: {len(errors)}")
        print('=' * 70)

    return 0 if (len(failed) + len(errors)) == 0 else 1


def main():
    load_default_env()

    p = argparse.ArgumentParser(description="LLM-as-judge for RESOLVER routing")
    p.add_argument("--resolver",
                   default=str(Path.home() / "nous-agaas/wiki/pages/skills/_gbrain/RESOLVER.md"),
                   help="Path to canonical RESOLVER.md")
    p.add_argument("--model", default=os.environ.get("JUDGE_MODEL", "glm-5.1"),
                   help="Model name (LiteLLM-routed). Default: glm-5.1 (free via ZAI)")
    p.add_argument("--base-url",
                   default=os.environ.get("LITELLM_BASE_URL", "http://localhost:4000"),
                   help="LiteLLM base URL")
    p.add_argument("--api-key",
                   default=os.environ.get("LITELLM_MASTER_KEY", ""),
                   help="LiteLLM master key (default reads $LITELLM_MASTER_KEY)")
    p.add_argument("--max-cases", type=int, default=None,
                   help="Limit to N cases (for fast smoke test)")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable JSON output")
    args = p.parse_args()

    # Resolve path with fallbacks (mirror trigger_eval.py)
    if not Path(args.resolver).is_file():
        for alt in [
            Path.home() / "nous-agaas/wiki/pages/skills/_gbrain/RESOLVER.md",
            Path.home() / "Documents/Projects/Nous AGaaS/Nous/pages/skills/_gbrain/RESOLVER.md",
        ]:
            if alt.is_file():
                args.resolver = str(alt)
                break
        else:
            print(f"ERROR: RESOLVER not found at {args.resolver}", file=sys.stderr)
            sys.exit(2)

    if not args.api_key:
        print(
            "ERROR: missing LiteLLM API key. Expected $LITELLM_MASTER_KEY or "
            "~/nous-agaas/litellm/.env; refusing to run 68 unauthorized judge calls.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(run_judge(args.resolver, args.model, args.max_cases,
                       args.base_url, args.api_key, args.json))


if __name__ == "__main__":
    main()
