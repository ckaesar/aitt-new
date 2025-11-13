from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.url import make_url

from app.models.user import User, UserRole
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户凭据。
        优先使用 ORM，若当前环境缺失 greenlet 导致 ORM 不可用，则降级为 Core 查询。
        """
        try:
            stmt = select(User).where(User.username == username)
            res = await self.db.execute(stmt)
            user = res.scalar_one_or_none()
        except Exception:
            # ORM 不可用（缺少 greenlet 等）时，降级为 PyMySQL 同步查询
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
                if not row:
                    return None

                class SimpleUser:
                    def __init__(self, r: dict):
                        self.id = r.get("id")
                        self.username = r.get("username")
                        self.email = r.get("email")
                        self.password_hash = r.get("password_hash")
                        self.full_name = r.get("full_name")
                        self.department = r.get("department")
                        # 角色字符串转换为枚举
                        role_val = r.get("role")
                        try:
                            self.role = UserRole[role_val.upper()] if isinstance(role_val, str) else role_val
                        except Exception:
                            self.role = UserRole.VIEWER
                        self.is_active = bool(r.get("is_active", 1))
                        self.created_at = r.get("created_at")
                        self.updated_at = r.get("updated_at")

                user = SimpleUser(row)
            except Exception:
                return None
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        return create_access_token(data, expires_delta)

    def get_password_hash(self, password: str) -> str:
        return get_password_hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)