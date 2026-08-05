#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复版：从干净备份提取原版 ctex，正确重建（RIFF@160），tpsheet 用绝对路径"""

import hashlib
import io
import os
import re
import shutil
import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image

CLEAN_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_strike"  # do_strike 前（ctex 原版）
CUR_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_fix"
AL = 32
DARK_PNG = r"D:/泯灭之塔/采纳图/卡牌/strike_silent_黑暗版.png"
CARD = "strike_silent"


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


def get_data(pck, entries, path):
    for pp, off, size in entries:
        if pp == path:
            with open(pck, "rb") as f:
                f.seek(off)
                return f.read(size)
    return None


def make_ctex(orig_ctex, dark_png, target_w, target_h):
    """RIFF 位置动态检测，重建 ctex"""
    riff_pos = orig_ctex.find(b"RIFF")
    assert riff_pos > 0, "原版 ctex 找不到 RIFF"
    header = orig_ctex[:riff_pos]  # 完整保留原头（含 GST2）
    print(f"  原头: {riff_pos}B (GST2@{orig_ctex.find(b'GST2')})")

    im = Image.open(dark_png).convert("RGBA")
    if im.size != (target_w, target_h):
        im = im.resize((target_w, target_h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", lossless=True, quality=100, method=6)
    webp = buf.getvalue()
    assert webp[:4] == b"RIFF", "Pillow 输出异常"

    new_ctex = bytearray(header + webp)
    # 更新 RIFF size（若 RIFF 在 GST2 头内被引用则一并更新）
    orig_riff_size = struct.unpack("<I", orig_ctex[riff_pos + 4:riff_pos + 8])[0]
    new_riff_size = len(webp) - 8
    struct.pack_into("<I", new_ctex, riff_pos + 4, new_riff_size)
    # GST2 头内 datasize（== orig webp 全长的字段）
    orig_webp_len = orig_riff_size + 8
    for pos in range(104, riff_pos - 3):
        v = struct.unpack("<I", orig_ctex[pos:pos + 4])[0]
        if v == orig_webp_len:
            struct.pack_into("<I", new_ctex, pos, len(webp))
    return bytes(new_ctex)


def main():
    # 1) 从干净备份拿原版 ctex
    _, clean_entries = read_entries(CLEAN_PCK)
    ctex_path = None
    for path, off, size in clean_entries:
        if path.startswith(f".godot/imported/{CARD}.png-") and path.endswith(".ctex"):
            ctex_path = path
            break
    orig_ctex = get_data(CLEAN_PCK, clean_entries, ctex_path)
    w = struct.unpack("<I", orig_ctex[112:116])[0]
    h = struct.unpack("<I", orig_ctex[116:120])[0]
    print(f"原版 ctex: {ctex_path} ({len(orig_ctex)}B {w}x{h}) RIFF@{orig_ctex.find(b'RIFF')}")

    new_ctex = make_ctex(orig_ctex, DARK_PNG, w, h)
    # 验证
    r = new_ctex.find(b"RIFF")
    print(f"新 ctex: {len(new_ctex)}B RIFF@{r}")
    assert r == orig_ctex.find(b"RIFF"), "RIFF 位置变了！"
    webp_len = len(new_ctex) - r
    riff_size = struct.unpack("<I", new_ctex[r + 4:r + 8])[0]
    print(f"  WebP 数据: {webp_len}B, RIFF size 字段: {riff_size}B, 一致={riff_size == webp_len - 8}")
    # Pillow 验证
    from PIL import Image as Im2
    im2 = Im2.open(io.BytesIO(bytes(new_ctex[r:])))
    print(f"  Pillow 验证: {im2.size} ✅")
    open(r"D:/泯灭之塔/采纳图/卡牌/strike_silent_黑暗版_fixed.ctex", "wb").write(new_ctex)

    # 2) tpsheet 修正：image 用绝对路径（当前 PCK 里已有插入条目）
    _, cur_entries = read_entries(CUR_PCK)
    tps = get_data(CUR_PCK, cur_entries, "images/atlases/card_atlas.tpsheet")
    n0 = tps.find(b"\x00")
    tail = tps[:n0]
    nulls = tps.count(b"\x00")
    head = tps[n0:].lstrip(b"\x00")
    rel = b'"image": "../packed/card_portraits/silent/strike_silent.png"'
    abs_ = b'"image": "res://images/packed/card_portraits/silent/strike_silent.png"'
    if rel in head:
        head = head.replace(rel, abs_)
        print("tpsheet: 相对路径 -> 绝对路径 ✅")
    else:
        print("tpsheet: 未找到相对路径（检查是否已修改）")
    new_tps = tail + b"\x00" * nulls + head

    # 3) 重打包
    shutil.copy2(CUR_PCK, BAK)
    print(f"备份 -> {BAK}")
    repl = {ctex_path: new_ctex, "images/atlases/card_atlas.tpsheet": new_tps}
    dir_off, entries = read_entries(CUR_PCK)
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
        if path in repl:
            data = repl[path]
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
