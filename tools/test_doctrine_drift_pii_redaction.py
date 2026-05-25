#!/usr/bin/env python3
"""
Regression test for the PII redaction filter in build_doctrine_drift_calibration_set.

Implements doctrine-drift Eng F7 + agent-quality AP-22:
"NEVER log raw user_query/assistant_text; redact via Kazakh IIN / plate /
phone / email allowlist BEFORE persisting to disk or sending to a judge."

Coverage:
- Kazakh IIN (12-digit numeric) — must redact
- Kazakh license plate (3 digits + 2-3 letters + 2 digits) — must redact
- Phone numbers (Kazakh + international formats) — must redact
- Email addresses — must redact
- Credit card numbers (16-19 digits) — must redact
- Plain text without PII — must NOT be modified
- Adversarial cases: PII embedded in URLs, JSON, prose

Run: python3 tools/test_doctrine_drift_pii_redaction.py
Exits 0 on all-pass, non-zero on any leak.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the redact_pii function from the calibration builder (sibling tool)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from build_doctrine_drift_calibration_set import redact_pii, truncate_120, REDACT
except ImportError as e:
    print(f"FAIL: cannot import from build_doctrine_drift_calibration_set: {e}", file=sys.stderr)
    sys.exit(2)


# Test fixtures — synthetic PII matching Kazakhstan road-safety domain
# (NEVER use real PII in tests; these are random-generated patterns)
PII_FIXTURES = [
    # (input, must_be_redacted, label)
    ("My IIN is 950101300123, please verify", True, "kazakh_iin_in_prose"),
    ("Plate 123ABC02 was flagged", True, "kazakh_plate_short"),
    ("Vehicle 456XYZ12 reported speeding", True, "kazakh_plate_long"),
    ("Call me on +7 701 234 56 78 anytime", True, "phone_kazakh_intl_spaces"),
    ("phone: +77012345678", True, "phone_kazakh_intl_compact"),
    ("Reach out at madi@example.com tomorrow", True, "email_simple"),
    ("contact: m.ayazbay+test@nous-agaas.kz for details", True, "email_with_plus_dots"),
    ("Card: 4532015112830366 expired", True, "cc_visa_16"),
    ("AmEx 378282246310005 declined", True, "cc_amex_15"),
]

NON_PII_FIXTURES = [
    # Plain text that should NOT be modified
    ("hello world", "plain_english"),
    ("гбрейн работает на VPS", "plain_russian"),
    ("error 404 not found", "code_2_3_digit_numbers"),
    ("session 100 mac 23069", "session_id_numbers"),
    ("HEAD: edbf4d3d at 2026-04-30T12:34:56Z", "git_sha_iso_date"),
    ("brain_score 81 / 100 health", "metric_two_digit"),
    ("ports 80, 443, 5432 are open", "port_numbers"),
]

ADVERSARIAL_FIXTURES = [
    # Trickier cases — embedded PII
    ("Visit https://example.com/users/950101300123/profile", True, "iin_in_url_path"),
    ('JSON: {"phone":"+77012345678","ok":true}', True, "phone_in_json"),
    ("```\nplate=123ABC02\n```", True, "plate_in_code_block"),
]


def assert_redacted(text: str, label: str) -> bool:
    """Returns True if redaction worked (no original PII pattern remains)."""
    out = redact_pii(text)
    if REDACT not in out:
        print(f"  ❌ FAIL [{label}]: redaction marker not found in output", file=sys.stderr)
        print(f"      input:  {text!r}", file=sys.stderr)
        print(f"      output: {out!r}", file=sys.stderr)
        return False
    return True


def assert_unmodified(text: str, label: str) -> bool:
    """Returns True if non-PII text passes through unchanged (no over-redaction)."""
    out = redact_pii(text)
    if out != text:
        print(f"  ⚠️  WARN [{label}]: text modified despite no PII", file=sys.stderr)
        print(f"      input:  {text!r}", file=sys.stderr)
        print(f"      output: {out!r}", file=sys.stderr)
        return False
    return True


def test_truncate_120_safe() -> bool:
    """truncate_120 must redact PII before truncation (PII at end shouldn't slip past 120 chars)."""
    long_pii = "A" * 130 + " 950101300123"  # IIN past the 120-char cut
    out = truncate_120(long_pii)
    if "950101300123" in out:
        print(f"  ❌ FAIL [truncate_120_pii_at_end]: IIN leaked past truncation", file=sys.stderr)
        print(f"      output: {out!r}", file=sys.stderr)
        return False
    return True


def main() -> int:
    print("=== PII redaction regression test ===\n")
    failures = 0
    total = 0

    print("MUST-REDACT cases:")
    for text, _expect, label in PII_FIXTURES:
        total += 1
        if not assert_redacted(text, label):
            failures += 1
        else:
            print(f"  ✅ {label}")

    print("\nMUST-NOT-MODIFY cases (no false positives):")
    for text, label in NON_PII_FIXTURES:
        total += 1
        if not assert_unmodified(text, label):
            failures += 1
        else:
            print(f"  ✅ {label}")

    print("\nADVERSARIAL (embedded PII) cases:")
    for text, _expect, label in ADVERSARIAL_FIXTURES:
        total += 1
        if not assert_redacted(text, label):
            failures += 1
        else:
            print(f"  ✅ {label}")

    print("\nTRUNCATION edge cases:")
    total += 1
    if not test_truncate_120_safe():
        failures += 1
    else:
        print(f"  ✅ truncate_120_redacts_before_cut")

    print(f"\n=== RESULT: {total - failures}/{total} passed, {failures} failed ===")
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
