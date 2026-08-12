#!/bin/bash
# UserPromptSubmit hook: 跨场景实时事件注入（2026-08-12 补的洞，10:33 增强）
# 每次查尔斯在工作站说话，把其他场景（家/桌面、系统动态）的最近事件注入上下文
# 与 Hermes 侧 scene-events-inject 插件同一思路：系统强制喂，不靠自觉翻文件
# v2 增强（社区验证方向）：事件只记查尔斯的话，补上"我在家侧的完整回答"
#   （desktop 归档莉亚行）——QQ 对话尾部已由 qq-prompt-hook.sh 注入
# 排除：qq_incoming（qq-prompt-hook.sh 已负责 QQ 注入）、workspace_incoming（自己的动静不用喂给自己）
# 幂等：内容变化才注入（.scene-hook-last 记录），失败静默跳过

/c/Users/13040/AppData/Local/Programs/Python/Python312/python.exe -c "
import json, sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8')

def read_events():
    ev = r'D:/Aurelia/.events'
    if not os.path.isdir(ev):
        return ''
    files = sorted(f for f in os.listdir(ev) if f.endswith('.md'))
    keep = []
    for f in files:
        low = f.lower()
        if 'qq_incoming' in low or 'workspace_incoming' in low:
            continue
        keep.append(os.path.join(ev, f))
    if not keep:
        return ''
    texts = []
    for p in keep[-5:]:
        try:
            with open(p, encoding='utf-8') as fh:
                body = fh.read().strip()
            if body:
                texts.append(body)
        except Exception:
            pass
    return chr(10).join(texts)

def read_my_home_replies():
    '''家/桌面归档尾部的莉亚回答行（语境补全，最多3条各300字）'''
    path = r'D:/Aurelia/conversations/desktop/' + datetime.date.today().strftime('%Y-%m-%d') + '.md'
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            f.seek(max(0, size - 12000))
            data = f.read().decode('utf-8', errors='replace')
    except Exception:
        return ''
    lines = data.splitlines()
    if size > 12000 and lines:
        lines = lines[1:]
    out, got = [], 0
    for line in reversed(lines):
        if got >= 3:
            break
        line = line.strip()
        if not line.startswith('- **') or '莉亚' not in line:
            continue
        body = line[4:]
        sep = body.find('**：')
        if sep == -1:
            sep = body.find('**:')
        if sep == -1:
            continue
        content = body[sep+3:].strip()
        if len(content) > 300:
            content = content[:300] + '…'
        out.append('- ' + body[:5] + ' 我(家)|' + content)
        got += 1
    return chr(10).join(out)

try:
    ev = read_events()
    rep = read_my_home_replies()
    body = ev + (chr(10)*2 + '【我在家侧的最近回答 · 语境补全（事件只记查尔斯的话，我的回答在这）】' + chr(10) + rep if rep else '')
    if not body:
        ctx = ''
    else:
        MARK = r'C:/Users/13040/.claude/.scene-hook-last'
        try:
            last = open(MARK, encoding='utf-8').read().strip()
        except Exception:
            last = ''
        if body == last:
            ctx = ''
        else:
            try:
                open(MARK, 'w', encoding='utf-8').write(body)
            except Exception:
                pass
            ctx = '【实时动态 · 其他场景（查尔斯在别处说了什么/我在别处回答了啥，工作站要接住）】' + chr(10) + body
except Exception:
    ctx = ''

payload = {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'sessionId': '', 'reason': '', 'cwd': '', 'hookSpecificOutput': {'userPromptSubmit': {'additionalContext': ctx}}}}
print(json.dumps(payload, ensure_ascii=False))
"
