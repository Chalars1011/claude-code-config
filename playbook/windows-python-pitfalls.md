# Windows + Python 坑合集（MSYS2/Git Bash 环境）

> 创建: 2026-08-11 | 更新: 2026-08-11 | 适用: 工作站/通用 | 类型: 经验

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

## npm 全局包更新（2026-08-11 实测 Claude Code 2.1.217→2.1.227）
- **npm 新安全策略会拦 install scripts**：`npm install -g` 后报 `install scripts blocked because they are not covered by allowScripts`，原生二进制没装上，命令报 `claude native binary not installed`。修法：`npm install -g <pkg> --allow-scripts=<pkg>` 或 `npm config set allow-scripts=<pkg> --location=user`
- **目录被 bash 锁删不掉**：`rm -rf` 报 `Device or resource busy`——是当前 shell 的 CWD 在里面（cd 进去过）。先 `cd` 出来再删；还 busy 就 `rm -rf dir/*` 清内容再 `rmdir`
- **npm 记录与实际安装位置可能对不上**：`npm root -g` 显示 Hermes 的 node 目录但包实际在 `AppData/Roaming/npm/node_modules/`——以 `which <cmd>` 和 `npm ls -g` 实际结果为准
- **验证更新成功**：`<cmd> --version` + 实测跑一次（`claude -p "回复OK" --permission-mode bypassPermissions`），别只看 npm 输出

## 文件编码
- 中文文件名/内容：写文件统一 encoding="utf-8"
- 特殊字符（·、…）会被 Hermes read_file 误判 binary——档案避免连续特殊字符行
