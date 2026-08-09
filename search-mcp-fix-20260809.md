# search MCP 修复记录（2026-08-09）

## 背景
搜索能力增强（agent-search-mcp v3.1.2）后一直返回 0 条结果。本次定位并修复 5 个 bug，验证恢复为 17 条（Bing + DDG + Sogou 三引擎）。

## 修复的 5 个 bug
1. **Bing 解析器正则过时** — 新版页面 `<h2 class=""><a target="_blank" href=...>`，原正则要求 `<a href=` 直接相邻 → 0 匹配
   - 文件: dist/engines/bing.js → 正则放宽为 `<h2[^>]*>[\s\S]*?<a[^>]*href=`
2. **Sogou snippet 提取失效** — 页面改版，class 从 str_info 变为 `fz-mid space-txt base-ellipsis clamp2` → snippet 为空被质量过滤
   - 文件: dist/engines/sogou.js → 支持新 class + 通用 `<p>` fallback
3. **Sogou URL 被全灭** — 结果 URL 全是 `sogou.com/link?url=`（加密跳转令牌，本地无法解码），被 filterLowQuality 过滤
   - 文件: dist/aggregation/dedup.js → 放行 sogou 官方跳转（浏览器/Jina 可跟随），仅过滤其他搜索引擎内部链接
4. **DDG Python 脚本崩溃** — Windows GBK 控制台下 `print(json.dumps(..., ensure_ascii=False))` 遇 U+2011 等字符 UnicodeEncodeError
   - 文件: scripts/ddg-search.py → 开头强制 stdout/stderr reconfigure UTF-8
5. **Baidu 反爬无检测** — 返回"百度安全验证"页（~1.4KB）时静默返回 0
   - 文件: dist/engines/baidu.js → 增加反爬页检测与 console.warn

## 状态
- 备份: `~/.claude/backups/agent-search-mcp-20260809/`（bing.js / sogou.js / dedup.js / ddg-search.py）
- 包位置: `C:/Users/13040/AppData/Roaming/npm/node_modules/agent-search-mcp/`
- **search MCP 进程已 kill，需重开会话自动拉起**（配置在 ~/.claude.json projects 的 mcpServers.search，stdio）

## 已知限制（正常现象）
- Baidu 反爬严重（大概率一直空）
- Sogou 连续请求会触发验证码（间隔冷却可恢复）
- DDG 需网络可访问 duckduckgo
- rate_limits 显示 remaining=0/1 是免费无 key 模式的正常显示
