#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动发布模块 - 骨架 (Step1 预留，Step2 接 Playwright)

调用约定：
  python publisher.py --input data/temp/publish.json
  publish.json: { "title": "...", "content": "..." }

真实逻辑 (Step2):
  from playwright.sync_api import sync_playwright
  page.goto("https://mp.toutiao.com/profile_v4/graphic/publish")
  page.fill("[placeholder='请输入标题']", title)
  page.fill(".editor", content)
  page.click("text=发布")
"""

import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Publisher Mock - IwanMoney")
    parser.add_argument("--input", required=True, help="publish.json 路径")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不真实发布")
    args = parser.parse_args()

    p = Path(args.input)
    if not p.exists():
        print(f"[publisher] 输入不存在: {p}")
        return 1
    data = json.loads(p.read_text(encoding="utf-8"))
    print(f"[publisher] 准备发布 标题={data.get('title','')[:30]} 内容长度={len(data.get('content',''))}")
    if args.dry_run:
        print("[publisher] DRY-RUN 模拟发布成功 (未真实调用 Playwright)")
    else:
        print("[publisher] Step1 骨架：真实发布将在 Step2 接入 Playwright 后启用")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
