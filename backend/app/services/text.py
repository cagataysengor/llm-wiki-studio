import re
from datetime import datetime
from hashlib import md5, sha1
from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".html"}
PDF_EXTENSION = ".pdf"
DOCX_EXTENSION = ".docx"


def detect_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def read_text_bytes(file_bytes: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode(errors="ignore")


def extract_text(filename: str, file_bytes: bytes) -> str:
    ext = detect_ext(filename)
    if ext in TEXT_EXTENSIONS:
        return read_text_bytes(file_bytes)
    if ext == PDF_EXTENSION:
        reader = PdfReader(BytesIO(file_bytes))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(page for page in pages if page)
    if ext == DOCX_EXTENSION:
        document = DocxDocument(BytesIO(file_bytes))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)
    raise RuntimeError(f"Unsupported file type for MVP scaffold: {ext}")


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 180) -> list[str]:
    clean = normalize_text(text)
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        chunk = clean[start:end]
        if end < len(clean):
            last_break = max(chunk.rfind("\n\n"), chunk.rfind(". "), chunk.rfind("\n"))
            if last_break > chunk_size // 2:
                end = start + last_break + 1
                chunk = clean[start:end]
        chunks.append(chunk.strip())
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return [item for item in chunks if item]


def make_doc_id(filename: str, text: str) -> str:
    raw = f"{filename}:{len(text)}:{md5(text.encode('utf-8', errors='ignore')).hexdigest()}"
    return sha1(raw.encode()).hexdigest()[:16]


def safe_slug(title: str) -> str:
    normalized = title.strip().lower()
    normalized = re.sub(r"[^a-z0-9ğüşöçıİĞÜŞÖÇ\s-]", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-") or f"page-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
