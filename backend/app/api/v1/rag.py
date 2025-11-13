"""
RAG 文档管理与查询 API
"""
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Query
from loguru import logger

from app.schemas.common import ErrorResponse
from app.schemas.rag import (
    RAGUpsertRequest,
    RAGUpsertResponse,
    RAGUpsertResult,
    RAGSearchResponse,
    RAGChunk,
)
from app.services.rag import RAGService


router = APIRouter()


@router.get('/search', response_model=RAGSearchResponse)
def search_documents(q: str = Query(..., description="查询关键词"), top_k: int = Query(4, ge=1, le=20, description="返回片段数")):
    try:
        rag = RAGService()
        chunks = rag.query(q, top_k=top_k)
        logger.info("RAG API 搜索: q_len={}, top_k={}, 返回数量={}", len(q or ''), top_k, len(chunks))
        # 映射为模型
        data: List[RAGChunk] = [RAGChunk(text=c.get('text', ''), source=c.get('source')) for c in chunks]
        return RAGSearchResponse(success=True, message="ok", code=200, data=data)
    except Exception as e:
        logger.exception("RAG API 搜索异常: {}", e)
        return ErrorResponse(message=str(e))


@router.post('/documents', response_model=RAGUpsertResponse)
def upsert_documents(payload: RAGUpsertRequest):
    try:
        docs = []
        for d in payload.documents:
            doc_id = d.id or str(uuid4())
            docs.append({
                'id': doc_id,
                'text': d.text,
                'source': d.source or 'unknown'
            })
        rag = RAGService()
        rag.upsert_documents(docs)
        logger.info("RAG API 写入: count={}, 示例ids={}", len(docs), [x['id'] for x in docs[:3]])
        return RAGUpsertResponse(success=True, message="ok", code=200, data=RAGUpsertResult(inserted_count=len(docs)))
    except Exception as e:
        logger.exception("RAG API 写入异常: {}", e)
        return ErrorResponse(message=str(e))