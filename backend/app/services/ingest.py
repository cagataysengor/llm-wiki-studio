import json
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.embeddings import embed_texts
from app.services.repositories import replace_document_chunks, upsert_document
from app.services.text import chunk_text, detect_ext, extract_text, make_doc_id, normalize_text
from app.services.wiki import create_or_update_source_summary_page


settings = get_settings()


def ingest_upload(db: Session, upload: UploadFile) -> dict[str, Any]:
    file_bytes = upload.file.read()
    if not file_bytes:
        raise RuntimeError("Uploaded file is empty.")

    text = normalize_text(extract_text(upload.filename or "unknown.txt", file_bytes))
    if not text:
        raise RuntimeError("No text could be extracted from the uploaded file.")

    target_path = settings.raw_dir / (upload.filename or "uploaded.txt")
    target_path.write_bytes(file_bytes)

    doc_id = make_doc_id(upload.filename or target_path.name, text)
    chunks = chunk_text(text)
    embeddings = embed_texts(chunks)
    _persist_chunks(
        doc_id=doc_id,
        filename=upload.filename or target_path.name,
        chunks=chunks,
    )
    upsert_document(
        db,
        doc_id=doc_id,
        filename=upload.filename or target_path.name,
        filepath=str(target_path),
        filetype=detect_ext(upload.filename or target_path.name),
        text_length=len(text),
    )
    replace_document_chunks(
        db,
        document_id=doc_id,
        filename=upload.filename or target_path.name,
        chunks=chunks,
        embeddings=embeddings,
    )
    summary_page = create_or_update_source_summary_page(
        db,
        doc_id=doc_id,
        filename=upload.filename or target_path.name,
        filetype=detect_ext(upload.filename or target_path.name),
        text=text,
        chunk_count=len(chunks),
    )
    return {
        "document_id": doc_id,
        "filename": upload.filename or target_path.name,
        "chunk_count": len(chunks),
        "text_length": len(text),
        "wiki_page_slug": summary_page["slug"],
        "wiki_page_title": summary_page["title"],
        "topic_page_slugs": [item["slug"] for item in summary_page.get("topic_pages", [])],
    }


def _persist_chunks(doc_id: str, filename: str, chunks: list[str]) -> None:
    chunk_path = settings.index_dir / "chunks.json"
    if chunk_path.exists():
        store = json.loads(chunk_path.read_text(encoding="utf-8"))
    else:
        store = []

    store.extend(
        {
            "id": f"{doc_id}_{idx}",
            "doc_id": doc_id,
            "filename": filename,
            "text": chunk,
            "embedding": None,
        }
        for idx, chunk in enumerate(chunks)
    )
    chunk_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
