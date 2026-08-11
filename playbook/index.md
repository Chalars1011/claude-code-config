> 创建: 2026-07-24 | 更新: 2026-08-11 | 类型: 索引

# Playbook Index

> 总文件: 16 | ~/.claude/rules: 4 | 更新时间: 2026-08-11

## 保鲜规则（2026-08-10 立）
- 每个 playbook 文件头部带 `更新:` 日期
- **每周沉淀时（周日 cron）检查一遍**：距今超 30 天未更新的文件 → 标记"待验证"；工具/路径/API 变了 → 当场更新
- 被标记"已过时"的条目，使用时先验证再照做，防止旧流程带偏

## 快速查找
| 关键词 | 文件 | 一句话 |
|--------|------|--------|
| 互锁、攻击、移动、动作逻辑 | action-game-patterns.md | 代码驱动路线A |
| 蹲下、碰撞体、子状态机、Trigger | crouch-design.md | 10+方案演进史 |
| Animator、weight、LayerMask、升级 | unity-animator-pitfalls.md | Unity 6五大坑 |
| Hermes、QQ、onebot、NapCat、补丁 | hermes-qq-integration.md | QQ接入Hermes全流程+6坑 |
| NapCat、OneBot、桥接、token、免扫码 | napcat-qq-bridge.md | QQ机器人接入基础 |
| DeepSeek、兼容层、hook失效、--mcp-config、headless | claude-code-deepseek-compat.md | 工作站兼容层踩坑 |
| GBK、UTF-8、MSYS、路径转换、Python环境、npm更新、allowScripts | windows-python-pitfalls.md | Windows+Python坑合集（含npm全局包更新） |
| gateway、cron、hooks、回流、approvals、skills | hermes-agent-basics.md | Hermes基础机制 |
| 五层记忆、注入精简、Lost in the Middle、MemGPT | memory-core-principles.md | 记忆核心设计原则 |
| PCK、卡牌图、16字节对齐、STS2、义眼验收 | sts2-card-pipeline.md | 泯灭之塔卡牌图改造全链路 |
| gateway重启、onebot、崩溃排查、运维 | hermes-gateway-ops.md | Gateway运维手册（三步重启） |
| 更新、升级、补丁、stash、重打补丁、回滚 | hermes-update-sop.md | Hermes更新避坑SOP（等tag→全停→备份→stash→更新→重打→验证） |
| 记忆搭建、五层结构、hook、cron、归档 | memory-system-build.md | 记忆系统搭建流程 |
| 团队、角色、sub-agent、伊莉丝、HARD RULE | agent-team-setup.md | AI团队搭建（五角色） |
| scene_bus、多场景、互通、事件总线 | scene-bus-sync.md | 三场景互通搭建 |
| 义眼、画笔、生图、验收、角色一致性 | vision-painter-pipeline.md | 画笔义眼闭环 |

## 工作流规则
| 场景 | 规则文件 |
|------|------|
| 新功能开发 | rules/01-new-feature.md (5步) |
| Bug修复 | rules/02-bug-fix.md (4步) |
| 重构 | rules/03-refactor.md (6阶段) |
| 会话收尾+启动 | rules/04-session-checklist.md |

## 搜索指南
1. 先扫本文件（10秒读完）
2. 命中关键词 → 打开对应文件
3. 新经验 → 更新本索引 + 新建文件
4. 遇到具体任务类型 → 先用对应的 rules/ 流程
