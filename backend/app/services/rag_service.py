# app/services/rag_service.py
"""
RAG Orchestrator:
- Stage 1: coarse retrieval from summary embeddings (Mongo + Chroma 'papers_embeddings')
- Stage 2: on-demand fulltext indexing + fine retrieval from full-text chunks
- call LLM to generate final answer
"""

import os
from typing import List, Dict, Any

from pymongo import MongoClient

from app.services.retriever_service import retriever_service
from app.services.rag_chunk_retriever import chunk_retriever
from app.services.fulltext_indexer import fulltext_indexer

from openai import OpenAI


# ======== LLM Client Wrapper =========
class LLMClient:
    """
    Wrapper around the new OpenAI Python SDK (>=1.0).
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment.")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()


# ======== RAG Service =========
class RagService:
    """
    End-to-end two-stage RAG:

    1. Stage 1: summary-level retriever to find relevant papers (coarse)
    2. Stage 2: for those papers, ensure full-text is indexed, then do chunk-level retrieval (fine)
    3. Build context from fine chunks and call LLM.
    """

    def __init__(self):
        # coarse & fine retrievers
        self.coarse_retriever = retriever_service
        self.chunk_retriever = chunk_retriever

        # LLM client
        self.llm_client = LLMClient()

        # Mongo
        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
        self.mongo_client = MongoClient(mongo_uri)
        db_name = os.getenv("MONGO_DB", "badger_db")
        self.db = self.mongo_client[db_name]
        self.paper_coll = self.db[os.getenv("MONGO_COLL", "papers")]

        print("✅ RagService initialized.")

    # ------ Build context text from chunks ------
    @staticmethod
    def _build_context_from_chunks(chunks: List[Dict], max_chunks_for_prompt: int = 5) -> str:
        """
        Turn retrieved chunks into a big context string for the LLM.
        """
        context_blocks = []
        for i, ch in enumerate(chunks[:max_chunks_for_prompt]):
            block = (
                f"[Source {i+1}] arxiv_id={ch.get('arxiv_id')} | "
                f"chunk_id={ch.get('chunk_id')}\n"
                f"{ch.get('text', '')}"
            )
            context_blocks.append(block)

        return "\n\n".join(context_blocks)

    # ------ Build final user prompt ------
    @staticmethod
    def _build_user_prompt(question: str, context: str) -> str:
        template = (
            "You are an AI assistant that answers questions strictly based on the provided context.\n"
            "\n"
            "If the context contains ANY relevant information — even partial —\n"
            "you MUST use it to construct an answer.\n"
            "\n"
            "Only if the context contains ZERO relevant content, say \"I am not sure.\"\n"
            "\n"
            "=== CONTEXT START ===\n"
            "{context}\n"
            "=== CONTEXT END ===\n"
            "\n"
            "Question: {question}\n"
            "\n"
            "Provide a direct, concise academic answer."
        )
        return template.format(context=context, question=question)

    # ------ Main entry: answer question ------
    def answer_question(
        self,
        question: str,
        top_k_papers: int = 5,
        top_k_chunks: int = 8,
    ) -> Dict[str, Any]:
        """
        Run the full 2-stage RAG pipeline and return:
          {
            "answer": str,
            "papers": [... coarse retrieval results ...],
            "chunks": [... fine-grained chunks used ...]
          }
        """

        # === Coarse retrieval on summary embeddings ===
        coarse_results = self.coarse_retriever.search(
            query=question,
            top_k=top_k_papers
        )
        arxiv_ids = [p["arxiv_id"] for p in coarse_results]

        # === Ensure full-text chunks exist for these papers (on-demand indexing) ===
        #    如果某篇 paper 还没有 fulltext_indexed，就在这里调用 fulltext_indexer 生成
        for aid in arxiv_ids:
            paper = self.paper_coll.find_one({"arxiv_id": aid})
            if paper and not paper.get("fulltext_indexed", False):
                print(f"Fulltext not indexed for {aid}, indexing now...")
                fulltext_indexer.process_single_paper(paper)

        # === Fine retrieval restricted to coarse arxiv_ids ===
        # 先全局取一个稍大的 top_k，比如 100，然后过滤到 coarse 的那几篇 paper
        raw_chunks = self.chunk_retriever.retrieve_chunks(
            question=question,
            top_k=100
        )

        fine_chunks = [
            c for c in raw_chunks
            if c.get("arxiv_id") in arxiv_ids
        ][:top_k_chunks]

        # === Build context string ===
        context_str = self._build_context_from_chunks(fine_chunks)

        # === Call LLM ===
        system_prompt = (
            "You are a helpful assistant that answers questions based only on the given context excerpts."
        )
        user_prompt = self._build_user_prompt(question, context_str)

        answer_text = self.llm_client.generate_answer(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # === Return structured result ===
        return {
            "answer": answer_text,
            "papers": coarse_results,
            "chunks": fine_chunks,
        }


# Singleton instance
rag_service = RagService()
