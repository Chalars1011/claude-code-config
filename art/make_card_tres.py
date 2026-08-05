#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🃏 make_card_tres — 把卡牌 .tres 改为引用 portrait 大图（绕开 BC7 图集）
格式: PCK 文本资源 = [正常文件尾段] + null填充 + [正常文件头段]
      （Godot 4.4+ 分段存储，实验验证）

用法:
    python make_card_tres.py <原.tres> <新.tres> <portrait_uid> <portrait_path>
"""

import struct
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def split_parts(data):
    """按 null 填充切分: 返回 (尾段, 头段)"""
    n = data.find(b"\x00")
    tail = data[:n]
    head = data[n:].lstrip(b"\x00")
    return tail, head


def build(card_id, portrait_uid, portrait_path):
    # 完整正常文本
    text = (
        '[gd_resource type="AtlasTexture" load_steps=2 format=3 uid="uid://'
        f'{portrait_uid}"]\n\n'
        f'[ext_resource type="Texture2D" path="{portrait_path}" id="1"]\n\n'
        "[resource]\n"
        'atlas = ExtResource("1")\n'
        "region = Rect2(0, 0, 1000, 760)\n"
    )
    return text.encode("utf-8")


def make(src_tres, out_tres, portrait_uid, portrait_path):
    with open(src_tres, "rb") as f:
        orig = f.read()
    tail, head = split_parts(orig)
    n_tail = len(tail)
    print(f"  原结构: 尾段 {n_tail}B, 头段 {len(head)}B, 总 {len(orig)}B")

    full = build(None, portrait_uid, portrait_path)
    print(f"  新完整文本: {len(full)}B")

    # 保持同样的切分点：尾段取新文本的后 n_tail 字节，头段取其余
    new_tail = full[-n_tail:]
    new_head = full[:-n_tail]
    nulls = orig.count(b"\x00")  # 保持原 null 数量
    new_data = new_tail + b"\x00" * nulls + new_head

    with open(out_tres, "wb") as f:
        f.write(new_data)
    print(f"  ✅ 输出: {out_tres} ({len(new_data)}B)  [uid={portrait_uid}]")
    return out_tres


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    make(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
