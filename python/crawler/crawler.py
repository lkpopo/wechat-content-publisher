#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫抓取 v3 - 支持候选扫描、文章勾选下载、精准时间提取、图片绝对路径与 Markdown 本地化
- 支持 --scan-only：快速检索候选文章及真实发布时间，供前端弹窗选择
- 支持 --targets-file：根据前端勾选的清单下载选定文章的正文与高清图片
- 提取微信正文原生时间戳 (var ct = "...")，严格时间排序
"""

import argparse
import json
import random
import time
import re
import sys
import os
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# 确保在 Windows 控制台或管道下 UTF-8 正常输出
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://weixin.sogou.com/",
        "Connection": "keep-alive"
    }

class WechatCrawlerEngine:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update(_headers())
        self._warmed_up = False

    def warmup(self):
        if self._warmed_up:
            return
        try:
            r = self.session.get("https://weixin.sogou.com/", timeout=10)
            self._warmed_up = True
        except Exception:
            pass

    def search_candidates(self, keyword: str, limit: int = 20) -> list:
        """检索候选文章"""
        self.warmup()
        from bs4 import BeautifulSoup

        q = urllib.parse.quote(keyword)
        search_url = f"https://weixin.sogou.com/weixin?type=2&query={q}&ie=utf8"
        headers = {"Referer": "https://weixin.sogou.com/"}
        r = self.session.get(search_url, headers=headers, timeout=12)

        if r.status_code != 200 or "antispider" in r.url or "验证码" in r.text:
            raise RuntimeError("搜狗搜索频控触发验证码")

        soup = BeautifulSoup(r.text, "lxml")
        items = soup.select("ul.news-list li")
        if not items:
            items = soup.select(".news-box")

        candidates = []
        for idx, li in enumerate(items[:limit]):
            try:
                a_el = li.select_one("h3 a, .txt-box a, h4 a")
                if not a_el:
                    continue
                title = a_el.get_text(strip=True)
                href = a_el.get("href") or ""
                snippet_el = li.select_one("p.txt-info, .txt-info, .s-p3")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # 提取搜狗时间戳
                ts = None
                m_ts = re.search(r"timeConvert\(['\"](\d+)['\"]\)", str(li))
                if m_ts:
                    ts = int(m_ts.group(1))
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else datetime.now().strftime("%Y-%m-%d")

                candidates.append({
                    "id": f"cand_{idx+1}",
                    "title": title,
                    "sogou_href": href,
                    "search_page_url": r.url,
                    "snippet": snippet,
                    "publish_time": date_str,
                    "timestamp": ts or int(time.time())
                })
            except Exception:
                continue

        return candidates

    def resolve_wechat_url(self, sogou_href: str, search_page_url: str) -> str:
        if "mp.weixin.qq.com" in sogou_href:
            return sogou_href

        link_url = sogou_href
        if sogou_href.startswith("/"):
            link_url = "https://weixin.sogou.com" + sogou_href
        elif not sogou_href.startswith("http"):
            link_url = "https://weixin.sogou.com/link?url=" + sogou_href

        headers = {"Referer": search_page_url or "https://weixin.sogou.com/"}
        r = self.session.get(link_url, headers=headers, timeout=12)

        if "antispider" in r.url:
            raise RuntimeError("搜狗链接跳转触发反爬")

        parts = re.findall(r"url\s*\+=\s*['\"]([^'\"]+)['\"]", r.text)
        if parts:
            real_url = "".join(parts).replace("@", "").replace("&amp;", "&")
            if "mp.weixin.qq.com" in real_url:
                return real_url

        m = re.search(r"https://mp\.weixin\.qq\.com/s[^\s'\"<>]+", r.text)
        if m:
            return m.group(0).replace("&amp;", "&").replace("@", "")

        if "mp.weixin.qq.com" in r.url:
            return r.url

        raise RuntimeError(f"未能从跳转页提取微信 URL: {r.url[:60]}")

    def download_image(self, img_url: str, dest_dir: Path, idx: int) -> tuple[Path | None, str]:
        try:
            if not img_url.startswith("http"):
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                else:
                    return None, img_url

            h = hashlib.md5(img_url.encode()).hexdigest()[:8]
            ext = ".jpg"
            if ".png" in img_url.lower() or "fmt=png" in img_url.lower():
                ext = ".png"
            elif ".gif" in img_url.lower() or "fmt=gif" in img_url.lower():
                ext = ".gif"
            elif ".webp" in img_url.lower() or "fmt=webp" in img_url.lower():
                ext = ".webp"

            fname = f"img_{idx:02d}_{h}{ext}"
            dest = dest_dir / fname
            if dest.exists() and dest.stat().st_size > 500:
                abs_url = dest.resolve().as_uri()
                return dest, abs_url

            dest_dir.mkdir(parents=True, exist_ok=True)
            r = self.session.get(img_url, headers={"Referer": "https://mp.weixin.qq.com/"}, timeout=15)
            if r.status_code == 200 and len(r.content) > 300:
                dest.write_bytes(r.content)
                abs_url = dest.resolve().as_uri()
                return dest, abs_url
        except Exception:
            pass
        return None, img_url

    def fetch_article_detail(self, wechat_url: str, blogger_id: str, article_idx: int, title_hint: str = "", initial_ts: int = None) -> tuple[str, str, list, str, datetime]:
        from bs4 import BeautifulSoup

        headers = {
            "Referer": "https://weixin.sogou.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        r = self.session.get(wechat_url, headers=headers, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"微信原文请求失败: HTTP {r.status_code}")

        soup = BeautifulSoup(r.text, "lxml")

        title_el = soup.select_one("#activity-name, .rich_media_title, h1#activity-name")
        title = title_el.get_text(strip=True) if title_el else title_hint
        if not title:
            title = "未命名微信文章"

        pub_datetime = None
        m_ct = re.search(r'var\s+ct\s*=\s*["\']?(\d{10})["\']?', r.text)
        if m_ct:
            ts = int(m_ct.group(1))
            pub_datetime = datetime.fromtimestamp(ts)
        elif initial_ts:
            pub_datetime = datetime.fromtimestamp(initial_ts)
        else:
            pub_datetime = datetime.now()

        content_el = soup.select_one("#js_content")
        if not content_el:
            content_el = soup.select_one(".rich_media_content, #img-content")
        if not content_el:
            raise RuntimeError("未在微信页面中找到正文内容")

        root = _project_root()
        safe_blogger = re.sub(r"[^\w\-]", "_", blogger_id)[:24]
        date_str = pub_datetime.strftime("%Y%m%d_%H%M%S")
        article_dir = root / "data" / "articles" / safe_blogger / f"article_{article_idx+1}_{date_str}"
        img_dir = article_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        img_tags = content_el.find_all("img")
        img_map = {}
        saved_images = []

        for idx, img in enumerate(img_tags):
            src = img.get("data-src") or img.get("src") or ""
            src = src.strip()
            if not src or "data:image" in src:
                continue
            if src.startswith("//"):
                src = "https:" + src

            local_path, file_uri = self.download_image(src, img_dir, idx + 1)
            if local_path:
                rel_path = local_path.relative_to(root).as_posix()
                img_map[src] = file_uri
                saved_images.append(rel_path)
            else:
                img_map[src] = src

        author_el = soup.select_one("#js_name, .rich_media_meta_text, #post-user")
        author = author_el.get_text(strip=True) if author_el else blogger_id
        pub_time_str = pub_datetime.strftime("%Y-%m-%d %H:%M:%S")

        md_lines = [
            f"# {title}",
            "",
            f"> 作者：{author} | 平台：微信公众号 | 发布时间：{pub_time_str}",
            f"> 原文地址：[{title}]({wechat_url})",
            "",
            "---",
            ""
        ]

        def clean_text(t: str) -> str:
            return re.sub(r"[ \t]+", " ", t).strip()

        for elem in content_el.descendants:
            if elem.name == "img":
                src = elem.get("data-src") or elem.get("src") or ""
                src = src.strip()
                if src.startswith("//"):
                    src = "https:" + src
                img_target = img_map.get(src, src)
                alt = elem.get("alt") or "插图"
                md_lines.append(f"![{alt}]({img_target})")
                md_lines.append("")
            elif elem.name in ("p", "h1", "h2", "h3", "blockquote", "li"):
                if elem.parent and elem.parent.name in ("li", "p", "blockquote") and elem.name == "p":
                    continue
                t = clean_text(elem.get_text())
                if not t:
                    continue
                if elem.name == "h1":
                    md_lines.append(f"# {t}")
                elif elem.name == "h2":
                    md_lines.append(f"## {t}")
                elif elem.name == "h3":
                    md_lines.append(f"### {t}")
                elif elem.name == "blockquote":
                    md_lines.append(f"> {t}")
                elif elem.name == "li":
                    md_lines.append(f"- {t}")
                else:
                    md_lines.append(t)
                md_lines.append("")

        markdown_content = "\n".join(md_lines).strip()
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        try:
            (article_dir / "content.md").write_text(markdown_content, encoding="utf-8")
            meta = {
                "title": title,
                "author": author,
                "url": wechat_url,
                "blogger": blogger_id,
                "publish_time": pub_time_str,
                "images": saved_images,
                "crawled_at": datetime.now().isoformat()
            }
            (article_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        return markdown_content, title, saved_images, wechat_url, pub_datetime

def generate_mock_candidates(blogger_id: str, platform: str, start: str, end: str) -> list:
    """按时间段生成候选 Mock 文章列表"""
    titles = [
        f"{blogger_id}：2026年最新深度选题与行业观察",
        f"自媒体运营实战：如何在当下获取优质流量",
        f"优质内容生产指南与自动化排版实践",
        f"从0到1拆解爆款推文与商业转化路径",
        f"自媒体从业者必看：效率翻倍的工具箱"
    ]
    try:
        s_dt = datetime.strptime(start, "%Y-%m-%d")
        e_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except Exception:
        s_dt = datetime.now() - timedelta(days=7)
        e_dt = datetime.now()

    if s_dt > e_dt: s_dt, e_dt = e_dt, s_dt
    delta = max(60, int((e_dt - s_dt).total_seconds()))
    step = delta // (len(titles) + 1)

    cands = []
    for i, t in enumerate(titles):
        p_dt = e_dt - timedelta(seconds=i * step + random.randint(0, min(1800, step // 2)))
        cands.append({
            "id": f"mock_cand_{i+1}",
            "title": t,
            "sogou_href": f"https://mock.{platform}.com/{blogger_id}/{i+1}",
            "search_page_url": "",
            "snippet": f"关于《{t}》的摘要介绍，探讨自媒体生产与创作要点。",
            "publish_time": p_dt.strftime("%Y-%m-%d %H:%M"),
            "timestamp": int(p_dt.timestamp())
        })
    cands.sort(key=lambda x: x["timestamp"], reverse=True)
    return cands

def main():
    parser = argparse.ArgumentParser(description="IwanMoney Crawler Engine v3")
    parser.add_argument("--blogger", required=True, help="博主标识或文章直链")
    parser.add_argument("--platform", default="wechat", choices=["wechat", "weibo", "xiaohongshu", "all"])
    parser.add_argument("--start", default=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"))
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default="data/temp/crawl_result.json")
    parser.add_argument("--real", action="store_true", help="真实抓取模式")
    parser.add_argument("--limit", type=int, default=15, help="篇数限制")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描候选文章列表，供弹窗勾选")
    parser.add_argument("--targets-file", help="指定勾选的目标文章 JSON 文件路径")
    args = parser.parse_args()

    engine = WechatCrawlerEngine()
    keyword = args.blogger.replace("wechat_", "").replace("_", " ").strip()
    if "ifanr" in args.blogger.lower():
        keyword = "爱范儿"
    elif "yongle" in args.blogger.lower():
        keyword = "李永乐老师"
    elif "banfo" in args.blogger.lower():
        keyword = "半佛仙人"

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = _project_root() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 扫描候选模式 (--scan-only)
    if args.scan_only:
        print(f"[crawler] 启动候选扫描: 博主={args.blogger}, 关键词={keyword}", file=sys.stderr)
        cands = []
        if args.real and "mp.weixin.qq.com" not in args.blogger:
            try:
                cands = engine.search_candidates(keyword, limit=args.limit)
            except Exception as e:
                print(f"[crawler] 搜索候选失败，采用 Mock 候选: {e}", file=sys.stderr)

        if not cands:
            cands = generate_mock_candidates(args.blogger, args.platform, args.start, args.end)

        # 标记是否在目标时间区间内
        try:
            s_dt = datetime.strptime(args.start, "%Y-%m-%d")
            e_dt = datetime.strptime(args.end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except Exception:
            s_dt = datetime.now() - timedelta(days=365)
            e_dt = datetime.now()

        for c in cands:
            dt = datetime.fromtimestamp(c["timestamp"])
            c["in_range"] = (s_dt <= dt <= e_dt)

        payload = {
            "blogger": args.blogger,
            "platform": args.platform,
            "start": args.start,
            "end": args.end,
            "count": len(cands),
            "candidates": cands,
            "generated_at": datetime.now().isoformat()
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[crawler] 候选扫描完成，共找到 {len(cands)} 篇", file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(0)

    # 2. 指定目标下载模式 (--targets-file)
    selected_targets = []
    if args.targets_file and Path(args.targets_file).exists():
        try:
            tf_data = json.loads(Path(args.targets_file).read_text(encoding="utf-8"))
            selected_targets = tf_data.get("selected", [])
        except Exception as e:
            print(f"[crawler] 读取目标文件异常: {e}", file=sys.stderr)

    articles = []
    if selected_targets:
        print(f"[crawler] 开始精准下载用户勾选的 {len(selected_targets)} 篇文章...", file=sys.stderr)
        for idx, t in enumerate(selected_targets):
            title = t.get("title", f"文章 {idx+1}")
            href = t.get("sogou_href", "")
            search_page = t.get("search_page_url", "")
            ts = t.get("timestamp")

            if "mock" in href or not args.real:
                # 生成高质量 Mock
                pub_str = t.get("publish_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                body = (
                    f"【博主】{args.blogger} @ {args.platform} ｜ 发布于 {pub_str}\n\n"
                    f"导语：关于《{title}》的深度分析与复盘。\n\n"
                    f"1. 核心洞察：结合受众心理与平台分发机制，强化内容吸引力。\n\n"
                    f"2. 结构拆解：开头抛出痛点，中间层层推进，结尾引导评论互动。\n\n"
                    f"3. 商业价值：提升自媒体内容变现效率与长尾效应。\n"
                )
                md = f"# {title}\n\n> 平台：{args.platform} | 发布时间：{pub_str}\n\n{body}\n"
                articles.append({
                    "id": f"{args.blogger}_{int(ts or time.time())}_{idx+1}",
                    "title": title,
                    "platform": args.platform,
                    "blogger_id": args.blogger,
                    "publish_time": pub_str,
                    "content": md,
                    "url": href,
                    "cover": "",
                    "images": [],
                    "_ts": ts or int(time.time())
                })
            else:
                try:
                    print(f"[crawler] 下载选中文章 {idx+1}/{len(selected_targets)}: 《{title[:25]}》", file=sys.stderr)
                    real_url = engine.resolve_wechat_url(href, search_page)
                    time.sleep(0.5)
                    md, real_title, imgs, final_u, pub_dt = engine.fetch_article_detail(
                        real_url, args.blogger, idx, title, ts
                    )
                    articles.append({
                        "id": f"{args.blogger}_{int(pub_dt.timestamp())}_{idx+1}",
                        "title": real_title,
                        "platform": args.platform,
                        "blogger_id": args.blogger,
                        "publish_time": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "content": md,
                        "url": final_u,
                        "cover": imgs[0] if imgs else "",
                        "images": imgs,
                        "_ts": int(pub_dt.timestamp())
                    })
                except Exception as ex:
                    print(f"[crawler] 下载 《{title}》 失败: {ex}", file=sys.stderr)

    # 兜底直接抓取
    if not articles:
        # 直链或常规抓取
        if "mp.weixin.qq.com" in args.blogger:
            md, real_title, imgs, final_u, pub_dt = engine.fetch_article_detail(args.blogger, "direct_link", 0)
            articles.append({
                "id": f"wechat_direct_{int(pub_dt.timestamp())}",
                "title": real_title,
                "platform": "wechat",
                "blogger_id": "direct_link",
                "publish_time": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "content": md,
                "url": final_u,
                "cover": imgs[0] if imgs else "",
                "images": imgs,
                "_ts": int(pub_dt.timestamp())
            })
        else:
            mock_cands = generate_mock_candidates(args.blogger, args.platform, args.start, args.end)
            for idx, c in enumerate(mock_cands[:args.limit]):
                articles.append({
                    "id": f"{args.blogger}_{c['timestamp']}_{idx+1}",
                    "title": c["title"],
                    "platform": args.platform,
                    "blogger_id": args.blogger,
                    "publish_time": c["publish_time"],
                    "content": f"# {c['title']}\n\n> 发布时间：{c['publish_time']}\n\n{c['snippet']}\n",
                    "url": c["sogou_href"],
                    "cover": "",
                    "images": [],
                    "_ts": c["timestamp"]
                })

    articles.sort(key=lambda x: x.get("_ts", 0), reverse=True)
    for a in articles:
        if "_ts" in a:
            del a["_ts"]

    payload = {
        "blogger": args.blogger,
        "platform": args.platform,
        "count": len(articles),
        "articles": articles,
        "generated_at": datetime.now().isoformat(),
        "mode": "real" if args.real else "mock"
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[crawler] 抓取完成，输出 {len(articles)} 篇", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()
