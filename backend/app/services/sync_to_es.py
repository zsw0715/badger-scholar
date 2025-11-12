# this file
# 1. sync all papers from MongoDB to Elasticsearch
# 2. convert MongoDB docs to Elastic format
# 3. bulk index the papers to Elasticsearch

# flows:
# start -> check index existence -> create index -> sync papers from MongoDB -> bulk index by batches -> statistics -> end

import os
from typing import Dict, List
from pymongo import MongoClient
from tqdm import tqdm
from app.services.elasticsearch_service import es_service

# ==== Configuration ====
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

BATCH_SIZE = 100     # this is sync 100 papers at a time (to avoid memory issues)

def prepare_document_for_es(doc: Dict) -> Dict:
  """
  Prepare MongoDB document for Elasticsearch.
  
  Args:
      doc: MongoDB document
      
  Returns:
      Cleaned document for ES, or None if invalid
  """
  # Skip if no arxiv_id
  if not doc.get("arxiv_id"):
    return None
  
  # Create a copy to avoid modifying the original
  es_doc = {}
  
  # Copy all fields except MongoDB's _id
  for key, value in doc.items():
    if key == "_id":
      continue
    es_doc[key] = value
      
  # Ensure required fields exist with defaults
  es_doc.setdefault("title", "")
  es_doc.setdefault("summary", "")
  es_doc.setdefault("authors", [])
  es_doc.setdefault("categories", [])
  es_doc.setdefault("primary_category", "")
  
  # Ensure arrays are actually lists
  if not isinstance(es_doc["authors"], list):
    es_doc["authors"] = []
  if not isinstance(es_doc["categories"], list):
    es_doc["categories"] = []
    
  return es_doc

def sync_papers_to_es(recreate_index: bool = False) -> Dict:
  """
  Sync all papers from MongoDB to Elasticsearch.
  
  Args:
      recreate_index: If True, delete and recreate the index
      
  Returns:
      Dict with sync statistics
  """
  print("🔄 Starting MongoDB -> Elasticsearch sync...")
  
  # 1. Check ES connection
  if not es_service.ping():
      return {
          "success": False,
          "error": "Elasticsearch is not reachable"
      }
  print("✅ Elasticsearch connected")
  
  # 2. Handle index creation/recreation
  if recreate_index:
    print("Deleting existing index...")
    es_service.delete_index()
  
  if not es_service.index_exists():
    print("Creating index...")
    result = es_service.create_index()
    if not result["success"]:
      return {
        "success": False,
        "error": result["message"]
      }
      print(f"✅ {result['message']}")
    else:
      print("✅ Index already exists")
  
  # 3. Connect to MongoDB
  try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLL_NAME]
    
    total_docs = collection.count_documents({})
    print(f"Found {total_docs} papers in MongoDB")
    
    if total_docs == 0:
      return {
        "success": True,
        "message": "No papers to sync",
        "total": 0,
        "synced": 0,
        "failed": 0
      }
      
  except Exception as e:
    return {
      "success": False,
      "error": f"MongoDB connection failed: {str(e)}"
    }
    
  # 4. Sync papers in batches
  total_synced = 0
  total_failed = 0
  
  try:
    # Use tqdm for progress bar
    for skip in tqdm(range(0, total_docs, BATCH_SIZE), desc="Syncing batches"):
      # Fetch a batch from MongoDB
      batch = list(collection.find().skip(skip).limit(BATCH_SIZE))
      
      # prepare documents for ES
      es_docs = []
      for doc in batch:
        es_doc = prepare_document_for_es(doc)
        if es_doc:
          es_docs.append(es_doc)
          
      # bulk index the documents to ES
      if es_docs:
        result = es_service.bulk_index_papers(es_docs)
        total_synced += result["success"]
        total_failed += result["failed"]
        
    print("\n" + "="*50)
    print("✅ Sync completed!")
    print("="*50)
    print(f"Total documents in MongoDB: {total_docs}")
    print(f"Successfully synced: {total_synced}")
    print(f"Failed: {total_failed}")
    print("="*50) 
    
    return {
      "success": True,
      "total": total_docs,
      "synced": total_synced,
      "failed": total_failed
    }
    
  except Exception as e:
    print(f"\n❌ Sync failed: {str(e)}")
    return {
        "success": False,
        "error": str(e),
        "synced": total_synced,
        "failed": total_failed
    }
  
  finally:
    client.close()
  
def get_sync_status() -> Dict:
  """
  Get current sync status (compare MongoDB and ES counts).
  
  Returns:
      Dict with counts from both databases
  """
  try:
    # MongoDB count
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLL_NAME]
    mongo_count = collection.count_documents({})
    client.close()
    
    # ES count
    es_stats = es_service.get_stats()
    es_count = es_stats.get("count", 0)
    
    return {
      "mongodb_count": mongo_count,
      "elasticsearch_count": es_count,
      "in_sync": mongo_count == es_count
    }

  except Exception as e:
    return {
      "error": str(e)
    }


# For command-line testing
if __name__ == "__main__":
  import argparse
  
  parser = argparse.ArgumentParser(description="Sync papers from MongoDB to Elasticsearch")
  parser.add_argument("--recreate", action="store_true", help="Recreate the index")
  args = parser.parse_args()
  
  result = sync_papers_to_es(recreate_index=args.recreate)
  
  if result["success"]:
    print(f"\n✅ Success! Synced {result['synced']}/{result['total']} papers")
  else:
    print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
