# NapCat + QQ 桥接经验（OneBot v11）

> 2026-08-08 搭建，2026-08-09 升级到 Hermes gateway。跨项目可复用：任何 QQ 机器人接入。

## NapCat 启动（免扫码）
- 启动参数带 `-q QQ号`：`node index.js -q 3839451331` —— 用缓存登录态秒登，免扫码
- 登录态失效时 NapCat 自动回退二维码（人工扫一次后恢复免扫码）
- 也可配 NAPCAT_QUICK_ACCOUNT / NAPCAT_QUICK_PASSWORD 自动重登

## OneBot v11 要点
- 正向 WebSocket：`ws://127.0.0.1:3001`（NapCat 默认），多客户端可同时连
- 鉴权：`Authorization: Bearer <token>`（token 在 NapCat 配置）
- 发私聊：action=`send_private_msg`，params={user_id, message}，带 echo 匹配响应
- 消息事件：message_type=private/group，user_id、sender.nickname
- **自己发的消息 user_id = 机器人自己**——适配器要跳过（防自回复循环）

## 桥接程序安全设计（自研桥经验，思路可复用）
- 白名单目录（路径规范化 + 前缀校验，防穿越）
- 工具禁写清单（tasks.md / config 等保护文件）
- 写操作 Y/N 确认流（5 分钟超时自动取消）
- 紧急开关（文件存在=暂停自动干活）
- 超时（工具轮数、进程超时）
- 长任务占位消息 + 忙碌插话安抚（防第二个进程答非所问）

## 切换 Hermes 后
- 旧桥 lia_qq.py 停用，备份保留（回滚保险）
- QQ 收发由 Hermes gateway onebot 适配器接管（见 hermes-qq-integration.md）
