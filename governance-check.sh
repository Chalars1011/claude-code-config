#!/bin/bash
# Governance Check — runs at session end via Stop hook
# 检查文件层面的合规指标（不检查质量，只抓最糟糕的遗漏）
# 质量检查依赖 CLAUDE.md 中的"Session End Self-Check"规则

REPORT_FILE="/c/Users/13040/.claude/governance-report.txt"
TRACKER="/c/Users/13040/.claude/.governance-tracker"
TODAY=$(date '+%Y-%m-%d')
NOW=$(date '+%Y-%m-%d %H:%M')
WARNINGS=0

echo "=== Governance Check $NOW ===" > "$REPORT_FILE"

# --- Check 1: context/progress.md touched today? ---
PROGRESS_FILE="/d/unity_school/2D-Action-Game_Unity6/.claude/context/progress.md"
if [ -f "$PROGRESS_FILE" ]; then
  PROGRESS_DATE=$(stat -c %Y "$PROGRESS_FILE" 2>/dev/null)
  PROGRESS_READABLE=$(date -d @$PROGRESS_DATE '+%Y-%m-%d %H:%M' 2>/dev/null || echo "unknown")
  echo "[context] progress.md: $PROGRESS_READABLE" >> "$REPORT_FILE"
  if [ "$(date -d @$PROGRESS_DATE '+%Y-%m-%d' 2>/dev/null)" != "$TODAY" ]; then
    echo "  ⚠ WARNING: progress.md was NOT updated today" >> "$REPORT_FILE"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  ✅ Updated today" >> "$REPORT_FILE"
  fi
else
  echo "[context] progress.md: FILE NOT FOUND" >> "$REPORT_FILE"
  WARNINGS=$((WARNINGS + 1))
fi

# --- Check 2: Uncommitted changes ---
if [ -d /d/unity_school/2D-Action-Game_Unity6/.git ]; then
  cd /d/unity_school/2D-Action-Game_Unity6
  UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l)
  echo "[git] Uncommitted changes: $UNCOMMITTED files" >> "$REPORT_FILE"
  if [ "$UNCOMMITTED" -gt 10 ]; then
    echo "  ⚠ WARNING: $UNCOMMITTED uncommitted files — consider committing" >> "$REPORT_FILE"
    WARNINGS=$((WARNINGS + 1))
  fi
fi

# --- Check 3: Session tracker ---
if [ -f "$TRACKER" ]; then
  LAST_SESSION=$(head -1 "$TRACKER" 2>/dev/null)
  echo "[tracker] Last session: $LAST_SESSION" >> "$REPORT_FILE"
fi
echo "$NOW" > "$TRACKER"

# --- Summary ---
echo "" >> "$REPORT_FILE"
echo "[summary] Warnings: $WARNINGS | $( [ "$WARNINGS" -eq 0 ] && echo '✅ PASS' || echo '⚠ NEEDS REVIEW' )" >> "$REPORT_FILE"
cat "$REPORT_FILE"
