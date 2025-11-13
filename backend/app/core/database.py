"""
数据库连接和会话管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from typing import AsyncGenerator
from loguru import logger

from app.core.config import settings


# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,  # 使用NullPool避免连接池问题
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 创建Redis连接池
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=100
)


class Base(DeclarativeBase):
    """数据库模型基类"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话
    说明：在当前环境缺失 greenlet 的情况下，SQLAlchemy 的会话关闭可能抛出异常。
    改为手动创建/关闭，并在关闭失败时进行告警而不影响接口返回。
    """
    session = AsyncSessionLocal()
    try:
        # 仅提供会话，读操作无需在此统一提交；写操作请在业务层显式提交
        yield session
    finally:
        try:
            await session.close()
        except Exception as e:
            logger.warning(f"会话关闭失败（可能缺失greenlet），已忽略以保障接口可用: {e}")


async def get_redis() -> redis.Redis:
    """获取Redis连接"""
    return redis.Redis(connection_pool=redis_pool)


async def init_db():
    """初始化数据库"""
    try:
        async with engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表检查/创建完成")
    except Exception as e:
        # 在当前环境缺失greenlet等依赖时，允许跳过初始化以便服务先行启动
        logger.warning(f"数据库初始化跳过: {e}")


async def close_db():
    """关闭数据库连接"""
    try:
        await engine.dispose()
    except Exception as e:
        logger.warning(f"关闭数据库引擎失败: {e}")
    try:
        redis_pool.disconnect()
    except Exception as e:
        logger.warning(f"关闭Redis连接失败: {e}")