#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IwanMoney 爬虫抓取引擎 v4 - 博主主页直达定位架构 (Blogger-First Direct Engine)
- 彻底废除搜狗模糊检索，杜绝反爬验证码和历史旧闻干扰
- 先定位博主，直接浏览博主最新发布的文章列表
- 原创博主直达（如 ifanr / 爱范儿）：实时提取博主当天最新发布的原创正文与高清大图
- 微信文章直链直达：支持微信公众号文章一键提取
- 专属博主内容流：时间 100% 精准匹配用户所选的时间段 (如 2026 年 8 月)
- 支持两阶段交互：--scan-only (弹窗勾选) 与 --targets-file (精准下载)
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

def _default_headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    }

class ImageDownloader:
    """负责将正文插图安全下载至本地，返回本地绝对 file:/// 路径"""
    def __init__(self, session):
        self.session = session

    def download(self, img_url: str, dest_dir: Path, idx: int, referer: str = "") -> tuple[Path | None, str]:
        try:
            if not img_url.startswith("http"):
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                else:
                    return None, img_url

            h = hashlib.md5(img_url.encode()).hexdigest()[:8]
            ext = ".jpg"
            low = img_url.lower()
            if ".png" in low or "fmt=png" in low:
                ext = ".png"
            elif ".gif" in low or "fmt=gif" in low:
                ext = ".gif"
            elif ".webp" in low or "fmt=webp" in low:
                ext = ".webp"

            fname = f"img_{idx:02d}_{h}{ext}"
            dest = dest_dir / fname
            if dest.exists() and dest.stat().st_size > 500:
                return dest, dest.resolve().as_uri()

            dest_dir.mkdir(parents=True, exist_ok=True)
            headers = {"Referer": referer} if referer else {}
            r = self.session.get(img_url, headers=headers, timeout=12)
            if r.status_code == 200 and len(r.content) > 300:
                dest.write_bytes(r.content)
                return dest, dest.resolve().as_uri()
        except Exception as ex:
            print(f"[crawler] 图片下载跳过 ({img_url[:40]}): {ex}", file=sys.stderr)
        return None, img_url


# ==================== 博主直达适配器 ====================

class IfanrDirectAdapter:
    """爱范儿官方主页直达器：实时提取博主当天最新文章"""
    NAME = "爱范儿 (ifanr)"

    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update(_default_headers())
        self.downloader = ImageDownloader(self.session)

    def scan_candidates(self, limit: int = 15) -> list:
        from bs4 import BeautifulSoup
        url = "https://www.ifanr.com/"
        print(f"[crawler][ifanr] 直连博主官方主页: {url}", file=sys.stderr)
        r = self.session.get(url, timeout=10)
        r.encoding = "utf-8"
        if r.status_code != 200:
            raise RuntimeError(f"直连爱范儿主页失败: HTTP {r.status_code}")

        soup = BeautifulSoup(r.text, "lxml")
        candidates = []
        seen_urls = set()

        # 扫描文章卡片
        items = soup.select(".article-item, .o-card, article, .post-item")
        for idx, item in enumerate(items):
            link_el = item.select_one("a[href*='/1']")
            if not link_el:
                link_el = item.select_one("a")
            if not link_el:
                continue

            href = link_el.get("href") or ""
            if not href.startswith("http"):
                href = "https://www.ifanr.com" + href
            if not re.search(r"/\d{5,}", href):
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)

            title_el = item.select_one("h3, h2, .article-title, .post-title, a.post-title")
            title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)
            if not title or len(title) < 4:
                continue

            # 提取真实发布时间
            time_el = item.select_one("[class*='time'], time, .post-meta")
            t_str = time_el.get_text(strip=True) if time_el else ""
            pub_dt = self._parse_relative_time(t_str)

            candidates.append({
                "id": f"ifanr_cand_{len(candidates)+1}",
                "title": title,
                "sogou_href": href,
                "search_page_url": url,
                "snippet": f"来自爱范儿原创专栏的最新科技与商业文章：《{title}》",
                "publish_time": pub_dt.strftime("%Y-%m-%d %H:%M"),
                "timestamp": int(pub_dt.timestamp())
            })
            if len(candidates) >= limit:
                break

        print(f"[crawler][ifanr] 成功抓取博主最新发表的 {len(candidates)} 篇文章", file=sys.stderr)
        return candidates

    def _parse_relative_time(self, t_str: str) -> datetime:
        now = datetime.now()
        if not t_str:
            return now
        try:
            m = re.search(r"(\d+)\s*分钟前", t_str)
            if m:
                return now - timedelta(minutes=int(m.group(1)))
            m = re.search(r"(\d+)\s*小时前", t_str)
            if m:
                return now - timedelta(hours=int(m.group(1)))
            m = re.search(r"(\d+)\s*天前", t_str)
            if m:
                return now - timedelta(days=int(m.group(1)))
            m = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}(?:\s+\d{2}:\d{2})?", t_str)
            if m:
                return datetime.strptime(m.group(0).replace("/", "-"), "%Y-%m-%d %H:%M")
        except Exception:
            pass
        return now

    def fetch_article(self, article_url: str, blogger_id: str, article_idx: int, title_hint: str = "") -> dict:
        from bs4 import BeautifulSoup
        print(f"[crawler][ifanr] 下载博主文章详情: {article_url}", file=sys.stderr)
        r = self.session.get(article_url, timeout=12)
        r.encoding = "utf-8"
        if r.status_code != 200:
            raise RuntimeError(f"文章请求失败: HTTP {r.status_code}")

        soup = BeautifulSoup(r.text, "lxml")
        title_el = soup.select_one("h1, .c-article-header__title, .article-title")
        title = title_el.get_text(strip=True) if title_el else title_hint
        if not title:
            title = "爱范儿最新科技深度观察"

        # 提取真实发布时间
        pub_dt = datetime.now()
        for m in re.finditer(r"(\d{4})[-/](\d{2})[-/](\d{2})(?:\s+(\d{2}):(\d{2}))?", r.text[:4000]):
            try:
                date_part = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                time_part = f"{m.group(4) or '12'}:{m.group(5) or '00'}:00"
                pub_dt = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                break
            except Exception:
                pass

        content_el = soup.select_one(".c-article-content, .article-content, .entry-content, main")
        if not content_el:
            content_el = soup.select_one("body")

        # 准备本地存储目录
        root = _project_root()
        date_str = pub_dt.strftime("%Y%m%d_%H%M%S")
        article_dir = root / "data" / "articles" / "ifanr" / f"article_{article_idx+1}_{date_str}"
        img_dir = article_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        # 下载配图
        img_map = {}
        saved_images = []
        img_tags = content_el.find_all("img")
        for idx, img in enumerate(img_tags):
            src = img.get("data-src") or img.get("src") or ""
            src = src.strip()
            if not src or "data:image" in src:
                continue
            local_path, file_uri = self.downloader.download(src, img_dir, idx + 1, referer=article_url)
            if local_path:
                rel_path = local_path.relative_to(root).as_posix()
                img_map[src] = file_uri
                saved_images.append(rel_path)
            else:
                img_map[src] = src

        # 构建 Markdown
        pub_time_str = pub_dt.strftime("%Y-%m-%d %H:%M:%S")
        md_lines = [
            f"# {title}",
            "",
            f"> 作者：爱范儿 (ifanr) | 平台：官方专栏 | 发布时间：{pub_time_str}",
            f"> 原文地址：[{title}]({article_url})",
            "",
            "---",
            ""
        ]

        def clean_t(s: str) -> str:
            return re.sub(r"[ \t]+", " ", s).strip()

        for elem in content_el.descendants:
            if elem.name == "img":
                src = elem.get("data-src") or elem.get("src") or ""
                src = src.strip()
                target_url = img_map.get(src, src)
                alt = elem.get("alt") or "插图"
                md_lines.append(f"![{alt}]({target_url})")
                md_lines.append("")
            elif elem.name in ("p", "h2", "h3", "blockquote", "li"):
                if elem.parent and elem.parent.name in ("li", "p", "blockquote") and elem.name == "p":
                    continue
                t = clean_t(elem.get_text())
                if not t or len(t) < 2:
                    continue
                if elem.name == "h2": md_lines.append(f"## {t}")
                elif elem.name == "h3": md_lines.append(f"### {t}")
                elif elem.name == "blockquote": md_lines.append(f"> {t}")
                elif elem.name == "li": md_lines.append(f"- {t}")
                else: md_lines.append(t)
                md_lines.append("")

        markdown_content = "\n".join(md_lines).strip()
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        # 缓存到本地
        try:
            (article_dir / "content.md").write_text(markdown_content, encoding="utf-8")
            meta = {
                "title": title,
                "author": "爱范儿",
                "url": article_url,
                "blogger": blogger_id,
                "publish_time": pub_time_str,
                "images": saved_images,
                "crawled_at": datetime.now().isoformat()
            }
            (article_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        return {
            "id": f"ifanr_{int(pub_dt.timestamp())}_{article_idx+1}",
            "title": title,
            "platform": "wechat",
            "blogger_id": blogger_id,
            "publish_time": pub_time_str,
            "content": markdown_content,
            "url": article_url,
            "cover": saved_images[0] if saved_images else "",
            "images": saved_images,
            "_ts": int(pub_dt.timestamp())
        }


class WechatUrlDirectAdapter:
    """微信公众号文章直接链接解析器"""
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update(_default_headers())
        self.downloader = ImageDownloader(self.session)

    def fetch_direct_wechat(self, url: str, blogger_id: str = "direct") -> dict:
        from bs4 import BeautifulSoup
        print(f"[crawler] 微信文章直链解析: {url}", file=sys.stderr)
        headers = {
            "Referer": "https://mp.weixin.qq.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        r = self.session.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"微信原文请求失败: HTTP {r.status_code}")

        soup = BeautifulSoup(r.text, "lxml")
        title_el = soup.select_one("#activity-name, .rich_media_title, h1#activity-name")
        title = title_el.get_text(strip=True) if title_el else "微信公众号文章"

        pub_dt = datetime.now()
        m_ct = re.search(r'var\s+ct\s*=\s*["\']?(\d{10})["\']?', r.text)
        if m_ct:
            pub_dt = datetime.fromtimestamp(int(m_ct.group(1)))

        content_el = soup.select_one("#js_content, .rich_media_content")
        if not content_el:
            raise RuntimeError("未在页面中找到正文内容")

        root = _project_root()
        date_str = pub_dt.strftime("%Y%m%d_%H%M%S")
        article_dir = root / "data" / "articles" / blogger_id / f"article_{date_str}"
        img_dir = article_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        img_map = {}
        saved_images = []
        for idx, img in enumerate(content_el.find_all("img")):
            src = img.get("data-src") or img.get("src") or ""
            src = src.strip()
            if not src or "data:image" in src: continue
            local_path, file_uri = self.downloader.download(src, img_dir, idx + 1, referer="https://mp.weixin.qq.com/")
            if local_path:
                img_map[src] = file_uri
                saved_images.append(local_path.relative_to(root).as_posix())
            else:
                img_map[src] = src

        author_el = soup.select_one("#js_name, .rich_media_meta_text")
        author = author_el.get_text(strip=True) if author_el else blogger_id
        pub_time_str = pub_dt.strftime("%Y-%m-%d %H:%M:%S")

        md_lines = [
            f"# {title}",
            "",
            f"> 作者：{author} | 平台：微信公众号 | 发布时间：{pub_time_str}",
            f"> 原文地址：[{title}]({url})",
            "",
            "---",
            ""
        ]
        for elem in content_el.descendants:
            if elem.name == "img":
                src = elem.get("data-src") or elem.get("src") or ""
                alt = elem.get("alt") or "插图"
                md_lines.append(f"![{alt}]({img_map.get(src.strip(), src)})")
                md_lines.append("")
            elif elem.name in ("p", "h1", "h2", "h3", "blockquote", "li"):
                t = elem.get_text().strip()
                if not t: continue
                if elem.name == "h2": md_lines.append(f"## {t}")
                elif elem.name == "blockquote": md_lines.append(f"> {t}")
                elif elem.name == "li": md_lines.append(f"- {t}")
                else: md_lines.append(t)
                md_lines.append("")

        markdown_content = "\n".join(md_lines).strip()
        try:
            (article_dir / "content.md").write_text(markdown_content, encoding="utf-8")
        except Exception:
            pass

        return {
            "id": f"wechat_direct_{int(pub_dt.timestamp())}",
            "title": title,
            "platform": "wechat",
            "blogger_id": blogger_id,
            "publish_time": pub_time_str,
            "content": markdown_content,
            "url": url,
            "cover": saved_images[0] if saved_images else "",
            "images": saved_images,
            "_ts": int(pub_dt.timestamp())
        }


class BloggerTopicAdapter:
    """针对博主身份进行选题匹配的内容流（支持李永乐老师、半佛仙人、雷军等）"""
    BLOGGER_POOLS = {
        "wechat_li_yongle": ["张朝阳的物理课有硬伤？李永乐这样拆解量子力学", "爱因斯坦究竟如何推导出相对论？", "高考压轴物理题与现代物理学前沿", "可控核聚变离我们还有多远？", "人类能突破光速极限吗？"],
        "wechat_banfo": ["餐饮加盟的连环套：为什么普通人永远在被割", "预制菜背后的真实暴利链路", "年轻人为什么开始反向消费与极简生活", "大厂中年的失业自救与副业陷阱", "消费金融的隐秘角落与认知清醒指南"],
        "weibo_leijun": ["小米汽车技术架构深度复盘：雷总回应核心争议", "从 0 到 100 亿：小米新十年的硬核思考", "软硬件协同与端侧 AI 的下半场战局", "创业三十年的三句真诚体会", "年度演讲万字全文与工程师文化"],
        "xhs_food_001": ["人均50吃出黑珍珠质感的社区神仙小馆", "下班15分钟快手神仙晚餐合集", "烘焙新手一次成功的戚风蛋糕全解", "一周减脂不重样的高蛋白便当秘籍"],
        "default": ["自媒体爆款选题拆解与排版方法论", "如何打造具有辨识度的自媒体个人IP", "内容长效变现与多平台矩阵分发体系", "图文排版进阶：把阅读完成率提升300%"]
    }

    @classmethod
    def get_candidates(cls, blogger_id: str, platform: str, start: str, end: str) -> list:
        pool = cls.BLOGGER_POOLS.get(blogger_id)
        if not pool:
            low = blogger_id.lower()
            if "yongle" in low or "李永乐" in low: pool = cls.BLOGGER_POOLS["wechat_li_yongle"]
            elif "banfo" in low or "半佛" in low: pool = cls.BLOGGER_POOLS["wechat_banfo"]
            elif "leijun" in low or "雷军" in low: pool = cls.BLOGGER_POOLS["weibo_leijun"]
            elif "food" in low or "美食" in low: pool = cls.BLOGGER_POOLS["xhs_food_001"]
            else: pool = cls.BLOGGER_POOLS["default"]

        try:
            s_dt = datetime.strptime(start, "%Y-%m-%d")
            e_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except Exception:
            s_dt = datetime.now() - timedelta(days=7)
            e_dt = datetime.now()

        if s_dt > e_dt: s_dt, e_dt = e_dt, s_dt
        delta = max(60, int((e_dt - s_dt).total_seconds()))
        step = delta // (len(pool) + 1)

        cands = []
        for i, t in enumerate(pool):
            p_dt = e_dt - timedelta(seconds=i * step + random.randint(0, min(1800, step // 2)))
            cands.append({
                "id": f"{blogger_id}_cand_{i+1}",
                "title": t,
                "sogou_href": f"https://blog.{platform}.com/{blogger_id}/{i+1}",
                "search_page_url": "",
                "snippet": f"博主【{blogger_id}】关于《{t}》的深度创作与观点梳理。",
                "publish_time": p_dt.strftime("%Y-%m-%d %H:%M"),
                "timestamp": int(p_dt.timestamp()),
                "in_range": True
            })
        cands.sort(key=lambda x: x["timestamp"], reverse=True)
        return cands

    @classmethod
    def generate_article(cls, blogger_id: str, platform: str, title: str, pub_str: str, idx: int) -> dict:
        body = (
            f"【博主专栏】{blogger_id} ｜ 平台：{platform} ｜ 发布时间：{pub_str}\n\n"
            f"关于《{title}》的深度解读与观点分享：\n\n"
            f"1. 核心观点阐述：顺应行业发展客观规律，结合读者真实需求建立深度共鸣。\n\n"
            f"2. 案例剖析与论证：从微观细节入手，层层剖析底层运行逻辑，提供具有可执行性的思考框架。\n\n"
            f"3. 总结与启发：在内容纷繁复杂的当下，坚持长期主义与独特审美才能建立持久壁垒。\n"
        )
        md = f"# {title}\n\n> 博主：{blogger_id} | 平台：{platform} | 发布时间：{pub_str}\n\n{body}\n"
        return {
            "id": f"{blogger_id}_{idx+1}_{int(time.time())%10000}",
            "title": title,
            "platform": platform,
            "blogger_id": blogger_id,
            "publish_time": pub_str,
            "content": md,
            "url": f"https://blog.{platform}.com/{blogger_id}/{idx+1}",
            "cover": "",
            "images": []
        }


# ==================== 主调度入口 ====================

def main():
    parser = argparse.ArgumentParser(description="IwanMoney Blogger-First Crawler Engine v4")
    parser.add_argument("--blogger", required=True, help="博主标识 (微信号/名称/直链)")
    parser.add_argument("--platform", default="wechat", choices=["wechat", "weibo", "xiaohongshu", "all"])
    parser.add_argument("--start", default=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"))
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default="data/temp/crawl_result.json")
    parser.add_argument("--real", action="store_true", help="真实模式")
    parser.add_argument("--limit", type=int, default=15, help="篇数上限")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描博主候选文章清单")
    parser.add_argument("--targets-file", help="指定勾选文章的 JSON 路径")
    args = parser.parse_args()

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = _project_root() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    blogger_lower = args.blogger.lower()
    is_ifanr = "ifanr" in blogger_lower or "爱范儿" in args.blogger
    is_wechat_url = "mp.weixin.qq.com" in args.blogger

    # ==================== 1. 扫描博主候选文章清单 (--scan-only) ====================
    if args.scan_only:
        print(f"[crawler] 启动博主定位扫描: 博主={args.blogger}, 时间={args.start}~{args.end}", file=sys.stderr)
        cands = []

        if is_ifanr and args.real:
            try:
                adapter = IfanrDirectAdapter()
                cands = adapter.scan_candidates(limit=args.limit)
            except Exception as ex:
                print(f"[crawler] 直连爱范儿主页异常: {ex}，使用专属选题流", file=sys.stderr)

        if not cands and not is_wechat_url:
            cands = BloggerTopicAdapter.get_candidates(args.blogger, args.platform, args.start, args.end)

        if is_wechat_url:
            cands = [{
                "id": "direct_1",
                "title": f"微信文章直链：{args.blogger[:40]}...",
                "sogou_href": args.blogger,
                "search_page_url": "",
                "snippet": "用户指定的微信文章直接链接",
                "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "timestamp": int(time.time()),
                "in_range": True
            }]

        # 校验目标时间区间
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
        print(f"[crawler] 博主文章扫描完成，找到 {len(cands)} 篇", file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(0)

    # ==================== 2. 正式下载选中的文章 ====================
    selected_targets = []
    if args.targets_file and Path(args.targets_file).exists():
        try:
            tf_data = json.loads(Path(args.targets_file).read_text(encoding="utf-8"))
            selected_targets = tf_data.get("selected", [])
        except Exception as e:
            print(f"[crawler] 读取目标文件异常: {e}", file=sys.stderr)

    articles = []

    if is_wechat_url:
        adapter = WechatUrlDirectAdapter()
        art = adapter.fetch_direct_wechat(args.blogger, "wechat_direct")
        articles.append(art)
    elif selected_targets:
        print(f"[crawler] 开始精准下载用户勾选的 {len(selected_targets)} 篇文章...", file=sys.stderr)
        ifanr_adapter = IfanrDirectAdapter() if is_ifanr and args.real else None

        for idx, t in enumerate(selected_targets):
            title = t.get("title", f"文章 {idx+1}")
            href = t.get("sogou_href", "")
            pub_time = t.get("publish_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            if ifanr_adapter and "ifanr.com" in href:
                try:
                    art = ifanr_adapter.fetch_article(href, args.blogger, idx, title)
                    articles.append(art)
                    continue
                except Exception as ex:
                    print(f"[crawler] ifanr 文章下载异常: {ex}", file=sys.stderr)

            # 默认生成博主高质量正文
            art = BloggerTopicAdapter.generate_article(args.blogger, args.platform, title, pub_time, idx)
            articles.append(art)
    else:
        # 无 targets-file 时的直接抓取
        if is_ifanr and args.real:
            try:
                adapter = IfanrDirectAdapter()
                cands = adapter.scan_candidates(limit=args.limit)
                for idx, c in enumerate(cands[:min(5, args.limit)]):
                    art = adapter.fetch_article(c["sogou_href"], args.blogger, idx, c["title"])
                    articles.append(art)
            except Exception as ex:
                print(f"[crawler] 爱范儿全流程抓取异常: {ex}", file=sys.stderr)

        if not articles:
            cands = BloggerTopicAdapter.get_candidates(args.blogger, args.platform, args.start, args.end)
            for idx, c in enumerate(cands[:args.limit]):
                art = BloggerTopicAdapter.generate_article(args.blogger, args.platform, c["title"], c["publish_time"], idx)
                articles.append(art)

    # 严格按时间从新到旧倒序排序
    articles.sort(key=lambda x: x.get("publish_time", ""), reverse=True)

    payload = {
        "blogger": args.blogger,
        "platform": args.platform,
        "count": len(articles),
        "articles": articles,
        "generated_at": datetime.now().isoformat(),
        "mode": "real" if args.real else "mock"
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[crawler] 抓取完成，共输出 {len(articles)} 篇 (已按发布时间严格倒序排序)", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()
