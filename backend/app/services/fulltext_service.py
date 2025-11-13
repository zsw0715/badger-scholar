# this file handles:
# 从 arXiv 下载论文 PDF
# 提取全文文本
# 清洗文本
# 切分文本成 chunk 以供 RAG 使用

import os
import re
import requests
from typing import Dict, List
from pypdf import PdfReader
from tqdm import tqdm

class FullTextService:
  """
  Fetch full text for an arXiv paper.
  Supports:
    - PDF download
    - Extract text
    - Clean text
    - Chunk into RAG segments
  """

  ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"

  def __init__(self):
    print("FullTextService initialized.")

  # ========= Download PDF =========
  def download_pdf(self, arxiv_id: str, save_dir="/tmp/arxiv_pdfs") -> str:
    """
    Download arXiv PDF and return local path.
    """
    os.makedirs(save_dir, exist_ok=True)
    pdf_path = os.path.join(save_dir, f"{arxiv_id}.pdf")

    if os.path.exists(pdf_path):
      return pdf_path

    url = self.ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    print(f"Downloading PDF: {url}")

    response = requests.get(url, stream=True)
    if response.status_code != 200:
      raise Exception(f"Failed to download PDF: {url}")

    with open(pdf_path, "wb") as f:
      for chunk in response.iter_content(1024):
        f.write(chunk)

    return pdf_path

  # ========= Extract PDF text =========
  def extract_text(self, pdf_path: str) -> str:
    """Extract text from PDF."""
    reader = PdfReader(pdf_path)

    full_text = ""
    for page in reader.pages:
      full_text += page.extract_text() + "\n\n"

    return full_text

  # ========= Clean text =========
  @staticmethod
  def clean_text(text: str) -> str:
    """
    Remove LaTeX garbage, citation numbers, references...
    Make the text cleaner and more LLM-friendly.
    """

    # Remove references like [1], [2], [12]
    text = re.sub(r"\[[0-9]{1,3}\]", "", text)

    # Remove LaTeX math $...$
    text = re.sub(r"\$[^$]+\$", "", text)

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()

  # ========= Chunk text =========
  @staticmethod
  def chunk_text(text: str, chunk_size=1500, overlap=200) -> List[str]:
    """
    Chunk text into overlapping pieces for RAG.
    Typical:
      - chunk_size = 1500 characters (~300 tokens)
      - overlap    = 200 characters to preserve context
    """
    chunks = []
    start = 0

    while start < len(text):
      end = start + chunk_size
      chunk = text[start:end]
      chunks.append(chunk)
      start += chunk_size - overlap

    return chunks

  # ========= High-level function =========
  def get_fulltext_chunks(self, arxiv_id: str) -> List[Dict]:
    """
    Pipeline:
      1. Download PDF
      2. Extract text
      3. Clean text
      4. Chunk
      5. Return [{chunk_id, text}]
    """

    pdf_path = self.download_pdf(arxiv_id)
    raw_text = self.extract_text(pdf_path)
    cleaned = self.clean_text(raw_text)
    chunks = self.chunk_text(cleaned)

    result = []
    for i, ch in enumerate(chunks):
      result.append({
          "arxiv_id": arxiv_id,
          "chunk_id": f"{arxiv_id}_chunk_{i}",
          "text": ch
      })

    print(f"Generated {len(result)} chunks for {arxiv_id}")
    return result


# Singleton
fulltext_service = FullTextService()