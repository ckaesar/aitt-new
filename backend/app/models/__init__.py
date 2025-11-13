"""模型包初始化"""
from .user import User, UserRole
from .data_source import DataSource, DataTable, TableColumn, DataSourceType
from .query import QueryHistory, QueryTemplate, QueryStatus
from .permission import Permission, PermissionType, PermissionAction
from .ai_conversation import AIConversation, AIMessage, ConversationStatus, MessageRole
from .system import SystemConfig, AuditLog, ConfigType, AuditAction
from .metadata_sync import MetadataSyncSummary

__all__ = [
    # 用户相关
    "User", "UserRole",
    
    # 数据源相关
    "DataSource", "DataTable", "TableColumn", "DataSourceType",
    
    # 查询相关
    "QueryHistory", "QueryTemplate", "QueryStatus",
    
    # 权限相关
    "Permission", "PermissionType", "PermissionAction",
    
    # AI对话相关
    "AIConversation", "AIMessage", "ConversationStatus", "MessageRole",
    
    # 系统相关
    "SystemConfig", "AuditLog", "ConfigType", "AuditAction",

    # 元数据同步摘要
    "MetadataSyncSummary",
]