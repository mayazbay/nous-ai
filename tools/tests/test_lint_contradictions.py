import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("wiki_root_lint", ROOT / "lint.py")
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


def write_page(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_status_contradictions_ignore_frontmatter_and_laws(tmp_path):
    dashboard = write_page(
        tmp_path / "pages" / "dashboards" / "ops.md",
        """---
type: dashboard
title: "Factory dashboard"
status: active
---

# Factory dashboard

OpenClaw route is green.
""",
    )
    law = write_page(
        tmp_path / "laws" / "AMENDMENT-001-circuit-breaker.md",
        """---
type: amendment
id: AMD-001
---

# Circuit Breaker

Factory kept retrying the same broken task forever. This is why the rule exists.
""",
    )

    assert lint.check_contradictions([dashboard, law]) == []


def test_status_contradictions_still_flag_current_pages(tmp_path):
    active = write_page(tmp_path / "pages" / "systems" / "factory-green.md", "factory is active now")
    broken = write_page(tmp_path / "pages" / "systems" / "factory-red.md", "factory is broken now")

    contradictions = lint.check_contradictions([active, broken])

    assert contradictions == [
        "FACTORY STATUS CONFLICT (non-historical): factory-green.md=active, factory-red.md=broken"
    ]
