from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    provider: str = "Local"
    model_name: str = "local-model"
    llm_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    embed_model: str = "intfloat/multilingual-e5-base"
    top_k: int = 6


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    question: str
    sources: list[SourceChunk]


class SaveAnswerRequest(BaseModel):
    title: str
    question: str
    answer: str
    source_files: list[str] = []
    merge_if_similar: bool = True


class SaveAnswerResponse(BaseModel):
    slug: str
    title: str
    filepath: str
    action: str
