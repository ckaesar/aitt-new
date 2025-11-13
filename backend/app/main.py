"""FastAPI应用主入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os
import threading
import time

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import api_router
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.services.metadata_index import MetadataIndexer

# 初始化日志（确保文件日志和控制台日志均生效）
setup_logging()


_stop_event: threading.Event | None = None


def _metadata_sync_loop(stop_evt: threading.Event):
    """每小时执行一次元数据同步的后台线程。"""
    indexer = MetadataIndexer()
    # 首次启动后立即同步一次
    try:
        logger.info("后台任务: 立即执行首次元数据同步…")
        indexer.sync_all()
        logger.info("后台任务: 首次元数据同步完成")
    except Exception as e:
        logger.warning(f"后台任务: 首次元数据同步失败: {e}")
    # 循环执行
    while not stop_evt.is_set():
        # 等待一小时或被终止
        stop_evt.wait(3600)
        if stop_evt.is_set():
            break
        try:
            logger.info("后台任务: 每小时元数据同步开始…")
            indexer.sync_all()
            logger.info("后台任务: 每小时元数据同步完成")
        except Exception as e:
            logger.warning(f"后台任务: 每小时元数据同步失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("应用启动中...")
    # 运行时环境检查与提示
    try:
        env_name = os.environ.get("CONDA_DEFAULT_ENV", "")
        interp = sys.executable
        if env_name == "aitt-py311":
            logger.info("运行环境: Conda '{}'，解释器: {}", env_name, interp)
        else:
            logger.warning(
                "当前环境非 aitt-py311 (CONDA_DEFAULT_ENV='{}')，解释器: {}。建议使用 'conda run -n aitt-py311 uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level info' 统一环境。",
                env_name,
                interp,
            )
    except Exception:
        pass
    
    try:
        # 初始化数据库
        await init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    
    # 启动后台定时任务线程
    global _stop_event
    _stop_event = threading.Event()
    t = threading.Thread(target=_metadata_sync_loop, args=(_stop_event,), daemon=True)
    t.start()

    yield
    
    # 停止后台定时任务
    try:
        if _stop_event is not None:
            _stop_event.set()
        logger.info("后台定时任务已发出停止信号")
    except Exception:
        pass

    try:
        # 关闭数据库连接
        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局请求日志
app.add_middleware(RequestLoggingMiddleware)

# 挂载API路由（统一使用配置的版本前缀）
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": f"欢迎使用{settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": settings.APP_NAME}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )