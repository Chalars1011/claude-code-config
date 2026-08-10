# Hermes Gateway 运维手册（重启/故障排查）

> 创建: 2026-08-10 | 更新: 2026-08-10 | 适用: Hermes 桌面端 | 类型: 运维流程
> 来源: 2026-08-10 QQ 链路连环事故（gateway 一天死三次）复盘

## 适用场景
QQ 没响应/消息发不出去/gateway 挂了，或改完 Hermes 代码需要重启 gateway。

## Gateway 是什么
Hermes 的消息网关：连接 NapCat(QQ) → onebot 适配器 → agent。QQ 消息进出的唯一通道。
- WS: ws://127.0.0.1:3001（NapCat 正向 WS）
- HTTP: 127.0.0.1:3000（NapCat HTTP API，standalone 发送通道）

## 重启 gateway（标准姿势，三步缺一不可）

### 1. 杀旧进程
```bash
powershell -Command "Get-CimInstance Win32_Process | Where-Object {\$_.CommandLine -match 'gateway run' -and \$_.Name -eq 'python.exe'} | Select-Object ProcessId"
# 对每个 PID：powershell Stop-Process -Id <PID> -Force
```

### 2. 拉起新进程（detached 方式）
```bash
cd ~/AppData/Local/hermes/gateway-service && cscript //nologo Hermes_Gateway.vbs
```

### 3. 验证（必须！）
```bash
# ① 进程存在
powershell -Command "Get-CimInstance Win32_Process | Where-Object {\$_.CommandLine -match 'gateway run'} | Select-Object ProcessId"
# ② onebot 已连接
tail ~/AppData/Local/hermes/logs/gateway.log  # 找 "✓ onebot connected"
```
**只杀不拉 = QQ 静默断链。拉起来不验证 = 等于没拉。**

## 故障排查清单

### QQ 没响应
1. gateway 进程在吗？（上面第 3 步的进程查询）
2. gateway.log 最后一条是什么时间？停在 inbound 没 response → 处理卡死/崩溃
3. 看 `~/AppData/Local/hermes/logs/gateway-exit-diag.log` 找退出原因（unclean exit = 被强杀）
4. 看 agent.log 里 QQ 会话有没有在跑

### 崩溃原因速查（2026-08-10 实测）
- **同步阻塞事件循环**：`urllib.request.urlopen` 直接跑在 async 函数里 → 心跳停 → 死。必须用 `asyncio.to_thread` 包
- **WS get_msg 超时**：NapCat 的 WS 通道对 get_msg 不响应（15s 超时常态）→ 走 HTTP 127.0.0.1:3000 兜底
- **只杀不拉**：执行"重启"只杀了旧进程没拉新的

### 改代码后必须验证
改 onebot.py / gateway 相关代码 → 语法检查（venv python -c "import ast; ast.parse(...)"）→ 重启 → 验证连接 → 实测功能（发条消息）

## 相关文件
- 启动脚本: `~/AppData/Local/hermes/gateway-service/Hermes_Gateway.vbs` / `.cmd`
- 适配器: `~/AppData/Local/hermes/hermes-agent/gateway/platforms/onebot.py`
- 日志: `~/AppData/Local/hermes/logs/gateway.log` / `agent.log` / `errors.log`
- PID: `~/AppData/Local/hermes/gateway.pid`

## 铁律
- 任何场景（QQ/家/工作站）改完 gateway 代码，回复必须附验证结果，不许只说"重启生效"
- 教训 008：同一天犯过两次（18:22 和 19:39），都是只杀不拉
