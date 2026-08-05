> 创建: 2026-07-24 | 更新: 2026-07-24 | 适用: Unity 6 | 类型: 版本敏感规则

# 动作游戏设计模式

## 互锁规则（代码驱动路线A）

```csharp
// 正确的互锁：检查其他动作的标志，不检查自己的
void OnAttack() {
    if(isDie || isSkillActive || isHurt || isDodging || isClimbing) return;
    // 不检查 isAttack！这样支持连打
    isAttack = true;
    rb.velocity = Vector2.zero;
    _anim.SetTrigger("attack");
}

// 技能同理
void OnSkill() {
    if(isDie || isAttack || isSkillActive || isHurt || isDodging) return;
    isSkillActive = true;
    _anim.SetTrigger("Skill_X");
}
```

## 移动门控
```csharp
bool blocked = isHurt || isAttack || isSkillActive || isDodging || isClimbing || isNailedToWall;
if (!blocked) _move.ApplyMove(input.x);
```

## Animator 动作参数
- canAttack / canShanBi / canRun → AnimDriver LateUpdate 同步
- IsXiaDun / IsAttack / IsClimbing / IsNailedToWall → FixedUpdate 直接设

## 业界参考
- 空洞骑士: 代码驱动，HeroController 为唯一权威
- Dead Cells: PlayerStateMachine 纯C# 驱动 Animator
- Celeste: Player.StateMachine，Animator 只做表现

来源: 神之亵渎项目 2026-07-23
