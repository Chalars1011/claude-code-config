# Hermes 接入 QQ（hermes-agent-onebot）· 实战经验

> 创建: 2026-08-09 | 更新: 2026-08-09 | 适用: 工作站/通用 | 类型: 经验

## 架构
QQ --NapCat(ws://127.0.0.1:3001 正向WS)-->> onebot.py 适配器 --> Hermes gateway --> agent 自判
- 复用现有 NapCat 3001，不用改 NapCat 配置（hermes-agent-onebot 是纯 WS）
- 旧桥 lia_qq.py 退役，备份保留（回滚用）

## 接入步骤（含踩坑）
1. git clone hermes-agent-onebot，然后 bash apply_patches.sh <hermes-agent路径>
   - 注意：自动补丁可能部分失败（版本差异）：成功=prompt_builder/scheduler/tools_config(需复查)/onebot.py；常失败=config.py/run.py/send_message_tool.py/toolsets.py
   - 注意：tools_config.py 自动补丁会把 onebot 条目**插进注释块**导致 SyntaxError（英文报错回给用户）——必须手动挪到平台表（tools_config.py 的 tuple 列表，参考 yuanbao 行）
2. config.py 手动补：Platform 枚举加 ONEBOT + _apply_env_overrides 加 OneBot env 处理
3. run.py 手动补：适配器工厂加 ONEBOT 分支 + allowlist/allow_all map 加 ONEBOT_ALLOWED_USERS / ONEBOT_ALLOW_ALL_USERS
4. toolsets.py：加 hermes-onebot toolset + hermes-gateway includes
5. onebot.py：connect() 要兼容 is_reconnect=False 参数（新版 gateway 调用签名）
6. .env：ONEBOT_WS_URL / ONEBOT_ACCESS_TOKEN / ONEBOT_BOT_ID / ONEBOT_PRIVATE_CHAT / ONEBOT_GROUP_AT_ONLY / ONEBOT_ALLOW_ALL_USERS
7. config.yaml：platforms.onebot（enabled/extra/ws_url/access_token/bot_id/**dm_policy: allowlist + allow_from**——不配会被 gateway 外层鉴权拦截 Unauthorized）
8. 重启 gateway，日志看 [OneBot] WebSocket connected / ✓ onebot connected

## Hermes 关键机制（经验）
- **MCP 接入**：hermes mcp add 在 Windows 下连接成功但不保存——手写 config.yaml 的 mcp_servers 键绕过（格式：name: {command, args}）
- **Hermes 原生 web_search**：agent 自带搜索工具，比挂 MCP 更顺
- **权限**：危险命令（rm -rf / git push --force）→ 弹确认（QQ 回 /approve）；shutdown 类 → 直接拒；config.yaml 的 approvals.deny 配 deny 规则（Bash(del *) 格式）；注意：hermes approvals test 可能不加载 config deny，实测以 gateway 运行为准
- **记忆**：agent 会把 .events/ 事件清单写进 MEMORY.md 造成膨胀重复——AGENTS.md 规则要写"看过即过，禁止复制进记忆"
- **会话归档**：on_session_end hook 跑 export_session.py，按 session_id 含 'onebot' 分到 conversations/qq/
- **补丁可回滚**：hermes-agent 是 git 仓库，打补丁前 git commit 留回滚点
