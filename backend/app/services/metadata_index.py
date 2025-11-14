"""
基于混合方案的元数据索引同步服务：
- 以 MySQL 中的事实元数据（数据源/数据表/字段）为准；
- 将可检索的描述信息增量/全量同步到 ChromaDB（向量索引），支持增删改；
- 提供 upsert 与删除逻辑，确保索引与数据库一致；
"""
from typing import List, Dict, Tuple
from datetime import datetime
from loguru import logger

# 惰性导入 chromadb 及其 embedding 函数，避免服务启动时因可选依赖缺失而崩溃
chromadb = None
ChromaSettings = None
embedding_functions = None

import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy.engine.url import make_url

from app.core.config import settings
from app.services.rag import RAGService


def _open_mysql_conn():
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
    return conn


def _build_source_text(row: Dict) -> str:
    return (
        f"[source] 名称:{row.get('name','')} 类型:{row.get('type','')} "
        f"描述:{row.get('description','')} 主机:{row.get('host','')}:{row.get('port','')} "
        f"库:{row.get('database_name','')} 用户:{row.get('username','')}."
    ).strip()


def _build_table_text(row: Dict) -> str:
    return (
        f"[table] 表:{row.get('table_name','')} 描述:{row.get('description','')} "
        f"分类:{row.get('category','')} 所属数据源:{row.get('data_source_id')} "
        f"行数:{row.get('row_count','')} 体积MB:{row.get('size_mb','')}"
    ).strip()


def _build_column_text(row: Dict) -> str:
    dim = "是" if row.get("is_dimension") else "否"
    met = "是" if row.get("is_metric") else "否"
    nullable = "是" if row.get("is_nullable") else "否"
    return (
        f"[column] 列:{row.get('column_name','')} 类型:{row.get('data_type','')} "
        f"可空:{nullable} 维度:{dim} 度量:{met} 顺序:{row.get('column_order','')} "
        f"描述:{row.get('description','')} 所属表:{row.get('table_id')}"
    ).strip()


class MetadataIndexer:
    def __init__(self):
        self._client = None
        self._collection = None
        self._ef = None
        self._available = False
        # 初始化不做导入，按需惰性初始化

    def _ensure_client(self):
        """惰性初始化 chroma 客户端与集合，embedding 函数可选。"""
        if self._collection is not None:
            self._available = True
            return
        try:
            global chromadb, ChromaSettings, embedding_functions
            if chromadb is None or ChromaSettings is None:
                import chromadb as _ch
                from chromadb.config import Settings as _ChromaSettings
                chromadb = _ch
                ChromaSettings = _ChromaSettings
            if embedding_functions is None:
                try:
                    from chromadb.utils import embedding_functions as _ef
                    embedding_functions = _ef
                except Exception:
                    embedding_functions = None
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            # 尝试加载嵌入函数；失败则置空
            try:
                if embedding_functions is not None:
                    try:
                        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                            model_name="paraphrase-multilingual-MiniLM-L12-v2"
                        )
                    except Exception:
                        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                            model_name="all-MiniLM-L6-v2"
                        )
                else:
                    self._ef = None
            except Exception:
                self._ef = None

            # 创建集合时若可用则绑定嵌入函数，保证后续 query_texts 可用
            if self._ef is not None:
                self._collection = self._client.get_or_create_collection(
                    name=settings.CHROMA_METADATA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=self._ef,
                )
            else:
                self._collection = self._client.get_or_create_collection(
                    name=settings.CHROMA_METADATA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            self._available = True
            logger.info(
                "MetadataIndexer 初始化: dir='{}', collection='{}'",
                settings.CHROMA_PERSIST_DIRECTORY,
                settings.CHROMA_METADATA_COLLECTION_NAME,
            )
        except Exception as e:
            self._client = None
            self._collection = None
            self._ef = None
            self._available = False
            # 打印完整异常堆栈并输出关键配置，便于定位问题
            logger.exception(
                "MetadataIndexer 初始化失败: dir='{}', collection='{}'",
                settings.CHROMA_PERSIST_DIRECTORY,
                settings.CHROMA_METADATA_COLLECTION_NAME,
            )

    # --- 内部工具 ---
    def _get_existing_ids_by_type(self, type_: str) -> List[str]:
        self._ensure_client()
        if not self._collection:
            return []
        try:
            # 在当前 chromadb 版本中不支持 include=['ids']，默认返回 ids
            res = self._collection.get(where={"type": type_})
            return res.get("ids", []) or []
        except Exception:
            return []

    def _delete_ids(self, ids: List[str]):
        self._ensure_client()
        if not self._collection or not ids:
            return
        try:
            self._collection.delete(ids=ids)
        except Exception as e:
            logger.warning("删除旧索引失败: {}", e)

    def _upsert_batch(self, items: List[Tuple[str, Dict, str]]):
        """items: [(id, metadata, document_text)]"""
        self._ensure_client()
        if not self._collection:
            logger.warning("集合不可用，跳过 upsert {} 条", len(items))
            return
        ids = [i[0] for i in items]
        metas = [i[1] for i in items]
        docs = [i[2] for i in items]
        try:
            # 若提供 embedding function，可在客户端侧生成向量（Chromadb也支持服务端嵌入）
            if self._ef is not None:
                # 统一批量生成嵌入以提高性能
                try:
                    embs = self._ef(docs)
                    self._collection.upsert(ids=ids, metadatas=metas, documents=docs, embeddings=embs)
                except Exception:
                    # 若嵌入生成失败，退化为不显式提供嵌入，由集合绑定的函数处理
                    self._collection.upsert(ids=ids, metadatas=metas, documents=docs)
            else:
                self._collection.upsert(ids=ids, metadatas=metas, documents=docs)
        except Exception as e:
            logger.warning("upsert 索引失败: {}", e)

    # --- 同步入口 ---
    def sync_all(self) -> Dict[str, int]:
        """全量比对并同步：
        - 删除: Chromadb 中存在但 MySQL 已不存在的条目；
        - upsert: 将 MySQL 中的所有现存元数据写入/更新到 Chromadb；
        返回统计信息。
        """
        # 若不可用则直接返回空统计
        self._ensure_client()
        if not self._collection:
            logger.warning("sync_all: chroma集合不可用，返回空统计")
            return {"upsert_sources": 0, "upsert_tables": 0, "upsert_columns": 0,
                    "deleted_sources": 0, "deleted_tables": 0, "deleted_columns": 0}
        conn = _open_mysql_conn()
        try:
            with conn.cursor() as cur:
                # 数据源
                cur.execute(
                    """
                    SELECT id, name, type, host, port, database_name, username, description,
                           is_active, created_by, created_at, updated_at
                    FROM aitt_data_sources
                    ORDER BY id
                    """
                )
                sources = cur.fetchall() or []

                # 数据表
                cur.execute(
                    """
                    SELECT id, data_source_id, table_name, display_name, description, category,
                           row_count, size_mb, created_at, updated_at
                    FROM aitt_data_tables
                    ORDER BY id
                    """
                )
                tables = cur.fetchall() or []

                # 字段
                cur.execute(
                    """
                    SELECT id, table_id, column_name, display_name, data_type, is_nullable, description,
                           is_dimension, is_metric, column_order, created_at, updated_at
                    FROM aitt_table_columns
                    ORDER BY id
                    """
                )
                columns = cur.fetchall() or []

            # 计算应保留的ID集合
            want_source_ids = {f"source:{int(x['id'])}" for x in sources}
            want_table_ids = {f"table:{int(x['id'])}" for x in tables}
            want_column_ids = {f"column:{int(x['id'])}" for x in columns}

            # 已存在索引ID（按类型）
            have_source_ids = set(self._get_existing_ids_by_type("source"))
            have_table_ids = set(self._get_existing_ids_by_type("table"))
            have_column_ids = set(self._get_existing_ids_by_type("column"))

            # 删除多余项
            del_source = list(have_source_ids - want_source_ids)
            del_table = list(have_table_ids - want_table_ids)
            del_column = list(have_column_ids - want_column_ids)
            self._delete_ids(del_source)
            self._delete_ids(del_table)
            self._delete_ids(del_column)

            # upsert 所有当前项
            up_source_items: List[Tuple[str, Dict, str]] = []
            for s in sources:
                sid = f"source:{int(s['id'])}"
                text = _build_source_text(s)
                meta = {
                    "type": "source",
                    "source_id": int(s["id"]),
                    "name": s.get("name"),
                    "database_name": s.get("database_name"),
                    "updated_at": str(s.get("updated_at") or ""),
                }
                up_source_items.append((sid, meta, text))

            # 建立表ID到表名/展示名的映射，便于列元数据携带表信息
            table_name_map = {int(t["id"]): (t.get("table_name"), t.get("display_name")) for t in tables}

            up_table_items: List[Tuple[str, Dict, str]] = []
            for t in tables:
                tid = f"table:{int(t['id'])}"
                text = _build_table_text(t)
                meta = {
                    "type": "table",
                    "table_id": int(t["id"]),
                    "data_source_id": int(t.get("data_source_id") or 0),
                    "table_name": t.get("table_name"),
                    "display_name": t.get("display_name"),
                    "updated_at": str(t.get("updated_at") or ""),
                }
                up_table_items.append((tid, meta, text))

            up_column_items: List[Tuple[str, Dict, str]] = []
            for c in columns:
                cid = f"column:{int(c['id'])}"
                text = _build_column_text(c)
                tname, tdisp = table_name_map.get(int(c.get("table_id") or 0), (None, None))
                meta = {
                    "type": "column",
                    "column_id": int(c["id"]),
                    "table_id": int(c.get("table_id") or 0),
                    "column_name": c.get("column_name"),
                    "data_type": c.get("data_type"),
                    "is_dimension": bool(c.get("is_dimension")),
                    "is_metric": bool(c.get("is_metric")),
                    "table_name": tname,
                    "table_display_name": tdisp,
                    "updated_at": str(c.get("updated_at") or ""),
                }
                up_column_items.append((cid, meta, text))

            # 批量写入
            self._upsert_batch(up_source_items)
            self._upsert_batch(up_table_items)
            self._upsert_batch(up_column_items)

            # 汇总统计并记录时间戳
            now_dt = datetime.now()
            summary = {
                "sources_total": len(sources),
                "tables_total": len(tables),
                "columns_total": len(columns),
                "deleted_sources": len(del_source),
                "deleted_tables": len(del_table),
                "deleted_columns": len(del_column),
                "upserted_sources": len(up_source_items),
                "upserted_tables": len(up_table_items),
                "upserted_columns": len(up_column_items),
                "last_sync_time": now_dt.isoformat(timespec="seconds"),
            }
            logger.info("元数据索引同步完成: {}", summary)
            # 从元数据派生任务型文档并写入文档RAG集合，提升检索可用性
            try:
                docs = []
                ds_by_id = {int(s["id"]): s for s in sources}
                cols_by_table: Dict[int, List[Dict]] = {}
                for c in columns:
                    tid = int(c.get("table_id") or 0)
                    cols_by_table.setdefault(tid, []).append(c)
                table_names = {int(t["id"]): str(t.get("table_name") or "") for t in tables}
                name_set = set(x for x in table_names.values() if x)
                def _rel_guess(col_name: str) -> str | None:
                    n = (col_name or "").lower()
                    if n.endswith("_id"):
                        base = n[:-3]
                        cand1 = base
                        cand2 = base + "s"
                        if cand1 in name_set:
                            return cand1
                        if cand2 in name_set:
                            return cand2
                    return None
                for t in tables:
                    tid = int(t["id"])
                    tname = str(t.get("table_name") or "")
                    tdisp = str(t.get("display_name") or "")
                    dsid = int(t.get("data_source_id") or 0)
                    ds = ds_by_id.get(dsid)
                    cols = cols_by_table.get(tid) or []
                    dim_cols = [str(c.get("column_name")) for c in cols if bool(c.get("is_dimension"))]
                    met_cols = [str(c.get("column_name")) for c in cols if bool(c.get("is_metric"))]
                    common_keys = ["id","name","category","brand","price","email","phone","city","address","status"]
                    pick = []
                    for k in common_keys:
                        for c in cols:
                            cn = str(c.get("column_name") or "")
                            if k in cn.lower() and cn not in pick:
                                pick.append(cn)
                    if not pick:
                        for c in cols:
                            if bool(c.get("is_dimension")):
                                pick.append(str(c.get("column_name")))
                                if len(pick) >= 6:
                                    break
                    rels = []
                    for c in cols:
                        g = _rel_guess(str(c.get("column_name") or ""))
                        if g:
                            rels.append((str(c.get("column_name") or ""), g))
                    rel_desc = "; ".join([f"{cn} -> {tn}" for cn, tn in rels]) if rels else ""
                    dss = str(ds.get("name") if ds else "")
                    doc_text = (
                        f"数据源 {dss} 的表 {tname}" + (f" ({tdisp})" if tdisp else "") +
                        (f"：常用字段：{', '.join(pick)}" if pick else "") +
                        (f"；维度：{', '.join(dim_cols)}" if dim_cols else "") +
                        (f"；指标：{', '.join(met_cols)}" if met_cols else "") +
                        (f"；关联：{rel_desc}" if rel_desc else "")
                    ).strip()
                    if doc_text:
                        docs.append({"id": f"doc:table:{tid}", "text": doc_text, "source": "metadata-doc"})
                for s in sources:
                    sid = int(s["id"])
                    doc_text = (
                        f"数据源 {str(s.get('name') or '')}：类型 {str(s.get('type') or '')}，库 {str(s.get('database_name') or '')}。"
                    ).strip()
                    if doc_text:
                        docs.append({"id": f"doc:source:{sid}", "text": doc_text, "source": "metadata-doc"})
                if docs:
                    try:
                        rag = RAGService()
                        rag.upsert_documents(docs)
                        logger.info("同步派生任务文档写入: {}", len(docs))
                    except Exception as e:
                        logger.warning("写入任务文档失败: {}", e)
            except Exception as e:
                logger.warning("生成任务文档异常: {}", e)
            # 将最近一次同步摘要写入 MySQL 表，供接口/前端查询
            try:
                with conn.cursor() as write_cur:
                    write_cur.execute(
                        """
                        INSERT INTO aitt_metadata_sync_summaries (
                            sources_total, tables_total, columns_total,
                            deleted_sources, deleted_tables, deleted_columns,
                            upserted_sources, upserted_tables, upserted_columns,
                            last_sync_time
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            len(sources), len(tables), len(columns),
                            len(del_source), len(del_table), len(del_column),
                            len(up_source_items), len(up_table_items), len(up_column_items),
                            now_dt,
                        ),
                    )
                conn.commit()
            except Exception as e:
                logger.warning("写入最近同步摘要到数据库失败: {}", e)
            return summary
        finally:
            try:
                conn.close()
            except Exception:
                pass