"""
Authentication Routes
Handles user registration, login, and session management
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import qrcode
import io
import base64

from app.core.engine import get_db
from app.models import User, Session
from app.config import settings
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_session_token,
    generate_session_id,
    generate_qr_token,
    generate_qr_url,
    get_current_user,
    TokenData
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==============================
# Request/Response Models
# ==============================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    """User login request"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    session_id: str


class QRSessionRequest(BaseModel):
    """Request to create a QR session"""
    device_info: Optional[str] = None


class QRSessionResponse(BaseModel):
    """QR session response with QR code data"""
    session_id: str
    qr_token: str
    qr_url: str
    qr_image_base64: str
    expires_in: int


class SessionValidateRequest(BaseModel):
    """Validate a QR session"""
    session_id: str
    qr_token: str


class UserResponse(BaseModel):
    """User info response"""
    id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    is_verified: bool
    created_at: str


# ==============================
# Routes
# ==============================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if email already exists
    if request.email:
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create user
    user_id = str(uuid.uuid4())
    session_id = generate_session_id()
    
    user = User(
        id=user_id,
        name=request.name,
        phone=request.phone,
        email=request.email,
        password_hash=hash_password(request.password),
        is_active=True
    )
    
    # Create session
    access_token = create_access_token(user_id, session_id)
    
    session = Session(
        id=session_id,
        user_id=user_id,
        token=access_token,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    
    db.add(user)
    db.add(session)
    await db.flush()
    
    logger.info("user_registered", user_id=user_id)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user_id=user_id,
        session_id=session_id
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: UserLoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email/phone and password
    """
    # Find user
    if request.email:
        stmt = select(User).where(User.email == request.email)
    elif request.phone:
        stmt = select(User).where(User.phone == request.phone)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone required"
        )
    
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create session
    session_id = generate_session_id()
    access_token = create_access_token(user.id, session_id)
    
    session = Session(
        id=session_id,
        user_id=user.id,
        token=access_token,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        ip_address=http_request.client.host if http_request.client else None
    )
    
    db.add(session)
    await db.flush()
    
    logger.info("user_logged_in", user_id=user.id, session_id=session_id)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user_id=user.id,
        session_id=session_id
    )


@router.post("/session/qr", response_model=QRSessionResponse)
async def create_qr_session(
    request: QRSessionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new QR-based session for mobile access
    Returns a QR code that can be scanned to start a session
    """
    session_id = generate_session_id()
    qr_token = generate_qr_token()
    
    # Create session without user (will be linked after face scan)
    session = Session(
        id=session_id,
        user_id=None,  # Will be set after successful face scan
        token=create_session_token(session_id),
        qr_token=qr_token,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.session_expire_minutes),
        device_info=request.device_info,
        ip_address=http_request.client.host if http_request.client else None
    )
    
    db.add(session)
    await db.flush()
    
    # Generate QR code
    qr_url = generate_qr_url(session_id, qr_token)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    logger.info("qr_session_created", session_id=session_id)
    
    return QRSessionResponse(
        session_id=session_id,
        qr_token=qr_token,
        qr_url=qr_url,
        qr_image_base64=f"data:image/png;base64,{qr_base64}",
        expires_in=settings.session_expire_minutes * 60
    )


@router.post("/session/validate", response_model=TokenResponse)
async def validate_qr_session(
    request: SessionValidateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate a QR session token
    Used when mobile user scans QR code
    """
    stmt = select(Session).where(
        Session.id == request.session_id,
        Session.qr_token == request.qr_token,
        Session.is_active == True
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired session"
        )
    
    if session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Session expired"
        )
    
    # Update session last used
    session.last_used_at = datetime.utcnow()
    await db.flush()
    
    logger.info("qr_session_validated", session_id=session.id)
    
    return TokenResponse(
        access_token=session.token,
        expires_in=int((session.expires_at - datetime.utcnow()).total_seconds()),
        user_id=session.user_id or "",
        session_id=session.id
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user info
    """
    stmt = select(User).where(User.id == token_data.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat()
    )


@router.post("/logout")
async def logout(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout current session
    """
    stmt = select(Session).where(Session.id == token_data.session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if session:
        session.is_active = False
        await db.flush()
    
    logger.info("user_logged_out", session_id=token_data.session_id)
    
    return {"message": "Logged out successfully"}
