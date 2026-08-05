> 创建: 2026-07-24 | 更新: 2026-07-25 | 类型: 版本敏感规则

# 安全重构流程

## 触发条件
替换现有系统、大改架构时执行。此规则优先级最高——任何重构必须走全部 6 阶段, 不可跳步。

## 六阶段（每步必须打标记）

### Phase 0: 预检
run project-audit + scene-health-check
✅ P0/6: [audit 结果]

### Phase 1: 旧新对照表
code-diff-audit: 列出旧系统所有 public API → 新系统逐项确认 → 拿给用户看
✅ P1/6: [缺失项清单, 等用户确认]

### Phase 2: 备份
.cs → .cs.bak
✅ P2/6: done

### Phase 3: 替换文件
删除旧文件 → 写入新文件 → assets-refresh → 0 编译错误
✅ P3/6: [编译状态]

### Phase 4: 单场景接线
当前场景: 删旧组件 → 加新组件 → 自动赋值子引用 + LayerMask
✅ P4/6: [接线状态]

### Phase 5: 17 场景批量同步
BatchAutoWire: 打开每个场景 → 执行接线 → 保存
✅ P5/6: [批处理结果]

### Phase 6: 验证 + 暴力测试
project-audit → console 检查 → 用户暴力测试
✅ P6/6: [audit 结果, 已知问题]
