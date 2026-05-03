from social_graph_service.insights import build_insights
from social_graph_service.models import Edge, GraphResult, Node


def test_build_insights_ranks_direct_relationships() -> None:
    result = GraphResult(
        nodes=[
            Node(node_id="self", label="You", node_type="person"),
            Node(node_id="alice", label="Alice", node_type="person"),
        ],
        edges=[
            Edge(
                source="self",
                target="alice",
                relation_type="direct_message",
                metrics={
                    "messages": 210,
                    "warmth": 0.8,
                    "reciprocity": 0.9,
                    "session_initiation_share": 0.5,
                    "responsiveness_score": 0.6,
                    "median_response_minutes": 12.0,
                },
                evidence={"chat_name": "Alice", "chat_id": "chat-1"},
            ),
            Edge(
                source="alice",
                target="self",
                relation_type="direct_message",
                metrics={
                    "messages": 220,
                    "warmth": 0.7,
                    "reciprocity": 0.9,
                    "session_initiation_share": 0.5,
                    "responsiveness_score": 0.7,
                    "median_response_minutes": 8.0,
                },
                evidence={"chat_name": "Alice", "chat_id": "chat-1"},
            ),
        ],
        summary={},
    )

    insights = build_insights(result)

    assert insights["relationship_count"] == 1
    assert insights["top_relationships"][0]["label"] == "Alice"
    assert insights["top_relationships"][0]["tie_strength"] > 0.7
