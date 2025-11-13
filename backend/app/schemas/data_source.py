"""
数据源相关schemas
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from app.models.data_source import DataSourceType


class DataSourceBase(BaseModel):
    """数据源基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    type: DataSourceType = Field(..., description="数据源类型")
    host: str = Field(..., min_length=1, max_length=255, description="主机地址")
    port: int = Field(..., ge=1, le=65535, description="端口")
    database_name: str = Field(..., min_length=1, max_length=100, description="数据库名")
    username: Optional[str] = Field(None, max_length=100, description="用户名")
    description: Optional[str] = Field(None, description="描述")


class DataSourceCreate(DataSourceBase):
    """创建数据源模型"""
    password: Optional[str] = Field(None, description="密码")


class DataSourceUpdate(BaseModel):
    """更新数据源模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="数据源名称")
    host: Optional[str] = Field(None, min_length=1, max_length=255, description="主机地址")
    port: Optional[int] = Field(None, ge=1, le=65535, description="端口")
    database_name: Optional[str] = Field(None, min_length=1, max_length=100, description="数据库名")
    username: Optional[str] = Field(None, max_length=100, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[bool] = Field(None, description="是否激活")


class DataSourceResponse(DataSourceBase):
    """数据源响应模型"""
    id: int = Field(..., description="数据源ID")
    is_active: bool = Field(..., description="是否激活")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class TableColumnResponse(BaseModel):
    """表字段响应模型"""
    id: int = Field(..., description="字段ID")
    column_name: str = Field(..., description="字段名")
    display_name: Optional[str] = Field(None, description="显示名称")
    data_type: str = Field(..., description="数据类型")
    is_nullable: bool = Field(..., description="是否可空")
    default_value: Optional[str] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="字段描述")
    is_dimension: bool = Field(..., description="是否维度")
    is_metric: bool = Field(..., description="是否指标")
    is_primary_key: bool = Field(..., description="是否主键")
    is_foreign_key: bool = Field(..., description="是否外键")
    column_order: int = Field(..., description="字段顺序")
    
    class Config:
        from_attributes = True


class DataTableResponse(BaseModel):
    """数据表响应模型"""
    id: int = Field(..., description="表ID")
    data_source_id: int = Field(..., description="数据源ID")
    table_name: str = Field(..., description="表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="表描述")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    row_count: int = Field(..., description="行数")
    size_mb: Optional[Decimal] = Field(None, description="大小MB")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    is_active: bool = Field(..., description="是否激活")
    columns: List[TableColumnResponse] = Field([], description="字段列表")
    
    class Config:
        from_attributes = True


class DataSourceTestRequest(BaseModel):
    """数据源测试连接请求"""
    type: DataSourceType = Field(..., description="数据源类型")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口")
    database_name: str = Field(..., description="数据库名")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")


class DataSourceTestResponse(BaseModel):
    """数据源测试连接响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="测试结果消息")
    connection_time_ms: Optional[int] = Field(None, description="连接时间毫秒")


class TableSyncRequest(BaseModel):
    """表同步请求"""
    data_source_id: int = Field(..., description="数据源ID")
    table_names: Optional[List[str]] = Field(None, description="指定同步的表名列表，为空则同步所有表")


class TableSyncResponse(BaseModel):
    """表同步响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="同步结果消息")
    synced_tables: int = Field(..., description="同步的表数量")
    synced_columns: int = Field(..., description="同步的字段数量")
    errors: List[str] = Field([], description="错误信息列表")