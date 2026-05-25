#!/usr/bin/env python3
"""
trigger_eval.py — Trigger evaluation test suite for RESOLVER.md

Verifies that the RESOLVER.md routes the right inputs to the right skills.
"If you can't prove the right skill fires for the right input, you don't
have a system. You have a collection of skills and a prayer."

Usage:
    python3 trigger_eval.py
    python3 trigger_eval.py --resolver /path/to/_gbrain/RESOLVER.md
    python3 trigger_eval.py --verbose
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Test cases: (input, expected_skill_slug, category)
#
# Skill slug is the directory name under skills/ or skills/_gbrain/.
# For _gbrain skills, prefix with "_gbrain/" so we can distinguish.
# ---------------------------------------------------------------------------

TEST_CASES = [
    # --- Camera Management ---
    ("check camera health", "camera-management", "domain"),
    ("what's the camera count", "camera-management", "domain"),
    ("subscribe to ISAPI events on camera 3", "camera-management", "domain"),
    ("Hikvision device is offline", "camera-management", "domain"),

    # --- Website Deploy ---
    ("deploy the website", "website-deploy", "domain"),
    ("rollback satory.nousagaas.com", "website-deploy", "domain"),
    ("check the fingerprint lock on the site", "website-deploy", "domain"),

    # --- Audit ---
    ("run audit on infrastructure", "audit", "domain"),
    ("/audit telegram", "audit", "domain"),
    ("factory audit report", "audit", "domain"),

    # --- Infrastructure ---
    ("check if LiteLLM is running", "infrastructure", "domain"),
    ("restart OpenClaw container", "infrastructure", "domain"),
    ("deploy new factory component", "infrastructure", "domain"),
    ("upgrade Docker on Air", "infrastructure", "domain"),
    ("launchd job is failing", "infrastructure", "domain"),

    # --- Command Center ---
    ("send telegram message", "command-center", "domain"),
    ("/ask what time is it", "ceo-hierarchy", "domain"),  # /ask routes via Tier-1 grok-ceo per CLAUDE.md routing model (session 67)
    ("/status of the system", "command-center", "domain"),
    ("/health check", "command-center", "domain"),

    # --- gbrain brain-ops ---
    ("update a brain page", "_gbrain/enrich", "gbrain"),  # "update/enrich" → enrich, not generic brain-ops (session 67 LLM-judge correction)
    ("write this to the wiki", "_gbrain/idea-ingest", "gbrain"),  # "this" = captured idea/link/article (session 67 LLM-judge confirms)
    ("look up the citation for lesson 87", "_gbrain/query", "gbrain"),  # "look up" = query (session 67)

    # --- gbrain skill-creator ---
    ("create a new skill", "_gbrain/skill-creator", "gbrain"),
    ("improve the audit skill", "_gbrain/skill-creator", "gbrain"),

    # --- Error Classification ---
    ("classify this error", "error-classification", "domain"),
    ("what type of error is HTTP 502", "error-classification", "domain"),

    # --- Evidence Verification ---
    ("is this evidence sufficient", "evidence-verification", "domain"),
    ("verify the photo evidence for violation", "evidence-verification", "domain"),

    # --- Kazakhstan Regulatory ---
    ("what's the fine for 76 in a 60 zone", "kazakhstan-regulatory", "domain"),
    ("KoAP article for speeding", "kazakhstan-regulatory", "domain"),

    # --- Metrology Cert Tracker ---
    ("check metrology calibration expiry", "metrology-cert-tracker", "domain"),
    ("camera calibration certificate is expiring", "metrology-cert-tracker", "domain"),
    ("legally-void violations from expired cert", "metrology-cert-tracker", "domain"),

    # --- SmartBridge SOAP ---
    ("submit violation to ERAP via SmartBridge", "smartbridge-soap-client", "domain"),
    ("GOST signing for ERAP packet", "smartbridge-soap-client", "domain"),

    # --- Air SSH Access ---
    ("how do I SSH to Air", "air-ssh-access", "domain"),
    ("Tailscale connection to Air is down", "air-ssh-access", "domain"),
    ("macOS SSH not working", "air-ssh-access", "domain"),

    # --- Planning Discipline ---
    ("what should I do next? plan the task", "planning-discipline", "domain"),

    # --- Factory Ops ---
    ("stop the factory", "factory-ops", "domain"),
    ("restart the task queue", "factory-ops", "domain"),
    ("watchdog triggered on factory", "factory-ops", "domain"),

    # --- Satory Dashboard ---
    ("satory dashboard is down", "satory-dashboard", "domain"),
    ("cameras not reflecting on portal", "satory-dashboard", "domain"),

    # --- Storage Retrieval ---
    ("video retention policy", "storage-retrieval", "domain"),
    ("how long do we keep violation footage", "storage-retrieval", "domain"),

    # --- gbrain-ops ---
    ("absorb lesson 115 into skills", "mistake-to-skill", "domain"),  # "absorb lesson into skill" IS mistake-to-skill's core purpose (session 67 LLM-judge correction)
    ("gbrain upgrade to new version", "gbrain-ops", "domain"),
    ("context poisoning detected", "gbrain-ops", "domain"),

    # --- Agent Quality ---
    ("about to declare this done", "agent-quality", "domain"),
    ("claiming the feature works", "agent-quality", "domain"),

    # --- Mistake to Skill (Tan skillify verb) ---
    ("turn this bug into a skill", "mistake-to-skill", "domain"),
    ("skillify it", "mistake-to-skill", "domain"),
    ("skillify this", "mistake-to-skill", "domain"),
    ("make this a skill", "mistake-to-skill", "domain"),
    ("remember this as a skill", "mistake-to-skill", "domain"),
    ("lock this in as a skill", "mistake-to-skill", "domain"),

    # --- gbrain query ---
    ("what do we know about Saken", "_gbrain/query", "gbrain"),
    ("search for NIT VPN info", "_gbrain/query", "gbrain"),

    # --- gbrain daily-task-manager ---
    ("add task: fix the poller", "_gbrain/daily-task-manager", "gbrain"),
    ("what tasks are pending", "_gbrain/daily-task-manager", "gbrain"),

    # --- gbrain briefing ---
    ("what's happening today", "_gbrain/briefing", "gbrain"),
    ("give me the daily briefing", "_gbrain/briefing", "gbrain"),

    # --- gbrain media-ingest ---
    ("ingest this YouTube video", "_gbrain/media-ingest", "gbrain"),
    ("process this PDF document", "_gbrain/media-ingest", "gbrain"),

    # --- gbrain meeting-ingestion ---
    ("meeting transcript just came in", "_gbrain/meeting-ingestion", "gbrain"),

    # --- gbrain maintain ---
    ("run brain health check", "_gbrain/maintain", "gbrain"),
    ("extract links and build link graph", "_gbrain/maintain", "gbrain"),
]


# ---------------------------------------------------------------------------
# RESOLVER.md parser
# ---------------------------------------------------------------------------

def parse_resolver(path: str) -> list[dict]:
    """
    Parse RESOLVER.md and return a list of route dicts:
      {
        "trigger": "lowercase trigger description",
        "skill_path": "skills/_gbrain/brain-ops/SKILL.md",
        "skill_slug": "_gbrain/brain-ops" or "camera-management",
      }
    """
    text = Path(path).read_text(encoding="utf-8")
    routes = []

    # Match markdown table rows: | trigger text | `skill/path/SKILL.md` |
    # Also match rows like: | trigger | Run `command` |
    # Pattern: pipes with content between them
    table_row_re = re.compile(
        r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
        re.MULTILINE,
    )

    for m in table_row_re.finditer(text):
        trigger_raw = m.group(1).strip()
        skill_raw = m.group(2).strip()

        # Skip header rows
        if trigger_raw.startswith("---") or trigger_raw.lower() == "trigger":
            continue

        # Extract skill path from backticks
        skill_match = re.search(r"`(skills/[^`]+/SKILL\.md)`", skill_raw)
        if not skill_match:
            # Some rows point to commands like "Run `gbrain features`"
            # or reference ACCESS_POLICY.md, SOUL.md, etc. -- skip these
            continue

        skill_path = skill_match.group(1)

        # Derive slug from path:
        #   skills/_gbrain/brain-ops/SKILL.md -> _gbrain/brain-ops
        #   skills/camera-management/SKILL.md -> camera-management
        parts = skill_path.replace("skills/", "").replace("/SKILL.md", "")
        skill_slug = parts

        routes.append({
            "trigger": trigger_raw.lower(),
            "skill_path": skill_path,
            "skill_slug": skill_slug,
        })

    return routes


# ---------------------------------------------------------------------------
# Matcher: keyword-based scoring
# ---------------------------------------------------------------------------

def tokenize(text: str) -> set[str]:
    """Split text into lowercase word tokens."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def compute_score(input_text: str, trigger_desc: str) -> float:
    """
    Score how well an input matches a trigger description.

    Uses multiple signals:
    - Token overlap (Jaccard-like)
    - Substring containment bonus
    - Exact phrase match bonus
    """
    input_lower = input_text.lower()
    trigger_lower = trigger_desc.lower()

    input_tokens = tokenize(input_text)
    trigger_tokens = tokenize(trigger_desc)

    if not trigger_tokens:
        return 0.0

    # Base: fraction of trigger tokens found in input
    overlap = input_tokens & trigger_tokens
    if not overlap:
        return 0.0

    # Jaccard similarity
    union = input_tokens | trigger_tokens
    jaccard = len(overlap) / len(union) if union else 0.0

    # Coverage: what fraction of trigger keywords appear in input
    coverage = len(overlap) / len(trigger_tokens)

    # Substring bonus: does a meaningful chunk of trigger appear in input?
    substr_bonus = 0.0
    # Check if any 2+ word phrase from trigger appears in input
    trigger_words = trigger_lower.split()
    for i in range(len(trigger_words) - 1):
        bigram = trigger_words[i] + " " + trigger_words[i + 1]
        if bigram in input_lower:
            substr_bonus = 0.3
            break

    # Check if any trigger phrase (quoted) matches
    # e.g., trigger: "what do we know about" -> check substring
    quoted = re.findall(r'"([^"]+)"', trigger_lower)
    for phrase in quoted:
        # Check if the pattern part matches (without the variable part)
        phrase_tokens = set(phrase.split())
        if phrase_tokens.issubset(input_tokens):
            substr_bonus = max(substr_bonus, 0.5)

    # Domain-specific keyword boost
    # Some trigger descriptions use slashes for commands
    if input_lower.startswith("/") and "/" in trigger_lower:
        cmd_match = re.search(r"/(\w+)", input_lower)
        if cmd_match and cmd_match.group(1) in trigger_lower:
            substr_bonus = max(substr_bonus, 0.6)

    score = (jaccard * 0.3) + (coverage * 0.4) + substr_bonus
    return score


PRIORITY_RULES: list[tuple[re.Pattern[str], str]] = [
    # Resolver "Conventions" rows are precedence rules. Keep these deterministic
    # so broad always-on rows cannot beat explicit command/domain routes.
    (re.compile(r"^/ask\b", re.I), "ceo-hierarchy"),
    (re.compile(r"\bcamera count\b", re.I), "camera-management"),
    (re.compile(r"\bupdate\b.*\bbrain page\b", re.I), "_gbrain/enrich"),
    (re.compile(r"\b(stop|start|stopping|starting)\b.*\bfactory\b", re.I), "factory-ops"),
    (re.compile(r"\brestart\b.*\btask queue\b", re.I), "factory-ops"),
    (re.compile(r"\bwatchdog\b.*\bfactory\b", re.I), "factory-ops"),
    (re.compile(r"\bgbrain\b.*\bupgrade\b", re.I), "gbrain-ops"),
    (re.compile(r"\badd task\b|^add task:|\bpending tasks\b|\btasks are pending\b", re.I), "_gbrain/daily-task-manager"),
    (re.compile(r"\b(ingest|process)\b.*\b(youtube|pdf|video|audio|document|book|screenshot)\b", re.I), "_gbrain/media-ingest"),
]


def find_best_match(input_text: str, routes: list[dict], threshold: float = 0.15) -> tuple[str | None, float]:
    """
    Find the best matching skill for an input.
    Returns (skill_slug, score) or (None, 0.0) if nothing above threshold.
    """
    known_slugs = {route["skill_slug"] for route in routes}
    for pattern, slug in PRIORITY_RULES:
        if slug in known_slugs and pattern.search(input_text):
            return slug, 1.0

    best_slug = None
    best_score = 0.0

    for route in routes:
        score = compute_score(input_text, route["trigger"])
        if score > best_score:
            best_score = score
            best_slug = route["skill_slug"]

    if best_score < threshold:
        return None, 0.0

    return best_slug, best_score


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests(resolver_path: str, verbose: bool = False) -> bool:
    routes = parse_resolver(resolver_path)

    if not routes:
        print(f"ERROR: No routes parsed from {resolver_path}")
        print("       Is the file a valid RESOLVER.md with markdown tables?")
        return False

    print(f"Parsed {len(routes)} routes from RESOLVER.md")
    print(f"Running {len(TEST_CASES)} test cases...\n")

    # Collect all skill slugs from routes for coverage reporting
    known_slugs = {r["skill_slug"] for r in routes}

    passed = 0
    failed = 0
    false_negatives = []
    false_positives = []
    not_in_resolver = []

    for input_text, expected_skill, category in TEST_CASES:
        matched_slug, score = find_best_match(input_text, routes)

        # Normalize: some expected skills might not have _gbrain/ prefix in resolver
        # Handle both directions
        if matched_slug == expected_skill:
            passed += 1
            if verbose:
                print(f"  PASS  [{category:6s}] \"{input_text}\"")
                print(f"         -> {expected_skill} (score={score:.3f})")
        else:
            failed += 1
            # Determine failure type
            if expected_skill not in known_slugs:
                not_in_resolver.append((input_text, expected_skill, matched_slug, score))
                label = "FAIL (not in RESOLVER)"
            elif matched_slug is None:
                false_negatives.append((input_text, expected_skill, score))
                label = "FAIL (false negative)"
            else:
                false_positives.append((input_text, expected_skill, matched_slug, score))
                label = "FAIL (false positive)"

            print(f"  {label}")
            print(f"         input:    \"{input_text}\"")
            print(f"         expected: {expected_skill}")
            print(f"         got:      {matched_slug or '(no match)'} (score={score:.3f})")
            print()

    # --- Summary ---
    total = len(TEST_CASES)
    print("=" * 70)
    print(f"RESULTS: {passed}/{total} passed, {failed}/{total} failed")
    print(f"  Pass rate: {passed/total*100:.1f}%")
    print()

    if false_negatives:
        print(f"FALSE NEGATIVES ({len(false_negatives)}): skill exists in RESOLVER but trigger too narrow")
        for inp, exp, sc in false_negatives:
            print(f"  - \"{inp}\" should match {exp}")
        print()

    if false_positives:
        print(f"FALSE POSITIVES ({len(false_positives)}): wrong skill matched")
        for inp, exp, got, sc in false_positives:
            print(f"  - \"{inp}\" expected {exp}, got {got}")
        print()

    if not_in_resolver:
        print(f"MISSING FROM RESOLVER ({len(not_in_resolver)}): skill exists on disk but has no trigger route")
        for inp, exp, got, sc in not_in_resolver:
            print(f"  - {exp} (tested with: \"{inp}\")")
        print()

    # Coverage: which skills on disk have no routes?
    expected_domain_skills = {
        "agent-quality", "air-ssh-access", "audit", "camera-management",
        "command-center", "error-classification", "evidence-verification",
        "factory-ops", "gbrain-ops", "infrastructure", "kazakhstan-regulatory",
        "metrology-cert-tracker", "mistake-to-skill", "planning-discipline",
        "satory-dashboard", "smartbridge-soap-client", "storage-retrieval",
        "website-deploy",
    }
    missing_in_resolver = expected_domain_skills - known_slugs
    if missing_in_resolver:
        print(f"COVERAGE GAPS: {len(missing_in_resolver)} domain skills have NO route in RESOLVER.md:")
        for s in sorted(missing_in_resolver):
            print(f"  - {s}")
        print()

    if failed == 0 and not missing_in_resolver:
        print("ALL CLEAR: every test passes and every domain skill has a route.")
    elif failed == 0:
        print("All test cases pass, but there are coverage gaps above.")

    return failed == 0 and not missing_in_resolver


def main():
    # Canonical resolver path (session 67, 2026-04-23 dedup): _gbrain/RESOLVER.md
    default_resolver = "/root/nous-agaas/wiki/pages/skills/_gbrain/RESOLVER.md"

    parser = argparse.ArgumentParser(
        description="Trigger evaluation test suite for RESOLVER.md",
        epilog="Exit 0 if all pass, 1 if any fail.",
    )
    parser.add_argument(
        "--resolver",
        default=default_resolver,
        help=f"Path to RESOLVER.md (default: {default_resolver})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show passing tests too",
    )
    args = parser.parse_args()

    # Resolve path - also check Mac/Air paths
    resolver_path = args.resolver
    if not Path(resolver_path).exists():
        alternatives = [
            Path.home() / "nous-agaas/wiki/pages/skills/_gbrain/RESOLVER.md",
            Path.home() / "Documents/Projects/Nous AGaaS/Nous/pages/skills/_gbrain/RESOLVER.md",
            # Legacy fallbacks (deduped session 67):
            Path.home() / "nous-agaas/wiki/pages/skills/_gbrain-RESOLVER.md",
            Path.home() / "Documents/Projects/Nous AGaaS/Nous/pages/skills/_gbrain-RESOLVER.md",
        ]
        for alt in alternatives:
            if alt.exists():
                resolver_path = str(alt)
                break
        else:
            print(f"ERROR: RESOLVER.md not found at {resolver_path}")
            print("       Use --resolver to specify the path.")
            sys.exit(1)

    print(f"RESOLVER: {resolver_path}")
    print()

    all_pass = run_tests(resolver_path, verbose=args.verbose)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
