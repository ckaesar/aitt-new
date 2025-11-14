from typing import Optional
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from loguru import logger
from app.models.ai_conversation import AIConversation, AIMessage, MessageRole, ConversationStatus
from app.services.rag import RAGService
from app.services.metadata_search import MetadataSearch
from app.services.prompt import build_sql_generation_prompt

try:
    # OpenAI Python SDK (v1.x)
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except Exception:
    OPENAI_SDK_AVAILABLE = False


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._max_retries = 2
        self._timeout_seconds = 20

    async def create_conversation(self, user_id: int, title: Optional[str] = None, context: Optional[str] = None) -> AIConversation:
        conv = AIConversation(user_id=user_id, title=title or "新会话", context=context)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        await self.db.commit()
        return conv

    async def add_message(self, conversation_id: int, role: MessageRole, content: str, token_count: Optional[int] = None) -> AIMessage:
        msg = AIMessage(conversation_id=conversation_id, role=role, content=content, token_count=token_count)
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        await self.db.commit()
        return msg

    def _rule_based_sql(self, nl_query: str) -> Optional[str]:
        """当未配置模型或调用失败时的规则兜底：
        - 利用元数据结构化匹配识别意图：
          1) 订单统计（近7天订单数与GMV）
          2) 简单详情类查询（查看X的详细信息：主表+常用维度列）
        - MySQL语法；若无法可靠生成返回None。
        """
        try:
            ms = MetadataSearch()
            matches = ms.get_structured_matches_for_query(nl_query, top_k=16)
            if not matches:
                # 若Chroma不可用或未命中，直接从MySQL元数据表兜底读取
                try:
                    from sqlalchemy.engine.url import make_url
                    import pymysql
                    from pymysql.cursors import DictCursor
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
                    tables_map: dict[str, dict] = {}
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT id, data_source_id, table_name, display_name
                            FROM aitt_data_tables
                            ORDER BY id
                            """
                        )
                        tables = cur.fetchall() or []
                        for t in tables:
                            tables_map[str(t["table_name"])]= {"display_name": t.get("display_name"), "columns": []}
                        cur.execute(
                            """
                            SELECT tc.table_id, tc.column_name, tc.data_type, tc.is_dimension, tc.is_metric, dt.table_name
                            FROM aitt_table_columns tc
                            JOIN aitt_data_tables dt ON dt.id = tc.table_id
                            ORDER BY tc.id
                            """
                        )
                        cols = cur.fetchall() or []
                        for c in cols:
                            tname = str(c.get("table_name") or "")
                            if tname and tname in tables_map:
                                tables_map[tname]["columns"].append({
                                    "name": c.get("column_name"),
                                    "type": c.get("data_type"),
                                    "is_dim": bool(c.get("is_dimension")),
                                    "is_met": bool(c.get("is_metric")),
                                })
                    try:
                        conn.close()
                    except Exception:
                        pass
                    matches = tables_map
                except Exception as e2:
                    logger.warning("规则兜底MySQL元数据读取失败: {}", e2)
                    return None
            q = (nl_query or "").lower()
            # 关键词集合（包含产品类词汇以支持详情意图）
            order_kw = ["order", "orders", "交易", "订单"]
            date_kw = ["date", "dt", "时间", "日期", "created_at", "order_date", "下单"]
            amt_kw = ["amount", "total_amount", "gmv", "price", "pay", "支付", "金额", "交易额"]
            product_kw = ["product", "商品", "产品", "sku", "spu", "brand", "category"]
            detail_kw = ["detail", "详细", "详情", "明细"]

            def pick_table() -> Optional[str]:
                # 优先表名包含订单/交易关键词
                candidates = list(matches.keys())
                for t in candidates:
                    t_low = (t or "").lower()
                    if any(k in t_low for k in order_kw):
                        return t
                # 回退：选择列中存在金额与日期列的表
                for t, info in matches.items():
                    cols = info.get("columns") or []
                    has_date = any(any(k in (c.get("name") or "").lower() for k in date_kw) for c in cols)
                    has_amt = any(any(k in (c.get("name") or "").lower() for k in amt_kw) for c in cols)
                    if has_date and has_amt:
                        return t
                return None

            def pick_col(cols: list[dict], kw_list: list[str]) -> Optional[str]:
                # 先按名称匹配，再按维度/指标标记
                for c in cols:
                    name = (c.get("name") or "").lower()
                    if any(k in name for k in kw_list):
                        return c.get("name")
                # 次选：如果金额列需要指标列
                for c in cols:
                    if c.get("is_met") and any(k in (c.get("name") or "").lower() for k in kw_list):
                        return c.get("name")
                return None

            # 详情意图：当包含产品相关词汇或明确详情关键词时，优先返回主表的常见维度列
            def is_detail_intent() -> bool:
                return any(k in q for k in detail_kw) or any(k in q for k in product_kw)

            if is_detail_intent():
                # 从匹配中选择更像“产品”的表
                candidates = list(matches.keys())
                chosen = None
                for t in candidates:
                    tl = (t or "").lower()
                    if any(k in tl for k in ["product", "sku", "spu"]):
                        chosen = t
                        break
                if not chosen and candidates:
                    chosen = candidates[0]
                cols = matches.get(chosen, {}).get("columns") or []
                # 选取常见维度列
                want_kw = ["id", "name", "category", "brand", "price"]
                sel = []
                for w in want_kw:
                    c = pick_col(cols, [w])
                    if c and c not in sel:
                        sel.append(c)
                # 回退：如果仍然为空，取前5个维度列
                if not sel:
                    for c in cols:
                        if c.get("is_dim"):
                            sel.append(c.get("name"))
                            if len(sel) >= 5:
                                break
                if chosen and sel:
                    select_list = ", ".join([f"{x}" for x in sel])
                    return f"SELECT {select_list} FROM {chosen}"
                # 若详情意图无法确定列/表，继续尝试订单统计兜底

            # 订单统计兜底
            tname = pick_table()
            if not tname:
                return None
            cols = matches[tname].get("columns") or []
            date_col = pick_col(cols, date_kw) or "created_at"
            amt_col = pick_col(cols, amt_kw) or "amount"
            has_7d = any(k in q for k in ["近7天", "最近7天", "past 7", "last 7", "近七天"])
            date_cond = "DATE_SUB(CURDATE(), INTERVAL 7 DAY)" if has_7d else "DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            return (
                f"SELECT COUNT(*) AS order_count, SUM({amt_col}) AS gmv\n"
                f"FROM {tname}\n"
                f"WHERE DATE({date_col}) >= {date_cond}"
            )
        except Exception as e:
            logger.warning("规则兜底生成失败: {}", e)
            return None

    async def generate_sql(self, nl_query: str, context: Optional[str] = None, use_rag: bool = True, rag_context: Optional[str] = None, conversation_id: Optional[int] = None, rag_chunks: Optional[list] = None) -> str:
        """生成SQL：支持RAG上下文与真实模型调用（带降级）。"""
        logger.info(
            f"AI生成SQL请求: len(query)={len(nl_query or '')}, use_rag={use_rag}, model={settings.AI_MODEL_NAME}, base_url={settings.OPENAI_BASE_URL}"
        )
        # 1) 元数据上下文（强制）：始终从Chroma元数据集合检索
        metadata_ctx: Optional[str] = None
        try:
            ms = MetadataSearch()
            # 优先使用结构化上下文（表/列分组），便于模型解析
            metadata_ctx = ms.get_grouped_context_for_query(nl_query, top_k=12)
            logger.info("AI生成SQL: 元数据上下文就绪 len(meta_ctx)={}", len(metadata_ctx or ""))
        except Exception:
            metadata_ctx = None
            logger.warning("AI生成SQL: 元数据上下文获取失败或不可用")

        # 2) 文档RAG上下文（可选）
        if use_rag and not rag_context:
            try:
                rag = RAGService()
                rag_context = rag.get_context_for_query(nl_query, top_k=4)
                logger.info(
                    "AI生成SQL: RAG上下文就绪 len(rag_ctx)={}",
                    len(rag_context or ""),
                )
            except Exception:
                rag_context = None
                logger.warning("AI生成SQL: RAG上下文获取失败或不可用，继续无RAG")
        # 3) Prompt拼装：优先包含元数据上下文，再附加RAG上下文
        combined_ctx = None
        if metadata_ctx and rag_context:
            combined_ctx = metadata_ctx + "\n" + rag_context
        else:
            combined_ctx = metadata_ctx or rag_context
        prompt = build_sql_generation_prompt(
            nl_query=nl_query,
            schema_context=combined_ctx,
            user_context=context,
        )
        try:
            logger.info("AI生成SQL: Prompt长度={}", len(prompt or ""))
        except Exception:
            pass

        # 4) 真实模型调用（OpenAI SDK），若不可用或未配置，走降级返回占位SQL
        if not settings.OPENAI_API_KEY or not OPENAI_SDK_AVAILABLE:
            # 尝试规则兜底
            rb = self._rule_based_sql(nl_query)
            if rb:
                logger.info("AI SDK不可用，使用规则兜底SQL")
                return rb
            logger.warning("AI SDK不可用或未配置API密钥，规则兜底失败，返回占位SQL")
            return "SELECT 1 AS placeholder;"

        # 带重试与超时的调用实现
        client = OpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY)
        attempt = 0
        last_err: Exception | None = None
        import time as _time
        t0 = _time.perf_counter()
        prompt_tokens = 0
        completion_tokens = 0
        model_name = settings.AI_MODEL_NAME
        while attempt <= self._max_retries:
            try:
                # 使用 Chat Completions，要求仅输出SQL
                _approx_len = max(1, len(prompt or ""))
                _dyn_max_tokens = max(128, min(512, int(_approx_len / 8)))
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "你是资深数据分析助理，只输出合法SQL，不要解释，不要包含代码块标记，不要包含分号。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    top_p=0.2,
                    presence_penalty=0,
                    frequency_penalty=0,
                    max_tokens=_dyn_max_tokens,
                    n=1,
                    stop=[";", "\n```", "\n\n```", "\n--"],
                    user=str(conversation_id or "anonymous"),
                    timeout=self._timeout_seconds,
                )
                # 统计tokens（SDK返回如有不一致则回退估算）
                try:
                    usage = getattr(completion, "usage", None)
                    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
                except Exception:
                    prompt_tokens = 0
                    completion_tokens = 0
                content = completion.choices[0].message.content or ""
                cleaned = content.strip()
                cleaned = re.sub(r"^```sql\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"```\s*$", "", cleaned)
                m = re.search(r"\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b[\s\S]*", cleaned, flags=re.IGNORECASE)
                sql_text = m.group(0).strip() if m else cleaned
                sql_text = sql_text or ""
                sql_text = re.sub(r";\s*$", "", sql_text)
                latency_ms = int((_time.perf_counter() - t0) * 1000)
                # 异步保存调用日志
                try:
                    import asyncio as _asyncio
                    _asyncio.create_task(self._save_ai_call_log(
                        conversation_id=conversation_id,
                        model_name=model_name,
                        endpoint="chat.completions",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                        latency_ms=latency_ms,
                        use_rag=bool(use_rag),
                        rag_context_len=len(rag_context or ""),
                        metadata_context_len=len((metadata_ctx or "")),
                        rag_chunks=rag_chunks,
                        status="success",
                        error_message=None,
                    ))
                except Exception:
                    pass
                if sql_text:
                    logger.info(f"AI生成SQL成功: {sql_text[:500]}")
                    return sql_text
                rb2 = self._rule_based_sql(nl_query)
                if rb2:
                    logger.info("模型返回空，使用规则兜底SQL")
                    return rb2
                logger.warning("AI返回空内容，降级为占位SQL")
                return "SELECT 1 AS placeholder;"
            except Exception as e:
                last_err = e
                attempt += 1
                if attempt <= self._max_retries:
                    # 指数退避重试
                    import math
                    _delay = min(2.0 ** attempt, 4.0)
                    try:
                        logger.warning("AI调用失败准备重试 attempt={} err={}", attempt, e)
                    except Exception:
                        pass
                    await self._async_sleep(_delay)
                else:
                    break
        # 全部失败：记录日志并降级
        try:
            import asyncio as _asyncio
            latency_ms = int((_time.perf_counter() - t0) * 1000)
            _asyncio.create_task(self._save_ai_call_log(
                conversation_id=conversation_id,
                model_name=model_name,
                endpoint="chat.completions",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                use_rag=bool(use_rag),
                rag_context_len=len(rag_context or ""),
                metadata_context_len=len((metadata_ctx or "")),
                rag_chunks=rag_chunks,
                status="error",
                error_message=str(last_err) if last_err else None,
            ))
        except Exception:
            pass
        rb3 = self._rule_based_sql(nl_query)
        if rb3:
            logger.info("模型调用失败，使用规则兜底SQL")
            return rb3
        logger.warning(f"AI模型调用失败，降级为占位SQL: {last_err}")
        return "SELECT 1 AS placeholder;"

    async def _async_sleep(self, seconds: float):
        """异步延时"""
        import asyncio
        await asyncio.sleep(max(0.0, float(seconds)))

    async def _save_ai_call_log(
        self,
        conversation_id: Optional[int],
        model_name: Optional[str],
        endpoint: Optional[str],
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: int,
        use_rag: bool,
        rag_context_len: int,
        metadata_context_len: int,
        rag_chunks: Optional[list],
        status: str,
        error_message: Optional[str],
    ):
        """保存AI调用日志到数据库"""
        try:
            from app.models.ai_conversation import AICallLog
            from app.models.query import QueryStatus
            from app.core.database import AsyncSessionLocal
            log = AICallLog(
                conversation_id=conversation_id,
                model_name=model_name or settings.AI_MODEL_NAME,
                endpoint=endpoint or "chat.completions",
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
                total_tokens=int(total_tokens or 0),
                latency_ms=int(latency_ms or 0),
                use_rag=bool(use_rag),
                rag_context_len=int(rag_context_len or 0),
                metadata_context_len=int(metadata_context_len or 0),
                rag_chunks=rag_chunks,
                status=QueryStatus.SUCCESS if status == "success" else QueryStatus.ERROR,
                error_message=error_message,
            )
            async with AsyncSessionLocal() as s:
                s.add(log)
                await s.flush()
                await s.commit()
        except Exception as e:
            try:
                logger.warning("保存AI调用日志失败: {}", e)
            except Exception:
                pass