import os
import shutil
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


TEST_ROOT = Path(tempfile.gettempdir()) / "llm_wiki_backend_tests"
DATA_DIR = TEST_ROOT / "data"
DB_PATH = TEST_ROOT / "test.db"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["APP_NAME"] = "LLM Wiki API Test"
os.environ["EMBEDDING_MODE"] = "deterministic"
os.environ["DATA_DIR"] = str(DATA_DIR)

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
settings = get_settings()

from app.main import app  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def prepare_runtime() -> None:
    engine.dispose()
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    init_db()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
