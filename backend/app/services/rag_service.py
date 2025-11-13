# # app/services/rag_service.py

# """
# RAG Orchestrator:
# - coarse retrieval from summary embeddings
# - fine retrieval from full-text chunks
# - call LLM to generate final answer
# """

# import os
# from typing import List, Dict, Any

# from app.services.retriever_service import retriever_service
# from app.services.rag_chunk_retriever import chunk_retriever

# from pymongo import MongoClient

# # ==== Optional: LLM (OpenAI) ====
# try:
#     import openai
#     HAS_OPENAI = True
# except ImportError:
#     HAS_OPENAI = False


# # ======== LLM Client Wrapper =========

# from openai import OpenAI

# class LLMClient:
#     """
#     Wrapper around the new OpenAI Python SDK (>=1.0).
#     """

#     def __init__(self):
#         api_key = os.getenv("OPENAI_API_KEY")
#         if not api_key:
#             raise RuntimeError("OPENAI_API_KEY not set in environment.")

#         # Create the client
#         self.client = OpenAI(api_key=api_key)
#         self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

#     def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
#         """
#         Use the new openai.chat.completions.create() API.
#         """
#         try:
#             response = self.client.chat.completions.create(
#                 model=self.model,
#                 messages=[
#                     {"role": "system", "content": system_prompt},
#                     {"role": "user", "content": user_prompt},
#                 ],
#                 temperature=0.2,
#             )
#             return response.choices[0].message.content.strip()

#         except Exception as e:
#             raise RuntimeError(f"OpenAI LLM call failed: {e}")


# # ======== RAG Service =========

# class RagService:
#     """
#     End-to-end RAG pipeline:

#     1. Use summary-level retriever to find relevant papers
#     2. Use chunk-level retriever to fetch fine-grained context
#     3. Build a prompt with context + question
#     4. Call LLM to generate answer
#     """

#     def __init__(self):
#         # coarse & fine retrievers
#         self.coarse_retriever = retriever_service
#         self.chunk_retriever = chunk_retriever

#         # LLM client (OpenAI for now)
#         self.llm_client = LLMClient()

#         # Mongo (optional, e.g. later for logging user queries or pulling extra metadata)
#         mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
#         self.mongo_client = MongoClient(mongo_uri)
#         db_name = os.getenv("MONGO_DB", "badger_db")
#         self.db = self.mongo_client[db_name]
#         self.paper_coll = self.db[os.getenv("MONGO_COLL", "papers")]

#         print("✅ RagService initialized.")

#     # ------ Build context text from chunks ------
#     @staticmethod
#     def _build_context_from_chunks(chunks: List[Dict], max_chunks_for_prompt: int = 5) -> str:
#         """
#         Turn retrieved chunks into a big context string for the LLM.
#         """
#         context_blocks = []
#         for i, ch in enumerate(chunks[:max_chunks_for_prompt]):
#             block = (
#                 f"[Source {i+1}] arxiv_id={ch.get('arxiv_id')} | "
#                 f"chunk_id={ch.get('chunk_id')}\n"
#                 f"{ch.get('text', '')}"
#             )
#             context_blocks.append(block)

#         return "\n\n".join(context_blocks)

#     # ------ Build final user prompt ------
#     @staticmethod
#     def _build_user_prompt(question: str, context: str) -> str:
#         """
#         Combine context + user question into a single prompt.
#         """
#         prompt = (
#             "You are an AI assistant that answers questions about academic papers.\n"
#             "Use ONLY the following context excerpts from papers to answer the question.\n"
#             "If the answer is not clearly supported by the context, say you are not sure.\n\n"
#             "=== CONTEXT START ===\n"
#             f"{context}\n"
#             "=== CONTEXT END ===\n\n"
#             f"Question: {question}\n\n"
#             "Answer in clear, concise academic English.\n"
#         )
#         return prompt

#     # ------ Main entry: answer question ------
#     def answer_question(
#         self,
#         question: str,
#         top_k_papers: int = 5,
#         top_k_chunks: int = 8,
#     ) -> Dict[str, Any]:
#         """
#         Run the full RAG pipeline and return:
#           {
#             "answer": str,
#             "papers": [... coarse retrieval results ...],
#             "chunks": [... fine-grained chunks used ...]
#           }
#         """

#         # 1. Coarse retrieval on summary embeddings
#         coarse_results = self.coarse_retriever.search(
#             query=question,
#             top_k=top_k_papers
#         )

#         # # 2. Fine retrieval on full-text chunks
#         # # NOTE: 当前版本不对 arxiv_id 做过滤，而是在所有 chunks 上检索。
#         # #       以后可以扩展：只在 coarse 的 arxiv_id 范围内搜。
#         # fine_chunks = self.chunk_retriever.retrieve_chunks(
#         #     question=question,
#         #     top_k=top_k_chunks
#         # )
#         # 2. Fine retrieval restricted to coarse arxiv_ids
#         candidate_ids = set([p["arxiv_id"] for p in coarse_results])

#         all_chunks = self.chunk_retriever.retrieve_chunks(
#             question=question,
#             top_k=50   # retrieve more globally
#         )

#         # filter only the chunks belonging to the coarse papers
#         fine_chunks = [
#             c for c in all_chunks
#             if c["arxiv_id"] in candidate_ids
#         ][:top_k_chunks]

#         # 3. Build context string
#         context_str = self._build_context_from_chunks(fine_chunks)

#         # 4. Build prompts
#         system_prompt = (
#             "You are a helpful assistant that answers questions based on academic papers.\n"
#             "You must ground your answers only on the given context excerpts."
#         )
#         user_prompt = self._build_user_prompt(question, context_str)

#         # 5. Call LLM
#         answer_text = self.llm_client.generate_answer(
#             system_prompt=system_prompt,
#             user_prompt=user_prompt
#         )

#         # 6. Return structured result
#         return {
#             "answer": answer_text,
#             "papers": coarse_results,   # summary-level
#             "chunks": fine_chunks,      # actual text used to answer
#         }


# # Singleton instance
# rag_service = RagService()

# app/services/rag_service.py
import os
from typing import List, Dict, Any

from pymongo import MongoClient

from app.services.retriever_service import retriever_service
from app.services.rag_chunk_retriever import chunk_retriever
from app.services.fulltext_indexer import fulltext_indexer

from openai import OpenAI


class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment.")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        res = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return res.choices[0].message.content.strip()


class RagService:
    def __init__(self):
        self.coarse_retriever = retriever_service
        self.chunk_retriever = chunk_retriever
        self.llm = LLMClient()

        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[os.getenv("MONGO_DB", "badger_db")]
        self.paper_coll = self.db[os.getenv("MONGO_COLL", "papers")]

        print("✅ RagService initialized.")

    # ===== BUILD CONTEXT =====
    @staticmethod
    def _build_context(chunks: List[Dict], max_chunks=5):
        blocks = []
        for i, c in enumerate(chunks[:max_chunks]):
            blocks.append(
                f"[Source {i+1}] arxiv_id={c['arxiv_id']} | chunk={c['chunk_id']}\n{c['text']}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _user_prompt(question: str, ctx: str) -> str:
        return (
            "You are an AI assistant answering based on the provided context.\n"
            "If the context does not contain the answer, say 'I am not sure.'\n\n"
            "=== CONTEXT START ===\n"
            f"{ctx}\n"
            "=== CONTEXT END ===\n\n"
            f"Question: {question}\n"
        )

    # ===== MAIN ENTRY =====
    def answer_question(self, question: str, top_k_papers=5, top_k_chunks=10):

        # --- 1. Coarse retrieval ---
        coarse = self.coarse_retriever.search(question, top_k_papers)
        arxiv_ids = [p["arxiv_id"] for p in coarse]

        # --- 2. Ensure full-text exists (auto fulltext index) ---
        for aid in arxiv_ids:
            paper = self.paper_coll.find_one({"arxiv_id": aid})
            if paper and not paper.get("fulltext_indexed", False):
                print(f"📥 Fulltext not found for {aid}, generating now...")
                fulltext_indexer.process_single_paper(paper)

        # --- 3. Fine retrieval restricted to coarse arxiv_ids ---
        raw_chunks = self.chunk_retriever.retrieve_chunks(question, top_k=100)
        fine_chunks = [c for c in raw_chunks if c["arxiv_id"] in arxiv_ids][:top_k_chunks]

        # --- 4. Build context ---
        context = self._build_context(fine_chunks)

        # --- 5. LLM answer ---
        system_prompt = "You answer ONLY using the provided context."
        user_prompt = self._user_prompt(question, context)

        answer = self.llm.generate_answer(system_prompt, user_prompt)

        # --- 6. Return structured result ---
        return {
            "answer": answer,
            "papers": coarse,
            "chunks": fine_chunks,
        }


# Singleton
rag_service = RagService()