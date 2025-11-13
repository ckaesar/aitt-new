"""
认证相关API路由
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.user import UserCreate, UserResponse, UserLoginResponse, ChangePasswordRequest
from app.schemas.common import DataResponse
from app.services.auth import AuthService
from app.services.user import UserService
# 开发模式：去除鉴权依赖

router = APIRouter()


@router.post("/register", response_model=DataResponse[UserResponse])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    user_service = UserService(db)
    auth_service = AuthService(db)
    
    # 检查用户名是否已存在
    existing_user = await user_service.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    existing_email = await user_service.get_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建用户
    # 对密码进行哈希
    hashed = auth_service.get_password_hash(user_data.password)
    user_data.password = hashed
    user = await user_service.create(user_data)
    
    return DataResponse(
        data=UserResponse.from_orm(user),
        message="注册成功"
    )


@router.post("/login", response_model=DataResponse[UserLoginResponse])
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    auth_service = AuthService(db)
    
    # 验证用户凭据
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return DataResponse(
        data=UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user)
        ),
        message="登录成功"
    )


@router.post("/change-password", response_model=DataResponse[dict])
async def change_password(
    password_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """开发模式：允许直接修改密码（不校验登录态）"""
    auth_service = AuthService(db)
    user_service = UserService(db)
    # 简化：按用户名查找并更新密码
    user = await user_service.get_by_username(password_data.username) if hasattr(password_data, "username") else None
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在或未提供用户名")
    new_password_hash = auth_service.get_password_hash(password_data.new_password)
    await user_service.update_password(user.id, new_password_hash)
    return DataResponse(data={"success": True}, message="密码修改成功（开发模式）")


@router.post("/refresh", response_model=DataResponse[UserLoginResponse])
async def refresh_token(
    db: AsyncSession = Depends(get_db)
):
    """开发模式：返回占位令牌与匿名用户"""
    auth_service = AuthService(db)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(data={"sub": "anonymous"}, expires_delta=access_token_expires)
    anon = UserResponse(id=0, username="anonymous", email="anon@example.com", is_active=True, is_superuser=False)
    return DataResponse(
        data=UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=anon
        ),
        message="令牌刷新成功（开发模式）"
    )


@router.get("/me", response_model=DataResponse[UserResponse])
async def get_current_user_info():
    """开发模式：返回匿名用户信息"""
    anon = UserResponse(id=0, username="anonymous", email="anon@example.com", is_active=True, is_superuser=False)
    return DataResponse(data=anon, message="获取用户信息成功（开发模式）")