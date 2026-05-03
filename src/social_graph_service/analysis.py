from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple

from .models import Chat, Edge, GraphResult, Message, Node


SESSION_BREAK_HOURS = 12
WARM_WORDS = {
    "ru": {"люблю", "скучаю", "обнимаю", "спасибо", "рад", "дорог", "ценю", "милый", "милая", "родной"},
    "en": {"love", "miss", "hug", "thanks", "dear", "care", "appreciate", "warm", "sweet"},
}
TENSION_WORDS = {
    "ru": {"бесит", "злюсь", "устал", "раздражает", "конфликт", "обидно", "ненавижу"},
    "en": {"annoyed", "angry", "upset", "hate", "conflict", "irritated"},
}
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё']+")


@dataclass
class AnalyzerConfig:
    self_node_id: str = "self"
    self_label: str = "You"
    max_response_gap_hours: int = 24


def analyze_chats(chats: Iterable[Chat], config: Optional[AnalyzerConfig] = None) -> GraphResult:
    config = config or AnalyzerConfig()
    chats = list(chats)
    nodes: Dict[str, Node] = {
        config.self_node_id: Node(
            node_id=config.self_node_id,
            label=config.self_label,
            node_type="person",
            metadata={"is_self": True},
        )
    }
    edges: List[Edge] = []
    total_messages = 0

    for chat in chats:
        total_messages += len(chat.messages)
        if chat.chat_type == "private":
            peer = _resolve_private_peer(chat.messages, config.self_node_id)
            if peer is None:
                continue
            nodes.setdefault(
                peer[0],
                Node(node_id=peer[0], label=peer[1], node_type="person", metadata={"chat_type": "private"}),
            )
            edges.extend(_analyze_private_chat(chat, peer[0], peer[1], config))
        elif chat.chat_type == "group":
            for node in _collect_group_nodes(chat.messages, config.self_node_id):
                nodes.setdefault(node.node_id, node)
            edges.extend(_analyze_group_chat(chat, config))

    summary = {
        "chat_count": len(chats),
        "message_count": total_messages,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    return GraphResult(nodes=list(nodes.values()), edges=edges, summary=summary)


def _resolve_private_peer(messages: List[Message], self_node_id: str) -> Optional[Tuple[str, str]]:
    participants: Dict[str, str] = {}
    for message in messages:
        node_id = self_node_id if message.is_outgoing else message.sender_id
        label = "You" if node_id == self_node_id else message.sender_name
        participants[node_id] = label

    peers = [(node_id, label) for node_id, label in participants.items() if node_id != self_node_id]
    if not peers:
        return None
    return peers[0]


def _collect_group_nodes(messages: List[Message], self_node_id: str) -> List[Node]:
    seen: Dict[str, Node] = {}
    for message in messages:
        node_id = self_node_id if message.is_outgoing else message.sender_id
        label = "You" if node_id == self_node_id else message.sender_name
        if node_id not in seen:
            seen[node_id] = Node(node_id=node_id, label=label, node_type="person", metadata={"chat_type": "group"})
    return list(seen.values())


def _analyze_private_chat(chat: Chat, peer_id: str, peer_name: str, config: AnalyzerConfig) -> List[Edge]:
    outgoing = [message for message in chat.messages if message.is_outgoing]
    incoming = [message for message in chat.messages if not message.is_outgoing]
    reply_metrics = _response_metrics(chat.messages, config.max_response_gap_hours)
    outgoing_media = _media_metrics(outgoing)
    incoming_media = _media_metrics(incoming)

    out_warmth = _warmth_score(outgoing)
    in_warmth = _warmth_score(incoming)
    reciprocity = _ratio(len(outgoing), len(incoming))
    initiation = _initiation_balance(chat.messages)

    shared_days = len({message.timestamp.date().isoformat() for message in chat.messages})
    evidence = {
        "chat_name": chat.name,
        "chat_id": chat.chat_id,
        "message_count": len(chat.messages),
        "shared_days": shared_days,
    }

    return [
        Edge(
            source=config.self_node_id,
            target=peer_id,
            relation_type="direct_message",
            metrics={
                "messages": len(outgoing),
                "chars": sum(len(message.text) for message in outgoing),
                "warmth": out_warmth,
                "reciprocity": reciprocity,
                "session_initiation_share": initiation["self_share"],
                "median_response_minutes": reply_metrics["self_response_median_minutes"],
                "responsiveness_score": reply_metrics["self_responsiveness_score"],
                "media_messages": outgoing_media["media_messages"],
                "media_breakdown": outgoing_media["media_breakdown"],
                "rich_media_ratio": outgoing_media["rich_media_ratio"],
            },
            evidence=evidence,
        ),
        Edge(
            source=peer_id,
            target=config.self_node_id,
            relation_type="direct_message",
            metrics={
                "messages": len(incoming),
                "chars": sum(len(message.text) for message in incoming),
                "warmth": in_warmth,
                "reciprocity": reciprocity,
                "session_initiation_share": initiation["peer_share"],
                "median_response_minutes": reply_metrics["peer_response_median_minutes"],
                "responsiveness_score": reply_metrics["peer_responsiveness_score"],
                "media_messages": incoming_media["media_messages"],
                "media_breakdown": incoming_media["media_breakdown"],
                "rich_media_ratio": incoming_media["rich_media_ratio"],
            },
            evidence=evidence,
        ),
    ]


def _analyze_group_chat(chat: Chat, config: AnalyzerConfig) -> List[Edge]:
    message_index = {message.message_id: message for message in chat.messages if message.message_id}
    interactions: DefaultDict[Tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: {"replies": 0.0, "mentions": 0.0, "messages": 0.0, "warmth_sum": 0.0}
    )
    known_names = {
        message.sender_name.strip(): (config.self_node_id if message.is_outgoing else message.sender_id)
        for message in chat.messages
        if message.sender_name.strip()
    }

    for message in chat.messages:
        source_id = config.self_node_id if message.is_outgoing else message.sender_id
        interactions[(source_id, f"group:{chat.chat_id}")]["messages"] += 1
        interactions[(source_id, f"group:{chat.chat_id}")]["warmth_sum"] += _warmth_score([message])

        if message.reply_to_message_id and message.reply_to_message_id in message_index:
            target_message = message_index[message.reply_to_message_id]
            target_id = config.self_node_id if target_message.is_outgoing else target_message.sender_id
            if target_id != source_id:
                interactions[(source_id, target_id)]["replies"] += 1

        for name, target_id in known_names.items():
            if target_id == source_id:
                continue
            if name and f"@{name.lower()}" in message.text.lower():
                interactions[(source_id, target_id)]["mentions"] += 1

    edges: List[Edge] = [
        Edge(
            source=source,
            target=target,
            relation_type="group_interaction",
            metrics={
                "reply_count": values["replies"],
                "mention_count": values["mentions"],
                "message_count": values["messages"],
                "warmth": round(values["warmth_sum"] / max(values["messages"], 1.0), 4),
            },
            evidence={"chat_name": chat.name, "chat_id": chat.chat_id},
        )
        for (source, target), values in interactions.items()
        if target != f"group:{chat.chat_id}"
    ]
    return edges


def _response_metrics(messages: List[Message], max_gap_hours: int) -> Dict[str, Optional[float]]:
    self_deltas: List[float] = []
    peer_deltas: List[float] = []
    max_gap = timedelta(hours=max_gap_hours)

    for previous, current in zip(messages, messages[1:]):
        delta = current.timestamp - previous.timestamp
        if delta <= timedelta(0) or delta > max_gap:
            continue
        minutes = delta.total_seconds() / 60.0
        if previous.is_outgoing and not current.is_outgoing:
            peer_deltas.append(minutes)
        elif not previous.is_outgoing and current.is_outgoing:
            self_deltas.append(minutes)

    return {
        "self_response_median_minutes": _safe_median(self_deltas),
        "peer_response_median_minutes": _safe_median(peer_deltas),
        "self_responsiveness_score": _responsiveness_score(self_deltas),
        "peer_responsiveness_score": _responsiveness_score(peer_deltas),
    }


def _safe_median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(median(values), 2)


def _responsiveness_score(values: List[float]) -> Optional[float]:
    if not values:
        return None
    minutes = median(values)
    return round(1.0 / (1.0 + math.log1p(minutes)), 4)


def _ratio(left: int, right: int) -> float:
    high = max(left, right)
    low = min(left, right)
    if high == 0:
        return 0.0
    return round(low / high, 4)


def _initiation_balance(messages: List[Message]) -> Dict[str, float]:
    self_initiations = 0
    peer_initiations = 0
    previous_timestamp: Optional[datetime] = None

    for message in messages:
        if previous_timestamp is None or message.timestamp - previous_timestamp > timedelta(hours=SESSION_BREAK_HOURS):
            if message.is_outgoing:
                self_initiations += 1
            else:
                peer_initiations += 1
        previous_timestamp = message.timestamp

    total = self_initiations + peer_initiations
    if total == 0:
        return {"self_share": 0.0, "peer_share": 0.0}
    return {
        "self_share": round(self_initiations / total, 4),
        "peer_share": round(peer_initiations / total, 4),
    }


def _warmth_score(messages: Iterable[Message]) -> float:
    warm_hits = 0
    tense_hits = 0
    token_count = 0

    for message in messages:
        tokens = TOKEN_RE.findall(message.text.casefold())
        token_count += len(tokens)
        warm_hits += sum(token in WARM_WORDS["ru"] or token in WARM_WORDS["en"] for token in tokens)
        tense_hits += sum(token in TENSION_WORDS["ru"] or token in TENSION_WORDS["en"] for token in tokens)

    if token_count == 0:
        return 0.0

    raw = (warm_hits - tense_hits) / max(token_count, 1)
    bounded = max(-1.0, min(1.0, raw * 8.0))
    return round((bounded + 1.0) / 2.0, 4)


def _media_metrics(messages: List[Message]) -> Dict[str, object]:
    counts: Dict[str, int] = defaultdict(int)
    media_messages = 0
    rich_media_messages = 0

    for message in messages:
        if not message.media_kind:
            continue
        media_messages += 1
        counts[message.media_kind] += 1
        if message.media_kind in {"photo", "voice", "video", "gif", "sticker", "audio"}:
            rich_media_messages += 1

    return {
        "media_messages": media_messages,
        "media_breakdown": dict(counts),
        "rich_media_ratio": round(rich_media_messages / len(messages), 4) if messages else 0.0,
    }
