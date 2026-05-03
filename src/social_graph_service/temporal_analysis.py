from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import Chat, Edge, GraphResult, Node


ACTIVE_STATUSES = {"active_mutual", "active_asymmetric", "revived", "new_connection"}
CURRENT_TIE_TOP_LIMIT = 25
TOKEN_WINDOW_30_DAYS = 30
TOKEN_WINDOW_28_DAYS = 28
TOKEN_WINDOW_90_DAYS = 90
TOKEN_WINDOW_91_DAYS = 91
TOKEN_WINDOW_180_DAYS = 180
TOKEN_WINDOW_365_DAYS = 365
TOKEN_WINDOW_7_DAYS = 7
SESSION_BREAK_HOURS = 12
DEPTH_MARKERS = (
    "чувств",
    "чувствую",
    "думаю",
    "пережива",
    "важно",
    "лично",
    "искрен",
    "откров",
    "смыс",
    "feel",
    "feeling",
    "think",
    "honest",
    "important",
    "personal",
    "vulnerab",
    "meaning",
)
SUPPORT_MARKERS = (
    "держись",
    "поддерж",
    "если что",
    "рядом",
    "помогу",
    "помочь",
    "береги",
    "не пережива",
    "все будет",
    "с тобой",
    "take care",
    "i'm here",
    "here for you",
    "support",
    "help you",
    "proud of you",
    "you can do it",
)
FORMALITY_MARKERS = (
    "здравствуйте",
    "добрый день",
    "доброе утро",
    "благодарю",
    "прошу",
    "коллеги",
    "уважаем",
    "с уважением",
    "сообщите",
    "подскажите",
    "направляю",
    "просьба",
    "good morning",
    "hello,",
    "regards",
    "please confirm",
    "kindly",
    "dear",
    "let me know",
)


@dataclass
class TemporalConfig:
    self_node_id: str = "self"
    self_label: str = "You"
    as_of_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cadence_days: int = 7
    short_window_days: int = 30
    window_days: int = 90
    prev_window_days: int = 90
    prev_year_window_days: int = 185
    max_response_gap_hours: int = 24


def analyze_temporal(chats: Iterable[Chat], config: TemporalConfig) -> Dict[str, Any]:
    chats = list(chats)
    end_date = config.as_of_date or config.end_date or _max_chat_date(chats) or date.today()
    start_date = config.start_date
    snapshot_now = build_snapshot(chats, end_date, config)

    weekly_dates = []
    if start_date is not None:
        weekly_dates = _weekly_dates(start_date, end_date, config.cadence_days)

    weekly_snapshots: List[Dict[str, Any]] = []
    network_timeseries: List[Dict[str, Any]] = []
    relationship_timeseries: List[Dict[str, Any]] = []
    person_reports: List[Dict[str, Any]] = []
    snapshot_series: List[Dict[str, Any]] = []

    if weekly_dates:
        snapshot_series = [build_snapshot(chats, current_date, config) for current_date in weekly_dates]
        weekly_snapshots = [_compact_weekly_snapshot(snapshot) for snapshot in snapshot_series]
        network_timeseries = [snapshot["network_snapshot"] for snapshot in snapshot_series]
        relationship_timeseries = _build_relationship_timeseries(snapshot_series)
        person_reports = _build_person_reports(relationship_timeseries)

    return {
        "analysis_config": {
            "as_of_date": end_date.isoformat(),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat(),
            "cadence_days": config.cadence_days,
            "short_window_days": config.short_window_days,
            "window_days": config.window_days,
            "prev_window_days": config.prev_window_days,
            "prev_year_window_days": config.prev_year_window_days,
        },
        "snapshot_now": snapshot_now,
        "snapshot_series": snapshot_series,
        "weekly_snapshots": weekly_snapshots,
        "relationship_timeseries": relationship_timeseries,
        "network_timeseries": network_timeseries,
        "person_reports": person_reports,
    }


def build_snapshot(chats: Iterable[Chat], as_of_date: date, config: TemporalConfig) -> Dict[str, Any]:
    chats = list(chats)
    as_of_dt = _as_of_datetime(as_of_date)
    nodes: Dict[str, Node] = {
        config.self_node_id: Node(
            node_id=config.self_node_id,
            label=config.self_label,
            node_type="person",
            metadata={"is_self": True},
        )
    }
    relationships: List[Dict[str, Any]] = []
    edges: List[Edge] = []
    total_messages_until_date = 0

    for chat in chats:
        visible_messages = [message for message in chat.messages if message.timestamp <= as_of_dt]
        if not visible_messages:
            continue
        total_messages_until_date += len(visible_messages)
        if chat.chat_type != "private":
            continue
        peer = _resolve_private_peer(visible_messages, config.self_node_id)
        if peer is None:
            continue
        peer_id, peer_label = peer
        if peer_id == config.self_node_id:
            continue
        nodes.setdefault(
            peer_id,
            Node(node_id=peer_id, label=peer_label, node_type="person", metadata={"chat_type": "private"}),
        )
        relationship = _build_relationship_snapshot(
            chat_id=chat.chat_id,
            chat_name=chat.name,
            peer_id=peer_id,
            peer_label=peer_label,
            messages=visible_messages,
            as_of_date=as_of_date,
            config=config,
        )
        if relationship is None:
            continue
        relationships.append(relationship)
        edges.extend(_relationship_to_edges(relationship, config))

    relationships.sort(key=lambda item: item["pair"]["tie_strength_score"], reverse=True)
    graph_result = GraphResult(
        nodes=list(nodes.values()),
        edges=edges,
        summary={
            "chat_count": len(relationships),
            "message_count": total_messages_until_date,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "as_of_date": as_of_date.isoformat(),
        },
    )
    network_snapshot = _build_network_snapshot(relationships, as_of_date)
    return {
        "as_of_date": as_of_date.isoformat(),
        "relationships": relationships,
        "network_snapshot": network_snapshot,
        "graph_result": graph_result,
        "top_relationships": relationships[:CURRENT_TIE_TOP_LIMIT],
    }


def _build_relationship_snapshot(
    *,
    chat_id: str,
    chat_name: str,
    peer_id: str,
    peer_label: str,
    messages: List[Any],
    as_of_date: date,
    config: TemporalConfig,
) -> Optional[Dict[str, Any]]:
    outbound_messages = [message for message in messages if message.is_outgoing]
    inbound_messages = [message for message in messages if not message.is_outgoing]
    if not outbound_messages and not inbound_messages:
        return None

    outbound = _directional_metrics(outbound_messages, messages, as_of_date, config)
    inbound = _directional_metrics(inbound_messages, messages, as_of_date, config)
    pair = _pair_metrics(messages, outbound, inbound, as_of_date, config)
    drivers = _relationship_drivers(outbound, inbound, pair)

    return {
        "peer_id": peer_id,
        "peer_label": peer_label,
        "chat_id": chat_id,
        "chat_name": chat_name,
        "as_of_date": as_of_date.isoformat(),
        "window_days": config.window_days,
        "outbound": outbound,
        "inbound": inbound,
        "pair": pair,
        "drivers": drivers,
    }


def _directional_metrics(
    direction_messages: List[Any],
    all_messages: List[Any],
    as_of_date: date,
    config: TemporalConfig,
) -> Dict[str, Any]:
    total_chars = 0
    counts: Counter[str] = Counter()
    weighted_messages = 0.0
    weighted_7d = 0.0
    weighted_28d = 0.0
    weighted_chars = 0.0
    weighted_30d = 0.0
    weighted_90d = 0.0
    count_7d = 0
    count_28d = 0
    count_30d = 0
    count_91d = 0
    count_90d = 0
    count_prev_90d = 0
    count_prev_365d = 0
    chars_90d = 0
    long_messages_90d = 0
    meaningful_messages_90d = 0
    question_messages_90d = 0
    short_messages_90d = 0
    depth_marker_messages_90d = 0
    support_marker_messages_90d = 0
    formal_marker_messages_90d = 0
    warmth_values: List[float] = []
    warmth_values_7d: List[float] = []
    warmth_values_28d: List[float] = []
    warmth_values_91d: List[float] = []
    tension_values: List[float] = []
    tension_values_7d: List[float] = []
    tension_values_28d: List[float] = []
    tension_values_91d: List[float] = []
    support_values: List[float] = []
    support_values_7d: List[float] = []
    support_values_28d: List[float] = []
    support_values_91d: List[float] = []
    formality_values: List[float] = []
    formality_values_7d: List[float] = []
    formality_values_28d: List[float] = []
    formality_values_91d: List[float] = []
    media_counts: Counter[str] = Counter()
    last_message_at: Optional[str] = None

    for message in direction_messages:
        age_days = _age_days(as_of_date, message.timestamp)
        if age_days < 0:
            continue
        weight = _time_weight(age_days)
        text_length = len(message.text or "")
        total_chars += text_length
        weighted_messages += weight
        weighted_chars += text_length * weight
        warmth, tension, support, formality = _tone_scores(message.text or "")
        warmth_values.append(warmth)
        tension_values.append(tension)
        support_values.append(support)
        formality_values.append(formality)
        if age_days <= TOKEN_WINDOW_7_DAYS:
            count_7d += 1
            weighted_7d += weight
            warmth_values_7d.append(warmth)
            tension_values_7d.append(tension)
            support_values_7d.append(support)
            formality_values_7d.append(formality)
        if age_days <= TOKEN_WINDOW_28_DAYS:
            count_28d += 1
            weighted_28d += weight
            warmth_values_28d.append(warmth)
            tension_values_28d.append(tension)
            support_values_28d.append(support)
            formality_values_28d.append(formality)
        if age_days <= TOKEN_WINDOW_30_DAYS:
            count_30d += 1
            weighted_30d += weight
        if age_days <= TOKEN_WINDOW_91_DAYS:
            count_91d += 1
            warmth_values_91d.append(warmth)
            tension_values_91d.append(tension)
            support_values_91d.append(support)
            formality_values_91d.append(formality)
        if age_days <= config.window_days:
            count_90d += 1
            weighted_90d += weight
            chars_90d += text_length
            if text_length >= 180:
                long_messages_90d += 1
            if text_length >= 48:
                meaningful_messages_90d += 1
            if text_length <= 8 and (message.text or "").casefold().strip():
                short_messages_90d += 1
            if "?" in (message.text or ""):
                question_messages_90d += 1
            if _contains_any(message.text or "", DEPTH_MARKERS):
                depth_marker_messages_90d += 1
            if _contains_any(message.text or "", SUPPORT_MARKERS):
                support_marker_messages_90d += 1
            if _contains_any(message.text or "", FORMALITY_MARKERS):
                formal_marker_messages_90d += 1
        elif age_days <= config.window_days + config.prev_window_days:
            count_prev_90d += 1
        elif age_days <= TOKEN_WINDOW_365_DAYS:
            count_prev_365d += 1
        if message.media_kind:
            counts["media_messages"] += 1
            media_counts[message.media_kind] += 1
        last_message_at = max(last_message_at or "", _isoformat(message.timestamp))

    reply_metrics = _response_metrics(all_messages, direction_messages, as_of_date, config.max_response_gap_hours)
    initiation_share = _initiation_share(all_messages, direction_messages, as_of_date)
    media_messages = int(counts.get("media_messages", 0))
    rich_media_messages = sum(media_counts[kind] for kind in {"photo", "voice", "video", "gif", "sticker", "audio"} if kind in media_counts)
    avg_chars_90d = round(chars_90d / count_90d, 2) if count_90d else 0.0
    meaningful_ratio_90d = round(meaningful_messages_90d / count_90d, 4) if count_90d else 0.0
    long_ratio_90d = round(long_messages_90d / count_90d, 4) if count_90d else 0.0
    question_ratio_90d = round(question_messages_90d / count_90d, 4) if count_90d else 0.0
    short_ratio_90d = round(short_messages_90d / count_90d, 4) if count_90d else 0.0
    depth_marker_ratio_90d = round(depth_marker_messages_90d / count_90d, 4) if count_90d else 0.0
    support_marker_ratio_90d = round(support_marker_messages_90d / count_90d, 4) if count_90d else 0.0
    formal_marker_ratio_90d = round(formal_marker_messages_90d / count_90d, 4) if count_90d else 0.0
    avg_chars_score = min(1.0, avg_chars_90d / 220.0) if count_90d else 0.0
    depth_score = round(
        min(
            1.0,
            avg_chars_score * 0.24
            + meaningful_ratio_90d * 0.22
            + long_ratio_90d * 0.20
            + question_ratio_90d * 0.14
            + depth_marker_ratio_90d * 0.20,
        ),
        4,
    )
    engagement_signal = round(
        min(
            1.0,
            float(initiation_share) * 0.42
            + question_ratio_90d * 0.18
            + meaningful_ratio_90d * 0.20
            + (reply_metrics["responsiveness_score"] or 0.0) * 0.20,
        ),
        4,
    )
    support_mean = round(sum(support_values) / len(support_values), 4) if support_values else 0.0
    formality_mean = round(sum(formality_values) / len(formality_values), 4) if formality_values else 0.0
    support_score = round(
        min(
            1.0,
            support_marker_ratio_90d * 3.2
            + support_mean * 1.4
            + depth_marker_ratio_90d * 0.25
            + max(0.0, (round(sum(warmth_values) / len(warmth_values), 4) if warmth_values else 0.0) - 0.5) * 0.35,
        ),
        4,
    )
    formality_score = round(
        min(
            1.0,
            formal_marker_ratio_90d * 2.8
            + formality_mean * 1.2
            + short_ratio_90d * 0.15,
        ),
        4,
    )
    warmth_index_7d = _directional_warmth_index(
        warmth=round(sum(warmth_values_7d) / len(warmth_values_7d), 4) if warmth_values_7d else 0.0,
        support=round(sum(support_values_7d) / len(support_values_7d), 4) if support_values_7d else 0.0,
        tension=round(sum(tension_values_7d) / len(tension_values_7d), 4) if tension_values_7d else 0.0,
        formality=round(sum(formality_values_7d) / len(formality_values_7d), 4) if formality_values_7d else 0.0,
        depth=0.0,
        responsiveness=0.0,
    )
    warmth_index_28d = _directional_warmth_index(
        warmth=round(sum(warmth_values_28d) / len(warmth_values_28d), 4) if warmth_values_28d else 0.0,
        support=round(sum(support_values_28d) / len(support_values_28d), 4) if support_values_28d else 0.0,
        tension=round(sum(tension_values_28d) / len(tension_values_28d), 4) if tension_values_28d else 0.0,
        formality=round(sum(formality_values_28d) / len(formality_values_28d), 4) if formality_values_28d else 0.0,
        depth=0.0,
        responsiveness=0.0,
    )
    warmth_index_91d = _directional_warmth_index(
        warmth=round(sum(warmth_values_91d) / len(warmth_values_91d), 4) if warmth_values_91d else 0.0,
        support=round(sum(support_values_91d) / len(support_values_91d), 4) if support_values_91d else 0.0,
        tension=round(sum(tension_values_91d) / len(tension_values_91d), 4) if tension_values_91d else 0.0,
        formality=round(sum(formality_values_91d) / len(formality_values_91d), 4) if formality_values_91d else 0.0,
        depth=0.0,
        responsiveness=0.0,
    )
    warmth_index = _directional_warmth_index(
        warmth=round(sum(warmth_values) / len(warmth_values), 4) if warmth_values else 0.0,
        support=support_score,
        tension=round(sum(tension_values) / len(tension_values), 4) if tension_values else 0.0,
        formality=formality_score,
        depth=depth_score,
        responsiveness=reply_metrics["responsiveness_score"] or 0.0,
    )

    return {
        "messages_count_7d": count_7d,
        "messages_count_28d": count_28d,
        "messages_count": count_90d,
        "messages_count_30d": count_30d,
        "messages_count_91d": count_91d,
        "messages_count_90d": count_90d,
        "messages_count_prev_90d": count_prev_90d,
        "messages_count_prev_365d": count_prev_365d,
        "chars_count": total_chars,
        "weighted_messages": round(weighted_messages, 4),
        "weighted_messages_7d": round(weighted_7d, 4),
        "weighted_messages_28d": round(weighted_28d, 4),
        "weighted_messages_30d": round(weighted_30d, 4),
        "weighted_messages_90d": round(weighted_90d, 4),
        "weighted_chars": round(weighted_chars, 4),
        "warmth_score_7d": round(sum(warmth_values_7d) / len(warmth_values_7d), 4) if warmth_values_7d else 0.0,
        "warmth_score_28d": round(sum(warmth_values_28d) / len(warmth_values_28d), 4) if warmth_values_28d else 0.0,
        "warmth_score_91d": round(sum(warmth_values_91d) / len(warmth_values_91d), 4) if warmth_values_91d else 0.0,
        "warmth_score": round(sum(warmth_values) / len(warmth_values), 4) if warmth_values else 0.0,
        "tension_score": round(sum(tension_values) / len(tension_values), 4) if tension_values else 0.0,
        "support_score_7d": round(sum(support_values_7d) / len(support_values_7d), 4) if support_values_7d else 0.0,
        "support_score_28d": round(sum(support_values_28d) / len(support_values_28d), 4) if support_values_28d else 0.0,
        "support_score_91d": round(sum(support_values_91d) / len(support_values_91d), 4) if support_values_91d else 0.0,
        "support_score": round(sum(support_values) / len(support_values), 4) if support_values else 0.0,
        "formality_score_7d": round(sum(formality_values_7d) / len(formality_values_7d), 4) if formality_values_7d else 0.0,
        "formality_score_28d": round(sum(formality_values_28d) / len(formality_values_28d), 4) if formality_values_28d else 0.0,
        "formality_score_91d": round(sum(formality_values_91d) / len(formality_values_91d), 4) if formality_values_91d else 0.0,
        "formality_score": round(sum(formality_values) / len(formality_values), 4) if formality_values else 0.0,
        "median_response_minutes": reply_metrics["median_response_minutes"],
        "responsiveness_score": reply_metrics["responsiveness_score"],
        "session_initiation_share": initiation_share,
        "avg_chars_90d": avg_chars_90d,
        "meaningful_ratio_90d": meaningful_ratio_90d,
        "long_message_ratio_90d": long_ratio_90d,
        "question_ratio_90d": question_ratio_90d,
        "short_message_ratio_90d": short_ratio_90d,
        "depth_marker_ratio_90d": depth_marker_ratio_90d,
        "support_marker_ratio_90d": support_marker_ratio_90d,
        "formal_marker_ratio_90d": formal_marker_ratio_90d,
        "depth_score": depth_score,
        "engagement_signal": engagement_signal,
        "support_score_density": support_mean,
        "formality_score_density": formality_mean,
        "support_score": support_score,
        "formality_score": formality_score,
        "warmth_index_7d": warmth_index_7d,
        "warmth_index_28d": warmth_index_28d,
        "warmth_index_91d": warmth_index_91d,
        "warmth_index": warmth_index,
        "media_messages": media_messages,
        "media_breakdown": dict(media_counts),
        "rich_media_ratio": round(rich_media_messages / max(len(direction_messages), 1), 4) if direction_messages else 0.0,
        "last_message_at": last_message_at,
    }


def _pair_metrics(
    all_messages: List[Any],
    outbound: Dict[str, Any],
    inbound: Dict[str, Any],
    as_of_date: date,
    config: TemporalConfig,
) -> Dict[str, Any]:
    messages_total_7d = int(outbound["messages_count_7d"]) + int(inbound["messages_count_7d"])
    messages_total_28d = int(outbound["messages_count_28d"]) + int(inbound["messages_count_28d"])
    messages_total_91d = int(outbound["messages_count_91d"]) + int(inbound["messages_count_91d"])
    messages_total = int(outbound["messages_count_90d"]) + int(inbound["messages_count_90d"])
    weighted_messages_total = round(float(outbound["weighted_messages"]) + float(inbound["weighted_messages"]), 4)
    reciprocity = _ratio(int(outbound["messages_count_90d"]), int(inbound["messages_count_90d"]))
    mutual_warmth_7d = round((float(outbound["warmth_score_7d"]) + float(inbound["warmth_score_7d"])) / 2.0, 4)
    mutual_warmth_28d = round((float(outbound["warmth_score_28d"]) + float(inbound["warmth_score_28d"])) / 2.0, 4)
    mutual_warmth_91d = round((float(outbound["warmth_score_91d"]) + float(inbound["warmth_score_91d"])) / 2.0, 4)
    mutual_warmth = round((float(outbound["warmth_score"]) + float(inbound["warmth_score"])) / 2.0, 4)
    mutual_tension = round((float(outbound["tension_score"]) + float(inbound["tension_score"])) / 2.0, 4)
    mutual_support = round((float(outbound["support_score"]) + float(inbound["support_score"])) / 2.0, 4)
    mutual_formality = round((float(outbound["formality_score"]) + float(inbound["formality_score"])) / 2.0, 4)
    mutual_responsiveness = _mean_defined(
        [outbound.get("responsiveness_score"), inbound.get("responsiveness_score")]
    )
    initiation_balance = round(
        1.0 - abs(float(outbound["session_initiation_share"]) - float(inbound["session_initiation_share"])),
        4,
    )
    continuity_score = _continuity_score(all_messages, as_of_date, config.window_days)
    recency_score = _recency_score(outbound, inbound)
    volume_score = round(min(1.0, math.log1p(max(weighted_messages_total, 0.0)) / 6.0), 4)
    stability_score = round(
        min(
            1.0,
            continuity_score * 0.62
            + recency_score * 0.23
        ),
        4,
    )
    if all_messages:
        active_days = {
            message.timestamp.date()
            for message in all_messages
            if 0 <= _age_days(as_of_date, message.timestamp) <= config.window_days
        }
        active_day_score = min(1.0, len(active_days) / 18.0)
        stability_score = round(min(1.0, stability_score + active_day_score * 0.15), 4)
    depth_score = round(
        min(
            1.0,
            (float(outbound["depth_score"]) + float(inbound["depth_score"])) / 2.0 * 0.82
            + initiation_balance * 0.10
            + min(1.0, reciprocity + 0.1) * 0.08,
        ),
        4,
    )
    total_messages_90d = max(1, messages_total)
    outbound_share = int(outbound["messages_count_90d"]) / total_messages_90d
    inbound_share = int(inbound["messages_count_90d"]) / total_messages_90d
    engagement_out = round(
        min(
            1.0,
            outbound_share * 0.34
            + float(outbound["session_initiation_share"]) * 0.28
            + float(outbound["engagement_signal"]) * 0.23
            + (float(outbound.get("responsiveness_score") or 0.0)) * 0.15,
        ),
        4,
    )
    engagement_in = round(
        min(
            1.0,
            inbound_share * 0.34
            + float(inbound["session_initiation_share"]) * 0.28
            + float(inbound["engagement_signal"]) * 0.23
            + (float(inbound.get("responsiveness_score") or 0.0)) * 0.15,
        ),
        4,
    )
    warmth_index_out = float(outbound["warmth_index"])
    warmth_index_in = float(inbound["warmth_index"])
    warmth_index_7d = round((float(outbound["warmth_index_7d"]) + float(inbound["warmth_index_7d"])) / 2.0, 4)
    warmth_index_28d = round((float(outbound["warmth_index_28d"]) + float(inbound["warmth_index_28d"])) / 2.0, 4)
    warmth_index_91d = round((float(outbound["warmth_index_91d"]) + float(inbound["warmth_index_91d"])) / 2.0, 4)
    warmth_index = _pair_warmth_index(warmth_index_out, warmth_index_in)
    bond_index_out = _directional_bond_index(
        warmth_index=warmth_index_out,
        engagement=engagement_out,
        responsiveness=float(outbound.get("responsiveness_score") or 0.0),
        depth=float(outbound["depth_score"]),
        support=float(outbound["support_score"]),
        formality=float(outbound["formality_score"]),
        reciprocity=reciprocity,
        stability=stability_score,
    )
    bond_index_in = _directional_bond_index(
        warmth_index=warmth_index_in,
        engagement=engagement_in,
        responsiveness=float(inbound.get("responsiveness_score") or 0.0),
        depth=float(inbound["depth_score"]),
        support=float(inbound["support_score"]),
        formality=float(inbound["formality_score"]),
        reciprocity=reciprocity,
        stability=stability_score,
    )
    bond_index = _pair_bond_index(bond_index_out, bond_index_in, reciprocity, stability_score)
    integrated_color_score = _integrated_color_score(warmth_index, bond_index)
    response_coverage = 0.0
    if outbound.get("responsiveness_score") is not None:
        response_coverage += 0.5
    if inbound.get("responsiveness_score") is not None:
        response_coverage += 0.5
    message_confidence = min(1.0, math.log1p(messages_total) / math.log1p(160.0)) if messages_total > 0 else 0.0
    confidence_score = round(
        min(
            1.0,
            message_confidence * 0.45
            + continuity_score * 0.18
            + min(1.0, reciprocity + 0.08) * 0.12
            + depth_score * 0.10
            + response_coverage * 0.10
            + min(1.0, weighted_messages_total / 120.0) * 0.05,
        ),
        4,
    )
    closeness_score = round(
        reciprocity * 0.30
        + mutual_warmth * 0.20
        + mutual_responsiveness * 0.15
        + initiation_balance * 0.15
        + continuity_score * 0.10
        + recency_score * 0.10,
        4,
    )
    evidence_score = round(min(1.0, messages_total / 500.0) ** 0.4, 4) if messages_total > 0 else 0.0
    tie_strength_score = round(closeness_score * evidence_score, 4)
    last_contact_at = _latest_defined([outbound.get("last_message_at"), inbound.get("last_message_at")])
    silence_gap_days = _silence_gap_days(as_of_date, last_contact_at)

    current_30d = int(outbound["messages_count_30d"]) + int(inbound["messages_count_30d"])
    current_90d = messages_total
    prev_90d = int(outbound["messages_count_prev_90d"]) + int(inbound["messages_count_prev_90d"])
    prev_365d = int(outbound["messages_count_prev_365d"]) + int(inbound["messages_count_prev_365d"])
    status = _classify_status(
        current_30d=current_30d,
        current_90d=current_90d,
        prev_90d=prev_90d,
        prev_365d=prev_365d,
        reciprocity=reciprocity,
        closeness_score=closeness_score,
        silence_gap_days=silence_gap_days,
    )

    return {
        "messages_total_7d": messages_total_7d,
        "messages_total_28d": messages_total_28d,
        "messages_total_91d": messages_total_91d,
        "messages_total": messages_total,
        "messages_total_30d": current_30d,
        "messages_total_90d": current_90d,
        "messages_total_prev_90d": prev_90d,
        "messages_total_prev_365d": prev_365d,
        "weighted_messages_total": weighted_messages_total,
        "reciprocity": reciprocity,
        "mutual_warmth_7d": mutual_warmth_7d,
        "mutual_warmth_28d": mutual_warmth_28d,
        "mutual_warmth_91d": mutual_warmth_91d,
        "mutual_warmth": mutual_warmth,
        "mutual_tension": mutual_tension,
        "mutual_support": mutual_support,
        "mutual_formality": mutual_formality,
        "mutual_responsiveness": mutual_responsiveness,
        "warmth_index_out": warmth_index_out,
        "warmth_index_in": warmth_index_in,
        "warmth_index_7d": warmth_index_7d,
        "warmth_index_28d": warmth_index_28d,
        "warmth_index_91d": warmth_index_91d,
        "warmth_index": warmth_index,
        "initiation_balance": initiation_balance,
        "continuity_score": continuity_score,
        "stability_score": stability_score,
        "depth_score": depth_score,
        "engagement_out": engagement_out,
        "engagement_in": engagement_in,
        "bond_index_out": bond_index_out,
        "bond_index_in": bond_index_in,
        "bond_index": bond_index,
        "integrated_color_score": integrated_color_score,
        "confidence_score": confidence_score,
        "recency_score": recency_score,
        "volume_score": volume_score,
        "closeness_score": closeness_score,
        "evidence_score": evidence_score,
        "tie_strength_score": tie_strength_score,
        "last_contact_at": last_contact_at,
        "silence_gap_days": silence_gap_days,
        "status": status,
    }


def _build_network_snapshot(relationships: List[Dict[str, Any]], as_of_date: date) -> Dict[str, Any]:
    status_counts = Counter(relationship["pair"]["status"] for relationship in relationships)
    active_relationships = sum(1 for relationship in relationships if relationship["pair"]["status"] in ACTIVE_STATUSES)
    mean_closeness = _mean_defined([relationship["pair"]["closeness_score"] for relationship in relationships])
    mean_reciprocity = _mean_defined([relationship["pair"]["reciprocity"] for relationship in relationships])
    mean_mutual_warmth = _mean_defined([relationship["pair"]["mutual_warmth"] for relationship in relationships])
    mean_warmth_index = _mean_defined([relationship["pair"]["warmth_index"] for relationship in relationships])
    mean_bond_index = _mean_defined([relationship["pair"]["bond_index"] for relationship in relationships])
    mean_mutual_responsiveness = _mean_defined(
        [relationship["pair"]["mutual_responsiveness"] for relationship in relationships]
    )

    top_relationship_ids = [relationship["peer_id"] for relationship in relationships[:CURRENT_TIE_TOP_LIMIT]]
    return {
        "as_of_date": as_of_date.isoformat(),
        "relationship_count": len(relationships),
        "active_relationships": active_relationships,
        "new_connections": status_counts.get("new_connection", 0),
        "revived_connections": status_counts.get("revived", 0),
        "fading_connections": status_counts.get("fading", 0),
        "dormant_connections": status_counts.get("dormant", 0),
        "lost_connections": status_counts.get("lost_connection", 0),
        "active_mutual_relationships": status_counts.get("active_mutual", 0),
        "active_asymmetric_relationships": status_counts.get("active_asymmetric", 0),
        "mean_closeness": mean_closeness,
        "mean_reciprocity": mean_reciprocity,
        "mean_mutual_warmth": mean_mutual_warmth,
        "mean_warmth_index": mean_warmth_index,
        "mean_bond_index": mean_bond_index,
        "mean_mutual_responsiveness": mean_mutual_responsiveness,
        "top_relationships": top_relationship_ids,
        "status_counts": dict(status_counts),
    }


def _relationship_to_edges(relationship: Dict[str, Any], config: TemporalConfig) -> List[Edge]:
    peer_id = relationship["peer_id"]
    evidence = {
        "chat_id": relationship["chat_id"],
        "chat_name": relationship["chat_name"],
        "as_of_date": relationship["as_of_date"],
    }
    pair = relationship["pair"]
    outbound = relationship["outbound"]
    inbound = relationship["inbound"]
    return [
        Edge(
            source=config.self_node_id,
            target=peer_id,
            relation_type="direct_message",
            metrics={
                "messages": outbound["messages_count_90d"],
                "weighted_messages": outbound["weighted_messages"],
                "warmth": outbound["warmth_score"],
                "tension": outbound["tension_score"],
                "reciprocity": pair["reciprocity"],
                "session_initiation_share": outbound["session_initiation_share"],
                "median_response_minutes": outbound["median_response_minutes"],
                "responsiveness_score": outbound["responsiveness_score"],
                "media_messages": outbound["media_messages"],
                "media_breakdown": outbound["media_breakdown"],
                "rich_media_ratio": outbound["rich_media_ratio"],
                "closeness_score": pair["closeness_score"],
                "tie_strength": pair["tie_strength_score"],
                "status": pair["status"],
            },
            evidence=evidence,
        ),
        Edge(
            source=peer_id,
            target=config.self_node_id,
            relation_type="direct_message",
            metrics={
                "messages": inbound["messages_count_90d"],
                "weighted_messages": inbound["weighted_messages"],
                "warmth": inbound["warmth_score"],
                "tension": inbound["tension_score"],
                "reciprocity": pair["reciprocity"],
                "session_initiation_share": inbound["session_initiation_share"],
                "median_response_minutes": inbound["median_response_minutes"],
                "responsiveness_score": inbound["responsiveness_score"],
                "media_messages": inbound["media_messages"],
                "media_breakdown": inbound["media_breakdown"],
                "rich_media_ratio": inbound["rich_media_ratio"],
                "closeness_score": pair["closeness_score"],
                "tie_strength": pair["tie_strength_score"],
                "status": pair["status"],
            },
            evidence=evidence,
        ),
    ]


def _build_relationship_timeseries(snapshot_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_peer: Dict[str, Dict[str, Any]] = {}
    for snapshot in snapshot_series:
        snapshot_date = snapshot["as_of_date"]
        for relationship in snapshot["relationships"]:
            entry = by_peer.setdefault(
                relationship["peer_id"],
                {
                    "peer_id": relationship["peer_id"],
                    "peer_label": relationship["peer_label"],
                    "chat_id": relationship["chat_id"],
                    "chat_name": relationship["chat_name"],
                    "snapshots": [],
                },
            )
            pair = relationship["pair"]
            outbound = relationship["outbound"]
            inbound = relationship["inbound"]
            entry["snapshots"].append(
                {
                    "as_of_date": snapshot_date,
                    "closeness_score": pair["closeness_score"],
                    "tie_strength_score": pair["tie_strength_score"],
                    "warmth_out": outbound["warmth_score"],
                    "warmth_in": inbound["warmth_score"],
                    "warmth_out_7d": outbound["warmth_score_7d"],
                    "warmth_in_7d": inbound["warmth_score_7d"],
                    "warmth_out_28d": outbound["warmth_score_28d"],
                    "warmth_in_28d": inbound["warmth_score_28d"],
                    "warmth_out_91d": outbound["warmth_score_91d"],
                    "warmth_in_91d": inbound["warmth_score_91d"],
                    "tension_out": outbound["tension_score"],
                    "tension_in": inbound["tension_score"],
                    "support_out": outbound["support_score"],
                    "support_in": inbound["support_score"],
                    "formality_out": outbound["formality_score"],
                    "formality_in": inbound["formality_score"],
                    "warmth_index_out": pair["warmth_index_out"],
                    "warmth_index_in": pair["warmth_index_in"],
                    "warmth_index_7d": pair["warmth_index_7d"],
                    "warmth_index_28d": pair["warmth_index_28d"],
                    "warmth_index_91d": pair["warmth_index_91d"],
                    "warmth_index": pair["warmth_index"],
                    "depth_out": outbound["depth_score"],
                    "depth_in": inbound["depth_score"],
                    "engagement_out": pair["engagement_out"],
                    "engagement_in": pair["engagement_in"],
                    "responsiveness_out": outbound.get("responsiveness_score") or 0.0,
                    "responsiveness_in": inbound.get("responsiveness_score") or 0.0,
                    "stability_score": pair["stability_score"],
                    "depth_score": pair["depth_score"],
                    "bond_index_out": pair["bond_index_out"],
                    "bond_index_in": pair["bond_index_in"],
                    "bond_index": pair["bond_index"],
                    "mutual_tension": pair["mutual_tension"],
                    "mutual_support": pair["mutual_support"],
                    "mutual_formality": pair["mutual_formality"],
                    "integrated_color_score": pair["integrated_color_score"],
                    "confidence_score": pair["confidence_score"],
                    "reciprocity": pair["reciprocity"],
                    "status": pair["status"],
                    "messages_total_7d": pair["messages_total_7d"],
                    "messages_total_28d": pair["messages_total_28d"],
                    "messages_total_91d": pair["messages_total_91d"],
                    "messages_total_90d": pair["messages_total_90d"],
                    "last_contact_at": pair["last_contact_at"],
                }
            )

    for entry in by_peer.values():
        entry["snapshots"].sort(key=lambda item: item["as_of_date"])
    return sorted(by_peer.values(), key=lambda item: item["snapshots"][-1]["tie_strength_score"], reverse=True)


def _build_person_reports(relationship_timeseries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reports: List[Dict[str, Any]] = []
    for entry in relationship_timeseries:
        snapshots = entry["snapshots"]
        if not snapshots:
            continue
        current = snapshots[-1]
        previous = snapshots[-2] if len(snapshots) >= 2 else None
        yearly_reference = snapshots[-53] if len(snapshots) >= 53 else None
        report = {
            "peer_id": entry["peer_id"],
            "peer_label": entry["peer_label"],
            "chat_id": entry["chat_id"],
            "chat_name": entry["chat_name"],
            "current_snapshot": current,
            "delta_vs_previous_week": _snapshot_delta(current, previous),
            "delta_vs_previous_year": _snapshot_delta(current, yearly_reference),
            "timeline_status_changes": _timeline_status_changes(snapshots),
        }
        report["trend"] = _classify_trend(report["delta_vs_previous_week"])
        reports.append(report)
    reports.sort(
        key=lambda item: item["current_snapshot"]["tie_strength_score"],
        reverse=True,
    )
    return reports


def _snapshot_delta(current: Dict[str, Any], baseline: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if baseline is None:
        return None
    return {
        "from_date": baseline["as_of_date"],
        "to_date": current["as_of_date"],
        "closeness_delta": round(float(current["closeness_score"]) - float(baseline["closeness_score"]), 4),
        "tie_strength_delta": round(
            float(current["tie_strength_score"]) - float(baseline["tie_strength_score"]),
            4,
        ),
        "warmth_out_delta": round(float(current["warmth_out"]) - float(baseline["warmth_out"]), 4),
        "warmth_in_delta": round(float(current["warmth_in"]) - float(baseline["warmth_in"]), 4),
        "warmth_index_delta": round(float(current.get("warmth_index", 0.0)) - float(baseline.get("warmth_index", 0.0)), 4),
        "bond_index_delta": round(float(current.get("bond_index", 0.0)) - float(baseline.get("bond_index", 0.0)), 4),
        "stability_delta": round(float(current.get("stability_score", 0.0)) - float(baseline.get("stability_score", 0.0)), 4),
        "depth_delta": round(float(current.get("depth_score", 0.0)) - float(baseline.get("depth_score", 0.0)), 4),
        "mutual_tension_delta": round(float(current.get("mutual_tension", 0.0)) - float(baseline.get("mutual_tension", 0.0)), 4),
        "reciprocity_delta": round(float(current["reciprocity"]) - float(baseline["reciprocity"]), 4),
        "messages_total_90d_delta": int(current["messages_total_90d"]) - int(baseline["messages_total_90d"]),
        "status_changed": current["status"] != baseline["status"],
        "previous_status": baseline["status"],
        "current_status": current["status"],
    }


def _timeline_status_changes(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    previous_status: Optional[str] = None
    for snapshot in snapshots:
        current_status = snapshot["status"]
        if previous_status is None or previous_status == current_status:
            previous_status = current_status
            continue
        changes.append(
            {
                "as_of_date": snapshot["as_of_date"],
                "from_status": previous_status,
                "to_status": current_status,
            }
        )
        previous_status = current_status
    return changes


def _classify_trend(delta: Optional[Dict[str, Any]]) -> str:
    if delta is None:
        return "unknown"
    closeness_delta = float(delta["closeness_delta"])
    if closeness_delta >= 0.05:
        return "strengthening"
    if closeness_delta <= -0.05:
        return "weakening"
    return "stable"


def _compact_weekly_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    network_snapshot = dict(snapshot["network_snapshot"])
    network_snapshot["top_relationship_preview"] = [
        {
            "peer_id": relationship["peer_id"],
            "peer_label": relationship["peer_label"],
            "tie_strength_score": relationship["pair"]["tie_strength_score"],
            "status": relationship["pair"]["status"],
        }
        for relationship in snapshot["top_relationships"][:10]
    ]
    return network_snapshot


def _classify_status(
    *,
    current_30d: int,
    current_90d: int,
    prev_90d: int,
    prev_365d: int,
    reciprocity: float,
    closeness_score: float,
    silence_gap_days: Optional[int],
) -> str:
    if current_90d <= 2:
        if prev_90d >= 15:
            return "lost_connection"
        if prev_365d >= 15:
            return "dormant"
        return "dormant"
    if current_30d >= 5 and prev_90d <= 2 and prev_365d <= 5:
        return "new_connection"
    if current_30d >= 5 and prev_90d <= 2 and prev_365d > 5:
        return "revived"
    if prev_90d >= 10 and current_90d < prev_90d * 0.4:
        return "fading"
    if current_30d == 0 and silence_gap_days is not None and silence_gap_days > 30:
        return "dormant"
    if reciprocity >= 0.6 and closeness_score >= 0.45 and current_30d > 0:
        return "active_mutual"
    return "active_asymmetric"


def _relationship_drivers(
    outbound: Dict[str, Any],
    inbound: Dict[str, Any],
    pair: Dict[str, Any],
) -> List[str]:
    drivers: List[str] = []
    total_90d = pair["messages_total_90d"]
    prev_90d = pair["messages_total_prev_90d"]
    if total_90d > prev_90d * 1.3 and total_90d - prev_90d >= 10:
        drivers.append("more frequent contact")
    elif prev_90d > 0 and total_90d < prev_90d * 0.7:
        drivers.append("contact fading")

    out_response = outbound.get("median_response_minutes")
    in_response = inbound.get("median_response_minutes")
    if isinstance(out_response, (int, float)) and isinstance(in_response, (int, float)):
        if out_response < in_response * 0.7:
            drivers.append("you respond faster")
        elif in_response < out_response * 0.7:
            drivers.append("peer responds faster")

    if outbound["warmth_score"] > inbound["warmth_score"] + 0.07:
        drivers.append("warmer outbound tone")
    elif inbound["warmth_score"] > outbound["warmth_score"] + 0.07:
        drivers.append("warmer inbound tone")

    if pair["reciprocity"] < 0.45:
        drivers.append("asymmetric exchange")
    if not drivers:
        drivers.append("stable interaction pattern")
    return drivers


def _response_metrics(
    all_messages: List[Any],
    direction_messages: List[Any],
    as_of_date: date,
    max_gap_hours: int,
) -> Dict[str, Optional[float]]:
    direction_message_ids = {message.message_id for message in direction_messages}
    deltas: List[float] = []
    max_gap = timedelta(hours=max_gap_hours)
    as_of_dt = _as_of_datetime(as_of_date)
    window_start = as_of_dt - timedelta(days=TOKEN_WINDOW_90_DAYS)
    visible_messages = [message for message in all_messages if window_start <= message.timestamp <= as_of_dt]
    for previous, current in zip(visible_messages, visible_messages[1:]):
        delta = current.timestamp - previous.timestamp
        if delta <= timedelta(0) or delta > max_gap:
            continue
        if current.message_id not in direction_message_ids:
            continue
        if previous.is_outgoing == current.is_outgoing:
            continue
        deltas.append(delta.total_seconds() / 60.0)
    if not deltas:
        return {"median_response_minutes": None, "responsiveness_score": None}
    median_minutes = round(median(deltas), 2)
    responsiveness_score = round(1.0 / (1.0 + math.log1p(median_minutes)), 4)
    return {"median_response_minutes": median_minutes, "responsiveness_score": responsiveness_score}


def _initiation_share(all_messages: List[Any], direction_messages: List[Any], as_of_date: date) -> float:
    direction_message_ids = {message.message_id for message in direction_messages}
    as_of_dt = _as_of_datetime(as_of_date)
    window_start = as_of_dt - timedelta(days=TOKEN_WINDOW_90_DAYS)
    visible_messages = [message for message in all_messages if window_start <= message.timestamp <= as_of_dt]
    if not visible_messages:
        return 0.0
    session_starters = 0
    direction_starters = 0
    previous_timestamp: Optional[datetime] = None
    for message in visible_messages:
        if previous_timestamp is None or message.timestamp - previous_timestamp > timedelta(hours=SESSION_BREAK_HOURS):
            session_starters += 1
            if message.message_id in direction_message_ids:
                direction_starters += 1
        previous_timestamp = message.timestamp
    if session_starters == 0:
        return 0.0
    return round(direction_starters / session_starters, 4)


def _continuity_score(messages: List[Any], as_of_date: date, window_days: int) -> float:
    weekly_activity: set[Tuple[int, int]] = set()
    for message in messages:
        age_days = _age_days(as_of_date, message.timestamp)
        if 0 <= age_days <= window_days:
            iso_year, iso_week, _ = message.timestamp.isocalendar()
            weekly_activity.add((iso_year, iso_week))
    expected_weeks = max(1, math.ceil(window_days / 7))
    return round(min(1.0, len(weekly_activity) / expected_weeks), 4)


def _recency_score(outbound: Dict[str, Any], inbound: Dict[str, Any]) -> float:
    weighted_30d = float(outbound["weighted_messages_30d"]) + float(inbound["weighted_messages_30d"])
    weighted_90d = float(outbound["weighted_messages_90d"]) + float(inbound["weighted_messages_90d"])
    return round(
        max(min(1.0, weighted_30d / 40.0), min(1.0, weighted_90d / 120.0)),
        4,
    )


def _directional_warmth_index(
    *,
    warmth: float,
    support: float,
    tension: float,
    formality: float,
    depth: float,
    responsiveness: float,
) -> float:
    return round(
        min(
            1.0,
            max(0.0, warmth) * 0.34
            + max(0.0, support) * 0.24
            + max(0.0, 1.0 - tension) * 0.18
            + max(0.0, 1.0 - formality) * 0.12
            + max(0.0, depth) * 0.08
            + max(0.0, responsiveness) * 0.04,
        ),
        4,
    )


def _pair_warmth_index(left: float, right: float) -> float:
    return round((float(left) + float(right)) / 2.0, 4)


def _directional_bond_index(
    *,
    warmth_index: float,
    engagement: float,
    responsiveness: float,
    depth: float,
    support: float,
    formality: float,
    reciprocity: float,
    stability: float,
) -> float:
    return round(
        min(
            1.0,
            max(0.0, engagement) * 0.26
            + max(0.0, responsiveness) * 0.18
            + max(0.0, depth) * 0.15
            + max(0.0, warmth_index) * 0.12
            + max(0.0, support) * 0.11
            + max(0.0, 1.0 - formality) * 0.06
            + max(0.0, reciprocity) * 0.06
            + max(0.0, stability) * 0.06,
        ),
        4,
    )


def _pair_bond_index(left: float, right: float, reciprocity: float, stability: float) -> float:
    return round(
        min(
            1.0,
            ((float(left) + float(right)) / 2.0) * 0.72
            + float(reciprocity) * 0.16
            + float(stability) * 0.12,
        ),
        4,
    )


def _integrated_color_score(warmth_index: float, bond_index: float) -> float:
    return round(min(1.0, float(warmth_index) * 0.48 + float(bond_index) * 0.52), 4)


def _ratio(left: int, right: int) -> float:
    high = max(left, right)
    low = min(left, right)
    if high == 0:
        return 0.0
    return round(low / high, 4)


def _mean_defined(values: Iterable[Optional[float]]) -> float:
    defined = [float(value) for value in values if isinstance(value, (int, float))]
    if not defined:
        return 0.0
    return round(sum(defined) / len(defined), 4)


def _latest_defined(values: Iterable[Optional[str]]) -> Optional[str]:
    defined = [value for value in values if value]
    if not defined:
        return None
    return max(defined)


def _silence_gap_days(as_of_date: date, last_contact_at: Optional[str]) -> Optional[int]:
    if not last_contact_at:
        return None
    last_contact = datetime.fromisoformat(last_contact_at.replace("Z", "+00:00"))
    return max(0, (as_of_date - last_contact.date()).days)


def _tone_scores(text: str) -> Tuple[float, float, float, float]:
    lowered = text.casefold()
    if not lowered.strip():
        return 0.5, 0.0, 0.0, 0.0
    warm_words = (
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
        "поддерж",
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
        "support",
    )
    tense_words = (
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
    warm_hits = sum(word in lowered for word in warm_words)
    tense_hits = sum(word in lowered for word in tense_words)
    support_hits = sum(word in lowered for word in SUPPORT_MARKERS)
    formality_hits = sum(word in lowered for word in FORMALITY_MARKERS)
    warmth = max(0.0, min(1.0, 0.5 + 0.08 * warm_hits - 0.06 * tense_hits))
    tension = max(0.0, min(1.0, 0.08 * tense_hits))
    support = max(0.0, min(1.0, 0.55 * min(1, support_hits) + 0.15 * max(0, support_hits - 1) + 0.06 * warm_hits))
    formality = max(
        0.0,
        min(1.0, 0.45 * min(1, formality_hits) + 0.12 * max(0, formality_hits - 1) + (0.08 if ":" in text and len(text) > 80 else 0.0)),
    )
    return round(warmth, 4), round(tension, 4), round(support, 4), round(formality, 4)


def _contains_any(text: str, markers: Tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in markers)


def _time_weight(age_days: int) -> float:
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.7
    if age_days <= 180:
        return 0.35
    if age_days <= 365:
        return 0.15
    return 0.05


def _age_days(as_of_date: date, timestamp: datetime) -> int:
    return (as_of_date - timestamp.date()).days


def _as_of_datetime(as_of_date: date) -> datetime:
    return datetime.combine(as_of_date, time.max, tzinfo=timezone.utc)


def _resolve_private_peer(messages: List[Any], self_node_id: str) -> Optional[Tuple[str, str]]:
    participants: Dict[str, str] = {}
    for message in messages:
        node_id = self_node_id if message.is_outgoing else message.sender_id
        label = "You" if node_id == self_node_id else message.sender_name
        participants[node_id] = label
    peers = [(node_id, label) for node_id, label in participants.items() if node_id != self_node_id]
    if not peers:
        return None
    peers.sort(key=lambda item: item[1])
    return peers[0]


def _weekly_dates(start_date: date, end_date: date, cadence_days: int) -> List[date]:
    dates: List[date] = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=cadence_days)
    if dates and dates[-1] != end_date:
        dates.append(end_date)
    elif not dates:
        dates.append(end_date)
    return dates


def _max_chat_date(chats: Iterable[Chat]) -> Optional[date]:
    dates = [message.timestamp.date() for chat in chats for message in chat.messages]
    if not dates:
        return None
    return max(dates)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
