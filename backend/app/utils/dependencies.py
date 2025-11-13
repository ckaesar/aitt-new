"""
依赖注入相关工具
"""
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from datetime import datetime
# 注：开发模式下允许禁用鉴权，为避免 OAuth2 依赖直接抛401，这里不强制使用OAuth2依赖
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserResponse
from app.services.user import UserService
from app.utils.security import verify_token
from app.models.user import UserRole
from app.core.config import settings
from sqlalchemy.engine.url import make_url

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 开发模式关闭鉴权：直接返回一个管理员用户，以便打通功能
    if settings.AUTH_DISABLED:
        return UserResponse(
            id=0,
            username="dev",
            email="dev@example.com",
            full_name="开发模式",
            department="Dev",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    # 生产/鉴权开启：从请求头解析Bearer令牌
    auth = request.headers.get("Authorization")
    token: Optional[str] = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
    if not token:
        raise credentials_exception
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # 获取用户信息（优先ORM，失败则降级PyMySQL）
    user_service = UserService(db)
    try:
        user = await user_service.get_by_username(username)
    except Exception:
        # ORM 不可用（例如缺失 greenlet）时，降级为 PyMySQL 查询
        try:
            import pymysql
            from pymysql.cursors import DictCursor

            url = make_url(settings.DATABASE_URL)
            conn = pymysql.connect(
                host=url.host or "localhost",
                port=int(url.port or 3306),
                user=url.username,
                password=url.password or "",
                database=url.database,
                charset="utf8mb4",
                cursorclass=DictCursor,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, username, email, password_hash, full_name, department, role, is_active, created_at, updated_at FROM aitt_users WHERE username=%s",
                        (username,),
                    )
                    row = cur.fetchone()
            finally:
                conn.close()
            if row:
                class SimpleUser:
                    def __init__(self, r: dict):
                        self.id = r.get("id")
                        self.username = r.get("username")
                        self.email = r.get("email")
                        self.password_hash = r.get("password_hash")
                        self.full_name = r.get("full_name")
                        self.department = r.get("department")
                        role_val = r.get("role")
                        try:
                            self.role = UserRole[role_val.upper()] if isinstance(role_val, str) else role_val
                        except Exception:
                            self.role = UserRole.VIEWER
                        self.is_active = bool(r.get("is_active", 1))
                        self.created_at = r.get("created_at")
                        self.updated_at = r.get("updated_at")
                user = SimpleUser(row)
            else:
                user = None
        except Exception:
            user = None
    if user is None:
        raise credentials_exception
    
    # 统一转为响应模型（SimpleUser 支持属性访问）
    # 角色字段兼容枚举/字符串
    _role = getattr(user, "role")
    try:
        from app.models.user import UserRole as _UserRole
        if isinstance(_role, _UserRole):
            role_str = _role.value
        else:
            s = str(_role)
            try:
                role_str = _UserRole(s.lower()).value  # 按枚举值匹配
            except Exception:
                role_str = _UserRole[s.upper()].value  # 回退按名称匹配
    except Exception:
        role_str = str(_role).lower()

    return UserResponse(
        id=getattr(user, "id"),
        username=getattr(user, "username"),
        email=getattr(user, "email"),
        full_name=getattr(user, "full_name"),
        department=getattr(user, "department"),
        role=role_str,
        is_active=getattr(user, "is_active", True),
        created_at=getattr(user, "created_at", None),
        updated_at=getattr(user, "updated_at", None),
    )


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="用户账户已被禁用"
        )
    return current_user


def require_role(required_role: str):
    """角色权限装饰器"""
    def role_checker(current_user: UserResponse = Depends(get_current_active_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


def require_admin():
    """需要管理员权限"""
    return require_role("admin")


def require_analyst():
    """需要分析师权限"""
    def analyst_checker(current_user: UserResponse = Depends(get_current_active_user)):
        if current_user.role not in ["admin", "analyst"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要分析师或管理员权限"
            )
        return current_user
    return analyst_checker