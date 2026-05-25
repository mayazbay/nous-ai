from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import mercury_seed as seed


def _fact(fid: str, subject: str, value: str) -> dict:
    return {
        "id": fid,
        "subject": subject,
        "value": value,
        "value_hash": seed.value_hash(value),
        "freshness": "2026-05-20",
        "source": f"[[skills/{subject.split('.')[0]}/skill]]",
        "reinforcement": 0,
        "conflicts_with": [],
        "load_bearing_in": [],
        "tombstone": False,
        "tombstone_reason": None,
        "tombstone_ts": None,
    }


def test_new_fact_does_not_steal_preserved_existing_fact_id() -> None:
    old_camera = _fact(
        "fact-00059",
        "camera-management.ap-1",
        "Never set ISAPI2 auth to None on production cameras",
    )
    existing = {seed.fact_identity(old_camera): old_camera}

    new_bdl = _fact(
        "fact-00059",
        "bdl-cerebro-replacement-gate.ap-5",
        "Audience-language discipline",
    )
    shifted_camera = _fact(
        "fact-00060",
        "camera-management.ap-1",
        "Never set ISAPI2 auth to None on production cameras",
    )

    facts = [new_bdl, shifted_camera]
    seed.preserve_existing_metadata(facts, existing)
    seed.assign_ids_for_new_facts(facts, existing)

    by_subject = {fact["subject"]: fact for fact in facts}
    assert by_subject["camera-management.ap-1"]["id"] == "fact-00059"
    assert by_subject["bdl-cerebro-replacement-gate.ap-5"]["id"] != "fact-00059"
    assert len({fact["id"] for fact in facts}) == len(facts)
