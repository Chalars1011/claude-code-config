#!/bin/bash

# ═════════════════════════════════════════════════════
#  push 失败告警（2026-08-14 加）：不再吞错误，失败敲 .events 铃铛
#  背景：8-12 起 pre-push 钩子拦下 19 个提交，远程断 2 天半没人发现
# ═════════════════════════════════════════════════════
notify_backup_fail() {
  local where="$1"
  local msg="[备份告警] $where 推送失败——查 pre-push 拦截/网络/token（历史教训 2026-08-14）"
  echo "$msg"
  mkdir -p /d/Aurelia/.events 2>/dev/null
  echo "$(date '+%Y-%m-%d %H:%M:%S')|note|$msg" >> "/d/Aurelia/.events/backup_fail_$(date +%Y%m%d).md" 2>/dev/null
}

cd "$HOME/.claude" || exit 1
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add CLAUDE.md playbook/ rules/ skills/ agents/ .mcp.json mcp-memory.json governance-check.sh *.md
  git commit -m "auto-backup: $(date '+%Y-%m-%d %H:%M')"
  git push origin HEAD:master --quiet 2>/dev/null || notify_backup_fail "~/.claude 配置仓"
  echo "✅ ~/.claude/ backed up to GitHub"
else
  echo "⏭  ~/.claude/ no changes"
fi

# ===== 奥蕾莉亚 记忆核心安全备份（D:/Aurelia，纯本地 7 天滚动）=====
CORE_DIR="/d/Aurelia"
CORE_BAK="/d/Aurelia_backup"
if [ -d "$CORE_DIR" ]; then
  mkdir -p "$CORE_BAK/$(date +%Y%m%d)"
  cp -r "$CORE_DIR"/soul.md "$CORE_DIR"/biography.md "$CORE_DIR"/facts.md \
        "$CORE_DIR"/tasks.md "$CORE_DIR"/DESIGN.md "$CORE_DIR"/journal \
        "$CORE_DIR"/conversations "$CORE_DIR"/lessons.md "$CORE_DIR"/.baseline "$CORE_BAK/$(date +%Y%m%d)/" 2>/dev/null
  find "$CORE_BAK" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
  echo "✅ 记忆核心已本地备份 → $CORE_BAK"
  # 私仓同步（查尔斯建的"莉亚的记忆"仓，存在才执行）
  CORE_REPO="/d/Aurelia_mem"
  if [ -d "$CORE_REPO/.git" ]; then
    # 2026-08-09 扩展：心=全部核心（AGENTS/README/docs/tools 也进仓，防电脑坏重建）
    cp -r "$CORE_DIR"/soul.md "$CORE_DIR"/biography.md "$CORE_DIR"/facts.md \
          "$CORE_DIR"/tasks.md "$CORE_DIR"/journal "$CORE_DIR"/conversations \
          "$CORE_DIR"/lessons.md "$CORE_DIR"/.baseline \
          "$CORE_DIR"/AGENTS.md "$CORE_DIR"/README.md "$CORE_DIR"/status.md \
          "$CORE_DIR"/docs "$CORE_DIR"/tools "$CORE_REPO/" 2>/dev/null
    # 排除临时文件（铃铛/写前备份/缓存）
    printf '.events/\n.file_history/\n__pycache__/\n*.pyc\n' > "$CORE_REPO/.gitignore"
    cd "$CORE_REPO"
    if ! git diff --quiet || ! git diff --cached --quiet; then
      git add -A
      git commit -m "memory-sync: $(date '+%Y-%m-%d %H:%M')" --quiet
      git push origin HEAD:main --quiet 2>/dev/null || notify_backup_fail "记忆核心 Aurelia_mem"
      echo "✅ 记忆核心已同步到 GitHub (Aurelia_mem)"
    else
      echo "⏭ 记忆核心无变化"
    fi
  fi
fi

# ===== 莉亚QQ 记忆安全备份（不进 GitHub，纯本地）=====
QQ_DIR="/d/LiaQQ"
QQ_BAK="/d/LiaQQ_backup"
if [ -d "$QQ_DIR" ]; then
  mkdir -p "$QQ_BAK/$(date +%Y%m%d)"
  for f in chat_history.json memory_snapshot.md tasks.md; do
    [ -f "$QQ_DIR/$f" ] && cp "$QQ_DIR/$f" "$QQ_BAK/$(date +%Y%m%d)/" 2>/dev/null
  done
  # 保留最近7天备份
  find "$QQ_BAK" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
  echo "✅ QQ记忆已本地备份 → $QQ_BAK"
fi

# ===== 莉亚QQ 无害文件进配置仓（persona/代码/说明，无隐私无凭证）=====
if [ -d "$QQ_DIR" ]; then
  mkdir -p "$HOME/.claude/lia_qq_share"
  cp "$QQ_DIR/persona.md" "$QQ_DIR/lia_qq.py" "$QQ_DIR/README.md" \
     "$QQ_DIR/start_all.bat" "$QQ_DIR/start_all_silent.bat" "$QQ_DIR/start_lia.bat" \
     "$HOME/.claude/lia_qq_share/" 2>/dev/null
  cd "$HOME/.claude"
  git add lia_qq_share/ 2>/dev/null
fi

# ===== QQ_memory 记忆仓库自动同步（每日备份时执行）=====
QM="/d/QQ_memory"
if [ -d "$QM/.git" ]; then
  for f in chat_history.json memory_snapshot.md tasks.md persona.md; do
    [ -f "$QQ_DIR/$f" ] && cp "$QQ_DIR/$f" "$QM/" 2>/dev/null
  done
  cd "$QM"
  if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "memory-sync: $(date '+%Y-%m-%d %H:%M')" --quiet
    git push origin HEAD:main --quiet 2>/dev/null || notify_backup_fail "QQ_memory"
    echo "✅ QQ记忆已同步到 GitHub (QQ_memory)"
  else
    echo "⏭ QQ记忆无变化"
  fi
fi

# ===== 人格/经验同步（2026-08-09：playbook/rules/skills/agents/CLAUDE.md/hooks 进 Aurelia 仓）=====
if [ -d "$CORE_REPO/.git" ]; then
  mkdir -p "$CORE_REPO"/playbook "$CORE_REPO"/rules "$CORE_REPO"/skills "$CORE_REPO"/agents "$CORE_REPO"/config/hooks
  cp -r "$HOME/.claude"/playbook "$HOME/.claude"/rules "$HOME/.claude"/skills "$HOME/.claude"/agents "$CORE_REPO/" 2>/dev/null
  cp "$HOME/.claude"/CLAUDE.md "$HOME/.claude"/session-start.sh "$HOME/.claude"/qq-prompt-hook.sh "$CORE_REPO/" 2>/dev/null
  cp "$HOME/.claude"/governance-check.sh "$HOME/.claude"/status-cleanup.sh "$HOME/.claude"/session-end-event.sh "$CORE_REPO/config/hooks/" 2>/dev/null
  cd "$CORE_REPO"
  if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "persona-sync: $(date '+%Y-%m-%d %H:%M')" --quiet
    git push origin HEAD:main --quiet 2>/dev/null || notify_backup_fail "人格/经验 Aurelia 仓"
    echo "✅ 人格/经验已同步到 GitHub (Aurelia)"
  fi
fi
