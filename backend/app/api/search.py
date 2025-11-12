from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.elasticsearch_service import es_service
from app.services.sync_to_es import sync_papers_to_es, get_sync_status

router = APIRouter(prefix="/api/search", tags=["Search"])

@router.get("")
async def search_papers(
  q: str = Query(..., description="Search query"),
  category: Optional[str] = Query(None, description="Filter by category (e.g., cs.AI)"),
  author: Optional[str] = Query(None, description="Filter by author name"),
  from_date: Optional[str] = Query(None, description="Filter papers after this date (YYYY-MM-DD)"),
  to_date: Optional[str] = Query(None, description="Filter papers before this date (YYYY-MM-DD)"),
  page: int = Query(1, ge=1, description="Page number (starting from 1)"),
  size: int = Query(20, ge=1, le=100, description="Number of results per page")
) -> dict:
  """
  Search papers with full-text search and filters.
  
  **Example:**
    GET /api/search?q=transformer&category=cs.AI&page=1&size=20
    
  **Return:**
    - total: Total number of results
    - page: Current page
    - size: Results per page
    - took: Search time in milliseconds
    - results: List of papers with highlights
  """
  try:
    # Check if ES is connected
    if not es_service.ping():
      raise HTTPException(
        status_code=503,
        detail="Elasticsearch is not available"
      )
    
    # Check if index exists
    if not es_service.index_exists():
      raise HTTPException(
        status_code=404,
        detail="Search index does not exist. Please sync data first."
      )
    
    # Execute search
    result = es_service.search_papers(
      query=q,
      category=category,
      author=author,
      from_date=from_date,
      to_date=to_date,
      page=page,
      size=size
    )
    
    # Check for errors
    if "error" in result:
      raise HTTPException(
        status_code=500,
        detail=f"Search failed: {result['error']}"
      )
    
    return result
  
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Unexpected error: {str(e)}"
    )
    
@router.get("/stats")
async def get_search_stats():
  """
  Get Elasticsearch index statistics.
  
  **Returns:**
  - exists: Whether the index exists
  - count: Number of documents in the index
  - size_in_bytes: Index size
  """
  try:
    stats = es_service.get_stats()
    return stats
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to get stats: {str(e)}"
    )
    
@router.get("/status")
async def get_search_status():
  """
  Get sync status (compare MongoDB and Elasticsearch counts).
  
  **Returns:**
  - mongodb_count: Number of papers in MongoDB
  - elasticsearch_count: Number of papers in Elasticsearch
  - in_sync: Whether the counts match
  """
  try:
    status = get_sync_status()
    return status
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to get status: {str(e)}"
    )
    
@router.post("/sync")
async def sync_data(
    recreate: bool = Query(False, description="Whether to recreate the index")
):
  """
    Sync papers from MongoDB to Elasticsearch.
    
    **Parameters:**
    - recreate: If true, delete and recreate the index before syncing
    
    **Example:**
      POST /api/search/sync?recreate=false
  """
  try:
    result = sync_papers_to_es(recreate_index=recreate)
    
    if not result.get("success"):
      raise HTTPException(
        status_code=500,
        detail=result.get("error", "Sync failed")
      )
    
    return {
      "message": "Sync completed successfully",
      "details": result
    }

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Sync failed: {str(e)}"
    )
  
@router.post("/index/create")
async def create_index():
  """
  Create the Elasticsearch index.
  
  **Note:** This will fail if the index already exists.
  Use DELETE first if you want to recreate it.
  """
  try:
    result = es_service.create_index()
    
    if not result.get("success"):
      raise HTTPException(
        status_code=400,
        detail=result.get("message", "Failed to create index")
      )
    
    return result
  
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to create index: {str(e)}"
    )
    

@router.delete("/index/delete")
async def delete_index():
  """
  Delete the Elasticsearch index.
  
  **Warning:** This will delete all indexed data!
  You'll need to sync again to restore the search functionality.
  """
  try:
    result = es_service.delete_index()
    
    if not result.get("success"):
      raise HTTPException(
        status_code=404,
        detail=result.get("message", "Failed to delete index")
      )
    
    return result
  
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to delete index: {str(e)}"
    )

@router.get("/health")
async def search_health():
  """
  Check if Elasticsearch is healthy.
  """
  try:
    is_connected = es_service.ping()
    index_exists = es_service.index_exists()
    
    return {
      "elasticsearch_connected": is_connected,
      "index_exists": index_exists if index_exists else "not created",
      "status": "healthy" if (is_connected and index_exists) else "degraded"
    }
  
  except Exception as e:
    return {
      "elasticsearch_connected": False,
      "index_exists": False,
      "status": "unhealthy",
      "error": str(e)
    }
    
