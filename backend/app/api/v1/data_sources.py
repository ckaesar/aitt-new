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
from app.models.data_source import DataSourceType
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
    """
    列出数据源，兼容底层返回的 ORM 模型或字典对象，并强制布尔字段为有效值。
    """
    service = DataSourceService(db)
    items = await service.list(limit=limit, offset=offset)
    data: list[DataSourceResponse] = []
    for i in items:
        # 兼容枚举字段类型
        try:
            ds_type = i.type if hasattr(i, "type") else None
            if ds_type is None:
                ds_type = None
            elif isinstance(ds_type, DataSourceType):
                pass
            else:
                ds_type = DataSourceType(str(ds_type))
        except Exception:
            ds_type = DataSourceType.MYSQL

        data.append(
            DataSourceResponse(
                id=int(getattr(i, "id")),
                name=str(getattr(i, "name")),
                type=ds_type,
                host=str(getattr(i, "host")),
                port=int(getattr(i, "port")),
                database_name=str(getattr(i, "database_name")),
                username=getattr(i, "username", None),
                description=getattr(i, "description", None),
                is_active=bool(getattr(i, "is_active", True)),
                created_by=int(getattr(i, "created_by", 0)),
                created_at=getattr(i, "created_at"),
                updated_at=getattr(i, "updated_at"),
            )
        )

    return PaginatedResponse(
        data=data,
        pagination=PaginationInfo(limit=limit, offset=offset, total=len(data)),
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
        safe_cols: list[TableColumnResponse] = []
        for c in cols:
            safe_cols.append(
                TableColumnResponse(
                    id=int(getattr(c, "id")),
                    column_name=str(getattr(c, "column_name")),
                    display_name=getattr(c, "display_name", None),
                    data_type=str(getattr(c, "data_type")),
                    is_nullable=bool(getattr(c, "is_nullable", True)),
                    default_value=getattr(c, "default_value", None),
                    description=getattr(c, "description", None),
                    is_dimension=bool(getattr(c, "is_dimension", False)),
                    is_metric=bool(getattr(c, "is_metric", False)),
                    is_primary_key=bool(getattr(c, "is_primary_key", False)),
                    is_foreign_key=bool(getattr(c, "is_foreign_key", False)),
                    column_order=int(getattr(c, "column_order", 0)),
                )
            )
        data.append(
            DataTableResponse(
                id=int(getattr(t, "id")),
                data_source_id=int(getattr(t, "data_source_id")),
                table_name=str(getattr(t, "table_name")),
                display_name=getattr(t, "display_name", None),
                description=getattr(t, "description", None),
                category=getattr(t, "category", None),
                tags=getattr(t, "tags", None),
                row_count=int(getattr(t, "row_count", 0) or 0),
                size_mb=getattr(t, "size_mb", None),
                last_updated=getattr(t, "last_updated", None),
                is_active=bool(getattr(t, "is_active", True)),
                columns=safe_cols,
            )
        )
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
    safe_cols: list[TableColumnResponse] = []
    for c in cols:
        safe_cols.append(
            TableColumnResponse(
                id=int(getattr(c, "id")),
                column_name=str(getattr(c, "column_name")),
                display_name=getattr(c, "display_name", None),
                data_type=str(getattr(c, "data_type")),
                is_nullable=bool(getattr(c, "is_nullable", True)),
                default_value=getattr(c, "default_value", None),
                description=getattr(c, "description", None),
                is_dimension=bool(getattr(c, "is_dimension", False)),
                is_metric=bool(getattr(c, "is_metric", False)),
                is_primary_key=bool(getattr(c, "is_primary_key", False)),
                is_foreign_key=bool(getattr(c, "is_foreign_key", False)),
                column_order=int(getattr(c, "column_order", 0)),
            )
        )
    return DataResponse(data=safe_cols, message="获取字段列表成功")


@router.get("/{ds_id}", response_model=DataResponse[DataSourceResponse])
async def get_data_source(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个数据源，确保布尔字段有效，兼容 ORM 或字典对象。
    """
    service = DataSourceService(db)
    ds = await service.get(ds_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")

    try:
        ds_type = ds.type if isinstance(getattr(ds, "type", None), DataSourceType) else DataSourceType(str(getattr(ds, "type")))
    except Exception:
        ds_type = DataSourceType.MYSQL

    resp = DataSourceResponse(
        id=int(getattr(ds, "id")),
        name=str(getattr(ds, "name")),
        type=ds_type,
        host=str(getattr(ds, "host")),
        port=int(getattr(ds, "port")),
        database_name=str(getattr(ds, "database_name")),
        username=getattr(ds, "username", None),
        description=getattr(ds, "description", None),
        is_active=bool(getattr(ds, "is_active", True)),
        created_by=int(getattr(ds, "created_by", 0)),
        created_at=getattr(ds, "created_at"),
        updated_at=getattr(ds, "updated_at"),
    )
    return DataResponse(data=resp, message="获取数据源成功")


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