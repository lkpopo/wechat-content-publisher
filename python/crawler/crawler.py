#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫抓取模块 - 接口骨架 + Mock (Step1)

设计目标：
  - 预留多平台接口：wechat / weibo / xiaohongshu
  - 第一阶段用 Mock 假数据返回，打通 C++ 链路
  - 第二阶段接入真实 Playwright/Selenium + BeautifulSoup

调用约定（与 C++ QProcess 一致）：
  python crawler.py --blogger <id> --platform wechat --start 2026-08-01 --end 2026-08-31 --output data/temp/crawl_result.json

输出：JSON 文件，供 C++ 读取后刷新文章列表
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# ============ 平台接口抽象 ============
class BaseCrawler:
    platform: str = "base"
    def crawl(self, blogger_id: str, start: str, end: str):
        raise NotImplementedError

class WechatCrawler(BaseCrawler):
    platform = "wechat"
    def crawl(self, blogger_id, start, end):
        # TODO Step2: Playwright 访问 https://mp.weixin.qq.com / 搜狗微信
        return mock_articles(blogger_id, self.platform, start, end)

class WeiboCrawler(BaseCrawler):
    platform = "weibo"
    def crawl(self, blogger_id, start, end):
        # TODO Step2: 微博开放 API / 移动端 m.weibo.cn 抓取
        return mock_articles(blogger_id, self.platform, start, end)

class XiaohongshuCrawler(BaseCrawler):
    platform = "xiaohongshu"
    def crawl(self, blogger_id, start, end):
        # TODO Step2: 小红书 web 抓取（需登录态）
        return mock_articles(blogger_id, self.platform, start, end)

CRAWLER_MAP = {
    "wechat": WechatCrawler,
    "weibo": WeiboCrawler,
    "xiaohongshu": XiaohongshuCrawler,
}

def mock_articles(blogger_id: str, platform: str, start: str, end: str):
    titles_pool = [
        "AI 颠覆内容创作的 5 个真相",
        "为什么你的公众号阅读量上不去？",
        "深度：自媒体搬运的合规边界",
        "实测：用 Grok 润色文章效率提升 300%",
        "今日头条推荐算法全解析",
        "从 0 到 10w 粉的运营手记",
    ]
    articles = []
    for i in range(random.randint(3, 6)):
        title = random.choice(titles_pool) + f" ({blogger_id} #{i+1})"
        articles.append({
            "id": f"{blogger_id}_{i+1}",
            "title": title,
            "platform": platform,
            "blogger_id": blogger_id,
            "publish_time": (datetime.now() - timedelta(days=i)).isoformat(),
            "content": f"这是 {blogger_id} 在 {platform} 的第 {i+1} 篇 Mock 文章正文。\n\n标题：{title}\n时间段：{start} 至 {end}\n\n第一段：引入话题，提出问题。\n第二段：展开论述，给出案例。\n第三段：总结观点，引导互动。",
            "url": f"https://mock.{platform}.com/{blogger_id}/{i+1}",
            "cover": "",
        })
    return articles

def main():
    parser = argparse.ArgumentParser(description="Crawler Mock - IwanMoney")
    parser.add_argument("--blogger", required=True, help="博主ID")
    parser.add_argument("--platform", default="wechat", choices=["wechat","weibo","xiaohongshu","all"])
    parser.add_argument("--start", default=(datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"))
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default="data/temp/crawl_result.json")
    args = parser.parse_args()

    platform = args.platform if args.platform != "all" else "wechat"
    crawler_cls = CRAWLER_MAP.get(platform, WechatCrawler)
    crawler = crawler_cls()

    print(f"[crawler] 平台={platform} 博主={args.blogger} 时间={args.start}~{args.end}", flush=True)
    articles = crawler.crawl(args.blogger, args.start, args.end)

    out = Path(args.output)
    # 若为相对路径，则相对于项目根
    if not out.is_absolute():
        out = Path(__file__).resolve().parents[2] / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"blogger": args.blogger, "platform": platform, "count": len(articles), "articles": articles}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[crawler] 已写入 {out} 共 {len(articles)} 篇", flush=True)
    # 同时 stdout 输出供 C++ 备用
    print(json.dumps(articles, ensure_ascii=False))

if __name__ == "__main__":
    main()
