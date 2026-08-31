#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI润色自动化 - Step2 真实 Playwright + Mock 回退

IPC: python ai_polish.py <input> <output> [--provider grok|mock] [--headless] [--timeout 60]
- 默认 provider=grok，若未安装 playwright 或启动失败则自动回退到 mock
- 真实链路复用 Chrome 用户数据目录以保持 Grok 登录态
"""

import sys
import os
import argparse
import time
import json
import re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs, flush=True)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        try:
            sys.stdout.buffer.write((text + "\n").encode('utf-8', errors='replace'))
            sys.stdout.buffer.flush()
        except Exception:
            pass

# ---------------- Mock ----------------
def mock_polish(text: str) -> str:
    if not text.strip():
        return "[已润色] (空内容，无需润色)"
    lines = text.strip().splitlines()
    out = ["【AI润色版本 · Mock演示】", "="*42, ""]
    for i, line in enumerate(lines, 1):
        line=line.strip()
        if not line:
            out.append(""); continue
        out.append(f"【润色】{line}")
        if i==1:
            out.append("  ↳ AI优化：增强开头吸引力，补充背景与数据支撑")
    out += ["", "-"*42, "✦ 模型: Mock-Grok-1.0 · 耗时 0.6s (模拟)", "提示：安装 playwright 并登录 grok.com 后可启用真实自动化"]
    return "\n".join(out)

# ---------------- Playwright 真实 ----------------
def polish_via_playwright(text: str, headless: bool=False, timeout: int=60, provider: str="grok") -> str:
    """
    尝试用 Playwright 操作 Grok，失败则抛异常由上层回退到 mock
    支持 provider: grok / grok_x / chatgpt (预留)
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as e:
        raise RuntimeError(f"playwright 未安装: {e} | pip install playwright && playwright install chromium") from e

    # Grok 提示词模板 - 针对今日头条优化
    prompt = (
        "你是一名资深的今日头条内容编辑，请将以下文章润色重写，要求：\n"
        "1. 保持原意与事实不变\n"
        "2. 标题更具吸引力（可提供3个备选标题）\n"
        "3. 段落更清晰，口语化与专业性平衡，适合移动端阅读\n"
        "4. 结尾增加互动引导句\n"
        "5. 全文保持中文，直接输出润色后正文，不要额外解释\n\n"
        "原文如下：\n" + text
    )

    grok_urls = [
        "https://grok.com/",
        "https://x.com/i/grok",
    ]
    # 用户数据目录 - 复用登录态
    user_data_dir = os.environ.get("GROK_USER_DATA_DIR", str(Path.home() / ".iwanmoney" / "grok_profile"))
    os.makedirs(user_data_dir, exist_ok=True)

    with sync_playwright() as p:
        # 优先用持久化上下文以保留登录
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                channel="chrome" if not headless else None,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                viewport={"width": 1280, "height": 860},
                timeout=timeout*1000,
            )
        except Exception:
            # 回退：普通 launch (无持久化)
            browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width":1280,"height":860})

        # 超时控制
        context.set_default_timeout(timeout*1000)
        page = context.pages[0] if context.pages else context.new_page()

        # 打开 Grok
        last_err = None
        for url in grok_urls:
            try:
                safe_print(f"[ai_polish] 打开 {url} ...", file=sys.stderr)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                break
            except Exception as e:
                last_err = e
                safe_print(f"[ai_polish] 打开失败 {url}: {e}", file=sys.stderr)
        else:
            raise RuntimeError(f"无法打开 Grok: {last_err}")

        # 检查是否需要登录
        # 若出现登录按钮则提示
        try:
            login_hint = page.locator("text=Sign in, text=登录, button:has-text('Log in')").first
            if login_hint.is_visible(timeout=3000):
                safe_print("[ai_polish] 检测到未登录，请在打开的浏览器中手动登录 Grok 后重试（登录态会保存在 user_data_dir）", file=sys.stderr)
                # 给用户 30s 手动登录时间（非 headless 时）
                if not headless:
                    page.wait_for_timeout(15000)
        except Exception:
            pass

        # 定位输入框 - 兼容多版本 Grok
        input_selectors = [
            "textarea[placeholder*='Ask']",
            "textarea[placeholder*='Message']",
            "div[contenteditable='true']",
            "textarea",
            "[data-testid='grok-input']",
            "div[role='textbox']",
        ]
        input_locator = None
        for sel in input_selectors:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=5000)
                input_locator = loc
                safe_print(f"[ai_polish] 找到输入框: {sel}", file=sys.stderr)
                break
            except Exception:
                continue
        if not input_locator:
            # 调试：截图
            try:
                page.screenshot(path=str(Path(user_data_dir)/"grok_no_input.png"))
            except Exception:
                pass
            raise RuntimeError("未找到 Grok 输入框，页面结构可能已变更")

        # 输入提示词
        try:
            # 对于 contenteditable，需要 click + fill
            input_locator.click(timeout=5000)
            page.wait_for_timeout(500)
            # 清空
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            # 分块填入避免一次过长
            # Playwright fill 对 contenteditable 可能不稳定，改用 keyboard type
            if "contenteditable" in (input_locator.get_attribute("contenteditable") or "") or "textbox" in sel:
                page.keyboard.type(prompt, delay=2)
            else:
                input_locator.fill(prompt, timeout=10000)
        except Exception as e:
            raise RuntimeError(f"填入失败: {e}") from e

        # 发送
        send_selectors = [
            "button[type='submit']",
            "button[aria-label*='Send']",
            "button:has-text('Send')",
            "button:has-text('发送')",
            "[data-testid='send-button']",
        ]
        sent = False
        for sel in send_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000) and btn.is_enabled():
                    btn.click(timeout=3000)
                    sent = True
                    safe_print(f"[ai_polish] 已点击发送: {sel}", file=sys.stderr)
                    break
            except Exception:
                continue
        if not sent:
            # 回退：按 Enter
            page.keyboard.press("Enter")
            safe_print("[ai_polish] 未找到发送按钮，已按 Enter", file=sys.stderr)

        # 等待响应 - 监听网络或 DOM
        # Grok 响应通常为流式，需要轮询直到内容稳定
        response_selectors = [
            "[data-message-author-role='assistant']",
            ".assistant",
            "[class*='response']",
            "[class*='message']",
            "div.prose",
            "article",
        ]
        start = time.time()
        last_text = ""
        stable_count = 0
        result_text = ""
        safe_print("[ai_polish] 等待 AI 生成...", file=sys.stderr)
        while time.time() - start < timeout:
            page.wait_for_timeout(1500)
            # 尝试多种选择器抓取最新 assistant 消息
            for sel in response_selectors:
                try:
                    locs = page.locator(sel)
                    cnt = locs.count()
                    if cnt == 0:
                        continue
                    # 取最后一条
                    last = locs.nth(cnt-1)
                    txt = last.inner_text(timeout=2000).strip()
                    if txt and len(txt) > 20:
                        # 排除输入回显
                        if txt[:30] not in prompt[:30]:
                            result_text = txt
                            break
                except Exception:
                    continue
            if result_text:
                if result_text == last_text:
                    stable_count += 1
                else:
                    stable_count = 0
                    last_text = result_text
                # 连续 2 次稳定且长度足够则认为完成
                if stable_count >= 2 and len(result_text) > 50:
                    safe_print(f"[ai_polish] 检测到稳定输出 {len(result_text)} 字符", file=sys.stderr)
                    break
            # 同时检查是否还在生成（typing 指示器）
            try:
                typing = page.locator("text=Generating, text=Thinking, [class*='typing'], [class*='loading']").first
                if typing.is_visible(timeout=500):
                    stable_count = 0
            except Exception:
                pass

        if not result_text:
            # 调试截图
            try:
                page.screenshot(path=str(Path(user_data_dir)/"grok_no_response.png"))
                html_snip = page.content()[:2000]
                safe_print(f"[ai_polish] 调试 HTML 片段: {html_snip[:500]}", file=sys.stderr)
            except Exception:
                pass
            raise RuntimeError("未获取到 AI 响应，超时")

        # 清理：去除可能的前后空白与引用
        result_text = result_text.strip()
        # 若获取到的是包含多轮对话的容器，尝试只取最后一段最长的
        if len(result_text) > 10000:
            result_text = result_text[-10000:]

        try:
            context.close()
        except Exception:
            pass
        try:
            if 'browser' in locals():
                browser.close()
        except Exception:
            pass

        # 包装输出
        header = "【AI润色版本 · Grok 真实】\n" + "="*42 + "\n"
        footer = "\n" + "-"*42 + f"\n✦ 模型: Grok via Playwright · 耗时 {int(time.time()-start)}s\n"
        return header + result_text + footer


def main():
    parser = argparse.ArgumentParser(description="AI Polish - IwanMoney Step2")
    parser.add_argument("input", nargs="?", help="输入文件 temp_in.txt")
    parser.add_argument("output", nargs="?", help="输出文件 temp_out.txt")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取")
    parser.add_argument("--stdout", action="store_true", help="输出到 stdout")
    parser.add_argument("--provider", default="grok", choices=["grok","mock","auto"], help="润色提供者，auto=优先真实失败回退mock")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--timeout", type=int, default=90, help="真实模式超时秒数")
    parser.add_argument("--mock", action="store_true", help="强制 Mock (兼容旧版)")
    args = parser.parse_args()

    if args.mock:
        args.provider = "mock"

    # 1. 读取
    text = ""
    if args.stdin:
        try:
            text = sys.stdin.read()
        except Exception:
            text = sys.stdin.buffer.read().decode('utf-8', errors='replace')
        print(f"[ai_polish] 从 stdin 读取 {len(text)} 字符", file=sys.stderr)
    elif args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[ai_polish] 错误: 输入不存在 {in_path}", file=sys.stderr)
            sys.exit(1)
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                text = in_path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        print(f"[ai_polish] 已读取 {in_path} ({len(text)} 字符) provider={args.provider}", file=sys.stderr)
    else:
        default_in = Path(__file__).resolve().parents[2] / "data" / "temp" / "temp_in.txt"
        if default_in.exists():
            text = default_in.read_text(encoding="utf-8-sig")
        else:
            parser.print_help(); sys.exit(1)

    time.sleep(0.5)
    polished = ""
    use_real = args.provider in ("grok", "auto")
    if use_real and not args.mock:
        try:
            polished = polish_via_playwright(text, headless=args.headless, timeout=args.timeout, provider=args.provider)
            print(f"[ai_polish] 真实模式成功 {len(polished)} 字符", file=sys.stderr)
        except Exception as e:
            print(f"[ai_polish] 真实模式失败: {e} -> 回退 Mock", file=sys.stderr)
            if args.provider == "grok":
                # grok 强制模式也回退，保证链路不因未登录而中断
                polished = mock_polish(text) + f"\n\n[注: 真实 Grok 失败已回退Mock，原因: {e}]"
            else:
                polished = mock_polish(text)
    else:
        polished = mock_polish(text)

    # 4. 写出
    if args.stdout:
        safe_print(polished)
    elif args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(polished, encoding="utf-8")
        print(f"[ai_polish] 已写入 {out_path} ({len(polished)} 字符)", file=sys.stderr)
        safe_print(polished)
    else:
        default_out = Path(__file__).resolve().parents[2] / "data" / "temp" / "temp_out.txt"
        default_out.parent.mkdir(parents=True, exist_ok=True)
        default_out.write_text(polished, encoding="utf-8")
        safe_print(polished)

    sys.exit(0)

if __name__ == "__main__":
    main()
