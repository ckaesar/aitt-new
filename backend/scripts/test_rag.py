import sys

sys.path.append("./backend")

from app.services.rag import RAGService


def main():
    rag = RAGService()
    # 插入示例文档（若 chromadb 未安装，则此处为无操作）
    rag.upsert_documents([
        {"id": "doc1", "text": "员工工资表包含字段：员工ID、姓名、部门、工资、发放日期。", "source": "schema.md"},
        {"id": "doc2", "text": "查询员工工资可按部门和日期范围过滤，结果按发放日期降序。", "source": "guide.md"},
    ])
    ctx = rag.get_context_for_query("员工工资查询", top_k=4)
    print("[RAG TEST] START")
    print("RAG 上下文: \n" + (ctx or "<empty>"))
    print("[RAG TEST] END")


if __name__ == "__main__":
    main()