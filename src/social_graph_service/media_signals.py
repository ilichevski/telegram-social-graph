from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from .models import Message


WARM_EMOJIS = {
    "❤",
    "❤️",
    "💕",
    "💖",
    "💗",
    "💞",
    "💓",
    "💘",
    "💙",
    "💚",
    "💛",
    "💜",
    "🤍",
    "🫶",
    "😘",
    "😍",
    "🥰",
    "😊",
    "☺️",
    "☺",
    "🤗",
    "😚",
    "😌",
}
SUPPORT_EMOJIS = {
    "👍",
    "👌",
    "🙏",
    "🤝",
    "💪",
    "🙌",
    "👏",
    "🫶",
    "❤️",
    "❤",
    "🤗",
    "🙂",
}
PLAYFUL_EMOJIS = {
    "😂",
    "🤣",
    "😹",
    "😜",
    "🤪",
    "😏",
    "😉",
    "😎",
    "🙃",
    "😅",
    "😋",
    "😛",
    "😺",
    "😸",
}
TENSE_EMOJIS = {
    "😡",
    "😠",
    "🙄",
    "😒",
    "😐",
    "😶",
    "👎",
    "🤦",
    "🤦‍♂️",
    "🤦‍♀️",
    "😤",
}

WARM_FILENAME_MARKERS = ("love", "heart", "hug", "kiss", "cute", "happy", "yay", "sweet")
SUPPORT_FILENAME_MARKERS = ("care", "support", "help", "proud", "bravo", "clap")
PLAYFUL_FILENAME_MARKERS = ("lol", "haha", "fun", "party", "dance", "wow", "cat", "dog", "meme", "giphy")
TENSION_FILENAME_MARKERS = ("angry", "mad", "ugh", "eyeroll", "facepalm", "wtf", "nope")
FORMAL_FILE_MARKERS = (
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "csv",
    "zip",
    "txt",
)


@dataclass(frozen=True)
class MediaSignal:
    warmth: float = 0.0
    support: float = 0.0
    tension: float = 0.0
    formality: float = 0.0
    depth: float = 0.0
    engagement: float = 0.0
    intimacy: float = 0.0
    playfulness: float = 0.0
    expressiveness: float = 0.0


ZERO_SIGNAL = MediaSignal()


def message_media_signal(message: Message) -> MediaSignal:
    kind = (message.media_kind or "").casefold()
    if not kind:
        return ZERO_SIGNAL

    if kind == "photo":
        return _photo_signal(message)
    if kind in {"voice", "audio"}:
        return _voice_signal(message, generic=(kind == "audio"))
    if kind in {"video", "gif"}:
        return _animated_signal(message, gif_like=(kind == "gif"))
    if kind == "sticker":
        return _sticker_signal(message)
    if kind == "file":
        return _file_signal(message)
    return ZERO_SIGNAL


def signal_mean(signals: Iterable[float]) -> float:
    values = [float(value) for value in signals]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _photo_signal(message: Message) -> MediaSignal:
    has_caption = bool((message.text or "").strip())
    binary_bonus = 0.04 if message.media_has_binary else 0.0
    return MediaSignal(
        warmth=0.08 if has_caption else 0.03,
        support=0.03 if has_caption else 0.0,
        depth=0.10 if has_caption else 0.04,
        engagement=0.10,
        intimacy=0.22 + binary_bonus,
        playfulness=0.04,
        expressiveness=0.18 + binary_bonus,
    )


def _voice_signal(message: Message, *, generic: bool) -> MediaSignal:
    duration = max(0.0, float(message.media_duration_seconds or 0.0))
    length_factor = min(1.0, duration / (120.0 if generic else 90.0))
    intimacy_base = 0.22 if generic else 0.28
    return MediaSignal(
        warmth=0.05 + length_factor * 0.08,
        support=0.06 + length_factor * 0.16,
        depth=0.18 + length_factor * 0.32,
        engagement=0.10 + length_factor * 0.14,
        intimacy=intimacy_base + length_factor * 0.42,
        playfulness=0.02 + length_factor * 0.04,
        expressiveness=0.24 + length_factor * 0.28,
    )


def _animated_signal(message: Message, *, gif_like: bool) -> MediaSignal:
    duration = max(0.0, float(message.media_duration_seconds or 0.0))
    length_factor = min(1.0, duration / 45.0)
    name = _normalized_media_name(message)
    warm = 0.12 if _contains_any(name, WARM_FILENAME_MARKERS) else 0.03
    support = 0.10 if _contains_any(name, SUPPORT_FILENAME_MARKERS) else 0.0
    playful = 0.28 if gif_like else 0.12
    if _contains_any(name, PLAYFUL_FILENAME_MARKERS):
        playful += 0.16
    tension = 0.18 if _contains_any(name, TENSION_FILENAME_MARKERS) else 0.0
    return MediaSignal(
        warmth=min(1.0, warm + length_factor * 0.05),
        support=support,
        tension=tension,
        depth=0.04 + length_factor * 0.05,
        engagement=0.10 + length_factor * 0.10,
        intimacy=0.10 + length_factor * 0.08,
        playfulness=min(1.0, playful),
        expressiveness=0.22 + length_factor * 0.16,
    )


def _sticker_signal(message: Message) -> MediaSignal:
    emoji = message.sticker_emoji or ""
    warmth = 0.26 if _contains_any(emoji, WARM_EMOJIS) else 0.02
    support = 0.22 if _contains_any(emoji, SUPPORT_EMOJIS) else 0.0
    tension = 0.28 if _contains_any(emoji, TENSE_EMOJIS) else 0.0
    playfulness = 0.24 if _contains_any(emoji, PLAYFUL_EMOJIS) else 0.08
    return MediaSignal(
        warmth=warmth,
        support=support,
        tension=tension,
        depth=0.02,
        engagement=0.08,
        intimacy=0.12 if warmth > 0 else 0.05,
        playfulness=playfulness,
        expressiveness=0.24,
    )


def _file_signal(message: Message) -> MediaSignal:
    mime_type = (message.mime_type or "").casefold()
    name = _normalized_media_name(message)
    looks_formal = any(marker in mime_type for marker in FORMAL_FILE_MARKERS) or _contains_any(name, FORMAL_FILE_MARKERS)
    return MediaSignal(
        formality=0.22 if looks_formal else 0.08,
        depth=0.02,
        engagement=0.06,
        expressiveness=0.04,
    )


def _normalized_media_name(message: Message) -> str:
    candidate = message.media_path or message.media_thumbnail_path or ""
    if not candidate:
        return ""
    return PurePosixPath(candidate).name.casefold()


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    lowered = text.casefold()
    return any(marker.casefold() in lowered for marker in markers)
