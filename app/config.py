"""
Configuration Management Module
Loads environment variables and provides typed settings
"""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/dev_studio_db",
        description="Async database URL"
    )
    database_sync_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/dev_studio_db",
        description="Sync database URL for migrations"
    )
    
    # JWT
    jwt_secret_key: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT encoding"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    reload: bool = Field(default=False)
    
    # FAISS
    faiss_index_path: str = Field(default="data/embeddings/face_index.faiss")
    faiss_metadata_path: str = Field(default="data/embeddings/metadata.json")
    similarity_threshold: float = Field(default=0.75)
    top_k_results: int = Field(default=10)
    
    # Face Detection
    face_model_name: str = Field(default="buffalo_l")
    face_det_size: int = Field(default=640)
    face_ctx_id: int = Field(default=0)
    
    # Storage
    upload_dir: str = Field(default="data/raw")
    processed_dir: str = Field(default="data/processed")
    max_file_size_mb: int = Field(default=10)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/app.log")
    
    # CORS
    allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    
    # Session
    session_expire_minutes: int = Field(default=30)
    qr_base_url: str = Field(default="http://localhost:3000")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export singleton
settings = get_settings()
