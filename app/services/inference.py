"""
Face Inference Service
High-level API for face detection and matching
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import settings
from app.core.pipeline import FaceNotFoundException, MultipleFacesException
from app.models import Image, EmbeddingCache
from app.services.embeddings import get_embedding_service, EmbeddingService
from app.services.search import get_search_service, VectorSearchService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InferenceService:
    """
    High-level inference service
    Orchestrates embedding generation, storage, and search
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        search_service: Optional[VectorSearchService] = None
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.search_service = search_service or get_search_service()
    
    async def process_and_store_image(
        self,
        db: AsyncSession,
        image_bytes: bytes,
        user_id: str,
        filename: str,
        file_size: int,
        mime_type: str = "image/jpeg"
    ) -> Tuple[Image, int]:
        """
        Process image, extract embedding, and store in database
        
        Args:
            db: Database session
            image_bytes: Raw image data
            user_id: Owner user ID
            filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type
            
        Returns:
            Tuple of (Image record, vector_id)
        """
        # Generate unique ID and paths
        image_id = str(uuid.uuid4())
        safe_filename = f"{image_id}_{filename}"
        file_path = os.path.join(settings.upload_dir, user_id, safe_filename)
        
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save raw image
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        try:
            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(
                image_bytes,
                require_single_face=False
            )
            
            # Add to vector index
            vector_id = self.search_service.add_vector(
                embedding=embedding,
                image_id=image_id,
                user_id=user_id
            )
            
            # Create database record
            image = Image(
                id=image_id,
                user_id=user_id,
                original_filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                face_count=1,
                vector_id=vector_id,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            
            db.add(image)
            
            # Also store embedding in cache
            embedding_cache = EmbeddingCache(
                image_id=image_id,
                user_id=user_id,
                embedding=self.embedding_service.embedding_to_bytes(embedding)
            )
            db.add(embedding_cache)
            
            await db.flush()
            
            # Save index periodically
            if self.search_service.get_vector_count() % 100 == 0:
                self.search_service.save_index()
            
            logger.info(
                "image_processed",
                image_id=image_id,
                user_id=user_id,
                vector_id=vector_id
            )
            
            return image, vector_id
            
        except FaceNotFoundException as e:
            # Still save image but mark as not processed
            image = Image(
                id=image_id,
                user_id=user_id,
                original_filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                face_count=0,
                is_processed=False,
                processing_error="No face detected"
            )
            db.add(image)
            await db.flush()
            
            logger.warning("image_no_face", image_id=image_id)
            raise
    
    async def find_similar_faces(
        self,
        image_bytes: bytes,
        k: int = 10,
        user_id: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find images with similar faces
        
        Args:
            image_bytes: Query image bytes
            k: Number of results
            user_id: Optional filter by user
            threshold: Similarity threshold
            
        Returns:
            List of matching results
        """
        threshold = threshold or settings.similarity_threshold
        
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(
            image_bytes,
            require_single_face=True
        )
        
        # Search
        results = self.search_service.search(
            query_embedding=query_embedding,
            k=k,
            user_id=user_id,
            threshold=threshold
        )
        
        logger.info(
            "similarity_search",
            k=k,
            user_filter=user_id is not None,
            results=len(results)
        )
        
        return results
    
    async def find_user_images(
        self,
        db: AsyncSession,
        image_bytes: bytes,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all images belonging to the same person
        Returns results filtered to only show the querying user's matches
        
        Args:
            db: Database session
            image_bytes: Query face image
            threshold: Similarity threshold
            
        Returns:
            List of matching images with metadata
        """
        threshold = threshold or settings.similarity_threshold
        
        # Find similar faces without user filter
        results = await self.find_similar_faces(
            image_bytes=image_bytes,
            k=settings.top_k_results,
            threshold=threshold
        )
        
        if not results:
            return []
        
        # Get image details for each result
        image_ids = [r["image_id"] for r in results]
        
        stmt = select(Image).where(Image.id.in_(image_ids))
        result = await db.execute(stmt)
        images = {img.id: img for img in result.scalars().all()}
        
        # Enrich results with image metadata
        enriched = []
        for r in results:
            image = images.get(r["image_id"])
            if image:
                enriched.append({
                    **r,
                    "filename": image.original_filename,
                    "file_path": image.file_path,
                    "created_at": image.created_at.isoformat(),
                    "user_id": image.user_id
                })
        
        return enriched
    
    async def get_user_images_count(
        self,
        db: AsyncSession,
        user_id: str
    ) -> int:
        """Get count of images for a user"""
        stmt = select(Image).where(Image.user_id == user_id)
        result = await db.execute(stmt)
        return len(result.scalars().all())
    
    async def delete_user_images(
        self,
        db: AsyncSession,
        user_id: str
    ) -> int:
        """
        Delete all images for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Count of deleted images
        """
        # Get images to delete
        stmt = select(Image).where(Image.user_id == user_id)
        result = await db.execute(stmt)
        images = result.scalars().all()
        
        count = len(images)
        
        # Delete files
        for image in images:
            if os.path.exists(image.file_path):
                os.remove(image.file_path)
        
        # Mark vectors as deleted
        self.search_service.remove_vectors_by_user(user_id)
        
        # Delete from database
        del_stmt = delete(Image).where(Image.user_id == user_id)
        await db.execute(del_stmt)
        
        del_cache_stmt = delete(EmbeddingCache).where(EmbeddingCache.user_id == user_id)
        await db.execute(del_cache_stmt)
        
        logger.info("user_images_deleted", user_id=user_id, count=count)
        
        return count
    
    def save_index(self) -> None:
        """Persist the FAISS index to disk"""
        self.search_service.save_index()
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_vectors": self.search_service.get_vector_count(),
            "embedding_dim": 512
        }


# Singleton instance
_inference_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    """Get singleton inference service instance"""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service
