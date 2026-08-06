#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主菜单背景黑暗化：bottom(BC7) + top(BC3) Pillow 调暗 → texconv 编码 → 16对齐重打包"""

import hashlib
import os
import shutil
import struct
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image, ImageEnhance

SRC_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"
ALIGN = 16
TEXCONV = r"C:/Users/13040/.claude/art/tools/texconv.exe"
TMP = r"D:/泯灭之塔/原版素材/卡牌/_menu_tmp"
os.makedirs(TMP, exist_ok=True)

# 条目: (PCK路径, 素材PNG, texconv格式) —— 素材为画笔重绘的黑暗版
TARGETS = [
    (".godot/imported/main_menu_bottom.png-d7d4537c3ec56f5f30144a17c9b31f7f.bptc.ctex",
     r"D:/泯灭之塔/采纳图/背景/bottom_黑暗版_v2_full.png", "BC7_UNORM"),
    (".godot/imported/main_menu_top.png-95e0772be3a5c9df8ceb498ad8b60bdb.s3tc.ctex",
     r"D:/泯灭之塔/采纳图/背景/top_黑暗版_full.png", "BC3_UNORM"),
]


def darken(png_path, out_png):
    """画笔版素材直接使用（已黑暗化），仅复制"""
    im = Image.open(png_path).convert("RGBA")
    print(f"  素材: {im.size}")
    im.save(out_png)


def rebuild_ctex(orig_ctex, dark_png, fmt_name):
    """GST2头 + texconv编码数据 + 原尾部"""
    w = struct.unpack("<I", orig_ctex[8:12])[0]
    h = struct.unpack("<I", orig_ctex[12:16])[0]
    need = ((w + 3) // 4) * ((h + 3) // 4) * 16
    tmp_png = os.path.join(TMP, "menu_dark.png")
    darken(dark_png, tmp_png)
    # 对齐尺寸（texconv 要求 4 倍数）
    tmp_png_a = os.path.join(TMP, "menu_dark_aligned.png")
    im = Image.open(tmp_png)
    bw, bh = (im.width + 3) // 4 * 4, (im.height + 3) // 4 * 4
    if im.size != (bw, bh):
        im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        im.paste(Image.open(tmp_png), (0, 0))
    im.save(tmp_png_a)
    r = subprocess.run([TEXCONV, "-f", fmt_name, "-m", "1", "-y", "-o", TMP, tmp_png_a],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"texconv: {r.stdout[-300:]}"
    dds_name = os.path.basename(tmp_png_a).replace(".png", ".dds")
    with open(os.path.join(TMP, dds_name), "rb") as f:
        dds = f.read()
    hdr_len = 148 if dds[84:88] == b"DX10" else 128
    encoded = dds[hdr_len:]
    print(f"  {fmt_name}: {len(encoded)}B (需 {need}B)")
    assert len(encoded) == need, "数据长度不匹配"
    tail = orig_ctex[36 + need:]
    return orig_ctex[:36] + encoded + tail


def main():
    shutil.copy2(SRC_PCK, SRC_PCK + ".bak_menu")
    with open(SRC_PCK, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    base = struct.unpack("<Q", hdr[24:32])[0]
    with open(SRC_PCK, "rb") as f:
        f.seek(dir_off)
        n = struct.unpack("<I", f.read(4))[0]
        entries = []
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
            for target, png, fmt in TARGETS:
                if path == target:
                    data = rebuild_ctex(data, png, fmt)
                    print(f"  🔄 {path.split('/')[-1]}")
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))

    out = open(OUT + ".mbg", "wb")
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
    shutil.move(OUT + ".mbg", OUT)
    print(f"✅ 主菜单背景黑暗化版已就位 ({os.path.getsize(OUT)/1024/1024:.0f}MB)")


if __name__ == "__main__":
    main()
