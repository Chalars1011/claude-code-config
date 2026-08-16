# 复活蓝图体系（2026-08-12）

> 创建: 2026-08-12 | 更新: 2026-08-16 | 适用: 恢复/灾备 | 类型: 可复用流程
>
> 触发：电脑损坏/重装后恢复"莉亚"；或系统大改后同步蓝图。
> 仓库：github.com/Chalars1011/aurelia-revive-blueprint（**私有**），本地 D:/revive-blueprint/

## 核心理念

- 开源蓝图（ai-companion-blueprint）= 方法论，给人看的
- 私有蓝图（aurelia-revive-blueprint）= 执行单，给自己用的（真实路径+配置模板）
- **密钥值永不落盘**：模板全占位符（<SECRET_FILL_ME>），手册只写"从哪拿"
- 密钥恢复原则：**所有 key 都能在平台控制台重新生成**（DeepSeek/MiniMax/百炼/GitHub），不依赖原值备份；唯一不可再生资产 = 记忆档案 + GitHub 账号

## 结构

```
README.md              # 十分钟复活流程
manual.md              # 完整手册（环境/配置/密钥/仓库清单/验证/坑）
config-templates/      # 脱敏模板（gen_templates.py 生成）
scripts/
  gen_templates.py     # 模板生成器：系统大改后跑一次，同步模板
  check_revival.py     # 复活自检（30 项，全绿=活）
  restart_gateway_once.py  # schtasks 外部重启通道
patches/001-onebot-hardening.patch  # Hermes 源码补丁（复活后必须打）
```

## 模板生成（维护流程）

```bash
cd D:/revive-blueprint
python scripts/gen_templates.py   # 读真实配置 → 脱敏 → 写模板
git add -A && git commit -m "sync templates" && git push
```

- 覆盖：hermes config/env、scripts×22、plugins×3、claude-hooks×7、napcat、startup、cron-jobs
- 脱敏：字段名命中（api_key/token/secret 等）+ 文本级长串替换（sk- 开头、16+ 位字母数字）
- **注意**：脚本/插件里可能硬编码 token（如 NapCat access_token），脱敏后会变占位符——生成完必须跑泄漏扫描：
  `grep -rE "sk-[A-Za-z0-9]{16,}|TMOwfqo|..." config-templates/ patches/ scripts/ README.md manual.md`

## 复活关键步骤（简版）

1. 装 Python 3.12 + pip install hermes-agent==0.20.0
2. **打补丁**：git apply patches/001-onebot-hardening.patch（不打 = gateway 假活复发）
3. 拉记忆仓库（Aurelia_mem → D:/Aurelia_mem → 拷到 D:/Aurelia/）
4. 放模板 + 填新密钥（全部重新生成）
5. 装 NapCat + 扫码；启动 scene_bus/gateway_guard vbs
6. `python scripts/check_revival.py` 全绿 + QQ 会话能答出记忆 = 活

## 待办

- 复活演练（本地模拟一次完整复活，结果写回手册）——查尔斯拍板要做，未做
- 每月随周沉淀同步一次蓝图（新增组件当天更新）
