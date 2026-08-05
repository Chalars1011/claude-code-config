> 创建: 2026-07-25 | 更新: 2026-07-25 | 类型: 版本敏感规则

# search-strategy
## Trigger: need to search docs, web, or look up unfamiliar domain

## Search Order (3+ rounds no progress → escalate)
1. `mcp__search__free_search` — external web (DuckDuckGo + Sogou for Chinese content)
2. `mcp__context7__query-docs` — official API docs (e.g. Unity/Cinemachine/URP)
3. `mcp__memory__search_nodes` — KG (metadata: tool versions, project paths, key configs)
4. Read `~/.claude/playbook/index.md` — keyword lookup (10 lines, identifies which file)
5. Open specific playbook file(s) — read full detail
6. Read `project/.claude/context/` — project-specific decisions/progress

## Auto-trigger (do not skip)
- Same bug survives 3 fix attempts → MUST stop and search
- User says "read the docs" or "check online" → search immediately
- Unfamiliar domain → search before coding
- Version upgrade issues → search "{topic} Unity {version} migration"

## Post-search
- Always cite URL or library source
- Reusable solution → write playbook entry (`~/.claude/playbook/{topic}.md`)
- API-specific → save libraryID for future context7 queries
