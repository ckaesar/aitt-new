from typing import List, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query import QueryHistory, QueryTemplate, QueryStatus
from app.schemas.query import QueryTemplateCreate, QueryTemplateUpdate


class QueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 模板相关
    async def create_template(self, payload: QueryTemplateCreate, created_by: int) -> QueryTemplate:
        """创建查询模板。
        优先使用 ORM；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步插入以保证接口可用。
        """
        try:
            tpl = QueryTemplate(
                name=payload.name,
                description=payload.description,
                category=payload.category,
                natural_language_template=payload.natural_language_template,
                sql_template=payload.sql_template,
                parameters=payload.parameters,
                is_public=payload.is_public,
                created_by=created_by,
            )
            self.db.add(tpl)
            await self.db.flush()
            await self.db.refresh(tpl)
            await self.db.commit()
            return tpl
        except Exception:
            # ORM 路径不可用（缺少 greenlet），降级为 PyMySQL 同步插入
            import json
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
            try:
                with conn.cursor() as cur:
                    # 确保创建者ID有效：优先 admin，其次任意用户；都不存在则创建一个 system 用户
                    uid = int(created_by) if created_by is not None else 0
                    if uid <= 0:
                        cur.execute("SELECT id FROM aitt_users WHERE username=%s LIMIT 1", ("admin",))
                        r = cur.fetchone()
                        if r and r.get("id"):
                            uid = int(r["id"])
                        else:
                            cur.execute("SELECT id FROM aitt_users LIMIT 1")
                            r2 = cur.fetchone()
                            if r2 and r2.get("id"):
                                uid = int(r2["id"])
                            else:
                                # 创建占位系统用户（避免外键约束失败）
                                cur.execute(
                                    """
                                    INSERT INTO aitt_users (username, email, password_hash, role, is_active)
                                    VALUES (%s, %s, %s, %s, %s)
                                    """,
                                    ("system", "system@example.com", "", "viewer", True),
                                )
                                uid = int(cur.lastrowid)

                    cur.execute(
                        """
                        INSERT INTO aitt_query_templates (
                            name, description, category, natural_language_template, sql_template,
                            parameters, usage_count, is_public, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payload.name,
                            payload.description,
                            payload.category,
                            payload.natural_language_template,
                            payload.sql_template,
                            json.dumps(payload.parameters) if payload.parameters is not None else None,
                            0,
                            bool(payload.is_public),
                            int(uid),
                        ),
                    )
                    new_id = int(cur.lastrowid)
                conn.commit()

                # 查询数据库生成的时间字段，确保响应模型校验通过
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT created_at, updated_at FROM aitt_query_templates WHERE id=%s LIMIT 1
                        """,
                        (new_id,),
                    )
                    ts_row = cur.fetchone() or {}
                    created_at_val = ts_row.get("created_at")
                    updated_at_val = ts_row.get("updated_at")

                # 返回一个轻量的模型实例（不再访问 ORM 刷新）
                tpl = QueryTemplate(
                    id=new_id,
                    name=payload.name,
                    description=payload.description,
                    category=payload.category,
                    natural_language_template=payload.natural_language_template,
                    sql_template=payload.sql_template,
                    parameters=payload.parameters,
                    usage_count=0,
                    is_public=bool(payload.is_public),
                    created_by=int(uid),
                )
                # 补充时间字段以满足 Pydantic 的必填校验
                try:
                    if created_at_val is not None:
                        setattr(tpl, "created_at", created_at_val)
                    if updated_at_val is not None:
                        setattr(tpl, "updated_at", updated_at_val)
                except Exception:
                    from datetime import datetime
                    now = datetime.now()
                    setattr(tpl, "created_at", getattr(tpl, "created_at", now))
                    setattr(tpl, "updated_at", getattr(tpl, "updated_at", now))

                return tpl
            finally:
                conn.close()

    async def update_template(self, tpl_id: int, payload: QueryTemplateUpdate) -> Optional[QueryTemplate]:
        stmt = (
            update(QueryTemplate)
            .where(QueryTemplate.id == tpl_id)
            .values(
                name=payload.name,
                description=payload.description,
                category=payload.category,
                natural_language_template=payload.natural_language_template,
                sql_template=payload.sql_template,
                parameters=payload.parameters,
                is_public=payload.is_public,
            )
            .returning(QueryTemplate)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def delete_template(self, tpl_id: int) -> None:
        stmt = delete(QueryTemplate).where(QueryTemplate.id == tpl_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def list_templates(self, limit: int = 20, offset: int = 0) -> List[QueryTemplate]:
        """列出查询模板。
        默认使用 ORM 异步查询；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步查询以保证接口可用。
        """
        try:
            stmt = select(QueryTemplate).order_by(QueryTemplate.id).limit(limit).offset(offset)
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
            items: List[QueryTemplate] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, name, description, category, natural_language_template, sql_template,
                               parameters, usage_count, is_public, created_by, created_at, updated_at
                        FROM aitt_query_templates
                        ORDER BY id
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                    rows = cur.fetchall()
                    from types import SimpleNamespace
                    for r in rows:
                        # 将 JSON 文本参数解析为字典
                        params_val = r.get("parameters")
                        if isinstance(params_val, str):
                            try:
                                import json
                                params_val = json.loads(params_val)
                            except Exception:
                                params_val = None
                        obj = SimpleNamespace(
                            id=int(r["id"]),
                            name=r["name"],
                            description=r.get("description"),
                            category=r.get("category"),
                            natural_language_template=r.get("natural_language_template"),
                            sql_template=r.get("sql_template"),
                            parameters=params_val,
                            usage_count=int(r.get("usage_count") or 0),
                            is_public=bool(r.get("is_public")),
                            created_by=int(r.get("created_by") or 0),
                            created_at=r.get("created_at"),
                            updated_at=r.get("updated_at"),
                        )
                        items.append(obj)
            finally:
                conn.close()
            return items

    async def get_template(self, tpl_id: int) -> Optional[QueryTemplate]:
        stmt = select(QueryTemplate).where(QueryTemplate.id == tpl_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    # 历史相关
    async def create_history(
        self,
        user_id: int,
        natural_language_query: str,
        generated_sql: Optional[str] = None,
        status: QueryStatus = QueryStatus.SUCCESS,
        execution_time_ms: Optional[int] = None,
        row_count: Optional[int] = None,
        error_message: Optional[str] = None,
        is_saved: bool = True,
        tags: Optional[List[str]] = None,
        executed_sql: Optional[str] = None,
        query_result: Optional[dict] = None,
    ) -> QueryHistory:
        # 优先使用 ORM 写入；在缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 同步写入
        try:
            item = QueryHistory(
                user_id=user_id,
                natural_language_query=natural_language_query,
                generated_sql=generated_sql,
                status=status,
                execution_time_ms=execution_time_ms,
                row_count=row_count,
                error_message=error_message,
                is_saved=is_saved,
                tags=tags,
                executed_sql=executed_sql,
                query_result=query_result,
            )
            self.db.add(item)
            await self.db.flush()
            await self.db.refresh(item)
            await self.db.commit()
            return item
        except Exception:
            # ORM 路径不可用（缺少 greenlet），降级为 PyMySQL 同步插入
            import json
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
            try:
                with conn.cursor() as cur:
                    # 确保 user_id 可用：优先 admin，其次任意用户；都不存在则创建一个 system 用户
                    uid = int(user_id) if user_id is not None else 0
                    if uid <= 0:
                        cur.execute("SELECT id FROM aitt_users WHERE username=%s LIMIT 1", ("admin",))
                        r = cur.fetchone()
                        if r and r.get("id"):
                            uid = int(r["id"])
                        else:
                            cur.execute("SELECT id FROM aitt_users LIMIT 1")
                            r2 = cur.fetchone()
                            if r2 and r2.get("id"):
                                uid = int(r2["id"])
                            else:
                                # 创建占位系统用户（避免外键约束失败）
                                # 注意：email 唯一约束，使用固定 system@example.com；password_hash 允许空字符串
                                cur.execute(
                                    """
                                    INSERT INTO aitt_users (username, email, password_hash, role, is_active)
                                    VALUES (%s, %s, %s, %s, %s)
                                    """,
                                    ("system", "system@example.com", "", "viewer", True),
                                )
                                uid = int(cur.lastrowid)

                    cur.execute(
                        """
                        INSERT INTO aitt_query_history (
                            user_id, query_name, natural_language_query, generated_sql,
                            executed_sql, query_result, execution_time_ms, row_count,
                            status, error_message, is_saved, is_shared, tags
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            uid,
                            None,  # 初次创建未命名
                            natural_language_query,
                            generated_sql or "",
                            executed_sql,
                            json.dumps(query_result) if query_result is not None else None,
                            int(execution_time_ms) if execution_time_ms is not None else None,
                            int(row_count) if row_count is not None else None,
                            str(status.value if hasattr(status, "value") else status),
                            error_message,
                            bool(is_saved),
                            False,  # 默认未分享
                            json.dumps(tags) if tags is not None else None,
                        ),
                    )
                conn.commit()

                new_id = cur.lastrowid
                # 查询数据库生成的创建时间，确保响应模型校验通过
                try:
                    cur.execute(
                        """
                        SELECT created_at FROM aitt_query_history WHERE id=%s LIMIT 1
                        """,
                        (new_id,),
                    )
                    created_row = cur.fetchone()
                    created_at_val = created_row.get("created_at") if created_row else None
                except Exception:
                    created_at_val = None

                # 返回一个轻量的模型实例（不再访问 ORM 刷新）
                item = QueryHistory(
                    id=int(new_id),
                    user_id=int(uid),
                    query_name=None,
                    natural_language_query=natural_language_query,
                    generated_sql=generated_sql or "",
                    executed_sql=executed_sql,
                    query_result=query_result,
                    execution_time_ms=execution_time_ms,
                    row_count=row_count,
                    status=status,
                    error_message=error_message,
                    is_saved=bool(is_saved),
                    is_shared=False,
                    tags=tags,
                )
                # 补充创建时间以满足 Pydantic 的必填校验
                if created_at_val is not None:
                    setattr(item, "created_at", created_at_val)
                else:
                    from datetime import datetime
                    setattr(item, "created_at", datetime.now())
                return item
            finally:
                conn.close()

    async def save_history(self, history_id: int, query_name: str, tags: Optional[List[str]]) -> Optional[QueryHistory]:
        stmt = (
            update(QueryHistory)
            .where(QueryHistory.id == history_id)
            .values(
                query_name=query_name,
                is_saved=True,
                tags=tags,
            )
            .returning(QueryHistory)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def share_history(self, history_id: int, is_shared: bool) -> Optional[QueryHistory]:
        stmt = (
            update(QueryHistory)
            .where(QueryHistory.id == history_id)
            .values(
                is_shared=is_shared,
            )
            .returning(QueryHistory)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def list_history_by_user(self, user_id: int, limit: int = 20, offset: int = 0) -> List[QueryHistory]:
        """按用户列出查询历史。
        优先使用 ORM；当当前环境缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 查询。
        """
        try:
            stmt = (
                select(QueryHistory)
                .where(QueryHistory.user_id == user_id)
                .order_by(QueryHistory.id.desc())
                .limit(limit)
                .offset(offset)
            )
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
            items: List[QueryHistory] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, query_name, natural_language_query, generated_sql,
                               status, execution_time_ms, row_count, is_saved, is_shared, tags, created_at
                        FROM aitt_query_history
                        WHERE user_id=%s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (user_id, limit, offset),
                    )
                    rows = cur.fetchall()
                from app.models.query import QueryStatus
                import json
                for r in rows:
                    # 字段类型转换
                    try:
                        status = QueryStatus(r.get("status") or QueryStatus.SUCCESS)
                    except Exception:
                        status = QueryStatus.SUCCESS
                    raw_tags = r.get("tags")
                    tags = None
                    if raw_tags:
                        try:
                            parsed = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
                            tags = parsed if isinstance(parsed, list) else None
                        except Exception:
                            tags = None
                    item = QueryHistory(
                        id=int(r["id"]),
                        user_id=int(r["user_id"]),
                        query_name=r.get("query_name"),
                        natural_language_query=r.get("natural_language_query") or "",
                        generated_sql=r.get("generated_sql") or "",
                        status=status,
                        execution_time_ms=r.get("execution_time_ms"),
                        row_count=r.get("row_count"),
                        is_saved=bool(r.get("is_saved")),
                        is_shared=bool(r.get("is_shared")),
                        tags=tags,
                        created_at=r.get("created_at"),
                    )
                    items.append(item)
                return items
            finally:
                conn.close()

    async def list_history_all(self, limit: int = 20, offset: int = 0) -> List[QueryHistory]:
        """列出全量查询历史。
        优先使用 ORM；当当前环境缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 查询。
        """
        try:
            stmt = (
                select(QueryHistory)
                .order_by(QueryHistory.id.desc())
                .limit(limit)
                .offset(offset)
            )
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
            items: List[QueryHistory] = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, query_name, natural_language_query, generated_sql,
                               status, execution_time_ms, row_count, is_saved, is_shared, tags, created_at
                        FROM aitt_query_history
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                    rows = cur.fetchall()
                from app.models.query import QueryStatus
                import json
                for r in rows:
                    # 字段类型转换
                    try:
                        status = QueryStatus(r.get("status") or QueryStatus.SUCCESS)
                    except Exception:
                        status = QueryStatus.SUCCESS
                    raw_tags = r.get("tags")
                    tags = None
                    if raw_tags:
                        try:
                            parsed = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
                            tags = parsed if isinstance(parsed, list) else None
                        except Exception:
                            tags = None
                    item = QueryHistory(
                        id=int(r["id"]),
                        user_id=int(r["user_id"]),
                        query_name=r.get("query_name"),
                        natural_language_query=r.get("natural_language_query") or "",
                        generated_sql=r.get("generated_sql") or "",
                        status=status,
                        execution_time_ms=r.get("execution_time_ms"),
                        row_count=r.get("row_count"),
                        is_saved=bool(r.get("is_saved")),
                        is_shared=bool(r.get("is_shared")),
                        tags=tags,
                        created_at=r.get("created_at"),
                    )
                    items.append(item)
                return items
            finally:
                conn.close()

    async def count_history_all(self) -> int:
        """统计查询历史总数。
        优先使用 ORM；当当前环境缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 统计。
        """
        try:
            stmt = select(func.count()).select_from(QueryHistory)
            res = await self.db.execute(stmt)
            total = res.scalar() or 0
            return int(total)
        except Exception:
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
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) AS cnt FROM aitt_query_history")
                    row = cur.fetchone() or {"cnt": 0}
                    return int(row.get("cnt") or 0)
            finally:
                conn.close()

    async def get_history(self, history_id: int) -> Optional[QueryHistory]:
        """获取单条查询历史。
        优先使用 ORM；当当前环境缺失 greenlet 等导致 ORM 不可用时，降级为 PyMySQL 查询。
        """
        try:
            stmt = select(QueryHistory).where(QueryHistory.id == history_id)
            res = await self.db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception:
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
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, query_name, natural_language_query, generated_sql,
                               status, execution_time_ms, row_count, is_saved, is_shared, tags, created_at
                        FROM aitt_query_history
                        WHERE id=%s
                        LIMIT 1
                        """,
                        (history_id,),
                    )
                    r = cur.fetchone()
                if not r:
                    return None
                from app.models.query import QueryStatus
                import json
                try:
                    status = QueryStatus(r.get("status") or QueryStatus.SUCCESS)
                except Exception:
                    status = QueryStatus.SUCCESS
                raw_tags = r.get("tags")
                tags = None
                if raw_tags:
                    try:
                        parsed = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
                        tags = parsed if isinstance(parsed, list) else None
                    except Exception:
                        tags = None
                item = QueryHistory(
                    id=int(r["id"]),
                    user_id=int(r["user_id"]),
                    query_name=r.get("query_name"),
                    natural_language_query=r.get("natural_language_query") or "",
                    generated_sql=r.get("generated_sql") or "",
                    status=status,
                    execution_time_ms=r.get("execution_time_ms"),
                    row_count=r.get("row_count"),
                    is_saved=bool(r.get("is_saved")),
                    is_shared=bool(r.get("is_shared")),
                    tags=tags,
                    created_at=r.get("created_at"),
                )
                return item
            finally:
                conn.close()