import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
import re
from app.schemas import (
    ArticleOut,
    ArticleCreate,
    ArticleListOut,
    ArticleUpdate,
    BatchCrawlRequest,
    BatchCrawlResponse,
    BatchCrawlItemResult,
)
from app.services import article_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("/fetch", response_model=ArticleOut)
async def fetch_article(request: ArticleCreate, db: Session = Depends(get_db)):
    try:
        article = article_service.create_article_from_url(db, str(request.url))
        article = await article_service.fetch_and_parse(db, article.id)
        return article
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl/batch", response_model=BatchCrawlResponse)
async def batch_crawl_articles(request: BatchCrawlRequest, db: Session = Depends(get_db)):
    """Batch crawl multiple URLs, cleaning empty lines, spaces, duplicates, and handling errors per URL."""
    cleaned_urls = []
    seen = set()
    for raw_url in request.urls:
        u = raw_url.strip()
        if not u:
            continue
        if u not in seen:
            seen.add(u)
            cleaned_urls.append(u)

    results: List[BatchCrawlItemResult] = []
    success_count = 0
    failed_count = 0

    url_regex = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

    for url in cleaned_urls:
        if not url_regex.match(url):
            results.append(
                BatchCrawlItemResult(
                    url=url,
                    status="failed",
                    error="URL 格式不合法，必须以 http:// 或 https:// 开头",
                )
            )
            failed_count += 1
            continue

        try:
            article = article_service.create_article_from_url(db, url)
            article = await article_service.fetch_and_parse(db, article.id)
            if article.fetch_status == "completed":
                success_count += 1
                results.append(
                    BatchCrawlItemResult(
                        url=url,
                        status="success",
                        article_id=article.id,
                        title=article.current_title or article.source_title or "抓取成功",
                    )
                )
            else:
                failed_count += 1
                results.append(
                    BatchCrawlItemResult(
                        url=url,
                        status="failed",
                        article_id=article.id,
                        error="文章解析失败，可能已被删除或包含非支持的格式",
                    )
                )
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to crawl URL in batch: {url}, error: {e}")
            results.append(
                BatchCrawlItemResult(
                    url=url,
                    status="failed",
                    error=str(e),
                )
            )

    return BatchCrawlResponse(
        total=len(cleaned_urls),
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )



@router.get("", response_model=ArticleListOut)
def list_articles(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    total, items = article_service.list_articles(db, skip=skip, limit=limit)
    return {"total": total, "items": items}


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: str, db: Session = Depends(get_db)):
    article = article_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.put("/{article_id}", response_model=ArticleOut)
def update_article(article_id: str, update: ArticleUpdate, db: Session = Depends(get_db)):
    try:
        article = article_service.update_article_content(db, article_id, update.current_title, update.current_content)
        return article
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{article_id}")
def delete_article(article_id: str, db: Session = Depends(get_db)):
    success = article_service.delete_article(db, article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"success": True}
