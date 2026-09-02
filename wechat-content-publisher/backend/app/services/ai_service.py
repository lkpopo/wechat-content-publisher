import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import Article, PublishRecord
from app.clients.ai import generate_draft
from app.config import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def ai_edit_article(db: Session, article_id: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise ValueError(f"Article not found: {article_id}")

    if article.ai_edit_status == "processing":
        raise ValueError("AI edit already in progress")

    if article.fetch_status != "completed":
        raise ValueError(f"Article not ready, fetch_status={article.fetch_status}")

    logger.info(f"[AI] Starting AI edit for article {article_id}")

    article.ai_edit_status = "processing"
    article.ai_edit_error = None
    article.ai_edit_started_at = _now()
    article.ai_edit_finished_at = None
    db.commit()

    try:
        input_content = article.current_content or article.content_text or ""
        logger.info(f"[AI] Input length: {len(input_content)} chars")

        result = await generate_draft(input_content)

        blocks = result.get("blocks", [])
        _validate_blocks(blocks, article_id)

        generated_title = (result.get("title") or "").strip()
        if len(generated_title) > 30:
            logger.warning(
                f"[AI] Generated title exceeded 30 characters ({len(generated_title)} chars): '{generated_title}', safely truncating..."
            )
            # Safe truncation: take first 30 chars and strip trailing punctuation/whitespace
            generated_title = generated_title[:30].rstrip("，。！？、：；—-_ ")

        article.current_title = generated_title
        article.current_content = json_dumps_blocks(blocks)
        article.ai_edit_status = "completed"
        article.ai_edit_finished_at = _now()

        logger.info(f"[AI] Completed: title='{article.current_title}' (len={len(article.current_title)}), blocks={len(blocks)}")

    except Exception as e:
        logger.error(f"[AI] Failed: {e}", exc_info=True)
        article.ai_edit_status = "failed"
        article.ai_edit_error = str(e)
        article.ai_edit_finished_at = _now()

    article.updated_at = _now()
    db.commit()
    db.refresh(article)
    return article


def _validate_blocks(blocks: list, article_id: str):
    if not isinstance(blocks, list):
        raise ValueError("AI response 'blocks' must be a list")

    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ValueError(f"Block {i} must be an object")
        if "type" not in block:
            raise ValueError(f"Block {i} missing 'type'")
        if block["type"] not in ("paragraph", "heading", "image"):
            raise ValueError(f"Block {i} invalid type: {block['type']}")
        if block["type"] == "image":
            image_id = block.get("image_id", "")
            if not image_id.startswith("image_"):
                raise ValueError(f"Block {i} invalid image_id: {image_id}")


def json_dumps_blocks(blocks: list) -> str:
    import json
    lines = []
    for block in blocks:
        if block["type"] == "image":
            lines.append(f"[{block['image_id']}]")
        else:
            lines.append(block.get("text", ""))
    return "\n\n".join(lines)


def save_article_content(db: Session, article_id: str, title: str, content: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise ValueError(f"Article not found: {article_id}")

    if title and len(title) > 30:
        logger.warning(f"[Save] Title exceeded 30 chars ({len(title)} chars), trimming to 30 chars: '{title}'")
        title = title[:30].rstrip("，。！？、：；—-_ ")

    article.current_title = title
    article.current_content = content
    article.updated_at = _now()
    db.commit()
    db.refresh(article)
    logger.info(f"[Save] Article {article_id} saved, title='{title}'")
    return article


def record_publish(db: Session, article_id: str, platform: str, title: str, content: str, success: bool, error: str = None) -> PublishRecord:
    record = PublishRecord(
        id=str(__import__("uuid").uuid4()),
        article_id=article_id,
        platform=platform,
        title=title,
        content_snapshot=content,
        status="success" if success else "failed",
        error_message=error,
        published_at=_now() if success else None,
        created_at=_now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(f"[Publish] Record created: {record.id}, success={success}")
    return record
