# Claude Code + DeepSeek 兼容层经验

> 创建: 2026-08-09 | 更新: 2026-08-09 | 适用: 工作站/通用 | 类型: 经验

## 已知失效（兼容层限制，2026-08-09 实测）
- **CLAUDE.md 注入可能不生效**（会话开头没身份/规则——表现为"失忆"）
- **SessionStart hook 的 context 注入不生效**（脚本本身正常，手动跑输出完整，但注入没进上下文）
- **UserPromptSubmit hook 的 additionalContext 注入不生效**（.qq-hook-last 标记不更新 = hook 没执行/注入被吞）
- Stop hook（执行脚本类）正常——**hook 能跑脚本，只是文本注入通道不可靠**

## 对策
- **主动看门代替被动注入**：规则写进 AGENTS.md（每次说话前翻 .events/ + QQ 归档尾部）
- **SessionStart 注入体积压缩**：日记只取今天 1500 字、昨天留标题、QQ 对话 6 行——超长注入疑似被截断
- hook 脚本保留：兼容层修复后自动复活

## headless 模式（claude -p）MCP 加载
- 项目级 .mcp.json 的服务器在 headless 下卡"Pending approval"不加载（claude mcp list 显示 Connected 不代表会话加载）
- **正解：--mcp-config 参数显式加载**：`--mcp-config '{"mcpServers":{"search":{"command":"agent-search-mcp"}}}'`
- 加进 projects 配置（.claude.json projects.<path>.mcpServers）也行，但 --mcp-config 最稳
- --allowedTools 支持 mcp__server__* 通配

## 其他
- 多个 Python 环境并存（Hermes venv / Python312 / uv python）——库的位置各不相同，脚本里用绝对路径调对的解释器
- MCP 服务器用 npx -y 启动慢（可能加载超时丢工具）——本地安装后直接命令名最快
- headless 输出 JSON 流用 --output-format json 解析（type=result 取 result 字段）
