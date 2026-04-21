from typing import Any

import requests


def answer_with_provider(
    *,
    provider: str,
    llm_url: str,
    model_name: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 800,
) -> str:
    if provider in {"Local", "OpenAI"}:
        return _call_openai_style_chat(
            provider=provider,
            llm_url=llm_url,
            model_name=model_name,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            prefer_completions=provider == "Local",
        )
    if provider == "Gemini":
        return _call_gemini_chat(
            base_url=llm_url,
            model_name=model_name,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
    if provider == "Claude":
        return _call_claude_chat(
            llm_url=llm_url,
            model_name=model_name,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
    return _build_fallback_answer(system_prompt=system_prompt, user_prompt=user_prompt, provider=provider)


def _call_openai_style_chat(
    *,
    provider: str,
    llm_url: str,
    model_name: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    prefer_completions: bool = False,
) -> str:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request_timeout = (10, 180) if prefer_completions else (10, 60)

    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    completion_url = _derive_completions_url(llm_url)
    if not prefer_completions:
        response = requests.post(llm_url, headers=headers, json=payload, timeout=request_timeout)
        if response.ok:
            data = response.json()
            text = _extract_openai_style_text(data)
            if text:
                return text

    response: requests.Response | None = None
    if completion_url and completion_url != llm_url:
        fallback_payload = {
            "model": model_name,
            "prompt": _build_completion_prompt(system_prompt=system_prompt, user_prompt=user_prompt),
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stop": [
                "\nQuestion:",
                "\nContext:",
                "\nUser request:",
                "\nSystem instruction:",
                "\nAnswer rules:",
            ],
        }
        completion_response = requests.post(
            completion_url,
            headers=headers,
            json=fallback_payload,
            timeout=request_timeout,
        )
        _raise_for_status_with_body(completion_response)
        completion_data = completion_response.json()
        completion_text = _extract_openai_style_text(completion_data, provider=provider)
        if completion_text:
            return completion_text

    if response is not None:
        _raise_for_status_with_body(response)
        data = response.json()
        text = _extract_openai_style_text(data, provider=provider)
        if text:
            return text
        raise RuntimeError(f"OpenAI-style endpoint returned no text: {data}")

    raise RuntimeError("OpenAI-style endpoint returned no usable response.")


def _call_gemini_chat(
    *,
    base_url: str,
    model_name: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    if not api_key:
        raise RuntimeError("Gemini is selected but GEMINI_API_KEY is not configured on the server.")

    url = f"{base_url.rstrip('/')}/{model_name}:generateContent?key={api_key}"
    payload: dict[str, Any] = {
        "system_instruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_tokens,
        },
    }

    response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=(10, 60))
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned no text: {data}")
    return text


def _call_claude_chat(
    *,
    llm_url: str,
    model_name: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    if not api_key:
        raise RuntimeError("Claude is selected but CLAUDE_API_KEY is not configured on the server.")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload: dict[str, Any] = {
        "model": model_name,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    response = requests.post(llm_url, headers=headers, json=payload, timeout=(10, 60))
    response.raise_for_status()
    data = response.json()
    content = data.get("content", [])
    text = "\n".join(item.get("text", "") for item in content if item.get("type") == "text").strip()
    if not text:
        raise RuntimeError(f"Claude returned no text: {data}")
    return text


def _build_fallback_answer(*, system_prompt: str, user_prompt: str, provider: str) -> str:
    return (
        f"Provider `{provider}` adapter is scaffolded but not yet fully implemented.\n\n"
        "System prompt:\n"
        f"{system_prompt[:400]}\n\n"
        "User prompt excerpt:\n"
        f"{user_prompt[:1200]}"
    )


def _derive_completions_url(llm_url: str) -> str | None:
    normalized = llm_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized.removesuffix("/chat/completions") + "/completions"
    return None


def _build_completion_prompt(*, system_prompt: str, user_prompt: str) -> str:
    return (
        "System instruction:\n"
        f"{system_prompt.strip()}\n\n"
        "Answer rules:\n"
        "- Reply only with the final answer.\n"
        "- Do not repeat the instructions.\n"
        "- Do not mention missing context unless there is truly no clue.\n"
        "- If the answer is likely visible in the file name or excerpt, state it directly.\n\n"
        "User request:\n"
        f"{user_prompt.strip()}\n\n"
        "Answer:"
    )


def _extract_openai_style_text(data: dict[str, Any], *, provider: str = "") -> str:
    choices = data.get("choices", [])
    if not choices:
        return ""

    choice = choices[0]
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()

    text = choice.get("text", "")
    if isinstance(text, str):
        cleaned = text.strip()
        if provider == "Local":
          return _clean_local_completion_text(cleaned)
        return cleaned

    return ""


def _clean_local_completion_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").strip()

    for marker in ("Answer:", "<|im_end|>", "<|endoftext|>"):
        cleaned = cleaned.replace(marker, "").strip()

    filtered_lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            continue
        if lowered.startswith("system instruction"):
            continue
        if lowered.startswith("user request"):
            continue
        if lowered.startswith("answer rules"):
            continue
        if lowered.startswith("question:"):
            continue
        if lowered.startswith("context:"):
            continue
        if lowered.startswith("you are an ai assistant"):
            continue
        filtered_lines.append(stripped)

    if not filtered_lines:
        return cleaned

    compact = " ".join(filtered_lines).strip()
    for splitter in (" You are an AI assistant", " System instruction:", " User request:"):
        if splitter in compact:
            compact = compact.split(splitter, 1)[0].strip()

    for splitter in (
        " The excerpt ",
        " Given the ",
        " However,",
        " Since the question",
        " Based on the context",
    ):
        if splitter in compact:
            compact = compact.split(splitter, 1)[0].strip()

    return compact


def _raise_for_status_with_body(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text.strip()
        if body:
            raise RuntimeError(f"{exc}. Response body: {body[:1000]}") from exc
        raise
