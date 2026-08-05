#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""替换卡牌 portrait 大图 ctex（图鉴显示用）→ 黑暗版，16 对齐重打包"""

import hashlib
import io
import os
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image

SRC_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"
ALIGN = 16

# 卡牌: PCK 条目路径 -> 黑暗版 PNG
PORTRAITS = {
    ".godot/imported/accelerant.png-880614f6ed1cd4d533608da0e80ba9de.ctex": r"D:/泯灭之塔/采纳图/卡牌/accelerant_黑暗版.png",
    ".godot/imported/accuracy.png-8174f09989ee3333ec2da7f05baffa53.ctex": r"D:/泯灭之塔/采纳图/卡牌/accuracy_黑暗版.png",
    ".godot/imported/acrobatics.png-fbd983bb839818137839c7942a0663f6.ctex": r"D:/泯灭之塔/采纳图/卡牌/acrobatics_黑暗版.png",
    ".godot/imported/backstab.png-21131b76861dc392c30f12a649ab177a.ctex": r"D:/泯灭之塔/采纳图/卡牌/backstab_黑暗版v2.png",
    ".godot/imported/blade_dance.png-32bddff6e2e283bd4c8dd24f8d569daa.ctex": r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png",
    ".godot/imported/dagger_spray.png-e68d84c4cddcb97b1e085c7adf6ae00a.ctex": r"D:/泯灭之塔/采纳图/卡牌/dagger_spray_黑暗版v2.png",
    ".godot/imported/strike_silent.png-96a36722b3d62cbc69f4f853c73244d6.ctex": r"D:/泯灭之塔/采纳图/卡牌/strike_silent_黑暗版.png",
}


def make_webp_ctex(orig_ctex, png):
    """原 ctex 头（到 RIFF 前）+ 新 WebP"""
    riff = orig_ctex.find(b"RIFF")
    assert riff > 0, "找不到 RIFF"
    header = orig_ctex[:riff]
    # 原尺寸（GST2 头 w/h @ 112/116 相对 ctex 文件起点 0）
    w = struct.unpack("<I", orig_ctex[8:12])[0]
    h = struct.unpack("<I", orig_ctex[12:16])[0]
    im = Image.open(png).convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", lossless=True, quality=100, method=6)
    webp = buf.getvalue()
    new_ctex = bytearray(header + webp)
    # 更新 RIFF size
    struct.pack_into("<I", new_ctex, riff + 4, len(webp) - 8)
    # GST2 头 datasize（原 WebP 全长）
    orig_len = struct.unpack("<I", orig_ctex[riff + 4:riff + 8])[0] + 8
    for pos in range(4, riff - 3):
        v = struct.unpack("<I", orig_ctex[pos:pos + 4])[0]
        if v == orig_len:
            struct.pack_into("<I", new_ctex, pos, len(webp))
    return bytes(new_ctex)


def main():
    shutil.copy2(SRC_PCK, SRC_PCK + ".bak_portrait")
    print(f"备份 -> {SRC_PCK}.bak_portrait")

    with open(SRC_PCK, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    base = struct.unpack("<Q", hdr[24:32])[0]
    with open(SRC_PCK, "rb") as f:
        f.seek(dir_off)
        n = struct.unpack("<I", f.read(4))[0]
        entries = []
        replaced = 0
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
            if path in PORTRAITS:
                data = make_webp_ctex(data, PORTRAITS[path])
                replaced += 1
                print(f"  🔄 {path.split('/')[-1]} ({size}B -> {len(data)}B)")
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))

    print(f"替换 {replaced}/{len(PORTRAITS)} 张")
    assert replaced == len(PORTRAITS), "有卡牌没匹配到！"

    out = open(OUT + ".pt", "wb")
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
    shutil.move(OUT + ".pt", OUT)
    print(f"✅ portrait 替换版已就位 ({os.path.getsize(OUT)/1024/1024:.0f}MB)")


if __name__ == "__main__":
    main()
