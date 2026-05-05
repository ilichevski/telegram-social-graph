from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .media_signals import message_media_signal
from .models import Chat, Message
from .temporal_analysis import DEPTH_MARKERS, FORMALITY_MARKERS, SUPPORT_MARKERS, SESSION_BREAK_HOURS


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
TRANSCRIPT_LINE_LIMIT = int(os.getenv("OLLAMA_TRANSCRIPT_LIMIT", "90"))
MAX_SESSION_COUNT = int(os.getenv("OLLAMA_SESSION_COUNT", "4"))
MAX_LINES_PER_SESSION = int(os.getenv("OLLAMA_LINES_PER_SESSION", "12"))

WARM_MARKERS = (
    "дорог",
    "родн",
    "нежно",
    "люблю",
    "скучаю",
    "обнимаю",
    "спасибо",
    "благодар",
    "забоч",
    "береги",
    "горж",
    "рад",
    "ценю",
    "happy for you",
    "love",
    "miss",
    "hug",
    "thanks",
    "appreciate",
    "care",
    "proud",
)
TENSION_MARKERS = (
    "бесит",
    "злюсь",
    "обидно",
    "ненавижу",
    "раздраж",
    "достал",
    "отвали",
    "annoyed",
    "angry",
    "upset",
    "hate",
    "irritat",
    "shut up",
)


@dataclass
class OllamaConfig:
    model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    endpoint: str = os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))


class OllamaError(RuntimeError):
    pass


def enrich_private_chat_scores(
    chats: Iterable[Chat],
    config: Optional[OllamaConfig] = None,
    cache: Optional[Dict[str, Dict[str, Any]]] = None,
    on_chat_scored: Optional[Callable[[str, Dict[str, Any], bool], None]] = None,
) -> Dict[str, Dict[str, Any]]:
    config = config or OllamaConfig()
    cache = cache if cache is not None else {}
    results: Dict[str, Dict[str, Any]] = {}

    for chat in chats:
        if chat.chat_type != "private":
            continue
        context = _build_chat_context(chat)
        if not context["transcript"]:
            continue
        cache_key = json.dumps(
            {
                "chat_name": chat.name,
                "context": context,
                "model": config.model,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        cached = cache.get(cache_key)
        if cached:
            results[chat.chat_id] = dict(cached)
            if on_chat_scored is not None:
                on_chat_scored(chat.chat_id, dict(cached), True)
            continue
        prompt = _build_prompt(chat.name, context)
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


def _build_chat_context(chat: Chat) -> Dict[str, object]:
    messages = [message for message in chat.messages if (message.text or "").strip() or message.media_kind]
    if not messages:
        return {"transcript": "", "stats": {}, "session_count": 0}

    recent_messages = messages[-TRANSCRIPT_LINE_LIMIT:]
    sessions = _sessionize_messages(recent_messages)
    selected_sessions = _select_representative_sessions(sessions)
    transcript = _render_session_transcript(selected_sessions)
    stats = _behavioral_summary(messages, sessions)

    return {
        "transcript": transcript,
        "stats": stats,
        "session_count": len(sessions),
    }


def _sessionize_messages(messages: Sequence[Message]) -> List[List[Message]]:
    sessions: List[List[Message]] = []
    current: List[Message] = []

    for message in messages:
        if not current:
            current = [message]
            continue
        previous = current[-1]
        gap_hours = (message.timestamp - previous.timestamp).total_seconds() / 3600.0
        if gap_hours > SESSION_BREAK_HOURS:
            sessions.append(current)
            current = [message]
        else:
            current.append(message)

    if current:
        sessions.append(current)
    return sessions


def _select_representative_sessions(sessions: Sequence[Sequence[Message]]) -> List[List[Message]]:
    if not sessions:
        return []

    indexed = list(enumerate(sessions))
    selected_indexes: List[int] = []

    # Always keep the freshest 1-2 sessions.
    latest_indexes = [index for index, _ in indexed[-2:]]
    selected_indexes.extend(latest_indexes)

    def best_index(metric_name: str) -> Optional[int]:
        best: Optional[tuple[float, int]] = None
        for index, session in indexed:
            summary = _session_summary(session)
            score = float(summary.get(metric_name, 0.0))
            if best is None or score > best[0]:
                best = (score, index)
        return best[1] if best and best[0] > 0 else None

    for metric_name in ("support_signal", "tension_signal", "depth_signal", "warmth_signal"):
        index = best_index(metric_name)
        if index is not None and index not in selected_indexes:
            selected_indexes.append(index)

    # Fill the remaining slots with highest blended-score sessions.
    ranked = sorted(
        (
            (
                _session_rank_score(session, order, len(sessions)),
                order,
            )
            for order, session in indexed
        ),
        reverse=True,
    )
    for _, index in ranked:
        if index not in selected_indexes:
            selected_indexes.append(index)
        if len(selected_indexes) >= MAX_SESSION_COUNT:
            break

    return [list(sessions[index]) for index in sorted(selected_indexes)[:MAX_SESSION_COUNT]]


def _session_rank_score(session: Sequence[Message], index: int, total_sessions: int) -> float:
    summary = _session_summary(session)
    recency = (index + 1) / max(1, total_sessions)
    size = min(1.0, len(session) / 14.0)
    signal = (
        float(summary["warmth_signal"]) * 0.25
        + float(summary["support_signal"]) * 0.25
        + float(summary["depth_signal"]) * 0.20
        + float(summary["tension_signal"]) * 0.15
        + size * 0.15
    )
    return recency * 0.45 + signal * 0.55


def _session_summary(session: Sequence[Message]) -> Dict[str, float]:
    warmth_signal = 0.0
    support_signal = 0.0
    depth_signal = 0.0
    tension_signal = 0.0

    for message in session:
        text = message.text or ""
        warmth_signal += _marker_hits(text, WARM_MARKERS)
        support_signal += _marker_hits(text, SUPPORT_MARKERS)
        depth_signal += _marker_hits(text, DEPTH_MARKERS)
        tension_signal += _marker_hits(text, TENSION_MARKERS)

    divisor = max(1.0, len(session))
    return {
        "warmth_signal": warmth_signal / divisor,
        "support_signal": support_signal / divisor,
        "depth_signal": depth_signal / divisor,
        "tension_signal": tension_signal / divisor,
    }


def _render_session_transcript(sessions: Sequence[Sequence[Message]]) -> str:
    blocks: List[str] = []
    for idx, session in enumerate(sessions, start=1):
        start = session[0].timestamp.astimezone(timezone.utc).strftime("%d %b %Y %H:%M UTC")
        end = session[-1].timestamp.astimezone(timezone.utc).strftime("%d %b %Y %H:%M UTC")
        lines = [f"[Session {idx} | {start} -> {end} | {len(session)} messages]"]
        for message in session[-MAX_LINES_PER_SESSION:]:
            speaker = "YOU" if message.is_outgoing else message.sender_name
            text = " ".join((message.text or "").split()) or _render_media_stub(message)
            lines.append(f"{speaker}: {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_media_stub(message: Message) -> str:
    kind = (message.media_kind or "media").upper()
    if message.media_kind == "voice":
        return f"[VOICE {int(round(float(message.media_duration_seconds or 0.0)))}s]"
    if message.media_kind == "audio":
        return f"[AUDIO {int(round(float(message.media_duration_seconds or 0.0)))}s]"
    if message.media_kind == "sticker":
        emoji = message.sticker_emoji or ""
        return f"[STICKER {emoji}]".strip()
    if message.media_kind == "photo":
        return "[PHOTO]"
    if message.media_kind == "gif":
        return "[GIF]"
    if message.media_kind == "video":
        return f"[VIDEO {int(round(float(message.media_duration_seconds or 0.0)))}s]"
    return f"[{kind}]"


def _behavioral_summary(messages: Sequence[Message], sessions: Sequence[Sequence[Message]]) -> Dict[str, object]:
    total_messages = len(messages)
    outgoing = [message for message in messages if message.is_outgoing]
    inbound = [message for message in messages if not message.is_outgoing]
    latest_ts = messages[-1].timestamp
    counts_7d = 0
    counts_28d = 0
    counts_91d = 0
    for message in messages:
        age_days = max(0.0, (latest_ts - message.timestamp).total_seconds() / 86400.0)
        if age_days <= 7:
            counts_7d += 1
        if age_days <= 28:
            counts_28d += 1
        if age_days <= 91:
            counts_91d += 1

    outbound_response, inbound_response = _response_latencies(messages)
    session_starts_out = sum(1 for session in sessions if session and session[0].is_outgoing)
    session_starts_in = sum(1 for session in sessions if session and not session[0].is_outgoing)
    marker_counts = {
        "warm": sum(_marker_hits(message.text or "", WARM_MARKERS) for message in messages),
        "support": sum(_marker_hits(message.text or "", SUPPORT_MARKERS) for message in messages),
        "depth": sum(_marker_hits(message.text or "", DEPTH_MARKERS) for message in messages),
        "formal": sum(_marker_hits(message.text or "", FORMALITY_MARKERS) for message in messages),
        "tension": sum(_marker_hits(message.text or "", TENSION_MARKERS) for message in messages),
    }
    media_counts: Dict[str, int] = {}
    sticker_emoji_counts: Dict[str, int] = {}
    voice_minutes_you = 0.0
    voice_minutes_them = 0.0
    media_intimacy_you = 0.0
    media_intimacy_them = 0.0
    media_messages_you = 0
    media_messages_them = 0

    for message in messages:
        if message.media_kind:
            media_counts[message.media_kind] = media_counts.get(message.media_kind, 0) + 1
            if message.sticker_emoji:
                sticker_emoji_counts[message.sticker_emoji] = sticker_emoji_counts.get(message.sticker_emoji, 0) + 1
            signal = message_media_signal(message)
            if message.is_outgoing:
                media_intimacy_you += signal.intimacy
                media_messages_you += 1
            else:
                media_intimacy_them += signal.intimacy
                media_messages_them += 1
            if message.media_kind in {"voice", "audio", "video"}:
                minutes = float(message.media_duration_seconds or 0.0) / 60.0
                if message.is_outgoing:
                    voice_minutes_you += minutes
                else:
                    voice_minutes_them += minutes

    return {
        "messages_total": total_messages,
        "messages_7d": counts_7d,
        "messages_28d": counts_28d,
        "messages_91d": counts_91d,
        "outgoing_messages": len(outgoing),
        "incoming_messages": len(inbound),
        "avg_chars_out": round(sum(len(message.text or "") for message in outgoing) / len(outgoing), 1) if outgoing else 0.0,
        "avg_chars_in": round(sum(len(message.text or "") for message in inbound) / len(inbound), 1) if inbound else 0.0,
        "median_reply_minutes_you": outbound_response,
        "median_reply_minutes_them": inbound_response,
        "session_count": len(sessions),
        "session_starts_you": session_starts_out,
        "session_starts_them": session_starts_in,
        "marker_counts": marker_counts,
        "media_counts": media_counts,
        "top_sticker_emoji": sorted(sticker_emoji_counts.items(), key=lambda item: item[1], reverse=True)[:10],
        "voice_minutes_you": round(voice_minutes_you, 1),
        "voice_minutes_them": round(voice_minutes_them, 1),
        "media_intimacy_you": round(media_intimacy_you / media_messages_you, 4) if media_messages_you else 0.0,
        "media_intimacy_them": round(media_intimacy_them / media_messages_them, 4) if media_messages_them else 0.0,
    }


def _response_latencies(messages: Sequence[Message]) -> tuple[Optional[float], Optional[float]]:
    if len(messages) < 2:
        return None, None

    you_latencies: List[float] = []
    them_latencies: List[float] = []
    previous = messages[0]
    for current in messages[1:]:
        if current.is_outgoing == previous.is_outgoing:
            previous = current
            continue
        delta_minutes = (current.timestamp - previous.timestamp).total_seconds() / 60.0
        if delta_minutes <= 0 or delta_minutes > 24 * 60:
            previous = current
            continue
        if current.is_outgoing:
            you_latencies.append(delta_minutes)
        else:
            them_latencies.append(delta_minutes)
        previous = current

    return (
        round(median(you_latencies), 1) if you_latencies else None,
        round(median(them_latencies), 1) if them_latencies else None,
    )


def _marker_hits(text: str, markers: Sequence[str]) -> int:
    lowered = text.casefold()
    return sum(marker in lowered for marker in markers)


def _build_prompt(chat_name: str, context: Dict[str, object]) -> str:
    stats_json = json.dumps(context.get("stats", {}), ensure_ascii=False, sort_keys=True)
    transcript = str(context.get("transcript", ""))
    return (
        "You are a careful judge of the current emotional state of a private relationship chat.\n"
        "Use both the behavioral summary and the selected transcript excerpts.\n"
        "Weight recent excerpts more than older excerpts. Score the relationship as it looks now, not over a lifetime.\n"
        "Return strict JSON only. No prose. All numeric fields must be between 0 and 1.\n"
        "{"
        '"self_to_peer_warmth": 0.0, '
        '"peer_to_self_warmth": 0.0, '
        '"self_to_peer_support": 0.0, '
        '"peer_to_self_support": 0.0, '
        '"self_to_peer_formality": 0.0, '
        '"peer_to_self_formality": 0.0, '
        '"depth": 0.0, '
        '"self_to_peer_engagement": 0.0, '
        '"peer_to_self_engagement": 0.0, '
        '"mutuality": 0.0, '
        '"tension": 0.0, '
        '"confidence": 0.0, '
        '"reason_codes": ["recent_reciprocity", "supportive_language"]'
        "}\n"
        "Scoring guidance:\n"
        "- warmth: affection, gratitude, personal warmth, care, emotional softness.\n"
        "- support: reassurance, care, practical or emotional help, being there for the other person.\n"
        "- formality: businesslike, distant, procedural, polite but impersonal tone.\n"
        "- depth: personal vulnerability, meaningful topics, inner life, non-transactional substance.\n"
        "- engagement: who sustains the contact, asks follow-ups, keeps it alive, re-opens after pauses.\n"
        "- mutuality: how reciprocal and two-sided the current relationship feels overall.\n"
        "- tension: irritation, conflict, coldness, strain.\n"
        "- confidence: how reliable your judgment is from the provided evidence.\n"
        "- voice notes, sticker usage, GIFs, photos, and other media in the behavioral summary are meaningful social signals.\n"
        "Prefer conservative scores when evidence is mixed.\n"
        f"CHAT: {chat_name}\n"
        f"BEHAVIORAL_SUMMARY: {stats_json}\n"
        f"SELECTED_EXCERPTS:\n{transcript}"
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
                "num_predict": 220,
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


def _parse_response(raw: str) -> Optional[Dict[str, Any]]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    numeric_fields = [
        "self_to_peer_warmth",
        "peer_to_self_warmth",
        "self_to_peer_support",
        "peer_to_self_support",
        "self_to_peer_formality",
        "peer_to_self_formality",
        "depth",
        "self_to_peer_engagement",
        "peer_to_self_engagement",
        "mutuality",
        "tension",
        "confidence",
    ]
    legacy_fallbacks = {
        "self_to_peer_support": "self_to_peer_warmth",
        "peer_to_self_support": "peer_to_self_warmth",
        "self_to_peer_formality": None,
        "peer_to_self_formality": None,
        "depth": None,
        "self_to_peer_engagement": "mutuality",
        "peer_to_self_engagement": "mutuality",
        "confidence": "mutuality",
    }

    result: Dict[str, float | List[str]] = {}
    for field in numeric_fields:
        value = payload.get(field)
        if not isinstance(value, (int, float)):
            fallback = legacy_fallbacks.get(field)
            if fallback:
                fallback_value = payload.get(fallback)
                value = fallback_value if isinstance(fallback_value, (int, float)) else None
            elif fallback is None and field in legacy_fallbacks:
                value = 0.0
        if isinstance(value, (int, float)):
            result[field] = round(max(0.0, min(1.0, float(value))), 4)

    reason_codes = payload.get("reason_codes")
    if isinstance(reason_codes, list):
        cleaned = [str(item).strip() for item in reason_codes if str(item).strip()]
        if cleaned:
            result["reason_codes"] = cleaned[:8]

    return result if result else None
