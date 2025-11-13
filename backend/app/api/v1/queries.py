"""
查询管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import DataResponse, PaginatedResponse, PaginationInfo
from app.schemas.query import (
    QueryTemplateCreate,
    QueryTemplateUpdate,
    QueryTemplateResponse,
    QueryHistoryResponse,
    QueryExecuteRequest,
    QueryResponse,
    QuerySaveRequest,
    QueryShareRequest,
)
from app.services.query import QueryService
from app.services.data_source import DataSourceService
# 暂时不做鉴权，移除用户依赖
from app.models.query import QueryStatus

router = APIRouter()


@router.post("/templates", response_model=DataResponse[QueryTemplateResponse])
async def create_template(
    payload: QueryTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    service = QueryService(db)
    # 暂时不做鉴权，使用0作为创建者占位
    tpl = await service.create_template(payload, created_by=0)
    return DataResponse(data=QueryTemplateResponse.from_orm(tpl), message="创建模板成功")


@router.get("/templates", response_model=PaginatedResponse[QueryTemplateResponse])
async def list_templates(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = QueryService(db)
    try:
        items = await service.list_templates(limit=limit, offset=offset)
        data: list[QueryTemplateResponse] = []
        for i in items:
            params_val = getattr(i, "parameters", None)
            if isinstance(params_val, str):
                try:
                    import json
                    params_val = json.loads(params_val)
                except Exception:
                    params_val = None
            data.append(
                QueryTemplateResponse(
                    id=int(getattr(i, "id")),
                    name=str(getattr(i, "name")),
                    description=getattr(i, "description", None),
                    category=getattr(i, "category", None),
                    natural_language_template=str(getattr(i, "natural_language_template")),
                    sql_template=str(getattr(i, "sql_template")),
                    parameters=params_val,
                    is_public=bool(getattr(i, "is_public", False)),
                    usage_count=int(getattr(i, "usage_count", 0) or 0),
                    created_by=int(getattr(i, "created_by", 0)),
                    created_at=getattr(i, "created_at"),
                    updated_at=getattr(i, "updated_at"),
                )
            )
        return PaginatedResponse(
            data=data,
            pagination=PaginationInfo(limit=limit, offset=offset, total=len(data)),
            message="获取模板列表成功",
        )
    except Exception as e:
        return PaginatedResponse(
            data=[],
            pagination=PaginationInfo(limit=limit, offset=offset, total=0),
            message=f"获取模板列表失败（已降级为空列表）：{e}",
        )


@router.patch("/templates/{tpl_id}", response_model=DataResponse[QueryTemplateResponse])
async def update_template(
    tpl_id: int,
    payload: QueryTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = QueryService(db)
    tpl = await service.update_template(tpl_id, payload)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return DataResponse(data=QueryTemplateResponse.from_orm(tpl), message="更新模板成功")


@router.delete("/templates/{tpl_id}", response_model=DataResponse[dict])
async def delete_template(
    tpl_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = QueryService(db)
    await service.delete_template(tpl_id)
    return DataResponse(data={"success": True}, message="删除模板成功")


@router.get("/history", response_model=PaginatedResponse[QueryHistoryResponse])
async def list_history(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
):
    service = QueryService(db)
    offset = (page - 1) * page_size
    items = await service.list_history_all(limit=page_size, offset=offset)
    try:
        total = await service.count_history_all()
    except Exception:
        # 若统计失败，则用当前返回条数兜底
        total = len(items)
    total_pages = (total + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1
    return PaginatedResponse(
        data=[QueryHistoryResponse.from_orm(i) for i in items],
        pagination=PaginationInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        ),
        message="获取查询历史成功",
    )


@router.get("/history/{history_id}", response_model=DataResponse[QueryHistoryResponse])
async def get_history(
    history_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = QueryService(db)
    item = await service.get_history(history_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="历史记录不存在")
    return DataResponse(data=QueryHistoryResponse.from_orm(item), message="获取历史记录成功")


@router.post("/execute", response_model=DataResponse[QueryResponse])
async def execute_query(
    payload: QueryExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    qs = QueryService(db)
    ds_service = DataSourceService(db)
    ds = await ds_service.get(payload.data_source_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    import time
    start = time.perf_counter()
    try:
        rows, columns = await ds_service.execute_sql(
            ds,
            payload.sql,
            max_rows=payload.max_rows or 1000,
            timeout_seconds=payload.timeout_seconds or 30,
        )
        exec_ms = int((time.perf_counter() - start) * 1000)
        item = await qs.create_history(
            user_id=0,
            natural_language_query="",
            generated_sql=payload.sql,
            status=QueryStatus.SUCCESS,
            execution_time_ms=exec_ms,
            row_count=len(rows),
            error_message=None,
            is_saved=True,
            tags=["execute"],
            executed_sql=payload.sql,
        )
        # 构造包含数据与列的响应
        resp = QueryResponse(
            query_id=item.id,
            natural_language_query=item.natural_language_query or "",
            generated_sql=item.generated_sql,
            executed_sql=payload.sql,
            status=QueryStatus.SUCCESS,
            execution_time_ms=exec_ms,
            row_count=len(rows),
            columns=[{"name": c} for c in columns],
            data=rows,
            error_message=None,
            created_at=item.created_at,
        )
        return DataResponse(data=resp, message="执行成功")
    except Exception as e:
        exec_ms = int((time.perf_counter() - start) * 1000)
        item = await qs.create_history(
            user_id=0,
            natural_language_query="",
            generated_sql=payload.sql,
            status=QueryStatus.ERROR,
            execution_time_ms=exec_ms,
            row_count=0,
            error_message=str(e),
            is_saved=True,
            tags=["execute_error"],
            executed_sql=payload.sql,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"执行失败: {e}")


@router.post("/save", response_model=DataResponse[QueryHistoryResponse])
async def save_query(
    payload: QuerySaveRequest,
    db: AsyncSession = Depends(get_db),
):
    qs = QueryService(db)
    item = await qs.get_history(payload.query_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="历史记录不存在")
    updated = await qs.save_history(history_id=payload.query_id, query_name=payload.query_name, tags=payload.tags)
    return DataResponse(data=QueryHistoryResponse.from_orm(updated), message="保存查询成功")


@router.post("/share", response_model=DataResponse[QueryHistoryResponse])
async def share_query(
    payload: QueryShareRequest,
    db: AsyncSession = Depends(get_db),
):
    qs = QueryService(db)
    item = await qs.get_history(payload.query_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="历史记录不存在")
    updated = await qs.share_history(history_id=payload.query_id, is_shared=payload.is_shared)
    return DataResponse(data=QueryHistoryResponse.from_orm(updated), message="分享状态更新成功")