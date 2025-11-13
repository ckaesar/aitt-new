"""
通用响应schemas
"""
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("", description="响应消息")
    code: int = Field(200, description="响应码")
    
    class Config:
        from_attributes = True


class DataResponse(BaseResponse, Generic[T]):
    """数据响应模型"""
    data: Optional[T] = Field(None, description="响应数据")


class PaginationInfo(BaseModel):
    """分页信息"""
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页大小")
    total: int = Field(0, description="总记录数")
    total_pages: int = Field(0, description="总页数")
    has_next: bool = Field(False, description="是否有下一页")
    has_prev: bool = Field(False, description="是否有上一页")


class PaginatedResponse(BaseResponse, Generic[T]):
    """分页响应模型"""
    data: List[T] = Field([], description="数据列表")
    pagination: PaginationInfo = Field(description="分页信息")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = Field(False)
    error_type: Optional[str] = Field(None, description="错误类型")
    error_details: Optional[dict] = Field(None, description="错误详情")


class ValidationErrorResponse(ErrorResponse):
    """验证错误响应模型"""
    validation_errors: List[dict] = Field([], description="验证错误列表")