"""
系统配置和审计日志模型
"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Enum, 
    Text, ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ConfigType(str, enum.Enum):
    """配置类型枚举"""
    SYSTEM = "system"
    AI = "ai"
    SECURITY = "security"
    PERFORMANCE = "performance"


class AuditAction(str, enum.Enum):
    """审计操作枚举"""
    LOGIN = "login"
    LOGOUT = "logout"
    QUERY = "query"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "aitt_system_configs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="配置ID")
    config_key = Column(String(100), nullable=False, unique=True, comment="配置键")
    config_value = Column(Text, comment="配置值")
    config_type = Column(Enum(ConfigType), nullable=False, comment="配置类型")
    description = Column(Text, comment="配置描述")
    is_encrypted = Column(Boolean, default=False, comment="是否加密")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 索引
    __table_args__ = (
        Index("idx_config_key", "config_key"),
        Index("idx_config_type", "config_type"),
        Index("idx_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<SystemConfig(id={self.id}, config_key='{self.config_key}', config_type='{self.config_type}')>"


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "aitt_audit_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="日志ID")
    user_id = Column(BigInteger, ForeignKey("aitt_users.id"), comment="用户ID")
    action = Column(Enum(AuditAction), nullable=False, comment="操作类型")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(BigInteger, comment="资源ID")
    details = Column(JSON, comment="操作详情")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    session_id = Column(String(100), comment="会话ID")
    success = Column(Boolean, default=True, comment="是否成功")
    error_message = Column(Text, comment="错误信息")
    execution_time_ms = Column(BigInteger, comment="执行时间毫秒")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    user = relationship("User")
    
    # 索引
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_action", "action"),
        Index("idx_resource", "resource_type", "resource_id"),
        Index("idx_created_at", "created_at"),
        Index("idx_success", "success"),
        Index("idx_ip_address", "ip_address"),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', success={self.success})>"