"""
Face Embedding Service
Handles embedding generation and management
"""

import numpy as np
from typing import Optional, List, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.pipeline import get_face_pipeline, FaceNotFoundException, MultipleFacesException
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thread pool for CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=4)


class EmbeddingService:
    """Service for generating and managing face embeddings"""
    
    def __init__(self):
        self.pipeline = get_face_pipeline()
        self.embedding_dim = 512
    
    async def generate_embedding(
        self,
        image_bytes: bytes,
        require_single_face: bool = True
    ) -> np.ndarray:
        """
        Generate face embedding from image bytes
        
        Args:
            image_bytes: Raw image data
            require_single_face: Raise error if multiple faces detected
            
        Returns:
            Normalized 512-d embedding vector
        """
        try:
            embedding = await self.pipeline.extract_embedding_async(
                image_bytes,
                require_single_face
            )
            logger.debug("embedding_generated", dim=embedding.shape[0])
            return embedding
        except FaceNotFoundException:
            logger.warning("no_face_detected")
            raise
        except MultipleFacesException:
            logger.warning("multiple_faces_detected")
            raise
    
    async def generate_embeddings_batch(
        self,
        image_bytes_list: List[bytes]
    ) -> List[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple images
        
        Args:
            image_bytes_list: List of raw image data
            
        Returns:
            List of embeddings (None for failed images)
        """
        tasks = [
            self.generate_embedding(img_bytes, require_single_face=False)
            for img_bytes in image_bytes_list
        ]
        
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                embedding = await task
                results.append(embedding)
            except Exception as e:
                logger.warning("batch_embedding_failed", error=str(e))
                results.append(None)
        
        return results
    
    def embedding_to_bytes(self, embedding: np.ndarray) -> bytes:
        """
        Convert embedding array to bytes for storage
        
        Args:
            embedding: Numpy embedding array
            
        Returns:
            Raw bytes representation
        """
        return embedding.astype(np.float32).tobytes()
    
    def bytes_to_embedding(self, data: bytes) -> np.ndarray:
        """
        Convert bytes back to embedding array
        
        Args:
            data: Raw bytes representation
            
        Returns:
            Numpy embedding array
        """
        return np.frombuffer(data, dtype=np.float32)
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score (0-1)
        """
        # Embeddings should already be normalized
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)
    
    def normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        Normalize embedding vector
        
        Args:
            embedding: Raw embedding
            
        Returns:
            L2 normalized embedding
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
