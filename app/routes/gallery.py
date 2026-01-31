"""
Gallery Routes
Handles image gallery and retrieval
"""

import os
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.engine import get_db
from app.models import Image
from app.services import get_inference_service
from app.utils.security import get_current_user, TokenData
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/gallery", tags=["Gallery"])


# ==============================
# Response Models
# ==============================

class ImageInfo(BaseModel):
    """Image information model"""
    id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    face_count: int = 0
    is_processed: bool = False
    created_at: str
    similarity: Optional[float] = None


class GalleryResponse(BaseModel):
    """Gallery listing response"""
    images: List[ImageInfo]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class ImageDetailResponse(BaseModel):
    """Detailed image information"""
    id: str
    filename: str
    file_url: str
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    face_count: int
    detection_score: Optional[float] = None
    is_processed: bool
    created_at: str
    processed_at: Optional[str] = None


# ==============================
# Routes
# ==============================

@router.get("", response_model=GalleryResponse)
async def get_gallery(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Get paginated gallery of user's images
    """
    offset = (page - 1) * per_page
    
    # Get total count
    count_stmt = select(func.count()).select_from(Image).where(
        Image.user_id == token_data.user_id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Get images
    stmt = select(Image).where(
        Image.user_id == token_data.user_id
    ).order_by(Image.created_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(stmt)
    images = result.scalars().all()
    
    items = [
        ImageInfo(
            id=img.id,
            filename=img.original_filename,
            file_path=img.file_path,
            file_size=img.file_size,
            mime_type=img.mime_type,
            width=img.width,
            height=img.height,
            face_count=img.face_count,
            is_processed=img.is_processed,
            created_at=img.created_at.isoformat()
        )
        for img in images
    ]
    
    logger.debug(
        "gallery_fetched",
        user_id=token_data.user_id,
        page=page,
        count=len(items)
    )
    
    return GalleryResponse(
        images=items,
        total=total,
        page=page,
        per_page=per_page,
        has_next=(page * per_page) < total,
        has_prev=page > 1
    )


@router.get("/search", response_model=GalleryResponse)
async def search_gallery(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Search user's images by filename
    """
    offset = (page - 1) * per_page
    
    # Case-insensitive filename search
    search_pattern = f"%{query}%"
    
    count_stmt = select(func.count()).select_from(Image).where(
        Image.user_id == token_data.user_id,
        Image.original_filename.ilike(search_pattern)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    stmt = select(Image).where(
        Image.user_id == token_data.user_id,
        Image.original_filename.ilike(search_pattern)
    ).order_by(Image.created_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(stmt)
    images = result.scalars().all()
    
    items = [
        ImageInfo(
            id=img.id,
            filename=img.original_filename,
            file_path=img.file_path,
            file_size=img.file_size,
            mime_type=img.mime_type,
            face_count=img.face_count,
            is_processed=img.is_processed,
            created_at=img.created_at.isoformat()
        )
        for img in images
    ]
    
    return GalleryResponse(
        images=items,
        total=total,
        page=page,
        per_page=per_page,
        has_next=(page * per_page) < total,
        has_prev=page > 1
    )


@router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_detail(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Get detailed information about a specific image
    """
    stmt = select(Image).where(
        Image.id == image_id,
        Image.user_id == token_data.user_id
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return ImageDetailResponse(
        id=image.id,
        filename=image.original_filename,
        file_url=f"/api/v1/gallery/{image.id}/file",
        file_size=image.file_size,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        face_count=image.face_count,
        detection_score=image.detection_score,
        is_processed=image.is_processed,
        created_at=image.created_at.isoformat(),
        processed_at=image.processed_at.isoformat() if image.processed_at else None
    )


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Get the actual image file
    """
    stmt = select(Image).where(
        Image.id == image_id,
        Image.user_id == token_data.user_id
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    if not os.path.exists(image.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found on disk"
        )
    
    return FileResponse(
        path=image.file_path,
        media_type=image.mime_type,
        filename=image.original_filename
    )


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Delete an image from the gallery
    """
    stmt = select(Image).where(
        Image.id == image_id,
        Image.user_id == token_data.user_id
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Delete file if exists
    if os.path.exists(image.file_path):
        os.remove(image.file_path)
    
    # Delete from database
    await db.delete(image)
    await db.flush()
    
    logger.info("image_deleted", image_id=image_id, user_id=token_data.user_id)
    
    return {"success": True, "message": "Image deleted"}


@router.delete("")
async def delete_all_images(
    confirm: bool = Query(False, description="Confirm deletion of all images"),
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Delete all images for the current user
    
    Requires confirmation flag
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please confirm deletion by passing confirm=true"
        )
    
    inference_service = get_inference_service()
    
    deleted = await inference_service.delete_user_images(db, token_data.user_id)
    
    logger.info(
        "all_images_deleted",
        user_id=token_data.user_id,
        count=deleted
    )
    
    return {
        "success": True,
        "message": f"Deleted {deleted} images",
        "deleted_count": deleted
    }
