#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单卡全流程：改 ctex + 改 tres（修复 uid bug：gd_resource uid 保留原值）"""

import hashlib
import io
import os
import re
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image

PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_strike"
AL = 32

# 卡牌配置: 卡名 -> (黑暗版png, 目标尺寸)
CARD = "strike_silent"
DARK_PNG = r"D:/泯灭之塔/采纳图/卡牌/strike_silent_黑暗版.png"


def read_entries():
    with open(PCK, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    with open(PCK, "rb") as f:
        f.seek(dir_off)
        n = struct.unpack("<I", f.read(4))[0]
        entries = []
        for i in range(n):
            plen = struct.unpack("<I", f.read(4))[0]
            path = f.read(plen).decode("utf-8", errors="replace").rstrip("\x00")
            off = struct.unpack("<Q", f.read(8))[0]
            size = struct.unpack("<Q", f.read(8))[0]
            f.read(16)
            f.read(4)
            entries.append((path, off, size))
    return dir_off, entries


def get_data(entries, path):
    for pp, off, size in entries:
        if pp == path:
            with open(PCK, "rb") as f:
                f.seek(off)
                return f.read(size)
    return None


def make_ctex(orig_ctex, dark_png, target_w, target_h):
    """原 ctex 头 + 新 WebP 数据"""
    header = orig_ctex[:160]
    im = Image.open(dark_png).convert("RGBA")
    if im.size != (target_w, target_h):
        im = im.resize((target_w, target_h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", lossless=True, quality=100, method=6)
    webp = buf.getvalue()
    new_ctex = header + webp
    # 更新 GST2 头 datasize 字段
    orig_riff = struct.unpack("<I", orig_ctex[164:168])[0]
    orig_webp_len = orig_riff + 8
    for pos in range(104, 160 - 3):
        v = struct.unpack("<I", orig_ctex[pos:pos + 4])[0]
        if v == orig_webp_len:
            new_ctex = new_ctex[:pos] + struct.pack("<I", len(webp)) + new_ctex[pos + 4:]
    return new_ctex


def make_tres(orig_tres, portrait_uid, portrait_path):
    """新 tres：gd_resource uid 保留原值；ext_resource 引用 portrait"""
    # 提取原 gd_resource uid
    m = re.search(rb'uid="(uid://[^"]+)"', orig_tres)
    orig_uid = m.group(1).decode() if m else "uid://unknown"
    n = orig_tres.find(b"\x00")
    tail_len = n
    nulls = orig_tres.count(b"\x00")
    full = (
        f'[gd_resource type="AtlasTexture" load_steps=2 format=3 uid="{orig_uid}"]\n\n'
        f'[ext_resource type="Texture2D" path="{portrait_path}" uid="{portrait_uid}" id="1"]\n\n'
        "[resource]\n"
        'atlas = ExtResource("1")\n'
        "region = Rect2(0, 0, 1000, 760)\n"
    ).encode("utf-8")
    new_tail = full[-tail_len:]
    new_head = full[:-tail_len]
    return new_tail + b"\x00" * nulls + new_head


def main():
    dir_off, entries = read_entries()
    print(f"条目: {len(entries)}")

    # 1) portrait uid
    imp = get_data(entries, f"images/packed/card_portraits/silent/{CARD}.png.import")
    m = re.search(rb'uid="(uid://[^"]+)"', imp)
    portrait_uid = m.group(1).decode()
    print(f"{CARD} portrait uid: {portrait_uid}")

    # 2) 原 ctex（portrait 大图）
    ctex_path = None
    for path, off, size in entries:
        if path.startswith(f".godot/imported/{CARD}.png-") and path.endswith(".ctex"):
            ctex_path = path
            break
    orig_ctex = get_data(entries, ctex_path)
    w = struct.unpack("<I", orig_ctex[112:116])[0]
    h = struct.unpack("<I", orig_ctex[116:120])[0]
    print(f"原 ctex: {ctex_path} ({len(orig_ctex)}B, {w}x{h})")

    # 3) 新 ctex
    new_ctex = make_ctex(orig_ctex, DARK_PNG, w, h)
    print(f"新 ctex: {len(new_ctex)}B")

    # 4) 新 tres
    tres_path = f"images/atlases/card_atlas.sprites/silent/{CARD}.tres"
    orig_tres = get_data(entries, tres_path)
    new_tres = make_tres(orig_tres, portrait_uid,
                         f"res://images/packed/card_portraits/silent/{CARD}.png")
    print(f"新 tres: {len(new_tres)}B (原 {len(orig_tres)}B)")

    # 5) 重打包
    shutil.copy2(PCK, BAK)
    print(f"备份 -> {BAK}")
    repl = {ctex_path: new_ctex, tres_path: new_tres}
    f = open(PCK, "rb")
    magic = f.read(4)
    fmt_ver = struct.unpack("<I", f.read(4))[0]
    gm, gmi, gp = struct.unpack("<III", f.read(12))
    flags = struct.unpack("<I", f.read(4))[0]
    old_base = struct.unpack("<Q", f.read(8))[0]
    f.seek(dir_off)
    fc = struct.unpack("<I", f.read(4))[0]
    out_entries = []
    for i in range(fc):
        pl = struct.unpack("<I", f.read(4))[0]
        pb = f.read(pl)
        path = pb.decode("utf-8", errors="replace").rstrip("\x00")
        off = struct.unpack("<Q", f.read(8))[0]
        sz = struct.unpack("<Q", f.read(8))[0]
        f.read(16)
        ef = struct.unpack("<I", f.read(4))[0]
        if path in repl:
            data = repl[path]
            print(f"  🔄 {path} ({sz}B -> {len(data)}B)")
        else:
            f2 = open(PCK, "rb")
            f2.seek(old_base + off)
            data = f2.read(sz)
            f2.close()
        pbytes = path.encode("utf-8")
        ppl = len(pbytes)
        while ppl % 4 != 0:
            ppl += 1
        out_entries.append((path, pbytes, ppl, data, ef))
    f.close()

    out = open(OUT, "wb")
    out.write(magic)
    out.write(struct.pack("<I", fmt_ver))
    out.write(struct.pack("<III", gm, gmi, gp))
    out.write(struct.pack("<I", flags))
    bp = out.tell()
    out.write(struct.pack("<Q", 0))
    dp = out.tell()
    out.write(struct.pack("<Q", 0))
    for _ in range(16):
        out.write(struct.pack("<I", 0))
    fstart = out.tell()
    offs = []
    for path, pbytes, ppl, data, ef in out_entries:
        while out.tell() % AL != 0:
            out.write(b"\0")
        offs.append(out.tell() - fstart)
        out.write(data)
    while out.tell() % AL != 0:
        out.write(b"\0")
    dstart = out.tell()
    out.write(struct.pack("<I", len(out_entries)))
    for i, (path, pbytes, ppl, data, ef) in enumerate(out_entries):
        out.write(struct.pack("<I", ppl))
        out.write(pbytes)
        if len(pbytes) < ppl:
            out.write(b"\0" * (ppl - len(pbytes)))
        out.write(struct.pack("<Q", offs[i]))
        out.write(struct.pack("<Q", len(data)))
        out.write(hashlib.md5(data).digest())
        out.write(struct.pack("<I", ef))
    while out.tell() % AL != 0:
        out.write(b"\0")
    out.seek(bp)
    out.write(struct.pack("<Q", fstart))
    out.seek(dp)
    out.write(struct.pack("<Q", dstart))
    out.close()
    print(f"\n✅ 完成: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB)")


if __name__ == "__main__":
    main()
