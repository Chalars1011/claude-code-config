> 创建: 2026-07-24 | 更新: 2026-07-24 | 适用: Unity 6 | 类型: 版本敏感规则

# Unity Animator 避坑指南

## 1. BaseLayer weight=0
**症状**: 所有 Idle/Run/Jump 动画不播放
**原因**: Unity 6 升级或误操作导致 weight 归零
**修复**: SerializedObject 写入 m_DefaultWeight=1 (layers[0].defaultWeight= 不生效!)
```csharp
var so = new SerializedObject(ctrl);
so.FindProperty("m_AnimatorLayers").GetArrayElementAtIndex(0)
  .FindPropertyRelative("m_DefaultWeight").floatValue = 1f;
so.ApplyModifiedProperties();
```

## 2. 子状态机 Entry + Bool = 每帧重入振荡
**症状**: 动画抽搐、重头播放、卡不住
**原因**: Unity 6 下 sub-SM Entry 条件用 Bool(非Trigger) 会每帧重评估
**解决方案**: 
- 不用于状态机: 把状态搬到根层，用 flat states
- 入口用 Trigger(一次性)，不要用 Bool(每帧)
- 出口条件用 Bool 没问题

## 3. AnyState + Trigger vs AnyState + Bool
- Trigger: 发一次消失 → 稳定（DingQiang/PanPa/Items 都在用）
- Bool: 按住一直 true → AnyState 每帧尝试重入 → 必须配合 hasExitTime 或用代码控制

## 4. LayerMask 丢失
**症状**: 换组件后 groundLayer/starsLayer 全部为 0
**修复**: 从场景中自动检测（如 DiBan 的 layer），用 script-execute 批量修复 17 个场景

## 5. dodgeLayerName 配置错误
**症状**: gameObject.layer = -1 报错
**原因**: Config 里写的 "DodgeLayer" 但项目里实际层叫 "ShanBi"
**修复**: 改 Config SO + 代码加 Mathf.Max(0, NameToLayer(...)) 防御

来源: 神之亵渎项目 2026-07-23
