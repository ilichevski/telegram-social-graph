from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from statistics import mean
from typing import Callable, Dict, Iterable, List, Optional

from .models import Chat


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
TRANSCRIPT_LINE_LIMIT = int(os.getenv("OLLAMA_TRANSCRIPT_LIMIT", "80"))


@dataclass
class OllamaConfig:
    model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    endpoint: str = os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))


class OllamaError(RuntimeError):
    pass


def enrich_private_chat_scores(
    chats: Iterable[Chat],
    config: Optional[OllamaConfig] = None,
    cache: Optional[Dict[str, Dict[str, float]]] = None,
    on_chat_scored: Optional[Callable[[str, Dict[str, float], bool], None]] = None,
) -> Dict[str, Dict[str, float]]:
    config = config or OllamaConfig()
    cache = cache if cache is not None else {}
    results: Dict[str, Dict[str, float]] = {}

    for chat in chats:
        if chat.chat_type != "private":
            continue
        transcript = _compact_transcript(chat)
        if not transcript:
            continue
        cache_key = f"{chat.name}\n{transcript}"
        cached = cache.get(cache_key)
        if cached:
            results[chat.chat_id] = dict(cached)
            if on_chat_scored is not None:
                on_chat_scored(chat.chat_id, dict(cached), True)
            continue
        prompt = _build_prompt(chat.name, transcript)
        try:
            response = _generate(prompt, config)
        except OllamaError:
            continue
        parsed = _parse_response(response)
        if parsed:
            cache[cache_key] = dict(parsed)
            results[chat.chat_id] = parsed
            if on_chat_scored is not None:
                on_chat_scored(chat.chat_id, dict(parsed), False)

    return results


def _compact_transcript(chat: Chat, limit: int = TRANSCRIPT_LINE_LIMIT) -> str:
    lines: List[str] = []
    for message in chat.messages[-limit:]:
        speaker = "YOU" if message.is_outgoing else message.sender_name
        if message.text.strip():
            lines.append(f"{speaker}: {message.text.strip()}")
    return "\n".join(lines)


def _build_prompt(chat_name: str, transcript: str) -> str:
    return (
        "You are scoring the emotional texture of a private chat.\n"
        "Return strict JSON with numeric fields from 0 to 1:\n"
        '{"self_to_peer_warmth": 0.0, "peer_to_self_warmth": 0.0, "mutuality": 0.0, "tension": 0.0}\n'
        "Judge only from the transcript. Do not explain.\n"
        f"CHAT: {chat_name}\n"
        f"TRANSCRIPT:\n{transcript}"
    )


def _generate(prompt: str, config: OllamaConfig) -> str:
    payload = json.dumps(
        {
            "model": config.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
            "options": {
                "temperature": 0,
                "num_predict": 64,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        config.endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise OllamaError(str(exc)) from exc

    raw = body.get("response")
    if not isinstance(raw, str):
        raise OllamaError("Ollama response did not include a string payload.")
    return raw


def _parse_response(raw: str) -> Optional[Dict[str, float]]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    fields = ["self_to_peer_warmth", "peer_to_self_warmth", "mutuality", "tension"]
    result: Dict[str, float] = {}
    for field in fields:
        value = payload.get(field)
        if isinstance(value, (int, float)):
            result[field] = round(max(0.0, min(1.0, float(value))), 4)
    return result if result else None
