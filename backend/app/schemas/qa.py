from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    provider: str = "Local"
    model_name: str = "local-model"
    llm_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    embed_model: str = "intfloat/multilingual-e5-base"
    top_k: int = 6
    agentic_mode: bool = False


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    text: str
    score: float


class AgenticWikiPageRef(BaseModel):
    slug: str
    title: str
    score: float


class AgenticTokenEstimate(BaseModel):
    context_tokens: int
    answer_tokens: int
    raw_retrieval_avoided: bool


class AgenticSuggestedUpdate(BaseModel):
    kind: str
    action: str
    target_slug: str
    title: str
    reason: str
    markdown: str


class AgenticSufficiencyFactor(BaseModel):
    name: str
    score: float
    reason: str


class AgenticWikiReport(BaseModel):
    enabled: bool
    wiki_sufficiency_score: float
    wiki_coverage: str
    wiki_confidence: str
    query_intent: str
    sufficiency_factors: list[AgenticSufficiencyFactor]
    used_raw_sources: bool
    why_raw_retrieval_needed: str
    wiki_pages: list[AgenticWikiPageRef]
    matched_wiki_terms: list[str]
    matched_source_terms: list[str]
    suggested_updates: list[AgenticSuggestedUpdate]
    agent_steps: list[str]
    token_estimate: AgenticTokenEstimate


class AskResponse(BaseModel):
    answer: str
    question: str
    sources: list[SourceChunk]
    agentic: AgenticWikiReport | None = None


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
