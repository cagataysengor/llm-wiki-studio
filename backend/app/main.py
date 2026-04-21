from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, health, qa, settings, wiki
from app.core.config import get_settings
from app.db.session import init_db


settings_obj = get_settings()

app = FastAPI(
    title=settings_obj.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_obj.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(wiki.router, prefix="/api")
app.include_router(qa.router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    init_db()

