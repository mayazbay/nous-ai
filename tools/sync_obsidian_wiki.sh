#!/bin/bash
# Sync wiki/ (agent source of truth) -> obsidian-wiki/wiki/ (Madi Obsidian app)
# NEVER delete .obsidian folder — Obsidian app needs it

# Step 1: Sync files from wiki/ to obsidian-wiki/wiki/
rsync -av --delete \
    --exclude .git \
    /root/nous-agaas/wiki/ \
    /root/nous-agaas/obsidian-wiki/wiki/ \
    > /dev/null 2>&1

# Step 2: Commit changes to obsidian-wiki git repo
cd /root/nous-agaas/obsidian-wiki || exit 1
git add -A > /dev/null 2>&1
git diff --cached --quiet || git commit -m "Auto-sync from wiki/ $(date +%Y-%m-%d_%H:%M)" > /dev/null 2>&1

# Step 3: Report
PAGE_COUNT=$(find wiki -name "*.md" -not -path "./.git/*" | wc -l)
echo "[$(date "+%Y-%m-%d %H:%M")] Obsidian wiki synced: ${PAGE_COUNT} pages"
