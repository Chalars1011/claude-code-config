> 创建: 2026-07-25 | 更新: 2026-07-25 | 类型: 版本敏感规则

# coding-standards
## Trigger: writing, editing, or refactoring code

## Rules
- Read old code before modifying (use code-diff-audit skill)
- All 17 DuShen scenes must be synced when modifying shared components
- Run project-audit + scene-health-check after refactors
- Update context/progress.md at end of each session
- Write architecture decisions to context/decisions.md

## Shell Command Rules (duplicated from CLAUDE.md for convenience)
- Bash (MSYS2/Git Bash), not Windows cmd
- Paths: `/c/Users/...`, `/d/unity_school/...`
- Commands: `ls`/`find`/`grep`, not `dir`/`where`/`findstr`
- Redirection: `2>/dev/null`, not `2>nul`
