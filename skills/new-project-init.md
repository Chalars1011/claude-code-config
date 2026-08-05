> 创建: 2026-07-25 | 更新: 2026-07-25 | 类型: 版本敏感规则

# new-project-init
## Trigger: entering a new project directory

## Checklist
When entering a new project directory, automatically check:
1. `.claude/context/` exists? (decisions.md / progress.md / project.md)
2. `.claude/skills/` has useful skills?
3. Is Unity project? `.mcp.json` configured?

## Actions if missing
- Copy context templates from `~/.claude/playbook/skill-templates/`
- Copy generic skills from `~/.claude/playbook/skill-templates/`
- Prompt user for Unity MCP config
