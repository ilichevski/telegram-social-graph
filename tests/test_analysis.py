from datetime import datetime, timezone

from social_graph_service.analysis import analyze_chats
from social_graph_service.models import Chat, Message


def message(message_id: str, sender_id: str, sender_name: str, hour: int, text: str, is_outgoing: bool) -> Message:
    return Message(
        chat_id="chat-1",
        chat_name="Alice",
        chat_type="private",
        message_id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        timestamp=datetime(2026, 5, 1, hour, 0, tzinfo=timezone.utc),
        text=text,
        is_outgoing=is_outgoing,
    )


def test_private_chat_creates_bidirectional_edges() -> None:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            message("1", "alice", "Alice", 8, "Hi", False),
            Message(
                chat_id="chat-1",
                chat_name="Alice",
                chat_type="private",
                message_id="2",
                sender_id="self",
                sender_name="Me",
                timestamp=datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
                text="Привет, спасибо",
                is_outgoing=True,
                media_kind="voice",
            ),
            message("3", "alice", "Alice", 9, "miss you", False),
        ],
    )

    result = analyze_chats([chat])

    assert result.summary["edge_count"] == 2
    assert {edge.source for edge in result.edges} == {"self", "alice"}
    assert any(edge.metrics["warmth"] > 0.5 for edge in result.edges)
    assert any(edge.metrics["media_messages"] == 1 for edge in result.edges if edge.source == "self")
