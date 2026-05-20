from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import audit_satory_todoist_state as audit


def test_test_proposal_deleted_offscope_links_are_ignored() -> None:
    proposal_links = [
        {
            "source_kind": "telegram-forward",
            "source_ref": "test-s68p-20260423-live",
            "linked_tasks": [
                {
                    "task_id": "deleted-test",
                    "status": "deleted",
                    "off_scope": True,
                }
            ],
        }
    ]

    risks, ignored = audit.classify_proposal_link_risks(proposal_links)

    assert risks == []
    assert ignored == 1


def test_non_test_deleted_offscope_links_remain_risks() -> None:
    proposal_links = [
        {
            "source_kind": "codex-keona",
            "source_ref": "2026-05-11-keona-team-update",
            "linked_tasks": [
                {
                    "task_id": "deleted-real",
                    "status": "deleted",
                    "off_scope": True,
                }
            ],
        }
    ]

    risks, ignored = audit.classify_proposal_link_risks(proposal_links)

    assert ignored == 0
    assert risks == [
        "state_linked_tasks_deleted:1",
        "state_linked_tasks_off_scope_after_direct_lookup:1",
    ]
