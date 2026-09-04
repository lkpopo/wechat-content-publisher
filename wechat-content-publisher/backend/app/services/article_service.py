import asyncio
import aiofiles
import logging
import shutil
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Article, ArticleImage, PublishRecord
from app.clients.wechat import fetch_html, parse_article
from app.clients.wechat.image_downloader import get_ext_from_url
from app.config import settings
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _article_dir(article_id: str) -> Path:
    return Path(settings.data_dir) / "articles" / article_id


def create_article_from_url(db: Session, url: str) -> Article:
    article_id = str(uuid.uuid4())

    article = Article(
        id=article_id,
        source_url=url,
        fetch_status="pending",
        ai_edit_status="idle",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    return article


async def fetch_and_parse(db: Session, article_id: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise ValueError(f"Article not found: {article_id}")

    article.fetch_status = "processing"
    article.updated_at = _now()
    db.commit()

    try:
        html = await fetch_html(article.source_url)
        parsed = parse_article(html, article.source_url)

        article.source_title = parsed["source_title"]
        article.source_account = parsed["source_account"]
        article.author = parsed["author"]
        article.publish_time = parsed["publish_time"]
        article.original_html = parsed["original_html"]
        article.clean_html = parsed["clean_html"]
        article.content_text = parsed["content_text"]

        article.current_title = parsed["source_title"]
        article.current_content = parsed["content_text"]

        image_dir = _article_dir(article_id)
        downloaded = await _download_images(parsed["images"], image_dir)

        for img_data in downloaded:
            image = ArticleImage(
                id=str(uuid.uuid4()),
                article_id=article_id,
                image_index=img_data["index"],
                original_url=img_data["original_url"],
                local_path=img_data.get("local_path"),
                created_at=_now(),
            )
            db.add(image)

        article.fetch_status = "completed"
        article.updated_at = _now()
        db.commit()

    except Exception as e:
        article.fetch_status = "failed"
        article.updated_at = _now()
        db.commit()

    db.refresh(article)
    return article


async def _download_images(images: List[dict], save_dir: Path) -> List[dict]:
    if not images:
        return []

    save_dir.mkdir(parents=True, exist_ok=True)
    results = []

    async with __import__("httpx").AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com/",
        },
        follow_redirects=True,
        timeout=60.0,
    ) as client:
        tasks = [_download_one(client, img, save_dir) for img in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    downloaded = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            downloaded.append({
                "index": images[i]["index"],
                "original_url": images[i]["original_url"],
                "local_path": None,
                "error": str(result),
            })
        else:
            downloaded.append(result)

    return downloaded


async def _download_one(client, img: dict, save_dir: Path) -> dict:
    idx = img["index"]
    url = img["original_url"]
    ext = get_ext_from_url(url)
    filename = f"image_{idx:03d}{ext}"
    local_path = save_dir / filename

    resp = await client.get(url)
    resp.raise_for_status()
    async with aiofiles.open(local_path, "wb") as f:
        await f.write(resp.content)

    return {
        "index": idx,
        "original_url": url,
        "local_path": str(local_path),
    }


def get_article(db: Session, article_id: str) -> Optional[Article]:
    return db.query(Article).filter(Article.id == article_id).first()


def list_articles(db: Session, skip: int = 0, limit: int = 20) -> tuple:
    total = db.query(Article).count()
    items = (
        db.query(Article)
        .order_by(Article.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return total, items


def delete_article(db: Session, article_id: str) -> bool:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return False

    # 1. 同步物理删除本地磁盘目录及其所有图片与静态文件
    art_dir = _article_dir(article_id)
    if art_dir.exists() and art_dir.is_dir():
        try:
            shutil.rmtree(art_dir, ignore_errors=True)
            logger.info(f"[Article] Successfully deleted article directory from disk: {art_dir}")
        except Exception as e:
            logger.warning(f"[Article] Failed to remove article directory {art_dir}: {e}")

    # 2. 级联删除关联的图片和发布记录
    db.query(ArticleImage).filter(ArticleImage.article_id == article_id).delete()
    db.query(PublishRecord).filter(PublishRecord.article_id == article_id).delete()

    db.delete(article)
    db.commit()
    return True


def update_article_content(db: Session, article_id: str, title: str = None, content: str = None) -> Optional[Article]:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return None

    if title is not None:
        title = title.strip()
        if len(title) > 30:
            title = title[:30].rstrip("，。！？、：；—-_ ")
        article.current_title = title
    if content is not None:
        article.current_content = content
    article.updated_at = _now()
    db.commit()
    db.refresh(article)
    return article
