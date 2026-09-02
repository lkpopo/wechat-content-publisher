from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from pathlib import Path
import aiofiles

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{article_id}/{image_name}")
async def get_image(article_id: str, image_name: str):
    image_path = Path(settings.data_dir) / "articles" / article_id / image_name

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    from fastapi.responses import FileResponse
    return FileResponse(str(image_path))
