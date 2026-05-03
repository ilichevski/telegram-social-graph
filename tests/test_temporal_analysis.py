from datetime import date, datetime, timezone

from social_graph_service.models import Chat, Message
from social_graph_service.temporal_analysis import TemporalConfig, analyze_temporal


def _message(
    message_id: str,
    sender_id: str,
    sender_name: str,
    dt: datetime,
    text: str,
    is_outgoing: bool,
) -> Message:
    return Message(
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


def test_temporal_snapshot_tracks_as_of_date_and_status() -> None:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            _message("1", "self", "Me", datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc), "thanks", True),
            _message("2", "alice", "Alice", datetime(2026, 4, 1, 10, 5, tzinfo=timezone.utc), "love", False),
            _message("3", "self", "Me", datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc), "see you", True),
            _message("4", "alice", "Alice", datetime(2026, 4, 20, 10, 8, tzinfo=timezone.utc), "ok", False),
        ],
    )

    payload = analyze_temporal([chat], TemporalConfig(as_of_date=date(2026, 5, 2)))
    relationship = payload["snapshot_now"]["relationships"][0]

    assert relationship["pair"]["messages_total_90d"] == 4
    assert relationship["pair"]["status"] in {"active_mutual", "active_asymmetric"}
    assert relationship["outbound"]["messages_count_30d"] == 1


def test_temporal_analysis_builds_weekly_timeseries() -> None:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            _message("1", "self", "Me", datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc), "hi", True),
            _message("2", "alice", "Alice", datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc), "yo", False),
            _message("3", "self", "Me", datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc), "again", True),
            _message("4", "alice", "Alice", datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc), "again", False),
        ],
    )

    payload = analyze_temporal(
        [chat],
        TemporalConfig(
            as_of_date=date(2026, 5, 2),
            start_date=date(2026, 4, 4),
            end_date=date(2026, 5, 2),
            cadence_days=7,
        ),
    )

    assert len(payload["weekly_snapshots"]) >= 4
    assert len(payload["relationship_timeseries"]) == 1
    assert payload["person_reports"][0]["current_snapshot"]["status"]
