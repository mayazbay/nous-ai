import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "telegram_ingest_persist.py"
SPEC = importlib.util.spec_from_file_location("telegram_ingest_persist", MODULE_PATH)
telegram_ingest_persist = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(telegram_ingest_persist)


def test_redacts_apk_ip_admin_password_line():
    fake_password = "CameraPass_2026"
    body = f"Ип 10.145.1.2 admin {fake_password}\nЛокация и направление соответствует ЛУ100."

    redacted = telegram_ingest_persist.redact_sensitive_text(body)

    assert fake_password not in redacted
    assert "10.145.1.2 admin [REDACTED]" in redacted
    assert "ЛУ100" in redacted


def test_redacts_admin_slash_password_form():
    body = "OpenBrain summary normalized creds as admin/SlashPass_2026 for the camera."

    redacted = telegram_ingest_persist.redact_sensitive_text(body)

    assert "SlashPass_2026" not in redacted
    assert "admin/[REDACTED]" in redacted


def test_redacts_test_and_prod_environment_password_fields():
    body = (
        "test: ExampleTestSecret_123!\n"
        "prod: ExampleProdSecret_456!\n"
        "Public IP: 65.108.215.200\n"
        "Порт: 443\n"
        "Протокол: HTTPS"
    )

    redacted = telegram_ingest_persist.redact_sensitive_text(body)

    assert "ExampleTestSecret_123!" not in redacted
    assert "ExampleProdSecret_456!" not in redacted
    assert "test: [REDACTED]" in redacted
    assert "prod: [REDACTED]" in redacted
    assert "65.108.215.200" in redacted


def test_write_inbox_redacts_secret_in_title_and_body(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_ingest_persist, "VAULT", tmp_path)
    monkeypatch.setattr(telegram_ingest_persist, "INBOX_ROOT", tmp_path / "pages" / "inbox")

    slug = telegram_ingest_persist.write_inbox(
        chat_id=-1002064137259,
        msg_id=1747,
        body="10.145.1.2 admin CameraPass_2026\nЛУ 100, ул. Карбышева 44",
        sender="@aliakbar_asylbek",
    )
    content = (tmp_path / f"{slug}.md").read_text(encoding="utf-8")

    assert "CameraPass_2026" not in content
    assert "10.145.1.2 admin [REDACTED]" in content
    assert "LU100 APK access details redacted" not in content


def test_write_inbox_keeps_title_single_line_after_multiline_redaction(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_ingest_persist, "VAULT", tmp_path)
    monkeypatch.setattr(telegram_ingest_persist, "INBOX_ROOT", tmp_path / "pages" / "inbox")

    slug = telegram_ingest_persist.write_inbox(
        chat_id=-1002064137259,
        msg_id=1767,
        body="test: ExampleTestSecret_123!\nprod: ExampleProdSecret_456!\nPublic IP: 65.108.215.200",
        sender="@madi_ayazbay",
    )
    content = (tmp_path / f"{slug}.md").read_text(encoding="utf-8")
    frontmatter = content.split("---", 2)[1]

    assert "ExampleTestSecret_123!" not in content
    assert "ExampleProdSecret_456!" not in content
    assert 'title: "Telegram ingest' in frontmatter
    assert "\nprod:" not in frontmatter
