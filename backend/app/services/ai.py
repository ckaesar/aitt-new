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
        - 利用元数据结构化匹配，尝试识别订单表、日期列、金额/GMV列
        - 生成近7天订单数量与GMV统计SQL（MySQL语法）
        返回None表示无法可靠生成。
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
            # 关键词集合
            order_kw = ["order", "orders", "交易", "订单"]
            date_kw = ["date", "dt", "时间", "日期", "created_at", "order_date", "下单"]
            amt_kw = ["amount", "total_amount", "gmv", "price", "pay", "支付", "金额", "交易额"]

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

            tname = pick_table()
            if not tname:
                return None
            cols = matches[tname].get("columns") or []
            date_col = pick_col(cols, date_kw) or "created_at"
            amt_col = pick_col(cols, amt_kw) or "amount"
            # 是否包含近7天意图
            has_7d = any(k in q for k in ["近7天", "最近7天", "past 7", "last 7", "近七天"])
            date_cond = "DATE_SUB(CURDATE(), INTERVAL 7 DAY)" if has_7d else "DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            sql = (
                f"SELECT COUNT(*) AS order_count, SUM({amt_col}) AS gmv\n"
                f"FROM {tname}\n"
                f"WHERE DATE({date_col}) >= {date_cond};"
            )
            return sql
        except Exception as e:
            logger.warning("规则兜底生成失败: {}", e)
            return None

    async def generate_sql(self, nl_query: str, context: Optional[str] = None, use_rag: bool = True, rag_context: Optional[str] = None) -> str:
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

        try:
            client = OpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY)
            # 使用 Chat Completions，要求仅输出SQL
            completion = client.chat.completions.create(
                model=settings.AI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是资深数据分析助理，只输出合法SQL，不要解释，不要包含代码块标记。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=512,
            )
            content = completion.choices[0].message.content or ""
            # 5) 规整输出：去除反引号代码块与前后噪音，只保留首段以 SELECT/WITH/INSERT/UPDATE/DELETE 开头的SQL
            cleaned = content.strip()
            # 去掉 ```sql/``` 包裹
            cleaned = re.sub(r"^```sql\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"```\s*$", "", cleaned)
            # 提取首个以常见SQL关键字开头的段落
            m = re.search(r"\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b[\s\S]*", cleaned, flags=re.IGNORECASE)
            if m:
                sql_text = m.group(0).strip()
            else:
                # 若模型未严格遵循，仅返回整段内容
                sql_text = cleaned

            # 简单兜底：若最终为空，返回占位SQL
            if sql_text:
                logger.info(f"AI生成SQL成功: {sql_text[:500]}")
                return sql_text
            else:
                # 模型返回空内容时尝试规则兜底
                rb2 = self._rule_based_sql(nl_query)
                if rb2:
                    logger.info("模型返回空，使用规则兜底SQL")
                    return rb2
                logger.warning("AI返回空内容，降级为占位SQL")
                return "SELECT 1 AS placeholder;"
        except Exception as e:
            # 调用失败兜底并记录原因
            # 调用失败时尝试规则兜底
            rb3 = self._rule_based_sql(nl_query)
            if rb3:
                logger.info("模型调用失败，使用规则兜底SQL")
                return rb3
            logger.warning(f"AI模型调用失败，降级为占位SQL: {e}")
            return "SELECT 1 AS placeholder;"