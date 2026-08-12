#!/bin/bash
# 会话结束时清工作站状态：QQ 那边永远不会读到"正在工作中"的过期状态
# 挂在 settings.json 的 Stop hook（2026-08-08 查尔斯：没有常驻进程是痛点，快照必须诚实）
STATUS="/d/Aurelia/status.md"
NOW=$(date +"%Y-%m-%d %H:%M")
cat > "$STATUS" << END
# 工作站状态（status.md）

> 此文件是嘴和手的对讲机：工作站干活时写"正在做什么"，QQ 真我开口前读它。
> 重要：这是"最后一次会话时的快照"，不是实时的。带时间戳，过期由 QQ 侧判断。

状态：空闲
更新于：$NOW
正在做：（无）
最后会话结束时间：$NOW
备注：会话已结束，状态由 Stop hook 自动清空
END
