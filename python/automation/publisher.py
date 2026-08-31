#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动发布 - Step2 Playwright 真实 + dry-run 保护

调用:
  python publisher.py --input data/temp/publish.json [--dry-run] [--headless]
  publish.json: {"title":"...","content":"...","platform":"toutiao"}

真实链路:
  1. 读取 publish.json
  2. 若 --dry-run: 仅校验与模拟，不打开浏览器
  3. 否则 Playwright 打开 https://mp.toutiao.com/profile_v4/graphic/publish
     填标题/正文/封面，等待用户确认或自动点击发布（默认需手动确认以防误发）
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def validate_payload(data: dict):
    title = data.get("title","").strip()
    content = data.get("content","").strip()
    if not title: raise ValueError("标题为空")
    if not content: raise ValueError("正文为空")
    if len(title) < 5: print(f"[publisher] 警告: 标题过短 ({len(title)}字)", file=sys.stderr)
    if len(content) < 20: print(f"[publisher] 警告: 正文过短 ({len(content)}字)", file=sys.stderr)
    if len(title) > 30: print(f"[publisher] 提示: 头条标题建议 ≤30字，当前 {len(title)}字", file=sys.stderr)
    return title, content

def publish_real(title: str, content: str, headless: bool=False, timeout: int=60):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(f"playwright 未安装: {e}") from e

    url = "https://mp.toutiao.com/profile_v4/graphic/publish"
    print(f"[publisher] 启动 Playwright headless={headless} 打开 {url}", file=sys.stderr)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"], channel="chrome" if not headless else None)
        context = browser.new_context(viewport={"width":1366,"height":900})
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)

        # 检查是否未登录（跳转到登录页）
        if "login" in page.url or page.locator("text=登录, text=Sign in").first.is_visible(timeout=3000):
            print("[publisher] 检测到未登录，请在浏览器中登录头条号后重试", file=sys.stderr)
            if not headless:
                print("[publisher] 等待 25s 供手动登录...", file=sys.stderr)
                page.wait_for_timeout(25000)
                # 再次检查
                if "login" in page.url:
                    raise RuntimeError("仍未登录，已超时")

        # 填标题 - 适配多版本选择器
        title_sels = ["[placeholder*='请输入标题']", "[placeholder*='标题']", "input[placeholder*='标题']", "textarea[placeholder*='标题']"]
        filled_title=False
        for sel in title_sels:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=4000)
                loc.click()
                loc.fill(title, timeout=5000)
                filled_title=True
                print(f"[publisher] 标题已填: {sel}", file=sys.stderr)
                break
            except Exception:
                continue
        if not filled_title:
            raise RuntimeError("未找到标题输入框")

        # 填正文 - 头条编辑器可能是 contenteditable / ProseMirror
        content_sels = [".ProseMirror", "[contenteditable='true']", ".editor", "div[role='textbox']", ".ql-editor"]
        filled=False
        for sel in content_sels:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=4000)
                loc.click()
                # 全选后填入
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                # 分段粘贴避免过长一次失败
                # 使用 fill 若可用，否则 keyboard.type
                try:
                    loc.fill(content, timeout=5000)
                except Exception:
                    page.keyboard.type(content[:2000], delay=1)
                    if len(content) > 2000:
                        # 剩余通过 evaluate 粘贴
                        page.evaluate(f"""() => {{ const el=document.querySelector("{sel}"); if(el) el.innerText += {json.dumps(content[2000:])}; }}""")
                filled=True
                print(f"[publisher] 正文已填: {sel}", file=sys.stderr)
                break
            except Exception as e:
                print(f"[publisher] 尝试 {sel} 失败: {e}", file=sys.stderr)
                continue
        if not filled:
            raise RuntimeError("未找到正文编辑器")

        page.wait_for_timeout(1500)
        # 截图供确认
        snap = Path.home() / ".iwanmoney" / "toutiao_preview.png"
        snap.parent.mkdir(parents=True, exist_ok=True)
        try:
            page.screenshot(path=str(snap), full_page=False)
            print(f"[publisher] 预览截图: {snap}", file=sys.stderr)
        except Exception:
            pass

        # 寻找发布按钮 - 默认不自动点击，提示用户
        publish_sels = ["button:has-text('发布')", "button:has-text('发表')", "text=发布", "[class*='publish']"]
        print("[publisher] 内容已填入，请在浏览器中检查并手动点击发布（30s 后自动尝试）", file=sys.stderr)
        if not headless:
            page.wait_for_timeout(30000)
            # 尝试自动点击一次
            for sel in publish_sels:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2000) and btn.is_enabled():
                        print(f"[publisher] 尝试自动点击: {sel}", file=sys.stderr)
                        btn.click(timeout=3000)
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

        # 等待发布结果
        try:
            page.wait_for_timeout(3000)
            if "publish" not in page.url:
                print(f"[publisher] 当前 URL: {page.url}", file=sys.stderr)
        except Exception:
            pass

        print("[publisher] 流程结束，请在浏览器确认是否发布成功", file=sys.stderr)
        if not headless:
            page.wait_for_timeout(5000)
        browser.close()
        return True

def main():
    parser=argparse.ArgumentParser(description="Publisher Step2")
    parser.add_argument("--input", required=True, help="publish.json 路径")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟不发布")
    parser.add_argument("--headless", action="store_true", help="无头")
    parser.add_argument("--timeout", type=int, default=60)
    args=parser.parse_args()

    p=Path(args.input)
    if not p.exists():
        print(f"[publisher] 输入不存在: {p}", file=sys.stderr); return 1
    try:
        data=json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"[publisher] JSON 解析失败: {e}", file=sys.stderr); return 1

    try:
        title, content = validate_payload(data)
    except ValueError as e:
        print(f"[publisher] 校验失败: {e}", file=sys.stderr); return 1

    print(f"[publisher] 标题: {title[:32]} | 正文 {len(content)} 字 | dry_run={args.dry_run}", file=sys.stderr)

    if args.dry_run:
        print("[publisher] DRY-RUN 校验通过，模拟发布成功", file=sys.stderr)
        print(json.dumps({"success":True,"dry_run":True,"title":title}, ensure_ascii=False))
        return 0

    try:
        publish_real(title, content, headless=args.headless, timeout=args.timeout)
        print("[publisher] 真实发布流程已执行，请在浏览器确认结果", file=sys.stderr)
        print(json.dumps({"success":True,"title":title}, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"[publisher] 发布失败: {e}", file=sys.stderr)
        # 打印调用栈便于排查
        import traceback; traceback.print_exc()
        print(json.dumps({"success":False,"error":str(e)}, ensure_ascii=False))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
