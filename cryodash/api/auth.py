"""Authentication routes for CryoDash."""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from cryodash.auth import (
    TokenData,
    create_access_token,
    get_admin_user,
    get_current_user,
)
from cryodash.config import API_KEY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Hardcoded admin credentials (in production, use database)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = API_KEY  # Use API_KEY as password for now


class LoginRequest(BaseModel):
    """Request schema for login."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Response schema for login."""

    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool


class UserInfo(BaseModel):
    """Response schema for current user info."""

    username: str
    is_admin: bool


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate user and return JWT token.

    Args:
        credentials: Username and password

    Returns:
        JWT access token and user info

    Raises:
        HTTPException: If credentials are invalid
    """
    # Simple admin authentication for now
    if credentials.username != ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Direct plaintext comparison for admin password (API_KEY)
    if credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": ADMIN_USERNAME, "is_admin": True},
        expires_delta=timedelta(hours=24),
    )

    return LoginResponse(
        access_token=access_token,
        username=ADMIN_USERNAME,
        is_admin=True,
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        User information
    """
    return UserInfo(username=current_user.username, is_admin=current_user.is_admin)


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """
    Logout user (client-side token deletion for stateless JWT).

    Args:
        current_user: Current authenticated user

    Returns:
        Logout confirmation
    """
    logger.info(f"User {current_user.username} logged out")
    return {"message": "Successfully logged out"}


@router.get("/admin/check")
async def check_admin_status(admin_user: TokenData = Depends(get_admin_user)):
    """
    Check if current user has admin privileges.

    Args:
        admin_user: Current user (must be admin)

    Returns:
        Admin status confirmation
    """
    return {"is_admin": True, "username": admin_user.username}
