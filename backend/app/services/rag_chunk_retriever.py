# this file handles:
# fine-grained retrieval from full-text chunks (ChromaDB)
# input: user question
# output: top-k relevant chunks

import os
from typing import List, Dict

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


# ========= Configuration =========
CHROMA_PERSIST_DIR = "/app/chroma_data"
CHROMA_COLLECTION_NAME = "papers_fulltext_chunks"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class ChunkRetriever:
  """
  The fine-grained retriever:
  1. embed question
  2. search ChromaDB chunk collection
  3. return the most relevant chunks
  """

  def __init__(self):
    # Load embedding model
    print("Loading embedding model for chunk retriever:", EMBEDDING_MODEL)
    self.model = SentenceTransformer(EMBEDDING_MODEL)

    # Connect to ChromaDB
    print("Connecting to Chroma (fulltext chunks)...")
    # self.chroma_client = chromadb.Client(Settings(
    #     chroma_db_impl="duckdb+parquet",
    #     persist_directory=CHROMA_PERSIST_DIR
    # ))
    self.chroma_client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR
    )

    # Load chunk-level collection
    self.collection = self.chroma_client.get_or_create_collection(
        CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    print("✅ ChunkRetriever ready.")

  # ========= Main function =========
  def retrieve_chunks(self, question: str, top_k: int = 5) -> List[Dict]:
    """
    Input:
        question   : The user query (string)
        top_k      : Number of chunks to retrieve

    Output:
        A list of dicts:
        [
            {
                "chunk_id": "...",
                "arxiv_id": "...",
                "text": "...",
                "score": float
            }
        ]
    """

    # ---- Step 1: embed question ----
    query_embedding = self.model.encode(question).tolist()

    # ---- Step 2: Chroma similarity search ----
    results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # Chroma's return structure looks like:
    # {
    #   "ids": [[...]],
    #   "documents": [[...]],
    #   "metadatas": [[...]],
    #   "distances": [[...]]
    # }

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results.get("distances", [[0]*len(ids)])[0]

    # ---- Step 3: format nicely ----
    ranked = []
    for i in range(len(ids)):
      ranked.append({
          "chunk_id": ids[i],
          "arxiv_id": metadatas[i].get("arxiv_id"),
          "text": documents[i],
          "score": 1 - distances[i]   # convert distance to similarity
      })

    # sort descending by score
    ranked = sorted(ranked, key=lambda x: x["score"], reverse=True)

    return ranked


# Singleton
chunk_retriever = ChunkRetriever()