from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LLM Wiki API"
    database_url: str = "sqlite:///./data/app.db"
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data")
    raw_dir_name: str = "raw"
    wiki_dir_name: str = "wiki"
    index_dir_name: str = "index"

    default_provider: str = "Local"
    providers: list[str] = ["Local", "OpenAI", "Gemini", "Claude"]
    default_embed_model: str = "intfloat/multilingual-e5-base"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    claude_api_key: str = ""
    embedding_provider: str = "Local"
    embedding_api_key: str = ""
    embedding_mode: str = "auto"
    embedding_url: str = "http://127.0.0.1:8080/v1/embeddings"
    default_local_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    default_local_model: str = "local-model"
    default_openai_url: str = "https://api.openai.com/v1/chat/completions"
    default_openai_model: str = "gpt-4.1-mini"
    default_gemini_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    default_gemini_model: str = "gemini-2.0-flash"
    default_claude_url: str = "https://api.anthropic.com/v1/messages"
    default_claude_model: str = "claude-3-5-sonnet-latest"

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / self.raw_dir_name

    @property
    def wiki_dir(self) -> Path:
        return self.data_dir / self.wiki_dir_name

    @property
    def index_dir(self) -> Path:
        return self.data_dir / self.index_dir_name

    def get_provider_api_key(self, provider: str) -> str:
        mapping = {
            "Local": "",
            "OpenAI": self.openai_api_key,
            "Gemini": self.gemini_api_key,
            "Claude": self.claude_api_key,
        }
        return mapping.get(provider, "")

    def provider_has_server_key(self, provider: str) -> bool:
        if provider == "Local":
            return True
        return bool(self.get_provider_api_key(provider))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    return settings
