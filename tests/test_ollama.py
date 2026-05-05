from datetime import datetime, timezone

from social_graph_service.models import Chat, Message
from social_graph_service.ollama import _build_chat_context, _build_prompt, _parse_response


def _message(
    message_id: str,
    sender_id: str,
    sender_name: str,
    dt: datetime,
    text: str,
    is_outgoing: bool,
    **kwargs,
) -> Message:
    payload = dict(
        chat_id="chat-1",
        chat_name="Alice",
        chat_type="private",
        message_id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        timestamp=dt,
        text=text,
        is_outgoing=is_outgoing,
    )
    payload.update(kwargs)
    return Message(**payload)


def test_build_chat_context_uses_sessions_and_behavioral_summary() -> None:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            _message("1", "self", "Me", datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc), "спасибо, я рядом", True),
            _message("2", "alice", "Alice", datetime(2026, 4, 1, 10, 6, tzinfo=timezone.utc), "love you too", False),
            _message("3", "self", "Me", datetime(2026, 4, 3, 15, 0, tzinfo=timezone.utc), "меня это бесит", True),
            _message("4", "alice", "Alice", datetime(2026, 4, 3, 15, 4, tzinfo=timezone.utc), "i'm here for you", False),
            _message("5", "self", "Me", datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc), "это правда важно и очень лично", True),
            _message("6", "alice", "Alice", datetime(2026, 4, 20, 9, 7, tzinfo=timezone.utc), "держись, помогу если что", False),
            _message("7", "self", "Me", datetime(2026, 4, 21, 9, 0, tzinfo=timezone.utc), "", True, media_kind="voice", media_duration_seconds=70, media_has_binary=True),
            _message("8", "alice", "Alice", datetime(2026, 4, 21, 9, 3, tzinfo=timezone.utc), "", False, media_kind="sticker", sticker_emoji="❤️", media_has_binary=True),
        ],
    )

    context = _build_chat_context(chat)

    assert context["session_count"] >= 2
    transcript = str(context["transcript"])
    assert "[Session 1" in transcript
    assert "YOU:" in transcript
    assert "Alice:" in transcript
    stats = context["stats"]
    assert stats["messages_total"] == 8
    assert stats["session_count"] >= 2
    assert stats["marker_counts"]["support"] >= 1
    assert stats["media_counts"]["voice"] == 1
    assert stats["voice_minutes_you"] > 1.0
    assert stats["top_sticker_emoji"][0][0] == "❤️"


def test_build_prompt_includes_behavioral_summary_and_excerpts() -> None:
    context = {
        "transcript": "[Session 1 | 20 Apr 2026 09:00 UTC -> 20 Apr 2026 09:07 UTC | 2 messages]\nYOU: спасибо\nAlice: love you",
        "stats": {
            "messages_total": 6,
            "messages_7d": 2,
            "median_reply_minutes_you": 4.0,
            "median_reply_minutes_them": 5.0,
        },
        "session_count": 2,
    }

    prompt = _build_prompt("Alice", context)

    assert "BEHAVIORAL_SUMMARY:" in prompt
    assert "SELECTED_EXCERPTS:" in prompt
    assert '"self_to_peer_support"' in prompt
    assert '"reason_codes"' in prompt
    assert "Alice" in prompt


def test_parse_response_supports_extended_schema_and_reason_codes() -> None:
    parsed = _parse_response(
        """
        {
          "self_to_peer_warmth": 0.84,
          "peer_to_self_warmth": 0.79,
          "self_to_peer_support": 0.61,
          "peer_to_self_support": 0.66,
          "self_to_peer_formality": 0.12,
          "peer_to_self_formality": 0.08,
          "depth": 0.73,
          "self_to_peer_engagement": 0.68,
          "peer_to_self_engagement": 0.71,
          "mutuality": 0.77,
          "tension": 0.14,
          "confidence": 0.82,
          "reason_codes": ["recent_reciprocity", "supportive_language"]
        }
        """
    )

    assert parsed is not None
    assert parsed["self_to_peer_support"] == 0.61
    assert parsed["depth"] == 0.73
    assert parsed["confidence"] == 0.82
    assert parsed["reason_codes"] == ["recent_reciprocity", "supportive_language"]


def test_parse_response_keeps_backward_compatibility_with_legacy_schema() -> None:
    parsed = _parse_response(
        """
        {
          "self_to_peer_warmth": 0.9,
          "peer_to_self_warmth": 0.8,
          "mutuality": 0.85,
          "tension": 0.15
        }
        """
    )

    assert parsed is not None
    assert parsed["self_to_peer_support"] == 0.9
    assert parsed["peer_to_self_support"] == 0.8
    assert parsed["self_to_peer_engagement"] == 0.85
    assert parsed["confidence"] == 0.85
