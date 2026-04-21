import hashlib
import math
import re

import requests

from app.core.config import get_settings
from app.models.document_chunk import EMBEDDING_DIMENSIONS


TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
settings = get_settings()


def embed_text(text: str, *, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    vectors = embed_texts([text], dimensions=dimensions)
    return vectors[0] if vectors else [0.0] * dimensions


def embed_texts(texts: list[str], *, dimensions: int = EMBEDDING_DIMENSIONS) -> list[list[float]]:
    if not texts:
        return []

    mode = settings.embedding_mode.lower().strip()
    if mode in {"remote", "auto"}:
        remote_vectors = _try_remote_embeddings(texts=texts, dimensions=dimensions)
        if remote_vectors is not None:
            return remote_vectors
        if mode == "remote":
            raise RuntimeError("Embedding provider is configured for remote-only mode, but the remote call failed.")

    return [_embed_text_deterministic(text, dimensions=dimensions) for text in texts]


def _embed_text_deterministic(text: str, *, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    tokens = TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = -1.0 if digest[4] % 2 else 1.0
        weight = 1.0 + (digest[5] / 255.0)
        vector[bucket] += sign * weight

    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0:
        return vector
    return [item / norm for item in vector]


def _try_remote_embeddings(texts: list[str], *, dimensions: int) -> list[list[float]] | None:
    if settings.embedding_provider not in {"Local", "OpenAI"}:
        return None
    if not settings.embedding_url.strip():
        return None

    headers = {"Content-Type": "application/json"}
    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"

    payload = {
        "model": settings.default_embed_model,
        "input": texts,
    }

    try:
        response = requests.post(settings.embedding_url, headers=headers, json=payload, timeout=(10, 120))
        response.raise_for_status()
        body = response.json()
        data = body.get("data", [])
        if len(data) != len(texts):
            return None

        vectors = [item.get("embedding", []) for item in data]
        if not all(isinstance(vector, list) and vector for vector in vectors):
            return None

        return [_normalize_or_resize(vector, dimensions=dimensions) for vector in vectors]
    except Exception:
        return None


def _normalize_or_resize(vector: list[float], *, dimensions: int) -> list[float]:
    coerced = [float(item) for item in vector[:dimensions]]
    if len(coerced) < dimensions:
        coerced.extend([0.0] * (dimensions - len(coerced)))
    norm = math.sqrt(sum(item * item for item in coerced))
    if norm == 0:
        return coerced
    return [item / norm for item in coerced]
