#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫抓取 - Step2 加强版
- 默认 Mock（稳定），可通过 --real 尝试真实 Playwright 抓取搜狗微信 / 微博移动端
- 接口预留 wechat/weibo/xiaohongshu，与 C++ QProcess 对接
- 输出 JSON 供 C++ 入库 + 列表展示
"""

import argparse
import json
import random
import time
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

class BaseCrawler:
    platform: str = "base"
    def crawl(self, blogger_id: str, start: str, end: str, real: bool=False):
        raise NotImplementedError

def mock_articles(blogger_id: str, platform: str, start: str, end: str):
    base_titles = {
        "wechat": ["AI 颠覆内容创作的 5 个真相","为什么你的公众号阅读量上不去？","深度：自媒体搬运的合规边界"],
        "weibo": ["今日热搜背后的流量密码","微博运营：从 0 到百万粉","雷军的创业思考"],
        "xiaohongshu": ["小红书爆款笔记拆解","探店视频如何剪出高级感","美食账号涨粉秘籍"],
    }
    pool = base_titles.get(platform, base_titles["wechat"]) + ["实测：用 Grok 润色效率提升 300%","今日头条推荐算法全解析","从 0 到 10w 粉的运营手记"]
    articles=[]
    cnt = random.randint(4,7)
    for i in range(cnt):
        title = random.choice(pool) + f" · {blogger_id.split('_')[-1]}#{i+1}"
        pub = (datetime.now() - timedelta(days=i, hours=random.randint(0,12))).isoformat()
        # 更丰富的 Mock 正文，模拟真实公众号结构
        content = (
            f"【标题】{title}\n\n"
            f"【博主】{blogger_id} @ {platform}\n"
            f"【时间】{pub[:10]}  区间 {start}~{end}\n"
            f"【链接】https://mock.{platform}.com/{blogger_id}/{i+1}\n\n"
            f"—— 正文 ——\n"
            f"第一段 · 痛点引入：许多创作者在 {platform} 上遇到内容同质化、阅读量下滑的问题，本文以 {blogger_id} 的实践为例展开。\n\n"
            f"第二段 · 方法论：通过选题-素材-结构-标题四步法，结合 AI 工具提效，实测单篇产出时间从 3h 缩短至 40min。\n\n"
            f"第三段 · 案例：某篇关于“AI 写作”的文章，润色后点击率提升 62%，评论区互动翻倍。\n\n"
            f"第四段 · 合规提醒：搬运需注明来源、避免洗稿，结合原创观点方能长效。\n\n"
            f"结尾 · 互动：你在 {platform} 运营中最大的困惑是什么？评论区聊聊，点赞过 100 下期拆解。\n"
        )
        articles.append({
            "id": f"{blogger_id}_{pub[:10]}_{i+1}",
            "title": title,
            "platform": platform,
            "blogger_id": blogger_id,
            "publish_time": pub,
            "content": content,
            "url": f"https://mock.{platform}.com/{blogger_id}/{i+1}",
            "cover": "",
        })
    return articles

# ---- 各平台 ----

class WechatCrawler(BaseCrawler):
    platform="wechat"
    def crawl(self, blogger_id, start, end, real=False):
        if real:
            try:
                return self.crawl_real(blogger_id, start, end)
            except Exception as e:
                print(f"[crawler][wechat] 真实抓取失败回退 Mock: {e}", file=sys.stderr)
        return mock_articles(blogger_id, self.platform, start, end)

    def crawl_real(self, blogger_id, start, end):
        """尝试搜狗微信搜索 - 需 playwright，且搜狗有反爬，可能仅作演示"""
        from playwright.sync_api import sync_playwright
        keyword = blogger_id.replace("wechat_","").replace("_"," ")
        print(f"[crawler][wechat] 真实模式 关键词={keyword}", file=sys.stderr)
        articles=[]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            # 搜狗微信
            page.goto(f"https://weixin.sogou.com/weixin?type=2&query={keyword}", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
            # 抓取前 5 条
            items = page.locator("ul.news-list li").all()[:5]
            for idx, it in enumerate(items):
                try:
                    title = it.locator("h3 a").first.inner_text(timeout=2000).strip()
                    url = it.locator("h3 a").first.get_attribute("href") or ""
                    snippet = it.locator("p.txt-info").first.inner_text(timeout=2000) if it.locator("p.txt-info").count() else ""
                    articles.append({
                        "id": f"{blogger_id}_real_{idx}",
                        "title": title or f"微信文章 {idx}",
                        "platform": "wechat",
                        "blogger_id": blogger_id,
                        "publish_time": (datetime.now()-timedelta(days=idx)).isoformat(),
                        "content": f"{title}\n\n{snippet}\n\n[真实抓取 via 搜狗微信] {url}",
                        "url": url,
                        "cover": "",
                    })
                except Exception:
                    continue
            browser.close()
        if not articles:
            raise RuntimeError("搜狗未抓到数据")
        return articles

class WeiboCrawler(BaseCrawler):
    platform="weibo"
    def crawl(self, blogger_id, start, end, real=False):
        if real:
            try:
                return self.crawl_real(blogger_id, start, end)
            except Exception as e:
                print(f"[crawler][weibo] 真实失败回退 Mock: {e}", file=sys.stderr)
        return mock_articles(blogger_id, self.platform, start, end)
    def crawl_real(self, blogger_id, start, end):
        import requests
        # 尝试微博移动端 API (无需登录的公开信息，uid 需映射)
        # 这里仅演示请求结构，实际 uid 需配置
        raise RuntimeError("weibo 真实抓取需配置 uid 与 cookie，暂回退 Mock")

class XiaohongshuCrawler(BaseCrawler):
    platform="xiaohongshu"
    def crawl(self, blogger_id, start, end, real=False):
        if real:
            print("[crawler][xhs] 真实抓取需登录态，暂回退 Mock", file=sys.stderr)
        return mock_articles(blogger_id, self.platform, start, end)

CRAWLER_MAP={"wechat":WechatCrawler,"weibo":WeiboCrawler,"xiaohongshu":XiaohongshuCrawler}

def main():
    parser=argparse.ArgumentParser(description="Crawler Step2")
    parser.add_argument("--blogger", required=True)
    parser.add_argument("--platform", default="wechat", choices=["wechat","weibo","xiaohongshu","all"])
    parser.add_argument("--start", default=(datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"))
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default="data/temp/crawl_result.json")
    parser.add_argument("--real", action="store_true", help="尝试真实抓取，否则 Mock")
    parser.add_argument("--limit", type=int, default=10, help="最大篇数")
    args=parser.parse_args()

    # 校验日期
    try:
        s=datetime.strptime(args.start, "%Y-%m-%d")
        e=datetime.strptime(args.end, "%Y-%m-%d")
        if s>e: raise ValueError("start > end")
    except Exception as ex:
        print(f"[crawler] 日期错误: {ex}", file=sys.stderr); sys.exit(1)

    platform=args.platform if args.platform!="all" else "wechat"
    cls=CRAWLER_MAP.get(platform, WechatCrawler)
    crawler=cls()
    print(f"[crawler] 平台={platform} 博主={args.blogger} 时间={args.start}~{args.end} real={args.real}", file=sys.stderr)

    # 模拟网络延迟
    time.sleep(0.6)

    for attempt in range(2):
        try:
            articles=crawler.crawl(args.blogger, args.start, args.end, real=args.real)
            break
        except Exception as ex:
            if attempt==0:
                print(f"[crawler] 第1次失败重试: {ex}", file=sys.stderr)
                time.sleep(1)
                continue
            print(f"[crawler] 抓取异常: {ex}", file=sys.stderr)
            articles=mock_articles(args.blogger, platform, args.start, args.end)

    articles=articles[:args.limit]
    out=Path(args.output)
    if not out.is_absolute():
        out=Path(__file__).resolve().parents[2]/out
    out.parent.mkdir(parents=True, exist_ok=True)
    payload={"blogger":args.blogger,"platform":platform,"count":len(articles),"articles":articles,"generated_at":datetime.now().isoformat(),"mode":"real" if args.real else "mock"}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[crawler] 已写入 {out} 共 {len(articles)} 篇", file=sys.stderr)
    # stdout 仍输出精简版供 C++ 备用
    print(json.dumps(payload, ensure_ascii=False))

if __name__=="__main__":
    main()
