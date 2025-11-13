"""
权限相关模型
"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Enum, 
    Text, ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class PermissionType(str, enum.Enum):
    """权限类型枚举"""
    TABLE = "table"
    COLUMN = "column"
    ROW = "row"


class PermissionAction(str, enum.Enum):
    """权限操作枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class Permission(Base):
    """权限表"""
    __tablename__ = "aitt_permissions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="权限ID")
    user_id = Column(BigInteger, ForeignKey("aitt_users.id"), nullable=False, comment="用户ID")
    resource_type = Column(Enum(PermissionType), nullable=False, comment="资源类型")
    resource_id = Column(BigInteger, nullable=False, comment="资源ID")
    action = Column(Enum(PermissionAction), nullable=False, comment="操作类型")
    conditions = Column(JSON, comment="权限条件")
    is_granted = Column(Boolean, default=True, comment="是否授权")
    granted_by = Column(BigInteger, ForeignKey("aitt_users.id"), comment="授权人")
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), comment="授权时间")
    expires_at = Column(DateTime(timezone=True), comment="过期时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], back_populates="permissions")
    granter = relationship("User", foreign_keys=[granted_by])
    
    # 索引和约束
    __table_args__ = (
        UniqueConstraint("user_id", "resource_type", "resource_id", "action", name="uk_user_resource_action"),
        Index("idx_user_id", "user_id"),
        Index("idx_resource", "resource_type", "resource_id"),
        Index("idx_action", "action"),
        Index("idx_is_granted", "is_granted"),
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, user_id={self.user_id}, resource_type='{self.resource_type}', action='{self.action}')>"