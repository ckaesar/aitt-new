"""
查询相关schemas
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.query import QueryStatus


class QueryRequest(BaseModel):
    """查询请求模型"""
    natural_language_query: str = Field(..., min_length=1, description="自然语言查询")
    data_source_id: Optional[int] = Field(None, description="指定数据源ID")
    max_rows: Optional[int] = Field(1000, ge=1, le=10000, description="最大返回行数")
    timeout_seconds: Optional[int] = Field(30, ge=1, le=300, description="超时时间秒")
    save_query: Optional[bool] = Field(False, description="是否保存查询")
    query_name: Optional[str] = Field(None, max_length=200, description="查询名称")


class QueryResponse(BaseModel):
    """查询响应模型"""
    query_id: int = Field(..., description="查询ID")
    natural_language_query: str = Field(..., description="自然语言查询")
    generated_sql: str = Field(..., description="生成的SQL")
    executed_sql: Optional[str] = Field(None, description="实际执行的SQL")
    status: QueryStatus = Field(..., description="执行状态")
    execution_time_ms: Optional[int] = Field(None, description="执行时间毫秒")
    row_count: Optional[int] = Field(None, description="结果行数")
    columns: List[Dict[str, Any]] = Field([], description="列信息")
    data: List[Dict[str, Any]] = Field([], description="查询结果数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")


class QueryHistoryResponse(BaseModel):
    """查询历史响应模型"""
    id: int = Field(..., description="查询ID")
    query_name: Optional[str] = Field(None, description="查询名称")
    natural_language_query: str = Field(..., description="自然语言查询")
    generated_sql: str = Field(..., description="生成的SQL")
    status: QueryStatus = Field(..., description="执行状态")
    execution_time_ms: Optional[int] = Field(None, description="执行时间毫秒")
    row_count: Optional[int] = Field(None, description="结果行数")
    is_saved: bool = Field(..., description="是否保存")
    is_shared: bool = Field(..., description="是否分享")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class QueryTemplateBase(BaseModel):
    """查询模板基础模型"""
    name: str = Field(..., min_length=1, max_length=200, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    natural_language_template: str = Field(..., min_length=1, description="自然语言模板")
    sql_template: str = Field(..., min_length=1, description="SQL模板")
    parameters: Optional[Dict[str, Any]] = Field(None, description="参数定义")
    is_public: bool = Field(False, description="是否公开")


class QueryTemplateCreate(QueryTemplateBase):
    """创建查询模板模型"""
    pass


class QueryTemplateUpdate(BaseModel):
    """更新查询模板模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    natural_language_template: Optional[str] = Field(None, min_length=1, description="自然语言模板")
    sql_template: Optional[str] = Field(None, min_length=1, description="SQL模板")
    parameters: Optional[Dict[str, Any]] = Field(None, description="参数定义")
    is_public: Optional[bool] = Field(None, description="是否公开")


class QueryTemplateResponse(QueryTemplateBase):
    """查询模板响应模型"""
    id: int = Field(..., description="模板ID")
    usage_count: int = Field(..., description="使用次数")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class QueryExecuteRequest(BaseModel):
    """执行查询请求模型"""
    sql: str = Field(..., min_length=1, description="SQL语句")
    data_source_id: int = Field(..., description="数据源ID")
    max_rows: Optional[int] = Field(1000, ge=1, le=10000, description="最大返回行数")
    timeout_seconds: Optional[int] = Field(30, ge=1, le=300, description="超时时间秒")


class QuerySaveRequest(BaseModel):
    """保存查询请求模型"""
    query_id: int = Field(..., description="查询ID")
    query_name: str = Field(..., min_length=1, max_length=200, description="查询名称")
    tags: Optional[List[str]] = Field(None, description="标签")


class QueryShareRequest(BaseModel):
    """分享查询请求模型"""
    query_id: int = Field(..., description="查询ID")
    is_shared: bool = Field(..., description="是否分享")