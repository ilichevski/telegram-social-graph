from __future__ import annotations


def _llm_payload_is_zero_judgment(llm_payload: dict[str, Any]) -> bool:
    core_fields = (
        "self_to_peer_warmth",
        "peer_to_self_warmth",
        "self_to_peer_support",
        "peer_to_self_support",
        "depth",
        "self_to_peer_engagement",
        "peer_to_self_engagement",
        "mutuality",
    )
    values: list[float] = []
    for field in core_fields:
        try:
            values.append(float(llm_payload.get(field, 0.0) or 0.0))
        except (TypeError, ValueError):
            values.append(0.0)
    return all(value == 0.0 for value in values)

from dataclasses import asdict
from datetime import date, datetime, time, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, Optional

from .chat_profiles import build_chat_profiles
from .exporters import write_outputs
from .ollama import enrich_private_chat_scores
from .temporal_analysis import (
    ACTIVE_STATUSES,
    CURRENT_TIE_TOP_LIMIT,
    TemporalConfig,
    _build_network_snapshot,
    _directional_bond_index,
    _directional_warmth_index,
    _build_person_reports,
    _build_relationship_timeseries,
    _classify_status,
    _classify_trend,
    _compact_weekly_snapshot,
    _integrated_color_score,
    _pair_bond_index,
    _pair_warmth_index,
    _relationship_drivers,
    _relationship_to_edges,
    _snapshot_delta,
    analyze_temporal,
)
from .telegram_export import load_chats
from .models import Chat
from .voice_asr import VoiceAsrConfig, apply_voice_transcripts, enrich_voice_transcripts

LLM_CHAT_LIMIT = 40
LLM_MIN_MESSAGES_90D = 6
LLM_ELIGIBLE_STATUSES = ACTIVE_STATUSES | {"fading"}


def run_analysis(
    export_path: Path,
    output_dir: Path,
    *,
    self_name: Optional[str] = None,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    cadence_days: int = 7,
    window_days: int = 90,
    short_window_days: int = 30,
    with_llm: bool = False,
    with_voice_asr: bool = False,
) -> Dict[str, Any]:
    chats, import_stats = load_chats(export_path, self_name=self_name)
    export_root = export_path if export_path.is_dir() else export_path.parent
    voice_asr_summary: Dict[str, Any] = {}
    if with_voice_asr:
        output_dir.mkdir(parents=True, exist_ok=True)
        voice_cache_path = output_dir / ".voice-asr-cache.json"
        voice_cache = _load_json_mapping(voice_cache_path)
        effective_as_of = as_of_date or end_date
        voice_transcripts = enrich_voice_transcripts(
            chats,
            export_root,
            cache=voice_cache,
            config=VoiceAsrConfig(as_of_date=effective_as_of, window_days=window_days + 1),
        )
        if voice_transcripts:
            chats = apply_voice_transcripts(chats, voice_transcripts)
            _save_json_mapping(voice_cache_path, voice_cache)
        voice_asr_summary = {
            "enabled": True,
            "chat_count": len(voice_transcripts),
            "message_count": sum(int(item.get("voice_message_count", 0)) for item in voice_transcripts.values()),
            "seconds_total": round(sum(float(item.get("voice_seconds_total", 0.0)) for item in voice_transcripts.values()), 2),
        }
    temporal_config = TemporalConfig(
        self_label=self_name or "You",
        as_of_date=as_of_date,
        start_date=start_date,
        end_date=end_date,
        cadence_days=cadence_days,
        window_days=window_days,
        short_window_days=short_window_days,
    )
    temporal_payload = analyze_temporal(
        chats,
        temporal_config,
    )
    snapshot_now = temporal_payload["snapshot_now"]
    current_graph = snapshot_now["graph_result"]
    effective_as_of = date.fromisoformat(temporal_payload["analysis_config"]["as_of_date"])
    visible_chats = _filter_chats_as_of(chats, effective_as_of)

    llm_scores: Dict[str, Dict[str, Any]] = {}
    llm_scores_by_date: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if with_llm:
        snapshot_series = temporal_payload.get("snapshot_series") or []
        if snapshot_series:
            llm_scores_by_date = _enrich_snapshot_series(
                chats=chats,
                snapshot_series=snapshot_series,
                temporal_payload=temporal_payload,
                temporal_config=temporal_config,
                output_dir=output_dir,
            )
            latest_date = snapshot_now["as_of_date"]
            llm_scores = llm_scores_by_date.get(latest_date, {})
        else:
            llm_input_chats = _select_llm_chats_for_enrichment(visible_chats, snapshot_now)
            llm_scores = enrich_private_chat_scores(llm_input_chats) if llm_input_chats else {}
            if llm_scores:
                _apply_llm_to_snapshot(
                    snapshot=snapshot_now,
                    llm_scores=llm_scores,
                    temporal_config=temporal_config,
                    update_graph=True,
                )

    snapshot_now_for_output = {key: value for key, value in snapshot_now.items() if key != "graph_result"}

    summary: Dict[str, Any] = {
        "input_path": str(export_path),
        "output_path": str(output_dir),
        "import_stats": asdict(import_stats),
        "graph_summary": current_graph.summary,
        "analysis_config": temporal_payload["analysis_config"],
        "llm_scores": llm_scores,
        "llm_scores_by_date": llm_scores_by_date,
        "llm_enriched_chat_count": len(llm_scores),
        "llm_selected_chat_count": len(llm_scores),
        "voice_asr": voice_asr_summary,
        "snapshot_now": snapshot_now_for_output,
        "weekly_snapshots": temporal_payload["weekly_snapshots"],
        "relationship_timeseries": temporal_payload["relationship_timeseries"],
        "network_timeseries": temporal_payload["network_timeseries"],
        "person_reports": temporal_payload["person_reports"],
        "chat_profiles": build_chat_profiles(visible_chats),
    }
    write_outputs(current_graph, output_dir, summary)
    return summary


def _filter_chats_as_of(chats: list[Chat], as_of_date: date) -> list[Chat]:
    end_dt = datetime.combine(as_of_date, time.max, tzinfo=timezone.utc)
    filtered: list[Chat] = []
    for chat in chats:
        messages = [message for message in chat.messages if message.timestamp <= end_dt]
        if not messages:
            continue
        filtered.append(
            Chat(
                chat_id=chat.chat_id,
                name=chat.name,
                chat_type=chat.chat_type,
                messages=messages,
            )
        )
    return filtered


def _select_llm_chats_for_enrichment(chats: list[Chat], snapshot_now: Dict[str, Any]) -> list[Chat]:
    chats_by_id = {chat.chat_id: chat for chat in chats if chat.chat_type == "private"}
    selected: list[Chat] = []

    for relationship in snapshot_now.get("relationships", []):
        pair = relationship.get("pair", {})
        if int(pair.get("messages_total_90d", 0)) < LLM_MIN_MESSAGES_90D:
            continue
        if pair.get("status") not in LLM_ELIGIBLE_STATUSES and int(pair.get("messages_total_30d", 0)) == 0:
            continue
        chat = chats_by_id.get(relationship["chat_id"])
        if chat is None:
            continue
        selected.append(chat)
        if len(selected) >= LLM_CHAT_LIMIT:
            break

    return selected


def _enrich_snapshot_series(
    *,
    chats: list[Chat],
    snapshot_series: list[Dict[str, Any]],
    temporal_payload: Dict[str, Any],
    temporal_config: TemporalConfig,
    output_dir: Path,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / ".llm-cache.json"
    progress_path = output_dir / ".llm-progress.json"
    llm_scores_by_date: Dict[str, Dict[str, Dict[str, Any]]] = _load_json_mapping(progress_path)
    llm_response_cache: Dict[str, Dict[str, Any]] = _load_json_mapping(cache_path)
    total_snapshots = len(snapshot_series)

    for index, snapshot in enumerate(snapshot_series, start=1):
        snapshot_key = snapshot["as_of_date"]
        snapshot_date = date.fromisoformat(snapshot_key)
        visible_chats = _filter_chats_as_of(chats, snapshot_date)
        llm_input_chats = _select_llm_chats_for_enrichment(visible_chats, snapshot)
        existing_scores = llm_scores_by_date.get(snapshot_key, {})
        selected_chat_ids = {chat.chat_id for chat in llm_input_chats}
        if existing_scores:
            existing_scores = {
                chat_id: payload
                for chat_id, payload in existing_scores.items()
                if chat_id in selected_chat_ids
            }
            llm_scores_by_date[snapshot_key] = dict(existing_scores)
        pending_chats = [chat for chat in llm_input_chats if chat.chat_id not in existing_scores]
        if existing_scores and not pending_chats:
            print(
                f"[LLM] {index}/{total_snapshots} {snapshot_key} resumed enriched={len(existing_scores)}",
                flush=True,
            )
            _apply_llm_to_snapshot(
                snapshot=snapshot,
                llm_scores=existing_scores,
                temporal_config=temporal_config,
                update_graph=snapshot_key == temporal_payload["analysis_config"]["as_of_date"],
            )
            continue
        print(
            f"[LLM] {index}/{total_snapshots} {snapshot_key} selected={len(llm_input_chats)} resumed={len(existing_scores)} pending={len(pending_chats)}",
            flush=True,
        )
        if not llm_input_chats:
            llm_scores_by_date[snapshot_key] = {}
            _save_json_mapping(progress_path, llm_scores_by_date)
            continue
        snapshot_scores: Dict[str, Dict[str, Any]] = dict(existing_scores)
        scored_count = len(existing_scores)

        def _on_chat_scored(chat_id: str, score: Dict[str, Any], from_cache: bool) -> None:
            nonlocal scored_count
            snapshot_scores[chat_id] = score
            llm_scores_by_date[snapshot_key] = dict(snapshot_scores)
            scored_count += 1
            if not from_cache:
                _save_json_mapping(cache_path, llm_response_cache)
            _save_json_mapping(progress_path, llm_scores_by_date)
            if scored_count == len(llm_input_chats) or scored_count % 5 == 0:
                source = "cache" if from_cache else "ollama"
                print(
                    f"[LLM] {index}/{total_snapshots} {snapshot_key} progress={scored_count}/{len(llm_input_chats)} last={source}",
                    flush=True,
                )

        llm_scores = enrich_private_chat_scores(
            pending_chats,
            cache=llm_response_cache,
            on_chat_scored=_on_chat_scored,
        )
        merged_scores = dict(existing_scores)
        merged_scores.update(llm_scores)
        llm_scores_by_date[snapshot_key] = merged_scores
        _save_json_mapping(cache_path, llm_response_cache)
        _save_json_mapping(progress_path, llm_scores_by_date)
        print(
            f"[LLM] {index}/{total_snapshots} {snapshot_key} enriched={len(merged_scores)} cache_entries={len(llm_response_cache)}",
            flush=True,
        )
        if merged_scores:
            _apply_llm_to_snapshot(
                snapshot=snapshot,
                llm_scores=merged_scores,
                temporal_config=temporal_config,
                update_graph=snapshot_key == temporal_payload["analysis_config"]["as_of_date"],
            )

    snapshot_now = next(
        (
            snapshot
            for snapshot in snapshot_series
            if snapshot["as_of_date"] == temporal_payload["analysis_config"]["as_of_date"]
        ),
        None,
    )
    if snapshot_now is not None:
        temporal_payload["snapshot_now"] = snapshot_now
    temporal_payload["weekly_snapshots"] = [_compact_weekly_snapshot(snapshot) for snapshot in snapshot_series]
    temporal_payload["network_timeseries"] = [snapshot["network_snapshot"] for snapshot in snapshot_series]
    temporal_payload["relationship_timeseries"] = _build_relationship_timeseries(snapshot_series)
    temporal_payload["person_reports"] = _build_person_reports(temporal_payload["relationship_timeseries"])
    return llm_scores_by_date


def _apply_llm_to_snapshot(
    *,
    snapshot: Dict[str, Any],
    llm_scores: Dict[str, Dict[str, Any]],
    temporal_config: TemporalConfig,
    update_graph: bool,
) -> None:
    as_of_date = date.fromisoformat(snapshot["as_of_date"])
    relationships = snapshot.get("relationships", [])
    enriched_peer_ids: set[str] = set()

    for relationship in relationships:
        llm_payload = llm_scores.get(relationship["chat_id"])
        if not llm_payload:
            continue
        _merge_llm_into_relationship(relationship, llm_payload)
        enriched_peer_ids.add(relationship["peer_id"])

    relationships.sort(key=lambda item: item["pair"]["tie_strength_score"], reverse=True)
    snapshot["top_relationships"] = relationships[:CURRENT_TIE_TOP_LIMIT]
    snapshot["network_snapshot"] = _build_network_snapshot(relationships, as_of_date)

    if enriched_peer_ids:
        snapshot["network_snapshot"]["llm_enriched_relationships"] = len(enriched_peer_ids)

    if update_graph and snapshot.get("graph_result") is not None:
        current_graph = snapshot["graph_result"]
        current_graph.edges = [
            edge
            for relationship in relationships
            for edge in _relationship_to_edges(relationship, temporal_config)
        ]
        current_graph.summary["chat_count"] = len(relationships)
        current_graph.summary["edge_count"] = len(current_graph.edges)
        current_graph.summary["llm_enriched_relationships"] = len(enriched_peer_ids)


def _merge_llm_into_relationship(relationship: Dict[str, Any], llm_payload: Dict[str, Any]) -> None:
    outbound = relationship["outbound"]
    inbound = relationship["inbound"]
    pair = relationship["pair"]
    if _llm_payload_is_zero_judgment(llm_payload):
        relationship["llm"] = dict(llm_payload)
        relationship["llm"]["ignored_as_zero_judgment"] = True
        relationship["drivers"] = _relationship_drivers(outbound, inbound, pair)
        return

    outbound["heuristic_warmth_score"] = outbound.get("warmth_score", 0.0)
    inbound["heuristic_warmth_score"] = inbound.get("warmth_score", 0.0)
    outbound["heuristic_tension_score"] = outbound.get("tension_score", 0.0)
    inbound["heuristic_tension_score"] = inbound.get("tension_score", 0.0)

    outbound["llm_warmth_score"] = round(float(llm_payload.get("self_to_peer_warmth", outbound["warmth_score"])), 4)
    inbound["llm_warmth_score"] = round(float(llm_payload.get("peer_to_self_warmth", inbound["warmth_score"])), 4)
    outbound["warmth_score"] = _blend_metric(outbound["heuristic_warmth_score"], outbound["llm_warmth_score"], 0.55)
    inbound["warmth_score"] = _blend_metric(inbound["heuristic_warmth_score"], inbound["llm_warmth_score"], 0.55)

    outbound["heuristic_support_score"] = outbound.get("support_score", 0.0)
    inbound["heuristic_support_score"] = inbound.get("support_score", 0.0)
    outbound["llm_support_score"] = round(
        float(llm_payload.get("self_to_peer_support", outbound["heuristic_support_score"])),
        4,
    )
    inbound["llm_support_score"] = round(
        float(llm_payload.get("peer_to_self_support", inbound["heuristic_support_score"])),
        4,
    )
    outbound["support_score"] = _blend_metric(outbound["heuristic_support_score"], outbound["llm_support_score"], 0.45)
    inbound["support_score"] = _blend_metric(inbound["heuristic_support_score"], inbound["llm_support_score"], 0.45)

    outbound["heuristic_formality_score"] = outbound.get("formality_score", 0.0)
    inbound["heuristic_formality_score"] = inbound.get("formality_score", 0.0)
    outbound["llm_formality_score"] = round(
        float(llm_payload.get("self_to_peer_formality", outbound["heuristic_formality_score"])),
        4,
    )
    inbound["llm_formality_score"] = round(
        float(llm_payload.get("peer_to_self_formality", inbound["heuristic_formality_score"])),
        4,
    )
    outbound["formality_score"] = min(
        float(outbound["heuristic_formality_score"]),
        _blend_metric(outbound["heuristic_formality_score"], outbound["llm_formality_score"], 0.40),
    )
    inbound["formality_score"] = min(
        float(inbound["heuristic_formality_score"]),
        _blend_metric(inbound["heuristic_formality_score"], inbound["llm_formality_score"], 0.40),
    )

    llm_depth = round(float(llm_payload.get("depth", pair.get("depth_score", 0.0))), 4)
    outbound["heuristic_depth_score"] = outbound.get("depth_score", 0.0)
    inbound["heuristic_depth_score"] = inbound.get("depth_score", 0.0)
    outbound["depth_score"] = _blend_metric(outbound["heuristic_depth_score"], llm_depth, 0.24)
    inbound["depth_score"] = _blend_metric(inbound["heuristic_depth_score"], llm_depth, 0.24)

    pair["heuristic_engagement_out"] = pair.get("engagement_out", 0.0)
    pair["heuristic_engagement_in"] = pair.get("engagement_in", 0.0)
    pair["llm_engagement_out"] = round(
        float(llm_payload.get("self_to_peer_engagement", pair["heuristic_engagement_out"])),
        4,
    )
    pair["llm_engagement_in"] = round(
        float(llm_payload.get("peer_to_self_engagement", pair["heuristic_engagement_in"])),
        4,
    )
    pair["engagement_out"] = _blend_metric(pair["heuristic_engagement_out"], pair["llm_engagement_out"], 0.28)
    pair["engagement_in"] = _blend_metric(pair["heuristic_engagement_in"], pair["llm_engagement_in"], 0.28)

    llm_tension = round(float(llm_payload.get("tension", 0.0)), 4)
    pair["llm_mutuality_score"] = round(float(llm_payload.get("mutuality", pair.get("reciprocity", 0.0))), 4)
    pair["llm_tension_score"] = llm_tension
    pair["llm_depth_score"] = llm_depth
    pair["llm_confidence_score"] = round(
        float(llm_payload.get("confidence", pair.get("confidence_score", 0.0))),
        4,
    )
    if "reason_codes" in llm_payload:
        pair["llm_reason_codes"] = llm_payload["reason_codes"]
    outbound["tension_score"] = _blend_metric(outbound["heuristic_tension_score"], llm_tension, 0.35)
    inbound["tension_score"] = _blend_metric(inbound["heuristic_tension_score"], llm_tension, 0.35)

    pair["heuristic_mutual_warmth"] = pair.get("mutual_warmth", 0.0)
    pair["mutual_warmth"] = round((float(outbound["warmth_score"]) + float(inbound["warmth_score"])) / 2.0, 4)
    pair["mutual_tension"] = round((float(outbound["tension_score"]) + float(inbound["tension_score"])) / 2.0, 4)
    pair["mutual_support"] = round((float(outbound["support_score"]) + float(inbound["support_score"])) / 2.0, 4)
    pair["mutual_formality"] = round((float(outbound["formality_score"]) + float(inbound["formality_score"])) / 2.0, 4)
    pair["depth_score"] = round(
        min(
            1.0,
            _blend_metric(float(pair.get("depth_score", 0.0)), llm_depth, 0.30),
        ),
        4,
    )
    outbound["warmth_index"] = _directional_warmth_index(
        warmth=float(outbound.get("warmth_score", 0.0)),
        support=float(outbound.get("support_score", 0.0)),
        tension=float(outbound.get("tension_score", 0.0)),
        formality=float(outbound.get("formality_score", 0.0)),
        depth=float(outbound.get("depth_score", 0.0)),
        responsiveness=float(outbound.get("responsiveness_score") or 0.0),
        media_intimacy=float(outbound.get("media_intimacy_score", 0.0)),
        playfulness=float(outbound.get("media_playfulness_score", 0.0)),
    )
    inbound["warmth_index"] = _directional_warmth_index(
        warmth=float(inbound.get("warmth_score", 0.0)),
        support=float(inbound.get("support_score", 0.0)),
        tension=float(inbound.get("tension_score", 0.0)),
        formality=float(inbound.get("formality_score", 0.0)),
        depth=float(inbound.get("depth_score", 0.0)),
        responsiveness=float(inbound.get("responsiveness_score") or 0.0),
        media_intimacy=float(inbound.get("media_intimacy_score", 0.0)),
        playfulness=float(inbound.get("media_playfulness_score", 0.0)),
    )
    pair["warmth_index_out"] = float(outbound["warmth_index"])
    pair["warmth_index_in"] = float(inbound["warmth_index"])
    pair["warmth_index"] = _pair_warmth_index(pair["warmth_index_out"], pair["warmth_index_in"])
    pair["bond_index_out"] = _directional_bond_index(
        warmth_index=float(pair["warmth_index_out"]),
        engagement=float(pair.get("engagement_out", 0.0)),
        responsiveness=float(outbound.get("responsiveness_score") or 0.0),
        depth=float(outbound.get("depth_score", 0.0)),
        support=float(outbound.get("support_score", 0.0)),
        formality=float(outbound.get("formality_score", 0.0)),
        reciprocity=float(pair.get("reciprocity", 0.0)),
        stability=float(pair.get("stability_score", pair.get("continuity_score", 0.0))),
        media_intimacy=float(outbound.get("media_intimacy_score", 0.0)),
        media_expressiveness=float(outbound.get("media_expressiveness_score", 0.0)),
    )
    pair["bond_index_in"] = _directional_bond_index(
        warmth_index=float(pair["warmth_index_in"]),
        engagement=float(pair.get("engagement_in", 0.0)),
        responsiveness=float(inbound.get("responsiveness_score") or 0.0),
        depth=float(inbound.get("depth_score", 0.0)),
        support=float(inbound.get("support_score", 0.0)),
        formality=float(inbound.get("formality_score", 0.0)),
        reciprocity=float(pair.get("reciprocity", 0.0)),
        stability=float(pair.get("stability_score", pair.get("continuity_score", 0.0))),
        media_intimacy=float(inbound.get("media_intimacy_score", 0.0)),
        media_expressiveness=float(inbound.get("media_expressiveness_score", 0.0)),
    )
    pair["bond_index"] = _pair_bond_index(
        pair["bond_index_out"],
        pair["bond_index_in"],
        float(pair.get("reciprocity", 0.0)),
        float(pair.get("stability_score", pair.get("continuity_score", 0.0))),
        float(pair.get("media_reciprocity", 0.0)),
    )

    heuristic_closeness = float(pair.get("closeness_score", 0.0))
    blended_closeness = (
        float(pair.get("reciprocity", 0.0)) * 0.30
        + float(pair["mutual_warmth"]) * 0.20
        + float(pair.get("mutual_responsiveness", 0.0)) * 0.15
        + float(pair.get("initiation_balance", 0.0)) * 0.15
        + float(pair.get("continuity_score", 0.0)) * 0.10
        + float(pair.get("recency_score", 0.0)) * 0.10
    )
    pair["heuristic_closeness_score"] = heuristic_closeness
    pair["closeness_score"] = _blend_metric(blended_closeness, pair["llm_mutuality_score"], 0.15)
    pair["tie_strength_score"] = round(pair["closeness_score"] * float(pair.get("evidence_score", 0.0)), 4)
    pair["integrated_color_score"] = _integrated_color_score(
        float(pair.get("warmth_index", 0.0)),
        float(pair.get("bond_index", 0.0)),
    )
    response_coverage = 0.0
    if outbound.get("responsiveness_score") is not None:
        response_coverage += 0.5
    if inbound.get("responsiveness_score") is not None:
        response_coverage += 0.5
    messages_total = int(pair.get("messages_total_90d", 0))
    weighted_messages_total = float(pair.get("weighted_messages_total", 0.0))
    pair["confidence_score"] = round(
        min(
            1.0,
            (min(1.0, math.log1p(messages_total) / math.log1p(160.0)) if messages_total > 0 else 0.0) * 0.45
            + float(pair.get("continuity_score", 0.0)) * 0.18
            + min(1.0, float(pair.get("reciprocity", 0.0)) + 0.08) * 0.12
            + float(pair.get("depth_score", 0.0)) * 0.10
            + response_coverage * 0.10
            + min(1.0, weighted_messages_total / 120.0) * 0.05,
        ),
        4,
    )
    pair["confidence_score"] = _blend_metric(
        float(pair["confidence_score"]),
        float(pair.get("llm_confidence_score", pair["confidence_score"])),
        0.12,
    )
    pair["status"] = _classify_status(
        current_30d=int(pair.get("messages_total_30d", 0)),
        current_90d=int(pair.get("messages_total_90d", 0)),
        prev_90d=int(pair.get("messages_total_prev_90d", 0)),
        prev_365d=int(pair.get("messages_total_prev_365d", 0)),
        reciprocity=float(pair.get("reciprocity", 0.0)),
        closeness_score=float(pair["closeness_score"]),
        silence_gap_days=pair.get("silence_gap_days"),
    )
    relationship["llm"] = llm_payload
    if _llm_payload_is_zero_judgment(llm_payload):
        relationship["llm"]["ignored_as_zero_judgment"] = True
        return
    relationship["drivers"] = _relationship_drivers(outbound, inbound, pair)


def _apply_llm_to_timeseries(
    relationship_timeseries: list[Dict[str, Any]],
    relationships: list[Dict[str, Any]],
    as_of_date: str,
) -> None:
    by_peer_id = {entry["peer_id"]: entry for entry in relationship_timeseries}

    for relationship in relationships:
        entry = by_peer_id.get(relationship["peer_id"])
        if not entry or not entry.get("snapshots"):
            continue
        snapshot = entry["snapshots"][-1]
        if snapshot.get("as_of_date") != as_of_date:
            continue
        snapshot["closeness_score"] = relationship["pair"]["closeness_score"]
        snapshot["tie_strength_score"] = relationship["pair"]["tie_strength_score"]
        snapshot["warmth_out"] = relationship["outbound"]["warmth_score"]
        snapshot["warmth_in"] = relationship["inbound"]["warmth_score"]
        snapshot["tension_out"] = relationship["outbound"]["tension_score"]
        snapshot["tension_in"] = relationship["inbound"]["tension_score"]
        snapshot["support_out"] = relationship["outbound"].get("support_score", 0.0)
        snapshot["support_in"] = relationship["inbound"].get("support_score", 0.0)
        snapshot["formality_out"] = relationship["outbound"].get("formality_score", 0.0)
        snapshot["formality_in"] = relationship["inbound"].get("formality_score", 0.0)
        snapshot["warmth_index_out"] = relationship["pair"].get("warmth_index_out", snapshot.get("warmth_index_out", 0.0))
        snapshot["warmth_index_in"] = relationship["pair"].get("warmth_index_in", snapshot.get("warmth_index_in", 0.0))
        snapshot["warmth_index"] = relationship["pair"].get("warmth_index", snapshot.get("warmth_index", 0.0))
        snapshot["engagement_out"] = relationship["pair"].get("engagement_out", snapshot.get("engagement_out", 0.0))
        snapshot["engagement_in"] = relationship["pair"].get("engagement_in", snapshot.get("engagement_in", 0.0))
        snapshot["responsiveness_out"] = relationship["outbound"].get("responsiveness_score") or 0.0
        snapshot["responsiveness_in"] = relationship["inbound"].get("responsiveness_score") or 0.0
        snapshot["stability_score"] = relationship["pair"].get("stability_score", snapshot.get("stability_score", 0.0))
        snapshot["depth_score"] = relationship["pair"].get("depth_score", snapshot.get("depth_score", 0.0))
        snapshot["bond_index_out"] = relationship["pair"].get("bond_index_out", snapshot.get("bond_index_out", 0.0))
        snapshot["bond_index_in"] = relationship["pair"].get("bond_index_in", snapshot.get("bond_index_in", 0.0))
        snapshot["bond_index"] = relationship["pair"].get("bond_index", snapshot.get("bond_index", 0.0))
        snapshot["mutual_tension"] = relationship["pair"].get("mutual_tension", snapshot.get("mutual_tension", 0.0))
        snapshot["mutual_support"] = relationship["pair"].get("mutual_support", snapshot.get("mutual_support", 0.0))
        snapshot["mutual_formality"] = relationship["pair"].get("mutual_formality", snapshot.get("mutual_formality", 0.0))
        snapshot["integrated_color_score"] = relationship["pair"].get(
            "integrated_color_score",
            snapshot.get("integrated_color_score", 0.0),
        )
        snapshot["confidence_score"] = relationship["pair"].get("confidence_score", snapshot.get("confidence_score", 0.0))
        snapshot["reciprocity"] = relationship["pair"]["reciprocity"]
        snapshot["status"] = relationship["pair"]["status"]


def _apply_llm_to_person_reports(
    person_reports: list[Dict[str, Any]],
    relationship_timeseries: list[Dict[str, Any]],
) -> None:
    timeseries_by_peer = {entry["peer_id"]: entry for entry in relationship_timeseries}

    for report in person_reports:
        series = timeseries_by_peer.get(report["peer_id"])
        if not series or not series.get("snapshots"):
            continue
        snapshots = series["snapshots"]
        current = snapshots[-1]
        previous = snapshots[-2] if len(snapshots) >= 2 else None
        yearly_reference = snapshots[-53] if len(snapshots) >= 53 else None
        report["current_snapshot"] = current
        report["delta_vs_previous_week"] = _snapshot_delta(current, previous)
        report["delta_vs_previous_year"] = _snapshot_delta(current, yearly_reference)
        report["trend"] = _classify_trend(report["delta_vs_previous_week"])


def _apply_llm_to_network_snapshots(
    network_timeseries: list[Dict[str, Any]],
    weekly_snapshots: list[Dict[str, Any]],
    snapshot_now: Dict[str, Any],
) -> None:
    as_of_date = snapshot_now["as_of_date"]
    network_snapshot = snapshot_now["network_snapshot"]

    for item in network_timeseries:
        if item.get("as_of_date") == as_of_date:
            item.update(network_snapshot)

    for index, item in enumerate(weekly_snapshots):
        if item.get("as_of_date") == as_of_date:
            weekly_snapshots[index] = _compact_weekly_snapshot(snapshot_now)


def _blend_metric(heuristic_value: float, llm_value: float, llm_weight: float) -> float:
    llm_weight = max(0.0, min(1.0, llm_weight))
    heuristic_weight = 1.0 - llm_weight
    return round((float(heuristic_value) * heuristic_weight) + (float(llm_value) * llm_weight), 4)


def _load_json_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_json_mapping(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
