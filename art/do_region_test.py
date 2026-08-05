#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""链路测试：改 blade_dance.tres 的 region 指向 (0,0)，验证卡牌显示是否走 tres"""

import hashlib
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"
ALIGN = 16
TRES_ENTRY = "images/atlases/card_atlas.sprites/silent/blade_dance.tres"


def main():
    shutil.copy2(SRC_PCK, SRC_PCK + ".bak_region")
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
            if path == TRES_ENTRY:
                text = data.decode("utf-8", errors="replace")
                print("原 tres region:", [l for l in text.split("\n") if "region" in l])
                text = text.replace("Rect2(253, 1345, 250, 190)", "Rect2(0, 0, 250, 190)")
                data = text.encode("utf-8")
                print("新 tres region:", [l for l in text.split("\n") if "region" in l])
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))

    out = open(OUT + ".rt", "wb")
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
    shutil.move(OUT + ".rt", OUT)
    print("✅ region 测试版已就位")


if __name__ == "__main__":
    main()
