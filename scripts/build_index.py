#!/usr/bin/env python
"""
Build FAISS Index from Existing Images
Scans the data directory and builds/rebuilds the vector index
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.pipeline import get_face_pipeline, FaceNotFoundException
from app.services.search import get_search_service


async def scan_images(directory: str) -> List[Tuple[str, str, str]]:
    """
    Scan directory for images
    
    Returns:
        List of (image_path, user_id, image_id) tuples
    """
    images = []
    
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in valid_extensions:
                file_path = os.path.join(root, file)
                
                # Extract user_id from path structure: data/raw/{user_id}/image.jpg
                rel_path = os.path.relpath(file_path, directory)
                parts = rel_path.split(os.sep)
                
                user_id = parts[0] if len(parts) > 1 else "default"
                image_id = Path(file).stem
                
                images.append((file_path, user_id, image_id))
    
    return images


def build_index(images: List[Tuple[str, str, str]], batch_size: int = 50) -> None:
    """
    Build FAISS index from images
    
    Args:
        images: List of (image_path, user_id, image_id)
        batch_size: Batch size for processing
    """
    pipeline = get_face_pipeline()
    search_service = get_search_service()
    
    print(f"\nProcessing {len(images)} images...")
    
    embeddings = []
    metadata_list = []
    skipped = 0
    
    for i, (image_path, user_id, image_id) in enumerate(images):
        try:
            # Extract embedding
            embedding = pipeline.extract_embedding_from_path(
                image_path,
                require_single_face=False
            )
            
            embeddings.append(embedding)
            metadata_list.append({
                "image_id": image_id,
                "user_id": user_id,
                "file_path": image_path
            })
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(images)} images...")
                
        except FaceNotFoundException:
            print(f"  No face in: {image_path}")
            skipped += 1
        except Exception as e:
            print(f"  Error processing {image_path}: {e}")
            skipped += 1
    
    if embeddings:
        # Rebuild index
        search_service.rebuild_index(embeddings, metadata_list)
        search_service.save_index()
        
        print(f"\nIndex built successfully!")
        print(f"  Total vectors: {search_service.get_vector_count()}")
        print(f"  Skipped: {skipped}")
    else:
        print("\nNo faces found to index!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build FAISS index from images")
    parser.add_argument(
        "--directory",
        "-d",
        default=settings.upload_dir,
        help="Directory to scan for images"
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=50,
        help="Batch size for processing"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Directory not found: {args.directory}")
        sys.exit(1)
    
    print(f"Building FAISS index from: {args.directory}")
    print(f"Index will be saved to: {settings.faiss_index_path}")
    
    # Scan for images
    images = asyncio.run(scan_images(args.directory))
    print(f"Found {len(images)} images")
    
    if not images:
        print("No images found!")
        sys.exit(0)
    
    # Build index
    build_index(images, args.batch_size)


if __name__ == "__main__":
    main()
