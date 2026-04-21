from collections.abc import Generator

from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models.document_chunk import DocumentChunk
from app.models.document import Document
from app.models.wiki_page import WikiPage


settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


if settings.database_url.startswith("postgresql"):
    @event.listens_for(engine, "connect")
    def register_pgvector(dbapi_connection, connection_record) -> None:
        del connection_record
        register_vector(dbapi_connection)


def init_db() -> None:
    if settings.database_url.startswith("postgresql"):
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
