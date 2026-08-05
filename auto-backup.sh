#!/bin/bash
cd "$HOME/.claude" || exit 1
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add CLAUDE.md playbook/ rules/ skills/ agents/ .mcp.json settings.json mcp-memory.json governance-check.sh *.md
  git commit -m "auto-backup: $(date '+%Y-%m-%d %H:%M')"
  git push --quiet
  echo "✅ ~/.claude/ backed up to GitHub"
else
  echo "⏭  ~/.claude/ no changes"
fi
