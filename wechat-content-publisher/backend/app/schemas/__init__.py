from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List


class ArticleImageOut(BaseModel):
    id: str
    image_index: int
    original_url: Optional[str] = None
    local_path: Optional[str] = None

    class Config:
        from_attributes = True


class PublishRecordOut(BaseModel):
    id: str
    article_id: str
    platform: str
    title: Optional[str] = None
    content_snapshot: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    published_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class ArticleOut(BaseModel):
    id: str
    source_url: str
    source_title: Optional[str] = None
    source_account: Optional[str] = None
    author: Optional[str] = None
    publish_time: Optional[str] = None
    cover_path: Optional[str] = None
    clean_html: Optional[str] = None
    content_text: Optional[str] = None

    current_title: Optional[str] = None
    current_content: Optional[str] = None

    fetch_status: str
    ai_edit_status: str
    ai_edit_error: Optional[str] = None

    created_at: str
    updated_at: str
    images: List[ArticleImageOut] = []
    publish_records: List[PublishRecordOut] = []

    class Config:
        from_attributes = True


class ArticleCreate(BaseModel):
    url: HttpUrl


class ArticleListOut(BaseModel):
    total: int
    items: List[ArticleOut]


class ArticleUpdate(BaseModel):
    current_title: Optional[str] = None
    current_content: Optional[str] = None


class DraftBlock(BaseModel):
    type: str = Field(..., pattern="^(paragraph|heading|image)$")
    text: Optional[str] = None
    image_id: Optional[str] = None


class AIEditRequest(BaseModel):
    pass


class PublishResponse(BaseModel):
    success: bool
    message: str
