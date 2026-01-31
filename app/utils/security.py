"""
Security Utilities Module
JWT authentication, password hashing, and session management
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


class TokenData:
    """Decoded JWT token data"""
    
    def __init__(
        self,
        user_id: str,
        session_id: str,
        exp: datetime,
        token_type: str = "access"
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.exp = exp
        self.token_type = token_type


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_session_id() -> str:
    """
    Generate a unique session ID
    
    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())


def generate_qr_token() -> str:
    """
    Generate a secure QR token for session initialization
    
    Returns:
        URL-safe random token
    """
    return secrets.token_urlsafe(32)


def create_access_token(
    user_id: str,
    session_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    logger.debug("access_token_created", user_id=user_id, session_id=session_id)
    return token


def create_session_token(session_id: str, expires_minutes: int = None) -> str:
    """
    Create a JWT token for QR-based session
    
    Args:
        session_id: Session identifier
        expires_minutes: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_minutes is None:
        expires_minutes = settings.session_expire_minutes
    
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    
    payload = {
        "session_id": session_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "session"
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    logger.debug("session_token_created", session_id=session_id)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dictionary
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning("token_decode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def verify_token(token: str) -> TokenData:
    """
    Verify and extract data from a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object with extracted information
    """
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    exp = datetime.fromtimestamp(payload.get("exp", 0))
    token_type = payload.get("type", "access")
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return TokenData(
        user_id=user_id or "",
        session_id=session_id,
        exp=exp,
        token_type=token_type
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """
    Dependency to get current authenticated user from token
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        TokenData with user information
        
    Raises:
        HTTPException: If not authenticated
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """
    Dependency to optionally get current user (no error if not authenticated)
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        TokenData if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None


def generate_qr_url(session_id: str, token: str) -> str:
    """
    Generate a QR code URL for mobile access
    
    Args:
        session_id: Session identifier
        token: Session token
        
    Returns:
        Full URL for QR code
    """
    return f"{settings.qr_base_url}/scan?session={session_id}&token={token}"
