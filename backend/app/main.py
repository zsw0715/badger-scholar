from fastapi import FastAPI

app = FastAPI(title="BadgerScholar API")

@app.get("/")
def root():
    return {"message": "Welcome to BadgerScholar"}

@app.get("/health")
def health():
    return {"status": "ok"}
