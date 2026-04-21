from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.wiki import WikiCreateRequest, WikiPageDetail, WikiPageListItem
from app.services.repositories import get_wiki_page_by_slug, list_wiki_pages
from app.services.wiki import create_manual_wiki_page


router = APIRouter(prefix="/wiki", tags=["wiki"])


@router.get("", response_model=list[WikiPageListItem])
def get_pages(db: Session = Depends(get_db)) -> list[WikiPageListItem]:
    return [WikiPageListItem.model_validate(item) for item in list_wiki_pages(db)]


@router.get("/{slug}", response_model=WikiPageDetail)
def get_page(slug: str, db: Session = Depends(get_db)) -> WikiPageDetail:
    page = get_wiki_page_by_slug(db, slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return WikiPageDetail.model_validate(page)


@router.post("", response_model=WikiPageDetail)
def create_page(payload: WikiCreateRequest, db: Session = Depends(get_db)) -> WikiPageDetail:
    page = create_manual_wiki_page(db=db, title=payload.title, markdown=payload.markdown)
    return WikiPageDetail.model_validate(page)

