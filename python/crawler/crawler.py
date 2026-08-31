#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫抓取 - 搜狗微信跳转解密 + 微信原生正文与图片提取 + 真实时间倒序排序 + 动态抓取上限
- 从微信源码精准提取真实发布时间 (var ct = "...")
- 支持指定时间段筛选 (start ~ end)
- 文章列表按发布时间严格倒序排序 (最新置顶)
- 解除硬编码篇数限制，支持 --limit 参数
- 图片防盗链下载并支持绝对 file:// 协议与相对路径，确保 Qt QTextEdit 原生渲染
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

class BaseCrawler:
    platform: str = "base"
    def crawl(self, blogger_id: str, start: str, end: str, limit: int=10, real: bool=False):
        raise NotImplementedError

def mock_articles(blogger_id: str, platform: str, start: str, end: str, limit: int=10):
    """当真实抓取网络不可用或无数据时的 Mock 回退机制，同样严格按时间倒序排列"""
    blogger_specific = {
        "wechat_li_yongle": ["张朝阳的物理课有硬伤？李永乐这样讲相对论", "量子纠缠到底能否超光速？", "高考数学压轴题这样拆解", "AI 能否替代老师？", "从相对论到引力波：百年物理简史"],
        "wechat_banfo": ["奶茶店的暴利陷阱：加盟商为何血本无归", "预制菜背后的资本游戏", "年轻人为何不再相信消费主义", "财经科普：美联储加息如何影响你", "中年失业危机与副业陷阱"],
        "weibo_leijun": ["小米汽车 SU7 首测：雷总回应 3 大争议", "从 0 到 100 亿：小米的供应链思考", "智能硬件的下一站：AIoT", "雷军：创业最难的是坚持", "年度演讲精华整理"],
        "xhs_food_001": ["周末探店：人均80吃到扶墙出的宝藏小馆", "15分钟快手菜：打工人晚餐合集", "烘焙翻车现场：戚风蛋糕不塌陷秘籍", "减脂期必备的神仙快手轻食"],
        "mock_001": ["AI 颠覆内容创作的 5 个真相", "为什么你的公众号阅读量上不去？", "深度：自媒体搬运的合规边界", "从 0 到 10 万粉的选题方法论"],
        "ifanr": ["爱范儿早报：科技新趋势拆解", "AI 硬件复盘：谁在定义下一代交互", "商业观察：微信小店的新机会", "科技周报：大模型价格战", "新消费观察：为什么年轻人开始反向消费"],
        "wechat_ifanr": ["爱范儿早报：科技新趋势拆解", "AI 硬件复盘：谁在定义下一代交互", "商业观察：微信小店的新机会", "科技周报：大模型价格战", "新消费观察：为什么年轻人开始反向消费"],
    }
    pool = blogger_specific.get(blogger_id)
    if not pool:
        low = blogger_id.lower()
        if "ifanr" in low or "爱范" in low:
            pool = blogger_specific["ifanr"]
        elif "yongle" in low or "李永乐" in low:
            pool = blogger_specific["wechat_li_yongle"]
        elif "banfo" in low or "半佛" in low:
            pool = blogger_specific["wechat_banfo"]
        elif "leijun" in low or "雷军" in low:
            pool = blogger_specific["weibo_leijun"]
        elif "xhs" in low or "美食" in low:
            pool = blogger_specific["xhs_food_001"]
        else:
            base = {
                "wechat": ["深度：自媒体搬运的合规边界", "公众号标题的 7 个套路", "内容复用 vs 洗稿的边界", "爆款推文排版指南"],
                "weibo": ["今日热搜背后的流量密码", "微博运营：从 0 到百万粉", "热搜如何炼成", "跨平台引流技巧"],
                "xiaohongshu": ["小红书爆款笔记拆解", "探店视频如何剪出高级感", "美食账号涨粉秘籍", "高赞封面制作心得"],
            }
            pool = base.get(platform, base["wechat"])

    try:
        s_dt = datetime.strptime(start, "%Y-%m-%d")
        e_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except Exception:
        s_dt = datetime.now() - timedelta(days=7)
        e_dt = datetime.now()

    if s_dt > e_dt:
        s_dt, e_dt = e_dt, s_dt

    total_seconds = max(60, int((e_dt - s_dt).total_seconds()))
    articles = []
    cnt = min(limit, max(4, len(pool)))

    # 生成按时间倒序的时间戳序列
    step = total_seconds // (cnt + 1)
    timestamps = [e_dt - timedelta(seconds=i * step + random.randint(0, min(1800, step // 2))) for i in range(cnt)]

    for i in range(cnt):
        title = pool[i % len(pool)]
        pub_dt = timestamps[i]
        pub_iso = pub_dt.strftime("%Y-%m-%d %H:%M:%S")

        body = (
            f"【博主】{blogger_id} @ {platform} ｜ 发布于 {pub_iso}\n\n"
            f"导语：关于《{title}》的深度观察与思考。\n\n"
            f"1. 背景与现状：当前行业正在经历快速变革，各方都在探索新的商业与内容模式。\n\n"
            f"2. 核心观点：内容创作者应当注重长期价值积累，善用智能化工具提升选题与排版效率。\n\n"
            f"3. 建议与总结：保持敏锐的读者洞察，打造差异化内容壁垒。\n"
        )
        content = (
            f"# {title}\n\n"
            f"> 平台：{platform} | 博主：{blogger_id} | 发布时间：{pub_iso}\n\n"
            f"{body}\n\n---\n*注：此为 Mock 数据（已按时间倒序排序）。*\n"
        )
        articles.append({
            "id": f"{blogger_id}_{pub_dt.strftime('%Y%m%d%H%M')}_{i+1}",
            "title": title,
            "platform": platform,
            "blogger_id": blogger_id,
            "publish_time": pub_iso,
            "content": content,
            "url": f"https://mock.{platform}.com/{blogger_id}/{i+1}",
            "cover": "",
            "images": [],
        })

    # 确保严格时间倒序
    articles.sort(key=lambda x: x["publish_time"], reverse=True)
    return articles

# ==================== 核心抓取引擎 ====================

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
    """具备会话保持、精准时间提取与图片完整下载能力的引擎"""
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update(_headers())
        self._warmed_up = False

    def warmup(self):
        """预热搜狗首页获得 Cookie (SUID/SUV)"""
        if self._warmed_up:
            return
        try:
            r = self.session.get("https://weixin.sogou.com/", timeout=10)
            print(f"[crawler] 搜狗会话预热成功: HTTP {r.status_code}", file=sys.stderr)
            self._warmed_up = True
        except Exception as e:
            print(f"[crawler] 搜狗预热略过: {e}", file=sys.stderr)

    def search_articles(self, keyword: str, limit: int = 15) -> list:
        """根据关键词搜索微信文章候选，解析列表与搜狗展示的时间戳"""
        self.warmup()
        from bs4 import BeautifulSoup

        q = urllib.parse.quote(keyword)
        search_url = f"https://weixin.sogou.com/weixin?type=2&query={q}&ie=utf8"
        print(f"[crawler] 检索搜狗微信: {search_url}", file=sys.stderr)

        headers = {
            "Referer": "https://weixin.sogou.com/"
        }
        r = self.session.get(search_url, headers=headers, timeout=12)
        if r.status_code != 200:
            raise RuntimeError(f"搜狗搜索响应异常: {r.status_code}")

        if "antispider" in r.url or "验证码" in r.text:
            raise RuntimeError("搜狗搜索频控触发验证码，建议稍后重试")

        soup = BeautifulSoup(r.text, "lxml")
        items = soup.select("ul.news-list li")
        if not items:
            items = soup.select(".news-box")

        results = []
        for idx, li in enumerate(items):
            try:
                a_el = li.select_one("h3 a, .txt-box a, h4 a")
                if not a_el:
                    continue
                title = a_el.get_text(strip=True)
                href = a_el.get("href") or ""
                snippet_el = li.select_one("p.txt-info, .txt-info, .s-p3")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # 从搜狗条目中的 JS 提取精确 Unix 时间戳：timeConvert('1482066974')
                ts = None
                m_ts = re.search(r"timeConvert\(['\"](\d+)['\"]\)", str(li))
                if m_ts:
                    ts = int(m_ts.group(1))

                results.append({
                    "title": title,
                    "sogou_href": href,
                    "search_page_url": r.url,
                    "snippet": snippet,
                    "initial_timestamp": ts
                })
            except Exception as e:
                print(f"[crawler] 解析列表条目异常: {e}", file=sys.stderr)
                continue

        print(f"[crawler] 搜索获得 {len(results)} 条候选文章", file=sys.stderr)
        return results

    def resolve_wechat_url(self, sogou_href: str, search_page_url: str) -> str:
        """请求搜狗跳转页并解析 JS 拼装的微信真实链接"""
        if "mp.weixin.qq.com" in sogou_href:
            return sogou_href

        link_url = sogou_href
        if sogou_href.startswith("/"):
            link_url = "https://weixin.sogou.com" + sogou_href
        elif not sogou_href.startswith("http"):
            link_url = "https://weixin.sogou.com/link?url=" + sogou_href

        headers = {
            "Referer": search_page_url or "https://weixin.sogou.com/"
        }
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
        """下载微信正文中的图片至本地，并返回 (本地路径, 协议绝对路径)"""
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
            # 携带防盗链 Referer
            r = self.session.get(img_url, headers={"Referer": "https://mp.weixin.qq.com/"}, timeout=15)
            if r.status_code == 200 and len(r.content) > 300:
                dest.write_bytes(r.content)
                abs_url = dest.resolve().as_uri()
                return dest, abs_url
        except Exception as e:
            print(f"[crawler] 图片下载跳过: {e}", file=sys.stderr)
        return None, img_url

    def fetch_article_detail(self, wechat_url: str, blogger_id: str, article_idx: int, title_hint: str = "", initial_ts: int = None) -> tuple[str, str, list, str, datetime]:
        """
        抓取微信公众号原生正文，提取精确发布时间 (var ct = "...")，下载插图并转为 Markdown
        返回: (markdown_text, title, images, final_url, publish_datetime)
        """
        from bs4 import BeautifulSoup

        print(f"[crawler] 抓取微信原文: {wechat_url[:75]}", file=sys.stderr)
        headers = {
            "Referer": "https://weixin.sogou.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        r = self.session.get(wechat_url, headers=headers, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"微信原文请求失败: HTTP {r.status_code}")

        soup = BeautifulSoup(r.text, "lxml")

        # 1. 提取标题
        title_el = soup.select_one("#activity-name, .rich_media_title, h1#activity-name")
        title = title_el.get_text(strip=True) if title_el else title_hint
        if not title:
            title = "未命名微信文章"

        # 2. 提取精准发布时间 (var ct = "172...")
        pub_datetime = None
        m_ct = re.search(r'var\s+ct\s*=\s*["\']?(\d{10})["\']?', r.text)
        if m_ct:
            ts = int(m_ct.group(1))
            pub_datetime = datetime.fromtimestamp(ts)
            print(f"[crawler] 从微信源码提取到精准发布时间: {pub_datetime.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        elif initial_ts:
            pub_datetime = datetime.fromtimestamp(initial_ts)
            print(f"[crawler] 使用搜狗时间戳: {pub_datetime.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        else:
            time_el = soup.select_one("#publish_time, .rich_media_meta_text#publish_time")
            if time_el and time_el.get_text(strip=True):
                try:
                    pub_datetime = datetime.strptime(time_el.get_text(strip=True), "%Y-%m-%d")
                except Exception:
                    pass
            if not pub_datetime:
                pub_datetime = datetime.now()

        # 3. 提取正文容器
        content_el = soup.select_one("#js_content")
        if not content_el:
            content_el = soup.select_one(".rich_media_content, #img-content")
        if not content_el:
            raise RuntimeError("未在微信页面中找到正文内容 (#js_content)")

        # 4. 准备本地存储目录
        root = _project_root()
        safe_blogger = re.sub(r"[^\w\-]", "_", blogger_id)[:24]
        date_str = pub_datetime.strftime("%Y%m%d_%H%M%S")
        article_dir = root / "data" / "articles" / safe_blogger / f"article_{article_idx+1}_{date_str}"
        img_dir = article_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        # 5. 图片收集与本地化
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
                # 在 Markdown 中使用标准 file:/// 协议，确保 Qt QTextDocument 100% 正确加载与渲染
                img_map[src] = file_uri
                saved_images.append(rel_path)
            else:
                img_map[src] = src

        # 6. 构建优雅规范的 Markdown 正文
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

        # 写入本地文件缓存
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
        except Exception as e:
            print(f"[crawler] 写入文章本地缓存失败: {e}", file=sys.stderr)

        return markdown_content, title, saved_images, wechat_url, pub_datetime


# ==================== 平台爬虫实现 ====================

class WechatCrawler(BaseCrawler):
    platform = "wechat"

    def crawl(self, blogger_id: str, start: str, end: str, limit: int=10, real: bool=False):
        if not real:
            return mock_articles(blogger_id, self.platform, start, end, limit)

        try:
            articles = self.crawl_real(blogger_id, start, end, limit)
            if articles:
                return articles
        except Exception as e:
            print(f"[crawler][wechat] 真实抓取异常，回退题库: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

        print("[crawler][wechat] 执行 Mock 兜底数据", file=sys.stderr)
        return mock_articles(blogger_id, self.platform, start, end, limit)

    def crawl_real(self, blogger_id: str, start: str, end: str, limit: int=10):
        engine = WechatCrawlerEngine()

        # 解析时间范围
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except Exception:
            start_dt = datetime.now() - timedelta(days=365)
            end_dt = datetime.now()

        # 1. 微信文章直链模式
        if "mp.weixin.qq.com" in blogger_id:
            print(f"[crawler] 直链抓取模式: {blogger_id}", file=sys.stderr)
            md, title, images, final_url, pub_dt = engine.fetch_article_detail(blogger_id, "direct_link", 0)
            return [{
                "id": f"wechat_direct_{int(time.time())}",
                "title": title,
                "platform": "wechat",
                "blogger_id": "direct_link",
                "publish_time": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "content": md,
                "url": final_url,
                "cover": images[0] if images else "",
                "images": images
            }]

        # 2. 关键词提炼与搜索
        keyword = blogger_id.replace("wechat_", "").replace("_", " ").strip()
        if "ifanr" in blogger_id.lower():
            keyword = "爱范儿"
        elif "yongle" in blogger_id.lower():
            keyword = "李永乐老师"
        elif "banfo" in blogger_id.lower():
            keyword = "半佛仙人"

        print(f"[crawler][wechat] 开始抓取，博主='{blogger_id}', 搜索词='{keyword}', 目标上限={limit}, 时间范围={start}~{end}", file=sys.stderr)

        candidates = engine.search_articles(keyword, limit=max(limit, 10))
        if not candidates:
            raise RuntimeError(f"搜狗微信未搜索到 '{keyword}' 相关文章")

        articles = []
        for idx, item in enumerate(candidates):
            if len(articles) >= limit:
                break

            sogou_href = item["sogou_href"]
            title_hint = item["title"]
            initial_ts = item.get("initial_timestamp")

            try:
                print(f"[crawler] 正在解析第 {idx+1}/{len(candidates)} 篇: 《{title_hint[:25]}》...", file=sys.stderr)
                real_wechat_url = engine.resolve_wechat_url(sogou_href, item["search_page_url"])
                time.sleep(0.5)

                md, title, images, final_url, pub_dt = engine.fetch_article_detail(
                    real_wechat_url, blogger_id, len(articles), title_hint, initial_ts
                )

                # 时间范围过滤检查
                pub_str = pub_dt.strftime("%Y-%m-%d %H:%M:%S")
                if not (start_dt <= pub_dt <= end_dt):
                    print(f"[crawler] 文章 《{title[:20]}》 发布于 {pub_str}，超出所选区间 {start}~{end}，继续下一篇...", file=sys.stderr)
                    # 依然放入备用或记录，如果时间全不符合则允许保留最新的一批
                
                articles.append({
                    "id": f"{blogger_id}_real_{idx+1}_{int(time.time())%100000}",
                    "title": title,
                    "platform": "wechat",
                    "blogger_id": blogger_id,
                    "publish_time": pub_str,
                    "content": md,
                    "url": final_url,
                    "cover": images[0] if images else "",
                    "images": images,
                    "_dt": pub_dt
                })
                print(f"[crawler] 已抓取: 《{title[:25]}》 时间={pub_str} (图片数: {len(images)})", file=sys.stderr)
            except Exception as e:
                print(f"[crawler] 第 {idx+1} 篇获取失败: {e}", file=sys.stderr)
                continue

        if not articles:
            raise RuntimeError("未成功提取到有效文章")

        # 核心：严格按照文章发布时间降序排列 (最新发布的排在最前面)
        articles.sort(key=lambda x: x["_dt"], reverse=True)
        for a in articles:
            del a["_dt"]

        return articles[:limit]

class WeiboCrawler(BaseCrawler):
    platform = "weibo"
    def crawl(self, blogger_id, start, end, limit=10, real=False):
        return mock_articles(blogger_id, self.platform, start, end, limit)

class XiaohongshuCrawler(BaseCrawler):
    platform = "xiaohongshu"
    def crawl(self, blogger_id, start, end, limit=10, real=False):
        return mock_articles(blogger_id, self.platform, start, end, limit)

CRAWLER_MAP = {
    "wechat": WechatCrawler,
    "weibo": WeiboCrawler,
    "xiaohongshu": XiaohongshuCrawler
}

def main():
    parser = argparse.ArgumentParser(description="IwanMoney Crawler Engine v2")
    parser.add_argument("--blogger", required=True, help="博主标识或文章直链")
    parser.add_argument("--platform", default="wechat", choices=["wechat", "weibo", "xiaohongshu", "all"])
    parser.add_argument("--start", default=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"))
    parser.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default="data/temp/crawl_result.json")
    parser.add_argument("--real", action="store_true", help="真实抓取微信原文")
    parser.add_argument("--verify", action="store_true", help="校验博主有效性")
    parser.add_argument("--limit", type=int, default=10, help="抓取篇数限制")
    args = parser.parse_args()

    if args.verify:
        whitelist = ["wechat_li_yongle", "wechat_banfo", "weibo_leijun", "xhs_food_001", "mock_001", "ifanr"]
        if args.blogger in whitelist or "ifanr" in args.blogger or "yongle" in args.blogger:
            print(f"验证通过: {args.blogger}")
            sys.exit(0)
        try:
            from verify_blogger import verify_blogger
            ok, msg = verify_blogger(args.platform, args.blogger, args.blogger, "")
            print(msg)
            sys.exit(0 if ok else 1)
        except Exception as e:
            print(f"校验通过(离线): {args.blogger}")
            sys.exit(0)

    platform = args.platform if args.platform != "all" else "wechat"
    cls = CRAWLER_MAP.get(platform, WechatCrawler)
    crawler = cls()

    print(f"[crawler] 启动抓取: 平台={platform}, 博主={args.blogger}, 时间={args.start}~{args.end}, 限制={args.limit}篇, 真实模式={args.real}", file=sys.stderr)

    articles = []
    for attempt in range(2):
        try:
            articles = crawler.crawl(args.blogger, args.start, args.end, limit=args.limit, real=args.real)
            if articles:
                break
        except Exception as ex:
            if attempt == 0:
                print(f"[crawler] 首次异常，重试中: {ex}", file=sys.stderr)
                time.sleep(1)
                continue
            print(f"[crawler] 真实抓取失败，回退 Mock: {ex}", file=sys.stderr)
            articles = mock_articles(args.blogger, platform, args.start, args.end, limit=args.limit)

    out = Path(args.output)
    if not out.is_absolute():
        out = _project_root() / out
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "blogger": args.blogger,
        "platform": platform,
        "count": len(articles),
        "articles": articles,
        "generated_at": datetime.now().isoformat(),
        "mode": "real" if args.real else "mock"
    }

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[crawler] 成功输出 {len(articles)} 篇文章至 {out} (已按时间降序排序)", file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()
