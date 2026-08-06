#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终发布版：Steam 原版 + 46 文案 + 图集黑暗版 + 7 portrait 黑暗版，16 对齐"""

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

import imagecodecs
import numpy as np
from PIL import Image

SRC_PCK = r"D:/steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.pck.modtest.orig"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"
ALIGN = 16
LOC_DIR = r"D:/泯灭之塔/localization/zhs"
TEXCONV = r"C:/Users/13040/.claude/art/tools/texconv.exe"
F = imagecodecs.BCN.FORMAT

ATLAS_ENTRY = ".godot/imported/card_atlas_2.png-b839d300f2a53ba5863bc17e02165eea.bptc.ctex"
ATLAS_REPLACE = [
    ((253, 1345, 250, 190), r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png"),
]
# 主菜单背景（画笔重绘版）
MENU_TARGETS = [
    (".godot/imported/main_menu_bottom.png-d7d4537c3ec56f5f30144a17c9b31f7f.bptc.ctex",
     r"D:/泯灭之塔/采纳图/背景/bottom_黑暗版_v2_full.png", "BC7_UNORM"),
    (".godot/imported/main_menu_top.png-95e0772be3a5c9df8ceb498ad8b60bdb.s3tc.ctex",
     r"D:/泯灭之塔/采纳图/背景/top_黑暗版_full.png", "BC3_UNORM"),
]
PORTRAITS = {
    ".godot/imported/accelerant.png-880614f6ed1cd4d533608da0e80ba9de.ctex": r"D:/泯灭之塔/采纳图/卡牌/accelerant_黑暗版.png",
    ".godot/imported/accuracy.png-8174f09989ee3333ec2da7f05baffa53.ctex": r"D:/泯灭之塔/采纳图/卡牌/accuracy_黑暗版.png",
    ".godot/imported/acrobatics.png-fbd983bb839818137839c7942a0663f6.ctex": r"D:/泯灭之塔/采纳图/卡牌/acrobatics_黑暗版.png",
    ".godot/imported/backstab.png-21131b76861dc392c30f12a649ab177a.ctex": r"D:/泯灭之塔/采纳图/卡牌/backstab_黑暗版v2.png",
    ".godot/imported/blade_dance.png-32bddff6e2e283bd4c8dd24f8d569daa.ctex": r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png",
    ".godot/imported/dagger_spray.png-e68d84c4cddcb97b1e085c7adf6ae00a.ctex": r"D:/泯灭之塔/采纳图/卡牌/dagger_spray_黑暗版v2.png",
    ".godot/imported/strike_silent.png-96a36722b3d62cbc69f4f853c73244d6.ctex": r"D:/泯灭之塔/采纳图/卡牌/strike_silent_黑暗版.png",
}


def make_dark_atlas(orig_data):
    w = struct.unpack("<I", orig_data[8:12])[0]
    h = struct.unpack("<I", orig_data[12:16])[0]
    need = (w // 4) * ((h + 3) // 4) * 16
    img = imagecodecs.bcn_decode(orig_data[36:36 + need], format=F.BC7, shape=(3080, 3528, 4))
    for (x, y, ww, hh), png in ATLAS_REPLACE:
        dark = Image.open(png).convert("RGBA").resize((ww, hh), Image.LANCZOS)
        img[y:y + hh, x:x + ww] = np.array(dark)
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_rel_tmp.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_rel_out"
    os.makedirs(tmp_dir, exist_ok=True)
    Image.fromarray(img).save(tmp_png)
    r = subprocess.run([TEXCONV, "-f", "BC7_UNORM", "-m", "1", "-y", "-o", tmp_dir, tmp_png],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"texconv: {r.stdout[-200:]}"
    with open(os.path.join(tmp_dir, "_rel_tmp.dds"), "rb") as f:
        dds = f.read()
    hdr_len = 148 if dds[84:88] == b"DX10" else 128
    encoded = dds[hdr_len:]
    assert len(encoded) == need
    return orig_data[:36] + orig_data[36:52] + encoded  # 保留扩展头


def make_menu_texture(orig_ctex, png, fmt_name):
    """主菜单纹理：texconv 编码（保持原压缩格式），保留扩展头(16B)"""
    w = struct.unpack("<I", orig_ctex[8:12])[0]
    h = struct.unpack("<I", orig_ctex[12:16])[0]
    need = ((w + 3) // 4) * ((h + 3) // 4) * 16
    ext_head = orig_ctex[36:52]  # 扩展头（含宽高/标志）
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_menu_tmp.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_menu_out"
    os.makedirs(tmp_dir, exist_ok=True)
    im = Image.open(png).convert("RGBA")
    bw, bh = (im.width + 3) // 4 * 4, (im.height + 3) // 4 * 4
    if im.size != (bw, bh):
        canvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        canvas.paste(im, (0, 0))
        im = canvas
    im.save(tmp_png)
    r = subprocess.run([TEXCONV, "-f", fmt_name, "-m", "1", "-y", "-o", tmp_dir, tmp_png],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"texconv: {r.stdout[-300:]}"
    with open(os.path.join(tmp_dir, "_menu_tmp.dds"), "rb") as f:
        dds = f.read()
    hdr_len = 148 if dds[84:88] == b"DX10" else 128
    encoded = dds[hdr_len:]
    assert len(encoded) == need, f"长度 {len(encoded)} != {need}"
    return orig_ctex[:36] + ext_head + encoded


def make_portrait(orig_ctex, png):
    riff = orig_ctex.find(b"RIFF")
    assert riff > 0
    header = orig_ctex[:riff]
    w = struct.unpack("<I", orig_ctex[8:12])[0]
    h = struct.unpack("<I", orig_ctex[12:16])[0]
    im = Image.open(png).convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", lossless=True, quality=100, method=6)
    webp = buf.getvalue()
    new_ctex = bytearray(header + webp)
    struct.pack_into("<I", new_ctex, riff + 4, len(webp) - 8)
    orig_len = struct.unpack("<I", orig_ctex[riff + 4:riff + 8])[0] + 8
    for pos in range(4, riff - 3):
        v = struct.unpack("<I", orig_ctex[pos:pos + 4])[0]
        if v == orig_len:
            struct.pack_into("<I", new_ctex, pos, len(webp))
    return bytes(new_ctex)


def main():
    # 收集文案
    loc_files = {}
    for fn in os.listdir(LOC_DIR):
        if fn.endswith(".json"):
            with open(os.path.join(LOC_DIR, fn), "rb") as f:
                loc_files[f"localization/zhs/{fn}"] = f.read()
    print(f"文案: {len(loc_files)} 个 JSON")

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
            if path == ATLAS_ENTRY:
                data = make_dark_atlas(data)
                print("  🔄 图集（黑暗版）")
            elif path in PORTRAITS:
                data = make_portrait(data, PORTRAITS[path])
                print(f"  🔄 portrait: {path.split('/')[-1]}")
            elif path in loc_files:
                data = loc_files[path]
            for menu_path, menu_png, menu_fmt in MENU_TARGETS:
                if path == menu_path:
                    data = make_menu_texture(data, menu_png, menu_fmt)
                    print(f"  🔄 主菜单: {path.split('/')[-1]}")
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))
    print(f"总条目: {len(entries)}")

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

    shutil.copy2(OUT, OUT + ".bak_release_prev")
    shutil.move(OUT + ".rel", OUT)
    print(f"✅ 最终发布版已就位: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB)")


if __name__ == "__main__":
    main()
