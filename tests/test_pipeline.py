from datetime import date, datetime, timezone

from social_graph_service.models import Chat, Message
from social_graph_service.pipeline import (
    _apply_llm_to_snapshot,
    _enrich_snapshot_series,
    _select_llm_chats_for_enrichment,
)
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


def _build_payload() -> tuple[Chat, TemporalConfig, dict]:
    chat = Chat(
        chat_id="chat-1",
        name="Alice",
        chat_type="private",
        messages=[
            _message("1", "self", "Me", datetime(2026, 4, 4, 10, 0, tzinfo=timezone.utc), "thanks", True),
            _message("2", "alice", "Alice", datetime(2026, 4, 4, 10, 5, tzinfo=timezone.utc), "love", False),
            _message("3", "self", "Me", datetime(2026, 4, 11, 10, 0, tzinfo=timezone.utc), "see you", True),
            _message("4", "alice", "Alice", datetime(2026, 4, 11, 10, 8, tzinfo=timezone.utc), "great", False),
            _message("5", "self", "Me", datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc), "you matter", True),
            _message("6", "alice", "Alice", datetime(2026, 4, 18, 10, 7, tzinfo=timezone.utc), "miss you", False),
        ],
    )
    config = TemporalConfig(
        as_of_date=date(2026, 5, 2),
        start_date=date(2026, 4, 4),
        end_date=date(2026, 5, 2),
        cadence_days=7,
    )
    payload = analyze_temporal([chat], config)
    return chat, config, payload


def test_llm_enrichment_updates_current_snapshot_outputs() -> None:
    chat, config, payload = _build_payload()
    snapshot_now = payload["snapshot_now"]
    current_graph = snapshot_now["graph_result"]

    selected = _select_llm_chats_for_enrichment([chat], snapshot_now)
    assert [item.chat_id for item in selected] == ["chat-1"]

    baseline_warmth = snapshot_now["relationships"][0]["outbound"]["warmth_score"]
    baseline_edge_warmth = current_graph.edges[0].metrics["warmth"]
    baseline_integrated_color = snapshot_now["relationships"][0]["pair"]["integrated_color_score"]
    baseline_confidence = snapshot_now["relationships"][0]["pair"]["confidence_score"]
    baseline_warmth_index = snapshot_now["relationships"][0]["pair"]["warmth_index"]
    baseline_bond_index = snapshot_now["relationships"][0]["pair"]["bond_index"]
    baseline_support = snapshot_now["relationships"][0]["outbound"]["support_score"]
    baseline_formality = snapshot_now["relationships"][0]["inbound"]["formality_score"]
    baseline_depth = snapshot_now["relationships"][0]["pair"]["depth_score"]

    _apply_llm_to_snapshot(
        snapshot=snapshot_now,
        llm_scores={
            "chat-1": {
                "self_to_peer_warmth": 0.9,
                "peer_to_self_warmth": 0.85,
                "self_to_peer_support": 0.82,
                "peer_to_self_support": 0.8,
                "self_to_peer_formality": 0.1,
                "peer_to_self_formality": 0.12,
                "depth": 0.78,
                "self_to_peer_engagement": 0.76,
                "peer_to_self_engagement": 0.74,
                "mutuality": 0.88,
                "tension": 0.1,
                "confidence": 0.83,
                "reason_codes": ["supportive_language", "recent_reciprocity"],
            }
        },
        temporal_config=config,
        update_graph=True,
    )

    relationship = snapshot_now["relationships"][0]
    assert relationship["outbound"]["warmth_score"] > baseline_warmth
    assert relationship["llm"]["mutuality"] == 0.88
    assert current_graph.edges[0].metrics["warmth"] > baseline_edge_warmth
    assert relationship["pair"]["integrated_color_score"] > baseline_integrated_color
    assert relationship["pair"]["confidence_score"] >= baseline_confidence
    assert relationship["pair"]["warmth_index"] > baseline_warmth_index
    assert relationship["pair"]["bond_index"] >= baseline_bond_index
    assert relationship["outbound"]["support_score"] > baseline_support
    assert relationship["inbound"]["formality_score"] <= baseline_formality
    assert relationship["pair"]["depth_score"] >= baseline_depth
    assert relationship["pair"]["llm_reason_codes"] == ["supportive_language", "recent_reciprocity"]


def test_enrich_snapshot_series_resumes_from_progress(tmp_path, monkeypatch) -> None:
    chat, config, payload = _build_payload()
    calls: list[int] = []

    def fake_enrich(chats, cache=None, config=None, on_chat_scored=None):
        chat_list = list(chats)
        calls.append(len(chat_list))
        result = {
            "chat-1": {
                "self_to_peer_warmth": 0.9,
                "peer_to_self_warmth": 0.85,
                "mutuality": 0.88,
                "tension": 0.1,
            }
        }
        if on_chat_scored is not None:
            on_chat_scored("chat-1", result["chat-1"], False)
        return result

    monkeypatch.setattr("social_graph_service.pipeline.enrich_private_chat_scores", fake_enrich)

    result = _enrich_snapshot_series(
        chats=[chat],
        snapshot_series=payload["snapshot_series"],
        temporal_payload=payload,
        temporal_config=config,
        output_dir=tmp_path,
    )

    assert len(result) == len(payload["snapshot_series"])
    assert calls
    assert (tmp_path / ".llm-cache.json").exists()
    assert (tmp_path / ".llm-progress.json").exists()

    calls.clear()
    resumed = _enrich_snapshot_series(
        chats=[chat],
        snapshot_series=payload["snapshot_series"],
        temporal_payload=payload,
        temporal_config=config,
        output_dir=tmp_path,
    )

    assert len(resumed) == len(payload["snapshot_series"])
    assert calls == []


def test_enrich_snapshot_series_resumes_partial_snapshot(tmp_path, monkeypatch) -> None:
    chat, config, payload = _build_payload()
    second_chat = Chat(
        chat_id="chat-2",
        name="Bob",
        chat_type="private",
        messages=[
            _message("b1", "self", "Me", datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc), "thanks", True),
            _message("b2", "bob", "Bob", datetime(2026, 4, 18, 11, 4, tzinfo=timezone.utc), "love", False),
            _message("b3", "self", "Me", datetime(2026, 4, 25, 11, 0, tzinfo=timezone.utc), "you matter", True),
            _message("b4", "bob", "Bob", datetime(2026, 4, 25, 11, 8, tzinfo=timezone.utc), "miss you", False),
        ],
    )
    payload = analyze_temporal([chat, second_chat], config)
    target_snapshot = next(snapshot for snapshot in payload["snapshot_series"] if len(snapshot["relationships"]) >= 2)
    first_snapshot_key = target_snapshot["as_of_date"]
    progress_path = tmp_path / ".llm-progress.json"
    progress_path.write_text(
        '{"%s":{"chat-1":{"self_to_peer_warmth":0.1}}}' % first_snapshot_key,
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_enrich(chats, cache=None, config=None, on_chat_scored=None):
        chat_list = list(chats)
        calls.append([item.chat_id for item in chat_list])
        result = {
            item.chat_id: {
                "self_to_peer_warmth": 0.9,
                "peer_to_self_warmth": 0.85,
                "mutuality": 0.88,
                "tension": 0.1,
            }
            for item in chat_list
        }
        if on_chat_scored is not None:
            for item in chat_list:
                on_chat_scored(item.chat_id, result[item.chat_id], False)
        return result

    monkeypatch.setattr("social_graph_service.pipeline.enrich_private_chat_scores", fake_enrich)
    monkeypatch.setattr(
        "social_graph_service.pipeline._select_llm_chats_for_enrichment",
        lambda visible_chats, snapshot: [chat, second_chat] if snapshot["as_of_date"] == first_snapshot_key else [chat],
    )

    result = _enrich_snapshot_series(
        chats=[chat, second_chat],
        snapshot_series=payload["snapshot_series"],
        temporal_payload=payload,
        temporal_config=config,
        output_dir=tmp_path,
    )

    assert len(result[first_snapshot_key]) == 2
    assert result[first_snapshot_key]["chat-1"]["self_to_peer_warmth"] == 0.1
    assert result[first_snapshot_key]["chat-2"]["self_to_peer_warmth"] == 0.9
    assert calls
