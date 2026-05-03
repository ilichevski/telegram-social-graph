from datetime import datetime, timezone

from social_graph_service.chat_profiles import build_chat_profiles
from social_graph_service.models import Chat, Message


def test_build_chat_profiles_detects_self_only_groups_and_media() -> None:
    chat = Chat(
        chat_id="group-1",
        name="Private Group",
        chat_type="group",
        messages=[
            Message(
                chat_id="group-1",
                chat_name="Private Group",
                chat_type="group",
                message_id="1",
                sender_id="self",
                sender_name="Me",
                timestamp=datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
                text="",
                is_outgoing=True,
                media_kind="photo",
            ),
            Message(
                chat_id="group-1",
                chat_name="Private Group",
                chat_type="group",
                message_id="2",
                sender_id="self",
                sender_name="Me",
                timestamp=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
                text="voice",
                is_outgoing=True,
                media_kind="voice",
            ),
        ],
    )

    profiles = build_chat_profiles([chat])

    assert profiles["self_only_group_count"] == 1
    assert profiles["media_totals"]["photo"] == 1
    assert profiles["media_totals"]["voice"] == 1
    assert profiles["self_only_groups"][0]["chat_name"] == "Private Group"
