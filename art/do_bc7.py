#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BC7 图集替换：解码 card_atlas_2 → 贴黑暗版区域 → BC7 编码 → 重建 ctex → 重打包"""

import hashlib
import os
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import imagecodecs
import numpy as np
from PIL import Image

CUR_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_bc7"
AL = 32
F = imagecodecs.BCN.FORMAT

# 目标：card_atlas_2（blade_dance 所在图集）
ATLAS_ENTRY = ".godot/imported/card_atlas_2.png-b839d300f2a53ba5863bc17e02165eea.bptc.ctex"
ATLAS_W, ATLAS_H = 3528, 3077
DATA_OFF = 44          # BC7 数据起点（实测）
TAIL_PAD = 8           # 尾部 padding
# 卡牌区域: (x, y, w, h) -> 黑暗版图
REPLACE = [
    ((253, 1345, 250, 190), r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png"),
]


def read_entries():
    with open(CUR_PCK, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    with open(CUR_PCK, "rb") as f:
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


def main():
    dir_off, entries = read_entries()
    # 1) 读原 ctex
    orig = None
    for pp, off, size in entries:
        if pp == ATLAS_ENTRY:
            with open(CUR_PCK, "rb") as f:
                f.seek(off)
                orig = f.read(size)
            break
    print(f"原 ctex: {len(orig)}B")
    head = orig[:DATA_OFF]
    tail = orig[-TAIL_PAD:]
    bw = (ATLAS_W + 3) // 4 * 4
    bh = (ATLAS_H + 3) // 4 * 4
    need = (ATLAS_W // 4) * ((ATLAS_H + 3) // 4) * 16
    print(f"尺寸 {ATLAS_W}x{ATLAS_H} 对齐 {bw}x{bh} BC7 {need}B")

    # 2) 解码
    img = imagecodecs.bcn_decode(orig[DATA_OFF:DATA_OFF + need], format=F.BC7, shape=(bh, bw, 4))
    print(f"解码: {img.shape}")

    # 3) 贴黑暗版
    for (x, y, w, h), png in REPLACE:
        dark = Image.open(png).convert("RGBA").resize((w, h), Image.LANCZOS)
        arr = np.array(dark)
        img[y:y + h, x:x + w] = arr
        print(f"  🔄 贴入 ({x},{y},{w}x{h}): {os.path.basename(png)}")

    # 4) BC7 编码（texconv）
    import subprocess
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_atlas2_edit.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_texconv_out"
    os.makedirs(tmp_dir, exist_ok=True)
    Image.fromarray(img).save(tmp_png)
    print("texconv BC7 编码中...")
    r = subprocess.run([
        r"C:/Users/13040/.claude/art/tools/texconv.exe",
        "-f", "BC7_UNORM", "-m", "1", "-y", "-o", tmp_dir, tmp_png,
    ], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print("texconv 失败:", r.stdout[-500:], r.stderr[-500:])
        sys.exit(1)
    dds_path = os.path.join(tmp_dir, "_atlas2_edit.dds")
    with open(dds_path, "rb") as f:
        dds = f.read()
    print(f"DDS: {len(dds)}B")
    # DDS 头：128B + (DX10 ? 20B)
    fourcc = dds[84:88]
    hdr_len = 148 if fourcc == b"DX10" else 128
    encoded = dds[hdr_len:]
    print(f"BC7 数据: {len(encoded)}B (需 {need}B)")
    if len(encoded) < need:
        encoded = encoded + b"\x00" * (need - len(encoded))
    elif len(encoded) > need:
        encoded = encoded[:need]

    # 5) 重建 ctex
    new_ctex = head + encoded + tail
    print(f"新 ctex: {len(new_ctex)}B (原 {len(orig)}B)")

    # 6) 重打包
    shutil.copy2(CUR_PCK, BAK)
    print(f"备份 -> {BAK}")
    f = open(CUR_PCK, "rb")
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
        if path == ATLAS_ENTRY:
            data = new_ctex
            print(f"  🔄 {path} ({sz}B -> {len(data)}B)")
        else:
            f2 = open(CUR_PCK, "rb")
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
