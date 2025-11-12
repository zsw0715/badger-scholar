from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import etl

app = FastAPI(
    title="BadgerScholar API",
    description="AI-Powered Research Assistant",
    version="0.1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# register routers
app.include_router(etl.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to BadgerScholar API",
        "docs": "/docs",
        "version": "0.1.0"
    }

@app.get("/health")
def health():
    return {"status": "ok"}


