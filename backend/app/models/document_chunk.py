from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


EMBEDDING_DIMENSIONS = 64
embedding_column_type = JSON().with_variant(VECTOR(EMBEDDING_DIMENSIONS), "postgresql")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(embedding_column_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
