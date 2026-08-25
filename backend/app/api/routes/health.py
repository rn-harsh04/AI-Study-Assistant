from __future__ import annotations

from typing import Any
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, Any]:
    settings = get_settings()
    has_key = bool(settings.gemini_api_key and settings.gemini_api_key.strip())
    return {
        "status": "ok",
        "gemini_api_key_configured": has_key,
    }