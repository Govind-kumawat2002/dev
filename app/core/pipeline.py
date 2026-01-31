"""
Face Processing Pipeline Module
Orchestrates face detection, alignment, and embedding generation
Uses the same FaceAnalysis configuration from the tested app.py
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thread pool for CPU-bound face processing
_executor = ThreadPoolExecutor(max_workers=4)


class FaceNotFoundException(Exception):
    """Raised when no face is detected in an image"""
    pass


class MultipleFacesException(Exception):
    """Raised when multiple faces are detected but only one expected"""
    pass


class FacePipeline:
    """
    Face processing pipeline using InsightFace
    Handles detection, alignment, and embedding extraction
    Uses same configuration as tested app.py
    """
    
    _instance: Optional["FacePipeline"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "FacePipeline":
        """Singleton pattern for efficient model loading"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize face analysis model - same as app.py"""
        if self._initialized:
            return
        
        logger.info("Loading face model...")
        
        # Use same configuration as working app.py
        self.face_app = FaceAnalysis(name="buffalo_l")
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))
        
        self.embedding_dim = 512  # ArcFace produces 512-d vectors
        self._initialized = True
        
        logger.info("Model loaded")
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """
        Load an image from file path
        
        Args:
            image_path: Path to image file
            
        Returns:
            BGR image array
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        return img
    
    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """
        Decode image from bytes - same as app.py
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            BGR image array
        """
        img_np = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image bytes")
        
        return img
    
    def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect all faces in an image
        
        Args:
            image: BGR image array
            
        Returns:
            List of face detection results
        """
        faces = self.face_app.get(image)
        
        return [
            {
                "bbox": face.bbox.tolist(),
                "det_score": float(face.det_score),
                "embedding": face.embedding,
            }
            for face in faces
        ]
    
    def extract_embedding(
        self,
        image: np.ndarray,
        require_single_face: bool = True
    ) -> np.ndarray:
        """
        Extract face embedding from image - similar to app.py logic
        
        Args:
            image: BGR image array
            require_single_face: If True, raise error if not exactly one face
            
        Returns:
            512-dimensional embedding vector (float32)
        """
        faces = self.face_app.get(image)
        
        if len(faces) == 0:
            raise FaceNotFoundException("No face detected")
        
        if require_single_face and len(faces) > 1:
            raise MultipleFacesException(
                f"Expected 1 face, found {len(faces)}"
            )
        
        # Get embedding of first face - same as app.py
        emb = faces[0].embedding.astype("float32")
        
        return emb
    
    def extract_embedding_from_path(
        self,
        image_path: str,
        require_single_face: bool = True
    ) -> np.ndarray:
        """
        Extract face embedding from image file
        
        Args:
            image_path: Path to image file
            require_single_face: If True, raise error if not exactly one face
            
        Returns:
            512-dimensional embedding vector
        """
        image = self._load_image(image_path)
        return self.extract_embedding(image, require_single_face)
    
    def extract_embedding_from_bytes(
        self,
        image_bytes: bytes,
        require_single_face: bool = True
    ) -> np.ndarray:
        """
        Extract face embedding from image bytes - same logic as app.py
        
        Args:
            image_bytes: Raw image bytes
            require_single_face: If True, raise error if not exactly one face
            
        Returns:
            512-dimensional embedding vector
        """
        image = self._decode_image(image_bytes)
        return self.extract_embedding(image, require_single_face)
    
    async def extract_embedding_async(
        self,
        image_bytes: bytes,
        require_single_face: bool = True
    ) -> np.ndarray:
        """
        Async wrapper for embedding extraction
        
        Args:
            image_bytes: Raw image bytes
            require_single_face: If True, raise error if not exactly one face
            
        Returns:
            512-dimensional embedding vector
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self.extract_embedding_from_bytes,
            image_bytes,
            require_single_face
        )
    
    def extract_all_embeddings(
        self,
        image: np.ndarray
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        Extract embeddings for all faces in an image
        
        Args:
            image: BGR image array
            
        Returns:
            List of (embedding, face_info) tuples
        """
        faces = self.face_app.get(image)
        
        results = []
        for face in faces:
            emb = face.embedding.astype("float32")
            
            face_info = {
                "bbox": face.bbox.tolist(),
                "det_score": float(face.det_score),
            }
            
            results.append((emb, face_info))
        
        return results
    
    def crop_face(
        self,
        image: np.ndarray,
        bbox: List[float],
        margin: float = 0.2
    ) -> np.ndarray:
        """
        Crop face region from image with margin
        
        Args:
            image: BGR image array
            bbox: Face bounding box [x1, y1, x2, y2]
            margin: Margin ratio to add around face
            
        Returns:
            Cropped face image
        """
        h, w = image.shape[:2]
        x1, y1, x2, y2 = map(int, bbox)
        
        # Add margin
        face_w = x2 - x1
        face_h = y2 - y1
        margin_w = int(face_w * margin)
        margin_h = int(face_h * margin)
        
        x1 = max(0, x1 - margin_w)
        y1 = max(0, y1 - margin_h)
        x2 = min(w, x2 + margin_w)
        y2 = min(h, y2 + margin_h)
        
        return image[y1:y2, x1:x2]
    
    def save_processed_face(
        self,
        image: np.ndarray,
        output_path: str,
        size: Tuple[int, int] = (256, 256)
    ) -> str:
        """
        Save processed face image
        
        Args:
            image: Face image array
            output_path: Path to save image
            size: Output image size
            
        Returns:
            Path to saved image
        """
        # Resize
        resized = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save
        cv2.imwrite(output_path, resized)
        
        return output_path


# Global pipeline instance
_pipeline_instance: Optional[FacePipeline] = None


def get_face_pipeline() -> FacePipeline:
    """
    Get the singleton face pipeline instance
    
    Returns:
        Initialized FacePipeline
    """
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = FacePipeline()
    return _pipeline_instance
