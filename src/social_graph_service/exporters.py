from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from xml.etree.ElementTree import Element, ElementTree, SubElement

from .models import GraphResult
from .reporting import write_html_report


def write_outputs(result: GraphResult, output_dir: Path, extra_summary: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "graph.json").open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, ensure_ascii=False, indent=2)

    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(extra_summary, handle, ensure_ascii=False, indent=2)

    _write_named_json(output_dir / "snapshot_now.json", extra_summary.get("snapshot_now", {}))
    _write_named_json(output_dir / "weekly_snapshots.json", extra_summary.get("weekly_snapshots", []))
    _write_named_json(output_dir / "relationship_timeseries.json", extra_summary.get("relationship_timeseries", []))
    _write_named_json(output_dir / "network_timeseries.json", extra_summary.get("network_timeseries", []))
    _write_named_json(output_dir / "person_reports.json", extra_summary.get("person_reports", []))

    _write_graphml(result, output_dir / "graph.graphml")
    write_html_report(result, extra_summary, output_dir / "report.html")


def _write_named_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _write_graphml(result: GraphResult, path: Path) -> None:
    root = Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    SubElement(root, "key", id="label", **{"for": "node"}, attr_name="label", attr_type="string")
    SubElement(root, "key", id="relation_type", **{"for": "edge"}, attr_name="relation_type", attr_type="string")
    SubElement(root, "key", id="metrics_json", **{"for": "edge"}, attr_name="metrics_json", attr_type="string")
    graph = SubElement(root, "graph", edgedefault="directed")

    for node in result.nodes:
        node_el = SubElement(graph, "node", id=node.node_id)
        data_el = SubElement(node_el, "data", key="label")
        data_el.text = node.label

    for index, edge in enumerate(result.edges, start=1):
        edge_el = SubElement(
            graph,
            "edge",
            id=f"e{index}",
            source=edge.source,
            target=edge.target,
        )
        relation_el = SubElement(edge_el, "data", key="relation_type")
        relation_el.text = edge.relation_type
        metrics_el = SubElement(edge_el, "data", key="metrics_json")
        metrics_el.text = json.dumps(edge.metrics, ensure_ascii=False)

    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
