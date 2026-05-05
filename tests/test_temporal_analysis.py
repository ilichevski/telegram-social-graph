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
    assert 0 <= relationship["outbound"]["depth_score"] <= 1
    assert 0 <= relationship["outbound"]["support_score"] <= 1
    assert 0 <= relationship["outbound"]["formality_score"] <= 1
    assert 0 <= relationship["pair"]["stability_score"] <= 1
    assert 0 <= relationship["pair"]["integrated_color_score"] <= 1
    assert 0 <= relationship["pair"]["confidence_score"] <= 1
    assert 0 <= relationship["pair"]["warmth_index"] <= 1
    assert 0 <= relationship["pair"]["bond_index"] <= 1


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
    snapshot = payload["relationship_timeseries"][0]["snapshots"][-1]
    assert "engagement_out" in snapshot
    assert "responsiveness_in" in snapshot
    assert "depth_score" in snapshot
    assert "confidence_score" in snapshot
    assert "support_out" in snapshot
    assert "formality_in" in snapshot
    assert "warmth_index" in snapshot
    assert "bond_index" in snapshot


def test_support_and_formality_scores_are_detectable() -> None:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            _message("1", "self", "Me", datetime(2026, 4, 28, 10, 0, tzinfo=timezone.utc), "держись, я рядом и помогу если что", True),
            _message("2", "alice", "Alice", datetime(2026, 4, 28, 10, 5, tzinfo=timezone.utc), "Здравствуйте. Добрый день, благодарю, пожалуйста подтвердите", False),
        ],
    )

    payload = analyze_temporal([chat], TemporalConfig(as_of_date=date(2026, 5, 2)))
    relationship = payload["snapshot_now"]["relationships"][0]

    assert relationship["outbound"]["support_score"] >= 0.45
    assert relationship["inbound"]["formality_score"] >= 0.35


def test_media_signals_influence_snapshot_scores() -> None:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            Message(
                chat_id="chat-1",
                chat_name="Alice",
                chat_type="private",
                message_id="1",
                sender_id="self",
                sender_name="Me",
                timestamp=datetime(2026, 4, 28, 10, 0, tzinfo=timezone.utc),
                text="",
                is_outgoing=True,
                media_kind="voice",
                media_duration_seconds=80,
                media_has_binary=True,
            ),
            Message(
                chat_id="chat-1",
                chat_name="Alice",
                chat_type="private",
                message_id="2",
                sender_id="alice",
                sender_name="Alice",
                timestamp=datetime(2026, 4, 28, 10, 5, tzinfo=timezone.utc),
                text="",
                is_outgoing=False,
                media_kind="sticker",
                sticker_emoji="❤️",
                media_has_binary=True,
            ),
        ],
    )

    payload = analyze_temporal([chat], TemporalConfig(as_of_date=date(2026, 5, 2)))
    relationship = payload["snapshot_now"]["relationships"][0]

    assert relationship["outbound"]["voice_minutes_90d"] > 1.0
    assert relationship["outbound"]["media_intimacy_score"] > 0.4
    assert relationship["inbound"]["media_playfulness_score"] >= 0.08
    assert relationship["pair"]["mutual_media_intimacy"] > 0.2
    assert relationship["pair"]["media_reciprocity"] > 0.0
