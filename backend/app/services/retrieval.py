from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document_chunk import DocumentChunk, EMBEDDING_DIMENSIONS
from app.services.repositories import list_wiki_pages
from app.services.embeddings import embed_text


settings = get_settings()

TECHNICAL_QUERY_TOKENS = {
    "kütüphane",
    "kutuphane",
    "library",
    "libraries",
    "import",
    "dependency",
    "dependencies",
    "requirements",
    "package",
    "packages",
    "module",
    "modül",
    "modul",
    "framework",
    "kod",
    "code",
    "python",
    "react",
    "next",
    "fastapi",
    "streamlit",
    "endpoint",
    "api",
    "fonksiyon",
    "function",
    "class",
    "metot",
    "method",
}

NARRATIVE_QUERY_TOKENS = {
    "kim",
    "who",
    "karakter",
    "character",
    "hikaye",
    "story",
    "roman",
    "novel",
    "kitap",
    "book",
    "özet",
    "ozet",
    "summary",
    "delikanlı",
    "simyacı",
    "simyaci",
    "olay",
    "plot",
    "kahraman",
    "başrol",
    "basrol",
}

TECHNICAL_CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".ipynb"}
TECHNICAL_CONFIG_SUFFIXES = {".toml", ".json", ".yaml", ".yml", ".ini", ".cfg", ".lock"}
NARRATIVE_SUFFIXES = {".pdf", ".docx"}


def retrieve_chunks(db: Session, query: str, top_k: int = 6) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    intent = _classify_query_intent(query)
    expanded_top_k = max(top_k * 6, 24)

    if settings.database_url.startswith("postgresql"):
        rows = db.execute(
            text(
                f"""
                SELECT
                    id,
                    document_id,
                    filename,
                    text,
                    1 - (embedding <=> CAST(:embedding AS vector({EMBEDDING_DIMENSIONS}))) AS score
                FROM document_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector({EMBEDDING_DIMENSIONS}))
                LIMIT :top_k
                """
            ),
            {
                "embedding": _vector_literal(embed_text(query)),
                "top_k": expanded_top_k,
            },
        ).mappings()
        candidates = [
            {
                "document_id": row["document_id"],
                "filename": row["filename"],
                "text": row["text"],
                "score": float(row["score"]),
            }
            for row in rows
        ]
        return _rank_and_select_chunks(candidates, query=query, top_k=top_k, intent=intent)

    query_embedding = embed_text(query)
    rows = db.scalars(select(DocumentChunk).where(DocumentChunk.embedding.is_not(None))).all()

    candidates: list[dict[str, Any]] = []
    for row in rows:
        embedding = row.embedding
        if not embedding:
            continue
        semantic_score = sum(a * b for a, b in zip(query_embedding, embedding))
        candidates.append(
            {
                "document_id": row.document_id,
                "filename": row.filename,
                "text": row.text,
                "score": float(semantic_score),
            }
        )

    candidates.sort(key=lambda item: float(item["score"]), reverse=True)
    candidates = candidates[:expanded_top_k]
    return _rank_and_select_chunks(candidates, query=query, top_k=top_k, intent=intent)


def read_wiki_snippets(limit: int = 4) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    for path in sorted(settings.wiki_dir.glob("*.md"))[:limit]:
        snippets.append(
            {
                "slug": path.stem,
                "title": path.stem.replace("-", " ").title(),
                "text": path.read_text(encoding="utf-8")[:2500],
            }
        )
    return snippets


def retrieve_wiki_pages(db: Session, query: str, top_k: int = 4) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    intent = _classify_query_intent(query)
    lowered_query = query.lower()
    query_terms = [term for term in lowered_query.split() if len(term) >= 3]

    pages = [
        page
        for page in list_wiki_pages(db)
        if str(page.get("slug", "")) not in {"index", "log"}
    ]
    scored_pages: list[dict[str, Any]] = []
    for page in pages:
        title = str(page.get("title", ""))
        slug = str(page.get("slug", ""))
        summary = str(page.get("summary", ""))
        markdown = str(page.get("markdown", ""))
        tags = [str(item).lower() for item in page.get("tags", [])]

        score = 0.0
        lowered_title = title.lower()
        lowered_slug = slug.lower()
        lowered_summary = summary.lower()
        lowered_markdown = markdown.lower()

        title_hits = sum(term in lowered_title for term in query_terms)
        slug_hits = sum(term in lowered_slug for term in query_terms)
        summary_hits = sum(term in lowered_summary for term in query_terms)
        markdown_hits = sum(term in lowered_markdown for term in query_terms)

        score += 0.16 * title_hits
        score += 0.12 * slug_hits
        score += 0.08 * summary_hits
        score += 0.03 * markdown_hits

        if "topic-page" in tags and intent == "technical":
            score += 0.18
        if "source-summary" in tags and intent in {"narrative", "general"}:
            score += 0.12
        if "qa-generated" in tags:
            score += 0.05

        if any(term in lowered_markdown for term in query_terms):
            score += 0.08

        if score <= 0:
            continue

        scored_pages.append(
            {
                "slug": slug,
                "title": title,
                "summary": summary,
                "markdown": markdown,
                "score": round(score, 4),
            }
        )

    scored_pages.sort(key=lambda item: float(item["score"]), reverse=True)
    return scored_pages[:top_k]


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{item:.8f}" for item in vector) + "]"


def _classify_query_intent(query: str) -> str:
    lowered = query.lower()
    technical_hits = sum(token in lowered for token in TECHNICAL_QUERY_TOKENS)
    narrative_hits = sum(token in lowered for token in NARRATIVE_QUERY_TOKENS)

    if technical_hits > narrative_hits and technical_hits > 0:
        return "technical"
    if narrative_hits > technical_hits and narrative_hits > 0:
        return "narrative"
    return "general"


def _rank_and_select_chunks(
    candidates: list[dict[str, Any]],
    *,
    query: str,
    top_k: int,
    intent: str,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    lowered_query = query.lower()
    rescored_candidates = [_rescore_candidate(item, query=lowered_query, intent=intent) for item in candidates]
    document_scores = _score_documents(rescored_candidates)
    top_document_ids = _select_top_documents(document_scores=document_scores, top_k=top_k, intent=intent)

    selected_from_top_docs = [item for item in rescored_candidates if str(item["document_id"]) in top_document_ids]
    selected_from_top_docs.sort(key=lambda item: float(item["score"]), reverse=True)
    return _select_chunks_from_top_documents(
        selected_from_top_docs,
        top_k=top_k,
        max_documents=len(top_document_ids),
        max_chunks_per_document=_chunks_per_document_for_intent(intent),
    )


def _rescore_candidate(item: dict[str, Any], *, query: str, intent: str) -> dict[str, Any]:
    filename = str(item.get("filename", ""))
    text = str(item.get("text", ""))
    suffix = Path(filename).suffix.lower()
    score = float(item.get("score", 0.0))

    score += _intent_file_bias(filename=filename, suffix=suffix, intent=intent)
    score += _lexical_overlap_bias(query=query, filename=filename, text=text, intent=intent)
    score += _structure_bias(text=text, suffix=suffix, intent=intent)

    rescored = dict(item)
    rescored["score"] = score
    return rescored


def _score_documents(candidates: list[dict[str, Any]]) -> dict[str, float]:
    document_scores: dict[str, float] = {}
    for item in candidates:
        document_id = str(item.get("document_id", ""))
        score = float(item.get("score", 0.0))
        previous = document_scores.get(document_id)
        if previous is None:
            document_scores[document_id] = score
        else:
            document_scores[document_id] = max(previous, score) + (0.15 * min(previous, score))
    return document_scores


def _select_top_documents(*, document_scores: dict[str, float], top_k: int, intent: str) -> list[str]:
    if not document_scores:
        return []

    if intent == "technical":
        max_documents = 2
    elif intent == "narrative":
        max_documents = 2
    else:
        max_documents = 2

    ranked_documents = sorted(document_scores.items(), key=lambda pair: pair[1], reverse=True)
    top_score = ranked_documents[0][1]
    minimum_score = max(top_score * 0.55, top_score - 0.22)

    selected: list[str] = []
    for document_id, score in ranked_documents:
        if len(selected) >= max_documents:
            break
        if score < minimum_score and selected:
            continue
        selected.append(document_id)

    return selected


def _chunks_per_document_for_intent(intent: str) -> int:
    if intent == "technical":
        return 1
    if intent == "narrative":
        return 2
    return 2


def _intent_file_bias(*, filename: str, suffix: str, intent: str) -> float:
    lowered = filename.lower()

    if intent == "technical":
        if suffix in TECHNICAL_CODE_SUFFIXES:
            return 0.24
        if suffix in TECHNICAL_CONFIG_SUFFIXES:
            return 0.18
        if suffix in {".md", ".txt"} and any(
            name in lowered for name in ("readme", "requirements", "package", "pyproject", "poetry", "dockerfile")
        ):
            return 0.14
        if suffix in NARRATIVE_SUFFIXES:
            return -0.18
        return 0.0

    if intent == "narrative":
        if suffix in NARRATIVE_SUFFIXES:
            return 0.2
        if suffix in {".md", ".txt"}:
            return 0.1
        if suffix in TECHNICAL_CODE_SUFFIXES | TECHNICAL_CONFIG_SUFFIXES:
            return -0.2
        return 0.0

    return 0.0


def _lexical_overlap_bias(*, query: str, filename: str, text: str, intent: str) -> float:
    query_terms = [term for term in query.split() if len(term) >= 3]
    if not query_terms:
        return 0.0

    lowered_filename = filename.lower()
    lowered_text = text.lower()
    filename_hits = sum(term in lowered_filename for term in query_terms)
    text_hits = sum(term in lowered_text for term in query_terms)

    if intent == "technical":
        return (0.05 * filename_hits) + (0.03 * text_hits)
    if intent == "narrative":
        return (0.03 * filename_hits) + (0.05 * text_hits)
    return (0.03 * filename_hits) + (0.03 * text_hits)


def _structure_bias(*, text: str, suffix: str, intent: str) -> float:
    lowered_text = text.lower()

    if intent == "technical":
        bias = 0.0
        if suffix in TECHNICAL_CODE_SUFFIXES and ("import " in lowered_text or "from " in lowered_text):
            bias += 0.08
        if suffix in TECHNICAL_CONFIG_SUFFIXES and any(
            token in lowered_text for token in ("dependencies", "requires", "package", "tool.poetry", "project")
        ):
            bias += 0.08
        return bias

    if intent == "narrative":
        bias = 0.0
        if any(token in lowered_text for token in ("dedi", "sordu", "karakter", "chapter", "bölüm", "bolum")):
            bias += 0.06
        return bias

    return 0.0


def _select_chunks_from_top_documents(
    results: list[dict[str, Any]],
    *,
    top_k: int,
    max_documents: int | None = None,
    max_chunks_per_document: int = 2,
) -> list[dict[str, Any]]:
    if not results:
        return []

    if max_documents is None:
        max_documents = min(max(top_k // 2, 1), top_k)

    chunks_by_document: dict[str, list[dict[str, Any]]] = {}
    document_scores: dict[str, float] = {}

    for item in results:
        document_id = str(item.get("document_id", ""))
        chunks_by_document.setdefault(document_id, []).append(item)
        document_scores[document_id] = max(document_scores.get(document_id, float("-inf")), float(item["score"]))

    top_document_ids = [
        document_id
        for document_id, _ in sorted(document_scores.items(), key=lambda pair: pair[1], reverse=True)[:max_documents]
    ]

    selected: list[dict[str, Any]] = []
    counts_by_document: dict[str, int] = {document_id: 0 for document_id in top_document_ids}

    for item in results:
        document_id = str(item.get("document_id", ""))
        if document_id not in counts_by_document:
            continue
        used = counts_by_document[document_id]
        if used >= max_chunks_per_document:
            continue
        selected.append(item)
        counts_by_document[document_id] = used + 1
        if len(selected) >= top_k:
            return selected

    if selected:
        return selected[:top_k]
    return results[:top_k]
