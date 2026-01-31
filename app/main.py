"""
Dev Studio Face Similarity Platform
Main FastAPI Application Entry Point
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import api_router
from app.core.engine import create_tables, dispose_engine, check_database_connection
from app.core.pipeline import FaceNotFoundException, MultipleFacesException
from app.services import get_search_service
from app.utils.logger import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("application_starting", host=settings.host, port=settings.port)
    
    # Create data directories
    directories = [
        settings.upload_dir,
        settings.processed_dir,
        Path(settings.faiss_index_path).parent,
        Path(settings.log_file).parent,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Create database tables
    try:
        await create_tables()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    
    # Initialize face pipeline (loads model)
    try:
        from app.core.pipeline import get_face_pipeline
        get_face_pipeline()
        logger.info("face_pipeline_ready")
    except Exception as e:
        logger.error("face_pipeline_init_failed", error=str(e))
    
    # Initialize vector search
    try:
        search_service = get_search_service()
        logger.info(
            "vector_search_ready",
            total_vectors=search_service.get_vector_count()
        )
    except Exception as e:
        logger.error("vector_search_init_failed", error=str(e))
    
    logger.info("application_started")
    
    yield
    
    # Shutdown
    logger.info("application_stopping")
    
    # Save FAISS index
    try:
        search_service = get_search_service()
        search_service.save_index()
        logger.info("vector_index_saved")
    except Exception as e:
        logger.error("vector_index_save_failed", error=str(e))
    
    # Dispose database connections
    await dispose_engine()
    
    logger.info("application_stopped")


# Create FastAPI application
app = FastAPI(
    title="Dev Studio Face Similarity Platform",
    description="""
    Production-grade Face Similarity Search Platform
    
    Features:
    - Face detection and recognition using InsightFace (ArcFace)
    - FAISS vector search for fast similarity matching
    - QR code session management for mobile access
    - JWT authentication
    - PostgreSQL for metadata storage
    
    API Documentation:
    - Swagger UI: /docs
    - ReDoc: /redoc
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(FaceNotFoundException)
async def face_not_found_handler(request: Request, exc: FaceNotFoundException):
    """Handle FaceNotFoundException"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "No face detected in the image", "error_type": "face_not_found"}
    )


@app.exception_handler(MultipleFacesException)
async def multiple_faces_handler(request: Request, exc: MultipleFacesException):
    """Handle MultipleFacesException"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "multiple_faces"}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include API routes
app.include_router(api_router)


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API info"""
    return {
        "name": "Dev Studio Face Similarity Platform",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_healthy = await check_database_connection()
    search_service = get_search_service()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "vector_index": {
            "status": "ready",
            "total_vectors": search_service.get_vector_count()
        }
    }


@app.get("/health/live", tags=["Health"])
async def liveness_probe():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness_probe():
    """Kubernetes readiness probe"""
    db_healthy = await check_database_connection()
    if not db_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "reason": "database unavailable"}
        )
    return {"status": "ready"}


# Mount static files for uploaded images (optional - behind auth in production)
if os.path.exists(settings.upload_dir):
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
