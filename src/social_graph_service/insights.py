from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .models import Edge, GraphResult


def build_insights(result: GraphResult) -> Dict[str, Any]:
    nodes_by_id = {node.node_id: node for node in result.nodes}
    direct_edges = [edge for edge in result.edges if edge.relation_type == "direct_message"]
    group_edges = [edge for edge in result.edges if edge.relation_type == "group_interaction"]

    outgoing_by_peer = {edge.target: edge for edge in direct_edges if edge.source == "self"}
    incoming_by_peer = {edge.source: edge for edge in direct_edges if edge.target == "self"}

    top_relationships: List[Dict[str, Any]] = []
    for peer_id, outgoing in outgoing_by_peer.items():
        incoming = incoming_by_peer.get(peer_id)
        if incoming is None:
            continue
        label = nodes_by_id.get(peer_id).label if peer_id in nodes_by_id else peer_id
        top_relationships.append(_build_relationship_insight(peer_id, label, outgoing, incoming))

    top_relationships.sort(key=lambda item: item["tie_strength"], reverse=True)
    top_group_interactions = _top_group_interactions(group_edges, nodes_by_id)

    return {
        "top_relationships": top_relationships[:25],
        "top_group_interactions": top_group_interactions[:25],
        "relationship_count": len(top_relationships),
        "group_interaction_count": len(top_group_interactions),
    }


def _build_relationship_insight(peer_id: str, label: str, outgoing: Edge, incoming: Edge) -> Dict[str, Any]:
    sent_messages = int(outgoing.metrics.get("messages", 0) or 0)
    received_messages = int(incoming.metrics.get("messages", 0) or 0)
    total_messages = sent_messages + received_messages
    reciprocity = _float(outgoing.metrics.get("reciprocity"))
    self_warmth = _pick_warmth(outgoing.metrics)
    peer_warmth = _pick_warmth(incoming.metrics)
    mutual_warmth = round((self_warmth + peer_warmth) / 2.0, 4)
    responsiveness = _mean_defined(
        [
            _float_or_none(outgoing.metrics.get("responsiveness_score")),
            _float_or_none(incoming.metrics.get("responsiveness_score")),
        ]
    )
    initiation_balance = 1.0 - abs(
        _float(outgoing.metrics.get("session_initiation_share"))
        - _float(incoming.metrics.get("session_initiation_share"))
    )
    volume_score = min(1.0, math.log1p(total_messages) / 6.0)
    base_tie_strength = round(
        (
            reciprocity * 0.3
            + mutual_warmth * 0.3
            + responsiveness * 0.15
            + initiation_balance * 0.1
            + volume_score * 0.15
        ),
        4,
    )
    evidence_score = round(min(1.0, total_messages / 500.0) ** 0.4, 4)
    tie_strength = round(base_tie_strength * evidence_score, 4)
    return {
        "peer_id": peer_id,
        "label": label,
        "messages_total": total_messages,
        "messages_sent": sent_messages,
        "messages_received": received_messages,
        "reciprocity": reciprocity,
        "self_warmth": self_warmth,
        "peer_warmth": peer_warmth,
        "mutual_warmth": mutual_warmth,
        "self_response_minutes": outgoing.metrics.get("median_response_minutes"),
        "peer_response_minutes": incoming.metrics.get("median_response_minutes"),
        "initiation_balance": round(initiation_balance, 4),
        "base_tie_strength": base_tie_strength,
        "evidence_score": evidence_score,
        "tie_strength": tie_strength,
        "chat_name": outgoing.evidence.get("chat_name"),
        "chat_id": outgoing.evidence.get("chat_id"),
    }


def _top_group_interactions(edges: List[Edge], nodes_by_id: Dict[str, Any]) -> List[Dict[str, Any]]:
    ranked = []
    for edge in edges:
        source_label = nodes_by_id.get(edge.source).label if edge.source in nodes_by_id else edge.source
        target_label = nodes_by_id.get(edge.target).label if edge.target in nodes_by_id else edge.target
        score = (
            _float(edge.metrics.get("reply_count")) * 0.5
            + _float(edge.metrics.get("mention_count")) * 0.3
            + _float(edge.metrics.get("warmth")) * 0.2
        )
        ranked.append(
            {
                "source": edge.source,
                "target": edge.target,
                "source_label": source_label,
                "target_label": target_label,
                "chat_name": edge.evidence.get("chat_name"),
                "reply_count": edge.metrics.get("reply_count", 0),
                "mention_count": edge.metrics.get("mention_count", 0),
                "message_count": edge.metrics.get("message_count", 0),
                "warmth": edge.metrics.get("warmth", 0),
                "interaction_score": round(score, 4),
            }
        )
    ranked.sort(key=lambda item: item["interaction_score"], reverse=True)
    return ranked


def _pick_warmth(metrics: Dict[str, Any]) -> float:
    llm_warmth = metrics.get("llm_warmth")
    if isinstance(llm_warmth, (int, float)):
        return round(float(llm_warmth), 4)
    return _float(metrics.get("warmth"))


def _mean_defined(values: List[Optional[float]]) -> float:
    defined = [value for value in values if value is not None]
    if not defined:
        return 0.0
    return round(sum(defined) / len(defined), 4)


def _float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    return 0.0


def _float_or_none(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    return None
