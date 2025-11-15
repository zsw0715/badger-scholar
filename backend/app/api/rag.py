# app/api/rag.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.rag_service import rag_service
from app.services.vector_index_service import vector_index_service
from app.services.fulltext_indexer import fulltext_indexer

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

class VectorSyncRequest(BaseModel):
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Only sync this many pending papers (None = sync all pending papers)."
    )

class VectorSyncResponse(BaseModel):
    status: str
    indexed_count: int
    message: str

class VectorSyncStatusResponse(BaseModel):
    mongodb_count: int
    chromadb_count: int
    in_sync: bool

class FulltextSyncStatusResponse(BaseModel):
    chromadb_count: int
    fulltext_indexed_papers: int
    in_sync: bool


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

@router.post("/sync-coarse", response_model=VectorSyncResponse)
async def sync_coarse_embeddings(req: Optional[VectorSyncRequest] = None):
    """
    Trigger coarse-grained vector indexing so MongoDB summaries are synced to ChromaDB.
    """
    try:
        limit = req.limit if req else None
        indexed_total = vector_index_service.run_indexing(limit=limit)

        if indexed_total == 0:
            status = "noop"
            message = "All papers already vector indexed."
        else:
            status = "success"
            message = f"Indexed {indexed_total} papers into ChromaDB."

        return VectorSyncResponse(
            status=status,
            indexed_count=indexed_total,
            message=message,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vector sync failed: {str(e)}"
        )

@router.get("/sync-status", response_model=VectorSyncStatusResponse)
async def get_vector_sync_status():
    """
    Compare MongoDB vs ChromaDB counts for coarse embeddings.
    """
    try:
        status = vector_index_service.get_sync_status()
        return VectorSyncStatusResponse(**status)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sync status: {str(e)}"
        )

@router.get("/sync-status/fulltext", response_model=FulltextSyncStatusResponse)
async def get_fulltext_sync_status():
    """
    Compare MongoDB vs ChromaDB counts for fine (full-text chunk) embeddings.
    """
    try:
        status = fulltext_indexer.get_sync_status()
        return FulltextSyncStatusResponse(**status)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch fulltext sync status: {str(e)}"
        )
