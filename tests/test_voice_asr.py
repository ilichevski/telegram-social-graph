from datetime import datetime, timezone

from social_graph_service.models import Chat, Message
from social_graph_service.voice_asr import apply_voice_transcripts, enrich_voice_transcripts


def _voice_message(tmp_path):
    audio = tmp_path / "audio.ogg"
    audio.write_bytes(b"voice")
    return Message(
        chat_id="chat-1",
        chat_name="Alice",
        chat_type="private",
        message_id="1",
        sender_id="self",
        sender_name="Me",
        timestamp=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        text="",
        is_outgoing=True,
        media_kind="voice",
        media_path=audio.name,
        mime_type="audio/ogg",
        media_duration_seconds=12,
        media_has_binary=True,
        media_file_size_bytes=5,
    )


def test_enrich_voice_transcripts_and_apply(monkeypatch, tmp_path) -> None:
    message = _voice_message(tmp_path)
    chat = Chat(chat_id="chat-1", name="Alice", chat_type="private", messages=[message])

    def fake_runtime(audio_paths, config):
        assert len(audio_paths) == 1
        assert audio_paths[0].exists()
        return {str(audio_paths[0]): "привет как дела"}

    monkeypatch.setattr("social_graph_service.voice_asr._get_runtime", lambda: fake_runtime)

    cache = {}
    transcripts = enrich_voice_transcripts([chat], tmp_path, cache=cache)

    assert transcripts["chat-1"]["voice_message_count"] == 1
    assert "привет" in transcripts["chat-1"]["sample_text"]
    augmented = apply_voice_transcripts([chat], transcripts)
    assert "[Voice transcript]" in augmented[0].messages[0].text
    assert "привет как дела" in augmented[0].messages[0].text
