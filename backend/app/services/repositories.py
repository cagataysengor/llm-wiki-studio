import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.document import Document
from app.models.wiki_page import WikiPage


def upsert_document(
    db: Session,
    *,
    doc_id: str,
    filename: str,
    filepath: str,
    filetype: str,
    text_length: int,
) -> Document:
    item = db.get(Document, doc_id)
    if item is None:
        item = Document(
            id=doc_id,
            filename=filename,
            filepath=filepath,
            filetype=filetype,
            created_at=datetime.utcnow(),
            text_length=text_length,
        )
        db.add(item)
    else:
        item.filename = filename
        item.filepath = filepath
        item.filetype = filetype
        item.text_length = text_length
    db.commit()
    db.refresh(item)
    return item


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())).all())


def get_document_by_id(db: Session, document_id: str) -> Document | None:
    return db.get(Document, document_id)


def replace_document_chunks(
    db: Session,
    *,
    document_id: str,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    rows = [
        DocumentChunk(
            id=f"{document_id}_{index}",
            document_id=document_id,
            filename=filename,
            chunk_index=index,
            text=chunk,
            embedding=embeddings[index],
            created_at=datetime.utcnow(),
        )
        for index, chunk in enumerate(chunks)
    ]
    db.add_all(rows)
    db.commit()


def list_document_chunks(db: Session) -> list[DocumentChunk]:
    return list(
        db.scalars(
            select(DocumentChunk).order_by(DocumentChunk.created_at.desc(), DocumentChunk.chunk_index.asc())
        ).all()
    )


def upsert_wiki_page(
    db: Session,
    *,
    slug: str,
    title: str,
    filepath: str,
    summary: str,
    tags: list[str],
    source_doc_ids: list[str],
) -> WikiPage:
    page = db.get(WikiPage, slug)
    if page is None:
        page = WikiPage(
            slug=slug,
            title=title,
            filepath=filepath,
            summary=summary,
            tags=json.dumps(tags, ensure_ascii=False),
            source_doc_ids=json.dumps(source_doc_ids, ensure_ascii=False),
            updated_at=datetime.utcnow(),
        )
        db.add(page)
    else:
        page.title = title
        page.filepath = filepath
        page.summary = summary
        page.tags = json.dumps(tags, ensure_ascii=False)
        page.source_doc_ids = json.dumps(source_doc_ids, ensure_ascii=False)
        page.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(page)
    return page


def list_wiki_pages(db: Session) -> list[dict[str, Any]]:
    pages = list(db.scalars(select(WikiPage).order_by(WikiPage.updated_at.desc())).all())
    return [_serialize_wiki_page(page) for page in pages]


def get_wiki_page_by_slug(db: Session, slug: str) -> dict[str, Any] | None:
    page = db.get(WikiPage, slug)
    if page is None:
        return None
    return _serialize_wiki_page(page)


def delete_wiki_page_by_slug(db: Session, slug: str) -> dict[str, Any] | None:
    page = db.get(WikiPage, slug)
    if page is None:
        return None
    serialized = _serialize_wiki_page(page)
    db.delete(page)
    db.commit()
    return serialized


def _serialize_wiki_page(page: WikiPage) -> dict[str, Any]:
    markdown = ""
    try:
        markdown = Path(page.filepath).read_text(encoding="utf-8")
    except OSError:
        markdown = ""
    return {
        "slug": page.slug,
        "title": page.title,
        "filepath": page.filepath,
        "summary": page.summary or "",
        "tags": json.loads(page.tags) if page.tags else [],
        "source_doc_ids": json.loads(page.source_doc_ids) if page.source_doc_ids else [],
        "updated_at": page.updated_at,
        "markdown": markdown,
    }
