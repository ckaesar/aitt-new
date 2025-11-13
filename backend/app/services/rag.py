from typing import List, Optional, Dict
import os
import json
from loguru import logger

# 取消模块级导入chromadb，避免因可选依赖缺失导致服务启动失败
CHROMA_AVAILABLE = False

from app.core.config import settings


class RAGService:
    def __init__(self):
        # 回退存储：当chromadb不可用时，使用本地JSONL文件持久化
        try:
            persist_dir = settings.CHROMA_PERSIST_DIRECTORY
        except Exception:
            persist_dir = "./chroma_db"
        self._fallback_dir = persist_dir
        self._fallback_store = os.path.join(self._fallback_dir, "fallback_rag_store.jsonl")
        # 确保目录存在
        try:
            os.makedirs(self._fallback_dir, exist_ok=True)
        except Exception:
            pass
        # 延迟初始化 chromadb 客户端/集合
        self.client = None
        self.collection = None
        self._client_initialized = False
        logger.info("RAG 初始化: 使用惰性chromadb加载策略，回退目录='{}'", self._fallback_dir)

    def _ensure_client(self):
        """惰性初始化 chromadb 客户端与集合，失败则保持回退模式。"""
        if self._client_initialized and self.collection is not None:
            return
        try:
            # 在方法内进行可选依赖导入，避免模块级副作用
            import chromadb  # type: ignore
            from chromadb.config import Settings as ChromaSettings  # type: ignore
            # 可选：配置嵌入函数提升检索相关性（若环境支持则启用）
            embedding_fn = None
            try:
                from chromadb.utils import embedding_functions as _ef  # type: ignore
                try:
                    embedding_fn = _ef.SentenceTransformerEmbeddingFunction(
                        model_name="paraphrase-multilingual-MiniLM-L12-v2"
                    )
                except Exception:
                    embedding_fn = _ef.SentenceTransformerEmbeddingFunction(
                        model_name="all-MiniLM-L6-v2"
                    )
            except Exception:
                embedding_fn = None
            global CHROMA_AVAILABLE
            CHROMA_AVAILABLE = True
            persist_dir = settings.CHROMA_PERSIST_DIRECTORY
            client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            collection_name = settings.CHROMA_COLLECTION_NAME
            if embedding_fn is not None:
                collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=embedding_fn,
                )
            else:
                collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            self.client = client
            self.collection = collection
            self._client_initialized = True
            try:
                logger.info(
                    "RAG 惰性初始化成功: path='{}', collection='{}', embedding_fn_enabled={}",
                    persist_dir,
                    collection_name,
                    bool(embedding_fn is not None),
                )
            except Exception:
                pass
        except Exception as e:
            self.client = None
            self.collection = None
            self._client_initialized = False
            CHROMA_AVAILABLE = False
            logger.warning("RAG chromadb 初始化失败，使用回退存储: {}", e)

    # -------- 回退存储实现 --------
    def _fallback_load(self) -> List[Dict[str, str]]:
        docs: List[Dict[str, str]] = []
        if not os.path.exists(self._fallback_store):
            return docs
        try:
            with open(self._fallback_store, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        doc = json.loads(line)
                        if isinstance(doc, dict) and "text" in doc:
                            docs.append(doc)
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("RAG 回退存储读取失败: {}", e)
        return docs

    def _fallback_save(self, docs: List[Dict[str, str]]):
        try:
            with open(self._fallback_store, "w", encoding="utf-8") as f:
                for d in docs:
                    f.write(json.dumps(d, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("RAG 回退存储写入失败: {}", e)

    def upsert_documents(self, docs: List[Dict[str, str]]):
        """docs: [{id, text, source}]"""
        # 惰性尝试连接chromadb
        self._ensure_client()
        if not CHROMA_AVAILABLE or self.collection is None:
            # 使用回退存储追加/更新
            store_docs = self._fallback_load()
            # 按id去重更新
            index_by_id: Dict[str, int] = {}
            for i, d in enumerate(store_docs):
                if d.get("id"):
                    index_by_id[d["id"]] = i
            for d in docs:
                doc_id = d.get("id") or f"auto_{len(store_docs)+1}"
                item = {"id": doc_id, "text": d.get("text", ""), "source": d.get("source", "unknown")}
                if doc_id in index_by_id:
                    store_docs[index_by_id[doc_id]] = item
                else:
                    store_docs.append(item)
            self._fallback_save(store_docs)
            try:
                logger.info(
                    "RAG 回退写入完成: count={}, ids_sample={}, sources_sample={}",
                    len(docs),
                    [d.get("id") for d in docs[:3]],
                    [d.get("source") for d in docs[:3]],
                )
            except Exception:
                pass
            return
        ids = [d["id"] for d in docs]
        texts = [d["text"] for d in docs]
        metadatas = [{"source": d.get("source", "unknown")} for d in docs]
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        try:
            logger.info(
                "RAG upsert 完成: count={}, ids_sample={}, sources_sample={}",
                len(ids),
                ids[:3],
                [m.get("source") for m in metadatas[:3]],
            )
        except Exception:
            pass

    def query(self, text: str, top_k: int = 4) -> List[Dict[str, str]]:
        # 惰性尝试连接chromadb
        self._ensure_client()
        if not CHROMA_AVAILABLE or self.collection is None:
            logger.warning("RAG 使用回退存储进行查询：chromadb不可用或集合为空")
            docs = self._fallback_load()
            if not docs:
                return []
            # 改进评分：中文/英文关键词包含 + 字符重叠（更鲁棒）
            q = (text or "").strip().lower()
            try:
                import re as _re
                kws = [k.lower() for k in _re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]{2,}", q)]
            except Exception:
                kws = [w for w in q.split() if len(w) >= 2]
            scored: List[Dict[str, str]] = []
            for d in docs:
                t_raw = d.get("text", "")
                t = t_raw.lower()
                score = 0
                for k in kws:
                    if k and k in t:
                        score += 10
                try:
                    overlap = len(set(q) & set(t))
                except Exception:
                    overlap = 0
                score += overlap
                scored.append({"text": t_raw, "source": d.get("source", "unknown"), "_score": score})
            scored.sort(key=lambda x: x.get("_score", 0), reverse=True)
            out = [{"text": s["text"], "source": s["source"]} for s in scored[:max(1, top_k)]]
            try:
                logger.info(
                    "RAG 回退查询返回(改进评分): count={}, sources={}",
                    len(out),
                    [c.get("source") for c in out],
                )
            except Exception:
                pass
            return out
        logger.info("RAG query 入参: len(text)={}, top_k={}", len(text or ""), top_k)
        res = self.collection.query(query_texts=[text], n_results=top_k)
        out = []
        for docs, metas in zip(res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]):
            out.append({"text": docs, "source": metas.get("source", "unknown")})
        # 若chromadb查询为空，尝试回退存储进行检索（提升健壮性）
        if not out:
            try:
                logger.warning("RAG chroma结果为空，启用回退检索作为补充")
            except Exception:
                pass
            # 复用改进回退评分逻辑
            docs_fb = self._fallback_load()
            if docs_fb:
                q = (text or "").strip().lower()
                try:
                    import re as _re
                    kws = [k.lower() for k in _re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]{2,}", q)]
                except Exception:
                    kws = [w for w in q.split() if len(w) >= 2]
                scored_fb: List[Dict[str, str]] = []
                for d in docs_fb:
                    t_raw = d.get("text", "")
                    t = t_raw.lower()
                    score = 0
                    for k in kws:
                        if k and k in t:
                            score += 10
                    try:
                        overlap = len(set(q) & set(t))
                    except Exception:
                        overlap = 0
                    score += overlap
                    scored_fb.append({"text": t_raw, "source": d.get("source", "unknown"), "_score": score})
                scored_fb.sort(key=lambda x: x.get("_score", 0), reverse=True)
                out = [{"text": s["text"], "source": s["source"]} for s in scored_fb[:max(1, top_k)]]
        try:
            logger.info(
                "RAG query 返回: count={}, sources={}",
                len(out),
                [c.get("source") for c in out],
            )
        except Exception:
            pass
        return out

    def get_context_for_query(self, text: str, top_k: int = 4) -> str:
        chunks = self.query(text, top_k=top_k)
        # 关键字过滤：要求查询文本与片段存在关键词重叠，否则丢弃
        q = (text or "").strip().lower()
        kws: List[str] = []
        try:
            import re as _re
            kws = [k.lower() for k in _re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]{2,}", q)]
        except Exception:
            kws = [w for w in q.split() if len(w) >= 2]
        def _overlap(t: str) -> bool:
            if not kws:
                return True
            s = (t or "").lower()
            return any(k in s for k in kws)
        filtered = [c for c in chunks if _overlap(c.get('text',''))]
        context_lines = [f"[来源:{c['source']}] {c['text']}" for c in filtered]
        ctx = "\n".join(context_lines)
        try:
            logger.info(
                "RAG context 构建(过滤后): chunks={}, sources={}, len(ctx)={}",
                len(filtered),
                [c.get("source") for c in filtered],
                len(ctx),
            )
        except Exception:
            pass
        return ctx