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
from tqdm import tqdm

from app.services.fulltext_service import fulltext_service

# ==== Configuration ====
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

CHROMA_PERSIST_DIR = "/app/chroma_data"
CHROMA_COLLECTION_NAME = "papers_fulltext_chunks"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


# ====== Utility: clean unsafe PDF text ======
def clean_chunk_text(text):
    """Make text 100% safe for SentenceTransformer."""
    if not isinstance(text, str):
        return ""

    # Remove control characters: \x00 - \x1F and \x7F
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Force utf-8 encoding (remove illegal byte sequences)
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

        # Load embedding model
        print("Loading embedding model:", EMBEDDING_MODEL)
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # ChromaDB
        print("Connecting to ChromaDB (fulltext)...")
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        self.collection_db = self.chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        print("FullTextIndexer initialized! ")

    # --------- Load unindexed papers ----------
    def load_unindexed(self, limit: Optional[int] = None) -> List[Dict]:
        query = {"fulltext_indexed": {"$ne": True}}
        cursor = self.collection.find(query)

        if limit:
            cursor = cursor.limit(limit)

        papers = list(cursor)
        print(f"Loaded {len(papers)} unindexed full-text papers")
        return papers

    # --------- Process one paper ----------
    def process_single_paper(self, paper: Dict) -> int:
        arxiv_id = paper["arxiv_id"]
        print(f"\n📄 Processing full text: {arxiv_id}")

        # Step 1: extract chunks
        chunks = fulltext_service.get_fulltext_chunks(arxiv_id)
        if not chunks:
            print("⚠️ No chunks extracted.")
            return 0

        ids, texts, metadatas = [], [], []
        skipped = 0

        for c in chunks:
            raw_text = c["text"]
            safe_text = clean_chunk_text(raw_text)

            if not safe_text:
                skipped += 1
                continue

            ids.append(c["chunk_id"])
            texts.append(safe_text)

            metadatas.append({
                "arxiv_id": arxiv_id,
                "chunk_id": c["chunk_id"]
            })

        if skipped > 0:
            print(f"⚠️ Skipped {skipped} invalid chunks")

        if not texts:
            print("❌ All chunks invalid, skipping this paper.")
            return 0

        # Step 2: embedding
        print(f"Embedding {len(texts)} chunks...")
        embeddings = self.model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=True
        )

        # Step 3: save to Chroma
        print("Saving to ChromaDB...")
        self.collection_db.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings
        )

        # Step 4: update MongoDB
        self.collection.update_one(
            {"_id": paper["_id"]},
            {"$set": {
                "fulltext_indexed": True,
                "fulltext_embedding_model": EMBEDDING_MODEL
            }}
        )

        print(f"✅ Done: {arxiv_id} ({len(texts)} valid chunks)")
        return len(texts)

    # --------- Main pipeline ----------
    def run_indexing(self, limit: Optional[int] = None):
        papers = self.load_unindexed(limit=limit)
        if not papers:
            print("All full-text papers already indexed.")
            return 0

        total = len(papers)
        print(f"\n🚀 Starting full-text indexing for {total} papers.")

        total_chunks = 0
        for paper in papers:
            total_chunks += self.process_single_paper(paper)

        print("\n==============================")
        print("🎉 Full-Text Indexing Completed")
        print(f"Total papers processed: {total}")
        print(f"Total chunks indexed: {total_chunks}")
        print("==============================")

        # self.chroma_client.persist()
        return total_chunks


# Singleton
fulltext_indexer = FullTextIndexer()