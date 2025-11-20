from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
import os
import sys
from pymongo import MongoClient

sys.path.append(os.path.join(os.path.dirname(__file__), "../services"))
from etl_service import run_recent, run_bulk

router = APIRouter(prefix="/api/etl", tags=["ETL"])

# Configuration (should match etl_service.py or be in a config file)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

# Global client instance
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
col = db[COLL_NAME]

def get_collection():
    return col

class ETLRequest(BaseModel):
  mode: Literal["recent", "bulk"] = Field(default="recent", description="ETL mode")
  categories: str = Field(default="cs.AI", description="arXiv category")
  limit: Optional[int] = Field(default=500, description="Limit for bulk mode")
  
class ETLResponse(BaseModel):
  status: str
  message: str
  stats: dict

class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[Dict[str, Any]]
  
@router.post("/run", response_model=ETLResponse)
async def run_etl(request: ETLRequest) -> ETLResponse:
  """
  Run the ETL process.
  
  - **mode**: ETL mode (recent or bulk)
  - **categories**: ArXiv category
  - **limit**: Limit for bulk mode
  """
  try:
    if request.mode == "recent":
      stats = run_recent(request.categories, skip=0, show_progress=False)
    else:
      stats = run_bulk(request.categories, request.limit, show_progress=False)
    
    return ETLResponse(
      status="success",
      message=f"ETL completed: {request.mode} mode for {request.categories}",
      stats=stats
    )
      
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  
@router.get("/status")
async def get_etl_status() -> dict:
  """
  Get the status of the ETL process.
  """
  return {
    "status": "ok",
    "message": "ETL process is running"
  }

@router.get("/papers", response_model=PaginationResponse)
async def list_papers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page")
):
    """
    List all papers from MongoDB with pagination.
    """
    try:
        col = get_collection()
        
        # Calculate skip
        skip = (page - 1) * page_size
        
        # Get total count
        total = col.count_documents({})
        
        # Query data
        cursor = col.find({}).skip(skip).limit(page_size)
        
        papers = []
        for doc in cursor:
            # Ensure _id is included and handled correctly
            papers.append(doc)
            
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": papers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
