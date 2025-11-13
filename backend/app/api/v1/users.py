"""
用户管理API
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import DataResponse, PaginatedResponse, PaginationInfo
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import UserService
# 开发模式：不依赖鉴权

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    users = await service.list_users(limit=limit, offset=offset)
    return PaginatedResponse(
        data=[UserResponse.from_orm(u) for u in users],
        pagination=PaginationInfo(limit=limit, offset=offset, total=len(users)),
        message="获取用户列表成功",
    )


@router.get("/{user_id}", response_model=DataResponse[UserResponse])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return DataResponse(data=UserResponse.from_orm(user), message="获取用户成功")


@router.patch("/{user_id}", response_model=DataResponse[UserResponse])
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.update_user(user_id, payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return DataResponse(data=UserResponse.from_orm(user), message="更新用户成功")


@router.delete("/{user_id}", response_model=DataResponse[dict])
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    await service.delete_user(user_id)
    return DataResponse(data={"success": True}, message="删除用户成功")