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

## 推送安全（任何 git push 前，P0 级）

> 2026-08-06 事件：DeepSeek key 曾随公开 GitHub 仓库泄露，7/27 起被盗刷 40+ 元。
> 根因：~/.claude 配置仓设为 public，settings.json（含 key）被提交。

### 硬性检查
- [ ] **仓库必须是 private**（新建仓库默认 private，public 需双确认）
- [ ] 敏感文件不在提交范围：settings.json / vision/config.json / .env / *.jsonl / backups/ / file-history/ / sessions/ / shell-snapshots/
- [ ] 不向任何外部工具（代码粘贴、AI 对话、群聊）发送 key 明文
- [ ] 全局 pre-push hook 已装（`git config --global core.hooksPath` = C:/Users/13040/.git-hooks）——命中自动拦截，逃生舱仅限确认安全后 `--no-verify`
- [ ] 密钥一旦进过公开渠道 → 立即吊销重建，只删文件不算完

## 会话启动（新对话开始时）

### 自动执行
- [ ] **P0: 确认搭档 — 读 CLAUDE.md Partner Info，第一句话称呼"查尔斯"。不准装不认识。**
- [ ] SessionStart hook 注入 context/*.md
- [ ] 读 CLAUDE.md 全局规则（全文）
- [ ] 项目是 Unity? → 确认 Unity MCP 在线
- [ ] 读 context/progress.md → 恢复进度
- [ ] 读 context/decisions.md → 恢复设计约束
✅ Session Start: [检查项状态]
