from social_graph_service.models import GraphResult, Node
from social_graph_service.reporting import write_html_report


def test_write_html_report_creates_readable_file(tmp_path) -> None:
    result = GraphResult(
        nodes=[Node(node_id="self", label="You", node_type="person")],
        edges=[],
        summary={"chat_count": 1, "message_count": 5, "node_count": 1, "edge_count": 0},
    )
    summary = {
        "analysis_config": {"as_of_date": "2026-05-02"},
        "graph_summary": result.summary,
        "import_stats": {"files_scanned": 1},
        "snapshot_now": {
            "as_of_date": "2026-05-02",
            "network_snapshot": {"relationship_count": 0, "active_relationships": 0, "status_counts": {}},
            "top_relationships": [],
        },
        "weekly_snapshots": [],
        "person_reports": [],
        "chat_profiles": {"media_totals": {}, "top_media_chats": []},
    }
    output_path = tmp_path / "report.html"

    write_html_report(result, summary, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "Relationship Snapshot" in content
    assert "Selected Relationship" in content
