#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终整合：原版 PCK + 黑暗化文案(47 JSON) + 黑暗版图集，16 对齐重打包"""

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
REPLACE = [
    ((253, 1345, 250, 190), r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png"),
]


def make_dark_ctex(orig_data):
    w = struct.unpack("<I", orig_data[8:12])[0]
    h = struct.unpack("<I", orig_data[12:16])[0]
    need = (w // 4) * ((h + 3) // 4) * 16
    img = imagecodecs.bcn_decode(orig_data[36:36 + need], format=F.BC7, shape=(3080, 3528, 4))
    for (x, y, ww, hh), png in REPLACE:
        dark = Image.open(png).convert("RGBA").resize((ww, hh), Image.LANCZOS)
        img[y:y + hh, x:x + ww] = np.array(dark)
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_final_tmp.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_final_out"
    os.makedirs(tmp_dir, exist_ok=True)
    Image.fromarray(img).save(tmp_png)
    r = subprocess.run([TEXCONV, "-f", "BC7_UNORM", "-m", "1", "-y", "-o", tmp_dir, tmp_png],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"texconv: {r.stdout[-200:]}"
    with open(os.path.join(tmp_dir, "_final_tmp.dds"), "rb") as f:
        dds = f.read()
    hdr_len = 148 if dds[84:88] == b"DX10" else 128
    encoded = dds[hdr_len:]
    assert len(encoded) == need
    return orig_data[:36] + encoded + orig_data[36 + need:]


def main():
    # 收集替换数据
    repl = {}
    # 1) 黑暗化文案（47 个 JSON）
    loc_count = 0
    for fn in os.listdir(LOC_DIR):
        if fn.endswith(".json"):
            with open(os.path.join(LOC_DIR, fn), "rb") as f:
                repl[f"localization/zhs/{fn}"] = f.read()
            loc_count += 1
    print(f"文案: {loc_count} 个 JSON")

    # 2) 图集
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
                assert data[:4] == b"GST2"
                data = make_dark_ctex(data)
                print(f"图集: 黑暗版已生成 ({len(data)}B)")
            elif path in repl:
                data = repl[path]
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))
        print(f"总条目: {len(entries)}")

    # 3) 16 对齐重打包
    out = open(OUT + ".final", "wb")
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

    # 4) 就位
    shutil.copy2(OUT, OUT + ".bak_before_final")
    shutil.move(OUT + ".final", OUT)
    print(f"✅ 最终版已就位: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB)")
    print(f"   文案 {loc_count} 个 + 图集 1 个 + 16 对齐")


if __name__ == "__main__":
    main()
