#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 云画笔 (Painter) — 云端 AI 生图/改图工具
================================================
调用阿里云百炼 Qwen-Image-3.0，文生图 + 图生图/编辑（1~3 张参考图）。

用法:
    python painter.py --text "描述" --out out.png           # 文生图
    python painter.py <图> "编辑指令" --out out.png          # 图生图/编辑（单图）
    python painter.py <图1> <图2> "指令" --out out.png       # 多参考图编辑
    python painter.py --text "..." --size "1024*1024" --seed 42
    python painter.py --list

配置:
    复用 ~/.claude/vision/config.json 的 api_key（同一个百炼账户）。
    模型: qwen-image-3.0-pro（旗舰）/ qwen-image-3.0（标准，平衡质量速度）

说明:
    - 图片可传本地路径（自动 base64）或公网 URL
    - 返回图片 URL 24 小时内有效，工具自动下载到 --out
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TOOL_VERSION = "1.0"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vision", "config.json")
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
RETRY_DELAYS = [2, 5, 10]

MODELS = {
    "qwen-image-3.0-pro": "旗舰版：质量优先，支持 T2I + I2I（1~3 参考图）",
    "qwen-image-3.0": "标准版：平衡质量与速度，支持 T2I + I2I",
}


def load_cfg():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ 找不到配置: {CONFIG_PATH}")
        print("   义眼的 config.json 不存在。请先配置 API Key。")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def to_data_url(src):
    """本地路径 → base64 data URL；http(s) URL 原样返回。"""
    if re.match(r"^https?://", src):
        return src
    if not os.path.exists(src):
        print(f"❌ 文件不存在: {src}")
        sys.exit(1)
    mime, _ = mimetypes.guess_type(src)
    if mime is None:
        mime = "image/png" if src.lower().endswith((".png",)) else "image/jpeg"
    with open(src, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def call_api(cfg, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg['api_key']}"},
    )
    last_err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            with urllib.request.urlopen(req, timeout=360) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429,) or e.code >= 500:
                if attempt < len(RETRY_DELAYS):
                    print(f"⚠️  HTTP {e.code}，{RETRY_DELAYS[attempt]}s 后重试...", file=sys.stderr)
                    time.sleep(RETRY_DELAYS[attempt])
                    last_err = f"HTTP {e.code}"
                    continue
            print(f"❌ API 请求失败 (HTTP {e.code}):")
            print(err_body[:800])
            if e.code == 401:
                print("   → API Key 无效，请检查 ~/.claude/vision/config.json")
            elif e.code == 400 and ("permission" in err_body.lower() or "not opened" in err_body.lower() or "开通" in err_body):
                print("   → 可能需要在百炼控制台开通 Qwen-Image 模型服务: bailian.console.aliyun.com")
            sys.exit(1)
        except Exception as e:
            if attempt < len(RETRY_DELAYS):
                print(f"⚠️  网络异常 ({e})，{RETRY_DELAYS[attempt]}s 后重试...", file=sys.stderr)
                time.sleep(RETRY_DELAYS[attempt])
                last_err = str(e)
                continue
            print(f"❌ 请求异常（已重试 {len(RETRY_DELAYS)} 次）: {last_err}")
            sys.exit(1)


def download(url, out_path):
    print(f"⬇️  下载生成图 → {out_path}")
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
    with open(out_path, "wb") as f:
        f.write(data)
    size = len(data) / 1024
    print(f"✅ 已保存 ({size:.0f} KB): {out_path}")


def main():
    parser = argparse.ArgumentParser(description="🎨 云画笔 — 云端生图/改图 v" + TOOL_VERSION)
    parser.add_argument("images", nargs="*", help="参考图路径或 URL（1~3 张 = 图生图/编辑）")
    parser.add_argument("--text", default=None, help="文生图描述（无参考图时必填）或与编辑指令合并")
    parser.add_argument("--out", default=None, help="输出图片路径（必填）")
    parser.add_argument("--size", default=None, help='输出尺寸，如 "1024*1024"（默认模型自动推荐）')
    parser.add_argument("--negative", default=None, help="负面提示词")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（复现用）")
    parser.add_argument("--model", default="qwen-image-3.0-pro", choices=list(MODELS.keys()))
    parser.add_argument("--prompt-extend", action="store_true", help="启用智能 prompt 扩写（默认关闭，改图时保持指令精确）")
    parser.add_argument("--list", action="store_true", help="列出可用模型")
    args = parser.parse_args()

    if args.list:
        print("可用模型:")
        for k, v in MODELS.items():
            print(f"  - {k}: {v}")
        return

    if not args.out:
        print("❌ 必须指定 --out 输出路径")
        parser.print_help()
        sys.exit(1)

    cfg = load_cfg()

    # 位置参数智能识别：存在的文件/URL → 参考图；其他文本 → 编辑指令
    refs = []
    instruction = args.text or ""
    for img in args.images:
        if re.match(r"^https?://", img) or os.path.exists(img):
            refs.append(img)
        elif not instruction:
            instruction = img
        else:
            print(f"❌ 无法识别的参数（既不是文件也不是指令）: {img[:40]}")
            sys.exit(1)

    # 组装 content
    content = []
    for img in refs:
        content.append({"image": to_data_url(img)})
    if instruction:
        content.append({"text": instruction})

    if not content:
        print("❌ 请提供 --text 描述，或参考图+编辑指令（或两者都有）")
        sys.exit(1)

    # 注意：文档要求 content 里只有一个 text 对象。images 无 text 时不传 text。
    parameters = {}
    if args.negative:
        parameters["negative_prompt"] = args.negative
    if args.seed is not None:
        parameters["seed"] = args.seed
    if args.size:
        parameters["size"] = args.size
    if args.prompt_extend:
        parameters["prompt_extend"] = True

    payload = {
        "model": args.model,
        "input": {"messages": [{"role": "user", "content": content}]},
        "parameters": parameters,
    }

    mode = "图生图/编辑" if refs else "文生图"
    print(f"🎨 云画笔 ({args.model}) [{mode}] 请求中...", file=sys.stderr)
    print(f"   参考图: {len(refs)} 张 | 指令: {instruction[:60]}...", file=sys.stderr)

    data = call_api(cfg, payload)

    # 解析响应
    try:
        content_out = data["output"]["choices"][0]["message"]["content"]
        img_url = None
        for item in content_out:
            if isinstance(item, dict) and "image" in item:
                img_url = item["image"]
                break
        if not img_url:
            print("❌ 响应中没有图片 URL:")
            print(json.dumps(data, ensure_ascii=False)[:800])
            sys.exit(1)
    except (KeyError, IndexError, TypeError):
        print("❌ 响应解析失败:")
        print(json.dumps(data, ensure_ascii=False)[:800])
        sys.exit(1)

    usage = data.get("usage", {})
    print(f"   usage: {usage}", file=sys.stderr)
    download(img_url, args.out)


if __name__ == "__main__":
    main()
