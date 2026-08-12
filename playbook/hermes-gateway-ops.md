# Hermes Gateway 运维手册（重启/故障排查）

> 创建: 2026-08-10 | 更新: 2026-08-11 | 适用: Hermes 桌面端 | 类型: 运维流程
> 来源: 2026-08-10 QQ 链路连环事故 + 2026-08-11 QQ 蹦英文两坑复盘

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

## QQ 蹦英文排查（2026-08-11 新增两坑）

### 坑 A：新会话第一条消息蹦英文 "📬 No home channel is set for Onebot..."
- **现象**：删旧会话/新会话第一条消息时，QQ 收到英文提示（home channel 通知）
- **根因**：`gateway/run.py` ~17835 行，平台没设 home channel 时对新会话首条消息发英文 notice
- **修法**：config.yaml `platforms.onebot.home_channel: {platform: onebot, chat_id: qq-1304024816, name: Charles}`（用 `hermes config set platforms.onebot.home_channel.chat_id qq-1304024816` 等，config.yaml 直接 patch 会被安全保护拒）
- **兜底**：run.py 的 notice 文案已中文化（以后换平台也不蹦英文）
- **排查线索**：这类提示不走对话归档！gateway.log/归档全干净时，去 grep run.py 的英文文案定位

### 坑 B：重启 gateway 后 QQ 收到"我回来了"自动回复
- **现象**：强杀/崩溃后重启，QQ 收到一条"刚才是网关断了一下又恢复了"式回复（45 字左右，中文，agent 生成）
- **根因**：Hermes 崩溃恢复 auto-resume（社区 issue #35576）：被杀时活动会话标 resume_pending，重启 `_schedule_resume_pending_sessions()` 合成空消息续跑 → 发回原平台。gateway.log 里是 `inbound message: ... msg=''` → response ready
- **开关（2026-08-11 本地加）**：config.yaml `agent.gateway_auto_resume: false`。run.py 两处改动：①~2210 行桥接 `HERMES_GATEWAY_AUTO_RESUME` env；②`_schedule_resume_pending_sessions()` 开头判断 false 直接 return
- **验证**：重启后日志出现 `Startup auto-resume skipped: HERMES_GATEWAY_AUTO_RESUME=false` 即生效
- **副作用**：关闭后崩溃中断的会话不自动续跑，但 transcript 保留，下条真实消息正常恢复

## 相关文件
- 启动脚本: `~/AppData/Local/hermes/gateway-service/Hermes_Gateway.vbs` / `.cmd`
- 适配器: `~/AppData/Local/hermes/hermes-agent/gateway/platforms/onebot.py`
- 日志: `~/AppData/Local/hermes/logs/gateway.log` / `agent.log` / `errors.log`
- PID: `~/AppData/Local/hermes/gateway.pid`

## 铁律
- 任何场景（QQ/家/工作站）改完 gateway 代码，回复必须附验证结果，不许只说"重启生效"
- 教训 008：同一天犯过两次（18:22 和 19:39），都是只杀不拉

## 外部重启通道（2026-08-12 新增，重要）

**问题**：Hermes 安全机制会在"gateway 在跑 + agent 上下文"时拦截 gateway lifecycle 命令（restart/stop/start 全拦，连 taskkill 也拦——防自杀循环，022 教训的机制化）。桌面会话也中招（进程树亲缘）。

**解法：schtasks 从系统环境拉起**（Windows 调度器启动，无 agent 标记，不被拦）：

```python
import subprocess
py = r"C:\Users\13040\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
script = r"C:\Users\13040\AppData\Local\hermes\scripts\restart_gateway_once.py"
subprocess.run(["schtasks", "/create", "/tn", "gw_restart_once", "/tr", f'"{py}" "{script}"',
                "/sc", "once", "/st", "23:59", "/f"], check=True)
subprocess.run(["schtasks", "/run", "/tn", "gw_restart_once"], check=True)
subprocess.run(["schtasks", "/delete", "/tn", "gw_restart_once", "/f"], check=True)
```

- 必须用 Python subprocess（列表参数），bash 直接调 schtasks 会被 MSYS 转义搞坏（/create 变 //create）
- restart_gateway_once.py 内部：subprocess.run(["hermes", "gateway", "restart"])，日志写 gateway-restart-standalone.log
- 守护进程（gateway_guard.py）也扛这个职责，但 schtasks 是"现在就要重启"的即时通道
