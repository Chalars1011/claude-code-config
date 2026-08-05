#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 repack_cards — 把黑暗版卡牌 ctex 替换进 PCK 并重打包
逻辑复用 final_lore.py（验证过）：读目录 → 替换匹配条目 → ALIGN=32 重写
"""

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
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_cards"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
AL = 32

# 替换映射: PCK 条目路径 -> 新 ctex 文件
REPLACEMENTS = {
    ".godot/imported/accelerant.png-880614f6ed1cd4d533608da0e80ba9de.ctex":
        r"D:/泯灭之塔/采纳图/卡牌/accelerant_黑暗版.ctex",
    ".godot/imported/accuracy.png-8174f09989ee3333ec2da7f05baffa53.ctex":
        r"D:/泯灭之塔/采纳图/卡牌/accuracy_黑暗版.ctex",
    ".godot/imported/acrobatics.png-fbd983bb839818137839c7942a0663f6.ctex":
        r"D:/泯灭之塔/采纳图/卡牌/acrobatics_黑暗版.ctex",
    ".godot/imported/backstab.png-21131b76861dc392c30f12a649ab177a.ctex":
        r"D:/泯灭之塔/采纳图/卡牌/backstab_黑暗版v2.ctex",
    ".godot/imported/blade_dance.png-32bddff6e2e283bd4c8dd24f8d569daa.ctex":
        r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.ctex",
    ".godot/imported/dagger_spray.png-e68d84c4cddcb97b1e085c7adf6ae00a.ctex":
        r"D:/泯灭之塔/采纳图/卡牌/dagger_spray_黑暗版v2.ctex",
}


def main():
    if not os.path.exists(PCK):
        print("❌ PCK 不存在:", PCK)
        sys.exit(1)
    # 备份
    shutil.copy2(PCK, BAK)
    print(f"📦 备份 -> {BAK}")

    f = open(PCK, "rb")
    magic = f.read(4)
    fmt_ver = struct.unpack("<I", f.read(4))[0]
    gm, gmi, gp = struct.unpack("<III", f.read(12))
    flags = struct.unpack("<I", f.read(4))[0]
    old_base = struct.unpack("<Q", f.read(8))[0]
    old_ddir = struct.unpack("<Q", f.read(8))[0]
    f.seek(old_ddir)
    fc = struct.unpack("<I", f.read(4))[0]
    entries = []
    replaced = 0
    for i in range(fc):
        pl = struct.unpack("<I", f.read(4))[0]
        pb = f.read(pl)
        path = pb.decode("utf-8", errors="replace").rstrip(chr(0))
        off = struct.unpack("<Q", f.read(8))[0]
        sz = struct.unpack("<Q", f.read(8))[0]
        f.read(16)  # md5
        ef = struct.unpack("<I", f.read(4))[0]

        repl = None
        if path in REPLACEMENTS:
            with open(REPLACEMENTS[path], "rb") as rf:
                repl = rf.read()
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
        entries.append((path, pbytes, ppl, repl, ef))
    f.close()

    if replaced == 0:
        print("❌ 没有匹配到任何替换条目！")
        sys.exit(1)

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
    for path, pbytes, ppl, data, ef in entries:
        while out.tell() % AL != 0:
            out.write(b"\0")
        offs.append(out.tell() - fstart)
        out.write(data)
    while out.tell() % AL != 0:
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
    while out.tell() % AL != 0:
        out.write(b"\0")
    out.seek(bp)
    out.write(struct.pack("<Q", fstart))
    out.seek(dp)
    out.write(struct.pack("<Q", dstart))
    out.close()
    print(f"\n✅ 重打包完成: {OUT} ({os.path.getsize(OUT)/1024/1024:.0f}MB)")
    print(f"   替换 {replaced}/{fc} 条目")


if __name__ == "__main__":
    main()
