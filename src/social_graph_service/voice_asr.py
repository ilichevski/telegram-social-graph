from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, Optional

from .models import Chat, Message


DEFAULT_ASR_MODEL = os.getenv("VOICE_ASR_MODEL", "small")
DEFAULT_ASR_LANG = os.getenv("VOICE_ASR_LANGUAGE", "ru")
MAX_VOICE_MESSAGES_PER_CHAT = int(os.getenv("VOICE_ASR_MAX_MESSAGES_PER_CHAT", "24"))
MAX_VOICE_SECONDS_PER_CHAT = float(os.getenv("VOICE_ASR_MAX_SECONDS_PER_CHAT", "900"))
MIN_VOICE_SECONDS = float(os.getenv("VOICE_ASR_MIN_SECONDS", "1.5"))


@dataclass(frozen=True)
class VoiceAsrConfig:
    model_name: str = DEFAULT_ASR_MODEL
    language: Optional[str] = DEFAULT_ASR_LANG
    max_messages_per_chat: int = MAX_VOICE_MESSAGES_PER_CHAT
    max_seconds_per_chat: float = MAX_VOICE_SECONDS_PER_CHAT
    min_seconds: float = MIN_VOICE_SECONDS
    as_of_date: Optional[date] = None
    window_days: int = 91


def enrich_voice_transcripts(
    chats: Iterable[Chat],
    export_root: Path,
    *,
    cache: Optional[Dict[str, Dict[str, object]]] = None,
    config: Optional[VoiceAsrConfig] = None,
) -> Dict[str, Dict[str, object]]:
    cache = cache if cache is not None else {}
    config = config or VoiceAsrConfig()
    runtime = _get_runtime()
    if runtime is None:
        return {}

    selected_entries: list[tuple[Chat, Message, Path, str]] = []
    for chat in chats:
        if chat.chat_type != "private":
            continue
        selected = _select_voice_messages(chat.messages, config)
        if not selected:
            continue
        for message in selected:
            if not message.media_path:
                continue
            audio_path = export_root / message.media_path
            if not audio_path.exists():
                continue
            cache_key = _cache_key(audio_path, message, config)
            selected_entries.append((chat, message, audio_path, cache_key))

    pending_paths = [audio_path for _chat, _message, audio_path, cache_key in selected_entries if cache_key not in cache]
    if pending_paths:
        batch_results = runtime(pending_paths, config)
        for chat, message, audio_path, cache_key in selected_entries:
            if cache_key in cache:
                continue
            text = batch_results.get(str(audio_path), "")
            cache[cache_key] = {
                "text": text,
                "seconds": float(message.media_duration_seconds or 0.0),
                "message_id": message.message_id,
                "is_outgoing": message.is_outgoing,
            }

    results: Dict[str, Dict[str, object]] = {}
    for chat, _message, _audio_path, cache_key in selected_entries:
        cached = cache.get(cache_key)
        if cached is None:
            continue
        results.setdefault(chat.chat_id, {"messages": []})
        results[chat.chat_id]["messages"].append(dict(cached))

    for chat_id, payload in results.items():
        transcripts = payload["messages"]
        payload["voice_message_count"] = len(transcripts)
        payload["voice_seconds_total"] = round(sum(item["seconds"] for item in transcripts), 2)
        payload["sample_text"] = " ".join(item["text"] for item in transcripts if item.get("text"))[:6000].strip()
    return results


def apply_voice_transcripts(chats: Iterable[Chat], transcripts_by_chat: Dict[str, Dict[str, object]]) -> list[Chat]:
    if not transcripts_by_chat:
        return list(chats)

    by_chat_and_message: Dict[tuple[str, str], Dict[str, object]] = {}
    for chat_id, payload in transcripts_by_chat.items():
        for item in payload.get("messages", []):
            message_id = str(item.get("message_id", ""))
            if message_id:
                by_chat_and_message[(chat_id, message_id)] = item

    augmented: list[Chat] = []
    for chat in chats:
        updated_messages: list[Message] = []
        changed = False
        for message in chat.messages:
            transcript = by_chat_and_message.get((chat.chat_id, message.message_id))
            if transcript and transcript.get("text"):
                text = str(transcript["text"]).strip()
                if text and text not in (message.text or ""):
                    prefix = "[Voice transcript] "
                    merged_text = (message.text or "").strip()
                    merged_text = f"{merged_text}\n{prefix}{text}".strip() if merged_text else f"{prefix}{text}"
                    updated_messages.append(
                        Message(
                            chat_id=message.chat_id,
                            chat_name=message.chat_name,
                            chat_type=message.chat_type,
                            message_id=message.message_id,
                            sender_id=message.sender_id,
                            sender_name=message.sender_name,
                            timestamp=message.timestamp,
                            text=merged_text,
                            is_outgoing=message.is_outgoing,
                            reply_to_message_id=message.reply_to_message_id,
                            media_kind=message.media_kind,
                            media_path=message.media_path,
                            media_thumbnail_path=message.media_thumbnail_path,
                            mime_type=message.mime_type,
                            media_duration_seconds=message.media_duration_seconds,
                            media_width=message.media_width,
                            media_height=message.media_height,
                            media_file_size_bytes=message.media_file_size_bytes,
                            media_has_binary=message.media_has_binary,
                            sticker_emoji=message.sticker_emoji,
                            raw=dict(message.raw),
                        )
                    )
                    changed = True
                    continue
            updated_messages.append(message)
        if changed:
            augmented.append(
                Chat(
                    chat_id=chat.chat_id,
                    name=chat.name,
                    chat_type=chat.chat_type,
                    messages=updated_messages,
                )
            )
        else:
            augmented.append(chat)
    return augmented


def _select_voice_messages(messages: Iterable[Message], config: VoiceAsrConfig) -> list[Message]:
    candidates = [
        message
        for message in messages
        if message.media_kind in {"voice", "audio"}
        and message.media_has_binary
        and float(message.media_duration_seconds or 0.0) >= config.min_seconds
        and _within_window(message, config)
    ]
    candidates.sort(key=lambda message: message.timestamp, reverse=True)
    picked: list[Message] = []
    seconds_total = 0.0
    for message in candidates:
        duration = float(message.media_duration_seconds or 0.0)
        if len(picked) >= config.max_messages_per_chat:
            break
        if picked and seconds_total + duration > config.max_seconds_per_chat:
            break
        picked.append(message)
        seconds_total += duration
    picked.sort(key=lambda message: message.timestamp)
    return picked


def _within_window(message: Message, config: VoiceAsrConfig) -> bool:
    if config.as_of_date is None:
        return True
    age_days = (config.as_of_date - message.timestamp.date()).days
    return 0 <= age_days <= config.window_days


def _cache_key(audio_path: Path, message: Message, config: VoiceAsrConfig) -> str:
    stat = audio_path.stat()
    payload = {
        "path": str(audio_path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "message_id": message.message_id,
        "model": config.model_name,
        "language": config.language,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest


def _get_runtime():
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return _get_subprocess_runtime()

    model_holder: dict[str, WhisperModel] = {}

    def _transcribe_many(audio_paths: list[Path], config: VoiceAsrConfig) -> Dict[str, str]:
        model = model_holder.get(config.model_name)
        if model is None:
            model = WhisperModel(config.model_name, device="cpu", compute_type="int8")
            model_holder[config.model_name] = model
        results: Dict[str, str] = {}
        for audio_path in audio_paths:
            segments, _info = model.transcribe(str(audio_path), language=config.language, vad_filter=True)
            text = " ".join(segment.text.strip() for segment in segments if segment.text and segment.text.strip())
            results[str(audio_path)] = " ".join(text.split())
        return results

    return _transcribe_many


def _get_subprocess_runtime():
    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src"
    asr_python = Path(os.getenv("VOICE_ASR_PYTHON", str(repo_root / ".asr-venv" / "bin" / "python")))
    if not asr_python.exists():
        return None

    def _transcribe_many(audio_paths: list[Path], config: VoiceAsrConfig) -> Dict[str, str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_root}{os.pathsep}{existing}" if existing else str(src_root)
        command = [
            str(asr_python),
            "-m",
            "social_graph_service._voice_asr_worker",
            "--model",
            config.model_name,
        ]
        if config.language:
            command.extend(["--language", config.language])
        command.extend([str(path) for path in audio_paths])
        completed = subprocess.run(command, capture_output=True, text=True, env=env, check=True)
        payload = json.loads(completed.stdout)
        return {
            str(item.get("path")): str(item.get("text", "")).strip()
            for item in payload
            if isinstance(item, dict) and item.get("path")
        }

    return _transcribe_many
