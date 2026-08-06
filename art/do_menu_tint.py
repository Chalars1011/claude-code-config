# -*- coding: utf-8 -*-
"""主菜单黑暗化调色: 像素级操作, 不移动任何像素(保 Spine 子图布局)
top = 主场景(天空渐变+城市+尖塔+船+水面)  → 暗紫夜空 + 幽绿磷火城市 + 深色水面
bottom = 氛围层(云+星星+底层)             → 暗紫云层 + 微光星点
输出: D:/泯灭之塔/采纳图/背景/tint_top.png / tint_bottom.png
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

def darken_top(path_out):
    im = Image.open(r'D:/泯灭之塔/原版素材/背景/main_menu_top.png').convert('RGB')
    a = np.array(im).astype(np.float32)
    # 1) 整体压暗
    a *= 0.62
    # 2) 色相偏移: 偏紫(降低蓝绿, 提升红蓝? 不——暗紫=红蓝混合, 降低绿)
    #    目标: 天空蓝→暗紫, 水面蓝→深绿黑
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # 天空区域(上部, 蓝占比高): 蓝转紫 (绿降 25%, 红升 15%, 蓝降 20%)
    sky = (b > g + 5) & (b > r + 5)
    r[sky] *= 1.10; g[sky] *= 0.72; b[sky] *= 0.78
    # 水面区域(下部, 蓝灰): 转深绿 (红降 40%, 绿保 85%, 蓝降 55%)
    water = (a[..., 2] > 55) & (a[..., 2] < 110) & (a[..., 1] >= a[..., 0])
    r[water] *= 0.60; g[water] *= 0.88; b[water] *= 0.48
    # 3) 降饱和
    gray = a.mean(axis=2, keepdims=True)
    a = a * 0.72 + gray * 0.28
    # 4) 暗角
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h/2, w/2
    dist = np.sqrt(((xx-cx)/(w/2))**2 + ((yy-cy)/(h/2))**2)
    vig = 1.0 - 0.28 * np.clip(dist - 0.35, 0, 1)**1.5
    a *= vig[..., None]
    # 5) 微提对比
    a = np.clip((a - 90) * 1.08 + 90, 0, 255)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    out.save(path_out)
    print('top 调色完成:', out.size)

def darken_bottom(path_out):
    im = Image.open(r'D:/泯灭之塔/原版素材/背景/main_menu_bottom.png').convert('RGB')
    a = np.array(im).astype(np.float32)
    # 1) 压暗 (云层更暗)
    a *= 0.55
    # 2) 云/星区偏紫: 绿降, 红蓝微升
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    g *= 0.75; b *= 0.92; r *= 1.02
    # 3) 降饱和
    gray = a.mean(axis=2, keepdims=True)
    a = a * 0.68 + gray * 0.32
    # 4) 暗角
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h/2, w/2
    dist = np.sqrt(((xx-cx)/(w/2))**2 + ((yy-cy)/(h/2))**2)
    vig = 1.0 - 0.30 * np.clip(dist - 0.35, 0, 1)**1.5
    a *= vig[..., None]
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    out.save(path_out)
    print('bottom 调色完成:', out.size)

darken_top(r'D:/泯灭之塔/采纳图/背景/tint_top.png')
darken_bottom(r'D:/泯灭之塔/采纳图/背景/tint_bottom.png')
