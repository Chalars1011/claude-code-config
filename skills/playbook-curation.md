> 创建: 2026-07-25 | 更新: 2026-07-25 | 类型: 版本敏感规则

# playbook-curation
## Trigger: bug took 3+ fix attempts OR involved trying a fundamentally different approach

## Process
1. Ask user: "Worth saving to playbook for future projects?"
2. If yes → write a new playbook entry with:
   - What was tried (in order)
   - Why each attempt failed
   - What finally worked
   - Source attribution if any
3. Naming convention: `{topic}-{key-insight}.md` (e.g. `crouch-subsm-oscillation.md`)
4. Update `~/.claude/playbook/index.md` with new entry
