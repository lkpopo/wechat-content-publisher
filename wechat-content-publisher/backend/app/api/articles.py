import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import ArticleOut, ArticleCreate, ArticleListOut, ArticleUpdate
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
