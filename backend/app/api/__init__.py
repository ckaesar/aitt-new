"""
API路由包初始化
"""
from fastapi import APIRouter
from .v1 import api_router as v1_router

# 顶层不再加版本前缀，版本前缀由主应用统一挂载
api_router = APIRouter()
api_router.include_router(v1_router)

__all__ = ["api_router"]