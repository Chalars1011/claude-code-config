> 创建: 2026-08-05 | 更新: 2026-08-05 | 类型: 工具使用规则

# vision-review
## Trigger: 美术改图任务完成 / 需对比原版与改版 / 批量评审素材

## 工具: 义眼 (C:/Users/13040/.claude/vision/vision.py，零依赖，python 直接跑)

### 命令速查
- 单图描述: `python vision.py <图>`
- 多图对比: `python vision.py <原版> <改版> [更多图...]`
- 批量评审: `python vision.py --dir <目录> -a --report <输出.md>`
- 结构化输出: 加 `--json`（批量用 `--report 文件.json`）

### 验收标准 (审美评审 -a)
- ≥85 采纳 | 70~84 打回修改 | <70 大改或弃用

### 工作流
锐亚改图完成 → 义眼对比原版/改版 → 不达标打回 → 达标进采纳图
