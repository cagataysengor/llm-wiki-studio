from fastapi import APIRouter
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
                "url": settings.default_local_url,
                "model": settings.default_local_model,
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
def get_local_status() -> dict[str, object]:
    settings = get_settings()
    models_url = settings.default_local_url.rstrip("/")
    if models_url.endswith("/chat/completions"):
        models_url = models_url.removesuffix("/chat/completions") + "/models"
    else:
        models_url = models_url + "/models"

    try:
        response = requests.get(models_url, timeout=(3, 5))
        response.raise_for_status()
        payload = response.json()
        models = payload.get("data") or payload.get("models") or []
        model_names: list[str] = []
        for item in models[:5]:
            if isinstance(item, dict):
                name = item.get("id") or item.get("name") or item.get("model")
                if isinstance(name, str) and name.strip():
                    model_names.append(name.strip())
        return {
            "reachable": True,
            "url": models_url,
            "model_count": len(models) if isinstance(models, list) else len(model_names),
            "models": model_names,
        }
    except Exception as exc:
        return {
            "reachable": False,
            "url": models_url,
            "model_count": 0,
            "models": [],
            "detail": str(exc),
        }
