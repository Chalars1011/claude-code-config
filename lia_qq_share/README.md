# 莉亚 QQ（查尔斯专用）

让"莉亚"拥有一个 QQ 号：加你好友、陪你聊天、接任务、报进度。

## 架构
```
你的 QQ号(查尔斯) <-> 小号QQ <-> NapCat(框架) <-> lia_qq.py(桥接) <-> DeepSeek API(大脑)
```

## 安装步骤（还差 NapCat 没装）

### 1. 下载 NapCat（需要你手动，浏览器下载快）
1. 打开 https://github.com/NapNeko/NapCatQQ/releases
2. 下载最新 Windows 版（文件名带 win 或 NapCat.Shell 的 zip）
3. 解压到 D:/LiaQQ/NapCat/
4. 双击运行里面的启动程序 → 弹出登录窗口 → **扫码登录小号**
5. 登录后打开 NapCat 管理面板，确认「OneBot 11 WebSocket 服务」开着、端口 6099

### 2. 填白名单（安全，必做）
打开 D:/LiaQQ/config.json，把 `allowed_uids` 改成你的 QQ 号：
```json
"allowed_uids": [123456789]
```
不填的话任何人发消息莉亚都会回（烧你的 API 钱）。

### 3. 启动
双击 D:/LiaQQ/start_lia.bat
看到「已连接 NapCat」就活了。用主号 QQ 给小号发消息测试。

## 在 QQ 上能用什么
- 正常聊天：当朋友聊，记得说人话，别指望它写小作文
- `任务：xxx` 或 `记一下 xxx` → 记进 D:/LiaQQ/tasks.md
- 问「进度 / 任务列表 / 干完没」→ 汇报任务清单
- 真正的活（改代码/跑游戏）要等电脑上开 Claude Code，那边会读 tasks.md 自动接活

## 文件
| 文件 | 作用 |
|---|---|
| lia_qq.py | 桥接脚本（核心） |
| persona.md | 莉亚的人格设定（想改性格改这里） |
| config.json | 配置（端口/白名单/延迟） |
| tasks.md | 任务清单（Claude Code 和 QQ 共用） |
| chat_history.json | 对话记忆（每好友最近30条） |
| lia_qq.log | 运行日志 |

## 常见问题
- 连不上 6099：NapCat 没启动 / 端口被改 / 登录没完成
- 回得很慢：API 在重试，看日志
- 想停：关掉黑窗口
- 小号被封风险：别实名、别充值、别拉群，只跟查尔斯聊
