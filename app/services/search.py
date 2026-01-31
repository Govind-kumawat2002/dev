"""
FAISS Vector Search Service
Handles vector indexing and similarity search
Uses same IndexFlatIP approach as tested app.py
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading

import numpy as np
import faiss

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorSearchService:
    """
    FAISS-based vector search service
    Uses same IndexFlatIP as tested app.py
    """
    
    _instance: Optional["VectorSearchService"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "VectorSearchService":
        """Singleton pattern for thread safety"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize FAISS index - same as app.py"""
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        # Same dimension as app.py
        self.DIM = 512
        self.index: Optional[faiss.Index] = None
        self.stored_names: List[str] = []  # Same as app.py
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self._write_lock = threading.Lock()
        
        self._index_path = Path(settings.faiss_index_path)
        self._metadata_path = Path(settings.faiss_metadata_path)
        
        self._load_or_create_index()
        self._initialized = True
    
    def _load_or_create_index(self) -> None:
        """Load existing index or create new one"""
        if self._index_path.exists() and self._metadata_path.exists():
            try:
                self._load_index()
                logger.info(
                    "faiss_index_loaded",
                    path=str(self._index_path),
                    total_vectors=self.index.ntotal
                )
            except Exception as e:
                logger.error("faiss_index_load_failed", error=str(e))
                self._create_index()
        else:
            self._create_index()
    
    def _create_index(self) -> None:
        """Create a new FAISS index - same as app.py: IndexFlatIP"""
        # Use Inner Product for cosine similarity - same as app.py
        self.index = faiss.IndexFlatIP(self.DIM)
        self.stored_names = []
        self.metadata = {}
        
        # Ensure directory exists
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("faiss_index_created", dim=self.DIM)
    
    def _load_index(self) -> None:
        """Load index and metadata from disk"""
        self.index = faiss.read_index(str(self._index_path))
        
        with open(self._metadata_path, "r") as f:
            data = json.load(f)
            # Support both old format (list) and new format (dict)
            if isinstance(data, list):
                self.stored_names = data
                self.metadata = {i: {"filename": name} for i, name in enumerate(data)}
            else:
                self.stored_names = data.get("stored_names", [])
                self.metadata = {int(k): v for k, v in data.get("metadata", {}).items()}
    
    def save_index(self) -> None:
        """Save index and metadata to disk"""
        with self._write_lock:
            # Ensure directory exists
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(self._index_path))
            
            # Save metadata
            data = {
                "stored_names": self.stored_names,
                "metadata": self.metadata
            }
            with open(self._metadata_path, "w") as f:
                json.dump(data, f, indent=2)
        
        logger.info(
            "faiss_index_saved",
            path=str(self._index_path),
            total_vectors=self.index.ntotal
        )
    
    def add_vector(
        self,
        embedding: np.ndarray,
        image_id: str,
        user_id: str,
        filename: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a vector to the index - similar to app.py add_face
        
        Args:
            embedding: 512-d embedding (float32)
            image_id: Image identifier
            user_id: User identifier
            filename: Original filename
            additional_metadata: Optional extra metadata
            
        Returns:
            Vector ID in index
        """
        with self._write_lock:
            # Get next ID
            vector_id = self.index.ntotal
            
            # Ensure embedding is 2D and float32 - same as app.py
            emb = np.array([embedding], dtype="float32")
            
            # Add to index
            self.index.add(emb)
            
            # Store name - same pattern as app.py
            self.stored_names.append(filename or image_id)
            
            # Store extended metadata
            self.metadata[vector_id] = {
                "image_id": image_id,
                "user_id": user_id,
                "filename": filename or image_id,
                **(additional_metadata or {})
            }
        
        logger.debug(
            "vector_added",
            vector_id=vector_id,
            image_id=image_id,
            user_id=user_id
        )
        
        return vector_id
    
    def add_vectors_batch(
        self,
        embeddings: List[np.ndarray],
        image_ids: List[str],
        user_ids: List[str],
        filenames: Optional[List[str]] = None
    ) -> List[int]:
        """
        Add multiple vectors to the index
        """
        with self._write_lock:
            start_id = self.index.ntotal
            
            # Stack embeddings - same dtype as app.py
            embeddings_array = np.array(embeddings, dtype="float32")
            
            # Add to index
            self.index.add(embeddings_array)
            
            # Store metadata
            vector_ids = []
            for i, (image_id, user_id) in enumerate(zip(image_ids, user_ids)):
                vector_id = start_id + i
                filename = filenames[i] if filenames else image_id
                
                self.stored_names.append(filename)
                self.metadata[vector_id] = {
                    "image_id": image_id,
                    "user_id": user_id,
                    "filename": filename
                }
                vector_ids.append(vector_id)
        
        logger.info("vectors_batch_added", count=len(vector_ids))
        
        return vector_ids
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        user_id: Optional[str] = None,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar faces - same logic as app.py search_face
        
        Args:
            query_embedding: Query face embedding
            k: Number of results to return (default 5 like app.py)
            user_id: Optional filter by user
            threshold: Minimum similarity threshold
            
        Returns:
            List of search results with metadata
        """
        if self.index.ntotal == 0:
            return []
        
        # Ensure embedding is 2D and float32 - same as app.py
        emb = np.array([query_embedding], dtype="float32")
        
        # Search more results if filtering by user
        search_k = min(k * 10 if user_id else k, self.index.ntotal)
        
        # Perform search - same as app.py
        D, I = self.index.search(emb, search_k)
        
        results = []
        for i, idx in enumerate(I[0]):
            if idx == -1:  # Invalid result
                continue
            
            similarity = float(D[0][i])  # Inner product = similarity
            
            if similarity < threshold:
                continue
            
            # Get metadata
            meta = self.metadata.get(int(idx), {})
            
            # Get filename from stored_names (like app.py)
            filename = self.stored_names[idx] if idx < len(self.stored_names) else None
            
            # Filter by user if specified
            if user_id and meta.get("user_id") != user_id:
                continue
            
            results.append({
                "rank": len(results) + 1,
                "image": filename,  # Same key as app.py
                "similarity": similarity,
                "vector_id": int(idx),
                "image_id": meta.get("image_id"),
                "user_id": meta.get("user_id"),
            })
            
            if len(results) >= k:
                break
        
        logger.debug("search_completed", query_k=k, results=len(results))
        
        return results
    
    def get_vector_count(self) -> int:
        """Get total number of vectors in index"""
        return self.index.ntotal
    
    def get_stored_names(self) -> List[str]:
        """Get list of stored filenames - same as app.py stored_names"""
        return self.stored_names
    
    def get_metadata(self, vector_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a vector ID"""
        return self.metadata.get(vector_id)
    
    def rebuild_index(
        self,
        embeddings: List[np.ndarray],
        metadata_list: List[Dict[str, Any]]
    ) -> None:
        """
        Rebuild the entire index
        """
        with self._write_lock:
            # Create new index
            self._create_index()
            
            if embeddings:
                # Add all embeddings
                embeddings_array = np.array(embeddings, dtype="float32")
                self.index.add(embeddings_array)
                
                # Store metadata
                for i, meta in enumerate(metadata_list):
                    self.stored_names.append(meta.get("filename", meta.get("image_id", str(i))))
                    self.metadata[i] = meta
        
        logger.info("index_rebuilt", total_vectors=self.index.ntotal)
    
    def remove_vectors_by_user(self, user_id: str) -> int:
        """
        Mark vectors for a user as removed
        NOTE: FAISS doesn't support true deletion, requires rebuild
        """
        removed = 0
        with self._write_lock:
            for vid, meta in list(self.metadata.items()):
                if meta.get("user_id") == user_id:
                    meta["deleted"] = True
                    removed += 1
        
        logger.info("vectors_marked_deleted", user_id=user_id, count=removed)
        return removed


# Singleton instance
_search_service: Optional[VectorSearchService] = None


def get_search_service() -> VectorSearchService:
    """Get singleton search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = VectorSearchService()
    return _search_service
