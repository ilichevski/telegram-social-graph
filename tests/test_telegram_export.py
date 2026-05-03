import json

from social_graph_service.telegram_export import load_chats


def test_load_chat_from_single_json(tmp_path) -> None:
    payload = {
        "id": 123,
        "name": "Alice",
        "type": "personal_chat",
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date_unixtime": "1714550400",
                "from": "Alice",
                "from_id": "alice",
                "text": "Hello",
            },
            {
                "id": 2,
                "type": "message",
                "date_unixtime": "1714554000",
                "from": "Me",
                "from_id": "user_self",
                "text": [{"type": "plain", "text": "Hi back"}],
                "out": True,
                "media_type": "voice_message",
                "file": "voice_messages/message_1.ogg",
                "duration_seconds": 4,
            },
        ],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    chats, stats = load_chats(path)

    assert stats.chats_loaded == 1
    assert len(chats[0].messages) == 2
    assert chats[0].messages[1].text == "Hi back"
    assert chats[0].messages[1].media_kind == "voice"
    assert chats[0].messages[1].media_path == "voice_messages/message_1.ogg"
