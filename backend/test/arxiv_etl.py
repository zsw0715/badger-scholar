# 这个文件可以测试，就是在 arxiv 中抓取数据，然后存到 mongodb 中
# 测试 command python backend/test/arxiv_etl.py --mode <recent or bulk> --categories cs.AI --limit <integer>

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
DEFAULT_CATEGORIES = "cs.AI"
DEFAULT_MODE = "recent"
DEFAULT_LIMIT = 1000
BATCH_SIZE = 50
SLEEP_SEC = 3.0  # arXiv API rate limit

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("MONGO_DB", "badger_db")
COLL_NAME = os.getenv("MONGO_COLL", "papers")

GLOBAL_STATS = {
    "total_upserted": 0,
    "total_modified": 0,
    "total_processed": 0,
    "final_total": 0
}

HEADERS = {
    "User-Agent": "BadgerScholar/0.1 (contact: szhang829@wisc.edu) Purpose: academic learning / ETL for demo"
}

# ==== utility functions ====
def recent_page_url_pagnate(category: str, skip: int) -> str:
    return f"https://arxiv.org/list/{category}/recent?skip={skip}&show=50"

def get_recent_ids(category: str, skip: int) -> List[str]:
    url = recent_page_url_pagnate(category, skip)
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

def fetch_by_ids(id_list: List[str]) -> List[Dict]:
    entries = []
    for i in tqdm(range(0, len(id_list), BATCH_SIZE), desc="Fetch metadata by ids"):
        chunk = id_list[i:i+BATCH_SIZE]
        url = (
            "http://export.arxiv.org/api/query?"
            "id_list=" + ",".join(chunk) +
            "&max_results=" + str(len(chunk))
        )
        feed = feedparser.parse(url)
        entries.extend(feed.entries)
        time.sleep(SLEEP_SEC)

    return entries

def entries_to_doc(e) -> Dict:
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
    global GLOBAL_STATS
    client = MongoClient(MONGO_URI)
    col = client[DB_NAME][COLL_NAME]
    ops = []
    for d in docs:
        ops.append(
            UpdateOne(
                {"_id": d["_id"]},
                {"$set": d},
                upsert=True
            )
        )
    if not ops:
        stats = {"upserted": 0, "modified": 0, "total": col.count_documents({})}
    else:
        res = col.bulk_write(ops, ordered=False)
        stats = {
            "upserted": res.upserted_count,
            "modified": res.modified_count,
            "total": col.count_documents({})
        }
    GLOBAL_STATS["total_upserted"] += stats["upserted"]
    GLOBAL_STATS["total_modified"] += stats["modified"]
    GLOBAL_STATS["total_processed"] += len(docs)
    GLOBAL_STATS["final_total"] = stats["total"]
    return stats

# ==== main logic ====
def run_recent(category: str, skip: int):
    print(f"🔎 crawl recent list: {category}")
    ids = get_recent_ids(category, skip)
    print(f"found {len(ids)} ids from recent page")
    if not ids:
        return
    entries = fetch_by_ids(ids)
    print(f"fetched {len(entries)} entries from API")
    if not entries:
        return
    docs = [entries_to_doc(e) for e in entries]
    print(f"converted {len(docs)} entries to docs")
    stats = upsert_docs(docs)   # update or insert to MongoDB
    print(f"✅ upserted={stats['upserted']} modified={stats['modified']} total={stats['total']}")

def run_bulk(category: str, limit: int):
    print(f"📦 bulk fetch: category={category}, limit={limit}")
    pages = (limit + 49) // 50
    all_ids = []
    for i in range(pages):
        skip = i * 50
        run_recent(category, skip)
        print(f"--- Finished page {i+1}/{pages} ---")

def main():
    global GLOBAL_STATS
    parser = argparse.ArgumentParser("BadgerScholar arXiv ETL")
    parser.add_argument("--mode", choices=["recent", "bulk"], default=DEFAULT_MODE, 
                        help="recent: Obtain from the 'recent' page; bulk: API batch retrieval")
    parser.add_argument("--categories", default=DEFAULT_CATEGORIES, 
                        help="ArXiv classification, such as cs.AI / cs.CL, etc.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="Bulk mode maximum number of items to be retrieved")
    args = parser.parse_args()
    
    GLOBAL_STATS = {
        "total_upserted": 0,
        "total_modified": 0,
        "total_processed": 0,
        "final_total": 0
    }
    if args.mode == "recent":
        run_recent(args.categories, 0)
        print(f"--- Finished recent crawl for category {args.categories} ---")
        print(f"📊 Recent operation stats: "
              f"upserted={GLOBAL_STATS['total_upserted']}, "
              f"modified={GLOBAL_STATS['total_modified']}, "
              f"processed={GLOBAL_STATS['total_processed']}")
    else:
        run_bulk(args.categories, args.limit)
        print(f"--- Finished bulk crawl for category {args.categories} ---")
        print("\n" + "="*50)
        print("📊 BULK OPERATION SUMMARY")
        print("="*50)
        print(f"Total documents processed: {GLOBAL_STATS['total_processed']}")
        print(f"Total new documents upserted: {GLOBAL_STATS['total_upserted']}")
        print(f"Total existing documents modified: {GLOBAL_STATS['total_modified']}")
        print(f"Final total documents in database: {GLOBAL_STATS['final_total']}")
        print("="*50)

if __name__ == "__main__":
    main()
