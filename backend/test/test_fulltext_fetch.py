# test_fulltext_fetch.py

import requests
from pypdf import PdfReader
import os


def download_pdf(arxiv_id: str, save_dir="/tmp/arxiv_test"):
    """Download arXiv PDF and return local path."""
    os.makedirs(save_dir, exist_ok=True)
    pdf_path = os.path.join(save_dir, f"{arxiv_id}.pdf")

    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    print(f"Downloading PDF: {url}")

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download PDF: {url}")

    with open(pdf_path, "wb") as f:
        for chunk in response.iter_content(1024):
            f.write(chunk)

    return pdf_path


def extract_pdf_text(pdf_path: str) -> str:
    """Extract raw text from PDF file."""
    print(f"Extracting text from: {pdf_path}")
    reader = PdfReader(pdf_path)

    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n\n"

    return full_text


if __name__ == "__main__":
    arxiv_id = "2511.07943"

    # Step 1: Download PDF
    pdf_path = download_pdf(arxiv_id)

    # Step 2: Extract text
    text = extract_pdf_text(pdf_path)

    print("\n========== Extracted Text (first 2000 chars) ==========\n")
    print(text[:2000])
    print("\n======================================================\n")
    print(f"Total characters extracted: {len(text)}")
    