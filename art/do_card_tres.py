#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改卡牌 tres 指向 portrait 大图：提取 uid → 生成新 tres → 重打包 PCK"""

import hashlib
import os
import re
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_tres"
AL = 32

CARDS = ["accelerant", "accuracy", "acrobatics", "blade_dance", "dagger_spray", "backstab"]


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


def extract_uid(imp_data):
    m = re.search(rb'uid="(uid://[^"]+)"', imp_data)
    return m.group(1).decode() if m else None


def split_parts(data):
    n = data.find(b"\x00")
    return data[:n], data[n:].lstrip(b"\x00")


def build_tres(portrait_uid, portrait_path):
    text = (
        f'[gd_resource type="AtlasTexture" load_steps=2 format=3 uid="uid://{portrait_uid}"]\n\n'
        f'[ext_resource type="Texture2D" path="{portrait_path}" id="1"]\n\n'
        "[resource]\n"
        'atlas = ExtResource("1")\n'
        "region = Rect2(0, 0, 1000, 760)\n"
    )
    return text.encode("utf-8")


def main():
    dir_off, entries = read_entries()
    print(f"条目: {len(entries)}")

    # 1) 提取每张卡的 portrait uid
    uids = {}
    for c in CARDS:
        imp = get_data(entries, f"images/packed/card_portraits/silent/{c}.png.import")
        if imp is None:
            print(f"  ❌ {c}: .import 不存在")
            continue
        uid = extract_uid(imp)
        uids[c] = uid
        print(f"  {c}: uid={uid}")

    # 2) 生成新 tres 字节
    new_tres = {}
    for c in CARDS:
        if c not in uids or not uids[c]:
            continue
        tres = get_data(entries, f"images/atlases/card_atlas.sprites/silent/{c}.tres")
        if tres is None:
            print(f"  ❌ {c}: tres 不存在")
            continue
        tail, head = split_parts(tres)
        full = build_tres(uids[c], f"res://images/packed/card_portraits/silent/{c}.png")
        new_tail = full[-len(tail):]
        new_head = full[:-len(tail)]
        nulls = tres.count(b"\x00")
        new_tres[f"images/atlases/card_atlas.sprites/silent/{c}.tres"] = new_tail + b"\x00" * nulls + new_head
        print(f"  ✅ 生成新 tres: {c} ({len(new_tres[f'images/atlases/card_atlas.sprites/silent/{c}.tres'])}B)")

    if not new_tres:
        print("❌ 没有生成任何 tres")
        sys.exit(1)

    # 3) 重打包
    shutil.copy2(PCK, BAK)
    print(f"📦 备份 -> {BAK}")
    f = open(PCK, "rb")
    magic = f.read(4)
    fmt_ver = struct.unpack("<I", f.read(4))[0]
    gm, gmi, gp = struct.unpack("<III", f.read(12))
    flags = struct.unpack("<I", f.read(4))[0]
    old_base = struct.unpack("<Q", f.read(8))[0]
    f.seek(dir_off)
    fc = struct.unpack("<I", f.read(4))[0]
    out_entries = []
    replaced = 0
    for i in range(fc):
        pl = struct.unpack("<I", f.read(4))[0]
        pb = f.read(pl)
        path = pb.decode("utf-8", errors="replace").rstrip("\x00")
        off = struct.unpack("<Q", f.read(8))[0]
        sz = struct.unpack("<Q", f.read(8))[0]
        f.read(16)
        ef = struct.unpack("<I", f.read(4))[0]
        if path in new_tres:
            repl = new_tres[path]
            replaced += 1
            print(f"  🔄 替换 {path} ({sz}B -> {len(repl)}B)")
        else:
            f2 = open(PCK, "rb")
            f2.seek(old_base + off)
            repl = f2.read(sz)
            f2.close()
        pbytes = path.encode("utf-8")
        ppl = len(pbytes)
        while ppl % 4 != 0:
            ppl += 1
        out_entries.append((path, pbytes, ppl, repl, ef))
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
    print(f"\n✅ 重打包完成: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB) 替换 {replaced} 个 tres")


if __name__ == "__main__":
    main()
