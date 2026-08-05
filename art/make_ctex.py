#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧩 make_ctex — 把 PNG 打包成 Godot 4.5 的 .ctex 纹理（WebP 内嵌格式）
================================================
原理: ctex = [原文件头 160 字节, 含 GST2 头] + [RIFF/WEBP 数据]
      RIFF size / VP8L size 字段随新数据长度更新。

用法:
    python make_ctex.py <原.ctex> <新.png> <输出.ctex> [尺寸W x 尺寸H]
    # 不指定尺寸则用原 ctex 的宽高
"""

import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HEADER_KEEP = 160  # GST2 头 + 前置资源头，保留原样


def read_ctex_header(src):
    with open(src, "rb") as f:
        data = f.read(HEADER_KEEP)
    assert len(data) == HEADER_KEEP, "ctex 文件小于 160 字节"
    # 校验特征
    gst2 = data.find(b"GST2")
    assert gst2 >= 0, "不是有效的 GST2 ctex"
    return data


def make_ctex(src_ctex, src_png, out_ctex, target_size=None):
    from PIL import Image

    header = read_ctex_header(src_ctex)

    # 读取原尺寸（GST2 头内 w/h：偏移 104+8=112 / 116）
    if target_size is None:
        orig_w = struct.unpack("<I", header[112:116])[0]
        orig_h = struct.unpack("<I", header[116:120])[0]
        target_size = (orig_w, orig_h)
        print(f"  目标尺寸(原): {orig_w}x{orig_h}")

    im = Image.open(src_png).convert("RGBA")
    if im.size != target_size:
        print(f"  调整尺寸: {im.size} -> {target_size}")
        im = im.resize(target_size, Image.LANCZOS)

    # 无损 WebP (VP8L) —— 与 Godot 内嵌格式一致
    import io
    buf = io.BytesIO()
    im.save(buf, format="WEBP", lossless=True, quality=100, method=6)
    webp = buf.getvalue()
    print(f"  WebP 数据: {len(webp)} 字节")

    # 校验 WebP 结构: RIFF(size) WEBP + chunk
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP", "Pillow 输出的不是标准 RIFF/WEBP"
    riff_size = len(webp) - 8

    # 组装新 ctex：原头 + 新 RIFF 数据
    new_ctex = header + webp

    # 更新 GST2 头内疑似 datasize 字段（原值 = 原 RIFF size + 8 或 +16，扫描替换）
    with open(src_ctex, "rb") as f:
        orig = f.read()
    orig_riff_size = struct.unpack("<I", orig[164:168])[0]
    orig_webp_len = orig_riff_size + 8
    # 扫描 GST2 头(104~160) 内等于 orig_webp_len 的字段并更新
    updated = 0
    for pos in range(104, HEADER_KEEP - 3):
        v = struct.unpack("<I", orig[pos:pos + 4])[0]
        if v == orig_webp_len:
            new_ctex = new_ctex[:pos] + struct.pack("<I", len(webp)) + new_ctex[pos + 4:]
            updated += 1
    print(f"  GST2 头 datasize 字段更新: {updated} 处")

    with open(out_ctex, "wb") as f:
        f.write(new_ctex)
    print(f"  ✅ 输出: {out_ctex} ({len(new_ctex)} 字节)")
    return out_ctex


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src_ctex, src_png, out_ctex = sys.argv[1], sys.argv[2], sys.argv[3]
    target = None
    if len(sys.argv) >= 6:
        target = (int(sys.argv[4]), int(sys.argv[5]))
    make_ctex(src_ctex, src_png, out_ctex, target)
