"""
数据源管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import DataResponse, PaginatedResponse, PaginationInfo
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceTestResponse,
    TableSyncResponse,
    DataTableResponse,
    TableColumnResponse,
)
from app.services.data_source import DataSourceService
# 暂时不做鉴权，移除 require_admin 与 require_analyst 依赖

router = APIRouter()


@router.post("/", response_model=DataResponse[DataSourceResponse])
async def create_data_source(
    payload: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    ds = await service.create(payload)
    return DataResponse(data=DataSourceResponse.from_orm(ds), message="创建数据源成功")


@router.get("/", response_model=PaginatedResponse[DataSourceResponse])
async def list_data_sources(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    items = await service.list(limit=limit, offset=offset)
    return PaginatedResponse(
        data=[DataSourceResponse.from_orm(i) for i in items],
        pagination=PaginationInfo(limit=limit, offset=offset, total=len(items)),
        message="获取数据源列表成功",
    )


@router.get("/{ds_id}/tables", response_model=PaginatedResponse[DataTableResponse])
async def list_tables_by_data_source(
    ds_id: int,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """列出指定数据源下的表（包含字段列表）。"""
    service = DataSourceService(db)
    tables = await service.list_tables(ds_id=ds_id, limit=limit, offset=offset)
    # 手动组装响应以包含字段
    data: list[DataTableResponse] = []
    for t in tables:
        cols = await service.list_columns(table_id=t.id)
        data.append(DataTableResponse(
            id=t.id,
            data_source_id=t.data_source_id,
            table_name=t.table_name,
            display_name=t.display_name,
            description=t.description,
            category=t.category,
            tags=t.tags,
            row_count=t.row_count or 0,
            size_mb=t.size_mb,
            last_updated=t.last_updated,
            is_active=t.is_active,
            columns=[TableColumnResponse.from_orm(c) for c in cols]
        ))
    return PaginatedResponse(
        data=data,
        pagination=PaginationInfo(limit=limit, offset=offset, total=len(data)),
        message="获取数据表列表成功",
    )


@router.get("/tables/{table_id}/columns", response_model=DataResponse[list[TableColumnResponse]])
async def list_columns_by_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
):
    """列出指定数据表的字段。"""
    service = DataSourceService(db)
    cols = await service.list_columns(table_id=table_id)
    return DataResponse(data=[TableColumnResponse.from_orm(c) for c in cols], message="获取字段列表成功")


@router.get("/{ds_id}", response_model=DataResponse[DataSourceResponse])
async def get_data_source(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    ds = await service.get(ds_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    return DataResponse(data=DataSourceResponse.from_orm(ds), message="获取数据源成功")


@router.patch("/{ds_id}", response_model=DataResponse[DataSourceResponse])
async def update_data_source(
    ds_id: int,
    payload: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    ds = await service.update(ds_id, payload)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    return DataResponse(data=DataSourceResponse.from_orm(ds), message="更新数据源成功")


@router.delete("/{ds_id}", response_model=DataResponse[dict])
async def delete_data_source(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    await service.delete(ds_id)
    return DataResponse(data={"success": True}, message="删除数据源成功")


@router.post("/{ds_id}/test-connection", response_model=DataResponse[DataSourceTestResponse])
async def test_connection(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    ds = await service.get(ds_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    ok, msg = await service.test_connection(ds)
    return DataResponse(data=DataSourceTestResponse(success=ok, message=msg), message="连接测试完成")


@router.post("/{ds_id}/sync-tables", response_model=DataResponse[TableSyncResponse])
async def sync_tables(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = DataSourceService(db)
    ds = await service.get(ds_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    tables_count, columns_count = await service.sync_tables(ds)
    return DataResponse(
        data=TableSyncResponse(tables_synced=tables_count, columns_synced=columns_count),
        message="表结构同步完成",
    )