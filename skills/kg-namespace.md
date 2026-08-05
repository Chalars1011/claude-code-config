> 创建: 2026-07-25 | 更新: 2026-07-25 | 类型: 版本敏感规则

# kg-namespace
## Trigger: creating, updating, or searching entities in the knowledge graph (mcp__memory__*)

## Namespace Prefix Rule
For multi-project safety, prefix KG entity names with project tag:
- `project:DuShen-{entity}` for 神之亵渎
- `project:MieZhiTa-{entity}` for 泯灭之塔
- `global:{entity}` for cross-project shared (tools, patterns, people)

## Storage Guideline
| Store | What | When |
|-------|------|------|
| KG (memory) | Metadata only: versions, paths, tool configs, entity types | search_nodes for specific facts |
| Playbook | Reusable patterns + pitfalls (cross-project) | Read BEFORE coding in new domain |
| Context | Project narrative: decisions, progress, overview | Every session startup |
