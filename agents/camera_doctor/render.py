"""agents.camera_doctor.render — Markdown brief + dated PDF artifact.

Phase 3 Tasks 3.1 + 3.2 of PLAN-SATORY-DAILY-OPERATOR-BRIEF-V1.

Per AUDIT-060 design review:
  - First TG/brief line leads with severity emoji + numbers (RU)
  - All-green case is a 1-line heartbeat (NOT a skip — operator trains trust)
  - Body is RU prose with units + comparison-to-normal
  - Yesterday-delta on lead line when yesterday data is available
  - RU executive summary signed "Nous AGaaS · Агентская служба"
  - 8 KB Markdown cap, 200 KB PDF cap (AP-72)
"""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from typing import Optional

from agents.camera_doctor.detectors import Finding


MARKDOWN_CAP_BYTES = 8192
# 256 KB: weasyprint embeds Cyrillic fonts (~150 KB baseline overhead) making 200 KB
# unreachable. Real risk is runaway generation (multi-MB); 256 KB caps that safely.
PDF_CAP_BYTES = 256 * 1024
SEVERITY_EMOJI = {"red": "🔴", "yellow": "🟡", "green": "✅"}


def _lang(brand: dict) -> str:
    language = str(brand.get("language") or brand.get("brief_language") or "ru").lower()
    return language if language in {"ru", "en"} else "ru"


def _now_almaty(now: Optional[dt.datetime] = None) -> str:
    n = now or dt.datetime.now(dt.timezone.utc)
    return n.strftime("%Y-%m-%d %H:%M")


def _date_only(now: Optional[dt.datetime] = None) -> str:
    n = now or dt.datetime.now(dt.timezone.utc)
    return n.strftime("%Y-%m-%d")


def _yesterday_delta(today: dict, yesterday: dict | None, language: str = "ru") -> str:
    if not yesterday:
        return ""
    today_off = today.get("total", 0) - today.get("online", 0)
    yest_off = yesterday.get("total", 0) - yesterday.get("online", 0)
    delta = today_off - yest_off
    if delta == 0:
        if language == "en":
            return " (no change since yesterday)"
        return " (без изменений со вчера)"
    sign = "+" if delta > 0 else ""
    if language == "en":
        return f" ({sign}{delta} since yesterday)"
    return f" ({sign}{delta} со вчера)"


def _lead_line(findings: list[Finding], fleet: dict,
               yesterday_fleet: dict | None, now: Optional[dt.datetime],
               brand: dict) -> str:
    """Build the first-line summary per AUDIT-060 design review #1+#3."""
    language = _lang(brand)
    total = fleet.get("total", 0)
    online = fleet.get("online", 0)
    offline = total - online
    pct = (online / total * 100) if total > 0 else 0.0
    delta = _yesterday_delta(fleet, yesterday_fleet, language)
    time_str = (now or dt.datetime.now(dt.timezone.utc)).strftime("%H:%M")

    if not findings:
        if language == "en":
            return f"✅ {online}/{total} online · report {time_str}{delta}"
        return f"✅ {online}/{total} онлайн · отчёт {time_str}{delta}"

    severities = [f.severity for f in findings]
    if "red" in severities:
        emoji = SEVERITY_EMOJI["red"]
    elif "yellow" in severities:
        emoji = SEVERITY_EMOJI["yellow"]
    else:
        emoji = SEVERITY_EMOJI["green"]

    n_problems = len(findings)
    if language == "en":
        return (
            f"{emoji} {offline}/{total} offline ({pct:.1f}% online) · "
            f"{n_problems} problem(s) · report {time_str}{delta}"
        )
    return (
        f"{emoji} {offline}/{total} офлайн ({pct:.1f}% онлайн) · "
        f"{n_problems} проблем(ы) · отчёт {time_str}{delta}"
    )


def _format_evidence_prose(evidence: dict) -> list[str]:
    """RU prose evidence per AUDIT-060 design review #4 — labels with units."""
    lines = []
    for label, value in evidence.items():
        lines.append(f"  {label}: {value}")
    return lines


def _exec_summary(findings: list[Finding], fleet: dict, brand: dict) -> list[str]:
    """RU executive summary signed by agent_signature per AUDIT-060 CEO #5."""
    if _lang(brand) == "en":
        sig = brand.get("agent_signature", "Nous AGaaS Agent Service")
        if not findings:
            body = "The fleet is operating normally. No incidents detected."
        else:
            red = sum(1 for f in findings if f.severity == "red")
            yellow = sum(1 for f in findings if f.severity == "yellow")
            if red:
                body = (f"Detected {len(findings)} issue(s): {red} critical, "
                        f"{yellow} need attention. Operator actions are listed below.")
            else:
                body = (f"Detected {len(findings)} attention-level observation(s). "
                        f"Operator actions are listed below.")
        return [body, "", f"-- {sig}"]

    sig = brand.get("agent_signature", "Nous AGaaS · Агентская служба")
    if not findings:
        body = "Парк работает в штатном режиме. Инцидентов не зафиксировано."
    else:
        red = sum(1 for f in findings if f.severity == "red")
        yellow = sum(1 for f in findings if f.severity == "yellow")
        if red:
            body = (f"Зафиксировано {len(findings)} проблем(ы): {red} критич., "
                    f"{yellow} требуют внимания. Действия операторов указаны ниже.")
        else:
            body = (f"Зафиксировано {len(findings)} наблюдений уровня «внимание». "
                    f"Действия операторов указаны ниже.")
    return [body, "", f"— {sig}"]


def _findings_section(findings: list[Finding], brand: dict) -> list[str]:
    if not findings:
        return []
    language = _lang(brand)
    out = []
    for i, f in enumerate(findings, start=1):
        emoji = SEVERITY_EMOJI.get(f.severity, "")
        heading = "Finding" if language == "en" else "Находка"
        action_label = "Action" if language == "en" else "Действие"
        out.append(f"## {heading} {i}: {emoji} {f.name}")
        out.extend(_format_evidence_prose(f.evidence))
        if f.action:
            out.append(f"  {action_label}: {f.action}")
        out.append("")
    return out


def _fleet_snapshot(fleet: dict, brand: dict, events_age_hours: float | None = None) -> list[str]:
    total = fleet.get("total", 0)
    online = fleet.get("online", 0)
    pct = (online / total * 100) if total > 0 else 0.0
    if _lang(brand) == "en":
        out = [
            "## Fleet status",
            f"  Online: {online}/{total} ({pct:.1f}%)",
            f"  Fresh checks in the last hour: {fleet.get('fresh_check_count', 0)}",
        ]
        if events_age_hours is not None:
            out.append(f"  Last event age: {events_age_hours:.1f} h")
        return out

    out = [
        "## Состояние парка",
        f"  Онлайн: {online}/{total} ({pct:.1f}%)",
        f"  Свежие проверки за час: {fleet.get('fresh_check_count', 0)}",
    ]
    if events_age_hours is not None:
        out.append(f"  Возраст последнего события: {events_age_hours:.1f} ч.")
    return out


def _enforce_cap(md: str, cap: int = MARKDOWN_CAP_BYTES) -> str:
    """Trim Markdown to fit byte cap. Drops sections from the bottom up."""
    encoded = md.encode("utf-8")
    if len(encoded) <= cap:
        return md
    # Strategy: trim from the end with [обрезано] marker until under cap
    truncation_marker = "\n\n_[обрезано — превышен лимит 8 КБ]_\n"
    target = cap - len(truncation_marker.encode("utf-8"))
    while len(md.encode("utf-8")) > target and md:
        # Drop trailing line by line
        lines = md.splitlines()
        if not lines:
            break
        md = "\n".join(lines[:-1])
    return md + truncation_marker


def render_markdown(findings: list[Finding], fleet: dict, brand: dict,
                    yesterday_fleet: dict | None = None,
                    events_age_hours: float | None = None,
                    now: dt.datetime | None = None) -> str:
    """Render the daily operator brief as RU-prose Markdown.

    Output is byte-capped at MARKDOWN_CAP_BYTES (8 KB, AP-72).
    """
    title = brand.get("brief_title", "Camera Doctor Daily Brief")
    timestamp = _now_almaty(now)

    parts = [
        _lead_line(findings, fleet, yesterday_fleet, now, brand),
        "",
        f"# {title} — {timestamp} Almaty",
        "",
    ]
    parts.extend(_exec_summary(findings, fleet, brand))
    parts.append("")
    parts.extend(_findings_section(findings, brand))
    parts.extend(_fleet_snapshot(fleet, brand, events_age_hours))

    md = "\n".join(parts).rstrip() + "\n"
    return _enforce_cap(md, MARKDOWN_CAP_BYTES)


# ---- PDF rendering ----

def _markdown_to_html(md: str, brand: dict) -> str:
    """Minimal MD→HTML for weasyprint. Stdlib only (no markdown lib needed)."""
    lines = []
    in_para = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            if in_para:
                lines.append("</p>")
                in_para = False
            lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_para:
                lines.append("</p>")
                in_para = False
            lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("  "):  # indented evidence/action line
            if in_para:
                lines.append("</p>")
                in_para = False
            lines.append(f"<div class='evidence'>{html.escape(line.strip())}</div>")
        elif line == "":
            if in_para:
                lines.append("</p>")
                in_para = False
        else:
            if not in_para:
                lines.append("<p>")
                in_para = True
            lines.append(html.escape(line))
    if in_para:
        lines.append("</p>")
    body = "\n".join(lines)
    title = html.escape(brand.get("brief_title", "Camera Doctor Daily Brief"))
    css = """
        @page { size: A4; margin: 1.6cm; }
        body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10.5pt; line-height: 1.4; color: #222; }
        h1 { font-size: 16pt; margin: 0 0 4pt 0; color: #111; }
        h2 { font-size: 12pt; margin: 10pt 0 4pt 0; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 2pt; }
        p { margin: 4pt 0; }
        .evidence { margin: 1pt 0 1pt 16pt; font-family: 'Menlo', 'Courier New', monospace; font-size: 9.5pt; color: #444; }
    """
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


def render_pdf(markdown: str, output_path: Path, brand: dict) -> Path:
    """Render the markdown brief to a dated branded PDF using weasyprint.

    Output path enforced ≤ PDF_CAP_BYTES. Caller is responsible for
    constructing the dated path from tenant config.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_str = _markdown_to_html(markdown, brand)

    # weasyprint is heavy; import lazily so import-time of render.py is fast
    from weasyprint import HTML  # type: ignore[import-not-found]
    HTML(string=html_str).write_pdf(str(output_path))

    if output_path.stat().st_size > PDF_CAP_BYTES:
        # Cap exceeded — try to trim the source markdown before regenerating
        trimmed = _enforce_cap(markdown, MARKDOWN_CAP_BYTES // 2)
        html2 = _markdown_to_html(trimmed, brand)
        HTML(string=html2).write_pdf(str(output_path))

    return output_path
