from fastapi import APIRouter, Query
import requests

from app.core.config import get_settings


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public")
def get_public_settings() -> dict[str, object]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "default_embed_model": settings.default_embed_model,
        "embedding_provider": settings.embedding_provider,
        "embedding_mode": settings.embedding_mode,
        "embedding_url": settings.embedding_url,
        "default_provider": settings.default_provider,
        "providers": settings.providers,
        "provider_server_configured": {
            provider: settings.provider_has_server_key(provider)
            for provider in settings.providers
        },
        "provider_runtime_support": {
            "Local": True,
            "OpenAI": True,
            "Gemini": True,
            "Claude": True,
        },
        "provider_defaults": {
            "Local": {
                "url": settings.local_chat_url,
                "model": settings.local_model_name,
            },
            "OpenAI": {
                "url": settings.default_openai_url,
                "model": settings.default_openai_model,
            },
            "Gemini": {
                "url": settings.default_gemini_url,
                "model": settings.default_gemini_model,
            },
            "Claude": {
                "url": settings.default_claude_url,
                "model": settings.default_claude_model,
            },
        },
        "data_dir": str(settings.data_dir),
    }


@router.get("/local-status")
def get_local_status(url: str | None = Query(default=None), model: str | None = Query(default=None)) -> dict[str, object]:
    settings = get_settings()
    models_url = (url or settings.local_chat_url).rstrip("/")
    if models_url.endswith("/chat/completions"):
        models_url = models_url.removesuffix("/chat/completions") + "/models"
    else:
        models_url = models_url + "/models"

    try:
        headers = {"Authorization": f"Bearer {settings.ollama_api_key}"} if settings.ollama_api_key else None
        response = requests.get(models_url, headers=headers, timeout=(3, 5))
        response.raise_for_status()
        payload = response.json()
        models = payload.get("data") or payload.get("models") or []
        model_names: list[str] = []
        for item in models[:5]:
            if isinstance(item, dict):
                name = item.get("id") or item.get("name") or item.get("model")
                if isinstance(name, str) and name.strip():
                    model_names.append(name.strip())
        all_model_names: list[str] = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("id") or item.get("name") or item.get("model")
                if isinstance(name, str) and name.strip():
                    all_model_names.append(name.strip())
        selected_model = (model or settings.local_model_name).strip()
        return {
            "reachable": True,
            "auth_ok": True,
            "url": models_url,
            "model_count": len(models) if isinstance(models, list) else len(model_names),
            "models": model_names,
            "selected_model": selected_model,
            "model_available": selected_model in all_model_names if selected_model else None,
            "diagnostics": [
                "Connection ok.",
                "Authentication ok.",
                "Selected model found."
                if selected_model in all_model_names
                else "Selected model was not listed by the provider; it may still work if the provider supports aliases.",
            ],
        }
    except Exception as exc:
        detail = str(exc)
        auth_ok = "401" not in detail and "unauthorized" not in detail.lower()
        return {
            "reachable": False,
            "auth_ok": auth_ok,
            "url": models_url,
            "model_count": 0,
            "models": [],
            "selected_model": (model or settings.local_model_name).strip(),
            "model_available": False,
            "detail": detail,
            "diagnostics": [
                "Connection or provider check failed.",
                "Authentication failed." if not auth_ok else "Authentication was not rejected explicitly.",
                detail[:240],
            ],
        }
