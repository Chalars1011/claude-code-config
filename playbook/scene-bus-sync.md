# 多场景互通搭建（场景总线 scene_bus）

> 创建: 2026-08-10 | 更新: 2026-08-10 | 适用: Hermes 多场景（家/QQ/工作站） | 类型: 搭建流程
> 来源: 2026-08-09 三端联通 + 2026-08-10 scene_bus 秒级同步 + 当天三次事故复盘

## 适用场景
让同一个 agent 在多个场景（Hermes 桌面/QQ/Claude Code 工作站）共享同一颗心——消息实时互通、记忆实时同步。

## 架构
```
                    ┌─────────────┐
QQ/NapCat(3001) ──→ │             │
Hermes state.db ──→ │ scene_bus   │──→ .events/ 铃铛（秒级）
Claude history ──→  │ (5s 一轮)   │──→ conversations/ 归档
                    └─────────────┘──→ MEMORY.md 最近事件块
```
- 每个场景有独立的"门"（QQ/桌面/工作站），共用一颗心（D:/Aurelia/）
- scene_bus.py 常驻进程：扫三个源 → 敲铃铛 + 归档 + 同步 MEMORY
- cron 分钟级 watchdog 兜底（幂等：mark 只前进、防重复行检查）

## 搭建步骤

### 1. 定场景与入口
- 每个场景一个消息源 + 一个归档目录（conversations/qq/、desktop/、workstation/）
- 每个场景一个事件类型（qq_incoming / home_incoming / workspace_incoming）

### 2. 写事件层
- .events/ 敲铃铛（带时间戳），每小时清理留最近 100 条
- 所有场景的消息 → 统一事件格式

### 3. 写归档 watchdog
- 每个场景一个 watchdog（读源 → 追加归档），提取 run_once() 供 scene_bus 复用
- 幂等：mark 文件记位置，只前进；防重复行检查

### 4. 写 scene_bus 主循环
- 5 秒一轮：扫 state.db 新消息 → QQ/桌面归档；扫 ~/.claude/history.jsonl → 工作站归档
- 同步 .events → MEMORY.md「最近事件」块（让会话启动带上最新动态）
- 开机自启（scene_bus.vbs 放启动文件夹）

### 5. 接 Hermes 适配器（消息进 state.db）
- QQ 走 onebot 适配器；桌面走 gateway；工作站写 history.jsonl
- 新场景接入：适配器 / 历史文件 watchdog / 直接调 event.py，总线自动接上

### 6. 立读心规矩
- 开口前翻 .events/ 最近几条（秒级到位）
- "看过即过"：禁止把事件清单复制进记忆（会膨胀）

## 关键坑（血泪）
1. **双响**：旧桥没死透还占着一条连接 → 一条消息回两次。杀干净 + netstat 验证只剩一个客户端
2. **gateway 只杀不拉**：改代码后"重启 gateway"只杀旧进程没拉新的 → QQ 静默断链（当天两次！）
3. **同步阻塞**：async 函数里直接调 urllib → 事件循环卡死 → gateway 心跳停 → 进程死。必须 asyncio.to_thread
4. **cron 抢锁**：两个 serve 进程同时跑会抢 jobs.json（Permission denied）
5. **配置存成字符串**：hermes config set 把数组存成字符串（MCP args / plugins.enabled）→ 手改 YAML

## 验收标准
- 在 QQ 说话 → 桌面/工作站 5 秒内能看到
- 工作站说话 → QQ 那边能答上
- 杀掉 gateway 重启后：进程在 + onebot connected 才算恢复
