# Hermes 更新 SOP（避坑流程）

> 创建: 2026-08-11 | 更新: 2026-08-11 | 适用: Hermes 桌面端 | 类型: 运维流程
> 来源: 2026-08-11 查尔斯问"以后更新应该怎么做"，+ 本地 9 文件补丁的现实

## 核心原则

1. **不追开发分支，只追正式 tag**。main 分支是开发版（小白鼠），正式 tag（v2026.x.x）才更新。本地 v2026.8.3 是 8/3 的，远程 main 领先 159 提交但没新 tag——不更新。
2. **咱们有 9 个本地补丁 + 1 个独有文件**，更新 = 重打补丁，这是最大的工作量，不是点一下按钮。
3. **更新前必须全停**：桌面 app、gateway、cron 都在跑时会锁 venv 的 .pyd 文件（--force-venv 警告明确说过），更新会半途失败。必须关掉 Hermes 全部进程再更新。
4. **更新后必须验证**（008 教训：杀完必须验证，改完先验证再收工）。

## 更新前（判断要不要更新）

```bash
cd ~/AppData/Local/hermes/hermes-agent
# 1. 看远程有没有新 tag（先开梯子！GitHub 直连会 SSL 断）
git ls-remote --tags origin | grep -v "\^{}" | sort -t. -k2 -n | tail -3
# 2. 看本地版本
hermes --version
# 3. 如果有新 tag，看它跟本地差多少提交、改了啥
git fetch origin
git log --oneline HEAD..origin/main | head -30
git log --oneline HEAD..origin/main -- gateway/platforms/onebot.py   # 咱们独有文件上游有没有动
```

**判断标准**：
- 没有新 tag → 不更新（main 是开发分支）
- 有新 tag 但都是边缘修复、咱们没踩到 → 不更新，等攒够了再说
- 有新 tag 且包含咱们在用的路径修复（cron/gateway/onebot/记忆）→ 值得更新
- 更新的收益必须 > 重打补丁的成本 + 翻车风险

## 更新前（备份，必须做）

```bash
mkdir -p ~/AppData/Local/hermes/patch_backup_$(date +%Y%m%d)
cd ~/AppData/Local/hermes/hermes-agent
# 1. 全部本地改动的 diff（4MB+，最重要）
git diff > ~/AppData/Local/hermes/patch_backup_$(date +%Y%m%d)/local_patches.diff
# 2. 独有文件单独备份（onebot.py 是全新文件，diff 里没有）
cp gateway/platforms/onebot.py ~/AppData/Local/hermes/patch_backup_$(date +%Y%m%d)/
# 3. 改过的文件清单（git status --short | grep "^ M" 就是）
git status --short
# 4. 配置、记忆、技能（不在 git 里的）
cp ~/AppData/Local/hermes/config.yaml ~/AppData/Local/hermes/patch_backup_$(date +%Y%m%d)/
cp -r ~/AppData/Local/hermes/skills ~/AppData/Local/hermes/patch_backup_$(date +%Y%m%d)/ 2>/dev/null
cp -r /d/Aurelia ~/AppData/Local/hermes/patch_backup_$(date +%Y%m%d)/aurelia_backup 2>/dev/null
```

## 更新中（全停 + 拉取）

**必须全停 Hermes 进程**（桌面 app + gateway + 所有 python 实例），否则 venv 锁死更新半途失败：
```bash
# 1. 停桌面 app（Hermes.exe 进程树）
powershell "Get-CimInstance Win32_Process | Where-Object {\$_.Name -match 'Hermes'} | Select-Object ProcessId"
# 2. 停 gateway
powershell "Get-CimInstance Win32_Process | Where-Object {\$_.CommandLine -match 'gateway run' -and \$_.Name -eq 'python.exe'}"
# 3. 杀干净（taskkill /F /T /PID 每个）
# 4. 更新（在项目目录，此时没有任何进程占用）
cd ~/AppData/Local/hermes/hermes-agent
git stash           # 把本地补丁暂存起来（不暂存直接 pull 会冲突）
hermes update --backup --yes
```

**注意**：`hermes update` 有 --backup 参数（全量备份），但咱们的补丁它不管——`git stash` 才是保补丁的正道。也可以 `git stash` 后手动 `git pull` + `pip install -r`（update 命令本质就是这个）。

## 更新后（重打补丁，最花时间的一步）

```bash
cd ~/AppData/Local/hermes/hermes-agent
# 1. 先看 stash 还在不在、补丁能不能干净应用
git stash list
git stash apply        # 应用补丁，冲突会报出来
# 2. 逐个文件看冲突
git status --short
# 3. 有冲突的文件（CONFLICT 标记）逐个手动合并：
#    - 咱们的改动是"功能补丁"（拆条、表情、auto-resume 开关、home channel 中文化）
#    - 上游改动是"修复"——两边都要留，不能丢上游修复
#    - 用 patch 工具逐个看冲突块，保留双方逻辑
# 4. 独有文件 onebot.py：如果上游新版本改了它依赖的接口（比如 gateway/run.py 的 send 调用）
#    要对照新接口调整，不能直接复制回去
# 5. 语法检查
cd ~/AppData/Local/hermes/hermes-agent && python -m py_compile gateway/run.py gateway/config.py cron/scheduler.py tools/send_message_tool.py agent/prompt_builder.py tools/file_operations.py hermes_cli/tools_config.py toolsets.py gateway/platforms/api_server.py
```

**重打补丁的通用步骤**（对每个冲突文件）：
1. `git show HEAD:path` 看上游新版本长啥样
2. 找到咱们补丁对应的逻辑（搜索特征字符串：拆条 `splits_long_messages`、表情 `_parse_face_markers`、开关 `HERMES_GATEWAY_AUTO_RESUME`、中文化提示、onebot checker）
3. 把逻辑重新加进新版本文件
4. 语法检查 + 实机验证

## 更新后（验证，必须全过）

```bash
# 1. 进程拉起来
cscript //nologo "C:\Users\13040\AppData\Local\hermes\gateway-service\Hermes_Gateway.vbs"
# 2. 等 10 秒验证
powershell "Get-CimInstance Win32_Process | Where-Object {\$_.CommandLine -match 'gateway run' -and \$_.Name -eq 'python.exe'}"
tail ~/AppData/Local/hermes/logs/gateway.log   # 找 "✓ onebot connected"
# 3. 桌面 app 拉起来，等它完全启动
# 4. 功能实测（按优先级）：
#    a. QQ 收发消息正常（发一条测试）
#    b. QQ 拆条发送正常（长回复分多条）
#    c. 表情转换正常（[表情:63] → 真玫瑰图标）
#    d. cron 正常跑（cronjob action=list 看 last_status）
#    e. 记忆/归档正常（scene_bus 敲铃铛）
# 5. 验证 auto-resume 开关还在（重启 gateway 日志出现 "Startup auto-resume skipped"）
# 6. 验证 home channel 配置还在（hermes config get platforms.onebot.home_channel）
```

## 回滚（万一翻车）

```bash
# 1. 回到更新前
cd ~/AppData/Local/hermes/hermes-agent
git stash apply 或 git checkout <更新前commit>
# 2. 还原配置
cp ~/AppData/Local/hermes/patch_backup_*/config.yaml ~/AppData/Local/hermes/config.yaml
# 3. 还原技能/记忆（从备份目录）
# 4. 重启 + 验证
```

## 边界清单（设计铁律五问，更新流程的答案）

1. **关机多天**：更新中途关机 → git 操作要么完成要么可重试，备份在磁盘上不丢。无风险。
2. **崩溃/被杀**：更新中进程被杀 → git pull 是原子的，重跑即可；venv 装一半 → 重跑 `pip install` 修复。
3. **数据异常**：更新把 config.yaml 迁移坏 → `--backup` 有全量 zip + 咱们手动备份了 config.yaml，还原即可。
4. **安全**：更新可能改密钥文件权限 → 更新后查 .env 权限和内容没变（或按迁移提示重输）。
5. **无人场景**：查尔斯不在时**不自动更新**（cron 不挂更新任务），更新必须人工在场，因为要全停 + 重打补丁 + 实测。

## 一句话总结

**等正式 tag → 全停 → 备份补丁 → git stash → 更新 → 重打补丁 → 全链路验证 → 有问题回滚。**
不追开发分支，不做无人更新，不跳过验证。
