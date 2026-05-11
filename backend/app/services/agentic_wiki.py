import json
from typing import Any

from app.services.llm import answer_with_provider


def should_use_raw_retrieval(*, wiki_pages: list[dict[str, Any]], question: str) -> tuple[bool, float, str]:
    analysis = analyze_wiki_sufficiency(wiki_pages=wiki_pages, question=question)
    score = float(analysis["score"])
    if not wiki_pages:
        return True, score, "No wiki pages matched the question, so raw source retrieval is needed."
    if score < 0.62:
        weakest = min(analysis["factors"], key=lambda item: float(item["score"]))
        return True, score, f"Wiki memory is weak on {weakest['name']}, so raw source retrieval is needed."
    return False, score, "The wiki memory looks sufficient, so raw source retrieval was skipped."


def build_agentic_report(
    *,
    question: str,
    wiki_pages: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    wiki_sufficiency_score: float,
    raw_retrieval_needed: bool,
    raw_retrieval_reason: str,
    context: str,
    answer: str,
    provider: str,
    model_name: str,
    api_key: str,
    llm_url: str,
) -> dict[str, object]:
    sufficiency = analyze_wiki_sufficiency(wiki_pages=wiki_pages, question=question)
    wiki_terms = _matched_terms(question, _wiki_text(wiki_pages))
    source_terms = _matched_terms(question, " ".join(str(item.get("text", "")) for item in sources))
    wiki_page_refs = [
        {
            "slug": str(page.get("slug", "")),
            "title": str(page.get("title", "")),
            "score": float(page.get("score", 0.0)),
        }
        for page in wiki_pages
    ]
    suggestions = _suggest_updates(
        question=question,
        wiki_pages=wiki_pages,
        sources=sources,
        wiki_sufficiency_score=wiki_sufficiency_score,
        raw_retrieval_needed=raw_retrieval_needed,
        answer=answer,
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        llm_url=llm_url,
    )

    return {
        "enabled": True,
        "wiki_sufficiency_score": wiki_sufficiency_score,
        "wiki_coverage": _coverage_label(wiki_sufficiency_score),
        "wiki_confidence": sufficiency["confidence"],
        "query_intent": sufficiency["query_intent"],
        "sufficiency_factors": sufficiency["factors"],
        "used_raw_sources": bool(sources),
        "why_raw_retrieval_needed": raw_retrieval_reason,
        "wiki_pages": wiki_page_refs,
        "matched_wiki_terms": wiki_terms,
        "matched_source_terms": source_terms,
        "suggested_updates": suggestions,
        "agent_steps": [
            "Checked synthesized wiki memory before raw source retrieval.",
            raw_retrieval_reason,
            "Generated an answer from the selected context.",
            "Prepared wiki improvement suggestions for reuse in future questions.",
        ],
        "token_estimate": {
            "context_tokens": _estimate_tokens(context),
            "answer_tokens": _estimate_tokens(answer),
            "raw_retrieval_avoided": not raw_retrieval_needed,
        },
    }


def calculate_wiki_sufficiency_score(*, wiki_pages: list[dict[str, Any]], question: str) -> float:
    return float(analyze_wiki_sufficiency(wiki_pages=wiki_pages, question=question)["score"])


def analyze_wiki_sufficiency(*, wiki_pages: list[dict[str, Any]], question: str) -> dict[str, object]:
    if not wiki_pages:
        return {
            "score": 0.0,
            "confidence": "low",
            "query_intent": _classify_query_intent(question),
            "factors": [
                {"name": "retrieval_strength", "score": 0.0, "reason": "No wiki pages matched."},
                {"name": "lexical_coverage", "score": 0.0, "reason": "No matched wiki text."},
                {"name": "page_quality", "score": 0.0, "reason": "No page quality can be estimated."},
                {"name": "topic_connectivity", "score": 0.0, "reason": "No wiki links are available."},
            ],
        }

    terms = _query_terms(question)
    wiki_text = _wiki_text(wiki_pages)
    lexical_coverage = 0.0
    if terms:
        lexical_coverage = len(_matched_terms(question, wiki_text)) / len(terms)

    top_score = max(float(page.get("score", 0.0)) for page in wiki_pages)
    retrieval_strength = min(top_score / 0.7, 1.0)
    page_quality = _page_quality_score(wiki_pages)
    topic_connectivity = _topic_connectivity_score(wiki_pages)
    source_topic_balance = _source_topic_balance_score(wiki_pages)
    intent_alignment = _intent_alignment_score(wiki_pages, question=question)

    score = (
        (0.30 * lexical_coverage)
        + (0.28 * retrieval_strength)
        + (0.18 * page_quality)
        + (0.10 * topic_connectivity)
        + (0.08 * source_topic_balance)
        + (0.06 * intent_alignment)
    )
    bounded = round(max(0.0, min(score, 1.0)), 2)
    confidence = "high" if bounded >= 0.75 else "medium" if bounded >= 0.55 else "low"
    return {
        "score": bounded,
        "confidence": confidence,
        "query_intent": _classify_query_intent(question),
        "factors": [
            {
                "name": "lexical_coverage",
                "score": round(lexical_coverage, 2),
                "reason": f"{len(_matched_terms(question, wiki_text))} of {len(terms)} query terms matched wiki text.",
            },
            {
                "name": "retrieval_strength",
                "score": round(retrieval_strength, 2),
                "reason": f"Top wiki retrieval score is {top_score:.2f}.",
            },
            {
                "name": "page_quality",
                "score": round(page_quality, 2),
                "reason": "Measures page length, headings, and source/reference structure.",
            },
            {
                "name": "topic_connectivity",
                "score": round(topic_connectivity, 2),
                "reason": "Measures whether matched pages link to other wiki topics.",
            },
            {
                "name": "source_topic_balance",
                "score": round(source_topic_balance, 2),
                "reason": "Rewards coverage from both source summaries and topic pages.",
            },
            {
                "name": "intent_alignment",
                "score": round(intent_alignment, 2),
                "reason": "Checks whether page tags match the apparent query intent.",
            },
        ],
    }


def _suggest_updates(
    *,
    question: str,
    wiki_pages: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    wiki_sufficiency_score: float,
    raw_retrieval_needed: bool,
    answer: str,
    provider: str,
    model_name: str,
    api_key: str,
    llm_url: str,
) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    if wiki_sufficiency_score < 0.45:
        title = _suggested_title(question)
        suggestions.append(
            {
                "kind": "create_topic_page",
                "action": "create",
                "target_slug": "",
                "title": title,
                "reason": "The wiki did not have enough synthesized coverage for this question.",
                "markdown": _build_topic_draft(title=title, question=question, answer=answer, sources=sources),
            }
        )
    elif raw_retrieval_needed and wiki_pages:
        target_page = wiki_pages[0]
        title = str(target_page.get("title", "Matched wiki page"))
        suggestions.append(
            {
                "kind": "update_existing_page",
                "action": "update",
                "target_slug": str(target_page.get("slug", "")),
                "title": title,
                "reason": "Raw sources were needed even though a related wiki page exists.",
                "markdown": _build_update_draft(page=target_page, question=question, answer=answer, sources=sources),
            }
        )

    if sources:
        title = _suggested_title(question)
        suggestions.append(
            {
                "kind": "save_answer",
                "action": "create",
                "target_slug": "",
                "title": _suggested_title(question),
                "reason": "The answer used raw source evidence that could reduce future retrieval cost if saved.",
                "markdown": _build_answer_draft(title=title, question=question, answer=answer, sources=sources),
            }
        )

    suggestions = _refine_actionable_suggestions(
        suggestions=suggestions,
        question=question,
        answer=answer,
        sources=sources,
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        llm_url=llm_url,
    )

    if not suggestions:
        suggestions.append(
            {
                "kind": "no_action",
                "action": "none",
                "target_slug": "",
                "title": "No wiki update needed",
                "reason": "The wiki memory appears sufficient for this question.",
                "markdown": "",
            }
        )
    return suggestions


def _refine_actionable_suggestions(
    *,
    suggestions: list[dict[str, str]],
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
    provider: str,
    model_name: str,
    api_key: str,
    llm_url: str,
) -> list[dict[str, str]]:
    refined: list[dict[str, str]] = []
    for suggestion in suggestions:
        if suggestion.get("action") == "none":
            refined.append(suggestion)
            continue
        llm_patch = _generate_llm_wiki_patch(
            suggestion=suggestion,
            question=question,
            answer=answer,
            sources=sources,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            llm_url=llm_url,
        )
        if llm_patch:
            next_suggestion = dict(suggestion)
            next_suggestion["title"] = llm_patch["title"]
            if suggestion.get("action") == "update":
                existing = suggestion.get("markdown", "").split("\n\n## Agentic Update Proposal", 1)[0].rstrip()
                patch_markdown = llm_patch["markdown"].strip()
                if not patch_markdown.startswith("## "):
                    patch_markdown = "## Agentic Update Proposal\n" + patch_markdown
                next_suggestion["markdown"] = f"{existing}\n\n{patch_markdown}\n"
            else:
                next_suggestion["markdown"] = llm_patch["markdown"]
            next_suggestion["reason"] = llm_patch["reason"]
            refined.append(next_suggestion)
        else:
            refined.append(suggestion)
    return refined


def _generate_llm_wiki_patch(
    *,
    suggestion: dict[str, str],
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
    provider: str,
    model_name: str,
    api_key: str,
    llm_url: str,
) -> dict[str, str] | None:
    if provider == "Disabled":
        return None

    source_names = ", ".join(list(dict.fromkeys(str(item.get("filename", "")) for item in sources))) or "wiki pages only"
    system = (
        "You write compact markdown wiki patches. Return only valid JSON with keys title, reason, markdown. "
        "Do not wrap the JSON in markdown fences. Keep markdown under 220 words. "
        "Use the same language as the user's question. Prefer reusable synthesized notes over full answers."
    )
    user = (
        f"Patch action: {suggestion.get('kind')}\n"
        f"Current title: {suggestion.get('title')}\n"
        f"Question: {question}\n"
        f"Source files: {source_names}\n\n"
        f"Answer to compact:\n{_compact_answer_note(answer, max_chars=1400)}\n\n"
        "Create markdown with: H1 title, short Context, Reusable Note, Sources. "
        "For an update patch, produce only the new section to append."
    )
    try:
        raw = answer_with_provider(
            provider=provider,
            llm_url=llm_url,
            model_name=model_name,
            api_key=api_key,
            system_prompt=system,
            user_prompt=user,
            max_tokens=500,
        )
        payload = _parse_json_object(raw)
        title = str(payload.get("title", "")).strip()
        reason = str(payload.get("reason", "")).strip()
        markdown = str(payload.get("markdown", "")).strip()
        if not title or not reason or not markdown:
            return None
        return {"title": title[:100], "reason": reason[:240], "markdown": markdown}
    except Exception:
        return None


def _coverage_label(score: float) -> str:
    if score >= 0.75:
        return "strong"
    if score >= 0.55:
        return "partial"
    if score > 0:
        return "weak"
    return "missing"


def _wiki_text(wiki_pages: list[dict[str, Any]]) -> str:
    return " ".join(
        " ".join(
            [
                str(page.get("title", "")),
                str(page.get("summary", "")),
                str(page.get("markdown", "")),
            ]
        )
        for page in wiki_pages
    ).lower()


def _matched_terms(question: str, text: str) -> list[str]:
    lowered_text = text.lower()
    return [term for term in _query_terms(question) if term in lowered_text]


def _query_terms(question: str) -> list[str]:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in question)
    stopwords = {
        "and",
        "are",
        "for",
        "how",
        "ile",
        "icin",
        "için",
        "nedir",
        "the",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
    terms: list[str] = []
    for term in cleaned.split():
        if len(term) < 3 or term in stopwords or term in terms:
            continue
        terms.append(term)
    return terms


def _classify_query_intent(question: str) -> str:
    lowered = question.lower()
    technical_tokens = {
        "api",
        "chunk",
        "code",
        "database",
        "embedding",
        "evaluation",
        "metric",
        "pipeline",
        "retrieval",
        "score",
        "vector",
        "veritaban",
    }
    maintenance_tokens = {
        "eksik",
        "güncelle",
        "guncelle",
        "health",
        "lint",
        "maintenance",
        "update",
        "wiki",
    }
    technical_hits = sum(token in lowered for token in technical_tokens)
    maintenance_hits = sum(token in lowered for token in maintenance_tokens)
    if maintenance_hits > technical_hits and maintenance_hits > 0:
        return "maintenance"
    if technical_hits > 0:
        return "technical"
    return "general"


def _page_quality_score(wiki_pages: list[dict[str, Any]]) -> float:
    if not wiki_pages:
        return 0.0
    scores: list[float] = []
    for page in wiki_pages[:4]:
        markdown = str(page.get("markdown", ""))
        heading_score = min(markdown.count("\n## ") / 4, 1.0)
        length_score = min(len(markdown) / 1600, 1.0)
        source_score = 1.0 if "## Sources" in markdown or "## Source Metadata" in markdown else 0.35
        scores.append((0.38 * heading_score) + (0.42 * length_score) + (0.20 * source_score))
    return sum(scores) / len(scores)


def _topic_connectivity_score(wiki_pages: list[dict[str, Any]]) -> float:
    if not wiki_pages:
        return 0.0
    link_counts = [str(page.get("markdown", "")).count("[[") for page in wiki_pages[:4]]
    return min(sum(link_counts) / max(len(link_counts) * 3, 1), 1.0)


def _source_topic_balance_score(wiki_pages: list[dict[str, Any]]) -> float:
    tags = {tag for page in wiki_pages for tag in page.get("tags", [])}
    slugs = {str(page.get("slug", "")) for page in wiki_pages}
    has_source = "source-summary" in tags or any(slug.startswith("source-") for slug in slugs)
    has_topic = "topic-page" in tags or any(slug.startswith("topic-") for slug in slugs)
    if has_source and has_topic:
        return 1.0
    if has_source or has_topic:
        return 0.55
    return 0.2


def _intent_alignment_score(wiki_pages: list[dict[str, Any]], *, question: str) -> float:
    intent = _classify_query_intent(question)
    tags = {str(tag) for page in wiki_pages for tag in page.get("tags", [])}
    markdown = _wiki_text(wiki_pages)
    if intent == "technical":
        return 1.0 if any(token in markdown for token in ("api", "chunk", "embedding", "retrieval", "vector")) else 0.35
    if intent == "maintenance":
        return 1.0 if "system" in tags or "qa-generated" in tags or "wiki" in markdown else 0.45
    return 0.75


def _suggested_title(question: str) -> str:
    compact = " ".join(question.strip().split())
    if not compact:
        return "New wiki note"
    return compact[:80].rstrip(" ?.")


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4)) if text else 0


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload


def _build_topic_draft(*, title: str, question: str, answer: str, sources: list[dict[str, Any]]) -> str:
    note = _compact_answer_note(answer)
    return (
        f"# {title}\n\n"
        "This topic page was drafted from an agentic wiki gap analysis.\n\n"
        "## What This Answers\n"
        f"{question}\n\n"
        "## Synthesized Notes\n"
        f"{note}\n\n"
        "## Reuse Value\n"
        "This note captures the reusable finding so future questions can rely on wiki memory before raw retrieval.\n\n"
        f"{_source_section(sources)}\n"
    )


def _build_answer_draft(*, title: str, question: str, answer: str, sources: list[dict[str, Any]]) -> str:
    note = _compact_answer_note(answer)
    return (
        f"# {title}\n\n"
        "This page was drafted from an agentic question-answer interaction for future reuse.\n\n"
        "## Question\n"
        f"{question}\n\n"
        "## Reusable Answer Note\n"
        f"{note}\n\n"
        f"{_source_section(sources)}\n"
    )


def _build_update_draft(
    *,
    page: dict[str, Any],
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
) -> str:
    existing = str(page.get("markdown", "")).rstrip()
    note = _compact_answer_note(answer)
    appendix = (
        "\n\n## Agentic Update Proposal\n"
        f"Question: {question}\n\n"
        f"{note}\n\n"
        f"{_source_section(sources)}"
    )
    return f"{existing}{appendix}\n"


def _source_section(sources: list[dict[str, Any]]) -> str:
    filenames = list(dict.fromkeys(str(item.get("filename", "unknown")) for item in sources))
    if not filenames:
        return "## Sources\n- No raw source chunks were used."
    lines = "\n".join(f"- {filename}" for filename in filenames)
    return f"## Sources\n{lines}"


def _compact_answer_note(answer: str, *, max_chars: int = 1100) -> str:
    cleaned = "\n".join(line.rstrip() for line in answer.strip().splitlines())
    if len(cleaned) <= max_chars:
        return cleaned

    paragraphs = [paragraph.strip() for paragraph in cleaned.split("\n\n") if paragraph.strip()]
    kept: list[str] = []
    total = 0
    for paragraph in paragraphs:
        next_total = total + len(paragraph) + 2
        if next_total > max_chars:
            break
        kept.append(paragraph)
        total = next_total

    compact = "\n\n".join(kept).strip()
    if compact:
        return compact + "\n\nFurther detail can be regenerated from the cited sources if needed."
    return cleaned[:max_chars].rstrip() + "...\n\nFurther detail can be regenerated from the cited sources if needed."
