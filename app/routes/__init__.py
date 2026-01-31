"""
Routes Package Initialization
"""

from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.scan import router as scan_router
from app.routes.gallery import router as gallery_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(scan_router)
api_router.include_router(gallery_router)

__all__ = [
    "api_router",
    "auth_router",
    "scan_router",
    "gallery_router",
]
