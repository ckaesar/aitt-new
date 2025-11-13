from fastapi import APIRouter
from app.services.metadata_index import MetadataIndexer
from app.services.metadata_search import MetadataSearch
from loguru import logger
import os
import json
import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy.engine.url import make_url
from app.core.config import settings

router = APIRouter(tags=["metadata"])


@router.post("/sync")
def sync_metadata_index():
    """
    触发一次全量同步：将 MySQL 中的元数据（数据源/表/字段）与 ChromaDB 索引对齐。
    """
    indexer = MetadataIndexer()
    summary = indexer.sync_all()
    return {"status": "ok", "summary": summary}


@router.get("/last-sync")
def get_last_sync_summary():
    """
    返回最近一次元数据同步的摘要信息（从 MySQL 表 aitt_metadata_sync_summaries 读取）。
    若无记录，返回占位信息。
    """
    try:
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
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    sources_total, tables_total, columns_total,
                    deleted_sources, deleted_tables, deleted_columns,
                    upserted_sources, upserted_tables, upserted_columns,
                    last_sync_time
                FROM aitt_metadata_sync_summaries
                ORDER BY last_sync_time DESC, id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
        try:
            conn.close()
        except Exception:
            pass
        if not row:
            return {
                "status": "ok",
                "summary": {
                    "sources_total": 0,
                    "tables_total": 0,
                    "columns_total": 0,
                    "deleted_sources": 0,
                    "deleted_tables": 0,
                    "deleted_columns": 0,
                    "upserted_sources": 0,
                    "upserted_tables": 0,
                    "upserted_columns": 0,
                    "last_sync_time": None,
                },
            }
        # 格式化时间为 ISO 字符串
        lst = row.get("last_sync_time")
        if lst is not None:
            try:
                row["last_sync_time"] = lst.isoformat(sep=" ", timespec="seconds")
            except Exception:
                row["last_sync_time"] = str(lst)
        return {"status": "ok", "summary": row}
    except Exception as e:
        logger.warning("读取最近同步摘要失败: {}", e)
        return {"status": "error", "message": str(e)}


@router.get("/diag/chroma-counts")
def get_chroma_counts():
    """
    诊断 Chroma 元数据集合中的条目数量（source/table/column）。
    便于确认手动同步后索引是否已落库。
    """
    try:
        ms = MetadataSearch()
        counts = ms.get_counts_by_type()
        available = bool(getattr(ms, "collection", None))
        return {
            "status": "ok",
            "counts": counts,
            "collection": settings.CHROMA_METADATA_COLLECTION_NAME,
            "available": available,
            "persist_dir": getattr(settings, "CHROMA_PERSIST_DIRECTORY", "./chroma_db"),
        }
    except Exception as e:
        logger.warning("获取 Chroma 计数失败: {}", e)
        return {"status": "error", "message": str(e)}