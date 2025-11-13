"""
健康检查API（v1前缀）
"""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_v1():
    """提供 /api/v1/health 端点，便于前端统一探活"""
    return {"status": "healthy", "service": settings.APP_NAME}