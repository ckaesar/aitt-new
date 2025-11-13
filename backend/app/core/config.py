"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用设置"""
    
    # 基本应用配置
    APP_NAME: str = Field(default="AI智能自助取数平台", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    DEBUG: bool = Field(default=True, description="调试模式")
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    
    # API配置
    API_V1_STR: str = Field(default="/api/v1", description="API版本前缀")
    
    # 数据库配置
    DATABASE_URL: str = Field(
        # 切换为MySQL异步驱动（aiomysql），默认指向提供的服务器
        # 如需修改库名或账号密码，建议通过 .env 覆盖
        default="mysql+aiomysql://mathapp:MathApp2024@localhost:3306/smart_finance_area?charset=utf8mb4",
        description="数据库连接URL"
    )
    
    # Redis配置
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    
    # JWT配置
    SECRET_KEY: str = Field(
        default="your_secret_key_here_change_in_production",
        description="JWT密钥"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="访问令牌过期时间（分钟）")

    # 鉴权开关（开发阶段可禁用鉴权快速打通前后端）
    AUTH_DISABLED: bool = Field(default=True, description="是否临时禁用鉴权（开发模式）")
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
        ],
        description="允许的跨域源"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "*"],
        description="允许的主机"
    )
    
    # AI模型配置
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API密钥")
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API基础URL"
    )
    AI_MODEL_NAME: str = Field(default="gpt-4", description="AI模型名称")
    
    # 查询配置
    MAX_QUERY_ROWS: int = Field(default=1000, description="查询结果最大行数")
    QUERY_TIMEOUT_SECONDS: int = Field(default=30, description="查询超时时间（秒）")
    ENABLE_QUERY_CACHE: bool = Field(default=True, description="是否启用查询缓存")
    CACHE_EXPIRE_MINUTES: int = Field(default=60, description="缓存过期时间（分钟）")
    
    # ChromaDB配置
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="./chroma_db",
        description="ChromaDB持久化目录"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="query_embeddings",
        description="ChromaDB集合名称"
    )
    # 元数据（数据源/表/字段）索引集合名称
    CHROMA_METADATA_COLLECTION_NAME: str = Field(
        default="metadata_embeddings",
        description="ChromaDB用于元数据语义检索的集合名称"
    )
    
    # 文件上传配置
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="最大文件大小（字节）")
    UPLOAD_DIR: str = Field(default="./uploads", description="文件上传目录")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()


def get_database_url() -> str:
    """获取数据库连接URL"""
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """获取Redis连接URL"""
    return settings.REDIS_URL