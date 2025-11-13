# app/api/rag.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/rag", tags=["RAG"])


# ========= Request & Response Models =========

class RAGQueryRequest(BaseModel):
    question: str = Field(..., description="User question")
    top_k_papers: int = Field(5, description="Summary-level coarse retrieval count")
    top_k_chunks: int = Field(8, description="Full-text fine retrieval chunk count")


class RAGQueryResponse(BaseModel):
    answer: str
    papers: list
    chunks: list


# ========= API Endpoint =========

@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(req: RAGQueryRequest):
    """
    Run the full RAG pipeline:

    1. Coarse retrieval (summary embeddings)
    2. Fine retrieval (full-text chunks)
    3. LLM answer grounded in retrieved context
    """
    try:
        result = rag_service.answer_question(
            question=req.question,
            top_k_papers=req.top_k_papers,
            top_k_chunks=req.top_k_chunks,
        )

        return RAGQueryResponse(
            answer=result["answer"],
            papers=result["papers"],
            chunks=result["chunks"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {str(e)}"
        )