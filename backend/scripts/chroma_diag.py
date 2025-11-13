import os
import sys

def main():
    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.api.types import Include
    except Exception as e:
        print("IMPORT_ERROR:", type(e).__name__, str(e))
        sys.exit(2)

    persist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_db"))
    print("persist_dir:", persist_dir, "exists:", os.path.isdir(persist_dir))

    try:
        client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
        print("client: OK")
    except Exception as e:
        print("CLIENT_ERROR:", type(e).__name__, str(e))
        sys.exit(3)

    try:
        col = client.get_or_create_collection(name="metadata_embeddings")
        print("collection: OK")
        res = col.get(include=[Include.metadatas, Include.ids])
        ids = res.get("ids", []) or []
        print("total_ids:", len(ids))
    except Exception as e:
        print("COLLECTION_ERROR:", type(e).__name__, str(e))
        sys.exit(4)

if __name__ == "__main__":
    main()