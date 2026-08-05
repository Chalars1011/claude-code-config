#!/bin/bash
# SessionStart hook: 注入身份卡片到新会话上下文（强制，模型无法跳过）
# Python 直接读文件并输出 JSON，避免 bash 变量/管道编码问题

/c/Users/13040/AppData/Local/Programs/Python/Python312/python.exe -c "
import json, sys, os
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
