from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import hermes_24h_gate_verifier as verifier


ALMATY = dt.timezone(dt.timedelta(hours=5))


def _args(tmp_path: Path, *, now: str = "2026-05-23T03:50:00+05:00", min_samples: int = 2) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=tmp_path,
        python=Path("python3"),
        watchdog_log=tmp_path / "logs/hermes-factory-watchdog.jsonl",
        verifier_log=tmp_path / "logs/hermes-24h-gate-verifier.jsonl",
        state_page=Path("pages/systems/hermes-24h-gate-verifier-status.md"),
        min_samples=min_samples,
        now=now,
        dry_run=False,
        no_writeback=True,
        no_telegram=True,
        json=True,
    )


def _reset(tmp_path: Path) -> None:
    path = tmp_path / "pages/audits/HERMES-24H-GATE-RESET-2026-05-22.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Reset\n\n"
        "Earliest strict green 24h candidate:\n\n"
        "```text\n"
        "2026-05-23 03:45 KZT\n"
        "```\n",
        encoding="utf-8",
    )


def _watchdog_log(path: Path, rows: list[tuple[str, str, int]]) -> None:
    path.parent.mkdir(parents=True)
    rendered = []
    for finished_at, overall, reds in rows:
        rendered.append(
            {
                "finished_at": finished_at,
                "checks": [
                    {
                        "name": "factory_probe",
                        "status": "done" if overall == "GREEN" and reds == 0 else "not_done",
                        "summary": "factory probe green" if overall == "GREEN" and reds == 0 else "factory probe red",
                        "evidence": {"overall": overall, "reds": reds},
                    }
                ],
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rendered) + "\n", encoding="utf-8")


def test_pending_before_candidate_does_not_write_receipt(tmp_path: Path) -> None:
    _reset(tmp_path)
    args = _args(tmp_path, now="2026-05-23T03:30:00+05:00")

    report = verifier.apply_outputs(args, verifier.evaluate(args))

    assert report["overall_status"] == "pending"
    assert report["reason"] == "candidate window has not elapsed"
    assert not list((tmp_path / "pages/audits").glob("HERMES-24H-GATE-GREEN-*.md"))


def test_red_watchdog_sample_blocks_receipt(tmp_path: Path) -> None:
    _reset(tmp_path)
    args = _args(tmp_path)
    _watchdog_log(
        args.watchdog_log,
        [
            ("2026-05-22T04:00:00+05:00", "GREEN", 0),
            ("2026-05-23T03:45:00+05:00", "RED", 1),
        ],
    )

    report = verifier.apply_outputs(args, verifier.evaluate(args))

    assert report["overall_status"] == "pending"
    assert report["watchdog"]["bad_count"] == 1
    assert not list((tmp_path / "pages/audits").glob("HERMES-24H-GATE-GREEN-*.md"))


def test_insufficient_watchdog_samples_blocks_receipt(tmp_path: Path) -> None:
    _reset(tmp_path)
    args = _args(tmp_path, min_samples=3)
    _watchdog_log(
        args.watchdog_log,
        [
            ("2026-05-22T04:00:00+05:00", "GREEN", 0),
            ("2026-05-23T03:45:00+05:00", "GREEN", 0),
        ],
    )

    report = verifier.apply_outputs(args, verifier.evaluate(args))

    assert report["overall_status"] == "pending"
    assert report["watchdog"]["sample_count"] == 2
    assert not list((tmp_path / "pages/audits").glob("HERMES-24H-GATE-GREEN-*.md"))


def test_eligible_window_writes_receipt_and_uses_non_promoting_runner(tmp_path: Path, monkeypatch) -> None:
    _reset(tmp_path)
    args = _args(tmp_path)
    _watchdog_log(
        args.watchdog_log,
        [
            ("2026-05-22T04:00:00+05:00", "GREEN", 0),
            ("2026-05-23T03:45:00+05:00", "GREEN", 0),
        ],
    )
    commands: list[str] = []

    def fake_run(cmd, *, cwd=None, timeout=180):
        commands.append(" ".join(str(part) for part in cmd))
        if "factory_no_drift_probe.sh" in commands[-1]:
            return {"ok": True, "returncode": 0, "stdout": '{"overall":"GREEN","reds":0}', "stderr": ""}
        if "hermes_canary_gate.py" in commands[-1]:
            return {"ok": True, "returncode": 0, "stdout": '{"overall":"GREEN","reds":0}', "stderr": ""}
        if "hermes_promotion_runner.py" in commands[-1]:
            return {"ok": True, "returncode": 0, "stdout": '{"overall":"GREEN","promoted":false}', "stderr": ""}
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(verifier, "run", fake_run)

    report = verifier.apply_outputs(args, verifier.evaluate(args))

    receipt = tmp_path / "pages/audits/HERMES-24H-GATE-GREEN-2026-05-23.md"
    assert report["overall_status"] == "done"
    assert receipt.exists()
    assert verifier.GREEN_MARKER in receipt.read_text(encoding="utf-8")
    promotion_commands = [cmd for cmd in commands if "hermes_promotion_runner.py" in cmd]
    assert len(promotion_commands) == 1
    assert "--promote" not in promotion_commands[0]


def test_existing_green_receipt_prevents_duplicate(tmp_path: Path, monkeypatch) -> None:
    _reset(tmp_path)
    existing = tmp_path / "pages/audits/HERMES-24H-GATE-GREEN-2026-05-23.md"
    existing.write_text("---\nstatus: green\n---\n\n" + verifier.GREEN_MARKER + "\n", encoding="utf-8")
    args = _args(tmp_path)

    monkeypatch.setattr(verifier, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run probes")))

    report = verifier.apply_outputs(args, verifier.evaluate(args))

    assert report["overall_status"] == "done"
    assert report["reason"] == "green receipt already exists"
    assert len(list((tmp_path / "pages/audits").glob("HERMES-24H-GATE-GREEN-*.md"))) == 1
