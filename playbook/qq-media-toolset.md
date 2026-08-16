# QQ 媒体工具集模式（2026-08-12）

> 创建: 2026-08-12 | 更新: 2026-08-16 | 适用: QQ 发送能力 | 类型: 可复用流程
>
> 触发：要给 QQ 加"发图/发文件/发语音/合并转发"能力；或新平台能力接入。
> 核心思路：**平台能力做成 agent 工具（MCP），不做死发送层**（社区 hermes-napcat 48 工具模式）。

## 架构

```
agent（任何场景）→ qq_media MCP（stdio）→ NapCat HTTP API（127.0.0.1:3000，Bearer token）
```

- 接收走 WS（gateway 平台层），发送走 HTTP（MCP 工具直接调），两路互不干扰
- token 从 config.yaml `platforms.onebot.extra.access_token` 读，**禁止硬编码默认值**（008 教训扩展）
- 工具集：qq_send_text / qq_send_image / qq_send_file / qq_send_voice / qq_send_forward / qq_poke
- chat_id 默认 `qq-1304024816`（查尔斯）

## 关键文件

- `C:/Users/13040/AppData/Local/hermes/scripts/qq_media_mcp.py` —— MCP server（FastMCP，Python312 跑）
- 注册：config.yaml `mcp_servers.qq_media`（command=Python312，args=[-E, 脚本路径]）

## 坑

1. **Python 版本**：MCP 脚本必须用系统 Python312（pymcp_libs 的二进制是 312 编译的），venv python 会 pydantic 崩溃
2. **PYTHONPATH**：脚本开头 `os.environ.pop("PYTHONPATH", None)`，否则污染
3. **图片**：本地路径转 `file:///C:/...` 形式传 CQ 码，NapCat 才能读
4. **语音**：NapCat 会自动转码（mp3/wav 都能发），不用自己转 silk
5. **合并转发**：私聊用 send_private_forward_msg（NapCat 扩展 API），node 消息组装
6. **MCP 加载**：新增/修改 MCP server 后 gateway 要重启才生效（serve 同理）

## 发送链路验证（快速自测）

```python
import sys, os
os.environ.pop("PYTHONPATH", None)
sys.path.insert(0, r"C:/Users/13040/AppData/Local/hermes/scripts")
import qq_media_mcp as q
print(q.qq_send_image(image=r"D:/Aurelia/art/aurelia_glasses_v2.png"))
```

## 相关

- 配套：onebot-standalone 插件（cron/后台投递走 HTTP 3000）
- 社区参考：hermes-napcat（PyPI）
