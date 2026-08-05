#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2（正确版）：ctex = GST2头(36B) + BC7数据 + 尾部。条目 offset 相对 base，读取用 base+off"""

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

CUR_PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
OUT = r"D:/泯灭之塔/SlayTheSpire2_new.pck"
BAK = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_bc7v2"
AL = 32
F = imagecodecs.BCN.FORMAT
TEXCONV = r"C:/Users/13040/.claude/art/tools/texconv.exe"

ATLAS_ENTRY = ".godot/imported/card_atlas_2.png-b839d300f2a53ba5863bc17e02165eea.bptc.ctex"
ATLAS_W, ATLAS_H = 3528, 3077
REPLACE = [
    ((253, 1345, 250, 190), r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png"),
]


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


def get_data(pck, base, entries, path):
    for pp, off, size in entries:
        if pp == path:
            with open(pck, "rb") as f:
                f.seek(base + off)  # 关键：base+off
                return f.read(size)
    return None


def main():
    # 1) 从干净 PCK（文案版）读原 ctex —— 注意从 bak_bc7（干净）读
    src_pck = r"D:/泯灭之塔/SlayTheSpire2.pck.bak_bc7"
    base, dir_off, entries = read_entries(src_pck)
    orig = get_data(src_pck, base, entries, ATLAS_ENTRY)
    print(f"原 ctex: {len(orig)}B")
    assert orig[:4] == b"GST2", f"不是 GST2 开头: {orig[:4]}"
    w = struct.unpack("<I", orig[8:12])[0]
    h = struct.unpack("<I", orig[12:16])[0]
    print(f"GST2 头: {w}x{h} ver={struct.unpack('<I', orig[4:8])[0]}")
    need = (w // 4) * ((h + 3) // 4) * 16
    print(f"BC7 需: {need}B, 头36B, 尾部 {len(orig)-36-need}B")
    gst2_head = orig[:36]

    # 2) 解码（数据从 36 起）
    img = imagecodecs.bcn_decode(orig[36:36 + need], format=F.BC7, shape=(3080, 3528, 4))
    print(f"解码: {img.shape}")

    # 3) 贴黑暗版
    for (x, y, ww, hh), png in REPLACE:
        dark = Image.open(png).convert("RGBA").resize((ww, hh), Image.LANCZOS)
        img[y:y + hh, x:x + ww] = np.array(dark)
        print(f"  🔄 贴入 ({x},{y},{ww}x{hh})")

    # 4) texconv 编码
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_atlas2_v2.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_texconv_out2"
    os.makedirs(tmp_dir, exist_ok=True)
    Image.fromarray(img).save(tmp_png)
    print("texconv 编码...")
    r = subprocess.run([TEXCONV, "-f", "BC7_UNORM", "-m", "1", "-y", "-o", tmp_dir, tmp_png],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print("texconv 失败:", r.stdout[-400:], r.stderr[-400:])
        sys.exit(1)
    with open(os.path.join(tmp_dir, "_atlas2_v2.dds"), "rb") as f:
        dds = f.read()
    fourcc = dds[84:88]
    hdr_len = 148 if fourcc == b"DX10" else 128
    encoded = dds[hdr_len:]
    print(f"BC7 数据: {len(encoded)}B (需 {need}B)")
    assert len(encoded) == need, "数据长度不匹配！"
    tail = orig[36 + need:]
    print(f"尾部: {len(tail)}B")

    # 5) 重建
    new_ctex = gst2_head + encoded + tail
    print(f"新 ctex: {len(new_ctex)}B (原 {len(orig)}B)")

    # 6) 本地验证：解码新 ctex 检查 region
    vimg = imagecodecs.bcn_decode(new_ctex[36:36 + need], format=F.BC7, shape=(3080, 3528, 4))
    vregion = vimg[1345:1345 + 190, 253:253 + 250]
    dark_arr = np.array(Image.open(r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png").convert("RGBA").resize((250, 190)))[:, :, :3].astype(float)
    vdiff = np.abs(vregion[:, :, :3].astype(float) - dark_arr).mean()
    print(f"✅ 验证: 新 ctex region vs 黑暗版 色差={vdiff:.1f} (应 < 30)")
    assert vdiff < 30, "验证失败！"

    # 7) 重打包
    shutil.copy2(CUR_PCK, BAK)
    print(f"备份 -> {BAK}")
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
            data = new_ctex
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
