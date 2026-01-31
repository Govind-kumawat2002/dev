"""
Face Scan Routes
Handles face scanning and matching
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.engine import get_db
from app.core.pipeline import FaceNotFoundException, MultipleFacesException
from app.models import User, Session
from app.services import get_inference_service
from app.config import settings
from app.utils.security import (
    get_current_user,
    get_optional_user,
    create_access_token,
    TokenData
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scan", tags=["Face Scan"])


# ==============================
# Request/Response Models
# ==============================

class ScanResponse(BaseModel):
    """Face scan response"""
    success: bool
    message: str
    faces_detected: int = 0
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    match_count: int = 0


class ScanMatchResult(BaseModel):
    """Single match result"""
    image_id: str
    similarity: float
    rank: int
    filename: Optional[str] = None
    file_path: Optional[str] = None


class ScanMatchResponse(BaseModel):
    """Face match response"""
    success: bool
    message: str
    matches: list[ScanMatchResult]
    total_matches: int


# ==============================
# Routes
# ==============================

@router.post("/face", response_model=ScanResponse)
async def scan_face(
    file: UploadFile = File(..., description="Face image to scan"),
    session_id: Optional[str] = Form(None, description="QR session ID"),
    db: AsyncSession = Depends(get_db),
    token_data: Optional[TokenData] = Depends(get_optional_user)
):
    """
    Scan a face and optionally link to session
    
    This endpoint:
    1. Detects face in uploaded image
    2. Generates embedding
    3. Searches for existing matches
    4. If session provided, links user to session
    """
    inference_service = get_inference_service()
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Check file size
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )
    
    try:
        # Find similar faces
        matches = await inference_service.find_similar_faces(
            image_bytes=contents,
            k=settings.top_k_results,
            threshold=settings.similarity_threshold
        )
        
        user_id = None
        access_token = None
        
        # If matches found, get the most likely user
        if matches:
            # Get the user with highest confidence match
            top_match = matches[0]
            user_id = top_match.get("user_id")
            
            # If session provided, link user to session
            if session_id and user_id:
                stmt = select(Session).where(Session.id == session_id, Session.is_active == True)
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                
                if session:
                    session.user_id = user_id
                    access_token = create_access_token(user_id, session_id)
                    session.token = access_token
                    await db.flush()
                    
                    logger.info(
                        "session_linked_to_user",
                        session_id=session_id,
                        user_id=user_id
                    )
        
        logger.info(
            "face_scanned",
            matches=len(matches),
            user_found=user_id is not None
        )
        
        return ScanResponse(
            success=True,
            message="Face scanned successfully",
            faces_detected=1,
            user_id=user_id,
            access_token=access_token,
            match_count=len(matches)
        )
        
    except FaceNotFoundException:
        logger.warning("no_face_in_scan")
        return ScanResponse(
            success=False,
            message="No face detected in image",
            faces_detected=0
        )
    except MultipleFacesException:
        logger.warning("multiple_faces_in_scan")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected. Please scan one face at a time."
        )


@router.post("/match", response_model=ScanMatchResponse)
async def find_matches(
    file: UploadFile = File(..., description="Face image to match"),
    limit: int = 10,
    threshold: float = 0.75,
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Find all matching images for the scanned face
    
    Only returns images belonging to the authenticated user
    """
    inference_service = get_inference_service()
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    contents = await file.read()
    
    try:
        # Find matches filtered by user
        results = await inference_service.find_user_images(
            db=db,
            image_bytes=contents,
            threshold=threshold
        )
        
        # Filter to only show user's own images
        user_results = [r for r in results if r.get("user_id") == token_data.user_id][:limit]
        
        matches = [
            ScanMatchResult(
                image_id=r["image_id"],
                similarity=r["similarity"],
                rank=i + 1,
                filename=r.get("filename"),
                file_path=r.get("file_path")
            )
            for i, r in enumerate(user_results)
        ]
        
        logger.info(
            "matches_found",
            user_id=token_data.user_id,
            total=len(matches)
        )
        
        return ScanMatchResponse(
            success=True,
            message="Matches found" if matches else "No matches found",
            matches=matches,
            total_matches=len(matches)
        )
        
    except FaceNotFoundException:
        return ScanMatchResponse(
            success=False,
            message="No face detected in image",
            matches=[],
            total_matches=0
        )


@router.post("/upload")
async def upload_face_image(
    file: UploadFile = File(..., description="Face image to upload"),
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Upload and index a new face image
    
    The image will be:
    1. Processed for face detection
    2. Embedding generated
    3. Stored in database and vector index
    """
    inference_service = get_inference_service()
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    contents = await file.read()
    
    # Check file size
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )
    
    try:
        image, vector_id = await inference_service.process_and_store_image(
            db=db,
            image_bytes=contents,
            user_id=token_data.user_id,
            filename=file.filename or "uploaded_image.jpg",
            file_size=len(contents),
            mime_type=file.content_type or "image/jpeg"
        )
        
        logger.info(
            "image_uploaded",
            image_id=image.id,
            user_id=token_data.user_id,
            vector_id=vector_id
        )
        
        return {
            "success": True,
            "message": "Image uploaded and indexed",
            "image_id": image.id,
            "vector_id": vector_id
        }
        
    except FaceNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in image"
        )


@router.get("/stats")
async def get_scan_stats(
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user)
):
    """
    Get scanning statistics for the current user
    """
    inference_service = get_inference_service()
    
    # Get user's image count
    image_count = await inference_service.get_user_images_count(db, token_data.user_id)
    
    # Get index stats
    index_stats = inference_service.get_index_stats()
    
    return {
        "user_images": image_count,
        "total_indexed": index_stats["total_vectors"],
        "embedding_dimension": index_stats["embedding_dim"]
    }
