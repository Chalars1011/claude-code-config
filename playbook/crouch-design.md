> 创建: 2026-07-23 | 更新: 2026-07-24 | 适用: Unity 6 | 类型: 设计决策记录

# 下蹲系统设计

## 最终方案（2026-07-23 收敛）

### Animator 结构
```
根层 Flat 状态:
  Crouch_Down (0.33s, 不循环) → exitTime=1 → Crouch_Hold
  Crouch_Hold (0.02s, 循环)    → IsXiaDun=false → Crouch_Up
  Crouch_Up (0.5s, 不循环)     → exitTime=1 → EXIT → Idel
```
入口: Idel/Run/RunStart/RunStop → Crouch_Down [CrouchDown Trigger]

### 代码
```csharp
bool keyDown = _input.Move.y < -0.4f;
isXiaDun = keyDown;
_anim.SetBool("IsXiaDun", isXiaDun); // 每帧!

if (keyDown && !_wasCrouching) { _anim.SetTrigger("CrouchDown"); _move.SetCrouch(true); }
if (!keyDown && _wasCrouching) { _move.SetCrouch(false); }
_wasCrouching = keyDown;
```

### 碰撞体
顶部缩一半，底部固定不动。不补偿 Y 位置（重力自然会拉回来）。

### 为什么不用子状态机
Unity 6 下 sub-SM Entry + Bool 每帧重入 → 动画抽搐。
钉墙(DingQiang)/攀爬(PanPa) 用的 AnyState+Trigger 模式稳定。

### 走过的弯路（按时间顺序）
1. Idel→EXIT[IsXiaDun] + subSM Entry → 根SM振荡
2. Idel→Player_XiaDun(直接连线) + subSM Entry → 两股力量争夺
3. AnyState→Player_XiaDun[IsXiaDun=Bool] → 每帧重入
4. 子SM Entry 改 CrouchDown Trigger → Trigger不在同一层无效
5. _anim.Play() 手动切 → 与Animator状态机打架
6. ✅ Flat 状态 + Trigger 入口 + Bool 出口（最终方案）

来源: 神之亵渎项目 2026-07-23（历时2.5小时，试了10+种方案）
