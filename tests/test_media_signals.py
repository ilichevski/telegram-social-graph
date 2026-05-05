from datetime import datetime, timezone

from social_graph_service.media_signals import message_media_signal
from social_graph_service.models import Message


def _message(**kwargs) -> Message:
    payload = dict(
        chat_id="chat-1",
        chat_name="Alice",
        chat_type="private",
        message_id="1",
        sender_id="self",
        sender_name="Me",
        timestamp=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        text="",
        is_outgoing=True,
    )
    payload.update(kwargs)
    return Message(**payload)


def test_sticker_and_voice_media_signals_are_meaningful() -> None:
    sticker_signal = message_media_signal(
        _message(media_kind="sticker", sticker_emoji="❤️", mime_type="image/webp", media_has_binary=True)
    )
    voice_signal = message_media_signal(
        _message(media_kind="voice", media_duration_seconds=75, mime_type="audio/ogg", media_has_binary=True)
    )

    assert sticker_signal.warmth > 0.2
    assert sticker_signal.support > 0.0
    assert voice_signal.intimacy > 0.5
    assert voice_signal.depth > 0.3


def test_formal_file_signal_is_detected() -> None:
    file_signal = message_media_signal(
        _message(
            media_kind="file",
            media_path="docs/contract.pdf",
            mime_type="application/pdf",
            media_has_binary=True,
        )
    )

    assert file_signal.formality >= 0.2
