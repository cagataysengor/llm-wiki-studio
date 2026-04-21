from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.api.routes.health import healthcheck
from app.api.routes.settings import get_public_settings
from app.db.session import SessionLocal
from app.services.ingest import ingest_upload
from app.services.qa import answer_question, save_answer_to_wiki
from app.services.reindex import reindex_documents
from app.services.retrieval import retrieve_wiki_pages
from app.services.repositories import get_wiki_page_by_slug, list_documents
from app.services.wiki import lint_wiki


def test_healthcheck() -> None:
    payload = healthcheck()
    assert payload["status"] == "ok"
    assert "timestamp" in payload


def test_public_settings_exposes_embedding_config() -> None:
    payload = get_public_settings()
    assert payload["app_name"] == "LLM Wiki API Test"
    assert payload["embedding_mode"] == "deterministic"
    assert "embedding_url" in payload


def test_ingest_ask_and_reindex_flow() -> None:
    db = SessionLocal()
    try:
        upload = UploadFile(
            filename="anomaly.txt",
            file=BytesIO(
                (
                    "Anomaly detection identifies rare patterns.\n\n"
                    "It is used in fraud detection, observability, and quality control."
                ).encode("utf-8")
            ),
        )

        ingest_payload = ingest_upload(db, upload)
        assert ingest_payload["filename"] == "anomaly.txt"
        assert ingest_payload["chunk_count"] >= 1
        assert ingest_payload["wiki_page_slug"] == "source-anomaly"
        assert "topic-anomaly-detection" in ingest_payload["topic_page_slugs"]

        documents = list_documents(db)
        assert any(item.filename == "anomaly.txt" for item in documents)
        wiki_page = get_wiki_page_by_slug(db, ingest_payload["wiki_page_slug"])
        assert wiki_page is not None
        assert "Source Summary: anomaly.txt" == wiki_page["title"]
        assert "## Key Points" in wiki_page["markdown"]
        assert "[[topic-anomaly-detection]]" in wiki_page["markdown"]
        topic_page = get_wiki_page_by_slug(db, "topic-anomaly-detection")
        assert topic_page is not None
        assert "anomaly.txt" in topic_page["markdown"]
        index_page = get_wiki_page_by_slug(db, "index")
        assert index_page is not None
        assert "[[source-anomaly]]" in index_page["markdown"]
        assert "[[topic-anomaly-detection]]" in index_page["markdown"]
        log_path = Path(index_page["filepath"]).with_name("log.md")
        assert log_path.exists()
        assert "ingest | anomaly.txt" in log_path.read_text(encoding="utf-8")
        wiki_hits = retrieve_wiki_pages(db, "What is anomaly detection used for?", top_k=3)
        assert len(wiki_hits) >= 1
        assert wiki_hits[0]["slug"] in {"topic-anomaly-detection", "source-anomaly"}

        qa_payload = answer_question(
            db=db,
            question="What is anomaly detection used for?",
            provider="Disabled",
            model_name="test-model",
            api_key="",
            llm_url="http://unused.local",
            embed_model="test-embed-model",
            top_k=3,
        )
        assert qa_payload["question"] == "What is anomaly detection used for?"
        assert len(qa_payload["sources"]) >= 1
        assert "Provider `Disabled` adapter" in qa_payload["answer"]
        assert "ask | What is anomaly detection used for?" in log_path.read_text(encoding="utf-8")

        save_payload = save_answer_to_wiki(
            db=db,
            title="Anomaly Detection Note",
            question=str(qa_payload["question"]),
            answer=str(qa_payload["answer"]),
            source_files=["anomaly.txt"],
            merge_if_similar=True,
        )
        assert save_payload["action"] == "created"
        assert Path(save_payload["filepath"]).exists()
        refreshed_index_page = get_wiki_page_by_slug(db, "index")
        assert refreshed_index_page is not None
        assert "[[anomaly-detection-note]]" in refreshed_index_page["markdown"]
        assert "save | Anomaly Detection Note" in log_path.read_text(encoding="utf-8")
        lint_payload = lint_wiki(db)
        assert lint_payload["checked_pages"] >= 3
        assert any(item["category"] == "thin-topic" for item in lint_payload["findings"])
        assert "lint | wiki health check" in log_path.read_text(encoding="utf-8")

        reindex_payload = reindex_documents(db=db, document_id=ingest_payload["document_id"])
        assert reindex_payload["reindexed_documents"] == 1
        assert reindex_payload["reindexed_chunks"] >= 1
    finally:
        db.close()
