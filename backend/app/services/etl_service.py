import os
import time
import argparse
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import feedparser
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

# ==== Configuration ====
BATCH_SIZE = 50
SLEEP_SEC = 3.0  # arXiv API rate limit

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

HEADERS = {
  "User-Agent": "BadgerScholar/0.1 (contact: szhang829@wisc.edu) Purpose: academic learning / ETL for demo"
}

# ==== Core ETL Functions ====
def recent_page_url_paginate(category: str, skip: int) -> str:
  """
  Generate the URL for the recent page of a given category and skip.
  Args:
    category (str): The category of the paper.
    skip (int): The number of papers to skip.
  Returns:
    str: The URL for the recent page of the given category and skip.
  """
  return f"https://arxiv.org/list/{category}/recent?skip={skip}&show=50"
  
def get_recent_ids(category: str, skip: int) -> List[str]:
  """
  Get the recent IDs from the recent page of a given category and skip.
  Args:
    category (str): The category of the paper.
    skip (int): The number of papers to skip.
  Returns:
    List[str]: The recent IDs from the recent page of the given category and skip.
  """
  url = recent_page_url_paginate(category, skip)
  r = requests.get(url, headers=HEADERS, timeout=30)
  r.raise_for_status()   # if not 200, raise error
  soup = BeautifulSoup(r.text, "html.parser")

  links = soup.select("dt a[title='Abstract']")
  if not links:
    print("⚠️ No links found on the recent page. No error before 9/19/2025")
    return []

  ids = []
  for a in links:
    href = a.get("href", "")
    if "/abs/" in href:
      raw = href.split("/abs/")[-1]
      ids.append(raw)

  seen, uniq = set(), []
  for i in ids:
    if i not in seen:
      uniq.append(i)
      seen.add(i)

  return uniq

def fetch_by_ids(id_list: List[str], show_progress: bool = True) -> List[Dict]:
  """
  Fetch the metadata by IDs from the arXiv API.
  Args:
    id_list (List[str]): The list of IDs to fetch.
    show_progress (bool): Whether to show progress bar.
  Returns:
    List[Dict]: The metadata by IDs.
  """
  entries = []
  iterator = range(0, len(id_list), BATCH_SIZE)
  
  if show_progress:
    iterator = tqdm(iterator, desc="Fetch metadata by ids")
  
  for i in iterator:
    chunk = id_list[i:i+BATCH_SIZE]
    url = (
      "http://export.arxiv.org/api/query?"
      "id_list=" + ",".join(chunk) +
      "&max_results=" + str(len(chunk))
    )
    
    try:
      print(f"📡 Fetching from arXiv API: {len(chunk)} papers")
      feed = feedparser.parse(url)
      
      if hasattr(feed, 'status'):
        print(f"   API Response status: {feed.status}")
      
      if hasattr(feed, 'entries') and feed.entries:
        print(f"   ✅ Got {len(feed.entries)} entries")
        entries.extend(feed.entries)
      else:
        print(f"   ⚠️ No entries in feed response")
        if hasattr(feed, 'bozo_exception'):
          print(f"   Feed parse error: {feed.bozo_exception}")
      
      time.sleep(SLEEP_SEC)
      
    except Exception as e:
      print(f"   ❌ Error fetching batch: {e}")

  print(f"📊 Total entries fetched: {len(entries)}")
  return entries

def entries_to_doc(e) -> Dict:
  """
  Perform data cleaning by converting the arXiv API entry to a dictionary.
  Args:
    e (Dict): The arXiv API entry.
  Returns:
    Dict: The cleaned dictionary.
  """
  arxid_full = e.id.split("/")[-1]  # e.g. 2509.12345v1
  arxid = arxid_full.split("v")[0]   # e.g. 2509.12345
  return {
    "_id": arxid,
    "arxiv_id": arxid,
    "title": (e.title or "").strip(),
    "summary": (getattr(e, "summary", "") or "").strip().replace("\n", " "),
    "authors": [a.name for a in getattr(e, "authors", [])],
    "published": getattr(e, "published", None),
    "updated": getattr(e, "updated", None),
    "primary_category": getattr(e, "arxiv_primary_category", {}).get("term")
        if hasattr(e, "arxiv_primary_category") else None,
    "categories": [t.get("term") for t in getattr(e, "tags", [])] if hasattr(e, "tags") else [],
    "link_abs": getattr(e, "link", None),
    "links": [{"href": l.get("href"), "type": l.get("type")} for l in getattr(e, "links", [])]
        if hasattr(e, "links") else [],
    "source": "api",
  }
  
def upsert_docs(docs: List[Dict]) -> Dict:
  """Batch upsert documents to MongoDB."""
  client = MongoClient(MONGO_URI)
  col = client[DB_NAME][COLL_NAME]
  
  if not docs:
    return {"upserted": 0, "modified": 0, "total": col.count_documents({})}
  
  ops = []
  for d in docs:
    ops.append(
      UpdateOne(
        {"_id": d["_id"]},
        {"$set": d},
        upsert=True
      )
    )
  
  res = col.bulk_write(ops, ordered=False)
  stats = {
    "upserted": res.upserted_count,
    "modified": res.modified_count,
    "total": col.count_documents({})
  }
  
  client.close()
  return stats

# ==== High-level ETL Functions ====
def run_recent(category: str, skip: int = 0, show_progress: bool = True) -> Dict:
  """Run the ETL in recent mode."""
  print(f"🔎 Crawling recent papers: {category}")
  
  ids = get_recent_ids(category, skip)
  print(f"Found {len(ids)} paper IDs")
  
  if not ids:
      return {"upserted": 0, "modified": 0, "processed": 0, "total": 0}
  
  entries = fetch_by_ids(ids, show_progress)
  print(f"Fetched {len(entries)} entries from API")
  
  docs = [entries_to_doc(e) for e in entries]
  print(f"Converted {len(docs)} entries to documents")
  
  stats = upsert_docs(docs)
  stats["processed"] = len(docs)
  
  print(f"✅ Upserted={stats['upserted']}, Modified={stats['modified']}, Total={stats['total']}")
  
  return stats

def run_bulk(category: str, limit: int = 1000, show_progress: bool = True) -> Dict:
  """运行 bulk 模式的 ETL"""
  print(f"📦 Bulk fetch: category={category}, limit={limit}")
  
  pages = (limit + 49) // 50
  total_stats = {
    "upserted": 0,
    "modified": 0,
    "processed": 0,
    "total": 0
  }
  
  for i in range(pages):
    skip = i * 50
    print(f"\n--- Page {i+1}/{pages} ---")
    stats = run_recent(category, skip, show_progress)
    
    total_stats["upserted"] += stats["upserted"]
    total_stats["modified"] += stats["modified"]
    total_stats["processed"] += stats["processed"]
    total_stats["total"] = stats["total"]
  
  print("\n" + "="*50)
  print("📊 BULK OPERATION SUMMARY")
  print("="*50)
  print(f"Total documents processed: {total_stats['processed']}")
  print(f"Total new documents upserted: {total_stats['upserted']}")
  print(f"Total existing documents modified: {total_stats['modified']}")
  print(f"Final total documents in database: {total_stats['total']}")
  print("="*50)
  
  return total_stats

