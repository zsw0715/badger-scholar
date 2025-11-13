# app/services/vector_index_service.py
# this file is mongodb -> chromadb
# add new fields to mongodb: vector_indexed, embedding_model
# Embedding Pipeline

import os
from typing import List, Dict, Optional

from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import chromadb

# ==== Configuration ====
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

CHROMA_PERSIST_DIR = "/app/chroma_data"
CHROMA_COLLECTION_NAME = "papers_embeddings"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


class VectorIndexService:
    """Handles embedding generation and ChromaDB indexing."""

    def __init__(self):
        # ----- MongoDB -----
        self.mongo_client = MongoClient(MONGO_URI)
        self.mongo_coll = self.mongo_client[DB_NAME][COLL_NAME]

        # ----- Embedding model -----
        print("Loading embedding model:", EMBEDDING_MODEL)
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # ----- ChromaDB -----
        print("Connecting to ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        self.chroma_coll = self.chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}  # cosine 距离
        )

        print("✅ VectorIndexService initialized.")

    # ========= Load unindexed docs =========
    def load_unindexed_papers(self, limit: Optional[int] = None) -> List[Dict]:
        """
        从 MongoDB 里加载还没有被向量化的论文。
        规则： vector_indexed != True 的都算“未索引”
        （包括字段不存在 / false / null）
        """
        query = {"vector_indexed": {"$ne": True}}
        cursor = self.mongo_coll.find(query)

        if limit:
            cursor = cursor.limit(limit)

        papers = list(cursor)
        print(f"Loaded {len(papers)} unindexed papers from MongoDB")
        return papers

    # ========= Build text for embedding =========
    @staticmethod
    def build_text(paper: Dict) -> str:
        """使用 title + summary 构建 embedding 输入文本。"""
        title = paper.get("title", "").strip()
        summary = paper.get("summary", "").strip()
        if not title and not summary:
            return ""
        return f"Title: {title}\n\nAbstract: {summary}"

    # ========= Embed & Write to Chroma =========
    def embed_and_index(self, papers: List[Dict]) -> int:
        if not papers:
            print("⚠️ No papers to index in this batch.")
            return 0

        # mongo_ids 用来更新 Mongo
        # chroma_ids 必须是 str，用来写入 Chroma
        mongo_ids = []
        chroma_ids = []
        texts = []
        metadatas = []

        for paper in papers:
            text = self.build_text(paper)
            if not text.strip():
                continue

            mongo_id = paper["_id"]
            chroma_id = str(mongo_id)

            mongo_ids.append(mongo_id)
            chroma_ids.append(chroma_id)
            texts.append(text)

            metadatas.append({
                "arxiv_id": paper.get("arxiv_id"),
                "title": paper.get("title"),
                "primary_category": paper.get("primary_category"),
            })

        if not texts:
            print("⚠️ All papers in this batch had empty text, skip.")
            return 0

        print(f"🧠 Embedding {len(texts)} papers...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=BATCH_SIZE
        )

        print("💾 Writing embeddings to Chroma...")
        self.chroma_coll.add(
            ids=chroma_ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings
        )

        # 更新 Mongo，打标记
        for mid in mongo_ids:
            self.mongo_coll.update_one(
                {"_id": mid},
                {"$set": {
                    "vector_indexed": True,
                    "embedding_model": EMBEDDING_MODEL
                }}
            )

        print(f"✅ Indexed {len(chroma_ids)} papers in this batch.")
        return len(chroma_ids)

    # ========= Entry point =========
    def run_indexing(self, limit: Optional[int] = None, batch_size: int = BATCH_SIZE) -> int:
        papers = self.load_unindexed_papers(limit)
        if not papers:
            print("All papers indexed.")
            return 0

        total = len(papers)
        print(f"\n🚀 Starting vector indexing for {total} papers...")

        indexed_total = 0

        for i in range(0, total, batch_size):
            batch = papers[i:i + batch_size]
            print(f"\n📦 Batch {i // batch_size + 1}")
            indexed_total += self.embed_and_index(batch)

        print("\n🎉 Completed")
        print(f"Total indexed: {indexed_total}")
        print(f"Remaining (unindexed, by this run): {total - indexed_total}")

        return indexed_total


# Singleton
vector_index_service = VectorIndexService()