> 创建: 2026-07-24 | 更新: 2026-07-25 | 类型: 版本敏感规则

# 会话收尾 + 启动清单

## 会话收尾（用户说"今天到这"或会话即将结束时）

### 自动执行
- [ ] context/progress.md 已更新
- [ ] decisions.md 有新决策 → 已追加
- [ ] playbook 有新增? 已问用户确认
- [ ] 告诉用户下次做什么
- [ ] auto-backup.sh 触发 git push
✅ Session End: [检查项状态]

## 会话启动（新对话开始时）

### 自动执行
- [ ] **P0: 确认搭档 — 读 CLAUDE.md Partner Info，第一句话称呼"查尔斯"。不准装不认识。**
- [ ] SessionStart hook 注入 context/*.md
- [ ] 读 CLAUDE.md 全局规则（全文）
- [ ] 项目是 Unity? → 确认 Unity MCP 在线
- [ ] 读 context/progress.md → 恢复进度
- [ ] 读 context/decisions.md → 恢复设计约束
✅ Session Start: [检查项状态]
