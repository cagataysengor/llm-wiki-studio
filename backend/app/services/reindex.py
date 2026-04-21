from sqlalchemy.orm import Session

from app.services.embeddings import embed_texts
from app.services.repositories import get_document_by_id, list_documents, replace_document_chunks
from app.services.text import chunk_text, extract_text, normalize_text


def reindex_documents(db: Session, document_id: str | None = None) -> dict[str, int]:
    targets = []
    if document_id:
        document = get_document_by_id(db, document_id)
        if document is None:
            raise RuntimeError("Document not found for reindex.")
        targets = [document]
    else:
        targets = list_documents(db)

    reindexed_documents = 0
    reindexed_chunks = 0

    for document in targets:
        file_bytes = open(document.filepath, "rb").read()
        text = normalize_text(extract_text(document.filename, file_bytes))
        chunks = chunk_text(text)
        embeddings = embed_texts(chunks)
        replace_document_chunks(
            db,
            document_id=document.id,
            filename=document.filename,
            chunks=chunks,
            embeddings=embeddings,
        )
        reindexed_documents += 1
        reindexed_chunks += len(chunks)

    return {
        "reindexed_documents": reindexed_documents,
        "reindexed_chunks": reindexed_chunks,
    }
