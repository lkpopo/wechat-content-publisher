import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ArticleOut
from app.services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/edit/{article_id}", response_model=ArticleOut)
async def ai_edit(article_id: str, db: Session = Depends(get_db)):
    logger.info(f"AI edit requested for article {article_id}")
    try:
        article = await ai_service.ai_edit_article(db, article_id)
        return article
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"AI edit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
