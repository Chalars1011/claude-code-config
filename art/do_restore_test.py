#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对照实验：把原版 ctex 数据原样写回（重算 md5），验证重打包流程本身是否 OK"""

import hashlib
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CUR_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
ORIG_PCK = r"D:/steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.pck.modtest.orig"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"  # 直接覆盖
AL = 32
ATLAS_ENTRY = ".godot/imported/card_atlas_2.png-b839d300f2a53ba5863bc17e02165eea.bptc.ctex"


def read_entries(pck):
    with open(pck, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    base = struct.unpack("<Q", hdr[24:32])[0]
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
    return base, dir_off, entries


def main():
    # 从 Steam 原版读原版 ctex 数据
    base, _, entries = read_entries(ORIG_PCK)
    orig_data = None
    for pp, off, size in entries:
        if pp == ATLAS_ENTRY:
            with open(ORIG_PCK, "rb") as f:
                f.seek(base + off)
                orig_data = f.read(size)
            break
    print(f"原版 ctex: {len(orig_data)}B GST2@0: {orig_data[:4] == b'GST2'}")

    # 重打包当前 PCK，替换该条目为原版数据（重算 md5）
    _, dir_off, entries = read_entries(CUR_PCK)
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
            data = orig_data
            print(f"  🔄 恢复原版条目 {path}")
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
    print("✅ 已写回原版 ctex（重算 md5）")


if __name__ == "__main__":
    main()
