from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.qa import AskRequest, AskResponse, SaveAnswerRequest, SaveAnswerResponse
from app.services.qa import answer_question, save_answer_to_wiki


router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    settings = get_settings()
    response = answer_question(
        db=db,
        question=payload.question,
        provider=payload.provider,
        model_name=payload.model_name,
        api_key=settings.get_provider_api_key(payload.provider),
        llm_url=payload.llm_url,
        embed_model=payload.embed_model,
        top_k=payload.top_k,
    )
    return AskResponse.model_validate(response)


@router.post("/save", response_model=SaveAnswerResponse)
def save_qa_result(payload: SaveAnswerRequest, db: Session = Depends(get_db)) -> SaveAnswerResponse:
    response = save_answer_to_wiki(
        db=db,
        title=payload.title,
        question=payload.question,
        answer=payload.answer,
        source_files=payload.source_files,
        merge_if_similar=payload.merge_if_similar,
    )
    return SaveAnswerResponse.model_validate(response)
