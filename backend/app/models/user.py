"""
用户模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    """用户表"""
    __tablename__ = "aitt_users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    full_name = Column(String(100), comment="全名")
    department = Column(String(100), comment="部门")
    role = Column(Enum(UserRole), default=UserRole.VIEWER, comment="角色")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    query_histories = relationship("QueryHistory", back_populates="user")
    # Permission 表存在两个指向 User 的外键（user_id 与 granted_by），需要指定 foreign_keys 避免歧义
    permissions = relationship(
        "Permission",
        back_populates="user",
        foreign_keys="Permission.user_id",
    )
    ai_conversations = relationship("AIConversation", back_populates="user")
    created_data_sources = relationship("DataSource", back_populates="creator")
    created_templates = relationship("QueryTemplate", back_populates="creator")
    
    # 索引
    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_email", "email"),
        Index("idx_role", "role"),
        Index("idx_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"