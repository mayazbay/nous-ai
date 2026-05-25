"""agents.camera_doctor — Tenant-agnostic Camera Doctor / Daily Operator Brief.

Per PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1 (2026-04-29):
- Single agent, configured per-tenant via tenants/<name>/camera_doctor.toml
- 3 detectors: Mirrors Stopped (vehicle_events), VPN/Network Down (camera_status
  + wg handshake), Fleet Degraded (camera_status online %)
- Output: RU-prose Markdown + dated branded PDF + Telegram message
- Run-log: append-only JSONL with full reasoning trace
- Reuses tenants/satory/agents/lib/{notion_client,tg_send,state_db}.py
"""
__version__ = "0.1.0"
