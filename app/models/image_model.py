"""
Image Model
SQLAlchemy model for image data and face embeddings
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Text, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.engine import Base


class Image(Base):
    """Image database model"""
    
    __tablename__ = "images"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        index=True
    )
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # File information
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    processed_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # File metadata
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Face detection results
    face_count: Mapped[int] = mapped_column(Integer, default=0)
    primary_face_bbox: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    detection_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Vector index reference
    vector_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Status
    is_processed: Mapped[bool] = mapped_column(default=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Tags and metadata (JSON)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="images")
    
    def __repr__(self) -> str:
        return f"<Image(id={self.id}, user_id={self.user_id}, filename={self.original_filename})>"


class EmbeddingCache(Base):
    """
    Embedding cache for fast lookup
    Stores embeddings alongside FAISS index for metadata retrieval
    """
    
    __tablename__ = "embedding_cache"
    
    # Primary key - matches FAISS vector ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True
    )
    
    # Foreign key to image
    image_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("images.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign key to user (denormalized for fast filtering)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Embedding data (stored as binary for efficiency)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    
    # Face position in image (for multi-face images)
    face_index: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<EmbeddingCache(id={self.id}, image_id={self.image_id})>"
