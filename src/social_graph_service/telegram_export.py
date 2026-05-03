from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import Chat, Message


SUPPORTED_FILENAMES = {"result.json"}
MEDIA_KIND_ALIASES = {
    "photo": "photo",
    "video_file": "video",
    "video message": "video",
    "video_message": "video",
    "animation": "gif",
    "gif": "gif",
    "sticker": "sticker",
    "voice_message": "voice",
    "voice message": "voice",
    "audio_file": "audio",
    "audio": "audio",
}


@dataclass
class ImportStats:
    files_scanned: int = 0
    chats_loaded: int = 0
    messages_loaded: int = 0


@dataclass
class SelfIdentity:
    self_name: Optional[str] = None
    self_user_id: Optional[str] = None


def discover_export_files(root: Path) -> List[Path]:
    if root.is_file():
        return [root]

    candidates: List[Path] = []
    for path in root.rglob("*.json"):
        if path.name in SUPPORTED_FILENAMES or path.parent == root or "chat" in path.stem.lower():
            candidates.append(path)
    return sorted(set(candidates))


def load_chats(root: Path, self_name: Optional[str] = None) -> tuple[List[Chat], ImportStats]:
    files = discover_export_files(root)
    stats = ImportStats(files_scanned=len(files))
    chats: List[Chat] = []

    for file_path in files:
        loaded = _load_chat_file(file_path, self_name=self_name)
        for chat in loaded:
            if not chat.messages:
                continue
            chats.append(chat)
            stats.chats_loaded += 1
            stats.messages_loaded += len(chat.messages)

    return chats, stats


def _load_chat_file(path: Path, self_name: Optional[str] = None) -> List[Chat]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    self_identity = _extract_self_identity(payload, override_name=self_name)

    if isinstance(payload, dict) and "messages" in payload:
        chat = _parse_single_chat(payload, path, self_identity=self_identity)
        return [chat] if chat else []

    if isinstance(payload, dict) and isinstance(payload.get("chats"), dict):
        chat_list = payload["chats"].get("list", [])
        parsed: List[Chat] = []
        for item in chat_list:
            if not isinstance(item, dict):
                continue
            chat = _parse_single_chat(item, path, self_identity=self_identity)
            if chat:
                parsed.append(chat)
        return parsed

    return []


def _parse_single_chat(payload: Dict[str, Any], path: Path, self_identity: Optional[SelfIdentity] = None) -> Optional[Chat]:
    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        return None

    chat_id = str(payload.get("id", path.stem))
    chat_name = str(payload.get("name", path.stem))
    chat_type = _infer_chat_type(payload)

    messages: List[Message] = []
    for item in raw_messages:
        message = _parse_message(
            item,
            chat_id=chat_id,
            chat_name=chat_name,
            chat_type=chat_type,
            self_identity=self_identity,
        )
        if message is not None:
            messages.append(message)

    return Chat(
        chat_id=chat_id,
        name=chat_name,
        chat_type=chat_type,
        messages=sorted(messages, key=lambda message: message.timestamp),
    )


def _infer_chat_type(payload: Dict[str, Any]) -> str:
    raw_type = str(payload.get("type", "")).lower()
    if raw_type == "private_group":
        return "group"
    if "private" in raw_type or "personal_chat" in raw_type:
        return "private"
    if "group" in raw_type or "supergroup" in raw_type:
        return "group"
    if "channel" in raw_type:
        return "channel"
    if "saved" in raw_type:
        return "self"
    return "unknown"


def _parse_message(
    payload: Dict[str, Any],
    *,
    chat_id: str,
    chat_name: str,
    chat_type: str,
    self_identity: Optional[SelfIdentity] = None,
) -> Optional[Message]:
    if not isinstance(payload, dict):
        return None
    if str(payload.get("type", "message")).lower() != "message":
        return None

    text = _flatten_text(payload.get("text", ""))
    sender_name = str(payload.get("from") or payload.get("actor") or "Unknown")
    sender_id = str(payload.get("from_id") or payload.get("actor_id") or sender_name)
    timestamp = _parse_timestamp(payload)
    is_outgoing = bool(payload.get("out")) or _looks_like_self(sender_name, sender_id, self_identity=self_identity)
    reply_to_message_id = payload.get("reply_to_message_id")
    media_kind, media_path, media_duration_seconds, sticker_emoji = _parse_media(payload)

    return Message(
        chat_id=chat_id,
        chat_name=chat_name,
        chat_type=chat_type,
        message_id=str(payload.get("id", "")),
        sender_id=sender_id,
        sender_name=sender_name,
        timestamp=timestamp,
        text=text.strip(),
        is_outgoing=is_outgoing,
        reply_to_message_id=str(reply_to_message_id) if reply_to_message_id is not None else None,
        media_kind=media_kind,
        media_path=media_path,
        media_duration_seconds=media_duration_seconds,
        sticker_emoji=sticker_emoji,
        raw=payload,
    )


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if isinstance(value, dict):
        return str(value.get("text", ""))
    return ""


def _parse_timestamp(payload: Dict[str, Any]) -> datetime:
    date_unix = payload.get("date_unixtime")
    if date_unix is not None:
        return datetime.fromtimestamp(int(date_unix), tz=timezone.utc)

    date_str = payload.get("date")
    if isinstance(date_str, str):
        candidate = date_str.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    return datetime.fromtimestamp(0, tz=timezone.utc)


def _looks_like_self(sender_name: str, sender_id: str, self_identity: Optional[SelfIdentity] = None) -> bool:
    if self_identity and self_identity.self_name:
        if sender_name.strip().casefold() == self_identity.self_name.strip().casefold():
            return True
    if self_identity and self_identity.self_user_id:
        lowered_sender_id = sender_id.casefold()
        lowered_self_user_id = self_identity.self_user_id.casefold()
        if lowered_sender_id == lowered_self_user_id:
            return True
        if lowered_self_user_id.startswith("user") and lowered_sender_id == lowered_self_user_id[4:]:
            return True
        if lowered_sender_id == f"user{lowered_self_user_id}":
            return True
    lowered_id = sender_id.casefold()
    lowered_name = sender_name.casefold()
    return lowered_id in {"user_self", "self", "me"} or lowered_name in {"me", "saved messages"}


def _extract_self_identity(payload: Dict[str, Any], override_name: Optional[str] = None) -> SelfIdentity:
    personal_information = payload.get("personal_information")
    if not isinstance(personal_information, dict):
        return SelfIdentity(self_name=override_name)

    first_name = _as_optional_string(personal_information.get("first_name"))
    last_name = _as_optional_string(personal_information.get("last_name"))
    full_name = " ".join(part for part in [first_name, last_name] if part)
    user_id = personal_information.get("user_id")
    return SelfIdentity(
        self_name=override_name or full_name or first_name,
        self_user_id=str(user_id) if user_id is not None else None,
    )


def _parse_media(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
    sticker_emoji = _as_optional_string(payload.get("sticker_emoji"))
    media_path = _as_optional_string(payload.get("photo")) or _as_optional_string(payload.get("file"))
    duration = _as_optional_float(payload.get("duration_seconds")) or _as_optional_float(payload.get("duration"))
    raw_media_type = _as_optional_string(payload.get("media_type"))
    mime_type = _as_optional_string(payload.get("mime_type"))

    media_kind: Optional[str] = None
    if raw_media_type:
        normalized = raw_media_type.strip().casefold().replace("-", "_")
        media_kind = MEDIA_KIND_ALIASES.get(normalized) or MEDIA_KIND_ALIASES.get(normalized.replace("_", " "))

    if media_kind is None and sticker_emoji:
        media_kind = "sticker"
    if media_kind is None and payload.get("photo"):
        media_kind = "photo"
    if media_kind is None and mime_type:
        media_kind = _infer_media_kind_from_mime(mime_type)
    if media_kind is None and media_path:
        media_kind = _infer_media_kind_from_path(media_path)

    return media_kind, media_path, duration, sticker_emoji


def _infer_media_kind_from_mime(mime_type: str) -> Optional[str]:
    lowered = mime_type.casefold()
    if lowered == "image/gif":
        return "gif"
    if lowered.startswith("image/"):
        return "photo"
    if lowered.startswith("video/"):
        return "video"
    if lowered == "audio/ogg":
        return "voice"
    if lowered.startswith("audio/"):
        return "audio"
    return None


def _infer_media_kind_from_path(path: str) -> Optional[str]:
    lowered = path.casefold()
    if lowered.endswith(".gif"):
        return "gif"
    if lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
        return "photo"
    if lowered.endswith((".mp4", ".mov", ".mkv", ".webm")):
        return "video"
    if lowered.endswith((".ogg", ".opus", ".m4a", ".mp3", ".wav")):
        return "audio"
    return "file"


def _as_optional_string(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _as_optional_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None
