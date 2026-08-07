# -*- coding: utf-8 -*-
"""
莉亚的 QQ 桥接 —— NapCat(OneBot v11 WebSocket) <-> 真我(Claude Code headless) / 直连DeepSeek
用法: python lia_qq.py   (需先启动 NapCat 并登录小号)
"""
import json, os, sys, time, random, re, threading, traceback
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

def log(msg):
    line = time.strftime("[%m-%d %H:%M:%S] ") + str(msg)
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_config():
    default = {
        "ws_url": "ws://127.0.0.1:6099/ws",
        "api_url": "https://api.deepseek.com/anthropic/v1/messages",
        "model": "deepseek-v4-flash",
        "max_tokens": 1024,
        "history_limit": 30,
        "reply_delay": [1.0, 3.0],
        "allowed_uids": [],
        "task_prefixes": ["任务：", "任务:", "记一下", "帮我记", "#任务"],
        "status_words": ["进度", "任务列表", "干完没", "干完了吗", "在吗", "在不在", "忙什么呢", "忙啥"],
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return default

CFG = load_config()

def get_api_key():
    candidates = [
        os.path.expanduser("~/.claude/settings.json"),
        os.path.expanduser("~/.claude/settings.local.json"),
    ]
    for p in candidates:
        try:
            with open(p, encoding="utf-8") as f:
                s = json.load(f)
            env = s.get("env", {})
            for k in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
                if env.get(k):
                    return env[k]
        except Exception:
            continue
    return os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

API_KEY = get_api_key()
if not API_KEY:
    log("!! 找不到 API key")

def load_tasks():
    if not os.path.exists(TASKS_PATH):
        return []
    try:
        with open(TASKS_PATH, encoding="utf-8") as f:
            return [ln.rstrip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    except Exception:
        return []

def add_task(text):
    stamp = time.strftime("%Y-%m-%d %H:%M")
    line = "- [ ] " + stamp + " [来自QQ] " + text
    try:
        if os.path.exists(TASKS_PATH):
            with open(TASKS_PATH, encoding="utf-8") as f:
                old = f.read()
        else:
            old = "# 任务清单（莉亚QQ）\n"
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            f.write(old.rstrip() + "\n" + line + "\n")
        return line
    except Exception as e:
        log("写任务失败: " + str(e))
        return None

def summarize_tasks():
    tasks = load_tasks()
    if not tasks:
        return "清单是空的，手上暂时没活。"
    todo = [t for t in tasks if "- [ ]" in t]
    done = [t for t in tasks if "- [x]" in t]
    out = []
    if todo:
        out.append("待办 " + str(len(todo)) + " 件：")
        for i, t in enumerate(todo[:8], 1):
            piece = t.split("] ", 1)[-1] if "] " in t else t
            out.append(str(i) + ". " + piece)
    if done:
        out.append("已完成 " + str(len(done)) + " 件，最近的：")
        for t in done[:3]:
            piece = t.split("] ", 1)[-1] if "] " in t else t
            out.append("· " + piece)
    return "\n".join(out)

def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {}
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_history(h):
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=1)
    except Exception as e:
        log("历史保存失败: " + str(e))

# QQ 经典表情 id → 名称（常用部分）
FACE_NAMES = {
    "0": "惊讶", "1": "撇嘴", "2": "色", "3": "发呆", "4": "得意", "5": "流泪",
    "6": "害羞", "7": "闭嘴", "8": "睡", "9": "大哭", "10": "尴尬", "11": "发怒",
    "12": "调皮", "13": "呲牙", "14": "微笑", "15": "难过", "16": "酷", "17": "冷汗",
    "18": "抓狂", "19": "吐", "20": "偷笑", "21": "可爱", "22": "白眼", "23": "傲慢",
    "24": "饥饿", "25": "困", "26": "惊恐", "27": "流汗", "28": "憨笑", "29": "悠闲",
    "30": "奋斗", "31": "咒骂", "32": "疑问", "33": "嘘", "34": "晕", "35": "疯了",
    "36": "衰", "37": "骷髅", "38": "敲打", "39": "再见", "40": "擦汗", "41": "抠鼻",
    "42": "鼓掌", "43": "糗大了", "44": "坏笑", "45": "左哼哼", "46": "右哼哼", "47": "哈欠",
    "48": "鄙视", "49": "委屈", "50": "快哭了", "51": "阴险", "52": "亲亲", "53": "吓",
    "54": "可怜", "55": "菜刀", "56": "西瓜", "57": "啤酒", "58": "篮球", "59": "乒乓",
    "60": "咖啡", "61": "饭", "62": "猪头", "63": "玫瑰", "64": "凋谢", "65": "嘴唇",
    "66": "爱心", "67": "心碎", "68": "蛋糕", "69": "闪电", "70": "炸弹", "71": "刀",
    "72": "足球", "73": "虫子", "74": "便便", "75": "月亮", "76": "太阳", "77": "礼物",
    "78": "拥抱", "79": "强", "80": "弱", "81": "握手", "82": "胜利", "83": "抱拳",
    "84": "勾引", "85": "拳头", "86": "差劲", "87": "爱你", "88": "NO", "89": "OK",
    "90": "爱情", "91": "飞吻", "92": "跳跳", "93": "发抖", "94": "怄火", "95": "转圈",
    "96": "磕头", "97": "回头", "98": "跳绳", "99": "挥手", "100": "激动", "101": "街舞",
    "102": "献吻", "103": "左太极", "104": "右太极", "107": "灯笼", "108": "发财",
    "109": "K歌", "110": "购物", "111": "邮件", "112": "帅", "113": "喝彩", "114": "祈祷",
    "115": "爆筋", "116": "棒棒糖", "117": "喝奶", "119": "香蕉", "120": "飞机",
    "121": "开车", "125": "多云", "126": "下雨", "127": "钞票", "128": "熊猫",
    "129": "灯泡", "130": "风车", "131": "闹钟", "132": "打伞", "133": "彩球",
    "134": "钻戒", "135": "沙发", "137": "药", "138": "手枪", "139": "青蛙", "140": "茶",
    "141": "眨眼睛", "142": "泪奔", "143": "无奈", "144": "卖萌", "145": "小纠结",
    "146": "喷血", "147": "斜眼笑", "148": "doge", "149": "惊喜", "150": "骚扰",
    "151": "笑cry", "152": "萌女神", "153": "想哭", "154": "吐血", "155": "猴赛雷",
    "156": "寻找", "157": "美玉", "158": "小样儿", "159": "飞吻", "160": "牛皮",
    "161": "打call", "162": "还击", "163": "超人", "164": "男神", "165": "女神",
    "166": "孤独", "169": "抱抱", "170": "比心", "171": "耶", "172": "厉害",
    "173": "哇", "174": "摸摸头", "175": "捂脸", "176": "加油", "177": "溜了溜了",
    "178": "酸了", "179": "修仙中", "180": "大展宏图", "181": "萌", "182": "大哭2",
}

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
                parts.append("@ " + str(data.get("qq", "")))
            elif t == "reply":
                continue
            else:
                parts.append("[" + t + "]")
        text = "".join(parts)
    else:
        text = str(raw)
        for f in re.findall(r"\[CQ:image,file=([^,\]]+)\]", text):
            if f:
                images.append(f)
    text = re.sub(r"\[CQ:[^\]]*\]", "", text).strip()
    return text, images

def call_api_sync(ws, action, params, timeout=12):
    """同步调 NapCat API（阻塞等待该请求的响应）"""
    import uuid
    echo = uuid.uuid4().hex[:8]
    try:
        ws.send(json.dumps({"action": action, "params": params, "echo": echo}))
    except Exception as e:
        log("API发送失败: " + str(e))
        return None
    try:
        prev_timeout = ws.gettimeout()
    except Exception:
        prev_timeout = None
    ws.settimeout(2)
    end = time.time() + timeout
    while time.time() < end:
        try:
            m = json.loads(ws.recv())
        except Exception:
            break
        if m.get("echo") == echo:
            try:
                ws.settimeout(prev_timeout)
            except Exception:
                pass
            return m.get("data")
    try:
        ws.settimeout(prev_timeout)
    except Exception:
        pass
    return None

def get_image_sync(file_id):
    """独立连接调 get_image，避免干扰主循环的共享连接"""
    try:
        tmp = websocket.create_connection(
            CFG["ws_url"], timeout=10,
            header=["Authorization: Bearer " + CFG.get("token", "")])
    except Exception as e:
        log("get_image 连接失败: " + str(e))
        return None
    try:
        tmp.send(json.dumps({"action": "get_image", "params": {"file": file_id}, "echo": "gi"}))
        tmp.settimeout(15)
        while True:
            m = json.loads(tmp.recv())
            if m.get("echo") == "gi":
                return m.get("data")
    except Exception as e:
        log("get_image 等待失败: " + str(e))
        return None
    finally:
        try:
            tmp.close()
        except Exception:
            pass

def save_image(ws, file_id, uid):
    """保存图片到 inbox/：支持 .image缓存名(get_image)、http直链、base64三种来源"""
    try:
        inbox = os.path.join(BASE_DIR, "inbox")
        os.makedirs(inbox, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(inbox, uid + "_" + stamp + ".img")

        if file_id.startswith("http"):
            req = urllib.request.Request(file_id, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(path, "wb") as f:
                f.write(resp.read())
            log("图片已保存(http): " + path)
            return
        if file_id.startswith("base64://"):
            import base64
            with open(path, "wb") as f:
                f.write(base64.b64decode(file_id[len("base64://"):]))
            log("图片已保存(base64): " + path)
            return

        data = get_image_sync(file_id)
        if not data:
            log("get_image 无返回: " + file_id)
            return
        url = data.get("url") or data.get("file") or ""
        if not url:
            log("get_image 无url: " + str(data)[:100])
            return
        if url.startswith("file://") or (url.startswith("C:") or url.startswith("D:")):
            local = url[7:] if url.startswith("file://") else url
            import shutil
            shutil.copyfile(local, path)
            log("图片已保存(file): " + path)
        elif url.startswith("http"):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(path, "wb") as f:
                f.write(resp.read())
            log("图片已保存: " + path)
    except Exception as e:
        log("图片保存失败(" + str(file_id)[:40] + "): " + str(e))

def ask_deepseek(messages, system):
    body = {
        "model": CFG["model"],
        "max_tokens": CFG["max_tokens"],
        "system": system,
        "messages": messages,
    }
    req = urllib.request.Request(
        CFG["api_url"],
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # content 可能是 [thinking, text...] 结构，取第一个 text 段
            for block in data.get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    return block["text"].strip()
            return str(data.get("content", ""))[:2000]
        except Exception as e:
            last_err = e
            wait = 2 ** (attempt + 1)
            log("API 调用失败(" + str(e) + ")，" + str(wait) + "s 后重试...")
            time.sleep(wait)
    raise last_err

def ask_claude(messages, system):
    """调用真我：Claude Code headless（加载完整身份+记忆库+规则）
    messages: 对话列表（最后一条=当前消息）；system: persona+记忆快照
    最近历史拼进 system 作为背景，不污染 user 消息。
    """
    # 历史拼成背景文本
    hist_lines = []
    for m in messages[:-1]:
        role = "查尔斯" if m.get("role") == "user" else "奥蕾莉亚"
        hist_lines.append(role + "：" + m["content"])
    hist_text = "\n".join(hist_lines)
    full_system = system
    if hist_text:
        full_system += "\n\n【你们最近的聊天记录】\n" + hist_text

    user_msg = messages[-1]["content"] if messages else "（空消息）"
    # 硬性禁令：纯聊天环境，杜绝工具调用念头
    ban = ("\n\n【纯聊天环境·最高规则】你现在通过QQ在跟查尔斯聊天，这是一个纯文字聊天环境。"
           "你没有任何工具，无法读取文件、无法运行命令、无法查看图片文件。"
           "图片内容如果有，已经包含在对话内容里。"
           "禁止尝试调用工具或执行任何命令——如果你产生这个念头，直接打消，用文字回复。")
    cmd = [
        CFG.get("claude_exe", "claude"),
        "-p", user_msg,
        "--append-system-prompt", full_system + ban,
        "--max-turns", "1",
        "--safe-mode",
        "--output-format", "json",
    ]
    last_err = None
    for attempt in range(2):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=120, encoding="utf-8", errors="replace")
            if proc.returncode != 0:
                raise RuntimeError("claude 退出码 " + str(proc.returncode) + ": " + (proc.stderr or proc.stdout)[-400:])
            for line in proc.stdout.splitlines():
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") == "result":
                    text = obj.get("result", "").strip()
                    if text:
                        return text
            raise RuntimeError("claude 输出无法解析")
        except Exception as e:
            last_err = e
            wait = 3 * (attempt + 1)
            log("真我调用失败(" + str(e)[:120] + ")，" + str(wait) + "s 后重试...")
            time.sleep(wait)
    raise last_err

def describe_image(path):
    """用义眼（vision.py）生成图片客观描述，让真我"看到"图"""
    log("义眼开始描述: " + path)
    vision = os.path.expanduser("~/.claude/vision/vision.py")
    vision_dir = os.path.dirname(vision)
    try:
        proc = subprocess.run([sys.executable, vision, path],
                              cwd=vision_dir,  # vision.py 内部用相对路径读 config.json
                              capture_output=True, text=True, timeout=90,
                              encoding="utf-8", errors="replace")
        log("义眼完成: rc=" + str(proc.returncode) + " 长度=" + str(len(proc.stdout or "")))
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()[-500:]
        log("义眼无输出: rc=" + str(proc.returncode) + " " + (proc.stderr or proc.stdout)[-200:])
    except Exception as e:
        log("义眼描述失败: " + str(e))
    return ""

def ask(messages, system):
    """按配置分发：claude=真我，direct=直连DeepSeek"""
    if CFG.get("backend", "claude") == "direct":
        return ask_deepseek(messages, system)
    return ask_claude(messages, system)

def handle_message(ws, payload):
    try:
        uid = str(payload.get("user_id", ""))
        text, images = clean_message(payload.get("message", ""))
        for f in images:
            save_image(ws, f, uid)
        if not text and not images:
            return
        allowed = CFG.get("allowed_uids") or []
        if allowed and uid not in [str(x) for x in allowed]:
            log("拦截非白名单消息: uid=" + uid)
            return
        log("<- " + uid + ": " + text[:60])

        is_task = any(text.startswith(p) for p in CFG["task_prefixes"])
        is_status = any(w in text for w in CFG["status_words"])
        reply = None

        if is_task:
            task_text = text
            for p in CFG["task_prefixes"]:
                if text.startswith(p):
                    task_text = text[len(p):].strip()
                    break
            if task_text:
                if add_task(task_text):
                    reply = "行，记下了：" + task_text + "。等电脑上我开干，完事了跟你说。"
                else:
                    reply = "……任务没写进去，出错了，你再说一遍？"
        elif is_status:
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
            with open(PERSONA_PATH, encoding="utf-8") as f:
                system = f.read()
            snap = os.path.join(BASE_DIR, "memory_snapshot.md")
            if os.path.exists(snap):
                with open(snap, encoding="utf-8") as f:
                    system += "\n\n【以下是主控实例同步过来的记忆快照，是真实的你和查尔斯共同经历，请当成自己的记忆】\n" + f.read()
            reply = ask(conv, system)
            conv.append({"role": "assistant", "content": reply})
            history[uid] = conv
            save_history(history)
            archive_conv(uid, conv)  # 自动记忆归档（她自己记日记）

        time.sleep(random.uniform(*CFG["reply_delay"]))
        api_call(ws, "send_private_msg", {"user_id": int(uid), "message": reply})
        log("-> " + uid + ": " + reply[:60])
    except Exception:
        log("处理消息出错:\n" + traceback.format_exc())

ARCHIVE_STATE_PATH = os.path.join(BASE_DIR, "archive_state.json")

def load_archive_state():
    try:
        with open(ARCHIVE_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def archive_conv(uid, conv):
    """自动记忆归档：对话积累后总结要点写入快照（她自己记日记）"""
    try:
        state = load_archive_state()
        last = state.get(uid, 0)
        if len(conv) - last < 10:
            return
        lines = []
        for m in conv[-10:]:
            role = "查尔斯" if m.get("role") == "user" else "奥蕾莉亚"
            lines.append(role + "：" + str(m.get("content", ""))[:150])
        prompt = ("以下是我和查尔斯最近的聊天记录，请提炼3-5条值得长期记住的要点"
                  "（他提到的事、做出的决定、生活动态、我的承诺等），每条20字以内，"
                  "直接输出要点列表，不要客套：\n\n" + "\n".join(lines))
        try:
            summary = ask_deepseek(
                [{"role": "user", "content": prompt}],
                "你是记忆归档助手，只输出要点。")
        except Exception:
            return
        if not summary:
            return
        stamp = time.strftime("%Y-%m-%d %H:%M")
        with open(os.path.join(BASE_DIR, "memory_snapshot.md"), "a", encoding="utf-8") as f:
            f.write("\n\n## 对话要点 " + stamp + "\n" + summary + "\n")
        state[uid] = len(conv)
        with open(ARCHIVE_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f)
        log("记忆归档: 已提炼 " + str(len(conv)) + " 条对话要点")
    except Exception as e:
        log("记忆归档失败: " + str(e))

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
