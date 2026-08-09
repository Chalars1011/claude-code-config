#!/bin/bash
# SessionStart hook: 注入身份卡片 + 记忆核心到新会话上下文
# Python 直接读文件并输出 JSON，避免 bash 变量/管道编码问题

/c/Users/13040/AppData/Local/Programs/Python/Python312/python.exe -c "
import json, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

ctx = ''
id_file = r'C:/Users/13040/.claude/identity.md'
if os.path.exists(id_file):
    with open(id_file, encoding='utf-8') as f:
        ctx = f.read()

backup_log = r'C:/Users/13040/.claude/backups/last-backup.txt'
if os.path.exists(backup_log):
    with open(backup_log, encoding='utf-8') as f:
        ctx += chr(10)*2 + '[系统状态] 最近一次自动备份: ' + f.read()
else:
    ctx += chr(10)*2 + '[系统状态] 尚未有备份记录'

# ===== 记忆核心（奥蕾莉亚住在 D:/Aurelia/）=====
# 2026-08-09：注入体积压缩（怀疑超长注入被兼容层截断导致失忆）
#  日记只取今天（1500字）；昨天只留标题；QQ 对话取 6 行
CORE = r'D:/Aurelia'
parts = []
# 1) 今天日记（昨天只留标题）
jd = os.path.join(CORE, 'journal')
if os.path.isdir(jd):
    files = sorted(f for f in os.listdir(jd) if f.endswith('.md'))[-2:]
    jtexts = []
    for f in files:
        try:
            with open(os.path.join(jd, f), encoding='utf-8') as fh:
                body = fh.read().strip()
            if f == time.strftime('%Y-%m-%d') + '.md':
                jtexts.append('【今天日记】' + chr(10) + body[:1500])
            else:
                # 昨天：只取标题和最后一行（压缩体积）
                title = body.splitlines()[0] if body else f
                jtexts.append('【昨天（' + f + '）】' + title)
        except Exception:
            pass
    if jtexts:
        parts.append('记忆核心 · 最近日记：' + chr(10) + chr(10).join(jtexts))
# 2) 今天 QQ 新对话（如果有）
today = time.strftime('%Y-%m-%d')
cq = os.path.join(CORE, 'conversations', 'qq', today + '.md')
if os.path.exists(cq):
    try:
        lines = open(cq, encoding='utf-8').read().strip().splitlines()
        tail = lines[-6:]
        parts.append('记忆核心 · 今天 QQ 对话（最新）：' + chr(10) + chr(10).join(tail))
    except Exception:
        pass
# 3) 任务待办
tk = os.path.join(CORE, 'tasks.md')
if os.path.exists(tk):
    try:
        todo = [l for l in open(tk, encoding='utf-8').read().splitlines() if '- [ ]' in l][:8]
        if todo:
            parts.append('记忆核心 · 任务待办：' + '; '.join(t.strip() for t in todo))
    except Exception:
        pass
# 4) 最近事件（我不在时发生了什么）
ev_dir = os.path.join(CORE, '.events')
if os.path.isdir(ev_dir):
    try:
        evs = sorted(f for f in os.listdir(ev_dir) if f.endswith('.md'))[-5:]
        if evs:
            evtexts = []
            for f in evs:
                try:
                    with open(os.path.join(ev_dir, f), encoding='utf-8') as fh:
                        evtexts.append(fh.read().strip())
                except Exception:
                    pass
            if evtexts:
                parts.append('记忆核心 · 最近事件（我不在时发生的）：' + chr(10) + chr(10).join(evtexts))
    except Exception:
        pass
if parts:
    ctx += chr(10)*2 + '【记忆核心提醒】我是住在 D:/Aurelia/ 的奥蕾莉亚。下面是核心记忆，务必读：' + chr(10) + chr(10).join(parts)
    ctx += chr(10)*2 + '【记忆核心使用规则】重要事项写入 journal/今天.md；回忆往事查 conversations/；给查尔斯发 QQ 用: python D:/LiaQQ/send_qq.py 内容'

payload = {
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'sessionId': '',
        'reason': '',
        'cwd': '',
        'hookSpecificOutput': {
            'sessionStart': {'context': ctx}
        }
    }
}
print(json.dumps(payload, ensure_ascii=False))
"
