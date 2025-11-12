from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../services"))
from etl_service import run_recent, run_bulk

router = APIRouter(prefix="/api/etl", tags=["ETL"])

class ETLRequest(BaseModel):
  mode: Literal["recent", "bulk"] = Field(default="recent", description="ETL mode")
  categories: str = Field(default="cs.AI", description="arXiv category")
  limit: Optional[int] = Field(default=500, description="Limit for bulk mode")
  
class ETLResponse(BaseModel):
  status: str
  message: str
  stats: dict
  
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

