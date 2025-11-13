from typing import List, Optional

import pymysql
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import DataSource, DataSourceType, DataTable, TableColumn
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate
from app.utils.security import encrypt_secret, decrypt_secret, InvalidToken


class DataSourceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: DataSourceCreate) -> DataSource:
        # 加密保存密码（若提供）
        enc_pwd = encrypt_secret(payload.password) if payload.password else None
        ds = DataSource(
            name=payload.name,
            type=DataSourceType[payload.type] if isinstance(payload.type, str) else payload.type,
            host=payload.host,
            port=payload.port,
            database_name=payload.database_name,
            username=payload.username,
            password_encrypted=enc_pwd,
            description=payload.description,
            is_active=True,
        )
        self.db.add(ds)
        await self.db.flush()
        await self.db.refresh(ds)
        await self.db.commit()
        return ds

    async def update(self, ds_id: int, payload: DataSourceUpdate) -> Optional[DataSource]:
        # 加密保存密码（若提供）
        enc_pwd = encrypt_secret(payload.password) if payload.password else None
        stmt = (
            update(DataSource)
            .where(DataSource.id == ds_id)
            .values(
                name=payload.name,
                host=payload.host,
                port=payload.port,
                database_name=payload.database_name,
                username=payload.username,
                password_encrypted=enc_pwd,
                description=payload.description,
                is_active=payload.is_active,
            )
            .returning(DataSource)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def delete(self, ds_id: int) -> None:
        stmt = delete(DataSource).where(DataSource.id == ds_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def get(self, ds_id: int) -> Optional[DataSource]:
        """获取单个数据源。
        默认使用 ORM 异步查询；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步查询以保证接口可用。
        """
        try:
            stmt = select(DataSource).where(DataSource.id == ds_id)
            res = await self.db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception:
            # ORM 不可用（缺少 greenlet），降级为 PyMySQL 同步查询
            from pymysql.cursors import DictCursor
            from sqlalchemy.engine.url import make_url
            from app.core.config import settings

            url = make_url(settings.DATABASE_URL)
            conn = pymysql.connect(
                host=url.host or "localhost",
                port=int(url.port or 3306),
                user=url.username,
                password=url.password or "",
                database=url.database,
                charset="utf8mb4",
                cursorclass=DictCursor,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, name, type, host, port, database_name, username, password_encrypted,
                               description, is_active, created_by, created_at, updated_at
                        FROM aitt_data_sources
                        WHERE id = %s
                        """,
                        (ds_id,),
                    )
                    r = cur.fetchone()
                    if not r:
                        return None
                    from types import SimpleNamespace
                    try:
                        ds_type = (
                            DataSourceType(r["type"]) if isinstance(r.get("type"), str) else r.get("type")
                        )
                    except Exception:
                        t = str(r.get("type") or "").lower()
                        ds_type = DataSourceType(t) if t in (x.value for x in DataSourceType) else DataSourceType.MYSQL
                    obj = SimpleNamespace(
                        id=int(r["id"]),
                        name=r["name"],
                        type=ds_type,
                        host=r["host"],
                        port=int(r["port"]),
                        database_name=r["database_name"],
                        username=r.get("username"),
                        password_encrypted=r.get("password_encrypted"),
                        description=r.get("description"),
                        is_active=bool(r.get("is_active")),
                        created_by=int(r.get("created_by")),
                        created_at=r.get("created_at"),
                        updated_at=r.get("updated_at"),
                    )
                    return obj
            finally:
                conn.close()

    async def list(self, limit: int = 20, offset: int = 0) -> List[DataSource]:
        """列出数据源。
        默认使用 ORM 异步查询；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步查询以保证接口可用。
        """
        try:
            stmt = select(DataSource).order_by(DataSource.id).limit(limit).offset(offset)
            res = await self.db.execute(stmt)
            return list(res.scalars().all())
        except Exception:
            # ORM 不可用（缺少 greenlet），降级为 PyMySQL 同步查询
            import pymysql
            from pymysql.cursors import DictCursor
            from sqlalchemy.engine.url import make_url
            from app.core.config import settings

            url = make_url(settings.DATABASE_URL)
            conn = pymysql.connect(
                host=url.host or "localhost",
                port=int(url.port or 3306),
                user=url.username,
                password=url.password or "",
                database=url.database,
                charset="utf8mb4",
                cursorclass=DictCursor,
            )
            items: List[DataSource] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, name, type, host, port, database_name, username, password_encrypted,
                               description, is_active, created_by, created_at, updated_at
                        FROM aitt_data_sources
                        ORDER BY id
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                    rows = cur.fetchall()
                    from types import SimpleNamespace
                    for r in rows:
                        try:
                            ds_type = (
                                DataSourceType(r["type"]) if isinstance(r.get("type"), str) else r.get("type")
                            )
                        except Exception:
                            # 兼容可能的枚举名称大小写差异
                            t = str(r.get("type") or "").lower()
                            ds_type = DataSourceType(t) if t in (x.value for x in DataSourceType) else DataSourceType.MYSQL
                        obj = SimpleNamespace(
                            id=int(r["id"]),
                            name=r["name"],
                            type=ds_type,
                            host=r["host"],
                            port=int(r["port"]),
                            database_name=r["database_name"],
                            username=r.get("username"),
                            password_encrypted=r.get("password_encrypted"),
                            description=r.get("description"),
                            is_active=bool(r.get("is_active")),
                            created_by=int(r.get("created_by")),
                            created_at=r.get("created_at"),
                            updated_at=r.get("updated_at"),
                        )
                        items.append(obj)
            finally:
                conn.close()
            return items

    async def list_tables(self, ds_id: int, limit: int = 200, offset: int = 0) -> List[DataTable]:
        """列出指定数据源下的表。
        默认使用 ORM 异步查询；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步查询以保证接口可用。
        """
        try:
            stmt = (
                select(DataTable)
                .where(DataTable.data_source_id == ds_id)
                .order_by(DataTable.table_name)
                .limit(limit)
                .offset(offset)
            )
            res = await self.db.execute(stmt)
            return list(res.scalars().all())
        except Exception:
            # ORM 不可用（缺少 greenlet），降级为 PyMySQL 同步查询
            from pymysql.cursors import DictCursor
            from sqlalchemy.engine.url import make_url
            from app.core.config import settings

            url = make_url(settings.DATABASE_URL)
            conn = pymysql.connect(
                host=url.host or "localhost",
                port=int(url.port or 3306),
                user=url.username,
                password=url.password or "",
                database=url.database,
                charset="utf8mb4",
                cursorclass=DictCursor,
            )
            items: List[DataTable] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, data_source_id, table_name, display_name, description, category, tags,
                               row_count, size_mb, last_updated, is_active, created_at, updated_at
                        FROM aitt_data_tables
                        WHERE data_source_id = %s
                        ORDER BY table_name
                        LIMIT %s OFFSET %s
                        """,
                        (ds_id, limit, offset),
                    )
                    rows = cur.fetchall()
                    from types import SimpleNamespace
                    import json
                    for r in rows:
                        tags_val = r.get("tags")
                        if isinstance(tags_val, str):
                            try:
                                tags_val = json.loads(tags_val)
                            except Exception:
                                tags_val = None
                        obj = SimpleNamespace(
                            id=int(r["id"]),
                            data_source_id=int(r["data_source_id"]),
                            table_name=r["table_name"],
                            display_name=r.get("display_name"),
                            description=r.get("description"),
                            category=r.get("category"),
                            tags=tags_val,
                            row_count=int(r.get("row_count") or 0),
                            size_mb=r.get("size_mb"),
                            last_updated=r.get("last_updated"),
                            is_active=bool(r.get("is_active")),
                            created_at=r.get("created_at"),
                            updated_at=r.get("updated_at"),
                        )
                        items.append(obj)
            finally:
                conn.close()
            return items

    async def list_columns(self, table_id: int) -> List[TableColumn]:
        """列出指定表的字段。
        默认使用 ORM 异步查询；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步查询以保证接口可用。
        """
        try:
            stmt = (
                select(TableColumn)
                .where(TableColumn.table_id == table_id)
                .order_by(TableColumn.column_order, TableColumn.column_name)
            )
            res = await self.db.execute(stmt)
            return list(res.scalars().all())
        except Exception:
            from pymysql.cursors import DictCursor
            from sqlalchemy.engine.url import make_url
            from app.core.config import settings

            url = make_url(settings.DATABASE_URL)
            conn = pymysql.connect(
                host=url.host or "localhost",
                port=int(url.port or 3306),
                user=url.username,
                password=url.password or "",
                database=url.database,
                charset="utf8mb4",
                cursorclass=DictCursor,
            )
            items: List[TableColumn] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, table_id, column_name, display_name, data_type, is_nullable, default_value,
                               description, is_dimension, is_metric, is_primary_key, is_foreign_key, column_order,
                               created_at, updated_at
                        FROM aitt_table_columns
                        WHERE table_id = %s
                        ORDER BY column_order, column_name
                        """,
                        (table_id,),
                    )
                    rows = cur.fetchall()
                    from types import SimpleNamespace
                    for r in rows:
                        obj = SimpleNamespace(
                            id=int(r["id"]),
                            table_id=int(r["table_id"]),
                            column_name=r["column_name"],
                            display_name=r.get("display_name"),
                            data_type=r["data_type"],
                            is_nullable=bool(r.get("is_nullable")),
                            default_value=r.get("default_value"),
                            description=r.get("description"),
                            is_dimension=bool(r.get("is_dimension")),
                            is_metric=bool(r.get("is_metric")),
                            is_primary_key=bool(r.get("is_primary_key")),
                            is_foreign_key=bool(r.get("is_foreign_key")),
                            column_order=int(r.get("column_order") or 0),
                            created_at=r.get("created_at"),
                            updated_at=r.get("updated_at"),
                        )
                        items.append(obj)
            finally:
                conn.close()
            return items

    async def test_connection(self, ds: DataSource) -> tuple[bool, str]:
        try:
            # 解密密码，兼容历史纯文本（解密失败则回退为原值）
            pwd = None
            try:
                pwd = decrypt_secret(ds.password_encrypted) if ds.password_encrypted else ""
            except Exception:
                pwd = ds.password_encrypted or ""
            if ds.type == DataSourceType.MYSQL:
                conn = pymysql.connect(
                    host=ds.host, port=ds.port, user=ds.username, password=pwd, database=ds.database_name,
                    connect_timeout=5
                )
                conn.close()
                return True, "MySQL连接成功"
            elif ds.type == DataSourceType.POSTGRESQL:
                try:
                    import psycopg  # 延迟导入，避免未安装时阻断服务启动
                except ImportError:
                    return False, "PostgreSQL驱动未安装，请安装 'psycopg' 或使用其它数据源类型"
                with psycopg.connect(
                    host=ds.host, port=ds.port, user=ds.username, password=pwd, dbname=ds.database_name
                ) as _:
                    pass
                return True, "PostgreSQL连接成功"
            else:
                return False, f"暂不支持该类型的连接测试: {ds.type}"
        except Exception as e:
            return False, f"连接失败: {e}"

    async def execute_sql(self, ds: DataSource, sql: str, max_rows: int = 1000, timeout_seconds: int = 30) -> tuple[List[dict], List[str]]:
        """在指定数据源上执行只读SQL，返回(结果行, 列名)。仅支持MySQL/PostgreSQL。
        为安全起见，仅允许以SELECT开头的语句。
        """
        q = sql.strip().lower()
        if not q.startswith("select"):
            raise ValueError("仅允许执行SELECT查询")
        rows: List[dict] = []
        columns: List[str] = []
        # 解密密码，兼容历史纯文本
        try:
            pwd = decrypt_secret(ds.password_encrypted) if ds.password_encrypted else ""
        except Exception:
            pwd = ds.password_encrypted or ""
        if ds.type == DataSourceType.MYSQL:
            conn = pymysql.connect(
                host=ds.host,
                port=ds.port,
                user=ds.username,
                password=pwd,
                database=ds.database_name,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=timeout_seconds,
            )
            try:
                with conn.cursor() as cur:
                    # 尝试设置语句级超时（MySQL 5.7+ 支持 MAX_EXECUTION_TIME），失败则忽略
                    try:
                        cur.execute(f"SET SESSION MAX_EXECUTION_TIME = {int(timeout_seconds * 1000)}")
                    except Exception:
                        pass
                    cur.execute(sql)
                    res = cur.fetchmany(max_rows)
                    rows = list(res)
                    # 通过描述获取列名
                    if cur.description:
                        columns = [d[0] for d in cur.description]
            finally:
                conn.close()
        elif ds.type == DataSourceType.POSTGRESQL:
            try:
                import psycopg  # 延迟导入
            except ImportError:
                raise ValueError("PostgreSQL驱动未安装，请安装 'psycopg' 以执行查询")
            with psycopg.connect(
                host=ds.host,
                port=ds.port,
                user=ds.username,
                password=pwd,
                dbname=ds.database_name,
                connect_timeout=timeout_seconds,
            ) as conn:
                with conn.cursor() as cur:
                    # 设置语句超时
                    try:
                        cur.execute(f"SET LOCAL statement_timeout = '{int(timeout_seconds)}s'")
                    except Exception:
                        pass
                    cur.execute(sql)
                    res = cur.fetchmany(max_rows)
                    # psycopg返回的是tuple列表，需要转字典
                    if cur.description:
                        columns = [c.name for c in cur.description]
                    for r in res:
                        rows.append({columns[i]: r[i] for i in range(len(columns))})
        else:
            raise ValueError(f"暂不支持该类型的SQL执行: {ds.type}")
        return rows, columns

    async def sync_tables(self, ds: DataSource) -> tuple[int, int]:
        """同步外部数据源的表与列元数据。仅实现MySQL与PostgreSQL的基本同步。返回(表数量, 列数量)。"""
        tables_count = 0
        columns_count = 0
        # 解密密码，兼容历史纯文本
        try:
            pwd = decrypt_secret(ds.password_encrypted) if ds.password_encrypted else ""
        except Exception:
            pwd = ds.password_encrypted or ""
        if ds.type == DataSourceType.MYSQL:
            conn = pymysql.connect(
                host=ds.host, port=ds.port, user=ds.username, password=pwd, database=ds.database_name,
                cursorclass=pymysql.cursors.DictCursor
            )
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema=%s", (ds.database_name,))
                    tables = cur.fetchall()
                    for t in tables:
                        table = DataTable(
                            data_source_id=ds.id,
                            table_name=t["table_name"],
                            description=None,
                            category=None,
                            tags=None,
                            row_count=t.get("table_rows") or 0,
                            size_mb=None,
                        )
                        self.db.add(table)
                        await self.db.flush()
                        await self.db.refresh(table)
                        tables_count += 1
                        cur.execute(
                            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
                            (ds.database_name, t["table_name"]),
                        )
                        cols = cur.fetchall()
                        for c in cols:
                            col = TableColumn(
                                table_id=table.id,
                                column_name=c["column_name"],
                                data_type=c["data_type"],
                                is_nullable=True if c["is_nullable"] == "YES" else False,
                                is_dimension=False,
                                is_metric=False,
                                is_primary_key=False,
                                is_foreign_key=False,
                            )
                            self.db.add(col)
                            columns_count += 1
                await self.db.commit()
            finally:
                conn.close()
        elif ds.type == DataSourceType.POSTGRESQL:
            try:
                import psycopg  # 延迟导入
            except ImportError:
                # 其它类型暂不支持
                return tables_count, columns_count
            with psycopg.connect(host=ds.host, port=ds.port, user=ds.username, password=pwd, dbname=ds.database_name) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                    tables = cur.fetchall()
                    for (table_name,) in tables:
                        table = DataTable(
                            data_source_id=ds.id,
                            table_name=table_name,
                        )
                        self.db.add(table)
                        await self.db.flush()
                        await self.db.refresh(table)
                        tables_count += 1
                        cur.execute(
                            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
                            (table_name,),
                        )
                        cols = cur.fetchall()
                        for column_name, data_type, is_nullable in cols:
                            col = TableColumn(
                                table_id=table.id,
                                column_name=column_name,
                                data_type=data_type,
                                is_nullable=True if is_nullable == "YES" else False,
                            )
                            self.db.add(col)
                            columns_count += 1
                await self.db.commit()
        else:
            # 其它类型暂不支持
            pass

        return tables_count, columns_count