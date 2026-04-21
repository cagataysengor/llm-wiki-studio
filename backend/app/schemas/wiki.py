from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WikiPageListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    filepath: str
    summary: str | None
    tags: list[str]
    source_doc_ids: list[str]
    updated_at: datetime


class WikiPageDetail(WikiPageListItem):
    markdown: str


class WikiCreateRequest(BaseModel):
    title: str
    markdown: str

