# Gateway 假活卡死排查与加固（2026-08-12）

> 触发场景：QQ 消息"半天不回话"、gateway 进程活着但日志断更、housekeeping 停摆。
> 这是 08-10 和 08-12 两次同症状事故后的完整排查路径，直接照做。

## 症状
- gateway 进程在（PID 活着），但 QQ 消息不回、日志无新写入、每分钟 housekeeping 停
- 通常紧跟一条 `Sending response` 日志之后
- 重启 gateway 后恢复

## 排查路径（按顺序）
1. **看日志铁证**：`grep -n "Sending response\|response ready" %LOCALAPPDATA%/hermes/logs/gateway.log`
   - `time=17x.xs api_calls=18` = 长任务（自由活动/巡检）占 agent 循环 3 分钟，属正常但要注意
   - `Sending response` 后无后续 = 发送阶段卡死
2. **代码级根因**：`gateway/platforms/onebot.py` 的 `_api_call`
   - 旧版：`async with self._ws_api_lock: await self._ws.send(...)` —— 锁+send 无超时
   - NapCat WS 假活（TCP 连着但应用层不响应）→ send 无限挂起 → 事件循环被占 → 整机假死
3. **注意**：日志"断更"不能当卡死判据——正常时段 gateway.log 也会断更 1.5 小时+（housekeeping 只启动时打日志）

## 修复（两层）
1. **根因**：onebot.py `_api_call` 锁获取+send 包 `asyncio.wait_for(..., 10.0)`，超时打 warning 返回 None 走调用方兜底
   - 改完：`py_compile` 验证 + `hermes gateway restart` + 日志确认 `✓ onebot connected`
   - hermes-agent 是 git 仓（editable 安装），改完 commit 备份
2. **兜底**：`scripts/gateway_guard.py` + `scripts/gateway_guard.vbs`（开机自启，同 scene_bus 模式）
   - 每 5 分钟：gateway 进程没了 → `hermes gateway restart` + 敲 .events/ 铃铛
   - 连续 3 次拉起失败 → 停手（防死循环）
   - 日志 >2h 无写入 → 只敲铃铛提醒，不自动重启
   - **关键：守护不能跑在 Hermes cron 里**（gateway 死了 cron 也死），必须独立 vbs 常驻

## 坑
- Hermes cron 创建带 `hermes gateway` 命令的 job 会被安全机制拦截（防 SIGTERM 循环）——正好提醒你守护者该独立
- 双 gateway 实例：开机自启 vbs + 桌面 app `hermes serve` 可能重复拉，开机时用 `tasklist | grep python` 核对
- 测试消息别用 curl（git-bash GBK 会乱码），用 Python UTF-8 发
