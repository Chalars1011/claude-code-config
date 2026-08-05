#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
👁️ 义眼 (Vision) — 让无视觉的 Agent 能"看"图片
================================================
把图片交给视觉模型，翻译成详细的结构化文字描述 / 审美评审。

用法:
    python vision.py <图片路径> [指令]                     # 单图描述
    python vision.py <图片路径> -a                          # 审美评审（打分+诊断）
    python vision.py <图1> <图2> [<图3> ...]                # 多图对比（自动识别）
    python vision.py --dir <目录> [-a] [--report 文件.md]   # 批量评审 + 报告
    python vision.py --dir <目录> --json                    # 批量评审 + JSON 报告
    python vision.py <图片> --json                          # 单图 JSON 输出
    python vision.py --list                                 # 列出可用 provider

配置:
    config.json 中设置 provider 和 api_key。

架构:
    统一入口 + provider 适配器，换模型只改 config.json 或 --provider。
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import struct
import sys
import time
import urllib.request
import urllib.error

# Windows 控制台 GBK 问题：强制 UTF-8 输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
TOOL_VERSION = "1.1"
MAX_TOKENS = 4096          # 审美评审输出量大，2048 会被截断
RETRY_DELAYS = [2, 5, 10]  # 429/5xx/网络错误时的退避重试

DEFAULT_PROMPT = (
    "请详细描述这张图片：1) 主体内容与人物/物体 2) 构图与视角 3) 整体色调与明暗 4) "
    "画风与质感（如暗黑/卡通/写实）5) 关键细节（服饰/武器/纹理/文字等）6) 画面氛围。"
    "用中文，按条目输出。"
)

COMPARE_PROMPT = (
    "请对比分析这 {n} 张图片（按传入顺序编号为 图1/图2/...）：\n"
    "1) 每张图单独一句话概括主体与画风\n"
    "2) 逐项横向对比：构图、色调、明暗层次、细节完整度、风格统一性\n"
    "3) 差异清单：图2及之后相对图1的具体变化（构图/色彩/质感）\n"
    "4) 评判：如果这是游戏美术的改图场景，哪张更适合游戏内使用？给出明确结论和理由。\n"
    "用中文，按条目输出，直接、严格、不客气。"
)

# 审美评审模式：rubric 制 + 风格自适应 + 项目调性基准
AESTHETIC_PROMPT = (
    "你是资深游戏美术总监。评审分两步：\n"
    "【第一步·风格识别】先判断这张图的风格类型（黑暗哥特/卡通赛璐璐/写实厚涂/像素/水彩等），"
    "用一句话说明，并声明你将按该风格的标准评审。\n"
    "【第二步·按风格评审】严格按识别出的风格的标准评，禁止拿其他风格的标准套评"
    "（例如：黑暗哥特风格的暗色调是特征，不是'明度不足'；卡通风平涂是特征，不是'缺层次'）。\n"
    "项目调性基准（最高优先级）：本图用于'泯灭之塔'——黑暗哥特风游戏，虚无主义+肉体恐怖+黑暗压抑。"
    "评审时先问：这张图是否服务于该调性？\n"
    "按以下结构输出：\n"
    "1) 风格识别与适用标准：什么风格，按什么标准评\n"
    "2) 氛围诊断（本项目最重要）：黑暗氛围是否到位？压抑/恐怖/虚无感渲染如何？"
    "是否'为暗而暗'（只有暗没有层次）？\n"
    "3) 色彩诊断：按风格评。黑暗哥特重点评：暗部是否有层次、主色调统一性、"
    "有无点缀色打破死板（不要求明亮）\n"
    "4) 构图诊断：视觉重心、主体辨识、动态引导（不要求'留白多'）\n"
    "5) 细节诊断：细节是否服务于氛围与叙事？材质是否可信（按风格）？\n"
    "6) 可读性：128px 小尺寸下主体轮廓是否可辨（游戏素材重点）\n"
    "7) 总评：必须用 '得分：XX/100' 格式输出（及格70，优秀85），列3个最致命问题，"
    "每个给具体修改方向（说人话，少术语）\n"
    "8) 一句话人话总结：大白话说这图行不行、哪舒服哪别扭，像美术同事口头意见\n"
    "直接、严格、不客气，但术语要少。"
)

PROVIDERS = {
    "qwen": {
        "name": "千问 Qwen3-VL",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3-vl-plus",
        "max_tokens": MAX_TOKENS,
    },
    # 未来可插拔：加一个 provider 条目即可，如
    # "zhipu": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4v-flash"},
    # "local": {"base_url": "http://127.0.0.1:8000/v1", "model": "Qwen2.5-VL-7B"},
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_image_info(path):
    """零依赖解析图片基本信息（PNG/JPEG/WebP/DDS 的宽高与格式），失败返回 None 字段不影响主流程。"""
    info = {"format": None, "width": None, "height": None}
    try:
        info["size_bytes"] = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(64)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            info["format"] = "PNG"
            w, h = struct.unpack(">II", head[16:24])
            info["width"], info["height"] = w, h
        elif head[:2] == b"\xff\xd8":
            info["format"] = "JPEG"
            w, h = _jpeg_size(head, path)
            info["width"], info["height"] = w, h
        elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            info["format"] = "WebP"
            w, h = _webp_size(head)
            info["width"], info["height"] = w, h
        elif head[:4] == b"DDS ":
            info["format"] = "DDS"
            info["width"] = struct.unpack("<I", head[16:20])[0]
            info["height"] = struct.unpack("<I", head[12:16])[0]
    except Exception:
        pass
    return info


def _jpeg_size(head, path):
    """JPEG 需要扫 SOF 段，读前 256KB 足够覆盖绝大多数情况。"""
    try:
        with open(path, "rb") as f:
            data = f.read(262144)
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h = struct.unpack(">H", data[i + 5:i + 7])[0]
                w = struct.unpack(">H", data[i + 7:i + 9])[0]
                return w, h
            if marker == 0xD8 or marker == 0xD9 or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg_len
    except Exception:
        pass
    return None, None


def _webp_size(head):
    """WebP: VP8X 可靠解析；VP8(有损)/VP8L(无损) 尽力而为。"""
    try:
        if head[12:16] == b"VP8X":
            w = struct.unpack("<I", head[24:28])[0] & 0xFFFFFF
            h = struct.unpack("<I", head[28:32])[0] & 0xFFFFFF
            return w + 1, h + 1
        if head[12:16] == b"VP8 ":
            w = struct.unpack("<H", head[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", head[28:30])[0] & 0x3FFF
            return w, h
        if head[12:16] == b"VP8L":
            b = struct.unpack("<I", head[21:25])[0]
            w = (b & 0x3FFF) + 1
            h = ((b >> 14) & 0x3FFF) + 1
            return w, h
    except Exception:
        pass
    return None, None


def image_to_base64(path):
    if not os.path.exists(path):
        print(f"❌ 图片不存在: {path}")
        sys.exit(1)
    mime, _ = mimetypes.guess_type(path)
    if mime is None:
        mime = "image/png" if path.lower().endswith((".png",)) else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def call_qwen(cfg, image_data_urls, prompt, max_tokens):
    api_key = cfg.get("api_key", "")
    if not api_key:
        print("❌ config.json 中缺少 api_key。请填入阿里云百炼的 API Key。")
        print("   获取: https://bailian.console.aliyun.com/ → API-KEY")
        sys.exit(1)
    provider_cfg = PROVIDERS[cfg.get("provider", "qwen")]
    model = cfg.get("model", provider_cfg["model"])
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": u}}
                for u in image_data_urls
            ] + [{"type": "text", "text": prompt}],
        }],
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        provider_cfg["base_url"] + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )

    # 指数退避重试：429 / 5xx / 网络异常
    last_err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429,) or e.code >= 500:
                if attempt < len(RETRY_DELAYS):
                    print(f"⚠️  HTTP {e.code}，{RETRY_DELAYS[attempt]}s 后重试 ({attempt+1}/{len(RETRY_DELAYS)})...", file=sys.stderr)
                    time.sleep(RETRY_DELAYS[attempt])
                    last_err = f"HTTP {e.code}"
                    continue
            print(f"❌ API 请求失败 (HTTP {e.code}):")
            print(body[:800])
            if e.code == 401:
                print("   → API Key 无效，请检查 config.json")
            elif e.code == 429:
                print("   → 触发限流或额度不足")
            sys.exit(1)
        except Exception as e:
            if attempt < len(RETRY_DELAYS):
                print(f"⚠️  网络异常 ({e})，{RETRY_DELAYS[attempt]}s 后重试...", file=sys.stderr)
                time.sleep(RETRY_DELAYS[attempt])
                last_err = str(e)
                continue
            print(f"❌ 请求异常（已重试 {len(RETRY_DELAYS)} 次）: {last_err}")
            sys.exit(1)


def extract_score(text):
    """从评审输出里提取分数：兼容 '58/100'、'58分'、'总评：58分' 等写法。"""
    m = re.search(r"(\d{1,3})\s*/\s*100", text)
    if m:
        return int(m.group(1))
    m = re.search(r"总评[：:\s]*(\d{1,3})\s*分", text)
    if m:
        return int(m.group(1))
    m = re.search(r"[（(]?\s*(\d{1,3})\s*分\s*[)）]?", text)
    if m:
        return int(m.group(1))
    return None


def fmt_size(n):
    if n is None:
        return "?"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.0f}KB"
    return f"{n}B"


def make_report(paths, results, mode, out_path, as_json=False):
    """results: [{path, info, text, score}]"""
    scored = [r for r in results if r.get("score") is not None]
    scored.sort(key=lambda r: r["score"], reverse=True)
    if as_json:
        report = {
            "tool": "vision", "version": TOOL_VERSION, "mode": mode,
            "total": len(paths), "ok": len(results), "failed": len(paths) - len(results),
            "items": [
                {"file": os.path.basename(r["path"]), "score": r.get("score"),
                 "info": {k: v for k, v in r.get("info", {}).items() if k != "size_bytes"},
                 "result": r["text"]}
                for r in results
            ],
        }
        text = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        lines = ["# 义眼批量评审报告", "",
                 f"- 工具版本: {TOOL_VERSION}", f"- 时间: {time.strftime('%Y-%m-%d %H:%M')}",
                 f"- 模式: {mode}", f"- 图片: {len(paths)} 张（成功 {len(results)} / 失败 {len(paths) - len(results)}）", ""]
        if scored:
            lines.append("## 排行（按分数）")
            lines.append("| 排名 | 文件 | 分数 |")
            lines.append("|------|------|------|")
            for i, r in enumerate(scored, 1):
                lines.append(f"| {i} | {os.path.basename(r['path'])} | {r['score']} |")
            lines.append("")
        for i, r in enumerate(results, 1):
            dims = f"{r['info']['width']}x{r['info']['height']}" if r["info"].get("width") else "?"
            lines.append(f"## {i}. {os.path.basename(r['path'])}（{fmt_size(r['info'].get('size_bytes'))}，{dims}）")
            if r.get("score") is not None:
                lines.append(f"**分数: {r['score']}**")
            lines.append("")
            lines.append(r["text"])
            lines.append("")
        text = "\n".join(lines)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"📄 报告已写入: {out_path}")
    else:
        print(text)


def main():
    parser = argparse.ArgumentParser(description="👁️ 义眼 — 图片描述/审美评审工具 v" + TOOL_VERSION)
    parser.add_argument("images", nargs="*", help="图片路径（多张 = 对比模式）")
    parser.add_argument("-a", "--aesthetic", action="store_true", help="审美评审模式（打分+诊断+修改建议）")
    parser.add_argument("--dir", default=None, help="批量评审目录下所有图片")
    parser.add_argument("--pattern", default=None, help="--dir 时的文件名过滤（正则，如 'png$'）")
    parser.add_argument("--report", default=None, help="报告输出路径（.md 或 .json，按扩展名识别格式）")
    parser.add_argument("--json", action="store_true", help="结构化 JSON 输出")
    parser.add_argument("--prompt", default=None, help="自定义完整 prompt")
    parser.add_argument("--provider", default="qwen", help="provider 名称")
    parser.add_argument("--list", action="store_true", help="列出可用 provider")
    args = parser.parse_args()

    if args.list:
        print("可用的 provider:")
        for k, v in PROVIDERS.items():
            print(f"  - {k}: {v['name']} (model: {v['model']})")
        print("模式: 默认描述 | -a/--aesthetic 审美评审 | 多图自动对比 | --dir 批量评审")
        return

    cfg = load_config()
    if args.provider not in PROVIDERS:
        print(f"❌ 未知 provider: {args.provider}，可用: {list(PROVIDERS.keys())}")
        sys.exit(1)

    # ---------- 批量模式 ----------
    if args.dir:
        if not os.path.isdir(args.dir):
            print(f"❌ 目录不存在: {args.dir}")
            sys.exit(1)
        pat = re.compile(args.pattern) if args.pattern else None
        paths = []
        for name in sorted(os.listdir(args.dir)):
            p = os.path.join(args.dir, name)
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".dds"):
                continue
            if pat and not pat.search(name):
                continue
            paths.append(p)
        if not paths:
            print("❌ 目录里没有可评审的图片")
            sys.exit(1)
        mode = "审美评审" if args.aesthetic else "描述"
        print(f"👁️ 义眼 批量[{mode}] 共 {len(paths)} 张，开始逐个评审...", file=sys.stderr)
        results = []
        for i, p in enumerate(paths, 1):
            info = get_image_info(p)
            dims = f"{info['width']}x{info['height']}" if info.get("width") else "?"
            print(f"  [{i}/{len(paths)}] {os.path.basename(p)} ({fmt_size(info.get('size_bytes'))}，{dims}) ...", file=sys.stderr)
            prompt = args.prompt or (AESTHETIC_PROMPT if args.aesthetic else DEFAULT_PROMPT)
            try:
                text = call_qwen(cfg, [image_to_base64(p)], prompt, PROVIDERS[args.provider]["max_tokens"])
                score = extract_score(text) if args.aesthetic else None
                results.append({"path": p, "info": info, "text": text, "score": score})
            except SystemExit:
                results.append({"path": p, "info": info, "text": "❌ 评审失败", "score": None})
                print(f"  [!!] {os.path.basename(p)} 评审失败，继续下一张", file=sys.stderr)
        out = args.report
        if out is None:
            out = os.path.join(args.dir, "vision_report.md" if not args.json else "vision_report.json")
        make_report(paths, results, mode, out, as_json=(args.json or (out and out.endswith(".json"))))
        return

    # ---------- 单图 / 多图对比模式 ----------
    if not args.images:
        parser.print_help()
        return

    # 位置参数智能识别：存在的文件/URL → 图片；其他文本 → 自定义指令
    refs = []
    extra_prompt = ""
    for img in args.images:
        if re.match(r"^https?://", img) or os.path.exists(img):
            refs.append(img)
        elif not extra_prompt:
            extra_prompt = img
        else:
            print(f"❌ 无法识别的参数（既不是文件也不是指令）: {img[:40]}")
            sys.exit(1)
    if extra_prompt and not args.prompt:
        args.prompt = extra_prompt
    paths = refs
    for p in paths:
        if not os.path.exists(p):
            print(f"❌ 图片不存在: {p}")
            sys.exit(1)

    infos = [get_image_info(p) for p in paths]
    for p, info in zip(paths, infos):
        dims = f"{info['width']}x{info['height']}" if info.get("width") else "?"
        print(f"  图片: {p}（{fmt_size(info.get('size_bytes'))}，{dims}）", file=sys.stderr)

    if args.aesthetic and len(paths) > 1:
        print("❌ 审美评审 (-a) 是单图模式。多图对比请去掉 -a；批量评审用 --dir -a。")
        sys.exit(1)

    if args.prompt:
        prompt = args.prompt
    elif args.aesthetic:
        prompt = AESTHETIC_PROMPT
    elif len(paths) > 1:
        prompt = COMPARE_PROMPT.format(n=len(paths))
    else:
        prompt = DEFAULT_PROMPT

    mode = "审美评审" if args.aesthetic else ("对比" if len(paths) > 1 else "描述")
    print(f"👁️ 义眼 ({PROVIDERS[args.provider]['name']}) [{mode}] 正在看图: {', '.join(os.path.basename(p) for p in paths)} ...", file=sys.stderr)
    result = call_qwen(cfg, [image_to_base64(p) for p in paths], prompt, PROVIDERS[args.provider]["max_tokens"])

    if args.json:
        out = {
            "tool": "vision", "version": TOOL_VERSION, "mode": mode,
            "prompt": prompt, "images": [
                {"file": os.path.basename(p), "path": p,
                 "info": {k: v for k, v in info.items() if k != "size_bytes"}}
                for p, info in zip(paths, infos)
            ],
            "result": result,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
