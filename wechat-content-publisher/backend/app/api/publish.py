import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import PublishResponse
from app.services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/publish", tags=["publish"])


@router.post("/{article_id}", response_model=PublishResponse)
def publish_article(article_id: str, db: Session = Depends(get_db)):
    logger.info(f"Publish requested for article {article_id}")

    from app.models import Article

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not article.current_content:
        raise HTTPException(status_code=400, detail="No content to publish")

    title = article.current_title or article.source_title or "无标题"
    content = article.current_content

    try:
        from app.services.publish_service import publish_to_toutiao
        result = publish_to_toutiao(article, title, content)

        ai_service.record_publish(
            db, article_id, "toutiao",
            title=title, content=content,
            success=True
        )

        logger.info(f"Article {article_id} published successfully")
        return {"success": True, "message": result.get("message", "发布成功")}
    except Exception as e:
        logger.error(f"Publish failed: {e}", exc_info=True)
        ai_service.record_publish(
            db, article_id, "toutiao",
            title=title, content=content,
            success=False, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
