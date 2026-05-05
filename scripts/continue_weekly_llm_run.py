from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from social_graph_service.ollama import enrich_private_chat_scores
from social_graph_service.pipeline import (
    _filter_chats_as_of,
    _load_json_mapping,
    _save_json_mapping,
    _select_llm_chats_for_enrichment,
    run_analysis,
)
from social_graph_service.telegram_export import load_chats
from social_graph_service.temporal_analysis import TemporalConfig, analyze_temporal
from social_graph_service.voice_asr import VoiceAsrConfig, apply_voice_transcripts, enrich_voice_transcripts


def main() -> int:
    parser = argparse.ArgumentParser(description="Continue a weekly LLM-enriched social graph run until completion.")
    parser.add_argument("export_path")
    parser.add_argument("--output", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--cadence-days", type=int, default=7)
    parser.add_argument("--window-days", type=int, default=90)
    parser.add_argument("--short-window-days", type=int, default=30)
    parser.add_argument("--self-name", default=None)
    args = parser.parse_args()

    export_path = Path(args.export_path)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)

    print(f"[runner] loading chats from {export_path}", flush=True)
    chats, _import_stats = load_chats(export_path, self_name=args.self_name)
    export_root = export_path if export_path.is_dir() else export_path.parent

    voice_cache_path = output_dir / ".voice-asr-cache.json"
    voice_cache = _load_json_mapping(voice_cache_path)
    print("[runner] enriching voice transcripts from local cache/ASR", flush=True)
    voice_transcripts = enrich_voice_transcripts(
        chats,
        export_root,
        cache=voice_cache,
        config=VoiceAsrConfig(as_of_date=end_date, window_days=args.window_days + 1),
    )
    if voice_transcripts:
        chats = apply_voice_transcripts(chats, voice_transcripts)
        _save_json_mapping(voice_cache_path, voice_cache)
    print(
        f"[runner] voice transcripts ready for {len(voice_transcripts)} chats",
        flush=True,
    )

    temporal_config = TemporalConfig(
        self_label=args.self_name or "You",
        as_of_date=end_date,
        start_date=start_date,
        end_date=end_date,
        cadence_days=args.cadence_days,
        window_days=args.window_days,
        short_window_days=args.short_window_days,
    )
    print("[runner] building temporal snapshots", flush=True)
    temporal_payload = analyze_temporal(chats, temporal_config)

    progress_path = output_dir / ".llm-progress.json"
    cache_path = output_dir / ".llm-cache.json"
    progress = _load_json_mapping(progress_path)
    cache = _load_json_mapping(cache_path)

    for index, snapshot in enumerate(temporal_payload["snapshot_series"], start=1):
        snapshot_key = snapshot["as_of_date"]
        snapshot_date = date.fromisoformat(snapshot_key)
        visible_chats = _filter_chats_as_of(chats, snapshot_date)
        selected = _select_llm_chats_for_enrichment(visible_chats, snapshot)
        selected_ids = {chat.chat_id for chat in selected}
        existing = {
            chat_id: payload
            for chat_id, payload in progress.get(snapshot_key, {}).items()
            if chat_id in selected_ids
        }
        pending = [chat for chat in selected if chat.chat_id not in existing]
        progress[snapshot_key] = dict(existing)
        _save_json_mapping(progress_path, progress)
        print(
            f"[runner] {index}/{len(temporal_payload['snapshot_series'])} {snapshot_key} selected={len(selected)} resumed={len(existing)} pending={len(pending)}",
            flush=True,
        )
        if not pending:
            continue

        def on_chat_scored(chat_id: str, score: dict, from_cache: bool) -> None:
            progress[snapshot_key][chat_id] = score
            _save_json_mapping(progress_path, progress)
            if not from_cache:
                _save_json_mapping(cache_path, cache)
            source = "cache" if from_cache else "ollama"
            print(
                f"[runner] {snapshot_key} progress={len(progress[snapshot_key])}/{len(selected)} last={chat_id} via={source}",
                flush=True,
            )

        enrich_private_chat_scores(
            pending,
            cache=cache,
            on_chat_scored=on_chat_scored,
        )
        _save_json_mapping(cache_path, cache)
        _save_json_mapping(progress_path, progress)
        print(
            f"[runner] {snapshot_key} complete={len(progress[snapshot_key])}",
            flush=True,
        )

    print("[runner] all weekly snapshots processed, assembling final outputs", flush=True)
    run_analysis(
        export_path,
        output_dir,
        self_name=args.self_name,
        start_date=start_date,
        end_date=end_date,
        cadence_days=args.cadence_days,
        window_days=args.window_days,
        short_window_days=args.short_window_days,
        with_llm=True,
        with_voice_asr=True,
    )
    print("[runner] final outputs written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
