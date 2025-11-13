"""
AI相关API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.schemas.common import DataResponse
from app.schemas.ai import AIQueryRequest, AIQueryResponse
from app.services.ai import AIService
from app.services.query import QueryService
from app.models.query import QueryStatus
from app.services.rag import RAGService

router = APIRouter()


@router.post("/query", response_model=DataResponse[AIQueryResponse])
async def ai_query(
    payload: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    # 入参日志（避免记录过长文本，做长度与关键标记）
    try:
        logger.info(
            "AI接口入参: len(query)={}, use_rag={}, has_context={}, conversation_id={}, data_source_id={}",
            len(payload.query or ""),
            bool(payload.use_rag),
            bool(payload.context),
            payload.conversation_id,
            payload.data_source_id,
        )
    except Exception:
        pass
    ai = AIService(db)
    qs = QueryService(db)
    # 若启用RAG，先检索片段与拼接上下文，供SQL生成与响应展示
    rag_chunks = []
    rag_context = None
    if payload.use_rag:
        try:
            rag = RAGService()
            rag_chunks = rag.query(payload.query, top_k=4)
            # 由一次检索构建上下文，避免重复向量查询
            rag_context = "\n".join([f"[来源:{c.get('source','unknown')}] {c.get('text','')}" for c in rag_chunks])
        except Exception:
            rag_chunks = []
            rag_context = None
    # 生成SQL（支持RAG上下文）
    generated_sql = await ai.generate_sql(payload.query, context=payload.context, use_rag=payload.use_rag or False, rag_context=rag_context)
    # 记录历史（开发模式：若数据库不可用则忽略错误）
    try:
        history = await qs.create_history(
            user_id=0,
            natural_language_query=payload.query,
            generated_sql=generated_sql,
            status=QueryStatus.SUCCESS,
            execution_time_ms=0,
            row_count=0,
            is_saved=True,
            tags=["ai_query"],
        )
    except Exception:
        history = None
    # 简单SQL解析，提取表、维度、指标、筛选与排序（启发式）
    def _analyze_sql(sql: str):
        import re
        txt = sql or ""
        tables: list[str] = []
        selected_table: str | None = None
        dimensions: list[str] = []
        metrics: list[dict] = []
        filters: list[dict] = []
        sorts: list[dict] = []

        # 提取FROM后的第一个标识为主表
        m_from = re.search(r"from\s+([\w\.`]+)", txt, re.IGNORECASE)
        if m_from:
            selected_table = m_from.group(1).strip().strip('`')
            tables.append(selected_table)
        # JOIN表
        for jm in re.finditer(r"join\s+([\w\.`]+)", txt, re.IGNORECASE):
            t = jm.group(1).strip().strip('`')
            if t not in tables:
                tables.append(t)

        # 选取SELECT部分
        m_sel = re.search(r"select\s+(.*?)\s+from\s", txt, re.IGNORECASE | re.DOTALL)
        if m_sel:
            select_part = m_sel.group(1)
            # 按逗号分割，识别聚合
            for item in [s.strip() for s in select_part.split(',') if s.strip()]:
                # 提取别名
                alias_m = re.search(r"\s+as\s+(\w+)$", item, re.IGNORECASE)
                alias = alias_m.group(1) if alias_m else None
                # 聚合函数
                agg_m = re.match(r"(sum|count|avg|min|max)\s*\(\s*([\w\.]+)\s*\)", item, re.IGNORECASE)
                if agg_m:
                    func = agg_m.group(1).lower()
                    col = agg_m.group(2)
                    metrics.append({"column": col, "aggregation": func, "alias": alias or f"{func}_{col.replace('.', '_')}"})
                else:
                    # 普通列作为维度
                    # 去掉可能的表前缀
                    col = re.sub(r"^\w+\.", "", item)
                    # 去掉函数包装
                    col = re.sub(r"\b(distinct|coalesce|ifnull)\b\s*\((.*?)\)", r"\2", col, flags=re.IGNORECASE)
                    # 去掉别名
                    col = re.sub(r"\s+as\s+\w+$", "", col, flags=re.IGNORECASE)
                    col = col.strip()
                    if col:
                        dimensions.append(col)

        # WHERE解析（简单等值与比较）
        m_where = re.search(r"where\s+(.*?)\s+(group\s+by|order\s+by|limit|$)", txt, re.IGNORECASE | re.DOTALL)
        if m_where:
            where_part = m_where.group(1)
            # 拆分 AND 条件
            for cond in re.split(r"\band\b", where_part, flags=re.IGNORECASE):
                cond = cond.strip()
                cm = re.match(r"([\w\.]+)\s*(=|!=|>=|<=|>|<|like)\s*(.+)$", cond, re.IGNORECASE)
                if cm:
                    col = cm.group(1)
                    op = cm.group(2).upper()
                    val = cm.group(3).strip().strip("'\"")
                    filters.append({"column": col, "operator": op, "value": val})

        # ORDER BY
        m_order = re.search(r"order\s+by\s+(.*?)\s+(limit|$)", txt, re.IGNORECASE | re.DOTALL)
        if m_order:
            order_part = m_order.group(1)
            for seg in [s.strip() for s in order_part.split(',') if s.strip()]:
                om = re.match(r"([\w\.]+)\s*(asc|desc)?", seg, re.IGNORECASE)
                if om:
                    col = om.group(1)
                    ord = (om.group(2) or 'asc').lower()
                    sorts.append({"column": col, "order": ord})

        return {
            "tables": tables,
            "selected_table": selected_table,
            "dimensions": dimensions,
            "metrics": metrics,
            "filters": filters,
            "sorts": sorts,
        }

    analysis = _analyze_sql(generated_sql or "")
    resp = AIQueryResponse(
        conversation_id=None,
        message_id=None,
        reply="SQL已生成",
        generated_sql=generated_sql,
        query_results=None,
        suggestions=["已为您解析出表、维度、指标、筛选与排序，可调整后执行"],
        confidence=0.5,
        processing_time_ms=0,
        rag_context=rag_context,
        rag_chunks=rag_chunks,
        tables=analysis["tables"],
        selected_table=analysis["selected_table"],
        dimensions=analysis["dimensions"],
        metrics=analysis["metrics"],
        filters=analysis["filters"],
        sorts=analysis["sorts"],
    )
    # 返回值摘要日志
    try:
        logger.info(
            "AI接口返回: len(sql)={}, tables={}, dims={}, metrics={}, filters={}, sorts={}, rag_chunks={}",
            len((resp.generated_sql or "")),
            ",".join(resp.tables or []),
            len(resp.dimensions or []),
            len(resp.metrics or []),
            len(resp.filters or []),
            len(resp.sorts or []),
            len(resp.rag_chunks or []),
        )
    except Exception:
        pass
    return DataResponse(data=resp, message="AI生成SQL成功")