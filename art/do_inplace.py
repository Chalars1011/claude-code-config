#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原地修改 PCK：保持原版布局不变，只覆盖条目数据 + 更新 md5 字段"""

import hashlib
import io
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

PCK = r"D:/泯灭之塔/SlayTheSpire2.pck"
ATLAS_ENTRY = ".godot/imported/card_atlas_2.png-b839d300f2a53ba5863bc17e02165eea.bptc.ctex"
F = imagecodecs.BCN.FORMAT
TEXCONV = r"C:/Users/13040/.claude/art/tools/texconv.exe"
REPLACE = [
    ((253, 1345, 250, 190), r"D:/泯灭之塔/采纳图/卡牌/blade_dance_黑暗版v2.png"),
]


def make_dark_ctex(orig_data):
    """解码 → 贴黑暗版 → texconv 编码 → 重建（与原版同大小）"""
    w = struct.unpack("<I", orig_data[8:12])[0]
    h = struct.unpack("<I", orig_data[12:16])[0]
    need = (w // 4) * ((h + 3) // 4) * 16
    img = imagecodecs.bcn_decode(orig_data[36:36 + need], format=F.BC7, shape=(3080, 3528, 4))
    for (x, y, ww, hh), png in REPLACE:
        dark = Image.open(png).convert("RGBA").resize((ww, hh), Image.LANCZOS)
        img[y:y + hh, x:x + ww] = np.array(dark)
        print(f"  贴入 ({x},{y},{ww}x{hh})")
    tmp_png = r"D:/泯灭之塔/原版素材/卡牌/_inplace.png"
    tmp_dir = r"D:/泯灭之塔/原版素材/卡牌/_inplace_out"
    os.makedirs(tmp_dir, exist_ok=True)
    Image.fromarray(img).save(tmp_png)
    r = subprocess.run([TEXCONV, "-f", "BC7_UNORM", "-m", "1", "-y", "-o", tmp_dir, tmp_png],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"texconv 失败: {r.stdout[-300:]}"
    with open(os.path.join(tmp_dir, "_inplace.dds"), "rb") as f:
        dds = f.read()
    hdr_len = 148 if dds[84:88] == b"DX10" else 128
    encoded = dds[hdr_len:]
    assert len(encoded) == need, f"长度 {len(encoded)} != {need}"
    return orig_data[:36] + encoded + orig_data[36 + need:]


def main():
    shutil.copy2(PCK, PCK + ".bak_inplace")
    print(f"备份 -> {PCK}.bak_inplace")

    with open(PCK, "rb") as f:
        hdr = f.read(64)
    dir_off = struct.unpack("<Q", hdr[32:40])[0]
    base = struct.unpack("<Q", hdr[24:32])[0]

    with open(PCK, "rb") as f:
        f.seek(dir_off)
        n = struct.unpack("<I", f.read(4))[0]
        target = None
        for i in range(n):
            plen = struct.unpack("<I", f.read(4))[0]
            pb = f.read(plen)
            path = pb.decode("utf-8", errors="replace").rstrip("\x00")
            off = struct.unpack("<Q", f.read(8))[0]
            size = struct.unpack("<Q", f.read(8))[0]
            md5_pos = f.tell()
            md5f = f.read(16)
            f.read(4)
            if path == ATLAS_ENTRY:
                target = {
                    "data_pos": base + off, "size": size,
                    "md5_pos": md5_pos + dir_off - dir_off + md5_pos,  # 修正：md5_pos 是相对文件
                }
                with open(PCK, "rb") as f:
                    f.seek(base + off)
                    orig_data = f.read(size)
                break
        assert target, "条目未找到"

    print(f"条目数据 @{target['data_pos']} size={target['size']}")
    print(f"md5 字段 @{target['md5_pos']}")
    assert orig_data[:4] == b"GST2", "数据开头不是 GST2"

    # 生成黑暗版（同大小）
    new_data = make_dark_ctex(orig_data)
    print(f"新数据: {len(new_data)}B (原 {len(orig_data)}B)")
    assert len(new_data) == len(orig_data), "大小不一致，无法原地替换！"

    # 原地写入数据 + 更新 md5
    with open(PCK, "r+b") as f:
        f.seek(target["data_pos"])
        f.write(new_data)
        f.seek(target["md5_pos"])
        f.write(hashlib.md5(new_data).digest())
    print("✅ 原地修改完成（数据 + md5）")


if __name__ == "__main__":
    main()
