#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重打包（复刻原版布局）：数据区起点对齐 16，保持原版结构 —— 验证对齐是否是加载失败根因"""

import hashlib
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC_PCK = r"D:/steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.pck.modtest.orig"
OUT = r"D:/泯灭之塔/SlayTheSpire2.pck"
ALIGN = 16  # 数据区对齐（原版 112 % 16 = 0）


def main():
    shutil.copy2(SRC_PCK, OUT)
    with open(OUT, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    base = struct.unpack("<Q", hdr[24:32])[0]
    with open(OUT, "rb") as f:
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
            with open(OUT, "rb") as f2:
                f2.seek(base + off)
                data = f2.read(size)
            pbytes = path.encode("utf-8")
            ppl = len(pbytes)
            while ppl % 4 != 0:
                ppl += 1
            entries.append((path, pbytes, ppl, data, ef))
        print(f"读取 {len(entries)} 条目")

    # 重写：数据区从对齐位置开始
    out = open(OUT + ".new", "wb")
    out.write(b"GDPC")
    out.write(struct.pack("<I", 3))       # fmt ver
    out.write(struct.pack("<III", 4, 5, 1))  # godot 4.5.1
    out.write(struct.pack("<I", 2))       # flags: PCK_FILE_RELATIVE_BASE
    bp = out.tell()
    out.write(struct.pack("<Q", 0))       # base 占位
    dp = out.tell()
    out.write(struct.pack("<Q", 0))       # dir 占位
    # reserved 填到数据区起点对齐 16（112 = 4+4+12+4+8+8+72）
    while out.tell() % ALIGN != 0:
        out.write(b"\0")
    fstart = out.tell()
    print(f"数据区起点: {fstart} (对齐 {ALIGN})")

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
    print(f"✅ 重打包完成: {OUT}.new  base={fstart} dir={dstart}")


if __name__ == "__main__":
    main()
