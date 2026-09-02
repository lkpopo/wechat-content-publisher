from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(String(36), primary_key=True)
    source_url = Column(String(2048), nullable=False, unique=True)
    source_title = Column(String(512))
    source_account = Column(String(256))
    author = Column(String(256))
    publish_time = Column(String(64))
    cover_path = Column(String(1024))
    original_html = Column(Text)
    clean_html = Column(Text)
    content_text = Column(Text)

    current_title = Column(String(512))
    current_content = Column(Text)

    fetch_status = Column(String(32), nullable=False, default="pending")
    ai_edit_status = Column(String(32), nullable=False, default="idle")
    ai_edit_error = Column(Text)
    ai_edit_started_at = Column(String(64))
    ai_edit_finished_at = Column(String(64))

    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)

    images = relationship("ArticleImage", back_populates="article", cascade="all, delete-orphan")
    publish_records = relationship("PublishRecord", back_populates="article", cascade="all, delete-orphan")


class ArticleImage(Base):
    __tablename__ = "article_images"

    id = Column(String(36), primary_key=True)
    article_id = Column(String(36), ForeignKey("articles.id"), nullable=False)
    image_index = Column(Integer, nullable=False)
    original_url = Column(String(2048))
    local_path = Column(String(1024))
    created_at = Column(String(64), nullable=False)

    article = relationship("Article", back_populates="images")


class PublishRecord(Base):
    __tablename__ = "publish_records"

    id = Column(String(36), primary_key=True)
    article_id = Column(String(36), ForeignKey("articles.id"), nullable=False)
    platform = Column(String(32), nullable=False, default="toutiao")
    title = Column(String(512))
    content_snapshot = Column(Text)
    status = Column(String(32), nullable=False, default="pending")
    error_message = Column(Text)
    published_at = Column(String(64))
    created_at = Column(String(64), nullable=False)

    article = relationship("Article", back_populates="publish_records")
