#!/bin/bash
# Ingest + export + sync, run every 15 min via cron.
set -e
cd ~/amit-derivatives-monitor
source venv/bin/activate

echo "=== $(date -u) ===" >> cron.log
python3 ingest.py >> cron.log 2>&1 || echo "ingest failed, exporting last-known data" >> cron.log
python3 export.py >> cron.log 2>&1

git add data/latest_snapshot.json cron.log
git commit -q -m "Snapshot: $(date -u +%Y-%m-%dT%H:%M)" || echo "nothing to commit" >> cron.log
git push -q origin main >> cron.log 2>&1 || echo "monitor repo push failed" >> cron.log

DASH=~/amit-quant-system/dashboard-repo
if [ -d "$DASH" ]; then
  cd "$DASH"
  git pull -q origin main >> ~/amit-derivatives-monitor/cron.log 2>&1 || echo "dashboard pull failed" >> ~/amit-derivatives-monitor/cron.log
  mkdir -p site/content/derivatives
  cp ~/amit-derivatives-monitor/data/latest_snapshot.json site/content/derivatives/latest_snapshot.json
  git add site/content/derivatives/latest_snapshot.json
  git commit -q -m "Sync derivatives snapshot: $(date -u +%Y-%m-%dT%H:%M)" || echo "dashboard: nothing to sync" >> ~/amit-derivatives-monitor/cron.log
  git push -q origin main >> ~/amit-derivatives-monitor/cron.log 2>&1 || echo "dashboard push failed" >> ~/amit-derivatives-monitor/cron.log
fi
