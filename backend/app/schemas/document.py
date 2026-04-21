from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    filepath: str
    filetype: str | None
    created_at: datetime
    text_length: int


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    text_length: int
    wiki_page_slug: str | None = None
    wiki_page_title: str | None = None
    topic_page_slugs: list[str] = []


class ReindexRequest(BaseModel):
    document_id: str | None = None


class ReindexResponse(BaseModel):
    reindexed_documents: int
    reindexed_chunks: int
