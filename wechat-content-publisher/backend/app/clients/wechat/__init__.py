import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text


def get_ext_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(".png"):
        return ".png"
    elif path.endswith(".gif"):
        return ".gif"
    elif path.endswith(".webp"):
        return ".webp"
    return ".jpg"


def parse_article(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.find("h2", class_="rich_media_title")
    title = _clean_text(title_el.get_text()) if title_el else ""

    account_el = soup.find("a", id="js_name")
    account = _clean_text(account_el.get_text()) if account_el else ""

    author_el = soup.find("span", class_="rich_media_meta_text")
    author = _clean_text(author_el.get_text()) if author_el else ""

    time_el = soup.find("em", id="publish_time")
    publish_time = _clean_text(time_el.get_text()) if time_el else ""

    content_el = soup.find("div", id="js_content")

    images: List[Dict] = []
    if content_el:
        for idx, img in enumerate(content_el.find_all("img"), 1):
            img_url = img.get("data-src") or img.get("src") or ""
            if img_url and img_url.startswith("http"):
                images.append({
                    "index": idx,
                    "original_url": img_url,
                })
                placeholder = NavigableString(f"[图{idx}]")
                img.replace_with(placeholder)

    clean_html = str(content_el) if content_el else ""
    content_text = _extract_text(content_el) if content_el else ""

    return {
        "source_url": url,
        "source_title": title,
        "source_account": account,
        "author": author,
        "publish_time": publish_time,
        "original_html": html,
        "clean_html": clean_html,
        "content_text": content_text,
        "images": images,
    }


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_text(el) -> str:
    if el is None:
        return ""

    parts: List[str] = []
    for child in el.descendants:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                parts.append(text.strip())
        elif isinstance(child, Tag):
            if child.name in ("p", "br", "div", "section", "h1", "h2", "h3", "h4"):
                parts.append("\n")

    raw = "".join(parts)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()
