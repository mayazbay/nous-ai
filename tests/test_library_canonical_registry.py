"""Unit tests for tools/library_canonical_registry.py (Ship 3 wave 1a).

Each test uses ``tmp_path`` as the wiki root via the ``NOUS_WIKI`` env var
(for the CLI subprocess test) and explicit ``wiki=`` kwargs (for direct
function calls). The registry's append-only JSONL + fcntl lock are exercised
in isolation per test.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).resolve().parent
TOOLS_DIR = THIS_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Load by file path to keep this isolated from any future module-name
# collisions (matches the pattern in test_queue.py).
_MOD_PATH = TOOLS_DIR / "library_canonical_registry.py"
_spec = importlib.util.spec_from_file_location(
    "tools_library_canonical_registry", _MOD_PATH
)
assert _spec is not None and _spec.loader is not None
reg = importlib.util.module_from_spec(_spec)
sys.modules["tools_library_canonical_registry"] = reg
_spec.loader.exec_module(reg)


KZT = dt.timezone(dt.timedelta(hours=5))
CROCKFORD_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]+$")


def _read_rows(wiki: Path) -> list[dict]:
    path = wiki / reg.REGISTRY_REL
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. ULID format
# ---------------------------------------------------------------------------

def test_generate_ulid_format():
    uid = reg.generate_ulid()
    assert len(uid) == 26, f"expected 26 chars, got {len(uid)}: {uid!r}"
    # Crockford base32 alphabet — no I, L, O, U.
    assert CROCKFORD_RE.match(uid), f"non-Crockford char in {uid!r}"
    for forbidden in ("I", "L", "O", "U"):
        assert forbidden not in uid, f"forbidden char {forbidden!r} in {uid!r}"


# ---------------------------------------------------------------------------
# 2. ULID monotonicity
# ---------------------------------------------------------------------------

def test_generate_ulid_monotonic():
    """Generate 100 ULIDs in succession; their natural order must be sorted.

    ULIDs encode a 48-bit ms timestamp first; within the same ms the random
    suffix may break monotonicity. We feed explicit increasing ``now`` values
    so the timestamp prefix strictly advances and the test is deterministic.
    """
    base = dt.datetime(2026, 5, 20, 12, 0, 0, tzinfo=KZT)
    uids = [reg.generate_ulid(now=base + dt.timedelta(milliseconds=i)) for i in range(100)]
    assert uids == sorted(uids), "ULIDs not lex-monotonic"
    assert len(set(uids)) == 100, "ULIDs should be unique"


# ---------------------------------------------------------------------------
# 3. Slugify
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert reg.slugify("Model Failover Latest") == "model-failover-latest"
    assert reg.slugify("Hello_World!!") == "hello-world"
    assert reg.slugify("  Spaces  ") == "spaces"
    assert reg.slugify("") == ""
    # Unicode normalization preserves ascii equivalents.
    assert reg.slugify("Café") == "cafe"
    # Collapse repeated separators.
    assert reg.slugify("a---b___c") == "a-b-c"


# ---------------------------------------------------------------------------
# 4. file_content_hash — missing file
# ---------------------------------------------------------------------------

def test_file_content_hash_empty_for_missing(tmp_path: Path):
    h = reg.file_content_hash(tmp_path / "missing.md")
    assert h == "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# ---------------------------------------------------------------------------
# 5. file_content_hash — changes with content
# ---------------------------------------------------------------------------

def test_file_content_hash_changes_with_content(tmp_path: Path):
    f = tmp_path / "x.md"
    f.write_text("a", encoding="utf-8")
    h1 = reg.file_content_hash(f)
    f.write_text("ab", encoding="utf-8")
    h2 = reg.file_content_hash(f)
    assert h1.startswith("sha256:") and h2.startswith("sha256:")
    assert h1 != h2


# ---------------------------------------------------------------------------
# 6. title_from_path — frontmatter wins
# ---------------------------------------------------------------------------

def test_title_from_path_frontmatter(tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text(
        "---\ntitle: Foo Bar\nother: x\n---\n# Other Heading\n\nbody\n",
        encoding="utf-8",
    )
    assert reg.title_from_path(f) == "Foo Bar"


# ---------------------------------------------------------------------------
# 7. title_from_path — H1 fallback
# ---------------------------------------------------------------------------

def test_title_from_path_h1(tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text("# Some Title\n\nbody\n", encoding="utf-8")
    assert reg.title_from_path(f) == "Some Title"


# ---------------------------------------------------------------------------
# 8. title_from_path — filename fallback
# ---------------------------------------------------------------------------

def test_title_from_path_filename_fallback(tmp_path: Path):
    f = tmp_path / "my-doc.md"
    f.write_text("just body, no frontmatter, no heading\n", encoding="utf-8")
    assert reg.title_from_path(f) == "My Doc"


# ---------------------------------------------------------------------------
# 9. add — idempotent on same obsidian_path
# ---------------------------------------------------------------------------

def test_add_idempotent_same_path(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "x" / "y.md", "# Y\n")
    uid1 = reg.add("x/y.md", wiki=wiki)
    uid2 = reg.add("x/y.md", wiki=wiki)
    assert uid1 == uid2
    rows = _read_rows(wiki)
    assert len(rows) == 1, f"expected 1 row, got {len(rows)}"


# ---------------------------------------------------------------------------
# 10. add — different paths get different uuids
# ---------------------------------------------------------------------------

def test_add_assigns_new_uuid_for_new_path(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "a.md", "# A\n")
    _write_file(wiki / "b.md", "# B\n")
    ua = reg.add("a.md", wiki=wiki)
    ub = reg.add("b.md", wiki=wiki)
    assert ua != ub
    rows = _read_rows(wiki)
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# 11. get — by uuid, path, alias all return same entry
# ---------------------------------------------------------------------------

def test_get_by_uuid_path_alias(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "foo-bar.md", "# Foo Bar\n")
    uid = reg.add("foo-bar.md", wiki=wiki, aliases=["foo-bar", "fb"])
    by_uuid = reg.get(uuid=uid, wiki=wiki)
    by_path = reg.get(path="foo-bar.md", wiki=wiki)
    by_alias = reg.get(alias="fb", wiki=wiki)
    assert by_uuid is not None
    assert by_uuid == by_path == by_alias
    assert by_uuid["canonical_uuid"] == uid
    # Missing lookup returns None.
    assert reg.get(uuid="nope", wiki=wiki) is None
    assert reg.get(path="nope.md", wiki=wiki) is None
    assert reg.get(alias="nope", wiki=wiki) is None


# ---------------------------------------------------------------------------
# 12. update_field — allowed field appends new row
# ---------------------------------------------------------------------------

def test_update_field_allowed_appends_new_row(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "z.md", "# Z\n")
    uid = reg.add("z.md", wiki=wiki)
    ok = reg.update_field(uid, "title", "X", wiki=wiki)
    assert ok is True
    entry = reg.get(uuid=uid, wiki=wiki)
    assert entry is not None
    assert entry["title"] == "X"
    # Slug should track updated title.
    assert entry["slug"] == "x"
    rows = _read_rows(wiki)
    assert len(rows) == 2, f"expected 2 rows after update, got {len(rows)}"


# ---------------------------------------------------------------------------
# 13. update_field — disallowed field returns False, no new row
# ---------------------------------------------------------------------------

def test_update_field_disallowed_returns_false(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "z.md", "# Z\n")
    uid = reg.add("z.md", wiki=wiki)
    before = len(_read_rows(wiki))
    assert reg.update_field(uid, "canonical_uuid", "new", wiki=wiki) is False
    assert reg.update_field(uid, "obsidian_path", "other.md", wiki=wiki) is False
    assert reg.update_field(uid, "slug", "x", wiki=wiki) is False
    assert reg.update_field(uid, "created", "now", wiki=wiki) is False
    after = len(_read_rows(wiki))
    assert before == after, "disallowed updates must not append a row"
    # Unknown uuid → False (and no row).
    assert reg.update_field("nope", "title", "X", wiki=wiki) is False
    assert len(_read_rows(wiki)) == after


# ---------------------------------------------------------------------------
# 14. list_all — sorted by created
# ---------------------------------------------------------------------------

def test_list_all_returns_current_state_sorted_by_created(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "a.md", "# A\n")
    _write_file(wiki / "b.md", "# B\n")
    _write_file(wiki / "c.md", "# C\n")

    t0 = dt.datetime(2026, 5, 20, 10, 0, 0, tzinfo=KZT)
    ua = reg.add("a.md", wiki=wiki, now=t0)
    ub = reg.add("b.md", wiki=wiki, now=t0 + dt.timedelta(seconds=1))
    uc = reg.add("c.md", wiki=wiki, now=t0 + dt.timedelta(seconds=2))

    entries = reg.list_all(wiki=wiki)
    assert [e["canonical_uuid"] for e in entries] == [ua, ub, uc]
    # And update on the middle entry doesn't break ordering by created.
    reg.update_field(ub, "title", "B-new", wiki=wiki, now=t0 + dt.timedelta(seconds=5))
    entries = reg.list_all(wiki=wiki)
    assert [e["canonical_uuid"] for e in entries] == [ua, ub, uc]
    middle = next(e for e in entries if e["canonical_uuid"] == ub)
    assert middle["title"] == "B-new"


# ---------------------------------------------------------------------------
# 15. CLI subprocess — add + get --json
# ---------------------------------------------------------------------------

def test_main_cli_add_get_json(tmp_path: Path):
    wiki = tmp_path
    _write_file(wiki / "foo.md", "# Foo\n")
    env = {**os.environ, "NOUS_WIKI": str(wiki)}

    # add
    out = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library_canonical_registry.py"),
         "add", "--path", "foo.md"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        check=False,
    )
    assert out.returncode == 0, f"add stderr: {out.stderr}"
    uid = out.stdout.strip()
    assert len(uid) == 26 and CROCKFORD_RE.match(uid), f"bad uid {uid!r}"

    # get --json
    out = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library_canonical_registry.py"),
         "get", "--uuid", uid, "--json"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        check=False,
    )
    assert out.returncode == 0, f"get stderr: {out.stderr}"
    entry = json.loads(out.stdout)
    assert entry["canonical_uuid"] == uid
    assert entry["obsidian_path"] == "foo.md"
    assert entry["title"] == "Foo"

    # get --path --field title (scalar field roundtrip)
    out = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library_canonical_registry.py"),
         "get", "--path", "foo.md", "--field", "title"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        check=False,
    )
    assert out.returncode == 0
    assert out.stdout.strip() == "Foo"

    # list --json
    out = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "library_canonical_registry.py"),
         "list", "--json"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        check=False,
    )
    assert out.returncode == 0
    listed = json.loads(out.stdout)
    assert len(listed) == 1
    assert listed[0]["canonical_uuid"] == uid
