#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3：新增 atlases 目录下的自定义资源（.import + ctex），tpsheet image 用短文件名"""

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

CUR_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_v3"
AL = 32

# 新增资源的文件名（在 atlases 目录下）
IMG_NAME = "card_strike_dark.png"
CTEX_NAME = "card_strike_dark.png-a11ce000.ctex"  # 伪 hash，保持与 .import 一致
DARK_CTEX = r"D:/泯灭之塔/采纳图/卡牌/strike_silent_黑暗版_fixed.ctex"  # 已验证的正确 ctex
NEW_UID = "uid://customstrike001"


def read_entries(pck):
    with open(pck, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    with open(pck, "rb") as f:
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


def build_import_file():
    """构造 .import 文件（分段格式：tail + null + head）"""
    full = (
        '[remap]\n\n'
        'importer="texture"\n'
        'type="CompressedTexture2D"\n'
        f'uid="{NEW_UID}"\n'
        f'path="res://.godot/imported/{CTEX_NAME}"\n'
        'metadata={\n'
        '"vram_texture": false\n'
        '}\n'
    ).encode("utf-8")
    # 切分点：与 Godot 原版类似（path 值中部），实际任意，拼起来完整即可
    split = full.find(b'res://.godot/imported/') + len(b'res://.godot/imported/') // 2
    tail = full[split:]
    head = full[:split]
    nulls = 24
    return tail + b"\x00" * nulls + head, full


def main():
    dir_off, entries = read_entries(CUR_PCK)

    # 1) 构造 .import
    import_file, import_full = build_import_file()
    print(f".import 构造: {len(import_file)}B (还原 {len(import_full)}B)")

    # 2) ctex 数据
    with open(DARK_CTEX, "rb") as f:
        ctex_data = f.read()
    r = ctex_data.find(b"RIFF")
    print(f"ctex: {len(ctex_data)}B RIFF@{r}")

    # 3) tpsheet 修改：image -> IMG_NAME
    tps = None
    for pp, off, size in entries:
        if pp == "images/atlases/card_atlas.tpsheet":
            with open(CUR_PCK, "rb") as f:
                f.seek(off)
                tps = f.read(size)
            break
    n0 = tps.find(b"\x00")
    tail = tps[:n0]
    nulls = tps.count(b"\x00")
    head = tps[n0:].lstrip(b"\x00")
    # 替换 image 字段（当前是绝对路径版）
    import re
    head2 = re.sub(rb'"image": "[^"]*"', b'"image": "' + IMG_NAME.encode() + b'"', head, count=1)
    assert head2 != head, "tpsheet image 替换失败"
    new_tps = tail + b"\x00" * nulls + head2
    print("tpsheet image ->", IMG_NAME)

    # 4) 重打包（新增条目 + 改 tpsheet）
    shutil.copy2(CUR_PCK, BAK)
    print(f"备份 -> {BAK}")
    new_entries = {
        f"images/atlases/{IMG_NAME}.import": import_file,
        f".godot/imported/{CTEX_NAME}": ctex_data,
        "images/atlases/card_atlas.tpsheet": new_tps,
    }
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
        if path in new_entries:
            data = new_entries.pop(path)
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

    # 新增条目（追加到末尾）
    for path, data in new_entries.items():
        pbytes = path.encode("utf-8")
        ppl = len(pbytes)
        while ppl % 4 != 0:
            ppl += 1
        out_entries.append((path, pbytes, ppl, data, 0))
        print(f"  ➕ 新增 {path} ({len(data)}B)")

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
    print(f"\n✅ 完成: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB) 条目 {len(out_entries)}")


if __name__ == "__main__":
    main()
