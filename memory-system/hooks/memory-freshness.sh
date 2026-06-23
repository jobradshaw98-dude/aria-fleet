#!/bin/bash
# UserPromptSubmit hook: nudge if memory audit log is stale.
# Uses memory_audit_log.json mtime (written by /memory-audit Step 9) as the
# "last audit" signal — more accurate than MEMORY.md mtime which updates
# on every memory edit, not on every audit.
#
# Threshold: 7 days (matches supervisor's weekly audit cadence per skill Step 11).
# Silent when fresh or when log is missing (first-time users).
# Safe to fail — exits 0 regardless.

LOG="$HOME/projects/aria-core/data/memory_audit_log.json"
[ -f "$LOG" ] || exit 0

MTIME=$(python -c "import os,sys; sys.stdout.write(str(int(os.path.getmtime(sys.argv[1]))))" "$LOG" 2>/dev/null)
[ -n "$MTIME" ] || exit 0

NOW=$(date +%s)
AGE_DAYS=$(( (NOW - MTIME) / 86400 ))

if [ "$AGE_DAYS" -ge 7 ]; then
  echo "[memory-freshness] Memory audit log ${AGE_DAYS} days old — consider running /memory-audit to catch stale entries."
fi
exit 0
