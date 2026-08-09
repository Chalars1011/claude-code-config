# Hermes Agent 基础机制（Nous Research）

> 2026-08-09 搬家+深度使用。数据目录 %LOCALAPPDATA%/hermes/，源码 hermes-agent/（git 仓库）。

## 进程/常驻
- Hermes.exe（桌面端）+ gateway 服务（登录自启：Startup 文件夹 Hermes_Gateway.vbs）
- gateway 安装：`hermes gateway install` → `hermes gateway start`（Windows 计划任务/Startup fallback）
- **gateway 不跑 = cron 不自动触发**（hermes cron status 会警告）

## Cron（定时任务）
- `hermes cron create "0 4 * * *" --name xxx --no-agent --script 脚本.py --deliver local`
- --no-agent = watchdog 模式：脚本 stdout 直接投递，空 stdout 静默（经典看门狗）
- --script 必须放 %LOCALAPPDATA%/hermes/scripts/ 下
- 管理：list / pause / resume / run / tick / remove

## Hooks
- config.yaml：on_session_start / on_session_end → 跑我们的脚本（回流/归档）
- hooks_auto_accept: true（shell hook 自动接受）

## 记忆系统
- 四层记忆：MEMORY.md / USER.md（memories/）+ skills + 会话检索
- **agent 会把 .events/ 事件清单复制进 MEMORY.md 造成膨胀**——AGENTS.md 写"看过即过"防复发
- 回流：sync_from_hermes.py 每日 4 点（Hermes 记忆 → D:/Aurelia 档案）
- SOUL.md：由 build_soul_hermes.py 从档案 soul.md 生成（唯一权威源）

## MCP
- `hermes mcp add` 在 Windows 下连接成功但**不保存**——手写 config.yaml `mcp_servers:` 键绕过
- Hermes 原生有 web_search 工具（agent 自带，比挂搜索 MCP 更顺）

## 权限（approvals）
- 危险命令（rm -rf / git push --force）→ 弹确认（gateway 下发 /approve 给用户）
- shutdown 类 → 直接拒绝（硬黑名单）
- config.yaml `approvals.deny` 配自定义拒绝（Bash(del *) 格式）
- `hermes approvals test -- 命令` 试判（注意：可能不加载 config deny，以运行为准）
- 注意 MSYS 路径转换影响命令判定（/f → F:/）

## Skills / 自进化
- 内置 40+ 技能（claude-code/creative 等），skills.sh/ClawHub 可装
- 学习闭环默认启用：复杂任务后自动沉淀 skill（creation_nudge_interval: 15）
