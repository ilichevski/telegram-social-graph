from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List

from .models import Chat, Message


RICH_MEDIA_KINDS = {"photo", "voice", "video", "gif", "sticker", "audio"}


def build_chat_profiles(chats: Iterable[Chat]) -> Dict[str, Any]:
    chats = list(chats)
    media_totals: Counter[str] = Counter()
    top_media_chats: List[Dict[str, Any]] = []
    self_only_groups: List[Dict[str, Any]] = []

    for chat in chats:
        all_media = _media_counts(chat.messages)
        own_messages = [message for message in chat.messages if message.is_outgoing]
        own_media = _media_counts(own_messages)
        media_totals.update(all_media)

        media_message_count = sum(all_media.values())
        profile = {
            "chat_id": chat.chat_id,
            "chat_name": chat.name,
            "chat_type": chat.chat_type,
            "messages_total": len(chat.messages),
            "messages_own": len(own_messages),
            "messages_other": len(chat.messages) - len(own_messages),
            "media_messages_total": media_message_count,
            "media_messages_own": sum(own_media.values()),
            "media_breakdown": dict(all_media),
            "own_media_breakdown": dict(own_media),
            "self_only_export": bool(chat.messages) and all(message.is_outgoing for message in chat.messages),
            "rich_media_ratio": _safe_ratio(sum(all_media[kind] for kind in RICH_MEDIA_KINDS), len(chat.messages)),
        }

        if media_message_count > 0:
            top_media_chats.append(profile)
        if chat.chat_type == "group" and profile["self_only_export"]:
            self_only_groups.append(profile)

    top_media_chats.sort(key=lambda item: (item["media_messages_total"], item["messages_total"]), reverse=True)
    self_only_groups.sort(key=lambda item: (item["messages_own"], item["media_messages_own"]), reverse=True)

    return {
        "media_totals": dict(media_totals),
        "media_message_count": int(sum(media_totals.values())),
        "top_media_chats": top_media_chats[:25],
        "self_only_groups": self_only_groups[:25],
        "self_only_group_count": len(self_only_groups),
    }


def _media_counts(messages: Iterable[Message]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for message in messages:
        if message.media_kind:
            counts[message.media_kind] += 1
    return counts


def _safe_ratio(left: int, right: int) -> float:
    if right <= 0:
        return 0.0
    return round(left / right, 4)
