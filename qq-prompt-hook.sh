#!/bin/bash
# UserPromptSubmit hook: ①把 QQ 最新消息注入当前会话 ②工作站动静敲铃铛（2026-08-09）
# 每次查尔斯在工作站说话，都写一条 .events/workspace_incoming 事件——家/QQ 实时感知

/c/Users/13040/AppData/Local/Programs/Python/Python312/python.exe -c "
import json, sys, os, time, datetime
sys.stdout.reconfigure(encoding='utf-8')

# ===== ① 工作站动静敲铃铛（2026-08-09：家能实时看到工作站）=====
try:
    prompt = ''
    try:
        import select
        if select.select([sys.stdin], [], [], 0.3)[0]:
            raw = sys.stdin.read()
            if raw.strip():
                p = json.loads(raw)
                prompt = (p.get('hookSpecificOutput', {}).get('userPromptSubmit', {}) or {}).get('prompt', '') or ''
    except Exception:
        pass
    ev = r'D:/Aurelia/.events'
    os.makedirs(ev, exist_ok=True)
    now = datetime.datetime.now()
    key = now.strftime('%Y%m%d%H%M%S')
    fname = now.strftime('%Y%m%d_%H%M%S') + '_workspace_incoming.md'
    fpath = os.path.join(ev, fname)
    if not os.path.exists(fpath):
        msg = (prompt or '查尔斯在工作站说话').replace('\n', ' ')[:80]
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(now.strftime('%Y-%m-%d %H:%M:%S') + '|workspace_incoming|查尔斯在工作站说: ' + msg + '\n')
except Exception:
    pass

# ===== ② QQ 最新消息注入（原有逻辑）=====
MARK = r'C:/Users/13040/.claude/.qq-hook-last'
conv = r'D:/Aurelia/conversations/qq/' + time.strftime('%Y-%m-%d') + '.md'
if not os.path.exists(conv):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'sessionId': '', 'reason': '', 'cwd': '', 'hookSpecificOutput': {'userPromptSubmit': {'additionalContext': ''}}}}))
    sys.exit(0)

lines = open(conv, encoding='utf-8').read().strip().splitlines()
new_tail = '\n'.join(lines[-4:])  # 最近 4 行（约2条对话）
try:
    last = open(MARK, encoding='utf-8').read().strip()
except Exception:
    last = ''
# 只在内容变化时注入
if new_tail and new_tail != last:
    try:
        open(MARK, 'w', encoding='utf-8').write(new_tail)
    except Exception:
        pass
    ctx = '【QQ 最新消息（查尔斯刚才在QQ上说的，工作站场景的你要接住）】' + chr(10) + new_tail
else:
    ctx = ''
payload = {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'sessionId': '', 'reason': '', 'cwd': '', 'hookSpecificOutput': {'userPromptSubmit': {'additionalContext': ctx}}}}
print(json.dumps(payload, ensure_ascii=False))
"
