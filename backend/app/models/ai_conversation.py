"""
AI对话相关模型
"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Enum, 
    Text, ForeignKey, JSON, Index, Integer
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.query import QueryStatus


class ConversationStatus(str, enum.Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AIConversation(Base):
    """AI对话表"""
    __tablename__ = "aitt_ai_conversations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="对话ID")
    user_id = Column(BigInteger, ForeignKey("aitt_users.id"), nullable=False, comment="用户ID")
    title = Column(String(200), comment="对话标题")
    context = Column(JSON, comment="对话上下文")
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE, comment="对话状态")
    total_messages = Column(BigInteger, default=0, comment="消息总数")
    total_tokens = Column(BigInteger, default=0, comment="Token总数")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<AIConversation(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class AIMessage(Base):
    """AI消息表"""
    __tablename__ = "aitt_ai_messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="消息ID")
    conversation_id = Column(BigInteger, ForeignKey("aitt_ai_conversations.id"), nullable=False, comment="对话ID")
    role = Column(Enum(MessageRole), nullable=False, comment="消息角色")
    content = Column(Text, nullable=False, comment="消息内容")
    message_metadata = Column(JSON, comment="消息元数据")
    token_count = Column(BigInteger, default=0, comment="Token数量")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    conversation = relationship("AIConversation", back_populates="messages")
    
    # 索引
    __table_args__ = (
        Index("idx_conversation_id", "conversation_id"),
        Index("idx_role", "role"),
        Index("idx_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<AIMessage(id={self.id}, conversation_id={self.conversation_id}, role='{self.role}')>"


class AICallLog(Base):
    """大模型调用日志表"""
    __tablename__ = "aitt_ai_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="日志ID")
    conversation_id = Column(BigInteger, ForeignKey("aitt_ai_conversations.id"), nullable=True, comment="关联会话ID")
    model_name = Column(String(100), nullable=True, comment="模型名称")
    endpoint = Column(String(100), nullable=True, comment="调用端点")
    prompt_tokens = Column(Integer, default=0, comment="提示词Token")
    completion_tokens = Column(Integer, default=0, comment="生成Token")
    total_tokens = Column(Integer, default=0, comment="总Token")
    latency_ms = Column(Integer, default=0, comment="调用耗时毫秒")
    use_rag = Column(Boolean, default=False, comment="是否启用RAG")
    rag_context_len = Column(Integer, default=0, comment="RAG上下文长度")
    metadata_context_len = Column(Integer, default=0, comment="元数据上下文长度")
    rag_chunks = Column(JSON, comment="检索片段")
    status = Column(Enum(QueryStatus), nullable=False, default=QueryStatus.SUCCESS, comment="调用状态")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关系
    conversation = relationship("AIConversation")

    # 索引
    __table_args__ = (
        Index("idx_model_name", "model_name"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<AICallLog(id={self.id}, model='{self.model_name}', status='{self.status}')>"