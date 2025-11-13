import os
import sys

def main():
    print("=== Python 环境诊断 ===")
    try:
        import platform, struct
        print("python_version:", sys.version)
        print("arch:", platform.architecture()[0])
        print("pointer_bits:", struct.calcsize('P') * 8)
    except Exception as e:
        print("PY_INFO_ERROR:", type(e).__name__, str(e))

    persist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_db"))
    print("persist_dir:", persist_dir, "exists:", os.path.isdir(persist_dir))

    print("=== Chroma 诊断 ===")
    try:
        import chromadb
        from chromadb.config import Settings
        print("chromadb_import: OK")
        try:
            client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
            print("client_init: OK")
            col = client.get_or_create_collection(name="query_embeddings")
            res = col.get()
            total_ids = len(res.get("ids", []) or [])
            print("collection_get: OK, total_ids:", total_ids)
        except Exception as e:
            print("CHROMA_CLIENT_ERROR:", type(e).__name__, str(e))
    except Exception as e:
        print("CHROMA_IMPORT_ERROR:", type(e).__name__, str(e))

if __name__ == "__main__":
    main()