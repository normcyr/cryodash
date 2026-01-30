"""Security utilities for CryoDash API."""

import logging
from typing import Optional

from fastapi import Header, HTTPException, status

from cryodash.config import API_KEY, REQUIRE_API_KEY

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The API key if valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not REQUIRE_API_KEY:
        # Skip verification in development mode
        return "dev-mode"

    if not x_api_key:
        logger.warning("API request without X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if x_api_key != API_KEY:
        logger.warning(f"API request with invalid key: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_api_key
