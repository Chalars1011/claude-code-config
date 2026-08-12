#!/bin/bash
# SessionStop hook: 会话结束时自动写事件（发布端自动化，实时通信的"广播"）
# 读取最近 journal 摘要，写 session_done 事件
/c/Users/13040/AppData/Local/Programs/Python/Python312/python.exe -c "
import sys, os, json, datetime
sys.stdout.reconfigure(encoding='utf-8')
try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}
# 事件内容：本次会话改了什么/做了什么（hook 没给总结，就用当前时间+会话摘要占位）
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
ev_dir = r'D:/Aurelia/.events'
os.makedirs(ev_dir, exist_ok=True)
fname = now.replace(':', '').replace('-', '').replace(' ', '_') + '_session_done.md'
with open(os.path.join(ev_dir, fname), 'w', encoding='utf-8') as f:
    f.write(f'{now}|session_done|工作站会话结束\n')
# 输出空 JSON（不注入上下文，只广播）
print(json.dumps({'hookSpecificOutput': {}}))
"
