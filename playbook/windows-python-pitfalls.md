# Windows + Python 坑合集（MSYS2/Git Bash 环境）

> 2026-08-09 多次踩坑。查尔斯的工作站是 Windows + Git Bash（MSYS2）。

## 控制台编码（高频）
- 现象：print 中文/特殊字符（U+2011 等）报 UnicodeEncodeError（GBK 控制台）
- 修法：脚本开头 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` + stderr 同样处理
- 注意：**被调用的子脚本**也可能踩（主脚本 reconfigure 不解决子进程）

## MSYS 路径转换（诡异坑）
- 现象：`del /f /q x` 在 MSYS bash 下变成 `del F:/ Q:/ x`（/f /q 被当成路径转换！）
- 影响：命令行测试命令时结果和真实环境不一致；approval 判定也因此误判
- 修法：测试命令用 MSYS_NO_PATHCONV=1 前缀或改用等价形式；判定以 gateway 真实运行为准

## Python 字符串引号
- 中文引号"详细"和英文双引号 " 混用 → SyntaxError
- 修法：外层用单引号包含中文引号的字符串

## 环境区分
- 系统 Python312（C:/Users/13040/AppData/Local/Programs/Python/Python312）——装了 websocket-client 等
- Hermes venv（hermes-agent/venv）——无 websocket-client，numpy 还可能是坏的（numpy._core._multiarray_umath 缺失）
- uv python（AppData/Roaming/uv）——Hermes 桌面端
- 脚本调子进程时用**绝对路径**指定对的解释器，别依赖 PATH
- **cron 环境 PATH 更窄**（2026-08-11 实测）：cron 拉起的 python 找不到 `bash`（WinError 2），`subprocess.run(["bash", ...])` 直接挂。修法：绝对路径 `D:/Git/bin/bash.exe`。症状：脚本手动跑成功但 cron 报 script failed
- **PYTHONPATH 污染**（2026-08-11 实测）：Hermes 设了 PYTHONPATH 指向 venv site-packages，所有 python（包括系统 Python312）都会加载 venv 里损坏的 numpy。跑独立脚本前 `unset PYTHONPATH`

## 文件编码
- 中文文件名/内容：写文件统一 encoding="utf-8"
- 特殊字符（·、…）会被 Hermes read_file 误判 binary——档案避免连续特殊字符行
