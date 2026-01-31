"""
Core Package Initialization
"""

from app.core.engine import (
    Base,
    engine,
    async_session_factory,
    get_db,
    get_db_context,
    create_tables,
    drop_tables,
    check_database_connection,
    dispose_engine
)
from app.core.pipeline import (
    FacePipeline,
    FaceNotFoundException,
    MultipleFacesException,
    get_face_pipeline
)

__all__ = [
    # Database
    "Base",
    "engine",
    "async_session_factory",
    "get_db",
    "get_db_context",
    "create_tables",
    "drop_tables",
    "check_database_connection",
    "dispose_engine",
    # Pipeline
    "FacePipeline",
    "FaceNotFoundException",
    "MultipleFacesException",
    "get_face_pipeline",
]
