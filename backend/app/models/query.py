"""
查询相关模型
"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Enum, 
    Text, Integer, ForeignKey, JSON, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class QueryStatus(str, enum.Enum):
    """查询状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class QueryHistory(Base):
    """查询历史表"""
    __tablename__ = "aitt_query_history"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="查询ID")
    user_id = Column(BigInteger, ForeignKey("aitt_users.id"), nullable=False, comment="用户ID")
    query_name = Column(String(200), comment="查询名称")
    natural_language_query = Column(Text, nullable=False, comment="自然语言查询")
    generated_sql = Column(Text, nullable=False, comment="生成的SQL")
    executed_sql = Column(Text, comment="实际执行的SQL")
    query_result = Column(JSON, comment="查询结果")
    execution_time_ms = Column(Integer, comment="执行时间毫秒")
    row_count = Column(Integer, comment="结果行数")
    status = Column(Enum(QueryStatus), nullable=False, comment="执行状态")
    error_message = Column(Text, comment="错误信息")
    is_saved = Column(Boolean, default=False, comment="是否保存")
    is_shared = Column(Boolean, default=False, comment="是否分享")
    tags = Column(JSON, comment="标签")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    user = relationship("User", back_populates="query_histories")
    
    # 索引
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
        Index("idx_is_saved", "is_saved"),
        Index("idx_is_shared", "is_shared"),
    )
    
    def __repr__(self):
        return f"<QueryHistory(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class QueryTemplate(Base):
    """查询模板表"""
    __tablename__ = "aitt_query_templates"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="模板ID")
    name = Column(String(200), nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    category = Column(String(50), comment="分类")
    natural_language_template = Column(Text, nullable=False, comment="自然语言模板")
    sql_template = Column(Text, nullable=False, comment="SQL模板")
    parameters = Column(JSON, comment="参数定义")
    usage_count = Column(Integer, default=0, comment="使用次数")
    is_public = Column(Boolean, default=False, comment="是否公开")
    created_by = Column(BigInteger, ForeignKey("aitt_users.id"), nullable=False, comment="创建人")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    creator = relationship("User", back_populates="created_templates")
    
    # 索引
    __table_args__ = (
        Index("idx_name", "name"),
        Index("idx_category", "category"),
        Index("idx_is_public", "is_public"),
        Index("idx_created_by", "created_by"),
    )
    
    def __repr__(self):
        return f"<QueryTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"