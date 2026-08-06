#!/bin/bash
# 游戏一键测试脚本: 杀旧进程 → 启动 → 等待 → 截图 → 关游戏
# 用法: bash game_test.sh [等待秒数默认18]
WAIT="${1:-18}"
OUT_DIR="/d/泯灭之塔/采纳图/背景"

echo "① 清理旧进程..."
powershell -NoProfile -Command "Stop-Process -Name SlayTheSpire2 -Force -ErrorAction SilentlyContinue" 2>/dev/null
sleep 2

echo "② 启动游戏..."
cd /d/泯灭之塔 && ./SlayTheSpire2.exe > /tmp/game_test_log.txt 2>&1 &
sleep "$WAIT"

echo "③ 截图..."
python - << 'PYEOF'
from PIL import ImageGrab
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
im = ImageGrab.grab()
out = r'D:/泯灭之塔/采纳图/背景/菜单_测试截图.png'
im.save(out)
px = im.resize((64,36)).getdata(); n = len(px)
avg = tuple(round(sum(p[i] for p in px)/n) for i in range(3))
print(f'截图已存: {out} ({im.size}) 平均色: {avg}')
PYEOF

echo "④ 保持游戏窗口开启等待人工验收（按 Ctrl+C 或手动关）"
