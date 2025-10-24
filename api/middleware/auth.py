"""
Authentication middleware for Code Review AI
"""
import time
from typing import Optional

import structlog
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from db.models import User

logger = structlog.get_logger(__name__)
security = HTTPBearer()
settings = get_settings()


class AuthMiddleware:
    """Authentication middleware for FastAPI"""
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip auth for health checks and docs
            if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/metrics"]:
                await self.app(scope, receive, send)
                return
            
            # Extract and validate token
            try:
                token = self._extract_token(request)
                if token:
                    payload = self._verify_token(token)
                    if payload:
                        # Add user info to request state
                        scope["user"] = payload
            except HTTPException:
                # Let individual endpoints handle auth requirements
                pass
            except Exception as e:
                logger.warning("Auth middleware error", error=str(e))

        await self.app(scope, receive, send)

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request"""
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        if not authorization.startswith("Bearer "):
            return None
            
        return authorization.split(" ")[1]

    def _verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Check token expiration
            exp = payload.get("exp")
            if exp and exp < time.time():
                raise HTTPException(status_code=401, detail="Token expired")
                
            return payload
            
        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
        
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error("User authentication failed", error=str(e))
        raise HTTPException(status_code=500, detail="Authentication failed")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
