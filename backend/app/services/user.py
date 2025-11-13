from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_users(self, limit: int = 20, offset: int = 0) -> List[User]:
        """列出用户列表。
        默认使用 ORM 异步查询；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步查询以保证接口可用。
        """
        try:
            stmt = select(User).order_by(User.id).limit(limit).offset(offset)
            res = await self.db.execute(stmt)
            return list(res.scalars().all())
        except Exception:
            # ORM 不可用（缺少 greenlet），降级为 PyMySQL 同步查询
            import pymysql
            from pymysql.cursors import DictCursor
            from sqlalchemy.engine.url import make_url
            from app.core.config import settings
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
            items: List[User] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, username, email, password_hash, full_name, department, role,
                               is_active, created_at, updated_at
                        FROM aitt_users
                        ORDER BY id
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                    rows = cur.fetchall()
                    from types import SimpleNamespace
                    for r in rows:
                        role_val = r.get("role")
                        try:
                            # 以值映射枚举（admin/analyst/viewer）
                            role_enum = UserRole(role_val) if isinstance(role_val, str) else role_val
                        except Exception:
                            role_enum = UserRole.VIEWER
                        obj = SimpleNamespace(
                            id=int(r["id"]),
                            username=r["username"],
                            email=r["email"],
                            password_hash=r.get("password_hash"),
                            full_name=r.get("full_name"),
                            department=r.get("department"),
                            role=role_enum,
                            is_active=bool(r.get("is_active", 1)),
                            created_at=r.get("created_at"),
                            updated_at=r.get("updated_at"),
                        )
                        items.append(obj)
            finally:
                conn.close()
            return items

    async def create(self, data: UserCreate) -> User:
        user = User(
            username=data.username,
            email=data.email,
            password_hash=data.password,  # 需在路由层处理为hash
            full_name=data.full_name,
            department=data.department,
            role=UserRole[data.role] if isinstance(data.role, str) else data.role,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        await self.db.commit()
        return user

    async def update_user(self, user_id: int, data: UserUpdate) -> Optional[User]:
        stmt = update(User).where(User.id == user_id).values(
            full_name=data.full_name,
            department=data.department,
            role=data.role,
            is_active=data.is_active,
        ).returning(User)
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def update_password(self, user_id: int, password_hash: str) -> None:
        stmt = update(User).where(User.id == user_id).values(password_hash=password_hash)
        await self.db.execute(stmt)
        await self.db.commit()

    async def delete_user(self, user_id: int) -> None:
        stmt = delete(User).where(User.id == user_id)
        await self.db.execute(stmt)
        await self.db.commit()