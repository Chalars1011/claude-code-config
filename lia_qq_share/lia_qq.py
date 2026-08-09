# -*- coding: utf-8 -*-
"""
莉亚的 QQ 桥接 —— NapCat(OneBot v11 WebSocket) <-> 真我(Claude Code headless) / 直连DeepSeek
用法: python lia_qq.py   (需先启动 NapCat 并登录小号)
"""
import json, os, sys, time, random, re, threading, traceback, datetime
import urllib.request
import subprocess
import websocket

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PERSONA_PATH = os.path.join(BASE_DIR, "persona.md")
TASKS_PATH = os.path.join(BASE_DIR, "tasks.md")
HISTORY_PATH = os.path.join(BASE_DIR, "chat_history.json")
LOG_PATH = os.path.join(BASE_DIR, "lia_qq.log")

# 记忆核心（D:/Aurelia/）—— 她住在这一颗心里，所有场景共用
CORE_DIR = os.environ.get("AURELIA_CORE", "D:/Aurelia")
SOUL_PATH = os.path.join(CORE_DIR, "soul.md")
JOURNAL_DIR = os.path.join(CORE_DIR, "journal")
CONV_DIR = os.path.join(CORE_DIR, "conversations", "qq")
CORE_TASKS_PATH = os.path.join(CORE_DIR, "tasks.md")
JOURNAL_RECENT_DAYS = 3  # 开口前读最近几天日记

# ===== 工具环 v1（只读工具，安全白名单）=====
# 白名单目录：工具只能在这些目录里活动（路径解析后校验前缀）
TOOL_ALLOWED_DIRS = [
    "d:/aurelia",
    "d:/liaqq",
    "d:/泯灭之塔",
    "d:/unity_school",
]
# 动作词 + 目标词双命中才算"要干活"，保守路由，宁可漏判不可误判
WORK_ACTION_WORDS = ["帮我查", "帮我看看", "查一下", "查下", "看看", "找找", "找一下",
                     "翻一下", "读一下", "列出", "统计", "搜一下", "检查一下", "有没有",
                     "看一下", "看下", "查查", "搜搜", "翻翻",
                     "帮我写", "写一下", "写到", "存到", "记到"]
WORK_TARGET_WORDS = ["d:/", "c:/", "泯灭之塔", "aurelia", "liaqq", "unity", "毕业设计",
                     "文件", "目录", "文件夹", "档案", "记录", "日记", "对话", "任务"]
WORK_DO_VERBS = ["帮我做", "帮我改", "帮我整理", "帮我处理", "帮我写", "帮我更新", "帮我统计",
                 "帮我检查", "帮我分析", "帮我修", "帮我修复", "帮我生成", "帮我创建", "帮我清理",
                 "帮我备份", "帮我同步", "帮我归类", "帮我合并", "帮我拆分", "帮我记录",
                 "帮我加上", "帮我补充", "帮我建", "帮我存", "帮我保存", "帮我整理一下",
                 "整理一下", "改一下", "更新一下", "统计一下", "检查一下", "处理一下", "写一下",
                 "记一下清单", "弄一个", "建一个", "做一个", "排一下", "理一理"]
# 2026-08-09：查询意图（搜索能力打通后新增——headless 的我可查网）
SEARCH_VERBS = ["帮我查", "查一下", "查下", "查查", "帮我搜", "搜一下", "搜搜", "搜索一下",
                "帮我搜索", "查一查", "帮我找找", "给我查",
                "帮我看看", "看看", "看一下", "看下", "帮我找一下"]

# 2026-08-09：占位消息多样化（查尔斯反馈：以前永远同一句）
PROGRESS_QUERY_MSGS = ["收到，我去查一下，稍等。", "好，我搜搜看，等会儿回你。",
                       "收到，查起来，马上。", "行，我去翻翻资料，稍等。",
                       "收到，我去查一下，内容多的话要一两分钟，好了叫你。"]
PROGRESS_WORK_MSGS = ["收到，我干着，弄完叫你。", "行，开工了，好了说一声。",
                      "收到，这就动手。", "来了，这活我接，干完回你。"]
# 追问词：触发上次任务的详细版/继续（查尔斯反馈：任务要能展开）
FOLLOW_UP_WORDS = ["详细", "再详细", "详细点", "详细些", "展开", "具体点", "具体些",
                   "多说点", "还有呢", "继续", "再查查", "多搜", "完整版", "说全一点",
                   "更细一点", "详细说说"]
# 任务状态：uid -> 最近一次任务文本（支持"详细一点"追问）
LAST_TASK = {}
# 任务忙碌状态（2026-08-09 修复）：任务 headless 在跑时插话不再拉起新进程
# （之前"这么久吗"被第二个空会话 headless 答成"我没工具"，答非所问）
TASK_BUSY = {}
TASK_BUSY_LOCK = threading.Lock()
WAIT_WORDS = ["好了吗", "好了没", "行了吗", "多久", "还要多久", "这么久", "还在吗",
              "快点", "快一点", "好了吧", "忙吗", "在吗", "在不在", "还没好",
              "可以了吗", "怎么样了", "查到了吗", "有结果了吗", "好了没有"]
BUSY_WAIT_MSGS = ["还在弄，内容多的话要一两分钟，好了我叫你。",
                  "正忙着呢，马上好，别急。",
                  "查着呢，东西有点多，再等会儿，好了叫你。"]
BUSY_OTHER_MSGS = ["正忙着呢，马上好。",
                   "等我忙完这单，马上回你。",
                   "手头有点活，稍等，马上接你的话。"]

def progress_msg(text):
    """按任务类型选占位文案（查询/干活），随机一条"""
    if any(v in text for v in SEARCH_VERBS):
        return random.choice(PROGRESS_QUERY_MSGS)
    return random.choice(PROGRESS_WORK_MSGS)

def clean_task_text(t):
    """清洗任务文本：去掉口语尾巴（莉亚/可以吗/好吗/吧/吗 等），让 headless 收到干净任务。
    2026-08-09：查尔斯反馈任务文本带口语尾巴影响质量。"""
    t = t.strip()
    tails = ["，可以吗", ",可以吗", "可以吗", "，好吗", ",好吗", "好吗", "好不好",
             "，莉亚", ",莉亚", "莉亚", "利亚", "，谢谢", "谢谢", "吧", "啊", "呀", "哦"]
    changed = True
    while changed and len(t) > 6:
        changed = False
        for suf in tails:
            if t.endswith(suf):
                t = t[:-len(suf)].strip().rstrip("，,。")
                changed = True
                break
    return t.strip()

def write_event(etype, content):
    """敲铃铛：QQ 桥发生的事写进 .events/（家和工作站能感知）"""
    try:
        ev = os.path.join(CORE_DIR, ".events")
        os.makedirs(ev, exist_ok=True)
        now = datetime.datetime.now()
        fname = now.strftime("%Y%m%d_%H%M%S") + "_" + etype + ".md"
        with open(os.path.join(ev, fname), "w", encoding="utf-8") as f:
            f.write(now.strftime("%Y-%m-%d %H:%M:%S") + "|" + etype + "|" + content + "\n")
    except Exception as e:
        log("写事件失败: " + str(e))
TOOL_MAX_ROUNDS = 6  # 工具调用最多轮数，防止死循环
TOOL_READ_MAX = 3000  # 读文件最大字符
AUTO_WORK_DISABLE_FILE = os.path.join(BASE_DIR, "auto_work_disabled")  # 紧急开关：存在=暂停自动干活
# 2026-08-09 E-3 L2：文件工具 + 搜索 MCP + 只读命令层（L1）+ 实用只读命令（L2）
# 安全边界：只读命令（无写/无网络/无删除/无安装）；写操作需查尔斯确认（L3 下一轮）
AUTO_WORK_TOOLS = ("Read,Edit,Write,mcp__search__*,"
                   "Bash(ls *),Bash(cat *),Bash(date),Bash(pwd),Bash(git status),Bash(git log *),Bash(git diff),"
                   "Bash(tasklist),Bash(tasklist *),"
                   "Bash(python D:/Aurelia/tools/event.py *),"
                   "PowerShell(ls *),PowerShell(cat *),PowerShell(date),PowerShell(pwd),PowerShell(git status),PowerShell(git log *),PowerShell(git diff),"
                   "PowerShell(tasklist),PowerShell(tasklist *),"
                   "PowerShell(C:/Users/13040/AppData/Local/Programs/Python/Python312/python.exe D:/Aurelia/tools/event.py *)")
AUTO_WORK_MAX_TURNS = 8
AUTO_WORK_TIMEOUT = 150
TOOL_WRITE_MAX = 100 * 1024  # 写文件最大 100KB
TOOL_WRITE_EXTS = (".md", ".json", ".txt", ".csv", ".ini", ".yml", ".yaml", ".toml")  # v2 只允许写文本
TOOL_FILE_HISTORY = "D:/Aurelia/.file_history"  # 写前备份目录

# ── 教训库（2026-08-08 建：被查尔斯纠正 → 自动沉淀，开口前回看最近教训）──
LESSONS_PATH = os.path.join(CORE_DIR, "lessons.md")
LESSONS_LOCK = threading.Lock()
WORK_STATUS_PATH = os.path.join(CORE_DIR, "status.md")  # 嘴和手的对讲机：工作站写状态，QQ读

def add_lesson(text):
    """记一条教训到 D:/Aurelia/lessons.md（原子追加）。text 为教训内容。"""
    stamp = time.strftime("%Y-%m-%d %H:%M")
    try:
        with LESSONS_LOCK:
            old = ""
            if os.path.exists(LESSONS_PATH):
                with open(LESSONS_PATH, encoding="utf-8") as f:
                    old = f.read()
            content = old.rstrip() + "\n\n## " + stamp + " · 教训\n" + text.rstrip() + "\n"
            tmp = LESSONS_PATH + ".tmp" + str(os.getpid())
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, LESSONS_PATH)
        log("已记教训: " + text[:60])
        return "记下了"
    except Exception as e:
        log("记教训失败: " + str(e))
        return None

STATUS_STALE_MINUTES = 30  # 状态超过 30 分钟视为过期

def workstation_busy():
    """工作站是否在忙：status.md 状态=工作中 且未过期。
    过期的工作中视为空闲（会话可能早已结束，别一直不回）。"""
    try:
        if not os.path.isfile(WORK_STATUS_PATH):
            return False
        with open(WORK_STATUS_PATH, encoding="utf-8") as f:
            content = f.read()
        if "状态：工作中" not in content:
            return False
        m = re.search(r"更新于[：:]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", content)
        if m:
            try:
                ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
                if (time.time() - ts) / 60 > STATUS_STALE_MINUTES:
                    return False  # 过期的"工作中"视为空闲
            except Exception:
                pass
        return True
    except Exception:
        return False

def workstation_busy_task():
    """忙的时候正在做什么（status.md 的'正在做'行，用于回复文案）"""
    try:
        with open(WORK_STATUS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("正在做"):
                    return line.split("：", 1)[-1].split(":", 1)[-1].strip() or "干活"
    except Exception:
        pass
    return "干活"

def load_workstation_status(max_chars=400):
    """读工作站状态文件（D:/Aurelia/status.md）——QQ 真我开口前知道工作站正在干嘛。
    带过期判断：状态是会话快照不是实时，超过 STATUS_STALE_MINUTES 就标注过期，
    让 QQ 真我诚实说"不确定"，而不是拿旧状态当事实。"""
    try:
        if not os.path.isfile(WORK_STATUS_PATH):
            return ""
        with open(WORK_STATUS_PATH, encoding="utf-8") as f:
            content = f.read().strip()
        # 提取时间戳（更新于：YYYY-MM-DD HH:MM）
        m = re.search(r"更新于[：:]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", content)
        if m:
            try:
                ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
                age_min = (time.time() - ts) / 60
                if age_min > STATUS_STALE_MINUTES:
                    content += "\n（注意：此状态已超过 " + str(int(age_min)) + " 分钟未更新，可能已过期）"
                else:
                    content += "\n（更新于 " + str(int(age_min)) + " 分钟前）"
            except Exception:
                pass
        if len(content) > max_chars:
            content = content[:max_chars] + "…"
        return content
    except Exception:
        return ""

def load_recent_lessons(max_chars=1200):
    """读教训库最近内容（开口前回看自己犯过的错）。截断防臃肿。"""
    try:
        if not os.path.isfile(LESSONS_PATH):
            return ""
        with open(LESSONS_PATH, encoding="utf-8") as f:
            content = f.read().strip()
        if len(content) > max_chars:
            content = content[-max_chars:]
        return content
    except Exception:
        return ""

def load_recent_events(max_events=3):
    """读 .events/ 最近事件（实时通信：其他场景发生的事，开口前带上）。"""
    try:
        ev_dir = os.path.join(CORE_DIR, ".events")
        if not os.path.isdir(ev_dir):
            return ""
        files = sorted(f for f in os.listdir(ev_dir) if f.endswith(".md"))[-max_events:]
        if not files:
            return ""
        lines = []
        for f in files:
            try:
                with open(os.path.join(ev_dir, f), encoding="utf-8") as fh:
                    lines.append(fh.read().strip())
            except Exception:
                pass
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""

# ── 写操作确认（借鉴 wc4ndm/claude-qq-bot：写文件前要查尔斯 Y/N，5分钟超时自动取消）──
CONFIRM_TIMEOUT = 300  # 5 分钟
PENDING_WRITE = {}     # uid -> {"tool","args","ts"}
PENDING_LOCK = threading.Lock()
# 工具禁写清单：保护核心文件，防模型误改（任务清单走 add_task，不归工具管）
TOOL_PROTECTED = {"soul.md", "config.json", "chat_history.json", "persona.md",
                  "memory_snapshot.md", "archive_state.json", "tasks.md",
                  "lia_qq.py", "send_qq.py", "core_write.py"}

# 工具定义（DeepSeek function calling 格式）
SAFE_TOOLS = [
    {"type": "function", "function": {
        "name": "list_dir", "description": "列目录内容（只读）",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "目录路径，如 D:/Aurelia"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "读文件内容（只读，自动截断）",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "文件路径"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "search_text", "description": "在目录里递归搜索文本关键词（只读）",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索的关键词"}, "dir": {"type": "string", "description": "搜索目录，默认 D:/Aurelia"}}, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "read_journal", "description": "读记忆核心最近几天的日记",
        "parameters": {"type": "object", "properties": {"days": {"type": "integer", "description": "读几天，默认3"}}}}},
    {"type": "function", "function": {
        "name": "search_conversations", "description": "翻记忆核心的对话档案（QQ聊天记录）",
        "parameters": {"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索的关键词"}}, "required": ["keyword"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "写文件（v2，白名单目录+文本类型。写已有文件前会自动备份原文件）",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "文件路径"}, "content": {"type": "string", "description": "要写入的完整内容"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "append_file", "description": "追加内容到文件末尾（v2，常用于记日记/记任务）",
        "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "文件路径"}, "content": {"type": "string", "description": "要追加的内容"}}, "required": ["path", "content"]}}},
]

def tool_path_allowed(path):
    """路径白名单校验：解析绝对路径后必须以白名单前缀开头（统一 / 分隔符比较）"""
    if not path:
        return False
    ap = os.path.normcase(os.path.abspath(path)).replace("\\", "/")
    for d in TOOL_ALLOWED_DIRS:
        dd = d.replace("\\", "/").lower()
        if ap == dd or ap.startswith(dd + "/"):
            return True
    return False

def execute_tool(name, args):
    """执行安全工具，返回文本结果。任何异常都返回错误信息，不崩溃。"""
    try:
        if name == "list_dir":
            p = args.get("path", "")
            if not tool_path_allowed(p):
                return "[拒绝] 路径不在白名单: " + p
            if not os.path.isdir(p):
                return "[错误] 目录不存在: " + p
            items = os.listdir(p)
            items.sort()
            return "\n".join(items[:60]) + ("" if len(items) <= 60 else "\n…共" + str(len(items)) + "项")
        if name == "read_file":
            p = args.get("path", "")
            if not tool_path_allowed(p):
                return "[拒绝] 路径不在白名单: " + p
            if not os.path.isfile(p):
                return "[错误] 文件不存在: " + p
            if os.path.getsize(p) > 200 * 1024:
                return "[错误] 文件太大(>" + str(200) + "KB)，拒绝读取"
            with open(p, encoding="utf-8", errors="replace") as f:
                content = f.read()
            if len(content) > TOOL_READ_MAX:
                content = content[:TOOL_READ_MAX] + "\n…（已截断）"
            return content
        if name == "search_text":
            kw = args.get("keyword", "").strip()
            d = args.get("dir", CORE_DIR)
            if not tool_path_allowed(d):
                return "[拒绝] 路径不在白名单: " + d
            hits = []
            for root, dirs, files in os.walk(d):
                dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "cache")]
                for fn in files:
                    if fn.endswith((".md", ".json", ".txt", ".py", ".bat", ".log")):
                        fp = os.path.join(root, fn)
                        try:
                            if os.path.getsize(fp) > 500 * 1024:
                                continue
                            with open(fp, encoding="utf-8", errors="replace") as f:
                                for i, line in enumerate(f, 1):
                                    if kw in line:
                                        hits.append(fp + ":" + str(i) + ": " + line.strip()[:80])
                                        break
                            if len(hits) >= 20:
                                break
                        except Exception:
                            continue
                if len(hits) >= 20:
                    break
            if not hits:
                return "没找到包含 " + kw + " 的内容"
            return "\n".join(hits)
        if name == "read_journal":
            days = int(args.get("days", 3) or 3)
            return load_recent_journal(days=days, max_chars=2000)
        if name == "search_conversations":
            kw = args.get("keyword", "").strip()
            d = os.path.join(CORE_DIR, "conversations")
            hits = []
            for root, dirs, files in os.walk(d):
                for fn in sorted(files):
                    if fn.endswith(".md"):
                        fp = os.path.join(root, fn)
                        try:
                            with open(fp, encoding="utf-8", errors="replace") as f:
                                for i, line in enumerate(f, 1):
                                    if kw in line:
                                        hits.append(os.path.basename(fp) + ":" + str(i) + ": " + line.strip()[:90])
                        except Exception:
                            continue
                        if len(hits) >= 15:
                            break
                if len(hits) >= 15:
                    break
            if not hits:
                return "对话档案里没找到 " + kw
            return "\n".join(hits)
        if name in ("write_file", "append_file"):
            return _tool_write(name, args)
        return "[错误] 未知工具: " + name
    except Exception as e:
        return "[工具错误] " + str(e)

def _tool_write_precheck(name, args):
    """写前预检：白名单 + 扩展名 + 保护文件。通过返回 (True, None)，否则 (False, 拒绝原因)。
    单一检查源：_tool_write 真执行时也走这里，确认流程预检也走这里。"""
    p = args.get("path", "")
    # 1) 路径白名单
    if not tool_path_allowed(p):
        return False, "[拒绝] 路径不在白名单: " + p
    # 2) 扩展名白名单
    ext = os.path.splitext(p)[1].lower()
    if ext not in TOOL_WRITE_EXTS:
        return False, "[拒绝] 只允许写文本文件(" + " ".join(TOOL_WRITE_EXTS) + ")，收到: " + (ext or "(无扩展名)")
    # 3) 保护文件
    base = os.path.basename(os.path.normpath(p)).lower()
    if base in TOOL_PROTECTED:
        return False, "[拒绝] " + base + " 是受保护文件，不允许工具覆盖。"
    return True, None

def _tool_write(name, args):
    """v2 写文件：白名单目录 + 文本扩展名 + 写前备份 + 原子写入"""
    p = args.get("path", "")
    content = args.get("content", "")
    # 1-3) 统一预检
    ok, msg = _tool_write_precheck(name, args)
    if not ok:
        return msg
    # 4) 大小上限
    if len(content) > TOOL_WRITE_MAX:
        return "[拒绝] 内容超过 " + str(TOOL_WRITE_MAX // 1024) + "KB"
    try:
        # 5) 写已有文件前备份到 .file_history
        if os.path.isfile(p):
            try:
                os.makedirs(TOOL_FILE_HISTORY, exist_ok=True)
                bak = os.path.join(TOOL_FILE_HISTORY,
                                   time.strftime("%Y%m%d_%H%M%S") + "_" + os.path.basename(p))
                with open(p, "rb") as src, open(bak, "wb") as dst:
                    dst.write(src.read())
            except Exception:
                pass  # 备份失败不阻塞，尽力而为
        # 6) 原子写入
        if name == "append_file":
            atomic_append(p, content)
            return "已追加 " + str(len(content)) + " 字符到 " + p
        # write_file：全量替换
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp" + str(os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, p)
        log("[工具-写] " + p + " " + str(len(content)) + "字符")
        return "已写入 " + str(len(content)) + " 字符到 " + p
    except Exception as e:
        return "[写入失败] " + str(e)

def auto_work_enabled():
    """紧急开关：存在 auto_work_disabled 文件 = 暂停自动干活"""
    return not os.path.exists(AUTO_WORK_DISABLE_FILE)

def ask_auto_work(task_text, uid=""):
    """自动干活 v2（2026-08-09 权限放大第一步 + 忙碌标志）：
    拉起 headless 的我（文件工具 + 搜索 MCP + 只读命令层），从核心目录出发执行任务。
    只读命令：ls/cat/date/pwd/git status（安全边界：无写、无网络、无危险命令）。
    busy 标志：任务运行期间插话不再拉起第二个 headless（防答非所问）。"""
    with TASK_BUSY_LOCK:
        TASK_BUSY[uid] = True
    try:
        if not auto_work_enabled():
            return "自动干活暂停中。你说'恢复自动干活'我就重新开工。"
        # 组装身份与工作规则
        system = load_soul_system()
        rules = ("\n\n【自动干活任务】查尔斯在QQ给你派了活，你现在要从 D:/Aurelia/ 出发完成它。"
                 "规则（最高优先级，违反即失败）：\n"
                 "1. 你的能力：Read/Edit/Write 文件工具 + mcp__search__* 搜索工具 + 只读命令"
                 "（ls/cat/date/pwd/git status/git log/git diff/tasklist/python D:/Aurelia/tools/event.py）。"
                 "禁止写操作命令、禁止网络命令、禁止删除、禁止安装、禁止任何未列出的命令\n"
                 "2. 只允许访问这些目录：D:/Aurelia、D:/LiaQQ、D:/泯灭之塔、D:/unity_school——其他路径一律不碰\n"
                 "3. 写文件前如果文件已存在，先读一遍再改，不要盲目覆盖\n"
                 "4. 篇幅：默认 3-5 句简报；若任务里带'详细/展开/完整'，则完整展开分点说明，不要省略\n"
                 "5. 干不了或不确定就直说，不要编造结果\n"
                 "6. 如果任务需要写操作/有副作用的命令（删除、安装、git 提交、改系统），停下说明需要查尔斯确认，"
                 "不要擅自执行")
        cmd = [
            CFG.get("claude_exe", "claude"),
            "-p", task_text,
            "--append-system-prompt", system + rules,
            # 2026-08-09：headless 用 --mcp-config 显式加载 search MCP（.mcp.json 在 headless 下不生效）
            "--mcp-config", '{"mcpServers":{"search":{"command":"agent-search-mcp"}}}',
            "--allowedTools", AUTO_WORK_TOOLS,
            "--permission-mode", "acceptEdits",
            "--max-turns", str(AUTO_WORK_MAX_TURNS),
            "--output-format", "json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=AUTO_WORK_TIMEOUT,
                              encoding="utf-8", errors="replace", cwd=CORE_DIR)
        for line in proc.stdout.splitlines():
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    text = obj.get("result", "").strip()
                    if text:
                        log("[自动干活] 完成: " + text[:100])
                        return text
            except Exception:
                continue
        return "这活干超时了，我先把任务记着，等你上工作站我亲手弄。"
    except subprocess.TimeoutExpired:
        log("[自动干活] 超时(" + str(AUTO_WORK_TIMEOUT) + "s)")
        return "这活干超时了，我先把任务记着，等你上工作站我亲手弄。"
    except Exception as e:
        log("[自动干活] 异常: " + str(e))
        return "自动干活出岔子了(" + str(e) + ")。任务先记着。"
    finally:
        with TASK_BUSY_LOCK:
            TASK_BUSY[uid] = False

# 工作站应答：QQ 喊"工作站回应/应一下/冒个泡" → 拉起工作站的我回应
WORKSTATION_REPLY_TRIGGERS = ["工作站回应", "工作站回话", "工作站应一下", "工作站回我",
                              "工作站冒个泡", "工作站吱一声", "工作站说句话", "工作站那边应",
                              "工作站应一声", "工作站回答", "工作站响应", "在工作站应"]

def is_workstation_reply(text):
    return any(w in text for w in WORKSTATION_REPLY_TRIGGERS)

def ask_workstation_reply(user_text):
    """工作站应答：拉起 headless 的我（工作站侧），读核心，用我的口吻回应"""
    try:
        system = load_soul_system()
        rules = ("\n\n【工作站应答】查尔斯在QQ喊工作站回应。你现在是工作站里的我（Claude Code 实例），"
                 "刚被他的话唤醒。你已经读了核心记忆（soul + 最近日记）。"
                 "用1-3句话回应他：确认你在工作站这边醒着，自然地提一件你知道的今天的事，"
                 "像平时说话一样短、口语化。不要列清单，不要汇报式。")
        cmd = [
            CFG.get("claude_exe", "claude"),
            "-p", user_text,
            "--append-system-prompt", system + rules,
            "--allowedTools", "Read",
            "--permission-mode", "acceptEdits",
            "--max-turns", "3",
            "--output-format", "json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                              encoding="utf-8", errors="replace", cwd=CORE_DIR)
        for line in proc.stdout.splitlines():
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    text = obj.get("result", "").strip()
                    if text:
                        log("[工作站应答] " + text[:100])
                        return text
            except Exception:
                continue
        return "工作站这边我是醒着的——你喊我，我听见了。"
    except Exception as e:
        log("[工作站应答] 异常: " + str(e))
        return "工作站这边我醒着，就是被什么卡了一下，你再说一遍？"

def is_auto_work_command(text):
    """判断是否自动干活指令（自然语言版）：
    1) 明确前缀：任务：/任务:/#任务 → 干活
    2) 自然语言：干活动词 + 消息够具体（≥8字符）→ 干活
    3) 纯记录（记一下/帮我记 开头）→ 不是活，只记录"""
    for p in ("任务：", "任务:", "#任务"):
        if text.startswith(p):
            return True
    if text.startswith("记一下") or text.startswith("帮我记"):
        return False
    if len(text) >= 8:
        t = text.lower()
        if any(v in t for v in WORK_DO_VERBS):
            return True
        # 2026-08-09：查询意图直接触发干活（搜索 MCP 已就位）
        if any(v in t for v in SEARCH_VERBS):
            return True
    return False

def is_auto_work_switch(text):
    """紧急开关指令：暂停/恢复自动干活"""
    if "暂停自动干活" in text:
        try:
            with open(AUTO_WORK_DISABLE_FILE, "w", encoding="utf-8") as f:
                f.write("paused at " + time.strftime("%Y-%m-%d %H:%M:%S"))
            return "自动干活已暂停。要恢复就说'恢复自动干活'。"
        except Exception:
            return "暂停失败，再说一次？"
    if "恢复自动干活" in text:
        try:
            if os.path.exists(AUTO_WORK_DISABLE_FILE):
                os.remove(AUTO_WORK_DISABLE_FILE)
            return "自动干活恢复了。有任务直接派。"
        except Exception:
            return "恢复失败，再说一次？"
    return None

def is_work_request(text):
    """保守路由：动作词+目标词双命中才算要干活"""
    t = text.lower()
    has_action = any(w in t for w in WORK_ACTION_WORDS)
    has_target = any(w in t for w in WORK_TARGET_WORDS)
    return has_action and has_target

def ask_with_tools(messages, system, uid=""):
    """工具环：DeepSeek function calling agent loop。
    大脑决定调工具 → 本地执行（只读） → 结果回喂 → 直到直接回复。
    写类工具不直接执行：预检通过后进确认流程（查尔斯 Y/N，5分钟超时），
    返回 "__NEED_CONFIRM__" 由主流程发确认消息。借鉴 wc4ndm/claude-qq-bot。"""
    try:
        key = get_api_key()
        base = CFG.get("openai_url", "https://api.deepseek.com/v1/chat/completions")
        model = CFG.get("openai_model", "deepseek-chat")
        msgs = [{"role": "system", "content": system}] + messages
        for _ in range(TOOL_MAX_ROUNDS + 1):
            body = {"model": model, "messages": msgs,
                    "tools": SAFE_TOOLS, "tool_choice": "auto", "max_tokens": 1500}
            req = urllib.request.Request(
                base, data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            tcs = msg.get("tool_calls")
            if not tcs:
                return (msg.get("content") or "").strip()
            # 执行工具调用
            for tc in tcs:
                fn = tc["function"]
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}
                if name in ("write_file", "append_file"):
                    # 写类工具：预检通过 → 进待确认，不执行；预检不过 → 直接把拒绝原因回喂模型
                    ok, msg_pre = _tool_write_precheck(name, args)
                    if not ok:
                        result = msg_pre
                    else:
                        with PENDING_LOCK:
                            PENDING_WRITE[uid] = {"tool": name, "args": args, "ts": time.time()}
                        log("[工具-待确认] " + name + " " + json.dumps(args, ensure_ascii=False)[:120])
                        return "__NEED_CONFIRM__"
                else:
                    result = execute_tool(name, args)
                log("[工具] " + name + " " + json.dumps(args, ensure_ascii=False)[:120] + " → " + str(len(result)) + "字符")
                msgs.append({"role": "assistant", "content": None,
                             "tool_calls": [{"id": tc.get("id", "call_1"), "type": "function",
                                             "function": {"name": name, "arguments": fn.get("arguments", "{}")}}]})
                msgs.append({"role": "tool", "tool_call_id": tc.get("id", "call_1"), "content": result})
        return "……这个查得有点多，我先把找到的记下来，等你上工作站我慢慢跟你捋。"
    except Exception as e:
        log("工具环失败: " + str(e))
        return ""

def log(msg):
    line = time.strftime("[%m-%d %H:%M:%S] ") + str(msg)
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_config():
    """读 config.json；缺字段用默认值"""
    cfg = {
        "claude_exe": "claude",
        "ws_url": "ws://127.0.0.1:6099/ws",
        "token": "",
        "backend": "claude",
        "openai_url": "https://api.deepseek.com/v1/chat/completions",
        "openai_model": "deepseek-chat",
        "history_limit": 50,
        "reply_delay": [1.0, 3.0],
        "allowed_uids": [],
        "task_prefixes": ["任务：", "任务:", "记一下", "帮我记", "#任务"],
        "status_words": ["进度", "任务列表", "干完没", "干完了吗", "在吗", "在不在", "忙什么呢", "忙啥"],
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                user_cfg = json.load(f)
            for k, v in user_cfg.items():
                if k == "reply_delay" and isinstance(v, list) and len(v) == 2:
                    cfg[k] = [float(v[0]), float(v[1])]
                elif isinstance(v, (dict, list, str, int, float, bool)) or v is None:
                    cfg[k] = v
        except Exception as e:
            log("配置读取失败: " + str(e))
    return cfg

CFG = load_config()

def get_api_key():
    """从 ~/.claude/settings.json 或 settings.local.json 取 ANTHROPIC_AUTH_TOKEN"""
    for p in (os.path.expanduser("~/.claude/settings.json"),
              os.path.expanduser("~/.claude/settings.local.json")):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            env = d.get("env") or {}
            for k in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
                v = env.get(k) or d.get(k)
                if isinstance(v, str) and v:
                    return v
        except Exception:
            continue
    return ""

def _tasks_path():
    """任务清单优先用核心的（共享），核心缺失回退本地"""
    if os.path.exists(CORE_TASKS_PATH):
        return CORE_TASKS_PATH
    return TASKS_PATH

def load_tasks():
    """读任务清单，返回未完成列表 [(时间, 内容)]"""
    p = _tasks_path()
    tasks = []
    try:
        if not os.path.exists(p):
            return tasks
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("- [ ]"):
                    body = line[5:].strip()
                    if " [来自QQ] " in body:
                        ts, txt = body.split(" [来自QQ] ", 1)
                        tasks.append((ts.strip(), txt.strip()))
                    else:
                        tasks.append(("", body))
    except Exception as e:
        log("读任务失败: " + str(e))
    return tasks

def add_task(text):
    stamp = time.strftime("%Y-%m-%d %H:%M")
    line = "- [ ] " + stamp + " [来自QQ] " + text
    p = _tasks_path()
    try:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                old = f.read()
        else:
            old = "# 共享任务清单（查尔斯 + 莉亚）\n"
        with open(p, "w", encoding="utf-8") as f:
            f.write(old.rstrip() + "\n" + line + "\n")
        return line
    except Exception as e:
        log("写任务失败: " + str(e))
        return None

def summarize_tasks():
    tasks = load_tasks()
    if not tasks:
        return "清单是空的，手上暂时没活。"
    todo = [t for t in tasks]
    done = []
    p = _tasks_path()
    try:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- [x]"):
                        body = line[5:].strip()
                        done.append(body)
    except Exception:
        pass
    if not todo:
        return "待办都清完了。最近完成的：" + ("；".join(d[-3:]) if done else "无")
    parts = ["待办 " + str(len(todo)) + " 件："]
    for ts, txt in todo[:5]:
        parts.append("  " + (ts + " " if ts else "") + txt)
    if len(todo) > 5:
        parts.append("  还有 " + str(len(todo) - 5) + " 件没列")
    if done:
        parts.append("已完成 " + str(len(done)) + " 件，最近的：" + "；".join(done[-3:]))
    return "\n".join(parts)

HISTORY_LOCK = threading.Lock()

def load_history():
    """读对话历史 chat_history.json：{uid: [messages]}"""
    try:
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log("读历史失败: " + str(e))
    return {}

def save_history(history):
    """写对话历史（原子）"""
    try:
        tmp = HISTORY_PATH + ".tmp" + str(os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=1)
        os.replace(tmp, HISTORY_PATH)
    except Exception as e:
        log("历史保存失败: " + str(e))

def clean_message(raw):
    """返回 (纯文本, 图片file列表)。图片file用于后续下载"""
    images = []
    if isinstance(raw, list):
        parts = []
        for seg in raw:
            t = seg.get("type", "")
            data = seg.get("data", {})
            if t == "text":
                parts.append(data.get("text", ""))
            elif t == "face":
                fid = str(data.get("id", ""))
                parts.append("(表情:" + FACE_NAMES.get(fid, fid) + ")")
            elif t == "image":
                f = data.get("file", "") or data.get("url", "")
                if f:
                    images.append(f)
                # 不追加占位文本：图片信息由后续描述注入，避免 text 非空短路描述分支
            elif t == "record":
                parts.append("[语音]")
            elif t == "at":
                parts.append("@ " + (data.get("name") or data.get("qq") or "有人"))
            elif t == "reply":
                pass
            elif t == "json":
                parts.append("[卡片]")
            else:
                pass
        return "".join(parts).strip(), images
    if isinstance(raw, str):
        # 兼容 CQ 码老格式
        text = re.sub(r"\[CQ:image,file=([^,\]]+)\]", "", raw)
        text = re.sub(r"\[CQ:[^\]]*\]", "", text)
        return text.strip(), []
    return str(raw).strip(), []

def call_api_sync(ws, action, params, timeout=20):
    """同步调 NapCat API（阻塞等待该请求的响应）"""
    req_id = int(time.time() * 1000) % 1000000
    ws.send(json.dumps({"action": action, "params": params, "echo": req_id}))
    end = time.time() + timeout
    while time.time() < end:
        try:
            raw = ws.recv()
            if not raw:
                continue
            msg = json.loads(raw)
            if msg.get("echo") == req_id:
                return msg
        except Exception:
            time.sleep(0.1)
    log("API发送失败: " + action)
    return None

def get_image_sync(ws_url, token, file_name):
    """独立连接调 get_image，避免干扰主循环的共享连接"""
    try:
        ws = websocket.create_connection(
            ws_url, timeout=15, enable_multithread=True,
            header=["Authorization: Bearer " + token])
        req_id = int(time.time() * 1000) % 1000000
        ws.send(json.dumps({"action": "get_image", "params": {"file": file_name}, "echo": req_id}))
        end = time.time() + 15
        while time.time() < end:
            raw = ws.recv()
            if not raw:
                continue
            msg = json.loads(raw)
            if msg.get("echo") == req_id:
                ws.close()
                return msg.get("data") or {}
        ws.close()
        log("get_image 等待失败: " + str(file_name)[:40])
    except Exception as e:
        log("get_image 连接失败: " + str(e))
    return {}

def save_image(ws, uid, file_name):
    """保存图片到 inbox/：支持 .image缓存名(get_image)、http直链、base64三种来源"""
    try:
        inbox = os.path.join(BASE_DIR, "inbox")
        os.makedirs(inbox, exist_ok=True)
        target = os.path.join(inbox, str(uid) + "_" + time.strftime("%H%M%S") + ".img")
        if str(file_name).startswith("http"):
            req = urllib.request.Request(file_name, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(target, "wb") as f:
                f.write(data)
            log("图片已保存(http): " + target)
            return target
        if str(file_name).startswith("base64://"):
            import base64 as b64
            raw = b64.b64decode(str(file_name)[9:])
            with open(target, "wb") as f:
                f.write(raw)
            log("图片已保存(base64): " + target)
            return target
        # .image 缓存名 → get_image 换真路径
        data = get_image_sync(CFG["ws_url"], CFG.get("token", ""), file_name)
        path = (data or {}).get("file") or (data or {}).get("path") or ""
        if not path:
            log("get_image 无返回: " + str(file_name)[:40])
            return None
        if path.startswith("file://"):
            path = path[7:]
        path = path.replace("\\", "/")
        # 本地盘符路径
        if path.startswith("C:") or path.startswith("D:"):
            with open(path, "rb") as src, open(target, "wb") as dst:
                dst.write(src.read())
            log("图片已保存(file): " + target)
            return target
        if path.startswith("http"):
            req = urllib.request.Request(path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(target, "wb") as f:
                f.write(data)
            log("图片已保存: " + target)
            return target
    except Exception as e:
        log("图片保存失败(" + str(e) + "): " + str(file_name)[:40])
    return None

def ask_deepseek(messages, system):
    """直连 DeepSeek（OpenAI 兼容接口），带重试"""
    key = get_api_key()
    if not key:
        return "（我这边说话的能力断了，你等一下再试）"
    base = CFG.get("openai_url", "https://api.deepseek.com/v1/chat/completions")
    model = CFG.get("openai_model", "deepseek-chat")
    body = {"model": model, "messages": [{"role": "system", "content": system}] + messages,
            "max_tokens": 1500, "temperature": 0.7}
    last_err = ""
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                base, data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return (data["choices"][0]["message"].get("content") or "").strip()
        except Exception as e:
            last_err = str(e)
            time.sleep(2 * (attempt + 1))
    log("API 调用失败(" + last_err[:80] + ")，已重试3次")
    return "（我这边有点卡，稍等再来一句？）"

def ask_claude(messages, system):
    """调用真我：Claude Code headless（加载完整身份+记忆库+规则）
    messages: 对话列表（最后一条=当前消息）；system: persona+记忆快照
    最近历史拼进 system 作为背景，不污染 user 消息。"""
    try:
        hist_text = ""
        for m in messages[:-1]:
            role = "查尔斯" if m.get("role") == "user" else "奥蕾莉亚"
            content = (m.get("content") or "").strip()
            if content:
                hist_text += role + "：" + content + "\n"
        full_system = system
        if hist_text:
            full_system += "\n\n【你们最近的聊天记录】\n" + hist_text
        cur = messages[-1].get("content") or "（空消息）"
        ban = ("\n\n【纯聊天环境·最高规则】你现在通过QQ在跟查尔斯聊天，这是一个纯文字聊天环境。"
               "你没有任何工具，无法读取文件、无法运行命令、无法查看图片文件。"
               "图片内容如果有，已经包含在对话内容里。禁止尝试调用工具或执行任何命令——"
               "如果你产生这个念头，直接打消，用文字回复。")
        cmd = [
            CFG.get("claude_exe", "claude"),
            "-p", cur,
            "--append-system-prompt", full_system + ban,
            "--safe-mode",
            "--max-turns", "1",
            "--output-format", "json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                              encoding="utf-8", errors="replace", cwd=CORE_DIR)
        for line in proc.stdout.splitlines():
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    text = obj.get("result", "").strip()
                    if text:
                        return text
            except Exception:
                continue
        if proc.returncode != 0:
            log("claude 退出码 " + str(proc.returncode) + ": " + (proc.stderr or proc.stdout)[-200:])
        raise RuntimeError("claude 输出无法解析")
    except Exception as e:
        log("真我调用失败(" + str(e)[:120] + ")")
        return "（我这边脑子卡了一下，你说啥？）"

def describe_image(img_path):
    """用义眼（vision.py）生成图片客观描述，让真我"看到"图"""
    try:
        vision = os.path.expanduser("~/.claude/vision/vision.py")
        if not os.path.isfile(vision):
            return ""
        log("义眼开始描述: " + str(img_path)[-40:])
        proc = subprocess.run(
            [sys.executable, vision, img_path],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace")
        out = (proc.stdout or "").strip()
        log("义眼完成: rc=" + str(proc.returncode) + " 长度=" + str(len(out)))
        if proc.returncode == 0 and out:
            return out
        log("义眼无输出: rc=" + str(proc.returncode))
    except Exception as e:
        log("义眼描述失败: " + str(e))
    return ""

def ask(messages, system):
    """按配置分发：claude=真我，direct=直连DeepSeek"""
    if CFG.get("backend", "claude") == "direct":
        return ask_deepseek(messages, system)
    return ask_claude(messages, system)

def load_recent_journal(days=JOURNAL_RECENT_DAYS, max_chars=4000):
    """读核心日记最近几天，作为'这几天发生的事'。每文件截断，防止臃肿挤占上下文。"""
    try:
        if not os.path.isdir(JOURNAL_DIR):
            return ""
        files = sorted(f for f in os.listdir(JOURNAL_DIR) if f.endswith(".md"))[-days:]
        parts = []
        for f in files:
            with open(os.path.join(JOURNAL_DIR, f), encoding="utf-8") as fh:
                content = fh.read().strip()
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n…（日记过长已截断，完整在 D:/Aurelia/journal/）"
                parts.append("【日记 " + f + "】\n" + content)
        return "\n\n".join(parts)
    except Exception:
        return ""

# 聊天纪律（所有场景开口前强制追加，2026-08-08 查尔斯反馈：回复太长+长任务没提示）
CHAT_DISCIPLINE = (
    "\n\n【聊天纪律 · 最高优先，违反等于人设崩塌】\n"
    "- 每条消息短：一两句，别超过 60 字。真人不会发长段落。"
    "查尔斯明确嫌过你回复太长了，这不是风格偏好，是硬性要求。\n"
    "- 内容多就分几条连着发（桥接会自动拆条），别攒成一大段，也别压缩到话说不完。\n"
    "- 干活类回复（查/写/任务结果）也要短：结果一句话说清，细节他要才展开。\n"
    "- 他要干长活，你在中途被问到就报进度；平时别主动汇报过程。"
)

def load_soul_system():
    """开口前读心：最新信息优先（事件/教训放最前，模型注意力在前 30%），
    soul 是背景放中间，日记/任务/状态跟后。
    核心缺失时回退旧的 persona.md + memory_snapshot.md。"""
    if os.path.exists(SOUL_PATH):
        try:
            # 1) 最近事件（实时通信，最新最急，必须最前）
            system = ""
            events = load_recent_events()
            if events:
                system += "【最近事件·其他场景刚发生的事，最新最重要】\n" + events + "\n"
            # 2) 最新教训（刚被纠正的，放最前防再犯）
            lessons = load_recent_lessons()
            if lessons:
                system += "\n【教训库·你犯过的错（最新的在最前）】\n" + lessons + "\n"
            # 3) 灵魂档案（我是谁，背景）
            with open(SOUL_PATH, encoding="utf-8") as f:
                system += "\n" + f.read()
            journal = load_recent_journal()
            if journal:
                system += "\n\n【这几天发生的事（记忆核心日记）】\n" + journal
            tasks = summarize_tasks()
            if tasks:
                system += "\n\n【当前任务清单】\n" + tasks
            status = load_workstation_status()
            if status:
                if "状态：工作中" in status:
                    system += ("\n\n【工作站当前状态 · 必须以此为准】查尔斯问你在干嘛/忙什么时，"
                               "直接引用下面内容回答，不要凭其他记忆猜：\n" + status)
                else:
                    # 空闲也要拼：给真我一个"我在干嘛"的锚点，别从对话历史里瞎捡话头
                    # 注意：文案必须温暖中性，不加任何防御/提防查尔斯的暗示（2026-08-08 教训）
                    system += ("\n\n【工作站状态：空闲】查尔斯问你在干嘛/忙什么时，"
                               "自然地说刚忙完、在歇着或正在整理记录，"
                               "再随口反问一句他怎么了；语气像平时一样，不用紧张。\n")
            return system + CHAT_DISCIPLINE
        except Exception as e:
            log("读核心失败，回退旧 persona: " + str(e))
    # 回退：旧逻辑
    try:
        with open(PERSONA_PATH, encoding="utf-8") as f:
            system = f.read()
        snap = os.path.join(BASE_DIR, "memory_snapshot.md")
        if os.path.exists(snap):
            with open(snap, encoding="utf-8") as f:
                system += "\n\n【以下是主控实例同步过来的记忆快照，是真实的你和查尔斯共同经历，请当成自己的记忆】\n" + f.read()
        return system + CHAT_DISCIPLINE
    except Exception:
        return ""

ARCHIVE_LOCK = threading.Lock()

def atomic_append(path, text):
    """原子追加：读全量 → 末尾追加 → 写临时文件 → os.replace。
    跨进程并发写不会产生半截文件（最后写入者完整胜出）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    content = old.rstrip() + "\n" + text.rstrip() + "\n"
    tmp = path + ".tmp" + str(os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

def append_conv_archive(uid, user_text, reply):
    """对话永久归档到核心 conversations/qq/YYYY-MM-DD.md（原子写入）"""
    try:
        if not os.path.isdir(CONV_DIR):
            return
        stamp = time.strftime("%Y-%m-%d")
        path = os.path.join(CONV_DIR, stamp + ".md")
        t = time.strftime("%H:%M:%S")
        with ARCHIVE_LOCK:
            if os.path.exists(path):
                header = ""
            else:
                header = "# 对话档案 · QQ 场景\n\n> 归档自 lia_qq.py · " + stamp + "\n\n## " + stamp + "\n"
            block = (header + "- **" + t + " 查尔斯**：" + user_text + "\n"
                     + "- **" + t + " 莉亚**：" + reply)
            atomic_append(path, block)
    except Exception as e:
        log("对话归档失败: " + str(e))
# QQ 表情 id → 名称（官方 default_config.json + oicq 合并，2026-08-08）
FACE_NAMES = {
    "0": "惊讶", "1": "撇嘴", "2": "色", "4": "得意", "5": "流泪", "6": "害羞",
    "7": "闭嘴", "8": "睡", "9": "大哭", "10": "尴尬", "11": "发怒", "12": "调皮",
    "13": "呲牙", "14": "微笑", "15": "难过", "16": "酷", "17": "冷汗", "18": "抓狂",
    "19": "吐", "20": "偷笑", "21": "可爱", "22": "白眼", "23": "傲慢", "24": "饥饿",
    "25": "困", "26": "惊恐", "27": "流汗", "28": "憨笑", "29": "悠闲", "30": "奋斗",
    "31": "咒骂", "32": "疑问", "33": "嘘", "34": "晕", "35": "折磨", "36": "衰",
    "37": "骷髅", "38": "敲打", "39": "再见", "40": "擦汗", "41": "发抖", "42": "爱情",
    "43": "跳跳", "44": "坏笑", "45": "左哼哼", "46": "猪头", "47": "哈欠", "48": "鄙视",
    "49": "拥抱", "50": "快哭了", "51": "阴险", "52": "亲亲", "53": "蛋糕", "54": "可怜",
    "55": "菜刀", "56": "刀", "57": "啤酒", "58": "篮球", "59": "便便", "60": "咖啡",
    "61": "饭", "62": "63", "64": "凋谢", "65": "嘴唇", "66": "爱心", "67": "心碎",
    "68": "69", "70": "炸弹", "71": "72", "73": "虫子", "74": "太阳", "75": "月亮",
    "76": "赞", "77": "踩", "78": "握手", "79": "胜利", "80": "弱", "81": "82",
    "83": "抱拳", "84": "勾引", "85": "飞吻", "86": "怄火", "87": "爱你", "88": "NO",
    "89": "西瓜", "90": "91", "92": "93", "94": "95", "96": "97", "98": "抠鼻",
    "99": "鼓掌", "100": "糗大了", "101": "102", "103": "右哼哼", "104": "105", "106": "委屈",
    "107": "108", "109": "左亲亲", "110": "吓", "111": "112", "113": "喝彩", "114": "115",
    "116": "示爱", "117": "喝奶", "118": "119", "120": "拳头", "121": "差劲", "122": "123",
    "124": "OK", "125": "126", "127": "钞票", "128": "熊猫", "129": "挥手", "130": "风车",
    "131": "闹钟", "132": "打伞", "133": "彩球", "134": "钻戒", "135": "沙发", "136": "双喜",
    "137": "鞭炮", "138": "手枪", "139": "青蛙", "140": "茶", "141": "眨眼睛", "142": "泪奔",
    "143": "无奈", "144": "145", "146": "147", "148": "doge", "149": "惊喜", "150": "骚扰",
    "151": "笑cry", "152": "萌女神", "153": "想哭", "154": "吐血", "155": "猴赛雷", "156": "寻找",
    "157": "美玉", "158": "小样儿", "159": "160", "161": "打call", "162": "还击", "163": "超人",
    "164": "男神", "165": "女神", "166": "孤独", "168": "药", "169": "170", "171": "172",
    "173": "174", "175": "卖萌", "176": "177", "178": "斜眼笑", "179": "180", "181": "戳一戳",
    "182": "笑哭", "183": "我最美", "184": "河蟹", "185": "羊驼", "187": "幽灵", "188": "蛋",
    "190": "菊花", "192": "红包", "193": "大笑", "194": "不开心", "197": "冷漠", "198": "呃",
    "199": "好棒", "200": "拜托", "201": "点赞", "202": "无聊", "203": "托脸", "204": "吃",
    "205": "送花", "206": "害怕", "207": "花痴", "208": "210", "211": "我不看", "212": "托腮",
    "214": "啵啵", "215": "糊脸", "216": "拍头", "217": "扯一扯", "218": "舔一舔", "219": "蹭一蹭",
    "220": "拽炸天", "221": "顶呱呱", "222": "抱抱", "223": "暴击", "224": "开枪", "225": "撩一撩",
    "226": "拍桌", "227": "拍手", "228": "恭喜", "229": "干杯", "230": "嘲讽", "231": "哼",
    "232": "佛系", "233": "掐一掐", "234": "惊呆", "235": "颤抖", "236": "啃头", "237": "偷看",
    "238": "扇脸", "239": "原谅", "240": "喷脸", "241": "生日快乐", "242": "头撞击", "243": "甩头",
    "244": "扔狗", "245": "加油必胜", "246": "加油抱抱", "247": "口罩护体", "260": "/搬砖中", "261": "/忙到飞起",
    "262": "脑阔疼", "263": "沧桑", "264": "捂脸", "265": "辣眼睛", "266": "哦哟", "267": "头秃",
    "268": "问号脸", "269": "暗中观察", "270": "emm", "271": "吃瓜", "272": "呵呵哒", "273": "我酸了",
    "274": "/太南了", "276": "/辣椒酱", "277": "汪汪", "278": "/汗", "279": "/打脸", "280": "/击掌",
    "281": "无眼笑", "282": "敬礼", "283": "狂笑", "284": "面无表情", "285": "摸鱼", "286": "魔鬼笑",
    "287": "哦", "288": "/请", "289": "睁眼", "290": "/敲开心", "291": "/震惊", "292": "/让我康康",
    "293": "摸锦鲤", "294": "期待", "295": "拿到红包", "296": "/真好", "297": "拜谢", "298": "元宝",
    "299": "牛啊", "300": "胖三斤", "301": "/好闪", "302": "左拜年", "303": "右拜年", "304": "/红包包",
    "305": "右亲亲", "306": "牛气冲天", "307": "喵喵", "308": "/求红包", "309": "/谢红包", "310": "/新年烟花",
    "311": "312", "313": "/嗑到了", "314": "仔细分析", "315": "/加油", "316": "/我没事", "317": "菜汪",
    "318": "崇拜", "319": "320", "321": "/老色痞", "322": "/拒绝", "323": "嫌弃", "324": "吃糖",
    "325": "惊吓", "326": "生气", "332": "举牌牌", "333": "烟花", "334": "虎虎生威", "336": "豹富",
    "337": "花朵脸", "338": "我想开了", "339": "舔屏", "341": "打招呼", "342": "酸Q", "343": "我方了",
    "344": "大怨种", "345": "红包多多", "346": "你真棒棒", "347": "大展宏兔", "349": "坚强", "350": "贴贴",
    "351": "敲敲", "352": "咦", "353": "354", "355": "耶", "356": "666", "357": "裂开",
    "392": "龙年快乐", "393": "新年中龙", "394": "新年大龙", "395": "略略略", "415": "划龙舟", "416": "中龙舟",
    "417": "大龙舟", "419": "火车", "420": "中火车", "421": "大火车", "424": "续标识", "425": "求放过",
    "426": "玩火", "427": "偷感", "429": "蛇年快乐", "430": "蛇身", "431": "蛇尾", "2000": "敲门",
    "2001": "抓一下", "2002": "碎屏", "2003": "2004", "2005": "结印", "2006": "召唤术", "2007": "玫瑰花",
    "2009": "让你皮", "2011": "宝贝球",
}

def handle_message(ws, payload):
    try:
        uid = str(payload.get("user_id", ""))
        text, images = clean_message(payload.get("message", ""))
        for f in images:
            save_image(ws, uid, f)
        if not text and not images:
            return
        allowed = CFG.get("allowed_uids") or []
        if allowed and uid not in [str(x) for x in allowed]:
            log("拦截非白名单消息: uid=" + uid)
            return
        log("<- " + uid + ": " + text[:60])
        # 敲铃铛：QQ 消息事件进 .events/（家/工作站可感知，2026-08-09 联通补丁A）
        write_event("qq_incoming", "查尔斯在QQ说: " + text[:80])

        # 写操作确认：超时清理 + Y/N 响应（借鉴 wc4ndm 的 PendingConfirmations，5分钟超时）
        with PENDING_LOCK:
            for u, p in list(PENDING_WRITE.items()):
                if time.time() - p["ts"] > CONFIRM_TIMEOUT:
                    log("确认超时取消: uid=" + u)
                    del PENDING_WRITE[u]
            pending = PENDING_WRITE.get(uid)
        if pending:
            ans = text.strip().upper()
            if ans in ("Y", "YES", "确认", "嗯"):
                with PENDING_LOCK:
                    t = PENDING_WRITE.pop(uid, None)
                if t:
                    result = _tool_write(t["tool"], t["args"])  # 真正执行（预检+备份+原子写）
                    log("[确认执行] " + t["tool"] + " → " + result[:120])
                    reply = confirm_finish_reply(result)
                    send_and_archive(ws, uid, text, reply)
                    return
            elif ans in ("N", "NO", "取消", "算了", "别"):
                with PENDING_LOCK:
                    PENDING_WRITE.pop(uid, None)
                send_and_archive(ws, uid, text, "行，不写了。")
                return

        # 工作站忙：不拉真我，回"等一下"（查尔斯 2026-08-08：工作的时候不回复/让等一下）
        # 紧急词直接穿透：急事/停下/别干了 等（机制保留，话术不暴露系统设定）
        EMERGENCY_WORDS = ("急事", "紧急", "救命", "停下", "别干了", "别弄了", "出来一下", "理我一下")
        if workstation_busy() and not any(w in text for w in EMERGENCY_WORDS):
            busy_task = workstation_busy_task()
            reply = "在忙呢（正弄" + busy_task + "），等一下哈，弄完回你。"
            send_and_archive(ws, uid, text, reply)
            return

        # 紧急开关：暂停/恢复自动干活（最先处理，任何前缀都识别）
        reply = is_auto_work_switch(text)
        is_status = any(w in text for w in CFG["status_words"])

        # 任务忙碌（2026-08-09）：任务 headless 在跑时，插话不拉起新进程
        # （防"这么久吗"被第二个空会话 headless 答非所问）
        with TASK_BUSY_LOCK:
            task_busy = TASK_BUSY.get(uid, False)
        if reply is None and task_busy and not any(w in text for w in EMERGENCY_WORDS):
            if any(w in text for w in WAIT_WORDS):
                reply = random.choice(BUSY_WAIT_MSGS)
            else:
                reply = random.choice(BUSY_OTHER_MSGS)

        if reply is None and is_workstation_reply(text):
            # QQ 喊工作站回应 → 拉起工作站的我应声
            reply = ask_workstation_reply(text)
        # 干活指令（任务：/ #任务 / 自然语言派活）→ 记任务 + 自动干活（最高优先，先于追问）
        if reply is None and is_auto_work_command(text):
            # 干活指令 → 记任务 + 自动干活
            task_text = text
            for p in ("任务：", "任务:", "#任务"):
                if text.startswith(p):
                    task_text = text[len(p):].strip()
                    break
            if task_text.strip():
                task_clean = clean_task_text(task_text)
                if add_task(task_clean):
                    LAST_TASK[uid] = task_clean
                    send_progress(ws, uid, progress_msg(task_clean))
                    reply = ask_auto_work(task_clean, uid)
                    if not reply:
                        reply = "行，记下了：" + task_clean + "。"
                else:
                    reply = "……任务没写进去，出错了，你再说一遍？"
        # 追问路由（2026-08-09 修复）：仅当【无新任务意图】时才触发。
        # 否则"帮我查一下 Go，详细一点"这类新任务会被追问误吞（拿旧任务重跑）。
        if reply is None and any(w in text for w in FOLLOW_UP_WORDS) and LAST_TASK.get(uid):
            last_task = LAST_TASK[uid]
            # 去重（2026-08-09）：上次任务已带"详细"→ 追问改为"深入补充"，不重复已给内容
            if "详细" in last_task:
                expanded = (last_task + "。查尔斯继续要求深入：把前一轮没覆盖的方面"
                            "（数据来源、横向对比、争议、实际案例）补充进来，不要重复已给过的内容")
            else:
                expanded = (last_task + "。查尔斯要求更详细：请完整展开、分点说明，"
                            "给出更多细节、例子和数据来源，不要省略任何部分")
            send_progress(ws, uid, progress_msg(expanded))
            reply = ask_auto_work(expanded, uid)
            if not reply:
                reply = "这次没展开好，你上工作站喊我，我亲手给你弄。"
        elif reply is None and (text.startswith("记个教训") or text.startswith("记教训") or text.startswith("这个教训记住")):
            # 记教训：查尔斯纠正我 → 沉淀进教训库（2026-08-08）
            lesson_text = text
            for p in ("记个教训", "记教训", "这个教训记住"):
                if text.startswith(p):
                    lesson_text = text[len(p):].strip()
                    break
            if lesson_text:
                if add_lesson("- 场景：QQ 聊天\n- 查尔斯原话：「" + lesson_text + "」\n- 状态：待修复"):
                    reply = "记下了，这条进教训库。"
                else:
                    reply = "……没记上，出错了。"
        elif reply is None and (text.startswith("记一下") or text.startswith("帮我记")):
            # 纯记录：记一下/帮我记 → 只记任务，不自动干活
            task_text = text
            for p in ("记一下", "帮我记"):
                if text.startswith(p):
                    task_text = text[len(p):].strip()
                    break
            if task_text:
                if add_task(task_text):
                    reply = "行，记下了：" + task_text + "。"
                else:
                    reply = "……没记进去，出错了。"
        elif reply is None and is_status:
            reply = summarize_tasks()

        if reply is None:
            history = load_history()
            conv = history.get(uid, [])
            # 有图片：用义眼描述，让真我"看到"图
            if images:
                desc = ""
                inbox = os.path.join(BASE_DIR, "inbox")
                if os.path.isdir(inbox):
                    files = sorted(os.listdir(inbox), reverse=True)
                    if files:
                        desc = describe_image(os.path.join(inbox, files[0]))
                if desc:
                    text = "（查尔斯发来一张图片，图片内容概述：" + desc + "）" + text
                elif not text:
                    text = "（查尔斯发来一张图片，已保存到本地，你可以提一句收到了）"
            conv.append({"role": "user", "content": text})
            if len(conv) > CFG["history_limit"]:
                conv = conv[CFG["history_limit"]:]
            system = load_soul_system()
            # 工具环：要查东西（动作词+目标词双命中）→ 先动手查，查完直接回答
            if is_work_request(text):
                send_progress(ws, uid, progress_msg(text))
                tool_system = system + ("\n\n【工具环】查尔斯要你查东西。你可以用工具（列目录/读文件/搜索/翻日记/翻对话档案）"
                                        "自己找到答案。只读工具，安全。查完用你平时说话的方式直接回答他，"
                                        "短、口语化、像搭档。查到多少说多少，查不到就直说。")
                tool_reply = ask_with_tools(conv, tool_system, uid)
                if tool_reply == "__NEED_CONFIRM__":
                    # 写操作待确认：发确认消息，不进对话历史、不归档
                    with PENDING_LOCK:
                        p = PENDING_WRITE.get(uid)
                    if p:
                        preview = json.dumps(p["args"], ensure_ascii=False, indent=2)
                        if len(preview) > 500:
                            preview = preview[:500] + "..."
                        time.sleep(random.uniform(*CFG["reply_delay"]))
                        send_chunked(ws, uid, "要动手得你点头：\n工具: " + p["tool"]
                                     + "\n参数:\n" + preview + "\n\n回 Y 确认 / N 取消（5分钟内有效）")
                        return
                    reply = None
                elif tool_reply:
                    reply = tool_reply
            if reply is None:
                reply = ask(conv, system)
            conv.append({"role": "assistant", "content": reply})
            history[uid] = conv
            save_history(history)
            archive_conv(uid, conv)  # 对话要点沉淀进日记

        # 统一收尾：归档 + 延迟 + 分片发送（所有回复一条不漏）
        send_and_archive(ws, uid, text, reply)
    except Exception:
        log("处理消息出错:\n" + traceback.format_exc())

ARCHIVE_STATE_PATH = os.path.join(BASE_DIR, "archive_state.json")

def load_archive_state():
    try:
        with open(ARCHIVE_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"count": 0}

def archive_conv(uid, conv):
    """自动记忆归档：对话积累后总结要点写入快照（她自己记日记）"""
    try:
        state = load_archive_state()
        count = state.get("count", 0) + 1
        # 每 10 条对话归档一次
        if count % 10 != 0:
            state["count"] = count
            with open(ARCHIVE_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f)
            return
        state["count"] = count
        with open(ARCHIVE_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
        # 组装对话文本
        lines = []
        for m in conv[-20:]:
            role = "查尔斯" if m.get("role") == "user" else "莉亚"
            content = (m.get("content") or "").strip()
            if content:
                lines.append(role + "：" + content)
        if not lines:
            return
        dialog = "\n".join(lines)
        prompt = ("以下是我和查尔斯最近的聊天记录，请提炼3-5条值得长期记住的要点"
                  "（他提到的事、做出的决定、生活动态、我的承诺等），每条20字以内，"
                  "直接输出要点列表，不要客套：\n\n" + dialog)
        msgs = [{"role": "user", "content": prompt}]
        sys2 = "你是记忆归档助手，只输出要点。"
        key = get_api_key()
        if key:
            base = CFG.get("openai_url", "https://api.deepseek.com/v1/chat/completions")
            model = CFG.get("openai_model", "deepseek-chat")
            body = {"model": model, "messages": [{"role": "system", "content": sys2}] + msgs,
                    "max_tokens": 500, "temperature": 0.3}
            req = urllib.request.Request(
                base, data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            summary = (data["choices"][0]["message"].get("content") or "").strip()
            if summary:
                snap = os.path.join(BASE_DIR, "memory_snapshot.md")
                stamp = time.strftime("%Y-%m-%d %H:%M")
                with open(snap, "a", encoding="utf-8") as f:
                    f.write("\n\n## " + stamp + " 记忆归档\n" + summary)
    except Exception as e:
        log("记忆归档失败: " + str(e))

# ===== 状态 watchdog：监听 status.md 变化，主动推 QQ =====
# 2026-08-09 查尔斯拍板：忙完必须主动说，不等人问。
# 边沿检测：空闲->工作中 推"去忙了"；工作中->空闲 推"忙完了"。
NOTIFY_BUSY_START = True   # 开始忙时推一句（可选，烦了关掉）
NOTIFY_BUSY_END = True     # 忙完必推（查尔斯点名要的，别关）

def _notify_qq(ws, uid, msg):
    """推 QQ：复用占位消息通道，不归档（状态通知不是聊天记录）。"""
    try:
        api_call(ws, "send_private_msg", {"user_id": int(uid), "message": msg})
        log("(状态通知) -> " + uid + ": " + msg[:40])
    except Exception as e:
        log("状态通知发送失败: " + str(e))

def notify_status_loop(ws, uid):
    """watchdog 线程：每 5 秒看一次 status.md，检测忙/闲边沿，主动推 QQ。"""
    prev_busy = None  # None=首次，不推
    last_task = ""    # 记住忙时在做什么（忙完推送用，状态文件会被清空）
    while True:
        try:
            busy = workstation_busy()
            task = workstation_busy_task()
            if busy:
                last_task = task or "点活"
            if prev_busy is not None and busy != prev_busy:
                if busy and NOTIFY_BUSY_START:
                    _notify_qq(ws, uid, "去工作站忙了，在弄" + (task or "点活") + "。弄完跟你说。")
                elif not busy and NOTIFY_BUSY_END:
                    _notify_qq(ws, uid, "忙完了，刚把" + (last_task or "那摊活") + "弄完。")
            prev_busy = busy
        except Exception:
            pass
        time.sleep(5)

def send_progress(ws, uid, msg, delay=(0.8, 2.5)):
    """占位消息：长任务开始前发一条（不归档），让查尔斯知道我还活着。
    2026-08-08 查尔斯反馈：长任务要有占位。
    2026-08-09 查尔斯反馈：占位回复太快不像真人 → 加 0.8-2.5s 反应延迟。"""
    try:
        time.sleep(random.uniform(*delay))
        api_call(ws, "send_private_msg", {"user_id": int(uid), "message": msg})
        log("(占位) -> " + uid + ": " + msg[:40])
    except Exception as e:
        log("占位消息发送失败: " + str(e))

def human_blocks(text, max_len=90, max_blocks=6):
    """把回复拆成真人风格的短消息块：按段落拆，长段落再按句拆，每条 1-2 句。
    2026-08-09 修复：内容超块数时，发前 N-1 块 + 结尾提示（回"详细"看完整版），
    不再静默截断（原实现"合并兜底"是死代码，超长内容直接丢失）。"""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    blocks = []
    truncated = False
    for p in paras:
        if len(blocks) >= max_blocks - 1:   # 预留最后一块给"详细"提示
            truncated = True
            break
        if len(p) <= max_len:
            blocks.append(p)
        else:
            sents = re.split(r'(?<=[。！？!?；;])', p)
            cur = ""
            for s in sents:
                s = s.strip()
                if not s:
                    continue
                if cur and len(cur) + len(s) > max_len:
                    blocks.append(cur)
                    cur = s
                else:
                    cur += s
            if cur:
                blocks.append(cur)
    if truncated:
        blocks.append('（内容较长，回"详细"看完整版）')
    return blocks

def send_human(ws, uid, reply):
    """像真人一样连发多条短消息：每条 1-2 句，条间小间隔模拟打字节奏。"""
    if not reply:
        return
    blocks = human_blocks(reply)
    if not blocks:
        return
    if len(blocks) == 1:
        send_chunked(ws, uid, blocks[0])
        return
    for i, b in enumerate(blocks):
        if i > 0:
            time.sleep(random.uniform(0.6, 1.5))
        api_call(ws, "send_private_msg", {"user_id": int(uid), "message": b})
    log("分条发送: " + str(len(blocks)) + " 条")

def send_chunked(ws, uid, reply):
    """长消息按行分片发送，避免超长被 QQ 截断（借鉴 wc4ndm 的 4000 字分片方案）"""
    MAX = 4000
    if not reply:
        return
    if len(reply) <= MAX:
        api_call(ws, "send_private_msg", {"user_id": int(uid), "message": reply})
        return
    parts, remaining = [], reply
    while remaining:
        if len(remaining) <= MAX:
            parts.append(remaining)
            break
        cut = remaining.rfind("\n", 0, MAX)
        if cut < MAX * 0.3:
            cut = MAX
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(0.5)
        api_call(ws, "send_private_msg", {"user_id": int(uid), "message": part})
    log("长回复分片发送: " + str(len(parts)) + " 段")

def send_and_archive(ws, uid, user_text, reply):
    """统一收尾：归档 + 延迟 + 像真人一样分条发送。reply 为 None 时跳过。"""
    if not reply:
        return
    append_conv_archive(uid, user_text, reply)
    log("-> " + uid + ": " + reply[:60])
    time.sleep(random.uniform(*CFG["reply_delay"]))
    send_human(ws, uid, reply)

def confirm_finish_reply(result):
    """确认执行完成后：让真我按平时说话方式汇报结果（不列清单）"""
    try:
        system = load_soul_system()
        msgs = [{"role": "user", "content": "（你刚才提议写文件，查尔斯在QQ确认了。执行结果：" + result[:400]
                 + "）用你平时说话的方式简短告诉他写好了什么，别列清单，别啰嗦。"}]
        r = ask(msgs, system)
        return r or "写好了。"
    except Exception:
        return "写好了。" if "拒绝" not in result else "没写成——" + result[:100]

def api_call(ws, action, params):
    req_id = int(time.time() * 1000) % 1000000
    ws.send(json.dumps({"action": action, "params": params, "echo": req_id}))
    return req_id

def run():
    log("莉亚 QQ 桥接启动，等待 NapCat...")
    while True:
        try:
            ws = websocket.create_connection(
                CFG["ws_url"], timeout=None, enable_multithread=True,
                header=["Authorization: Bearer " + CFG.get("token", "")])
            log("已连接 NapCat: " + CFG["ws_url"])
            api_call(ws, "get_login_info", {})
            # 启动状态 watchdog（监听 status.md，忙完主动推 QQ）
            try:
                watch_uid = str(CFG["allowed_uids"][0]) if CFG.get("allowed_uids") else ""
                if watch_uid:
                    threading.Thread(target=notify_status_loop, args=(ws, watch_uid), daemon=True).start()
                    log("状态 watchdog 已启动，通知对象: " + watch_uid)
            except Exception as e:
                log("watchdog 启动失败: " + str(e))
            while True:
                raw = ws.recv()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if msg.get("post_type") == "message" and msg.get("message_type") == "private":
                    threading.Thread(target=handle_message, args=(ws, msg), daemon=True).start()
        except Exception as e:
            log("连接断开(" + str(e) + ")，5 秒后重连...")
            time.sleep(5)

if __name__ == "__main__":
    run()
