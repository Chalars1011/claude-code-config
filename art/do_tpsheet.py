#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改 card_atlas.tpsheet：textures 数组最前面插入 portrait 大图条目，让卡牌 sprite 命中大图"""

import hashlib
import os
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_tpsheet"
AL = 32
TPSHEET = "images/atlases/card_atlas.tpsheet"

# 插入的新 texture 条目（portrait 大图 + 目标卡牌）
NEW_TEXTURES = [
    {
        "image": "../packed/card_portraits/silent/strike_silent.png",
        "filename": "silent/strike_silent.png",
        "w": 1000,
        "h": 760,
    },
]


def build_new_entry(t):
    return (
        '    {\n'
        f'      "image": "{t["image"]}",\n'
        '      "size": {\n'
        f'        "w": {t["w"]},\n'
        f'        "h": {t["h"]}\n'
        '      },\n'
        '      "sprites": [\n'
        '        {\n'
        f'          "filename": "{t["filename"]}",\n'
        '          "region": {\n'
        '            "x": 0,\n'
        '            "y": 0,\n'
        f'            "w": {t["w"]},\n'
        f'            "h": {t["h"]}\n'
        '          },\n'
        '          "margin": {\n'
        '            "x": 0,\n'
        '            "y": 0,\n'
        '            "w": 0,\n'
        '            "h": 0\n'
        '          }\n'
        '        }\n'
        '      ]\n'
        '    },\n'
    )


def main():
    # 读取当前 PCK 目录
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

    tps = None
    for pp, off, size in entries:
        if pp == TPSHEET:
            with open(PCK, "rb") as f:
                f.seek(off)
                tps = f.read(size)
            break
    if tps is None:
        print("❌ tpsheet 不存在")
        sys.exit(1)
    print(f"原 tpsheet: {len(tps)}B")

    # 分段
    n0 = tps.find(b"\x00")
    tail = tps[:n0]
    nulls = tps.count(b"\x00")
    head = tps[n0:].lstrip(b"\x00")
    print(f"tail={len(tail)}B nulls={nulls} head={len(head)}B")

    # 插入新条目到 "textures": [ 之后
    marker = b'"textures": [\n'
    idx = head.find(marker)
    if idx < 0:
        print("❌ 找不到 textures 标记")
        sys.exit(1)
    insert_pos = idx + len(marker)
    additions = "".join(build_new_entry(t) for t in NEW_TEXTURES).encode("utf-8")
    new_head = head[:insert_pos] + additions + head[insert_pos:]
    print(f"插入 {len(additions)}B，新 head: {len(new_head)}B")

    # 重组（null 数量保持）
    new_tps = tail + b"\x00" * nulls + new_head
    print(f"新 tpsheet: {len(new_tps)}B")

    # 重打包
    shutil.copy2(PCK, BAK)
    print(f"备份 -> {BAK}")
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
        if path == TPSHEET:
            data = new_tps
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
