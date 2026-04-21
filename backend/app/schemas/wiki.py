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


class WikiLintFinding(BaseModel):
    severity: str
    category: str
    page_slug: str | None = None
    page_title: str | None = None
    message: str


class WikiLintResponse(BaseModel):
    checked_pages: int
    findings: list[WikiLintFinding]


class WikiDeleteResponse(BaseModel):
    slug: str
    title: str
    action: str
