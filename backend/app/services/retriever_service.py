# this file
# 从 ChromaDB 做 向量检索（semantic search）
# 根据用户问题找到最相关的论文摘要
# 为后续的 LLM 生成做准备

# Goal: 给一个 query（自然语言），得到 top-k 相似论文（根据 title+summary embedding 匹配）。

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict

CHROMA_PERSIST_DIR = "/app/chroma_data"
CHROMA_COLLECTION_NAME = "papers_embeddings"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class RetrieverService:
    """
    Retrieve top-k similar papers using vector embeddings from ChromaDB.
    """
    def __init__(self):
        # Load embedding model (same as indexing)
        print("Loading embedding model:", EMBEDDING_MODEL)
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # Connect Chroma
        print("Connecting to ChromaDB...")

        self.chroma = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR
        )

        # Load existing collection
        self.collection = self.chroma.get_or_create_collection(
            CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        print("RetrieverService initialized! ")
  
    # ========= Build embedding for query =========
    def embed_query(self, query: str):
        """Convert user query -> embedding vector"""
        # self.model 是 SentenceTransformer 实例，encode() 方法返回 numpy.ndarray(一个 shape 为 384 的向量，这个向量对应着 all-MiniLM-L6-v2 模型的输出)
        # 然后这个向量会被用来在 ChromaDB 里做向量搜索
        return self.model.encode([query])[0]   # shape (384,)  this is the shape of all-MiniLM-L6-v2
  
    # ========= Search collection =========
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Top-k semantic search

        Return format:
        [
            {
                "arxiv_id": "...",
                "score": ...,
                "title": "...",
                "document": "Title: ...\n\nAbstract: ...",
            }
        ]
        """
        query_embedding = self.embed_query(query)
    
        # 把上一步返回的 embedding 向量传给 ChromaDB，做向量搜索, collection 是 ChromaDB 里的一个“表”
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,        # 返回 top_k 个最相似的结果
            include=["distances", "documents", "metadatas"]     # 需要返回的字段，包括距离、文本内容、元数据
        )
        # 之前的 "distance" 可以用来选择相似度评分，通过 1 - distance 转换为 similarity score
        # "documents" 是之前写入的文本内容 《《Title: ...\n\nAbstract: ...》》
        # "metadatas" 包含 arxiv_id, title, primary_category 等信息
    
        # Chroma returns list-of-lists
        docs = result["documents"][0]
        metas = result["metadatas"][0]
        dists = result["distances"][0]
    
        # Convert distance → similarity score
        def to_score(d):
            return round(1 - d, 4)  # cosine distance => similarity

        final = []
        for doc, meta, dist in zip(docs, metas, dists):
            final.append({
                "arxiv_id": meta["arxiv_id"],
                "title": meta["title"],
                "primary_category": meta.get("primary_category"),
                "document": doc,
                "score": to_score(dist)
            })

        return final

# Singleton
retriever_service = RetrieverService()
