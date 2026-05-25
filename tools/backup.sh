#!/bin/bash
# Nous AI — Daily Backup Script
# Backs up all databases and configs, keeps 30 days of history

BACKUP_DIR="$HOME/nous-ai-backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

echo "═══ NOUS AI — Backup ═══"
echo "Target: $BACKUP_DIR"
echo ""

# Backup iMac mission control database
echo "📦 Mission Control DB..."
ssh madia@192.168.1.30 "cp ~/nous-ai-main/mission_control.db /tmp/mc_backup.db 2>/dev/null" 2>/dev/null
scp madia@192.168.1.30:/tmp/mc_backup.db "$BACKUP_DIR/mission_control.db" 2>/dev/null && echo "  ✅ mission_control.db" || echo "  ⚠️ mission_control.db skipped"

# Backup iMac alpha trading database
echo "📦 Alpha Trading DB..."
ssh madia@192.168.1.30 "cp ~/alpha/data/trading.db /tmp/alpha_backup.db 2>/dev/null" 2>/dev/null
scp madia@192.168.1.30:/tmp/alpha_backup.db "$BACKUP_DIR/alpha_trading.db" 2>/dev/null && echo "  ✅ alpha_trading.db" || echo "  ⚠️ alpha_trading.db skipped"

# Backup VMS database
echo "📦 VMS DB..."
ssh madia@192.168.1.30 "cp ~/nous-vms/nous_vms.db /tmp/vms_backup.db 2>/dev/null" 2>/dev/null
scp madia@192.168.1.30:/tmp/vms_backup.db "$BACKUP_DIR/nous_vms.db" 2>/dev/null && echo "  ✅ nous_vms.db" || echo "  ⚠️ nous_vms.db skipped"

# Backup .env (sensitive — chmod 600)
echo "📦 Environment config..."
cp "$HOME/Desktop/nous ai/.env" "$BACKUP_DIR/env_backup" 2>/dev/null && chmod 600 "$BACKUP_DIR/env_backup" && echo "  ✅ .env" || echo "  ⚠️ .env skipped"

# Backup mission_control.py (the main codebase)
echo "📦 Source code snapshot..."
cp "$HOME/Desktop/nous ai/mission_control.py" "$BACKUP_DIR/mission_control.py" 2>/dev/null && echo "  ✅ mission_control.py" || echo "  ⚠️ mission_control.py skipped"

# Keep only last 30 days of backups
echo ""
echo "🧹 Cleaning old backups (>30 days)..."
DELETED=$(find "$HOME/nous-ai-backups" -maxdepth 1 -type d -mtime +30 2>/dev/null | wc -l | tr -d ' ')
find "$HOME/nous-ai-backups" -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null
echo "  Removed $DELETED old backups"

echo ""
echo "═══ BACKUP COMPLETE ═══"
ls -lh "$BACKUP_DIR" 2>/dev/null
echo ""
TOTAL=$(du -sh "$HOME/nous-ai-backups" 2>/dev/null | cut -f1)
echo "Total backup storage: $TOTAL"
