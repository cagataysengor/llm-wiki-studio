from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.api.routes.health import healthcheck
from app.api.routes.settings import get_public_settings
from app.db.session import SessionLocal
from app.services.ingest import ingest_upload
from app.services.qa import answer_question, save_answer_to_wiki
from app.services.reindex import reindex_documents
from app.services.repositories import list_documents


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

        documents = list_documents(db)
        assert any(item.filename == "anomaly.txt" for item in documents)

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

        reindex_payload = reindex_documents(db=db, document_id=ingest_payload["document_id"])
        assert reindex_payload["reindexed_documents"] == 1
        assert reindex_payload["reindexed_chunks"] >= 1
    finally:
        db.close()
