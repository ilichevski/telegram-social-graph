from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    chat_id: str
    chat_name: str
    chat_type: str
    message_id: str
    sender_id: str
    sender_name: str
    timestamp: datetime
    text: str
    is_outgoing: bool
    reply_to_message_id: Optional[str] = None
    media_kind: Optional[str] = None
    media_path: Optional[str] = None
    media_duration_seconds: Optional[float] = None
    sticker_emoji: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chat:
    chat_id: str
    name: str
    chat_type: str
    messages: List[Message]


@dataclass
class Node:
    node_id: str
    label: str
    node_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Node":
        return cls(
            node_id=str(payload["node_id"]),
            label=str(payload["label"]),
            node_type=str(payload["node_type"]),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass
class Edge:
    source: str
    target: str
    relation_type: str
    metrics: Dict[str, Any]
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Edge":
        return cls(
            source=str(payload["source"]),
            target=str(payload["target"]),
            relation_type=str(payload["relation_type"]),
            metrics=dict(payload.get("metrics", {})),
            evidence=dict(payload.get("evidence", {})),
        )


@dataclass
class GraphResult:
    nodes: List[Node]
    edges: List[Edge]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "GraphResult":
        return cls(
            nodes=[Node.from_dict(item) for item in payload.get("nodes", [])],
            edges=[Edge.from_dict(item) for item in payload.get("edges", [])],
            summary=dict(payload.get("summary", {})),
        )
