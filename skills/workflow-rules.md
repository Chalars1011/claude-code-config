> 创建: 2026-07-25 | 更新: 2026-07-25 | 类型: 版本敏感规则

# workflow-rules
## Trigger: new feature, bug fix, or refactor task

## Reference: ~/.claude/rules/
The following 4 SOP files define mandatory step-by-step workflows:

| Rule File | Use When |
|-----------|---------|
| `~/.claude/rules/01-new-feature.md` | Creating new system/feature/enemy |
| `~/.claude/rules/02-bug-fix.md` | User reports a bug |
| `~/.claude/rules/03-refactor.md` | Replacing existing system (6 phases, HIGHEST priority) |
| `~/.claude/rules/04-session-checklist.md` | Session startup + shutdown |

## Execution Rule
When task matches a rule → read the corresponding file → follow every step → output ✅ checkpoint at each step.
03-refactor.md takes priority over all other workflows.
