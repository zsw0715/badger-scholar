# this file is used to clear the dataset for testing purposes
# it will clear all data in mongodb, elasticsearch, and chromadb

import os
import shutil
from pymongo import MongoClient
from app.services.elasticsearch_service import ElasticsearchService
import chromadb

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB", "badger_db")

ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "papers")  # align with ES service default

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_data")

def clear_mongodb():
    client = MongoClient(MONGO_URI)
    client.drop_database(MONGO_DB)
    client.close()
    print(f"✅ MongoDB database '{MONGO_DB}' dropped.")


def clear_elasticsearch():
    """
    Mirror backend Elasticsearch service behaviour:
    - default index is 'papers'
    - optionally delete all indices by setting ELASTIC_INDEX='*'
    """
    es_service = ElasticsearchService()
    index_name = ELASTIC_INDEX.strip() or "papers"

    if index_name == "*":
        es_service.es.options(ignore_status=[400, 404]).indices.delete(
            index="*",
            expand_wildcards="all"
        )
        print("✅ Elasticsearch: deleted all indices (expand_wildcards=all).")
    else:
        result = es_service.delete_index()
        status = "✅" if result.get("success") else "⚠️"
        print(f"{status} {result.get('message')}")


def clear_chromadb():
    shutil.rmtree(CHROMA_PERSIST_DIR, ignore_errors=True)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    print(f"✅ ChromaDB data directory '{CHROMA_PERSIST_DIR}' cleared.")


def main():
    clear_mongodb()
    clear_elasticsearch()
    clear_chromadb()
    print("🎉 All backends cleared.")


if __name__ == "__main__":
    main()
