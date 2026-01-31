#!/usr/bin/env python
"""
Seed Database with Sample Data
Creates test users and processes sample images
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.config import settings
from app.core.engine import get_db_context
from app.models import User, Image
from app.utils.security import hash_password


# Sample users
SAMPLE_USERS = [
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "password": "password123"
    },
    {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+1987654321",
        "password": "password123"
    },
    {
        "name": "Demo User",
        "email": "demo@devstudio.app",
        "phone": "+1555123456",
        "password": "demopassword"
    }
]


async def create_users() -> list[User]:
    """Create sample users"""
    created = []
    
    async with get_db_context() as db:
        for user_data in SAMPLE_USERS:
            # Check if user exists
            stmt = select(User).where(User.email == user_data["email"])
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"  User already exists: {user_data['email']}")
                created.append(existing)
                continue
            
            user = User(
                id=str(uuid.uuid4()),
                name=user_data["name"],
                email=user_data["email"],
                phone=user_data["phone"],
                password_hash=hash_password(user_data["password"]),
                is_active=True,
                is_verified=True
            )
            
            db.add(user)
            await db.flush()
            created.append(user)
            
            print(f"  Created user: {user.name} ({user.email})")
        
        await db.commit()
    
    return created


async def process_sample_images(users: list[User]) -> None:
    """Process sample images if they exist"""
    from app.services import get_inference_service
    
    inference = get_inference_service()
    sample_dir = Path("data/sample")
    
    if not sample_dir.exists():
        print("\n  No sample images directory found (data/sample)")
        return
    
    async with get_db_context() as db:
        for i, user in enumerate(users):
            user_sample_dir = sample_dir / str(i + 1)  # data/sample/1, data/sample/2, etc.
            
            if not user_sample_dir.exists():
                continue
            
            print(f"\n  Processing images for {user.name}...")
            
            for image_file in user_sample_dir.iterdir():
                if image_file.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                    continue
                
                try:
                    with open(image_file, "rb") as f:
                        image_bytes = f.read()
                    
                    image, vector_id = await inference.process_and_store_image(
                        db=db,
                        image_bytes=image_bytes,
                        user_id=user.id,
                        filename=image_file.name,
                        file_size=len(image_bytes)
                    )
                    
                    print(f"    Indexed: {image_file.name} -> vector {vector_id}")
                    
                except Exception as e:
                    print(f"    Error processing {image_file.name}: {e}")
        
        await db.commit()
    
    # Save index
    inference.save_index()


async def main():
    """Main entry point"""
    print("=" * 50)
    print("Dev Studio Database Seeder")
    print("=" * 50)
    
    # Create directories
    dirs = [
        settings.upload_dir,
        settings.processed_dir,
        Path(settings.faiss_index_path).parent,
        "data/sample"
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    print("\n1. Creating users...")
    users = await create_users()
    print(f"   Total users: {len(users)}")
    
    print("\n2. Processing sample images...")
    await process_sample_images(users)
    
    print("\n" + "=" * 50)
    print("Seeding complete!")
    print("=" * 50)
    print("\nTest credentials:")
    for user in SAMPLE_USERS:
        print(f"  Email: {user['email']} / Password: {user['password']}")


if __name__ == "__main__":
    asyncio.run(main())
