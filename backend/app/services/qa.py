from sqlalchemy.orm import Session

from app.services.llm import answer_with_provider
from app.services.retrieval import retrieve_chunks, retrieve_wiki_pages
from app.services.repositories import list_wiki_pages
from app.services.text import safe_slug
from app.services.wiki import append_wiki_log, create_or_merge_qa_wiki_page


def answer_question(
    *,
    db: Session,
    question: str,
    provider: str,
    model_name: str,
    api_key: str,
    llm_url: str,
    embed_model: str,
    top_k: int,
) -> dict[str, object]:
    del embed_model

    wiki_pages = retrieve_wiki_pages(db, question, top_k=max(3, min(top_k, 4)))
    sources = retrieve_chunks(db, question, top_k=top_k)
    source_char_limit = 1200
    wiki_char_limit = 1400
    context_budget = 6500
    completion_budget = 1200

    context_parts: list[str] = []
    for index, wiki in enumerate(wiki_pages, start=1):
        context_parts.append(
            f"[WIKI PAGE {index} | title={wiki['title']} | slug={wiki['slug']} | score={wiki['score']}]\n"
            f"{wiki['markdown'][:wiki_char_limit]}"
        )
    for index, source in enumerate(sources, start=1):
        context_parts.append(
            f"[SOURCE CHUNK {index} | file={source['filename']} | score={source['score']}]\n"
            f"{source['text'][:source_char_limit]}"
        )

    context = _join_with_budget(context_parts, max_chars=context_budget) if context_parts else "No indexed context was found."
    if provider == "Local":
        system = (
            "You answer questions using the provided wiki pages first and source chunks second. "
            "Treat the wiki as the primary synthesized knowledge layer, and use raw source chunks to support or refine it. "
            "Write a concise but complete answer in 3 short parts when possible: "
            "1) direct answer, 2) relationship or difference, 3) one or two concrete examples. "
            "Do not answer with a single short sentence unless the question is trivial. "
            "End with a short Sources section."
        )
    else:
        system = (
            "You answer questions using the provided wiki pages first and source chunks second. "
            "Treat the wiki as the primary synthesized knowledge layer, and use raw source chunks to support or refine it. "
            "Prefer grounded answers. If context is weak, say so clearly. End with a short Sources section."
        )
    user = f"Question: {question}\n\nContext:\n{context}"
    answer = answer_with_provider(
        provider=provider,
        llm_url=llm_url,
        model_name=model_name,
        api_key=api_key,
        system_prompt=system,
        user_prompt=user,
        max_tokens=completion_budget,
    )
    append_wiki_log(
        event_type="ask",
        title=question[:120],
        details={
            "provider": provider,
            "top_k": str(top_k),
            "wiki_page_count": str(len(wiki_pages)),
            "source_count": str(len(sources)),
        },
    )
    return {
        "question": question,
        "answer": answer,
        "sources": sources,
    }


def save_answer_to_wiki(
    *,
    db: Session,
    title: str,
    question: str,
    answer: str,
    source_files: list[str],
    merge_if_similar: bool,
) -> dict[str, str]:
    merge_target: dict[str, object] | None = None
    if merge_if_similar:
        merge_target = _find_similar_page_by_title(db=db, title=title)

    return create_or_merge_qa_wiki_page(
        db=db,
        title=title,
        question=question,
        answer=answer,
        source_files=source_files,
        merge_target=merge_target,
    )


def _find_similar_page_by_title(*, db: Session, title: str) -> dict[str, object] | None:
    target_slug = safe_slug(title)
    lowered_title = title.strip().lower()
    for page in list_wiki_pages(db):
        slug = str(page.get("slug", ""))
        existing_title = str(page.get("title", "")).strip().lower()
        if slug == target_slug or existing_title == lowered_title:
            return page
        if target_slug and (target_slug in slug or slug in target_slug):
            return page
    return None


def _join_with_budget(parts: list[str], *, max_chars: int) -> str:
    kept: list[str] = []
    total = 0
    for part in parts:
        if total >= max_chars:
            break
        remaining = max_chars - total
        if len(part) > remaining:
            kept.append(part[:remaining])
            break
        kept.append(part)
        total += len(part) + 2
    return "\n\n".join(kept)
