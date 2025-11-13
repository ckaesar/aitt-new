"""
元数据检索服务：从 Chroma 的元数据集合中查询相关文本，构造用于SQL生成的上下文。
"""
from typing import List, Dict, Optional, DefaultDict
from collections import defaultdict
from loguru import logger

# 运行时惰性导入 chromadb，避免在启动阶段因可选依赖缺失而崩溃
chromadb = None
ChromaSettings = None

from app.core.config import settings


class MetadataSearch:
    def __init__(self):
        self.client = None
        self.collection = None
        self.available = False
        # 初始化时不强制导入，延迟到第一次使用，保证服务可启动

    def _ensure_client(self):
        """惰性导入并初始化chroma客户端与集合。"""
        if self.collection is not None:
            self.available = True
            return
        try:
            global chromadb, ChromaSettings
            if chromadb is None or ChromaSettings is None:
                import chromadb as _ch
                from chromadb.config import Settings as _ChromaSettings
                chromadb = _ch
                ChromaSettings = _ChromaSettings
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            # 绑定嵌入函数以支持 query_texts
            ef = None
            try:
                from chromadb.utils import embedding_functions as _ef
                try:
                    ef = _ef.SentenceTransformerEmbeddingFunction(
                        model_name="paraphrase-multilingual-MiniLM-L12-v2"
                    )
                except Exception:
                    ef = _ef.SentenceTransformerEmbeddingFunction(
                        model_name="all-MiniLM-L6-v2"
                    )
            except Exception:
                ef = None

            if ef is not None:
                self.collection = self.client.get_or_create_collection(
                    name=settings.CHROMA_METADATA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=ef,
                )
            else:
                self.collection = self.client.get_or_create_collection(
                    name=settings.CHROMA_METADATA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            self.available = True
            logger.info(
                "MetadataSearch 初始化: dir='{}', collection='{}'",
                settings.CHROMA_PERSIST_DIRECTORY,
                settings.CHROMA_METADATA_COLLECTION_NAME,
            )
        except Exception as e:
            self.client = None
            self.collection = None
            self.available = False
            logger.warning("MetadataSearch 初始化失败: {}", e)

    def query(self, text: str, top_k: int = 6) -> List[Dict[str, str]]:
        self._ensure_client()
        if not self.available or self.collection is None:
            return []
        try:
            res = self.collection.query(query_texts=[text], n_results=top_k)
            out: List[Dict[str, str]] = []
            docs_list = res.get("documents", [[]])[0]
            metas_list = res.get("metadatas", [[]])[0]
            ids_list = res.get("ids", [[]])[0]
            for doc, meta, id_ in zip(docs_list, metas_list, ids_list):
                item: Dict[str, str] = {
                    "id": id_,
                    "text": doc,
                    "type": meta.get("type", "unknown"),
                    "source": meta.get("source", "metadata"),
                }
                # 带上有用的元信息，便于后续分组
                for k in [
                    "table_id", "table_name", "table_display_name",
                    "column_id", "column_name", "data_type", "is_dimension", "is_metric",
                    "data_source_id",
                ]:
                    if meta.get(k) is not None:
                        item[k] = meta.get(k)
                out.append(item)
            return out
        except Exception as e:
            logger.warning("MetadataSearch 查询失败: {}", e)
            return []

    def get_context_for_query(self, text: str, top_k: int = 6) -> str:
        items = self.query(text, top_k=top_k)
        # 以类型标识拼接上下文，便于提示词识别
        lines = []
        for it in items:
            t = it.get("type", "?")
            lines.append(f"[{t}] {it.get('text','')}")
        ctx = "\n".join(lines)
        try:
            logger.info("MetadataSearch 上下文构建: count={}, len(ctx)={}", len(items), len(ctx))
        except Exception:
            pass
        return ctx

    def get_grouped_context_for_query(self, text: str, top_k: int = 10) -> str:
        """
        以“表 -> 列”结构化上下文返回，便于模型理解：
        Table: table_name (display_name)
          - column_name: data_type [D][M]
        """
        items = self.query(text, top_k=top_k)
        tables: DefaultDict[str, Dict] = defaultdict(lambda: {
            "display_name": None,
            "columns": [],
        })
        # 先收集表项
        for it in items:
            if it.get("type") == "table":
                tname = it.get("table_name") or ""
                if not tname:
                    # 尝试从文本中提取表名（保留原始做法作为兜底）
                    tname = it.get("text", "")[:64]
                tables[tname]["display_name"] = it.get("table_display_name")
        # 再收集列项并挂到表上
        for it in items:
            if it.get("type") == "column":
                tname = it.get("table_name") or ""
                col = it.get("column_name") or ""
                dtype = it.get("data_type") or ""
                is_dim = str(it.get("is_dimension", "")).lower() in ("true", "1")
                is_met = str(it.get("is_metric", "")).lower() in ("true", "1")
                if tname:
                    tables[tname]["columns"].append({
                        "name": col,
                        "type": dtype,
                        "is_dim": is_dim,
                        "is_met": is_met,
                    })
        # 构造上下文文本
        lines: List[str] = []
        for tname, info in tables.items():
            dname = info.get("display_name")
            head = f"Table: {tname}"
            if dname:
                head += f" ({dname})"
            lines.append(head)
            for c in info.get("columns") or []:
                flags = ""
                if c.get("is_dim"):
                    flags += " [D]"
                if c.get("is_met"):
                    flags += " [M]"
                lines.append(f"  - {c.get('name')}: {c.get('type')}{flags}")
        ctx = "\n".join(lines)
        try:
            logger.info("MetadataSearch 结构化上下文构建: tables={}, len(ctx)={}", len(tables), len(ctx))
        except Exception:
            pass
        # 若结构化为空，回退到普通上下文
        return ctx or self.get_context_for_query(text, top_k=top_k)

    def get_structured_matches_for_query(self, text: str, top_k: int = 12) -> Dict[str, Dict]:
        """
        返回结构化匹配结果，便于规则兜底：
        {
          table_name: {
            "display_name": str | None,
            "columns": [{"name": str, "type": str, "is_dim": bool, "is_met": bool}],
          }, ...
        }

        同时进行简单的关键字过滤：要求查询文本中的关键词与表/列名或文本存在至少一个重叠。
        """
        items = self.query(text, top_k=top_k)
        # 提取关键词（英文字母数字词 + 连续中文字符，长度>=2）
        q = (text or "").strip().lower()
        kw: List[str] = []
        try:
            import re as _re
            kw = [k.lower() for k in _re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]{2,}", q)]
        except Exception:
            kw = [w for w in q.split() if len(w) >= 2]

        def _match_any(s: str | None) -> bool:
            if not kw:
                return True
            t = (s or "").lower()
            return any(k in t for k in kw)

        tables: DefaultDict[str, Dict] = defaultdict(lambda: {
            "display_name": None,
            "columns": [],
        })

        # 先收集表项，进行关键字过滤
        for it in items:
            if it.get("type") == "table":
                tname = it.get("table_name") or ""
                if not tname:
                    tname = it.get("text", "")[:64]
                if not _match_any(tname) and not _match_any(it.get("text")):
                    continue
                tables[tname]["display_name"] = it.get("table_display_name")

        # 收集列项（仅纳入已匹配的表），也进行关键字过滤
        for it in items:
            if it.get("type") == "column":
                tname = it.get("table_name") or ""
                col = it.get("column_name") or ""
                dtype = it.get("data_type") or ""
                is_dim = str(it.get("is_dimension", "")).lower() in ("true", "1")
                is_met = str(it.get("is_metric", "")).lower() in ("true", "1")
                if not tname or tname not in tables:
                    continue
                # 列关键字过滤（列名或文本匹配任意关键词）
                if not _match_any(col) and not _match_any(it.get("text")):
                    continue
                tables[tname]["columns"].append({
                    "name": col,
                    "type": dtype,
                    "is_dim": is_dim,
                    "is_met": is_met,
                })

        # 去除无列的空表，保留至少一个列匹配
        filtered = {t: info for t, info in tables.items() if (info.get("columns") or [])}
        try:
            logger.info("MetadataSearch 结构化匹配: input_kw={}, tables_ret={}", kw[:8], len(filtered))
        except Exception:
            pass
        return filtered

    def get_counts_by_type(self) -> Dict[str, int]:
        """统计集合中不同type（source/table/column）的条目数量，用于诊断索引状态。"""
        self._ensure_client()
        if not self.available or self.collection is None:
            return {"source": 0, "table": 0, "column": 0}
        counts: Dict[str, int] = {}
        for t in ("source", "table", "column"):
            try:
                # Chromadb 在不同版本中对 include 参数的支持不一致，ids 总是默认返回，这里不显式传入 include 以保证兼容
                res = self.collection.get(where={"type": t}, limit=100000)
                counts[t] = len(res.get("ids", []))
            except Exception as e:
                logger.warning("MetadataSearch 统计失败 type={} error={}", t, e)
                counts[t] = 0
        try:
            logger.info("MetadataSearch 类型计数: {}", counts)
        except Exception:
            pass
        return counts