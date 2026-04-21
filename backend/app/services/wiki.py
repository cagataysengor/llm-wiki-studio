from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.repositories import upsert_wiki_page
from app.services.text import safe_slug


settings = get_settings()


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
    return {
        "slug": record.slug,
        "title": record.title,
        "filepath": record.filepath,
        "action": "created",
    }


def _make_unique_slug(base_slug: str) -> str:
    candidate = base_slug
    counter = 2
    while (settings.wiki_dir / f"{candidate}.md").exists():
        candidate = f"{base_slug}-{counter}"
        counter += 1
    return candidate


def _build_qa_page(*, title: str, question: str, answer: str, source_files: list[str]) -> str:
    sources_md = "\n".join(f"- {item}" for item in source_files) if source_files else "- Unknown source"
    return (
        f"# {title}\n\n"
        "## Overview\n"
        "This page was created from a question-answer interaction and saved for reuse.\n\n"
        f"## Question\n{question}\n\n"
        f"## Answer\n{answer}\n\n"
        f"## Sources\n{sources_md}\n\n"
        "## Related Topics\n"
        "- [[question-answer-derived-note]]\n"
    )


def _build_qa_appendix(*, question: str, answer: str, source_files: list[str]) -> str:
    sources_md = "\n".join(f"- {item}" for item in source_files) if source_files else "- Unknown source"
    return (
        "\n\n---\n\n"
        "## Added from QA\n\n"
        f"### Question\n{question}\n\n"
        f"### Answer\n{answer}\n\n"
        f"### Sources\n{sources_md}\n"
    )
