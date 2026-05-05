from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .models import GraphResult
from .pipeline import run_analysis
from .reporting import write_html_report


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local social graph from Telegram exports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a Telegram export.")
    analyze.add_argument("export_path", type=Path, help="Path to a Telegram export JSON file or folder.")
    analyze.add_argument("--output", type=Path, required=True, help="Directory for analysis artifacts.")
    analyze.add_argument("--self-name", type=str, default=None, help="Your display name in Telegram exports.")
    analyze.add_argument("--as-of-date", type=_parse_date, default=None, help="Evaluate the network as of YYYY-MM-DD.")
    analyze.add_argument("--start-date", type=_parse_date, default=None, help="Start date for weekly snapshots.")
    analyze.add_argument("--end-date", type=_parse_date, default=None, help="End date for weekly snapshots.")
    analyze.add_argument("--cadence-days", type=int, default=7, help="Cadence in days for temporal snapshots.")
    analyze.add_argument("--window-days", type=int, default=90, help="Main evidence window in days.")
    analyze.add_argument("--short-window-days", type=int, default=30, help="Short recency window in days.")
    analyze.add_argument("--with-llm", action="store_true", help="Enable local Ollama emotional scoring.")
    analyze.add_argument("--with-voice-asr", action="store_true", help="Enable fully local voice transcription for Telegram voice/audio messages.")

    report = subparsers.add_parser("report", help="Render an HTML report from graph artifacts.")
    report.add_argument("graph_json", type=Path, help="Path to graph.json.")
    report.add_argument("--summary-json", type=Path, required=True, help="Path to summary.json.")
    report.add_argument("--output", type=Path, required=True, help="Target HTML report path.")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "analyze":
        summary = run_analysis(
            args.export_path,
            args.output,
            self_name=args.self_name,
            as_of_date=args.as_of_date,
            start_date=args.start_date,
            end_date=args.end_date,
            cadence_days=args.cadence_days,
            window_days=args.window_days,
            short_window_days=args.short_window_days,
            with_llm=args.with_llm,
            with_voice_asr=args.with_voice_asr,
        )
        compact = {
            "output_path": summary["output_path"],
            "as_of_date": summary["analysis_config"]["as_of_date"],
            "weekly_points": len(summary["weekly_snapshots"]),
            "relationship_count": summary["snapshot_now"]["network_snapshot"]["relationship_count"],
            "active_relationships": summary["snapshot_now"]["network_snapshot"]["active_relationships"],
        }
        print(json.dumps(compact, ensure_ascii=False, indent=2))
    elif args.command == "report":
        graph = GraphResult.from_dict(json.loads(args.graph_json.read_text(encoding="utf-8")))
        summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
        write_html_report(graph, summary, args.output)
        print(json.dumps({"report_path": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
