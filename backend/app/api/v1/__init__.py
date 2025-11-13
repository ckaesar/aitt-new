"""
API v1版本路由
"""
from fastapi import APIRouter
from .auth import router as auth_router
from .health import router as health_router
from .users import router as users_router
from .data_sources import router as data_sources_router
from .queries import router as queries_router
from .ai import router as ai_router
from .rag import router as rag_router
from .metadata import router as metadata_router

api_router = APIRouter()

# 健康检查路由（v1前缀）
api_router.include_router(health_router, tags=["健康检查"])

# 认证相关路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])

# 用户管理路由
api_router.include_router(users_router, prefix="/users", tags=["用户管理"])

# 数据源管理路由
api_router.include_router(data_sources_router, prefix="/data-sources", tags=["数据源管理"])

# 查询相关路由
api_router.include_router(queries_router, prefix="/queries", tags=["查询管理"])

# AI相关路由
api_router.include_router(ai_router, prefix="/ai", tags=["AI服务"])

# RAG相关路由
api_router.include_router(rag_router, prefix="/rag", tags=["RAG"])

# 元数据索引同步路由
api_router.include_router(metadata_router, prefix="/metadata", tags=["元数据索引"])

__all__ = ["api_router"]