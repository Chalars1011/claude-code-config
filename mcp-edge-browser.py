#!/usr/bin/env python
"""Simple browser MCP server using Edge CDP + Playwright"""
import json, sys, os, base64, io
from playwright.sync_api import sync_playwright

browser = None
page = None

def ensure_browser():
    global browser, page
    if browser is None:
        p = sync_playwright().start()
        browser = p.chromium.launch(
            channel="msedge",
            headless=True,
            args=['--no-sandbox', '--disable-gpu']
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})
    return page

def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")
    
    if method == "tools/list":
        return {
            "id": req_id,
            "result": {
                "tools": [
                    {"name": "browser_navigate", "description": "Navigate to URL", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
                    {"name": "browser_snapshot", "description": "Get page accessibility snapshot", "inputSchema": {"type": "object", "properties": {}}},
                    {"name": "browser_take_screenshot", "description": "Take page screenshot", "inputSchema": {"type": "object", "properties": {"filename": {"type": "string"}}}},
                    {"name": "browser_click", "description": "Click element", "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]}},
                    {"name": "browser_type", "description": "Type text", "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}, "text": {"type": "string"}}, "required": ["target", "text"]}},
                    {"name": "browser_evaluate", "description": "Run JS", "inputSchema": {"type": "object", "properties": {"function": {"type": "string"}}, "required": ["function"]}},
                    {"name": "browser_close", "description": "Close browser", "inputSchema": {"type": "object", "properties": {}}},
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        pg = ensure_browser()
        
        try:
            if tool_name == "browser_navigate":
                pg.goto(args["url"], timeout=15000)
                pg.wait_for_load_state("networkidle", timeout=10000)
                # Return snapshot
                snapshot = pg.accessibility.snapshot()
                text = json.dumps(snapshot, indent=2, ensure_ascii=False)[:4000]
                return {"id": req_id, "result": {"content": [{"type": "text", "text": f"Navigated to {args['url']}\nSnap:\n{text}"}]}}
            
            elif tool_name == "browser_snapshot":
                snapshot = pg.accessibility.snapshot()
                text = json.dumps(snapshot, indent=2, ensure_ascii=False)[:5000]
                return {"id": req_id, "result": {"content": [{"type": "text", "text": text}]}}
            
            elif tool_name == "browser_take_screenshot":
                fname = args.get("filename", "screenshot.png")
                ss = pg.screenshot(full_page=True)
                # Save to D:/泯灭之塔/黑化版贴图/
                path = f"D:/泯灭之塔/黑化版贴图/{fname}"
                with open(path, "wb") as f:
                    f.write(ss)
                return {"id": req_id, "result": {"content": [{"type": "text", "text": f"Screenshot saved: {path}"}]}}
            
            elif tool_name == "browser_click":
                target = args["target"]
                # Try to click by text or selector
                pg.locator(f"text={target}").first.click(timeout=5000)
                pg.wait_for_timeout(500)
                return {"id": req_id, "result": {"content": [{"type": "text", "text": f"Clicked: {target}"}]}}
            
            elif tool_name == "browser_type":
                target = args["target"]
                text = args["text"]
                pg.locator(f"input,textarea,{target}").first.fill(text, timeout=5000)
                return {"id": req_id, "result": {"content": [{"type": "text", "text": f"Typed '{text}'"}]}}
            
            elif tool_name == "browser_evaluate":
                result = pg.evaluate(args["function"])
                return {"id": req_id, "result": {"content": [{"type": "text", "text": str(result)}]}}
            
            elif tool_name == "browser_close":
                if browser:
                    browser.close()
                return {"id": req_id, "result": {"content": [{"type": "text", "text": "Closed"}]}}
            
            else:
                return {"id": req_id, "error": {"message": f"Unknown tool: {tool_name}"}}
        except Exception as e:
            return {"id": req_id, "error": {"message": str(e)}}
    
    elif method == "initialize":
        return {"id": req_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "edge-browser", "version": "1.0"}}}
    
    return {}

if __name__ == "__main__":
    # Read JSON-RPC from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            if resp:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err = {"id": 0, "error": {"message": str(e)}}
            sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            sys.stdout.flush()
