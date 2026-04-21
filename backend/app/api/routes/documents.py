from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import DocumentListItem, IngestResponse, ReindexRequest, ReindexResponse
from app.services.ingest import ingest_upload
from app.services.reindex import reindex_documents
from app.services.repositories import list_documents


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentListItem])
def get_documents(db: Session = Depends(get_db)) -> list[DocumentListItem]:
    return [DocumentListItem.model_validate(item) for item in list_documents(db)]


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> IngestResponse:
    try:
        payload = ingest_upload(db=db, upload=file)
        return IngestResponse.model_validate(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reindex", response_model=ReindexResponse)
def reindex_document_embeddings(
    payload: ReindexRequest,
    db: Session = Depends(get_db),
) -> ReindexResponse:
    try:
        result = reindex_documents(db=db, document_id=payload.document_id)
        return ReindexResponse.model_validate(result)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
