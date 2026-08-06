#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""选人界面·噬影立绘黑暗版：当前 PCK 基底 + 只替换 characterselect_silent ctex + 16 对齐"""
import hashlib
import io
import os
import shutil
import struct
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
from PIL import Image

SRC_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"
ALIGN = 16
TEXCONV = r"C:/Users/13040/.claude/art/tools/texconv.exe"

# 噬影选人立绘 ctex（Spine 图集，BC3/s3tc）
CHAR_TARGET = ".godot/imported/characterselect_silent.png-befe05e5b152d0e2459d112ea0b26595.s3tc.ctex"
CHAR_PNG = r"D:/泯灭之塔/采纳图/选人/立绘_silent_黑暗版v2_大胆.png"


def make_char_texture(orig_ctex, png):
    """重编码：保留 GST2 头 36B + 扩展头 16B，替换 BC3 数据"""
    w = struct.unpack("<I", orig_ctex[8:12])[0]
    h = struct.unpack("<I", orig_ctex[12:16])[0]
    need = ((w + 3) // 4) * ((h + 3) // 4) * 16
    ext_head = orig_ctex[36:52]
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_cs_tmp.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_cs_out"
    os.makedirs(tmp_dir, exist_ok=True)
    im = Image.open(png).convert("RGBA")
    bw, bh = (im.width + 3) // 4 * 4, (im.height + 3) // 4 * 4
    if im.size != (bw, bh):
        canvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        canvas.paste(im, (0, 0))
        im = canvas
    im.save(tmp_png)
    r = subprocess.run([TEXCONV, "-f", "BC3_UNORM", "-m", "1", "-y", "-o", tmp_dir, tmp_png],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"texconv: {r.stdout[-300:]}"
    with open(os.path.join(tmp_dir, "_cs_tmp.dds"), "rb") as f:
        dds = f.read()
    hdr_len = 148 if dds[84:88] == b"DX10" else 128
    encoded = dds[hdr_len:]
    assert len(encoded) == need, f"长度 {len(encoded)} != {need}"
    # 尾部 padding：原 ctex 数据之后可能还有 16B，取原文件同长
    tail = orig_ctex[52 + need:]
    return orig_ctex[:36] + ext_head + encoded + tail


def main():
    with open(SRC_PCK, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    base = struct.unpack("<Q", hdr[24:32])[0]
    with open(SRC_PCK, "rb") as f:
        f.seek(dir_off)
        n = struct.unpack("<I", f.read(4))[0]
        entries = []
        changed = []
        for i in range(n):
            plen = struct.unpack("<I", f.read(4))[0]
            path = f.read(plen).decode("utf-8", errors="replace").rstrip("\x00")
            off = struct.unpack("<Q", f.read(8))[0]
            size = struct.unpack("<Q", f.read(8))[0]
            f.read(16)
            ef = struct.unpack("<I", f.read(4))[0]
            with open(SRC_PCK, "rb") as f2:
                f2.seek(base + off)
                data = f2.read(size)
            if path == CHAR_TARGET:
                data = make_char_texture(data, CHAR_PNG)
                changed.append(path)
                print(f"  🔄 噬影立绘: {path.split('/')[-1]}")
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))
    print(f"总条目: {len(entries)} | 已替换: {len(changed)}")
    assert len(changed) == 1, "替换数不对，中止！"

    out = open(OUT + ".rel", "wb")
    out.write(b"GDPC")
    out.write(struct.pack("<I", 3))
    out.write(struct.pack("<III", 4, 5, 1))
    out.write(struct.pack("<I", 2))
    bp = out.tell()
    out.write(struct.pack("<Q", 0))
    dp = out.tell()
    out.write(struct.pack("<Q", 0))
    while out.tell() % ALIGN != 0:
        out.write(b"\0")
    fstart = out.tell()
    offs = []
    for path, pbytes, ppl, data, ef in entries:
        offs.append(out.tell() - fstart)
        out.write(data)
    while out.tell() % ALIGN != 0:
        out.write(b"\0")
    dstart = out.tell()
    out.write(struct.pack("<I", len(entries)))
    for i, (path, pbytes, ppl, data, ef) in enumerate(entries):
        out.write(struct.pack("<I", ppl))
        out.write(pbytes)
        if len(pbytes) < ppl:
            out.write(b"\0" * (ppl - len(pbytes)))
        out.write(struct.pack("<Q", offs[i]))
        out.write(struct.pack("<Q", len(data)))
        out.write(hashlib.md5(data).digest())
        out.write(struct.pack("<I", ef))
    while out.tell() % ALIGN != 0:
        out.write(b"\0")
    out.seek(bp)
    out.write(struct.pack("<Q", fstart))
    out.seek(dp)
    out.write(struct.pack("<Q", dstart))
    out.close()

    shutil.copy2(OUT, OUT + ".bak_charselect_prev")
    shutil.move(OUT + ".rel", OUT)
    print(f"✅ 发布版已就位: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB)")


if __name__ == "__main__":
    main()
