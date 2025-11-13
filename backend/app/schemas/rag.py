"""
RAG 文档管理与查询相关的请求/响应模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field

from .common import DataResponse


class RAGDocument(BaseModel):
    """表示一个可存储到 ChromaDB 的文档片段"""
    id: Optional[str] = Field(default=None, description="文档ID，不填则由后端生成")
    text: str = Field(..., description="文档正文内容")
    source: Optional[str] = Field(default=None, description="文档来源或标签")


class RAGUpsertRequest(BaseModel):
    """批量新增或更新文档片段请求"""
    documents: List[RAGDocument] = Field(..., description="文档片段列表")


class RAGUpsertResult(BaseModel):
    """返回写入数量统计"""
    inserted_count: int = Field(..., description="成功写入的文档数量")


class RAGChunk(BaseModel):
    """查询返回的文档片段"""
    text: str = Field(..., description="片段文本")
    source: Optional[str] = Field(default=None, description="片段来源")


class RAGSearchResponse(DataResponse[List[RAGChunk]]):
    """RAG 搜索返回：data 为片段列表"""
    pass


class RAGUpsertResponse(DataResponse[RAGUpsertResult]):
    """RAG 写入返回：data 为写入统计"""
    pass