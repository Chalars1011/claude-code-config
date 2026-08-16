> 创建: 2026-08-16 | 更新: 2026-08-16 | 类型: 工作流

# HTML 游戏 headless 自检与交付

> 场景：给查尔斯做 HTML 游戏（方块世界 v2 这类硬活）。验收口径 = 离线双击能跑 + 体感密度。
> 本次 1 小时 14 分交付满配版，靠的就是这套"数据后门 + 截图 + 像素复核"自检链。

## 核心结论

1. **headless 下 rAF 被严重节流**（虚拟时间 10-14 秒只跑 5-14 帧）。物理/移动/AI 的动态行为测不了——**只测渲染与数据正确性**，动态逻辑靠代码 review + 真机验收。
2. **vision 分析截图频繁误判**：把正常的第一人称像素风画面读成"渲染崩溃/穿模"，把调试水印读成编造的版本号（"MINECRAFT 1.20.1"）。**关键结论一律用 PIL 像素统计复核**，不要信 vision 的定性描述。
3. **dump-dom 读水印比 vision OCR 靠谱**：水印写进 DOM（display:block 的 div），`--dump-dom` + grep 直接拿文本。vision OCR 要放大 4 倍裁图才勉强可读。

## 自检基建（写进 index.html / game.js）

```js
// 1. 错误横幅：window.onerror → 红条 div（file:// 下只能拿到 "Script error. @:0"，但能知道"有没有崩"）
// 2. 调试水印：WM(text) 写 div#watermark，截图右上角可见
// 3. 后门参数（QUERY 解析 location.search）：
//    ?shot=1      俯瞰全景截图（相机拉到高空）
//    ?walk=1      第一人称自动前进 + 玩家状态水印
//    ?monster=1   夜晚直刷怪 + 斜视角（billboard 生物俯视不可见！必须斜视）
//    ?torch=1     夜晚放火把 + 看光圈
//    ?inv=1       自动开背包/工作台 UI
//    ?save=1      触发存档 + 回读长度水印
//    ?fresh=1     清档（防测试脏档污染）
// 4. 水印打点时机：init 里同步打一次（rAF 不可靠），loop 里 frames>=5 或 performance.now()>1200 兜底打一次
```

## 截图命令（Edge headless）

```bash
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
"$EDGE" --headless=new --disable-gpu --disable-sync --no-first-run \
  --screenshot="shots/x.png" --window-size=1280,720 --virtual-time-budget=12000 \
  "file:///D:/path/index.html?shot=1"
# dump-dom 版：--dump-dom 替换 --screenshot，grep watermark/errbar div
```

## 像素复核模板（vision 说"画面崩了"时）

```python
from PIL import Image
from collections import Counter
img = Image.open(path).convert("RGB")
c = Counter(img.getpixel((x,y)) for y in range(0,h,2) for x in range(0,w,2))
# 颜色分布规律 = 渲染正常（天空浅蓝/草地绿/树干棕）；大量无规律杂色 = 真崩
```

## 本场踩过的坑（写 JS 时直接避开）

1. **TypedArray 浮点索引返回 undefined**（不截断！）——循环变量用浮点起跳时 get/set 全部静默失效。地形生成/矿脉等用 `Math.floor` 起跳。
2. **对象键名 vs 数字索引**：纹理表 `{grass:[...]}` 被 `T[blockId]` 查——全查不到。表和查询用同一套键。
3. **UI 面板变量没初始化**（`let uiPanel = null` 后用 innerHTML）——打开即崩。声明时直接 getElementById。
4. **刷新函数自递归**：openInv 末尾调 refreshInvUI，refreshInvUI 又调 openInv。刷新函数里绝不回调打开函数。
5. **模块 init 条件跳过但 update 照跑**：update 开头判 `if(!camera) return` 双保险。
6. **String.fromCharCode.apply(null, 92160 长度 TypedArray) 栈溢出**——base64 分块（8192/块）。
7. **导出对象漏字段**：存档要 blocks/meta，模块没导出 → undefined.length 崩。
8. **billboard 生物俯视不可见**（plane 面向相机=平躺）：测试镜头必须斜视或平视。
9. **headless 里 setInterval 可能先于 rAF 跑完**：定时逻辑放 update 里按 dt 累计，别用 setInterval。
10. **右键"使用 vs 放置"顺序**：先 raycast 使用（工作台/熔炉/箱子/门/床），未命中才放置；吃东西用捕获阶段 stopImmediatePropagation 阻止放置链。

## 交付要点

- 打包 zip（index.html + three.min.js + js/），QQ 发文件 + 操作说明一段话（说人话，不列术语）。
- 自检结论诚实：headless 只验了渲染和数据，动态手感明确说"真机待验"。
- 查尔斯硬活验收 = 体感密度不是功能勾选：交付说明里点出体验链（出生第一夜：砍树→合成→天黑→怪围→火把守夜→日出），引导他按链走。
