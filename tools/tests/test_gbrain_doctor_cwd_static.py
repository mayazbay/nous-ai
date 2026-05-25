from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_scheduled_gbrain_doctor_probes_cd_to_repo_root():
    for rel in ("tools/morning-brief.sh", "tools/nightly-audit.sh"):
        body = (ROOT / rel).read_text()
        assert "cd /opt/nous-agaas/gbrain && bin/gbrain doctor" in body
        assert "/opt/nous-agaas/gbrain/bin/gbrain doctor" not in body


def test_gbrain_ops_documents_root_skills_doctor_shim():
    body = (ROOT / "pages/skills/gbrain-ops/SKILL.md").read_text()
    assert "AP-110" in body
    assert "ln -sfn /opt/nous-agaas/gbrain/skills /root/skills" in body
