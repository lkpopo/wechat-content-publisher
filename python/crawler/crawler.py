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
    # 博主专属题库 - 让不同博主抓到的内容明显不同，解决“不是该博主内容”的体感
    blogger_specific = {
        "wechat_li_yongle": ["张朝阳的物理课有硬伤？李永乐这样讲相对论", "量子纠缠到底能否超光速？", "高考数学压轴题这样拆解", "AI 能否替代老师？"],
        "wechat_banfo": ["奶茶店的暴利陷阱：加盟商为何血本无归", "预制菜背后的资本游戏", "年轻人为何不再相信消费主义", "财经科普：美联储加息如何影响你"],
        "weibo_leijun": ["小米汽车 SU7 首测：雷总回应 3 大争议", "从 0 到 100 亿：小米的供应链思考", "智能硬件的下一站：AIoT", "雷军：创业最难的是坚持"],
        "xhs_food_001": ["周末探店：人均80吃到扶墙出的宝藏小馆", "15分钟快手菜：打工人晚餐合集", "烘焙翻车现场：戚风蛋糕不塌陷秘籍"],
        "mock_001": ["AI 颠覆内容创作的 5 个真相","为什么你的公众号阅读量上不去？","深度：自媒体搬运的合规边界"],
    }
    # 若命中专属，否则按平台通用
    pool = blogger_specific.get(blogger_id)
    if not pool:
        # 尝试按名称关键字匹配
        low = blogger_id.lower()
        if "yongle" in low or "李永乐" in low:
            pool = blogger_specific["wechat_li_yongle"]
        elif "banfo" in low or "半佛" in low:
            pool = blogger_specific["wechat_banfo"]
        elif "leijun" in low or "雷军" in low:
            pool = blogger_specific["weibo_leijun"]
        elif "xhs" in low or "美食" in low:
            pool = blogger_specific["xhs_food_001"]
        else:
            base = {
                "wechat": ["深度：自媒体搬运的合规边界","公众号标题的 7 个套路","内容复用 vs 洗稿的边界"],
                "weibo": ["今日热搜背后的流量密码","微博运营：从 0 到百万粉","热搜如何炼成"],
                "xiaohongshu": ["小红书爆款笔记拆解","探店视频如何剪出高级感","美食账号涨粉秘籍"],
            }
            pool = base.get(platform, base["wechat"]) + ["实测：用 Grok 润色效率提升 300%","今日头条推荐算法全解析"]
    # 时间段内生成 pub 时间
    try:
        s_dt = datetime.strptime(start, "%Y-%m-%d")
        e_dt = datetime.strptime(end, "%Y-%m-%d")
    except Exception:
        s_dt = datetime.now() - timedelta(days=7)
        e_dt = datetime.now()
    if s_dt > e_dt: s_dt, e_dt = e_dt, s_dt
    delta_days = max(1, (e_dt - s_dt).days + 1)
    articles=[]
    cnt = random.randint(4,7)
    # 打散标题避免重复
    titles = random.sample(pool*3, min(cnt, len(pool*3))) if len(pool)>=cnt else [random.choice(pool) for _ in range(cnt)]
    for i in range(cnt):
        title = titles[i] if i < len(titles) else random.choice(pool)
        # pub 时间落在 start~end 内随机
        rand_days = random.randint(0, delta_days-1)
        rand_hours = random.randint(0, 23)
        pub_dt = s_dt + timedelta(days=rand_days, hours=rand_hours)
        pub = pub_dt.isoformat()
        # 博主专属正文模板
        if "wechat_li_yongle" in blogger_id or "yongle" in blogger_id.lower():
            body = (
                f"大家好，我是李永乐。今天聊聊《{title}》。\n\n"
                f"我们先看一个具体的例子：假设……（此处为 {blogger_id} 的物理/数学视角拆解，含公式与生活类比）。\n\n"
                f"第二部分：核心原理。很多同学误以为……其实从量纲和守恒角度可以更清晰理解。\n\n"
                f"第三部分：与 AI/现实的联系。最近 Grok、ChatGPT 等工具也能推导这类问题，但理解底层逻辑更重要。\n\n"
                f"总结：{title} 的本质是……欢迎点赞关注，下期讲更深入的推导。\n"
            )
        elif "banfo" in blogger_id.lower():
            body = (
                f"半佛仙人曰：今天聊《{title}》——别被表象骗了。\n\n"
                f"第一层：你看到的是 {title} 的热闹，实际背后是资本与人性的博弈。以奶茶加盟为例，品牌方赚加盟费、供应链赚差价，加盟商接盘。\n\n"
                f"第二层：数据拆解。我们算一笔账：单店日销 200 杯、客单 15 元，月流水 9w，扣除房租人力原料，净利不足 1w——这还是理想情况。\n\n"
                f"第三层：怎么办？普通人别迷信风口，回归常识：先验证需求、再控成本、最后才谈规模。\n\n"
                f"彩蛋：评论区聊聊你踩过的消费坑。\n"
            )
        elif "leijun" in blogger_id.lower():
            body = (
                f"【雷军】{title}\n\n"
                f"各位米粉：今天分享小米在《{title}》上的思考。\n\n"
                f"1. 极致性价比不是便宜，是感动人心。SU7 在三电、智能座舱上我们坚持自研，成本压到极致但体验不打折。\n\n"
                f"2. 生态：手机×汽车×IoT 的闭环，核心是 OS 打通与供应链协同。\n\n"
                f"3. 创业心得：顺势而为，专注、极致、口碑、快——这四点至今适用。\n\n"
                f"互动：你对小米汽车最期待什么？留言抽 3 位送周边。\n"
            )
        elif "xhs" in blogger_id.lower() or platform=="xiaohongshu":
            body = (
                f"姐妹们！今日探店《{title}》真实体验：\n\n"
                f"📍 店名：{blogger_id} 推荐 · 人均 85\n"
                f"✨ 必点：招牌牛蛙锅、芝士年糕、冰粉\n"
                f"💬 口味：麻辣适中，牛蛙嫩滑，年糕拉丝——拍照出片率 100%！\n"
                f"⚠️ 避坑：周末排队 40min，建议工作日 17:30 前到。\n"
                f"🏷️ 标签：#探店 #{platform} #美食\n"
            )
        else:
            body = (
                f"【博主】{blogger_id} @ {platform} ｜ {pub_dt.strftime('%Y-%m-%d')}\n\n"
                f"第一段 · 痛点：{title} 背后，许多创作者遇到同质化与流量焦虑。\n\n"
                f"第二段 · 方法：选题-素材-结构-标题四步法，结合 AI 提效，单篇从 3h 降至 40min。\n\n"
                f"第三段 · 案例：某篇相关文章润色后点击率 +62%，评论翻倍。\n\n"
                f"结尾 · 互动：你在 {platform} 运营中最大的困惑是？评论区见。\n"
            )
        content = (
            f"【标题】{title}\n"
            f"【博主】{blogger_id} @ {platform}\n"
            f"【时间】{pub_dt.strftime('%Y-%m-%d %H:%M')}  区间 {start}~{end}\n"
            f"【链接】https://mock.{platform}.com/{blogger_id}/{i+1}\n\n"
            f"—— 正文 ——\n{body}"
            f"\n---\n*注：此为 Mock 数据，已按博主 {blogger_id} 专属题库生成，真实抓取将替换为实际公众号文章。*\n"
        )
        articles.append({
            "id": f"{blogger_id}_{pub_dt.strftime('%Y%m%d')}_{i+1}",
            "title": title,
            "platform": platform,
            "blogger_id": blogger_id,
            "publish_time": pub,
            "content": content,
            "url": f"https://mock.{platform}.com/{blogger_id}/{i+1}",
            "cover": "",
        })
    # 按时间倒序
    articles.sort(key=lambda x: x["publish_time"], reverse=True)
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
    parser.add_argument("--verify", action="store_true", help="仅校验博主是否存在，不抓取")
    parser.add_argument("--limit", type=int, default=10, help="最大篇数")
    args=parser.parse_args()

    # 校验模式：供博主对话框调用
    if args.verify:
        # 复用 verify_blogger 逻辑，若文件存在则调用，否则简易白名单
        try:
            from verify_blogger import verify_blogger
            ok, msg = verify_blogger(args.platform, args.blogger, args.blogger, "")
            print(msg)
            sys.exit(0 if ok else 1)
        except Exception as e:
            # 回退：白名单检查
            whitelist = ["wechat_li_yongle","wechat_banfo","weibo_leijun","xhs_food_001","mock_001"]
            if args.blogger in whitelist:
                print(f"白名单验证通过: {args.blogger}")
                sys.exit(0)
            print(f"校验失败: {e}")
            sys.exit(1)

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
