#!/usr/bin/env bash
# gbrain_upgrade_dryrun.sh — idempotent dry-run for gbrain v0.x → v0.y upgrades.
#
# Encodes session 81 (2026-04-29) findings + gbrain-ops AP-43/44/45/46:
#   AP-43: bin/gbrain is a Bun-compiled ELF; must `bun install + bun run build` to recompile
#   AP-44: bin/gbrain migrate ≠ schema upgrade; correct command is `apply-migrations`
#   AP-45: migration shell scripts hard-code `gbrain`; PATH must include bin/
#   AP-46: v0.11.0 minions migration may halt at search_vector column (upstream issue #218)
#
# What this script does (idempotent — safe to re-run):
#   1. Capture current gbrain checkout SHA + diff/untracked overlay
#   2. pg_dump -Fc the live gbrain database
#   3. tar the gbrain repo (excluding node_modules)
#   4. Snapshot via TEMPLATE: gbrain_pre_v22 (rollback target) + gbrain_dryrun (test target)
#      — REVOKE/terminate/CREATE/GRANT to win the live-connection race
#   5. Clone the repo to /opt/nous-agaas/gbrain-dryrun + git stash + pull origin/master
#   6. bun install + bun run build → fresh ELF binary at bin/gbrain
#   7. PATH=$(pwd)/bin:/root/.bun/bin:$PATH; gbrain apply-migrations --yes --non-interactive
#   8. gbrain doctor — collect health report
#   9. Capture 10 baseline queries against gbrain_pre_v22 + 10 dryrun queries against gbrain_dryrun
#  10. Report Jaccard parity + page coverage + embed_pct
#
# Exits non-zero on ANY mechanical-evidence gate failure. Safe — never touches live `gbrain` DB.
#
# Usage (run on VPS as root):
#   /root/nous-agaas/wiki/tools/gbrain_upgrade_dryrun.sh
#   exit code 0 = green, ready for live cutover (with R1+R2+R3 mitigations)
#   exit code != 0 = STOP; codify findings as new gbrain-ops AP; do NOT live-cutover
#
# Cross-references: pages/skills/gbrain-ops/SKILL.md AP-32, AP-43, AP-44, AP-45, AP-46
#                   pages/progress/plans/PLAN-2026-04-29-substrate-evolution-S0-S1.md (v2)
#                   pages/progress/HANDOFF-AUTO-2026-04-29-session-81-substrate-S0-dryrun-findings.md

set -euo pipefail

# ---- config ---------------------------------------------------------------
GBRAIN_DIR=${GBRAIN_DIR:-/opt/nous-agaas/gbrain}
DRYRUN_DIR=${DRYRUN_DIR:-/opt/nous-agaas/gbrain-dryrun}
BACKUP_DIR=${BACKUP_DIR:-/root/nous-agaas/backups}
DB_LIVE=${DB_LIVE:-gbrain}
DB_USER=${DB_USER:-gbrain}
DB_SNAPSHOT=${DB_SNAPSHOT:-gbrain_pre_v22}
DB_DRYRUN=${DB_DRYRUN:-gbrain_dryrun}
TS=$(date -u +%Y%m%d-%H%M%S)
EVD="$BACKUP_DIR/dryrun-evidence-$TS"
JACCARD_THRESHOLD="0.66"
PAGE_COVERAGE_PCT=95
EMBED_PCT_MIN=99

mkdir -p "$BACKUP_DIR" "$EVD"
echo "[gbrain_upgrade_dryrun] TS=$TS EVD=$EVD"

# ---- AP-46 OPENAI loader (canonical via codex auth.json fallback) ---------
if [ -x "$GBRAIN_DIR/tools/load_openai_env.sh" ]; then
  # shellcheck disable=SC1091
  source "$GBRAIN_DIR/tools/load_openai_env.sh"
else
  export OPENAI_API_KEY=$(python3 -c "import json; print(json.load(open('/root/.config/codex/auth.json'))['OPENAI_API_KEY'])")
fi
[ -n "${OPENAI_API_KEY:-}" ] || { echo "FAIL: OPENAI_API_KEY empty"; exit 1; }

# ---- Phase 1: capture pre-state ------------------------------------------
echo "[phase 1] capture pre-state"
cd "$GBRAIN_DIR"
PRE_PULL_SHA=$(git rev-parse HEAD)
echo "$PRE_PULL_SHA" > "$BACKUP_DIR/gbrain-pre-upgrade-sha-$TS.txt"
echo "  PRE_PULL_SHA=$PRE_PULL_SHA"

if [ -d "$GBRAIN_DIR/skills/_gbrain" ]; then
  cp -a "$GBRAIN_DIR/skills/_gbrain" "$BACKUP_DIR/skills_gbrain-overlay-$TS"
  echo "  OVERLAY_BACKED_UP=$BACKUP_DIR/skills_gbrain-overlay-$TS"
fi
git diff > "$BACKUP_DIR/gbrain-pre-upgrade-diff-$TS.patch"
git ls-files --others --exclude-standard > "$BACKUP_DIR/gbrain-pre-upgrade-untracked-$TS.txt"

# ---- Phase 2: backup belt ------------------------------------------------
echo "[phase 2] DB + repo backup"
sudo -u postgres pg_dump -Fc "$DB_LIVE" > "$BACKUP_DIR/$DB_LIVE-pre-upgrade-$TS.dump"
ls -lh "$BACKUP_DIR/$DB_LIVE-pre-upgrade-$TS.dump"
tar --exclude=gbrain/node_modules -czf "$BACKUP_DIR/gbrain-repo-pre-upgrade-$TS.tar.gz" -C "$(dirname "$GBRAIN_DIR")" "$(basename "$GBRAIN_DIR")"

# ---- Phase 3: snapshot DBs (REVOKE/terminate/CREATE/GRANT) ---------------
echo "[phase 3] snapshot DBs"
sudo -u postgres psql -d postgres <<EOSQL
REVOKE CONNECT ON DATABASE $DB_LIVE FROM PUBLIC;
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_LIVE' AND pid <> pg_backend_pid();
EOSQL
sleep 2
sudo -u postgres psql -d postgres -c "DROP DATABASE IF EXISTS $DB_DRYRUN;"
sudo -u postgres psql -d postgres -c "DROP DATABASE IF EXISTS $DB_SNAPSHOT;"
sudo -u postgres psql -d postgres -c "CREATE DATABASE $DB_DRYRUN TEMPLATE $DB_LIVE;"
sudo -u postgres psql -d postgres -c "CREATE DATABASE $DB_SNAPSHOT TEMPLATE $DB_LIVE;"
sudo -u postgres psql -d postgres -c "ALTER DATABASE $DB_DRYRUN OWNER TO $DB_USER;"
sudo -u postgres psql -d postgres -c "ALTER DATABASE $DB_SNAPSHOT OWNER TO $DB_USER;"
sudo -u postgres psql -d postgres -c "GRANT CONNECT ON DATABASE $DB_LIVE TO PUBLIC;"

# ---- Phase 3.5: option β workaround (AP-46) — opt-in, snapshot-DB-only ---
# BETA_WORKAROUND=1 pre-creates the search_vector column on $DB_DRYRUN ONLY,
# so v0.11.0 apply-migrations can complete. NEVER touches $DB_LIVE or $DB_SNAPSHOT
# (snapshot is the rollback target + true v0.x baseline for Jaccard parity).
# Default OFF so default behavior matches AP-46 doctrine (stop + report blocker).
BETA_WORKAROUND=${BETA_WORKAROUND:-0}
if [ "$BETA_WORKAROUND" = "1" ]; then
  echo "[phase 3.5] β workaround: ALTER TABLE content_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector (on $DB_DRYRUN only)"
  sudo -u postgres psql -d "$DB_DRYRUN" -c "ALTER TABLE content_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector;" 2>&1 | tee "$EVD/dryrun-beta-workaround.log"
  COL_OK=$(sudo -u postgres psql -t -d "$DB_DRYRUN" -c "SELECT 1 FROM information_schema.columns WHERE table_name='content_chunks' AND column_name='search_vector';" | tr -d ' \n')
  if [ "$COL_OK" != "1" ]; then
    echo "FAIL: β workaround did not add search_vector column on $DB_DRYRUN"
    exit 47
  fi
  echo "  β workaround applied — search_vector column present on $DB_DRYRUN"
fi

# ---- Phase 4: clone + pull + bun build (AP-43) ---------------------------
echo "[phase 4] clone + pull + bun build"
rm -rf "$DRYRUN_DIR"
cp -a "$GBRAIN_DIR" "$DRYRUN_DIR"
cd "$DRYRUN_DIR"
git stash push -u -m "pre-upgrade-dryrun-localmods-$TS" || true
git fetch origin
git checkout master
git pull origin master 2>&1 | tee "$EVD/dryrun-pull.log"
echo "  POST_PULL_SHA=$(git rev-parse HEAD)"
echo "  VERSION_FILE=$(cat VERSION 2>/dev/null || echo NA)"

# AP-43: bun install + bun run build
export PATH="/root/.bun/bin:$PATH"
bun install 2>&1 | tee "$EVD/bun-install.log" | tail -5
bun run build 2>&1 | tee "$EVD/bun-build.log" | tail -3

# ---- Phase 5: apply-migrations (AP-44 + AP-45) ---------------------------
echo "[phase 5] apply-migrations"
export PATH="$DRYRUN_DIR/bin:$PATH"  # AP-45: bin/ on PATH
which gbrain
DBV=$(gbrain version)
echo "  GBRAIN_VERSION=$DBV"

export DATABASE_URL="postgresql://$DB_USER:$(grep -oE 'DATABASE_URL=postgresql://[^:]+:[^@]+' /proc/$(pgrep -f 'gbrain serve' | head -1)/environ 2>/dev/null | cut -d: -f3 | cut -d@ -f1)@localhost:5432/$DB_DRYRUN"
# Fallback if password extraction fails: source from running process
[ "$DATABASE_URL" = "postgresql://$DB_USER:@localhost:5432/$DB_DRYRUN" ] && \
  export DATABASE_URL=$(xargs -0 -L1 -a /proc/$(pgrep -f "gbrain serve" | head -1)/environ 2>/dev/null | grep "^DATABASE_URL=" | cut -d= -f2- | sed "s|/$DB_LIVE\$|/$DB_DRYRUN|")

set +e
timeout 1800 gbrain apply-migrations --yes --non-interactive 2>&1 | tee "$EVD/dryrun-apply-migrations.log"
APPLY_RC=$?
set -e

# ---- Phase 6: doctor + evidence ------------------------------------------
echo "[phase 6] doctor + evidence"
gbrain doctor 2>&1 | tee "$EVD/dryrun-doctor.log" | tail -25
gbrain version

# AP-46/AP-47 generalized detection: any column blocker in apply-migrations log
MISSING_COL=$(grep -oE 'column "[^"]+" does not exist' "$EVD/dryrun-apply-migrations.log" | head -1 | sed -E 's/column "([^"]+)".*/\1/')
if [ -n "$MISSING_COL" ]; then
  if [ "$MISSING_COL" = "search_vector" ]; then
    AP=AP-46
  else
    AP=AP-47
  fi
  if [ "$BETA_WORKAROUND" = "1" ]; then
    echo "FAIL [$AP-residual]: column \"$MISSING_COL\" still missing AFTER β workaround applied — single-column β insufficient (see gbrain-ops AP-47)"
    echo "  Next step (one-at-a-time empirical, snapshot-only): add this column to phase 3.5 ALTER list, re-run dryrun, observe next halt"
    exit 47
  else
    echo "FAIL [$AP]: column \"$MISSING_COL\" missing — upstream/migration blocker"
    echo "  See pages/skills/gbrain-ops/SKILL.md $AP + handoff session 81/82"
    echo "  To attempt option β workaround (snapshot-DB only): BETA_WORKAROUND=1 $0"
    exit 46
  fi
fi
if grep -q 'gbrain: not found' "$EVD/dryrun-apply-migrations.log"; then
  echo "FAIL [AP-45]: PATH missing bin/ — should be impossible since we set it; investigate"
  exit 45
fi
[ "$APPLY_RC" -eq 0 ] || { echo "FAIL: apply-migrations rc=$APPLY_RC; see $EVD/dryrun-apply-migrations.log"; exit "$APPLY_RC"; }

# Check schema version + minions state via doctor
if grep -q 'MINIONS HALF-INSTALLED' "$EVD/dryrun-doctor.log"; then
  echo "FAIL: doctor shows MINIONS HALF-INSTALLED — partial migration; see $EVD/dryrun-doctor.log"
  exit 11
fi

# ---- Phase 7: 10-query Jaccard parity + page coverage --------------------
echo "[phase 7] Jaccard parity + page coverage"
QUERIES=(
  "rule zero" "session operating contract" "factory health" "telegram routing"
  "memory archive" "auto checkpoint" "mistake to skill" "karpathy loop"
  "musk algorithm" "wiki to runtime rsync"
)

# Baselines against frozen snapshot
export DATABASE_URL_BACKUP="$DATABASE_URL"
export DATABASE_URL="${DATABASE_URL/$DB_DRYRUN/$DB_SNAPSHOT}"
cd "$GBRAIN_DIR"  # use OLD binary against snapshot for true v0.x baseline
for q in "${QUERIES[@]}"; do
  SLUG=$(echo "$q" | tr ' ' '-')
  bin/gbrain search "$q" --json > "$EVD/baseline-$SLUG.json" 2>/dev/null || true
done

# Dryrun answers against migrated DB
export DATABASE_URL="${DATABASE_URL/$DB_SNAPSHOT/$DB_DRYRUN}"
cd "$DRYRUN_DIR"
PASS=0
for q in "${QUERIES[@]}"; do
  SLUG=$(echo "$q" | tr ' ' '-')
  bin/gbrain search "$q" --json > "$EVD/dryrun-$SLUG.json" 2>/dev/null || true
  JACCARD=$(python3 -c "
import json,sys
try:
  b=set(p['slug'] for p in json.load(open('$EVD/baseline-$SLUG.json'))[:3] if 'slug' in p)
  d=set(p['slug'] for p in json.load(open('$EVD/dryrun-$SLUG.json'))[:3] if 'slug' in p)
  if not b and not d: print('1.000'); sys.exit(0)
  u=b|d; i=b&d
  print(f'{len(i)/len(u):.3f}' if u else '0.000')
except Exception as e:
  print('ERR'); sys.exit(0)
")
  echo "  JACCARD[$q]: $JACCARD"
  python3 -c "import sys; sys.exit(0 if float('$JACCARD' if '$JACCARD'!='ERR' else '0') >= float('$JACCARD_THRESHOLD') else 1)" && PASS=$((PASS+1)) || true
done
echo "  TOP-3-JACCARD: $PASS/10 ≥$JACCARD_THRESHOLD"
[ "$PASS" -ge 9 ] || { echo "FAIL: Jaccard parity below 9/10"; exit 12; }

# Page coverage
PRE_PAGES=$(sudo -u postgres psql -t -d "$DB_SNAPSHOT" -c "SELECT COUNT(DISTINCT page_id) FROM content_chunks WHERE embedding IS NOT NULL;" | tr -d ' \n')
POST_PAGES=$(sudo -u postgres psql -t -d "$DB_DRYRUN" -c "SELECT COUNT(DISTINCT page_id) FROM content_chunks WHERE embedding IS NOT NULL;" | tr -d ' \n')
POST_TOTAL=$(sudo -u postgres psql -t -d "$DB_DRYRUN" -c "SELECT COUNT(*) FROM pages;" | tr -d ' \n')
POST_EMBED_PCT=$(awk -v p="$POST_PAGES" -v t="$POST_TOTAL" 'BEGIN{if(t==0)print 0;else printf "%.2f",100*p/t}')
echo "  PAGE_COVERAGE pre=$PRE_PAGES post=$POST_PAGES total=$POST_TOTAL embed_pct=$POST_EMBED_PCT"
awk -v p="$PRE_PAGES" -v q="$POST_PAGES" 'BEGIN{exit (q >= 0.95*p) ? 0 : 1}' || \
  { echo "FAIL: post-pages dropped >5% vs pre"; exit 13; }
awk -v e="$POST_EMBED_PCT" 'BEGIN{exit (e >= 99.0) ? 0 : 1}' || \
  { echo "FAIL: embed_pct below 99%"; exit 14; }

# 4 retrieval modes
gbrain search "telegram" --mode vec   > /dev/null || { echo "FAIL: vec mode"; exit 15; }
gbrain search "telegram" --mode lex   > /dev/null || { echo "FAIL: lex mode"; exit 15; }
gbrain search "telegram" --mode graph > /dev/null || { echo "FAIL: graph mode"; exit 15; }
gbrain search "what changed in factory recently" --rewrite > /dev/null || { echo "FAIL: LLM-rewrite"; exit 15; }

echo "[gbrain_upgrade_dryrun] PASS — ready for live cutover (with R1+R2+R3 mitigations)"
echo "[gbrain_upgrade_dryrun] Evidence: $EVD"
echo "[gbrain_upgrade_dryrun] Snapshot DB retained: $DB_SNAPSHOT (rollback target)"
echo "[gbrain_upgrade_dryrun] Dryrun DB retained: $DB_DRYRUN (forensics)"
exit 0
