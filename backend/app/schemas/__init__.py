"""
Pydantic schemas包初始化
"""
from .user import UserCreate, UserUpdate, UserResponse, UserLogin
from .data_source import (
    DataSourceCreate, DataSourceUpdate, DataSourceResponse,
    DataTableResponse, TableColumnResponse
)
from .query import (
    QueryRequest, QueryResponse, QueryHistoryResponse,
    QueryTemplateCreate, QueryTemplateResponse
)
from .ai import (
    AIQueryRequest, AIQueryResponse, ConversationResponse,
    MessageResponse
)
from .common import BaseResponse, PaginatedResponse

__all__ = [
    # 用户相关
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin",
    
    # 数据源相关
    "DataSourceCreate", "DataSourceUpdate", "DataSourceResponse",
    "DataTableResponse", "TableColumnResponse",
    
    # 查询相关
    "QueryRequest", "QueryResponse", "QueryHistoryResponse",
    "QueryTemplateCreate", "QueryTemplateResponse",
    
    # AI相关
    "AIQueryRequest", "AIQueryResponse", "ConversationResponse",
    "MessageResponse",
    
    # 通用
    "BaseResponse", "PaginatedResponse"
]