import os
from typing import List, Dict, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# ==== Configuration ====
ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
INDEX_NAME = "papers"

# ==== Singleton Instance ====
class ElasticsearchService:
  """Elasticsearch service for managing paper search index."""
  
  def __init__(self):
    """Initialize Elasticsearch client."""
    self.es = Elasticsearch([ES_HOST])
    self.index_name = INDEX_NAME
  
  def ping(self) -> bool:
    """Check if Elasticsearch is reachable."""
    try:
      return self.es.ping()
    except Exception as e:
      print(f"❌ Elasticsearch ping failed: {e}")
      return False
  
  def index_exists(self) -> bool:
    """Check if the papers index exists."""
    try:
      return self.es.indices.exists(index=self.index_name)
    except Exception as e:
      print(f"❌ Failed to check index existence: {e}")
      return False
  
  def create_index(self) -> bool:
    """
    Create the papers index with proper mapping.
    
    Returns:
      Dict with success status and message
    """
    if self.index_exists():
      return {
        "success": False,
        "message": f"Index '{self.index_name}' already exists"
      }
    
    # define the mapping
    mapping = {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
          "analyzer": {
            "english_analyzer": {
              "type": "english"
            }
          }
        }
      },
      "mappings": {
        "properties": {
          "arxiv_id": {
            "type": "keyword"
          },
          "title": {
            "type": "text",
            "analyzer": "english",
            "fields": {
              "keyword": {
                "type": "keyword",
                "ignore_above": 256
              }
            }
          },
          "summary": {
            "type": "text",
            "analyzer": "english"
          },
          "authors": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
              "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
              }
            }
          },
          "published": {
            "type": "date"
          },
          "updated": {
            "type": "date"
          },
          "primary_category": {
            "type": "keyword"
          },
          "categories": {
            "type": "keyword"
          },
          "link_abs": {
            "type": "keyword",
            "index": False
          },
          "links": {
            "type": "object",
            "enabled": False
          }
        }
      }
    }
    
    try:
      self.es.indices.create(index=self.index_name, body=mapping)
      return {
        "success": True,
        "message": f"Index '{self.index_name}' created successfully"
      }
    except Exception as e:
      print(f"❌ Failed to create index: {str(e)}")
      return {
        "success": False,
        "message": f"Failed to create index: {str(e)}"
      }
  
  def delete_index(self) -> bool:
    """
    Delete the papers index.
    
    Returns:
      Dict with success status and message
    """
    if not self.index_exists():
      return {
        "success": False,
        "message": f"Index '{self.index_name}' does not exist"
      }
    
    try:
      self.es.indices.delete(index=self.index_name)
      return {
        "success": True,
        "message": f"Index '{self.index_name}' deleted successfully"
      }
    except Exception as e:
      print(f"❌ Failed to delete index: {str(e)}")
      return {
        "success": False,
        "message": f"Failed to delete index: {str(e)}"
      }
  
  def bulk_index_papers(self, papers: List[Dict]) -> bool:
    """
    Bulk index papers to Elasticsearch.
    
    Args:
      papers: List of paper documents
        
    Returns:
      Dict with success count and failed count
    """
    if not papers:
      return {
        "success": False,
        "failed": 0
      }
    
    actions = []
    for paper in papers:
      action = {
        "_index": self.index_name,
        "_id": paper.get("arxiv_id"),
        "_source": paper
      }
      actions.append(action)
      
    try:
      success, failed = bulk(self.es, actions, stats_only=True, raise_on_error=False)
      return {
        "success": success,
        "failed": failed
      }
    except Exception as e:
      print(f"❌ Failed to bulk index papers: {str(e)}")
      return {
        "success": False,
        "failed": len(papers)
      }
      
  def search_papers(
    self,
    query: str,
    category: Optional[str] = None,
    author: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    size: int = 20
  ) -> Dict:
    """
    Search papers with filters.
    
    Args:
        query: Search query string
        category: Filter by category
        author: Filter by author
        from_date: Filter papers after this date
        to_date: Filter papers before this date
        page: Page number (1-indexed)
        size: Number of results per page
        
    Returns:
        Search results with highlights and metadata
    """
    must_queries = []
    
    if query:
      must_queries.append({
        "multi_match": {
            "query": query,
            "fields": ["title^3", "summary^1", "authors^2"],
            "type": "best_fields",
            "fuzziness": "AUTO"
        }
      })
    else:
      must_queries.append({
        "match_all": {}
      })
    
    filter_queries = []
    
    if category:
      filter_queries.append({"term": {"categories": category}})
    
    if author:
      filter_queries.append({"match": {"authors": author}})
    
    if from_date or to_date:
      date_range = {}
      if from_date:
        date_range["gte"] = from_date
      if to_date:
        date_range["lte"] = to_date
      filter_queries.append({"range": {"published": date_range}})
    
    # Construct search body
    search_body = {
      "query": {
        "bool": {
          "must": must_queries,
          "filter": filter_queries
        }
      },
      "highlight": {
        "fields": {
          "title": {"number_of_fragments": 0},
          "summary": {
            "fragment_size": 150,
            "number_of_fragments": 3
          }
        },
        "pre_tags": ["<em>"],
        "post_tags": ["</em>"]
      },
      "from": (page - 1) * size,
      "size": size,
      "sort": [
        {"_score": {"order": "desc"}},
        {"published": {"order": "desc"}}
      ]
    }
    
    try:
      result = self.es.search(index=self.index_name, body=search_body)
      
      # Format results
      hits = result["hits"]
      papers = []
      
      for hit in hits["hits"]:
        paper = hit["_source"]
        paper["score"] = hit["_score"]
        
        # Add highlights if available
        if "highlight" in hit:
          if "title" in hit["highlight"]:
            paper["title_highlight"] = hit["highlight"]["title"][0]
          if "summary" in hit["highlight"]:
            paper["summary_highlight"] = " ... ".join(hit["highlight"]["summary"])
        
        papers.append(paper)
      
      return {
        "total": hits["total"]["value"],
        "page": page,
        "size": size,
        "took": result["took"],
        "results": papers
      }
    
    except Exception as e:
      print(f"❌ Search error: {e}")
      return {
        "total": 0,
        "page": page,
        "size": size,
        "took": 0,
        "results": [],
        "error": str(e)
      }
  
  def get_stats(self) -> Dict:
    """
    Get index statistics.
    
    Returns:
        Dict with index stats
    """
    if not self.index_exists():
      return {
        "exists": False,
        "count": 0
      }
    
    try:
      count = self.es.count(index=self.index_name)
      stats = self.es.indices.stats(index=self.index_name)
      
      return {
        "exists": True,
        "count": count["count"],
        "size_in_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"]
      }
    except Exception as e:
      return {
        "exists": True,
        "error": str(e)
      }
    
# Create a singleton instance
es_service = ElasticsearchService()
