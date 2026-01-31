"""
Test Suite for Dev Studio Face Similarity Platform
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from app.main import app
from app.core.engine import Base, get_db
from app.models import User, Image
from app.utils.security import hash_password, create_access_token, generate_session_id


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden dependencies"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        id="test-user-id",
        name="Test User",
        email="test@example.com",
        phone="+1234567890",
        password_hash=hash_password("testpassword123"),
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers"""
    session_id = generate_session_id()
    token = create_access_token(test_user.id, session_id)
    return {"Authorization": f"Bearer {token}"}


# ==============================
# API Tests
# ==============================

class TestHealthEndpoints:
    """Test health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Dev Studio Face Similarity Platform"
        assert data["status"] == "operational"
    
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """Test health endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "vector_index" in data
    
    @pytest.mark.asyncio
    async def test_liveness(self, client: AsyncClient):
        """Test liveness probe"""
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestAuthRoutes:
    """Test authentication routes"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "user_id" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Another User",
                "email": test_user.email,
                "password": "password123"
            }
        )
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test getting current user info"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["name"] == test_user.name
    
    @pytest.mark.asyncio
    async def test_qr_session_creation(self, client: AsyncClient):
        """Test QR session creation"""
        response = await client.post(
            "/api/v1/auth/session/qr",
            json={"device_info": "Test Device"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "qr_token" in data
        assert "qr_url" in data
        assert "qr_image_base64" in data


class TestGalleryRoutes:
    """Test gallery routes"""
    
    @pytest.mark.asyncio
    async def test_get_empty_gallery(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test getting empty gallery"""
        response = await client.get("/api/v1/gallery", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["images"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_unauthorized_gallery_access(self, client: AsyncClient):
        """Test unauthorized gallery access"""
        response = await client.get("/api/v1/gallery")
        assert response.status_code == 401


class TestScanRoutes:
    """Test face scan routes"""
    
    @pytest.mark.asyncio
    async def test_scan_stats(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test scan statistics endpoint"""
        response = await client.get("/api/v1/scan/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "user_images" in data
        assert "total_indexed" in data


# ==============================
# Unit Tests
# ==============================

class TestSecurityUtils:
    """Test security utilities"""
    
    def test_password_hashing(self):
        """Test password hash and verify"""
        from app.utils.security import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
    
    def test_token_creation(self):
        """Test JWT token creation and verification"""
        from app.utils.security import (
            create_access_token,
            verify_token,
            generate_session_id
        )
        
        user_id = "test-user"
        session_id = generate_session_id()
        token = create_access_token(user_id, session_id)
        
        token_data = verify_token(token)
        assert token_data.user_id == user_id
        assert token_data.session_id == session_id


class TestEmbeddingService:
    """Test embedding service"""
    
    def test_embedding_bytes_conversion(self):
        """Test embedding to bytes and back"""
        import numpy as np
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        original = np.random.randn(512).astype(np.float32)
        
        as_bytes = service.embedding_to_bytes(original)
        restored = service.bytes_to_embedding(as_bytes)
        
        np.testing.assert_array_almost_equal(original, restored)
    
    def test_normalize_embedding(self):
        """Test embedding normalization"""
        import numpy as np
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        embedding = np.array([3, 4, 0], dtype=np.float32)
        normalized = service.normalize_embedding(embedding)
        
        assert np.isclose(np.linalg.norm(normalized), 1.0)


# ==============================
# Run Tests
# ==============================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
