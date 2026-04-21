from datetime import datetime, timezone
from pathlib import Path
import re
from collections import Counter

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.repositories import delete_wiki_page_by_slug, get_wiki_page_by_slug, list_wiki_pages, upsert_wiki_page
from app.services.text import safe_slug


settings = get_settings()
TOPIC_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "among",
    "an",
    "and",
    "are",
    "because",
    "between",
    "but",
    "code",
    "data",
    "document",
    "documents",
    "file",
    "from",
    "have",
    "identifies",
    "into",
    "its",
    "it",
    "more",
    "patterns",
    "source",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "this",
    "those",
    "overview",
    "notes",
    "summary",
    "page",
    "pages",
    "overview",
    "used",
    "uses",
    "using",
    "what",
    "which",
    "with",
}


def create_manual_wiki_page(db: Session, *, title: str, markdown: str) -> dict[str, object]:
    slug = _make_unique_slug(safe_slug(title))
    path = settings.wiki_dir / f"{slug}.md"
    path.write_text(markdown, encoding="utf-8")
    record = upsert_wiki_page(
        db,
        slug=slug,
        title=title.strip(),
        filepath=str(path),
        summary="Manual wiki page",
        tags=[],
        source_doc_ids=[],
    )
    rebuild_wiki_index(db)
    append_wiki_log(
        event_type="wiki",
        title=title.strip(),
        details={"action": "manual-create"},
    )
    return {
        "slug": record.slug,
        "title": record.title,
        "filepath": record.filepath,
        "summary": record.summary or "",
        "tags": [],
        "source_doc_ids": [],
        "updated_at": record.updated_at,
        "markdown": markdown,
    }


def lint_wiki(db: Session) -> dict[str, object]:
    pages = [
        page
        for page in list_wiki_pages(db)
        if str(page.get("slug", "")) not in {"index", "log"}
    ]
    slug_set = {str(page["slug"]) for page in pages}
    inbound_links = {slug: 0 for slug in slug_set}

    for page in pages:
        markdown = str(page.get("markdown", ""))
        for linked_slug in re.findall(r"\[\[([^\]]+)\]\]", markdown):
            if linked_slug in inbound_links:
                inbound_links[linked_slug] += 1

    findings: list[dict[str, object]] = []
    for page in pages:
        slug = str(page["slug"])
        title = str(page.get("title", ""))
        tags = {str(item) for item in page.get("tags", [])}
        source_doc_ids = list(page.get("source_doc_ids", []))
        markdown = str(page.get("markdown", ""))

        if inbound_links.get(slug, 0) == 0 and "source-summary" not in tags:
            findings.append(
                {
                    "severity": "warning",
                    "category": "orphan-page",
                    "page_slug": slug,
                    "page_title": title,
                    "message": "This page is not linked from other wiki pages yet, so it may be harder to discover.",
                }
            )

        if "topic-page" in tags and len(source_doc_ids) <= 1:
            findings.append(
                {
                    "severity": "info",
                    "category": "thin-topic",
                    "page_slug": slug,
                    "page_title": title,
                    "message": "This topic currently has limited source coverage and is supported by only one source.",
                }
            )

        if "source-summary" in tags and "## Related Topics\n- No related topics identified." in markdown:
            findings.append(
                {
                    "severity": "info",
                    "category": "missing-topics",
                    "page_slug": slug,
                    "page_title": title,
                    "message": "This source summary does not have any related topic pages yet.",
                }
            )

        if not source_doc_ids and "qa-generated" not in tags and "system" not in tags:
            findings.append(
                {
                    "severity": "info",
                    "category": "missing-source-link",
                    "page_slug": slug,
                    "page_title": title,
                    "message": "This page is not linked back to a source document yet.",
                }
            )

    if not findings:
        findings.append(
            {
                "severity": "info",
                "category": "healthy",
                "page_slug": None,
                "page_title": None,
                "message": "No obvious wiki maintenance issues were found.",
            }
        )

    append_wiki_log(
        event_type="lint",
        title="wiki health check",
        details={
            "checked_pages": str(len(pages)),
            "finding_count": str(len(findings)),
        },
    )
    return {
        "checked_pages": len(pages),
        "findings": findings,
    }


def delete_wiki_page(db: Session, *, slug: str) -> dict[str, object]:
    if slug in {"index", "log"}:
        raise RuntimeError("System wiki pages cannot be deleted.")

    deleted = delete_wiki_page_by_slug(db, slug)
    if deleted is None:
        raise RuntimeError("Wiki page not found.")

    filepath = str(deleted.get("filepath", ""))
    if filepath:
        path = Path(filepath)
        if path.exists():
            path.unlink()

    rebuild_wiki_index(db)
    append_wiki_log(
        event_type="wiki",
        title=str(deleted.get("title", slug)),
        details={
            "action": "delete",
            "slug": slug,
        },
    )
    return {
        "slug": str(deleted.get("slug", slug)),
        "title": str(deleted.get("title", slug)),
        "action": "deleted",
    }


def create_or_merge_qa_wiki_page(
    db: Session,
    *,
    title: str,
    question: str,
    answer: str,
    source_files: list[str],
    merge_target: dict[str, object] | None = None,
) -> dict[str, object]:
    if merge_target is not None:
        markdown = str(merge_target.get("markdown", "")).rstrip() + _build_qa_appendix(
            question=question,
            answer=answer,
            source_files=source_files,
        )
        slug = str(merge_target["slug"])
        path = settings.wiki_dir / f"{slug}.md"
        path.write_text(markdown, encoding="utf-8")
        record = upsert_wiki_page(
            db,
            slug=slug,
            title=str(merge_target["title"]),
            filepath=str(path),
            summary=str(merge_target.get("summary", "") or ""),
            tags=list(dict.fromkeys([*list(merge_target.get("tags", [])), "qa-extended"])),
            source_doc_ids=list(merge_target.get("source_doc_ids", [])),
        )
        rebuild_wiki_index(db)
        append_wiki_log(
            event_type="save",
            title=str(merge_target["title"]),
            details={
                "action": "merged",
                "question": question,
                "sources": ", ".join(source_files) if source_files else "unknown",
            },
        )
        return {
            "slug": record.slug,
            "title": record.title,
            "filepath": record.filepath,
            "action": "merged",
        }

    slug = _make_unique_slug(safe_slug(title))
    path = settings.wiki_dir / f"{slug}.md"
    markdown = _build_qa_page(
        title=title,
        question=question,
        answer=answer,
        source_files=source_files,
    )
    path.write_text(markdown, encoding="utf-8")
    record = upsert_wiki_page(
        db,
        slug=slug,
        title=title.strip(),
        filepath=str(path),
        summary=f"Saved from QA: {question[:120]}",
        tags=["qa-generated"],
        source_doc_ids=[],
    )
    rebuild_wiki_index(db)
    append_wiki_log(
        event_type="save",
        title=title.strip(),
        details={
            "action": "created",
            "question": question,
            "sources": ", ".join(source_files) if source_files else "unknown",
        },
    )
    return {
        "slug": record.slug,
        "title": record.title,
        "filepath": record.filepath,
        "action": "created",
    }


def create_or_update_source_summary_page(
    db: Session,
    *,
    doc_id: str,
    filename: str,
    filetype: str,
    text: str,
    chunk_count: int,
) -> dict[str, object]:
    title = f"Source Summary: {filename}"
    slug = f"source-{safe_slug(Path(filename).stem)}"
    path = settings.wiki_dir / f"{slug}.md"
    summary = _build_source_summary(text)
    topic_pages = create_or_update_topic_pages(
        db,
        doc_id=doc_id,
        filename=filename,
        text=text,
    )
    markdown = _build_source_summary_page(
        title=title,
        filename=filename,
        filetype=filetype or "unknown",
        chunk_count=chunk_count,
        summary=summary,
        key_points=_extract_key_points(text),
        related_topics=[item["slug"] for item in topic_pages],
    )
    path.write_text(markdown, encoding="utf-8")
    record = upsert_wiki_page(
        db,
        slug=slug,
        title=title,
        filepath=str(path),
        summary=summary,
        tags=["source-summary", filetype or "unknown"],
        source_doc_ids=[doc_id],
    )
    rebuild_wiki_index(db)
    append_wiki_log(
        event_type="ingest",
        title=filename,
        details={
            "wiki_page": record.slug,
            "filetype": filetype or "unknown",
            "chunks": str(chunk_count),
        },
    )
    return {
        "slug": record.slug,
        "title": record.title,
        "filepath": record.filepath,
        "summary": record.summary or "",
        "topic_pages": topic_pages,
    }


def create_or_update_topic_pages(
    db: Session,
    *,
    doc_id: str,
    filename: str,
    text: str,
    limit: int = 3,
) -> list[dict[str, object]]:
    topics = _extract_topic_candidates(text, limit=limit)
    created_pages: list[dict[str, object]] = []
    for topic in topics:
        title = f"Topic: {topic}"
        slug = f"topic-{safe_slug(topic)}"
        path = settings.wiki_dir / f"{slug}.md"
        existing = get_wiki_page_by_slug(db, slug)
        source_doc_ids = list(existing.get("source_doc_ids", [])) if existing else []
        if doc_id not in source_doc_ids:
            source_doc_ids.append(doc_id)
        related_sources = _extract_related_sources(existing_markdown=existing.get("markdown", "") if existing else "", filename=filename)
        if filename not in related_sources:
            related_sources.append(filename)
        existing_points = _extract_existing_topic_points(existing.get("markdown", "") if existing else "")
        merged_points = _merge_topic_points(
            topic=topic,
            existing_points=existing_points,
            new_points=_extract_topic_points(text, topic),
        )
        markdown = _build_topic_page(
            title=title,
            topic=topic,
            related_sources=related_sources,
            related_points=merged_points,
        )
        path.write_text(markdown, encoding="utf-8")
        record = upsert_wiki_page(
            db,
            slug=slug,
            title=title,
            filepath=str(path),
            summary=f"Aggregated notes and source references for {topic}.",
            tags=["topic-page"],
            source_doc_ids=source_doc_ids,
        )
        created_pages.append(
            {
                "slug": record.slug,
                "title": record.title,
                "filepath": record.filepath,
            }
        )
    return created_pages


def rebuild_wiki_index(db: Session) -> None:
    pages = [
        page
        for page in list_wiki_pages(db)
        if str(page.get("slug", "")) not in {"index", "log"}
    ]
    pages.sort(key=lambda item: str(item.get("title", "")).lower())
    markdown = _build_index_markdown(pages)
    path = settings.wiki_dir / "index.md"
    path.write_text(markdown, encoding="utf-8")
    upsert_wiki_page(
        db,
        slug="index",
        title="Index",
        filepath=str(path),
        summary="Catalog of wiki pages and generated knowledge artifacts.",
        tags=["system", "index"],
        source_doc_ids=[],
    )


def append_wiki_log(*, event_type: str, title: str, details: dict[str, str] | None = None) -> None:
    path = settings.wiki_dir / "log.md"
    if path.exists():
        existing = path.read_text(encoding="utf-8").rstrip()
    else:
        existing = "# Activity Log\n\nChronological record of wiki updates and knowledge operations."

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"## [{timestamp}] {event_type} | {title}"]
    for key, value in (details or {}).items():
        lines.append(f"- {key}: {value}")
    entry = "\n".join(lines)
    path.write_text(f"{existing}\n\n{entry}\n", encoding="utf-8")


def _make_unique_slug(base_slug: str) -> str:
    candidate = base_slug
    counter = 2
    while (settings.wiki_dir / f"{candidate}.md").exists():
        candidate = f"{base_slug}-{counter}"
        counter += 1
    return candidate


def _build_qa_page(*, title: str, question: str, answer: str, source_files: list[str]) -> str:
    clean_answer = _strip_embedded_sources(answer)
    sources_md = "\n".join(f"- {item}" for item in source_files) if source_files else "- Unknown source"
    return (
        f"# {title}\n\n"
        "## Overview\n"
        "This page was created from a question-answer interaction and saved for reuse.\n\n"
        f"## Question\n{question}\n\n"
        f"## Answer\n{clean_answer}\n\n"
        f"## Sources\n{sources_md}\n"
    )


def _build_qa_appendix(*, question: str, answer: str, source_files: list[str]) -> str:
    clean_answer = _strip_embedded_sources(answer)
    sources_md = "\n".join(f"- {item}" for item in source_files) if source_files else "- Unknown source"
    return (
        "\n\n---\n\n"
        "## Added from QA\n\n"
        f"### Question\n{question}\n\n"
        f"### Answer\n{clean_answer}\n\n"
        f"### Sources\n{sources_md}\n"
    )


def _build_source_summary_page(
    *,
    title: str,
    filename: str,
    filetype: str,
    chunk_count: int,
    summary: str,
    key_points: list[str],
    related_topics: list[str],
) -> str:
    points_md = "\n".join(f"- {item}" for item in key_points) if key_points else "- No key points extracted."
    topics_md = "\n".join(f"- [[{item}]]" for item in related_topics) if related_topics else "- No related topics identified."
    return (
        f"# {title}\n\n"
        "## Overview\n"
        f"{summary}\n\n"
        "## Source Metadata\n"
        f"- Filename: `{filename}`\n"
        f"- File type: `{filetype}`\n"
        f"- Indexed chunks: `{chunk_count}`\n\n"
        "## Key Points\n"
        f"{points_md}\n\n"
        "## Related Topics\n"
        f"{topics_md}\n\n"
        "## Notes\n"
        "This page is generated automatically during source ingestion and can be updated when the same source is reprocessed.\n"
    )


def _build_source_summary(text: str) -> str:
    clean = " ".join(_content_paragraphs(text))
    if not clean:
        return "No summary available."
    if len(clean) <= 280:
        return clean
    truncated = clean[:277].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def _extract_key_points(text: str, *, limit: int = 4) -> list[str]:
    paragraphs = _content_paragraphs(text)
    points: list[str] = []
    for paragraph in paragraphs:
        candidate = " ".join(paragraph.split())
        if len(candidate) < 40:
            continue
        if len(candidate) > 220:
            candidate = candidate[:217].rsplit(" ", 1)[0].strip() + "..."
        points.append(candidate)
        if len(points) >= limit:
            break
    return points


def _build_index_markdown(pages: list[dict[str, object]]) -> str:
    if not pages:
        body = "- No wiki pages available yet."
    else:
        body = "\n".join(
            f"- [[{page['slug']}]] - {page.get('summary') or 'No summary available.'}"
            for page in pages
        )
    return (
        "# Index\n\n"
        "This file lists the current wiki pages and generated knowledge artifacts.\n\n"
        "## Pages\n"
        f"{body}\n"
    )


def _build_topic_page(*, title: str, topic: str, related_sources: list[str], related_points: list[str]) -> str:
    sources_md = "\n".join(f"- {item}" for item in related_sources) if related_sources else "- No related sources recorded."
    points_md = "\n".join(f"- {item}" for item in related_points) if related_points else "- No detailed points recorded."
    return (
        f"# {title}\n\n"
        "## Overview\n"
        f"This page tracks recurring knowledge related to {topic} across ingested sources.\n\n"
        "## Related Sources\n"
        f"{sources_md}\n\n"
        "## Notes From Sources\n"
        f"{points_md}\n"
    )


def _extract_topic_candidates(text: str, *, limit: int = 3) -> list[str]:
    paragraphs = _content_paragraphs(text)
    words = re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ]{4,}", " ".join(paragraphs).lower())
    bigrams: list[str] = []
    for left, right in zip(words, words[1:]):
        if left in TOPIC_STOPWORDS or right in TOPIC_STOPWORDS:
            continue
        bigrams.append(f"{left} {right}")

    counts = Counter(bigrams)
    first_positions: dict[str, int] = {}
    for index, phrase in enumerate(bigrams):
        first_positions.setdefault(phrase, index)

    ranked = sorted(
        counts.items(),
        key=lambda item: (-item[1], first_positions.get(item[0], 0)),
    )
    candidates = [phrase.title() for phrase, count in ranked if count >= 2][:limit]
    if candidates:
        return candidates

    fallback: list[str] = []
    for phrase, _count in ranked:
        titled = phrase.title()
        if titled not in fallback:
            fallback.append(titled)
        if len(fallback) >= limit:
            break
    return fallback


def _extract_topic_points(text: str, topic: str, *, limit: int = 3) -> list[str]:
    topic_phrase = topic.lower()
    topic_terms = [term.lower() for term in topic.split()]
    sentences = _content_sentences(text)
    ranked: list[tuple[int, str]] = []

    for sentence in sentences:
        lowered = sentence.lower()
        phrase_hits = lowered.count(topic_phrase)
        term_hits = sum(term in lowered for term in topic_terms)
        if phrase_hits == 0 and term_hits == 0:
            continue

        # Exact phrase matches should dominate, with term overlap as a fallback.
        score = (phrase_hits * 10) + (term_hits * 3)
        ranked.append((score, sentence))

    ranked.sort(key=lambda item: (-item[0], len(item[1])))
    points: list[str] = []
    for _score, sentence in ranked:
        candidate = " ".join(sentence.split())
        if len(candidate) > 220:
            candidate = candidate[:217].rsplit(" ", 1)[0].strip() + "..."
        if candidate not in points:
            points.append(candidate)
        if len(points) >= limit:
            break
    return points


def _extract_related_sources(*, existing_markdown: str, filename: str) -> list[str]:
    section_match = re.search(
        r"## Related Sources\n(?P<body>.*?)(?:\n## |\Z)",
        existing_markdown,
        flags=re.DOTALL,
    )
    body = section_match.group("body") if section_match else ""
    matches = re.findall(r"^- ([^\n]+)$", body, flags=re.MULTILINE)
    sources: list[str] = []
    for match in matches:
        cleaned = match.strip()
        if not cleaned:
            continue
        if not re.search(r"\.(txt|md|csv|json|py|html|pdf|docx)$", cleaned, flags=re.IGNORECASE):
            continue
        if cleaned not in sources:
            sources.append(cleaned)
    if filename not in sources:
        sources.append(filename)
    return sources


def _content_paragraphs(text: str) -> list[str]:
    return [
        part.strip()
        for part in text.split("\n\n")
        if part.strip() and not part.strip().startswith("#")
    ]


def _content_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph in _content_paragraphs(text):
        parts = re.split(r"(?<=[.!?])\s+", paragraph)
        for part in parts:
            cleaned = part.strip()
            if len(cleaned) >= 30:
                sentences.append(cleaned)
    return sentences


def _strip_embedded_sources(answer: str) -> str:
    cleaned = answer.strip()
    cleaned = re.split(r"\n\s*Sources:\s*", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return cleaned


def _extract_existing_topic_points(markdown: str) -> list[str]:
    section_match = re.search(
        r"## Notes From Sources\n(?P<body>.*?)(?:\n## |\Z)",
        markdown,
        flags=re.DOTALL,
    )
    body = section_match.group("body") if section_match else ""
    return [item.strip() for item in re.findall(r"^- ([^\n]+)$", body, flags=re.MULTILINE) if item.strip()]


def _merge_topic_points(*, topic: str, existing_points: list[str], new_points: list[str], limit: int = 4) -> list[str]:
    combined: list[str] = []
    for item in [*existing_points, *new_points]:
        cleaned = item.strip()
        if cleaned and cleaned not in combined:
            combined.append(cleaned)

    ranked = sorted(
        combined,
        key=lambda item: (-_score_topic_text(item, topic), len(item)),
    )
    return ranked[:limit]


def _score_topic_text(text: str, topic: str) -> int:
    lowered = text.lower()
    topic_phrase = topic.lower()
    topic_terms = [term.lower() for term in topic.split()]
    phrase_hits = lowered.count(topic_phrase)
    term_hits = sum(term in lowered for term in topic_terms)
    return (phrase_hits * 10) + (term_hits * 3)
