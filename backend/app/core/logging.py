"""
日志配置
"""
import sys
import os
from loguru import logger
from app.core.config import settings


def setup_logging():
    """设置日志配置"""
    # 尝试将控制台标准输出/错误输出设置为 UTF-8，避免中文日志在控制台乱码
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        # 某些运行环境可能不支持 reconfigure（如旧版解释器或特殊终端），忽略即可
        pass

    # 确保日志目录存在
    try:
        os.makedirs("logs", exist_ok=True)
    except Exception:
        # 目录创建失败不阻塞服务启动，仍允许控制台输出
        pass
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )
    
    # 添加文件输出
    logger.add(
        "logs/app.log",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )
    
    # 添加错误日志文件
    logger.add(
        "logs/error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )


def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return logger.bind(name=name)
    return logger