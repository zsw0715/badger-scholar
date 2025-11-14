# app/services/fulltext_indexer.py
# this file handles:
# full text chunk → embedding → ChromaDB
# add new MongoDB fields:
#   fulltext_indexed: bool
#   fulltext_embedding_model: str

import os
import re
from typing import Dict, List, Optional

from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import chromadb

from app.services.fulltext_service import fulltext_service

# ==== Configuration ====
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

CHROMA_PERSIST_DIR = "/app/chroma_data"
CHROMA_COLLECTION_NAME = "papers_fulltext_chunks"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


def clean_chunk_text(text: str) -> str:
    """
    Make text safe for SentenceTransformer:
    - remove control chars
    - force utf-8
    - strip insane repetitions
    """
    if not isinstance(text, str):
        return ""

    # Remove control characters: \x00 - \x1F and \x7F
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Force utf-8 encoding (drop invalid bytes)
    text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")

    # Remove extremely long repeated characters (PDF corruption)
    text = re.sub(r"(.)\1{20,}", r"\1", text)

    return text.strip()


class FullTextIndexer:
    """
    Downloads PDF → extracts full text → chunks → embed → save to ChromaDB.
    """

    def __init__(self):
        # MongoDB
        self.mongo_client = MongoClient(MONGO_URI)
        self.collection = self.mongo_client[DB_NAME][COLL_NAME]

        # Embedding model
        print("Loading embedding model:", EMBEDDING_MODEL)
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # ChromaDB (persistent client, 不需要手动 persist())
        print("Connecting to ChromaDB (fulltext)...")
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        self.collection_db = self.chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        print("✅ FullTextIndexer initialized.")

    # --------- Load unindexed papers ----------
    def load_unindexed(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Find all papers without fulltext_indexed=True
        """
        query = {"fulltext_indexed": {"$ne": True}}
        cursor = self.collection.find(query)

        if limit:
            cursor = cursor.limit(limit)

        papers = list(cursor)
        print(f"Loaded {len(papers)} unindexed full-text papers")
        return papers

    # --------- Process one paper ----------
    def process_single_paper(self, paper: Dict) -> int:
        """
        1. get fulltext chunks
        2. clean each chunk
        3. embed + write to Chroma
        4. mark Mongo as fulltext_indexed
        """
        arxiv_id = paper["arxiv_id"]
        print(f"\n📄 Processing full text: {arxiv_id}")

        # Step 1: extract chunks
        chunks = fulltext_service.get_fulltext_chunks(arxiv_id)
        if not chunks:
            print("⚠️ No chunks extracted.")
            return 0

        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict] = []
        skipped = 0

        for c in chunks:
            raw_text = c.get("text", "")
            safe_text = clean_chunk_text(raw_text)

            if not safe_text:
                skipped += 1
                continue

            ids.append(c["chunk_id"])
            texts.append(safe_text)
            metadatas.append({
                "arxiv_id": arxiv_id,
                "chunk_id": c["chunk_id"],
            })

        if skipped > 0:
            print(f"⚠️ Skipped {skipped} invalid/empty chunks")

        if not texts:
            print("❌ All chunks invalid, skipping this paper.")
            return 0

        # Step 2: embedding
        print(f"🧠 Embedding {len(texts)} chunks...")
        embeddings = self.model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
        )

        # Step 3: save to Chroma
        print("💾 Saving to ChromaDB...")
        self.collection_db.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        # Step 4: update MongoDB
        self.collection.update_one(
            {"_id": paper["_id"]},
            {"$set": {
                "fulltext_indexed": True,
                "fulltext_embedding_model": EMBEDDING_MODEL,
            }}
        )

        print(f"✅ Done: {arxiv_id} ({len(texts)} valid chunks)")
        return len(texts)

    # --------- Index only specific arxiv_ids ----------
    def index_specific_papers(self, arxiv_ids: List[str]) -> int:
        """
        Only download + embed for the specified arxiv_ids
        (skip those already fulltext_indexed=True)
        """
        query = {
            "arxiv_id": {"$in": arxiv_ids},
            "fulltext_indexed": {"$ne": True},
        }
        papers = list(self.collection.find(query))
        print(f"Need to index fulltext for {len(papers)} papers")

        total_chunks = 0
        for p in papers:
            total_chunks += self.process_single_paper(p)

        return total_chunks

    # --------- Main pipeline ----------
    def run_indexing(self, limit: Optional[int] = None) -> int:
        papers = self.load_unindexed(limit=limit)
        if not papers:
            print("All full-text papers already indexed.")
            return 0

        total = len(papers)
        print(f"\n🚀 Starting full-text indexing for {total} papers.")

        total_chunks = 0
        for p in papers:
            total_chunks += self.process_single_paper(p)

        print("\n==============================")
        print("🎉 Full-Text Indexing Completed")
        print(f"Total papers processed: {total}")
        print(f"Total chunks indexed: {total_chunks}")
        print("==============================")

        return total_chunks


# Singleton
fulltext_indexer = FullTextIndexer()