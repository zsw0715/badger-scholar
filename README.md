# BadgerScholar 
> This README contains introduction, how to use, key features, followed with a video introduction. <links here TODO>

**An AI-Powered Academic Research Assistant**

BadgerScholar is a full-stack data management and retrieval system that helps researchers discover and interact with academic papers from arXiv. This project demonstrates end-to-end data engineering practices, from ETL pipelines to advanced RAG techniques.

## Introduction
This project was developed as a personal learning initiative to apply and extend the concepts learned in **CS639: Data Management for Data Science.** This project's trying to addresses a real-world challenge, "efficiently searching and extracting insights from the vast corpus of academic literature."

**Key Features:**
- **Intelligent Search**: Multi-modal search combining full-text (Elasticsearch) and semantic search (vector embeddings)
- **AI-Powered Q&A**: Two-stage RAG system (coarse-grained and fine-grained)
- **Scalable Data Pipeline**: Automated ETL from arXiv with MongoDB storage and multi-database syncing (ChromaDB, Elastic Search)
- **Containerized Architecture**: Fully Dockerized
- **Modern Web Interface**: Next.js frontend

## How to use?
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd badger-scholar
   ```

2. **Set up environment variables**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env to add your OPENAI_API_KEY
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - MongoDB (port 27017)
   - Elasticsearch (port 9200)
   - ChromaDB (port 8001)
   - PostgreSQL (port 5432)
   - FastAPI Backend (port 8000)

4. **Start the frontend**
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API Docs: http://localhost:8000/docs

**Usage Flow**
1. **Import Data** (Dataset page)
   - Run ETL to fetch papers from arXiv by category (e.g., `cs.AI`)

2. **Search Papers** (Homepage)
   - Use Elasticsearch full-text search with filters (category, author, date range)
   - View results with highlighting

3. **Ask Questions** (Chat page)
   - Ask natural language questions about the papers
   - The system will:
     - Retrieve relevant papers (coarse-grained retrieval)
     - Extract relevant chunks from full-text (fine-grained retrieval)

## Technology Stack
### 1. Data Storage & Databases

1. **MongoDB (NoSQL Document Database)**: 
   
   1.1. Primary data store that stores paper metadata (id, authors, categories, title, summary, etc.) scraped from arXiv.

2. **Elasticsearch (Search Engine)**: 
   
   2.1. Provides fast full-text search functionality with keyword search, filtering, and highlighting.
   
   2.2. MongoDB's text search is limited; ES is specifically optimized for full-text search (tokenization, stemming, relevance scoring).
   
   2.3. Supports multi-field search (title + summary + authors), Boolean queries, and range filtering (dates, categories), with search response times in milliseconds.

3. **ChromaDB (Vector Database)**: 
   
   3.1. Stores paper embedding vectors for semantic similarity search (understanding meaning, not just keywords).
   
   3.2. Enables Two-Stage RAG system with two collections:
   
   3.3. `papers_embeddings` collection stores summary embeddings for coarse-grained retrieval (quickly filtering relevant papers from the entire database).
   
   3.4. `fulltext_chunks` collection stores PDF full-text chunk embeddings for fine-grained retrieval (precisely locating relevant paragraphs).


### 2. Data Integration & ETL 

1. **MongoDB Schema Design**

   The following schema is the structure of data being scraped from arXiv and injected into MongoDB:

```json
{
  "_id": "2401.12345",
  "arxiv_id": "2401.12345",
  "title": "...",
  "summary": "...",
  "authors": ["Author 1", "Author 2"],
  "categories": ["cs.AI", "cs.LG"],
  "primary_category": "cs.AI",
  "published": "2024-01-15T00:00:00Z",
  "updated": "2024-01-16T00:00:00Z",
  "link_abs": "https://arxiv.org/abs/2401.12345",
  "links": [
    {
      "href": "https://arxiv.org/abs/2401.12345",
      "type": "text/html"
    },
    {
      "href": "https://arxiv.org/pdf/2401.12345",
      "type": "application/pdf"
    }
  ],
  "source": "api",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "vector_indexed": true,
  "fulltext_indexed": false
}
```

   **Key Design Decisions:**

   - **`arxiv_id`**: Used to construct PDF URL: `https://arxiv.org/pdf/{arxiv_id}` for on-demand full-text downloading
   - **`vector_indexed`** & **`fulltext_indexed`**: Boolean flags to prevent duplicate indexing during sync to ChromaDB
   - **`embedding_model`**: Records which model generated the embeddings (currently `all-MiniLM-L6-v2`), enabling model version tracking and potential re-indexing

2. **ETL Processing**

   File: `etl_service.py` and `arxiv_etl.py`

   **2.1. Web Scraping for Paper IDs**
   
   - Tool: BeautifulSoup (HTML parsing)
   - Extract arxiv_id from paper links using CSS selectors:

```python
soup = BeautifulSoup(r.text, "html.parser")
links = soup.select("dt a[title='Abstract']")
```

   - Output: List of recent paper IDs → used in next stage
   - The reason why I'm using the BeautifulSoup to scrape the data is because I want the users to see what and get what (https://arxiv.org/list/cs.AI/recent)
   - Here is the user agent:
```
HEADERS = {
   "User-Agent": "BadgerScholar/0.1 (contact: szhang829@wisc.edu) Purpose: academic learning / ETL for demo"
}
```

   **2.2. Data Transformation & Cleaning**
   - Using the http://export.arxiv.org/api/query?id_list=... arXiv api to get the raw metadata of the papers giving the list of Ids(from previous step). Getting the data maybe slow become only 50 data items will be got for one time, and thread sleep for 3 seconds based on the arxiv api rule.
   - output is the structured metadata (title, summary, authors, categories, dates), the key function here is entries_to_doc() in both files `etl_service.py` and `arxiv_etl.py`. The structured data follows the MongoDB schema above.
   - the user can select run_recent and run_bulk mode, run_recent select the first 50 papers based on selected category. The bulk mode allows the user the specify the number to scrape and category. The default is 1000. 
   - data cleaning inludes Remove version numbers from arxiv_id (2401.12345v1 → 2401.12345). Normalize summary text (strip newlines, trim whitespace). Extract structured arrays (authors, categories, links). Standardize date formats (published, updated)...
   - loading data into the MongoDB by upsert to avoid the duplicate data, and update the old data, the existing papers, if re-scraped.


### 3. **Elasticsearch Synchronization**

File: `sync_to_es.py` and `elasticsearch_service.py`
   
   Data Flow: MongoDB (Source of Truth) → `sync_to_es.py` → Elasticsearch (Search Index)

**3.1. Sync Implementation (`sync_to_es.py`)**

   The synchronization process follows 5 steps:

   - **Step 1: Connection Check**
     es_service.ping()  # Verify Elasticsearch is reachable
   - **Step 2: Index Management**
     - If `recreate_index=True`: Delete old index and recreate
     - If index doesn't exist: Call `create_index()` to create with proper mapping
     
     Key Index Mapping Design:
```
{
   "arxiv_id": {"type": "keyword"},           # Exact match
   "title": {"type": "text", "analyzer": "english"},  # Full-text search
   "summary": {"type": "text", "analyzer": "english"},
   "authors": {"type": "text"},
   "published": {"type": "date"},             # Date range filtering
   "categories": {"type": "keyword"}          # Exact match for filtering
   ... you can find it in elasticsaerch_service.py
}
```
   - **Step 3: Batch Reading from MongoDB**
     BATCH_SIZE = 100  # Process 100 papers at a time
     collection.find().skip(skip).limit(BATCH_SIZE)
          Uses pagination (`skip` + `limit`) to avoid loading all data into memory

   - **Step 4: Data Transformation**
     def prepare_document_for_es(doc):
         # 1. Remove MongoDB's _id field (ES uses arxiv_id as _id)
         # 2. Ensure required fields exist (title, summary, authors, categories)
         # 3. Validate array types (authors, categories must be lists)
      **Why transform?**
     - MongoDB's `_id` (ObjectId) → ES uses `arxiv_id` as document ID
     - Ensures idempotency: re-syncing won't create duplicates

   - **Step 5: Bulk Indexing to Elasticsearch**
     bulk(self.es, actions, stats_only=True, raise_on_error=False)
          Uses Elasticsearch's bulk API for efficient batch insertion

   **Key Design Decisions:**
   
   - **Batch Processing**: BATCH_SIZE=100 balances memory usage and network overhead
   - **Idempotency**: Using `arxiv_id` as ES document `_id` ensures duplicate syncs overwrite rather than duplicate
   - **Error Tolerance**: Partial failures don't stop the entire sync process
   - **Status Tracking**: `get_sync_status()` compares MongoDB and ES document counts to verify sync completion

**3.2. Search Implementation (`elasticsearch_service.py`)**
   Key FILES: "elasticsearch_service.py 's search_papers()" and thee "api/search.py's search_papers()"
   The `search_papers()` function provides advanced full-text search with multiple features:
   - **Multi-field Search with Boosting**:
   ```
     "multi_match": {
       "query": query,
       "fields": ["title^3", "summary^1", "authors^2"],  # title has 3x weight
       "type": "best_fields",
       "fuzziness": "AUTO"  # Typo tolerance (transformr → transformer)
     }
   ```
   title > summary > author

   - **Filter Support**:
     - Category filtering: `{"term": {"categories": category}}`
     - Author filtering: `{"match": {"authors": author}}`
     - Date range: `{"range": {"published": {"gte": from_date, "lte": to_date}}}`

   - **Highlighting**:
   ```
     "highlight": {
       "fields": {
         "title": {"number_of_fragments": 0},        # Highlight entire title
         "summary": {"fragment_size": 150, "number_of_fragments": 3}  # 3 snippets
       },
       "pre_tags": ["<em>"], "post_tags": ["</em>"]  # HTML tags for frontend
     }
   ```
   Returns matched text snippets with `<em>` tags for highlighting in UI

   - **Ranking**:
   ```
     "sort": [
       {"_score": {"order": "desc"}},      # Relevance score first
       {"published": {"order": "desc"}}    # Then by publication date
     ]

   ```
   **Why Elasticsearch over MongoDB for search?**
   
   - **Inverted Index**: O(1) lookup for documents containing keywords
   - **TF-IDF Scoring**: Ranks results by relevance (term frequency × inverse document frequency)
   - **Analyzer**: English stemming (running → run), stop words removal (the, a, an)
   - **Fuzzy Search**: Handles typos automatically
   - MongoDB's text index lacks these advanced features


### 4. AI Integration

   KEY FILES: `rag.py`, `rag_service.py`, `retriever_service.py`, `fulltext_indexer.py`, `rag_chunk_retriever.py`, `fulltext_service.py` and `vector_index_service.py`

**4.1. The Functionality of Each File**
- `rag.py`: (API Layer): Exposes HTTP endpoints for RAG operations (/api/rag/query, /api/rag/sync-coarse, /api/rag/sync-status ... )
- `rag_service.py`: (Orchestrator): Coordinates the entire Two-Stage RAG pipeline, calls coarse/fine retrievers and LLM
- `retriever_service.py`: (Coarse Retrieval): Semantic search on summary embeddings to find top-k relevant papers
- `fulltext_service.py`: (PDF Processing): Downloads PDF from arXiv, extracts text with pypdf, cleans text (removes LaTeX/citations), chunks into 1500-character segments with 200-character overlap
- `rag_chunk_retriever.py`: (Fine Retrieval): Semantic search on full-text chunks to find the most relevant paragraphs
- `fulltext_indexer.py`: (Fine Indexing): Generates embeddings for full-text chunks and syncs to ChromaDB's papers_fulltext_chunks collection
- `vector_index_service.py`: (Coarse Indexing): Generates summary embeddings (title + abstract) and syncs to ChromaDB's papers_embeddings collection

**4.2. Design Mode: Two Stage Rag (Improvement over CS639 Last Project)**
**Problem with Single-Stage RAG:**
- Searching all full-text chunks across the entire database is computationally expensive (I remember it was the coarse lecture recording scripts)

**Solution: Two-Stage RAGs**
> Summary: provided with 10000 papers in the database(TOO LARGE!!), first stage finds the top_k most relevant accordings to the summary of the papers(MongoDB attr), and then the second stage is download the fulltexts of the top_k and finding the top 100 most relevant chunk within the top_k's fulltext of the previous stage, returning the top_k most relevant chunk (default 8) to the user and LLM.

**Stage 1: Coarse-Grained Retrieval (Paper-Level)**
```
# retriever_service.py
coarse_results = retriever_service.search(
    query="How do transformers handle long sequences?",
    top_k=5  # Returns 5 most relevant papers
)
# Searches ChromaDB 'papers_embeddings' collection
# Embeddings generated from: "Title: {title}\n\nAbstract: {summary}"
```
Output: 5 most relevant papers based on semantic similarity of summaries
**Stage 2: Fine-Grained Retrieval (Chunk-Level)**
```
# rag_service.py
for arxiv_id in coarse_results:
    if not paper.get("fulltext_indexed"):
        # On-demand PDF extraction
        fulltext_indexer.process_single_paper(paper)

# rag_chunk_retriever.py
all_chunks = chunk_retriever.retrieve_chunks(
    question=question,
    top_k=100  # Get broad candidate set
)

# Filter to only chunks from coarse-selected papers
fine_chunks = [
    chunk for chunk in all_chunks
    if chunk["arxiv_id"] in coarse_arxiv_ids
][:8]  # Take top 8 most relevant chunks
```
Output: 8 most relevant text chunks from the 5 papers selected in Stage 1

**4.3. On-Demand PDF Extraction**
> Only download the fulltext that's needed, and a sliding window that delete the previous stored fulltext when count > 70
Key design: Lazy loading of full-text to save storage and processing time
```
# rag_service.py: answer_question()
for arxiv_id in coarse_results:
    paper = mongo_collection.find_one({"arxiv_id": arxiv_id})
    if not paper.get("fulltext_indexed", False):
        print(f"Fulltext not indexed for {arxiv_id}, indexing now...")
        fulltext_indexer.process_single_paper(paper)
```
**Workflow:**
1. Check MongoDB flag: `fulltext_indexed`
2. If `False`, download PDF: `https://arxiv.org/pdf/{arxiv_id}.pdf`
3. Extract text with `pypdf.PdfReader`
4. Clean text: remove `[citations]`, `$math$`, control characters
5. Chunk into 1500-char segments with 200-char overlap
6. Generate embeddings for each chunk
7. Store in ChromaDB `papers_fulltext_chunks` collection
8. Update MongoDB: `{"fulltext_indexed": True}`

**Benefits:**
- Only process papers that are actually queried
- Saves ~90% storage vs. indexing all papers upfront

**4.4 Data Flow Diagrams**

```

User Question: "How do transformers handle long sequences?"
    ↓
┌─────────────────────────────────────────────────┐
│ Stage 1: Coarse-Grained Retrieval               │
│ - Query embedding: model.encode(question)       │
│ - Search ChromaDB 'papers_embeddings'           │
│ - Return top-5 papers by cosine similarity      │
└───────────────────┬─────────────────────────────┘
                    ↓
         [2401.12345, 2402.67890, 2403.11111, ...]
                    ↓
┌─────────────────────────────────────────────────┐
│ On-Demand PDF Extraction (if needed)            │
│ - Check: fulltext_indexed == True?             │
│ - If False: Download → Extract → Chunk → Embed │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Stage 2: Fine-Grained Retrieval                 │
│ - Search ChromaDB 'papers_fulltext_chunks'      │
│ - Filter: only chunks from coarse papers        │
│ - Return top-8 chunks                           │
└───────────────────┬─────────────────────────────┘
                    ↓
        [chunk_0, chunk_3, chunk_7, ...]
                    ↓
┌─────────────────────────────────────────────────┐
│ Context Construction                            │
│ - Build prompt with source attribution          │
│ - Format: [Source N] arxiv_id | chunk_id       │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ LLM Answer Generation                           │
│ - Model: <OPENAI MODEL>                         │
│ - Temperature: 0.2                              │
│ - System: "Answer based only on context"       │
└───────────────────┬─────────────────────────────┘
                    ↓
      Final Answer + Source Papers + Chunks

```

### 5. Backend
   - The Backend API part use the FastAPI framework
   - The API Design is here
```
# 1. ETL Operations (/api/etl)
POST   /api/etl/run          # Run ETL pipeline (recent/bulk mode)
GET    /api/etl/papers       # List papers with pagination
DELETE /api/etl/drop         # Drop all data from MongoDB
GET    /api/etl/status       # Get ETL status

# 2. Search Operations (/api/search)
GET    /api/search           # Full-text search with filters
GET    /api/search/stats     # Elasticsearch index statistics
GET    /api/search/status    # Sync status (MongoDB vs ES)
POST   /api/search/sync      # Sync MongoDB → Elasticsearch
POST   /api/search/index/create   # Create ES index
DELETE /api/search/index/delete   # Delete ES index

# 3. RAG Operations (/api/rag)
POST   /api/rag/query        # Ask question (Two-Stage RAG)
POST   /api/rag/sync-coarse  # Sync summary embeddings to ChromaDB
GET    /api/rag/sync-status  # Check coarse embedding sync status
GET    /api/rag/sync-status/fulltext  # Check fine embedding sync status
DELETE /api/rag/drop         # Drop all vectors from ChromaDB
```
   - Service Layer Pattern is here
```
API Layer (app/api/)
    ↓ calls
Service Layer (app/services/)
    ↓ interacts with
Data Layer (MongoDB, ES, ChromaDB)
```
   - Pydantic Models for Validation
```
example:
class ETLRequest(BaseModel):
    mode: Literal["recent", "bulk"] = Field(default="recent")
    categories: str = Field(default="cs.AI")
    limit: Optional[int] = Field(default=500, ge=1)

class ETLResponse(BaseModel):
    status: str
    message: str
    stats: dict
```
   - CORS Configuration
```
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins (development)
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all headers
)
```
the reason is to enables the Next.js frontend (running on localhost:3000) to call the backend API (running on localhost:8000) without CORS errors.

   - API Documentation: Swagger UI: http://localhost:8000/docs OR ReDoc: http://localhost:8000/redoc



### 6. Frontend
The Frontend uses the Nextjs 15 and React 19. Using TypeScript, TailwindCSS, Shadcn UI


### Future Enhancements && Connection with CS639
**1. Future Enhancements:**
- Adding user authenication using MySQL. 
- Add time-series analysis of research trends (LightGBM/XGBoost). 
- Get it deployed.

**2. Connections with course materials:**
- Connections with CS639 materials includes the tech of Docker, MongoDB, Elasticsearch, Data Ingestion & ETL, Data Cleaning, Data Modeling, LLM & RAG(two-staged improvement in accuracy)

## Acknowledgments 🙏
This project would not have been possible without the foundational knowledge and inspiration from CS639: Data Management for Data Science and CS544: Introduction to Big Data Systems, both taught by Professor Meenakshi Syamkumar.

Thank you! for your efforts and times in making both CS639 and CS544 such a transformative learning experiences. And hope that more and more students will enroll in your new course CS574 (CS639).



