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
- Data Scaping, Cleaning and Injection (MongoDB part)
The following schema is the schema of Data that's being scraping and injected into the nosql database.
```
{
  "_id": "<mongodbid>",
  "arxiv_id": "...",
  "authors": [
    "string",
    ...
  ],
  "categories": [
    "..."
  ],
  "link_abs": "https://arxiv.org/abs/{arxid_id}",
  "links": [
    {
      "href": "https://arxiv.org/abs/{arxid_id}",
      "type": "text/html"
    },
    ...
  ],
  "primary_category": "...",
  "published": "...",
  "summary": "...",
  "title": "...",
  "updated": "...",
  "embedding_model": "...",
  "vector_indexed": <boolean>,
  "fulltext_indexed": <boolean>
}
```



### 3. AI Integration


### 4. Backend


### 5. Frontend


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



