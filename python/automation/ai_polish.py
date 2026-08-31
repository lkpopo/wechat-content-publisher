#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI润色自动化模块 - Mock版 (Step1)

职责：
  1. 接收 C++ QProcess 传入的两个文件路径参数： temp_in.txt -> temp_out.txt
  2. 读取输入文件，在开头加上 "[已润色]" 标记并简单模拟润色效果
  3. 写出到输出文件

真实版 (Step2) 将在此基础上接入 Playwright：
  - 启动本地 Chrome (playwright.chromium.launch)
  - 自动访问 Grok (https://grok.com 或 https://x.com/i/grok)
  - 填入待润色文章，等待生成，抓取结果保存到 temp_out.txt

IPC约定（与 C++ 一致）：
  python ai_polish.py <input_path> <output_path>
  也可通过 stdin/stdout 交换长文本（备选）
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Windows 控制台 GBK 编码兼容：强制 stdout/stderr 为 utf-8 并忽略错误
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def safe_print(*args, **kwargs):
    """兼容 GBK 控制台的安全打印"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 回退：直接写 bytes
        text = " ".join(str(a) for a in args)
        try:
            sys.stdout.buffer.write((text + "\n").encode('utf-8', errors='replace'))
            sys.stdout.buffer.flush()
        except Exception:
            pass


def mock_polish(text: str) -> str:
    """
    Mock 润色逻辑：仅用于打通 C++ <-> Python 链路
    真实逻辑将替换为 Playwright 自动化 Grok
    """
    if not text.strip():
        return "[已润色] (空内容，无需润色)"

    # 简单模拟：加前缀、分段优化、加结语
    lines = text.strip().splitlines()
    polished_lines = []
    polished_lines.append("【AI润色版本 - Mock演示】")
    polished_lines.append("=" * 40)
    polished_lines.append("")
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            polished_lines.append("")
            continue
        # 模拟润色：简单改写
        polished_lines.append(f"[已润色] {line}")
        if i == 1:
            polished_lines.append("  -> (AI优化：首段已增强吸引力，补充背景说明)")
    polished_lines.append("")
    polished_lines.append("-" * 40)
    polished_lines.append("✨ 润色完成 | 模型: Mock-Grok-1.0 | 耗时: 0.5s (模拟)")
    polished_lines.append("提示：Step2 将接入真实 Grok/ChatGPT Playwright 自动化")
    return "\n".join(polished_lines)


def polish_with_playwright_stub(text: str) -> str:
    """
    预留：真实 Playwright 逻辑骨架（Step2 启用）
    ```python
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        page = browser.new_page()
        page.goto("https://grok.com/")
        page.fill("textarea", text)
        page.click("button[type=submit]")
        page.wait_for_selector(".response", timeout=60000)
        result = page.inner_text(".response")
        browser.close()
        return result
    ```
    """
    # 目前直接走 mock
    return mock_polish(text)


def main():
    parser = argparse.ArgumentParser(description="AI Polish Mock - IwanMoney")
    parser.add_argument("input", nargs="?", help="输入文件路径 (temp_in.txt)")
    parser.add_argument("output", nargs="?", help="输出文件路径 (temp_out.txt)")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取")
    parser.add_argument("--stdout", action="store_true", help="输出到 stdout 而非文件")
    args = parser.parse_args()

    # 1. 读取输入
    text = ""
    if args.stdin:
        try:
            # 兼容 Windows 控制台编码
            text = sys.stdin.read()
        except Exception:
            text = sys.stdin.buffer.read().decode('utf-8', errors='replace')
        print(f"[ai_polish] 从 stdin 读取 {len(text)} 字符", file=sys.stderr)
    elif args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[ai_polish] 错误: 输入文件不存在: {in_path}", file=sys.stderr)
            sys.exit(1)
        # 尝试 utf-8-sig 优先（兼容 C++ / .NET 写入的 BOM）
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                text = in_path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        print(f"[ai_polish] 已读取 {in_path} ({len(text)} 字符)", file=sys.stderr)
    else:
        # 无参数时，尝试默认临时路径（兼容 C++ 默认）
        default_in = Path(__file__).resolve().parents[2] / "data" / "temp" / "temp_in.txt"
        if default_in.exists():
            text = default_in.read_text(encoding="utf-8")
            print(f"[ai_polish] 使用默认输入: {default_in}", file=sys.stderr)
        else:
            parser.print_help()
            sys.exit(1)

    # 2. 模拟耗时（让 C++ 端能看到 progress）
    time.sleep(0.8)

    # 3. 执行润色
    polished = polish_with_playwright_stub(text)

    # 4. 写出结果
    if args.stdout:
        safe_print(polished)
    elif args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(polished, encoding="utf-8")
        print(f"[ai_polish] 已写入 {out_path} ({len(polished)} 字符)", file=sys.stderr)
        # 同时回显到 stdout 供 C++ 备用读取（安全打印）
        safe_print(polished)
    else:
        default_out = Path(__file__).resolve().parents[2] / "data" / "temp" / "temp_out.txt"
        default_out.parent.mkdir(parents=True, exist_ok=True)
        default_out.write_text(polished, encoding="utf-8")
        print(f"[ai_polish] 已写入默认输出: {default_out}", file=sys.stderr)
        safe_print(polished)

    sys.exit(0)


if __name__ == "__main__":
    main()
