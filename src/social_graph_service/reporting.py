from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import GraphResult


def write_html_report(result: GraphResult, run_summary: Dict[str, Any], output_path: Path) -> None:
    output_path.write_text(render_html_report(result, run_summary), encoding="utf-8")


def render_html_report(result: GraphResult, run_summary: Dict[str, Any]) -> str:
    payload = _build_dashboard_payload(result, run_summary)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Relationship Snapshot</title>
  <style>
    :root {{
      --bg: #f6f2ec;
      --bg-soft: #fbfaf8;
      --ink: #201814;
      --muted: #6f6761;
      --line: #ddd6cf;
      --card: rgba(255, 255, 255, 0.88);
      --shadow: 0 16px 40px rgba(53, 40, 24, 0.08);
      --green: #2b9d61;
      --red: #c15b57;
      --amber: #d6a545;
      --dark: #241d19;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.82) 0%, transparent 36%),
        linear-gradient(180deg, #f7f3ee 0%, var(--bg) 100%);
    }}
    .page {{
      max-width: none;
      margin: 0 auto;
      padding: 22px 24px 48px;
    }}
    .hero {{
      display: grid;
      gap: 8px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(30px, 3.2vw, 42px);
      line-height: 0.96;
      letter-spacing: -0.04em;
    }}
    .lede {{
      margin: 0;
      max-width: 1040px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.65;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .metric-card, .main-card, .side-card, .strip-card {{
      background: var(--card);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .metric-card {{
      border-radius: 18px;
      padding: 16px;
    }}
    .metric-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--muted);
    }}
    .metric-value {{
      margin-top: 8px;
      font-size: 30px;
      font-weight: 700;
      letter-spacing: -0.04em;
    }}
    .metric-sub {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }}
    .dashboard {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 16px;
      align-items: start;
    }}
    .main-card {{
      border-radius: 26px;
      padding: 16px;
      min-height: 860px;
    }}
    .side-card {{
      border-radius: 24px;
      padding: 18px;
      position: sticky;
      top: 18px;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 12px;
      align-items: center;
      margin-bottom: 14px;
    }}
    .toolbar-group {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.45);
    }}
    .toolbar-label {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.09em;
    }}
    button, input[type="range"] {{
      font: inherit;
    }}
    .segmented button {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      padding: 8px 12px;
      color: var(--ink);
      cursor: pointer;
    }}
    .segmented button.active {{
      background: var(--dark);
      color: #fff;
      border-color: var(--dark);
    }}
    .timeline-caption, .board-caption {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .timeline-scroll {{
      overflow-x: auto;
      padding-bottom: 6px;
    }}
    .timeline {{
      display: flex;
      gap: 8px;
      min-width: max-content;
    }}
    .time-pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      background: #fff;
      cursor: pointer;
      font-size: 13px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .time-pill.active {{
      background: var(--ink);
      color: #fff;
      border-color: var(--ink);
    }}
    .board-shell {{
      display: grid;
      gap: 12px;
      min-height: 640px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .legend-chip {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-swatch {{
      width: 16px;
      height: 16px;
      border-radius: 999px;
      border: 1px solid rgba(0,0,0,0.08);
    }}
    .bubble-board {{
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      align-content: flex-start;
      justify-content: center;
      min-height: 560px;
      padding: 18px 8px 8px;
      border-radius: 22px;
      border: 1px solid rgba(221, 210, 196, 0.9);
      background:
        radial-gradient(circle at center, rgba(255,255,255,0.82) 0%, rgba(255,255,255,0.3) 65%, transparent 100%),
        linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.08));
    }}
    .bubble-button {{
      position: relative;
      border: none;
      padding: 0;
      background: transparent;
      cursor: pointer;
    }}
    .bubble {{
      position: relative;
      border-radius: 999px;
      overflow: hidden;
      border: 2px solid rgba(255,255,255,0.8);
      box-shadow: 0 14px 32px rgba(44, 33, 21, 0.14);
      isolation: isolate;
      background: rgba(255,255,255,0.18);
    }}
    .bubble.selected {{
      border-color: var(--dark);
      box-shadow: 0 0 0 5px rgba(36, 29, 25, 0.14), 0 18px 42px rgba(44, 33, 21, 0.18);
    }}
    .ring {{
      position: absolute;
      inset: 0;
      border-radius: 999px;
    }}
    .ring.bond-ring {{
      inset: 10%;
    }}
    .bubble-core {{
      position: absolute;
      inset: 20%;
      display: grid;
      place-items: center;
      text-align: center;
      padding: 8px;
      border-radius: 999px;
      background: rgba(250, 248, 244, 0.9);
      border: 1px solid rgba(255,255,255,0.7);
      color: var(--dark);
    }}
    .bubble-name {{
      display: -webkit-box;
      width: 100%;
      font-weight: 500;
      line-height: 1.08;
      letter-spacing: -0.02em;
      overflow: hidden;
      text-overflow: ellipsis;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }}
    .trend-badge {{
      position: absolute;
      top: -6px;
      right: -6px;
      min-width: 34px;
      height: 34px;
      padding: 0 10px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: rgba(31, 26, 23, 0.92);
      color: #fff;
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.02em;
      box-shadow: 0 10px 24px rgba(31,26,23,0.22);
    }}
    .side-title {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .detail-name {{
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.04em;
      line-height: 1.02;
      margin-bottom: 6px;
    }}
    .detail-sub {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
      margin-bottom: 14px;
    }}
    .detail-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .detail-pills span {{
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.7);
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
    }}
    .detail-bubble-wrap {{
      display: grid;
      place-items: center;
      margin: 12px 0 18px;
    }}
    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .detail-box {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.5);
      padding: 12px;
    }}
    .detail-box .k {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .detail-box .v {{
      margin-top: 6px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.03em;
    }}
    .baseline-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .baseline-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.55);
      padding: 12px;
      text-align: center;
    }}
    .baseline-card .label {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .baseline-card .value {{
      margin-top: 6px;
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}
    .baseline-card .sub {{
      margin-top: 4px;
      font-size: 12px;
      color: var(--muted);
    }}
    .comparison-title {{
      margin: 0 0 8px;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .profile-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .scale-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.55);
      padding: 12px;
    }}
    .scale-card .label {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .scale-card .value-row {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 8px;
      margin-top: 6px;
    }}
    .scale-card .value {{
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}
    .scale-card .sub {{
      font-size: 12px;
      color: var(--muted);
    }}
    .scale-bar {{
      margin-top: 10px;
      height: 9px;
      border-radius: 999px;
      background: rgba(31, 26, 23, 0.08);
      overflow: hidden;
    }}
    .scale-bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #d56f68 0%, #e0bf60 48%, #79c487 100%);
    }}
    .empty {{
      border: 1px dashed var(--line);
      border-radius: 16px;
      padding: 18px;
      color: var(--muted);
      background: rgba(255,255,255,0.38);
    }}
    .strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .strip-card {{
      border-radius: 18px;
      padding: 14px;
    }}
    .strip-title {{
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .strip-value {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}
    .strip-sub {{
      margin-top: 4px;
      font-size: 13px;
      color: var(--muted);
    }}
    @media (max-width: 1120px) {{
      .dashboard {{
        grid-template-columns: 1fr;
      }}
      .side-card {{
        position: static;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>Relationship Snapshot</h1>
      <p class="lede">Each bubble shows two concentric directional rings. The outer ring is warmth, the inner ring is bond. On each ring, the left half is your side and the right half is the other side. Greener means warmer or stronger; redder means colder or weaker. Open a relationship to inspect the full profile behind those rings.</p>
    </section>

    <section class="metrics" id="metrics"></section>

    <section class="dashboard">
      <section class="main-card">
        <div class="toolbar">
          <div class="toolbar-group segmented" id="sort-switch">
            <span class="toolbar-label">Sort</span>
            <button data-sort="volume" class="active">Volume</button>
            <button data-sort="warmth">Warmth</button>
            <button data-sort="bond">Bond</button>
            <button data-sort="change">Change</button>
          </div>
          <div class="toolbar-group segmented" id="filter-switch">
            <span class="toolbar-label">Filter</span>
            <button data-filter="all" class="active">All</button>
            <button data-filter="active">Active</button>
            <button data-filter="warmer">Warmer</button>
            <button data-filter="cooling">Cooling</button>
          </div>
          <div class="toolbar-group">
            <span class="toolbar-label">Top N</span>
            <input type="range" id="top-n-range" min="10" max="120" value="15" step="1">
            <span id="top-n-value">15</span>
          </div>
        </div>

        <div class="timeline-caption">The timeline changes the state estimate date. Each point is a weekly snapshot, not just messages from that day.</div>
        <div class="timeline-scroll">
          <div class="timeline" id="timeline"></div>
        </div>

        <div class="board-shell">
          <div class="legend">
            <div class="legend-chip"><span class="legend-swatch" style="background:#77c78c"></span><span>stronger / warmer</span></div>
            <div class="legend-chip"><span class="legend-swatch" style="background:#f0c763"></span><span>mixed</span></div>
            <div class="legend-chip"><span class="legend-swatch" style="background:#e07d78"></span><span>weaker / colder</span></div>
            <div class="legend-chip"><span>Outer ring: Warmth</span></div>
            <div class="legend-chip"><span>Inner ring: Bond</span></div>
            <div class="legend-chip"><span>Volume:</span></div>
            <div class="legend-chip"><span>↑↑ strong growth</span></div>
            <div class="legend-chip"><span>↑ moderate growth</span></div>
            <div class="legend-chip"><span>↔ stable</span></div>
            <div class="legend-chip"><span>↓ moderate decline</span></div>
            <div class="legend-chip"><span>↓↓ sharp decline</span></div>
          </div>
          <div class="board-caption">Volume is measured from the 90-day evidence window. Warmth index is anchored at 100 and compared to a weighted baseline from roughly 7, 30, and 90 days earlier.</div>
          <div class="bubble-board" id="bubble-board"></div>
        </div>

        <div class="strip" id="snapshot-strip"></div>
      </section>

      <aside class="side-card">
        <div class="side-title">Selected Relationship</div>
        <div class="detail-name" id="detail-name"></div>
        <div class="detail-sub" id="detail-sub"></div>
        <div class="detail-pills" id="detail-pills"></div>
        <div class="detail-bubble-wrap" id="detail-bubble-wrap"></div>
        <div class="detail-grid" id="detail-grid"></div>
        <div class="comparison-title">Relationship Profile</div>
        <div class="profile-grid" id="profile-grid"></div>
        <div class="comparison-title">Volume Delta</div>
        <div class="baseline-grid" id="volume-grid"></div>
        <div class="comparison-title">Warmth Index</div>
        <div class="baseline-grid" id="warmth-grid"></div>
      </aside>
    </section>
  </div>

  <script>
    const payload = {data_json};
    const relationshipSeries = payload.relationshipSeries || [];
    const weeklySnapshots = payload.weeklySnapshots || [];
    const personReportsById = new Map((payload.personReports || []).map((item) => [item.peer_id, item]));
    const dates = payload.availableDates || [payload.asOfDate];

    const state = {{
      selectedDate: payload.asOfDate || dates[0] || '',
      selectedPeerId: null,
      sort: 'volume',
      filter: 'all',
      topN: 15,
    }};

    const metricsEl = document.getElementById('metrics');
    const timelineEl = document.getElementById('timeline');
    const boardEl = document.getElementById('bubble-board');
    const snapshotStrip = document.getElementById('snapshot-strip');
    const detailName = document.getElementById('detail-name');
    const detailSub = document.getElementById('detail-sub');
    const detailPills = document.getElementById('detail-pills');
    const detailBubbleWrap = document.getElementById('detail-bubble-wrap');
    const detailGrid = document.getElementById('detail-grid');
    const profileGrid = document.getElementById('profile-grid');
    const volumeGrid = document.getElementById('volume-grid');
    const warmthGrid = document.getElementById('warmth-grid');
    const topNRange = document.getElementById('top-n-range');
    const topNValue = document.getElementById('top-n-value');

    document.getElementById('sort-switch').addEventListener('click', (event) => {{
      const value = event.target.dataset.sort;
      if (!value) return;
      state.sort = value;
      setActiveButtons('sort-switch', value, 'sort');
      render();
    }});

    document.getElementById('filter-switch').addEventListener('click', (event) => {{
      const value = event.target.dataset.filter;
      if (!value) return;
      state.filter = value;
      setActiveButtons('filter-switch', value, 'filter');
      render();
    }});

    topNRange.addEventListener('input', () => {{
      state.topN = Number(topNRange.value);
      topNValue.textContent = String(state.topN);
      render();
    }});

    function setActiveButtons(containerId, value, key) {{
      document.querySelectorAll(`#${{containerId}} button`).forEach((button) => {{
        button.classList.toggle('active', button.dataset[key] === value);
      }});
    }}

    function htmlEscape(value) {{
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function formatNumber(value) {{
      if (value == null) return 'n/a';
      if (typeof value === 'number') {{
        return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
      }}
      return String(value);
    }}

    function formatDateLabel(value) {{
      if (!value) return 'n/a';
      const date = value.includes('T') ? new Date(value) : new Date(`${{value}}T00:00:00Z`);
      return new Intl.DateTimeFormat('en-GB', {{
        day: '2-digit',
        month: 'short',
        year: '2-digit',
        timeZone: 'UTC',
      }}).format(date);
    }}

    function parseDateOnly(value) {{
      return new Date(`${{value}}T00:00:00Z`);
    }}

    function relationshipSnapshot(series, asOfDate) {{
      return (series.snapshots || []).find((item) => item.as_of_date === asOfDate) || null;
    }}

    function meanWarmth(snapshot) {{
      return ((snapshot?.warmth_index_out || snapshot?.warmth_out || 0) + (snapshot?.warmth_index_in || snapshot?.warmth_in || 0)) / 2;
    }}

    function integratedColor(snapshot) {{
      return snapshot?.integrated_color_score ?? (((snapshot?.warmth_index || 0) + (snapshot?.bond_index || 0)) / 2);
    }}

    function clamp(value, min, max) {{
      return Math.max(min, Math.min(max, Number(value) || 0));
    }}

    function trendSymbol(deltaRatio) {{
      if (deltaRatio >= 0.35) return '↑↑';
      if (deltaRatio >= 0.12) return '↑';
      if (deltaRatio <= -0.35) return '↓↓';
      if (deltaRatio <= -0.12) return '↓';
      return '↔';
    }}

    function trendLabel(deltaRatio) {{
      if (deltaRatio >= 0.35) return 'Sharp volume growth';
      if (deltaRatio >= 0.12) return 'Volume growing';
      if (deltaRatio <= -0.35) return 'Sharp volume decline';
      if (deltaRatio <= -0.12) return 'Volume declining';
      return 'Volume stable';
    }}

    function warmthColor(score) {{
      const clamped = Math.max(0, Math.min(1, score));
      const hue = clamped * 120;
      return `hsl(${{hue}} 66% 68%)`;
    }}

    function buildScoreNormalizer(rows, getter) {{
      const values = rows
        .map((row) => Number(getter(row)) || 0)
        .filter((value) => Number.isFinite(value));
      if (!values.length) {{
        return (score) => Math.max(0, Math.min(1, Number(score) || 0));
      }}
      const min = Math.min(...values);
      const max = Math.max(...values);
      const spread = max - min;
      if (spread < 0.035) {{
        return (score) => Math.max(0, Math.min(1, 0.5 + ((((Number(score) || 0) - ((min + max) / 2)) * 8))));
      }}
      return (score) => Math.max(0, Math.min(1, (((Number(score) || 0) - min) / spread)));
    }}

    function sizeForVolume(value, minValue, maxValue) {{
      const safe = Math.max(0, value || 0);
      const minSafe = Math.max(0, minValue || 0);
      const maxSafe = Math.max(minSafe + 1, maxValue || 1);
      const minLog = Math.log1p(minSafe);
      const maxLog = Math.log1p(maxSafe);
      const currentLog = Math.log1p(safe);
      const spread = Math.max(0.0001, maxLog - minLog);
      const normalized = Math.max(0, Math.min(1, (currentLog - minLog) / spread));
      const curved = Math.pow(normalized, 0.82);
      return Math.round(102 + curved * 72);
    }}

    function buildRow(series) {{
      const snapshot = relationshipSnapshot(series, state.selectedDate);
      if (!snapshot) return null;
      const currentWarmth = meanWarmth(snapshot);
      const evidenceGate = snapshot.evidence_gate || (0.28 + 0.72 * clamp(snapshot.confidence_score || 0, 0, 1));
      const volume7vs28 = rateDelta(snapshot.messages_total_7d || 0, 7, snapshot.messages_total_28d || 0, 28);
      const volume28vs91 = rateDelta(snapshot.messages_total_28d || 0, 28, snapshot.messages_total_91d || 0, 91);
      const warmth7vs28 = indexFromRatio(currentWarmthWindow(snapshot, 7), currentWarmthWindow(snapshot, 28));
      const warmth28vs91 = indexFromRatio(currentWarmthWindow(snapshot, 28), currentWarmthWindow(snapshot, 91));
      const volumeDeltaRatio = volume7vs28.delta;
      return {{
        peer_id: series.peer_id,
        peer_label: series.peer_label,
        chat_name: series.chat_name,
        snapshot,
        currentWarmth,
        warmthIndexAbsolute: clamp((snapshot.warmth_index || currentWarmth) * evidenceGate, 0, 1),
        bondIndexAbsolute: clamp((snapshot.bond_index || snapshot.tie_strength_score || 0) * evidenceGate, 0, 1),
        integratedColor: clamp(integratedColor(snapshot) * evidenceGate, 0, 1),
        warmthIndex: warmth7vs28,
        volume7vs28,
        volume28vs91,
        warmth7vs28,
        warmth28vs91,
        volumeDeltaRatio,
        trendSymbol: trendSymbol(volumeDeltaRatio),
        trendLabel: trendLabel(volumeDeltaRatio),
        evidenceGate,
      }};
    }}

    function isEligibleRow(row) {{
      const total = row.snapshot.messages_total_90d || 0;
      const reciprocity = row.snapshot.reciprocity || 0;
      if (total < 8) return false;
      if (reciprocity <= 0.02) return false;
      if (total < 20 && reciprocity < 0.10) return false;
      if ((row.snapshot.confidence_score || 0) < 0.12) return false;
      return true;
    }}

    function passesFilter(row) {{
      if (state.filter === 'all') return true;
      if (state.filter === 'active') return ['active_mutual','active_asymmetric','revived','new_connection'].includes(row.snapshot.status);
      if (state.filter === 'warmer') return row.warmthIndexAbsolute >= 0.58 || row.warmth7vs28 > 103;
      if (state.filter === 'cooling') return row.warmth7vs28 < 97 || row.volumeDeltaRatio < -0.12;
      return true;
    }}

    function sortMetric(row) {{
      if (state.sort === 'warmth') return (row.warmthIndexAbsolute * Math.max(row.confidence || 0, row.evidenceGate || 0)) * 1000 + row.snapshot.tie_strength_score;
      if (state.sort === 'bond') return (row.bondIndexAbsolute * Math.max(row.confidence || 0, row.evidenceGate || 0)) * 1000 + row.snapshot.tie_strength_score;
      if (state.sort === 'change') return Math.abs(row.volumeDeltaRatio) * 1000 + Math.abs(row.warmth7vs28 - 100) * 10 + row.snapshot.tie_strength_score;
      return row.snapshot.messages_total_90d || 0;
    }}

    function computeRows() {{
      const allRows = relationshipSeries
        .map(buildRow)
        .filter(Boolean)
        .filter(isEligibleRow)
        .filter(passesFilter)
        .sort((a, b) => sortMetric(b) - sortMetric(a));
      return {{
        allRows,
        visibleRows: allRows.slice(0, state.topN),
      }};
    }}

    function weightedIndex(items, getter) {{
      if (!items.length) return 100;
      const total = items.reduce((sum, item) => sum + Math.max(1, item.snapshot.messages_total_90d || 0), 0);
      const score = items.reduce((sum, item) => sum + getter(item) * Math.max(1, item.snapshot.messages_total_90d || 0), 0) / total;
      return Math.round(score);
    }}

    function renderMetrics(allRows, visibleRows) {{
      const snapshot = payload.networkSnapshotsByDate[state.selectedDate] || payload.networkSnapshot || {{}};
      const warmth7vs28 = weightedIndex(allRows, (item) => item.warmth7vs28);
      const warmth28vs91 = weightedIndex(allRows, (item) => item.warmth28vs91);
      const items = [
        ['As of', formatDateLabel(state.selectedDate), 'selected snapshot date'],
        ['Active ties', snapshot.active_relationships || 0, 'currently active relationships'],
        ['Warmth 7d vs 28d', warmth7vs28, '100 = same daily warmth'],
        ['Warmth 28d vs 91d', warmth28vs91, '100 = same daily warmth'],
        ['Mean warmth index', formatScale01(snapshot.mean_warmth_index || 0), '0 = cold, 1 = warm'],
        ['Mean bond index', formatScale01(snapshot.mean_bond_index || 0), '0 = weak, 1 = strong'],
      ];
      metricsEl.innerHTML = items.map(([label, value, sub]) => `
        <div class="metric-card">
          <div class="metric-label">${{htmlEscape(label)}}</div>
          <div class="metric-value">${{htmlEscape(formatNumber(value))}}</div>
          <div class="metric-sub">${{htmlEscape(sub)}}</div>
        </div>
      `).join('');
    }}

    function renderTimeline() {{
      timelineEl.innerHTML = dates.map((date) => `
        <button class="time-pill ${{date === state.selectedDate ? 'active' : ''}}" data-date="${{date}}">
          ${{htmlEscape(formatDateLabel(date))}}
        </button>
      `).join('');
      timelineEl.querySelectorAll('.time-pill').forEach((button) => {{
        button.addEventListener('click', () => {{
          state.selectedDate = button.dataset.date;
          render();
        }});
      }});
    }}

    function renderBoard(rows) {{
      if (!rows.length) {{
        boardEl.innerHTML = '<div class="empty">No relationships visible for this filter or date.</div>';
        return;
      }}
      const volumes = rows.map((row) => row.snapshot.messages_total_90d || 0);
      const maxVolume = Math.max(...volumes, 1);
      const minVolume = Math.min(...volumes, maxVolume);
      const normalizeWarmth = buildScoreNormalizer(
        rows.flatMap((row) => [
          {{ value: row.snapshot.warmth_index_out || 0 }},
          {{ value: row.snapshot.warmth_index_in || 0 }},
        ]),
        (item) => item.value,
      );
      const normalizeBond = buildScoreNormalizer(
        rows.flatMap((row) => [
          {{ value: row.snapshot.bond_index_out || 0 }},
          {{ value: row.snapshot.bond_index_in || 0 }},
        ]),
        (item) => item.value,
      );
      boardEl.innerHTML = rows.map((row) => {{
        const size = sizeForVolume(row.snapshot.messages_total_90d || 0, minVolume, maxVolume);
        const selected = row.peer_id === state.selectedPeerId;
        const warmthLeft = warmthColor(normalizeWarmth(row.snapshot.warmth_index_out || 0));
        const warmthRight = warmthColor(normalizeWarmth(row.snapshot.warmth_index_in || 0));
        const bondLeft = warmthColor(normalizeBond(row.snapshot.bond_index_out || 0));
        const bondRight = warmthColor(normalizeBond(row.snapshot.bond_index_in || 0));
        const fontSize = Math.max(10, Math.min(16, Math.round(size / 9.8)));
        const name = shortLabel(row.peer_label, size >= 150 ? 22 : 18);
        return `
          <button class="bubble-button" data-peer="${{htmlEscape(row.peer_id)}}" title="${{htmlEscape(row.peer_label || row.peer_id)}}">
            <div class="trend-badge">${{htmlEscape(row.trendSymbol)}}</div>
            <div class="bubble ${{selected ? 'selected' : ''}}" style="width:${{size}}px;height:${{size}}px;">
              <div class="ring warmth-ring" style="background:linear-gradient(90deg, ${{warmthLeft}} 0 50%, ${{warmthRight}} 50% 100%);"></div>
              <div class="ring bond-ring" style="background:linear-gradient(90deg, ${{bondLeft}} 0 50%, ${{bondRight}} 50% 100%);"></div>
              <div class="bubble-core">
                <span class="bubble-name" style="font-size:${{fontSize}}px;">${{htmlEscape(name)}}</span>
              </div>
            </div>
          </button>
        `;
      }}).join('');
      boardEl.querySelectorAll('.bubble-button').forEach((button) => {{
        button.addEventListener('click', () => {{
          state.selectedPeerId = button.dataset.peer;
          render();
        }});
      }});
    }}

    function shortLabel(label, limit) {{
      if (!label) return 'Unknown';
      if (label.length <= limit) return label;
      return label.slice(0, limit - 1) + '…';
    }}

    function renderDetail(rows) {{
      const selected = rows.find((row) => row.peer_id === state.selectedPeerId) || rows[0] || null;
      if (!selected) {{
        detailName.textContent = 'No visible relationships';
        detailSub.textContent = 'Adjust the filter, date, or top-N threshold.';
        detailPills.innerHTML = '';
        detailBubbleWrap.innerHTML = '';
        detailGrid.innerHTML = '';
        profileGrid.innerHTML = '';
        volumeGrid.innerHTML = '';
        warmthGrid.innerHTML = '';
        return;
      }}
      state.selectedPeerId = selected.peer_id;
      detailName.textContent = selected.peer_label || selected.peer_id;
      detailSub.textContent = `last contact ${{formatDateLabel(selected.snapshot.last_contact_at || '')}}`;
      detailPills.innerHTML = '';
      detailBubbleWrap.innerHTML = renderDetailBubble(selected, rows);
      const detailItems = [
        ['Messages 90d', selected.snapshot.messages_total_90d],
        ['Reciprocity', formatScale01(selected.snapshot.reciprocity)],
        ['Warmth index', formatScale01(selected.snapshot.warmth_index || selected.warmthIndexAbsolute)],
        ['Bond index', formatScale01(selected.snapshot.bond_index || selected.bondIndexAbsolute)],
        ['Confidence', formatScale01(selected.snapshot.confidence_score || 0)],
      ];
      detailGrid.innerHTML = detailItems.map(([label, value]) => `
        <div class="detail-box">
          <div class="k">${{htmlEscape(label)}}</div>
          <div class="v">${{htmlEscape(formatNumber(value))}}</div>
        </div>
      `).join('');
      const profileItems = [
        ['You → warmth', selected.snapshot.warmth_out || 0, 'tone from your side', false],
        ['Them → warmth', selected.snapshot.warmth_in || 0, 'tone from their side', false],
        ['You → warmth index', selected.snapshot.warmth_index_out || 0, 'integrated emotional warmth', false],
        ['Them → warmth index', selected.snapshot.warmth_index_in || 0, 'integrated emotional warmth', false],
        ['You → support', selected.snapshot.support_out || 0, 'care / reassurance / help', false],
        ['Them → support', selected.snapshot.support_in || 0, 'care / reassurance / help', false],
        ['You → media intimacy', selected.snapshot.media_intimacy_out || 0, 'voice / photo / sticker closeness', false],
        ['Them → media intimacy', selected.snapshot.media_intimacy_in || 0, 'voice / photo / sticker closeness', false],
        ['You → playfulness', selected.snapshot.media_playfulness_out || 0, 'lighter expressive media', false],
        ['Them → playfulness', selected.snapshot.media_playfulness_in || 0, 'lighter expressive media', false],
        ['You → engagement', selected.snapshot.engagement_out || 0, 'who carries the exchange', false],
        ['Them → engagement', selected.snapshot.engagement_in || 0, 'who carries the exchange', false],
        ['You → bond index', selected.snapshot.bond_index_out || 0, 'strength from your side', false],
        ['Them → bond index', selected.snapshot.bond_index_in || 0, 'strength from their side', false],
        ['You → responsiveness', selected.snapshot.responsiveness_out || 0, 'speed / consistency', false],
        ['Them → responsiveness', selected.snapshot.responsiveness_in || 0, 'speed / consistency', false],
        ['You → formality', selected.snapshot.formality_out || 0, 'higher means more formal', true],
        ['Them → formality', selected.snapshot.formality_in || 0, 'higher means more formal', true],
        ['Stability', selected.snapshot.stability_score || 0, 'active across recent weeks', false],
        ['Depth', selected.snapshot.depth_score || 0, 'longer / more personal text', false],
        ['Tension', selected.snapshot.mutual_tension || 0, 'higher means more friction', true],
      ];
      profileGrid.innerHTML = profileItems.map(([label, value, sub, invert]) => renderScaleCard(label, value, sub, invert)).join('');
      volumeGrid.innerHTML = [
        ['7d vs 28d', signedPercent(selected.volume7vs28.delta), 'daily msg rate'],
        ['28d vs 91d', signedPercent(selected.volume28vs91.delta), 'daily msg rate'],
      ].map(([label, value, sub]) => `
        <div class="baseline-card">
          <div class="label">${{htmlEscape(label)}}</div>
          <div class="value">${{htmlEscape(formatNumber(value))}}</div>
          <div class="sub">${{htmlEscape(sub)}}</div>
        </div>
      `).join('');
      warmthGrid.innerHTML = [
        ['7d vs 28d', Math.round(selected.warmth7vs28), '100 = neutral'],
        ['28d vs 91d', Math.round(selected.warmth28vs91), '100 = neutral'],
      ].map(([label, value, sub]) => `
        <div class="baseline-card">
          <div class="label">${{htmlEscape(label)}}</div>
          <div class="value">${{htmlEscape(formatNumber(value))}}</div>
          <div class="sub">${{htmlEscape(sub)}}</div>
        </div>
      `).join('');
    }}

    function renderDetailBubble(row, rows) {{
      const normalizeWarmth = buildScoreNormalizer(
        rows.flatMap((item) => [
          {{ value: item.snapshot.warmth_index_out || 0 }},
          {{ value: item.snapshot.warmth_index_in || 0 }},
        ]),
        (item) => item.value,
      );
      const normalizeBond = buildScoreNormalizer(
        rows.flatMap((item) => [
          {{ value: item.snapshot.bond_index_out || 0 }},
          {{ value: item.snapshot.bond_index_in || 0 }},
        ]),
        (item) => item.value,
      );
      const warmthLeft = warmthColor(normalizeWarmth(row.snapshot.warmth_index_out || 0));
      const warmthRight = warmthColor(normalizeWarmth(row.snapshot.warmth_index_in || 0));
      const bondLeft = warmthColor(normalizeBond(row.snapshot.bond_index_out || 0));
      const bondRight = warmthColor(normalizeBond(row.snapshot.bond_index_in || 0));
      return `
        <div class="bubble selected" style="width:182px;height:182px;">
          <div class="ring warmth-ring" style="background:linear-gradient(90deg, ${{warmthLeft}} 0 50%, ${{warmthRight}} 50% 100%);"></div>
          <div class="ring bond-ring" style="background:linear-gradient(90deg, ${{bondLeft}} 0 50%, ${{bondRight}} 50% 100%);"></div>
          <div class="bubble-core">
            <span class="bubble-name" style="font-size:16px;">${{htmlEscape(shortLabel(row.peer_label, 28))}}</span>
          </div>
        </div>
      `;
    }}

    function renderScaleCard(label, value, sub, invert = false) {{
      const clamped = Math.max(0, Math.min(1, Number(value) || 0));
      const barValue = invert ? 1 - clamped : clamped;
      return `
        <div class="scale-card">
          <div class="label">${{htmlEscape(label)}}</div>
          <div class="value-row">
            <div class="value">${{htmlEscape(formatScale01(clamped))}}</div>
            <div class="sub">${{htmlEscape(sub)}}</div>
          </div>
          <div class="scale-bar"><div class="scale-bar-fill" style="width:${{Math.round(barValue * 100)}}%"></div></div>
        </div>
      `;
    }}

    function renderSnapshotStrip(allRows) {{
      const recent = weeklySnapshots.slice(-6);
      if (!recent.length) {{
        snapshotStrip.innerHTML = '<div class="empty">Run with a date range to populate weekly network snapshots.</div>';
        return;
      }}
      const currentIndex = weightedIndex(allRows, (item) => item.warmth7vs28);
      snapshotStrip.innerHTML = recent.map((item) => `
        <div class="strip-card">
          <div class="strip-title">${{htmlEscape(formatDateLabel(item.as_of_date))}}</div>
          <div class="strip-value">${{htmlEscape(formatNumber(item.active_relationships || 0))}}</div>
          <div class="strip-sub">active ties</div>
          <div class="strip-sub">mean closeness ${{htmlEscape(formatNumber(item.mean_closeness || 0))}}</div>
          ${{item.as_of_date === state.selectedDate ? `<div class="strip-sub">warmth index ${{currentIndex}}</div>` : ''}}
        </div>
      `).join('');
    }}

    function signedPercent(value) {{
      if (value == null) return 'n/a';
      return `${{value >= 0 ? '+' : ''}}${{Math.round(value * 100)}}%`;
    }}

    function formatScale01(value) {{
      if (value == null) return 'n/a';
      return `${{Number(value).toFixed(3)}} / 1.0`;
    }}

    function indexFromRatio(shortMetric, longMetric) {{
      if (!longMetric || longMetric <= 0) return 100;
      return Math.max(40, Math.min(160, 100 * (shortMetric / longMetric)));
    }}

    function rateDelta(shortCount, shortDays, longCount, longDays) {{
      const shortRate = shortDays > 0 ? shortCount / shortDays : 0;
      const longRate = longDays > 0 ? longCount / longDays : 0;
      if (longRate <= 0) {{
        return {{ delta: shortRate > 0 ? 1 : 0, shortRate, longRate }};
      }}
      return {{ delta: (shortRate - longRate) / longRate, shortRate, longRate }};
    }}

    function currentWarmthWindow(snapshot, days) {{
      if (days <= 7) return snapshot.warmth_index_7d || ((snapshot.warmth_out_7d || 0) + (snapshot.warmth_in_7d || 0)) / 2;
      if (days <= 28) return snapshot.warmth_index_28d || ((snapshot.warmth_out_28d || 0) + (snapshot.warmth_in_28d || 0)) / 2;
      return snapshot.warmth_index_91d || ((snapshot.warmth_out_91d || 0) + (snapshot.warmth_in_91d || 0)) / 2;
    }}

    function render() {{
      const {{ allRows, visibleRows }} = computeRows();
      renderMetrics(allRows, visibleRows);
      renderTimeline();
      renderBoard(visibleRows);
      renderDetail(visibleRows);
      renderSnapshotStrip(allRows);
      topNValue.textContent = String(state.topN);
    }}

    render();
  </script>
</body>
</html>
"""


def _build_dashboard_payload(result: GraphResult, run_summary: Dict[str, Any]) -> Dict[str, Any]:
    snapshot_now = run_summary.get("snapshot_now", {})
    network_timeseries = run_summary.get("network_timeseries", [])
    network_snapshots_by_date = {item.get("as_of_date"): item for item in network_timeseries}
    if snapshot_now.get("network_snapshot"):
        network_snapshots_by_date.setdefault(
            snapshot_now["network_snapshot"].get("as_of_date"),
            snapshot_now["network_snapshot"],
        )

    relationship_series = run_summary.get("relationship_timeseries") or _snapshot_to_series(snapshot_now)

    return {
        "asOfDate": run_summary.get("analysis_config", {}).get("as_of_date") or snapshot_now.get("as_of_date"),
        "graphSummary": result.summary,
        "analysisConfig": run_summary.get("analysis_config", {}),
        "networkSnapshot": snapshot_now.get("network_snapshot", {}),
        "weeklySnapshots": run_summary.get("weekly_snapshots", []),
        "networkSnapshotsByDate": network_snapshots_by_date,
        "relationshipSeries": relationship_series,
        "personReports": run_summary.get("person_reports", []),
        "chatProfiles": {
            "media_totals": run_summary.get("chat_profiles", {}).get("media_totals", {}),
            "top_media_chats": run_summary.get("chat_profiles", {}).get("top_media_chats", [])[:18],
        },
        "availableDates": _available_dates(relationship_series, snapshot_now),
    }


def _snapshot_to_series(snapshot_now: Dict[str, Any]) -> List[Dict[str, Any]]:
    series = []
    for item in snapshot_now.get("relationships", []):
        pair = item.get("pair", {})
        outbound = item.get("outbound", {})
        inbound = item.get("inbound", {})
        series.append(
            {
                "peer_id": item.get("peer_id"),
                "peer_label": item.get("peer_label"),
                "chat_id": item.get("chat_id"),
                "chat_name": item.get("chat_name"),
                "snapshots": [
                    {
                        "as_of_date": item.get("as_of_date"),
                        "closeness_score": pair.get("closeness_score", 0),
                        "tie_strength_score": pair.get("tie_strength_score", 0),
                        "warmth_out": outbound.get("warmth_score", 0),
                        "warmth_in": inbound.get("warmth_score", 0),
                        "warmth_out_7d": outbound.get("warmth_score_7d", 0),
                        "warmth_in_7d": inbound.get("warmth_score_7d", 0),
                        "warmth_out_28d": outbound.get("warmth_score_28d", 0),
                        "warmth_in_28d": inbound.get("warmth_score_28d", 0),
                        "warmth_out_91d": outbound.get("warmth_score_91d", 0),
                        "warmth_in_91d": inbound.get("warmth_score_91d", 0),
                        "tension_out": outbound.get("tension_score", 0),
                        "tension_in": inbound.get("tension_score", 0),
                        "support_out": outbound.get("support_score", 0),
                        "support_in": inbound.get("support_score", 0),
                        "formality_out": outbound.get("formality_score", 0),
                        "formality_in": inbound.get("formality_score", 0),
                        "media_intimacy_out": outbound.get("media_intimacy_score", 0),
                        "media_intimacy_in": inbound.get("media_intimacy_score", 0),
                        "media_playfulness_out": outbound.get("media_playfulness_score", 0),
                        "media_playfulness_in": inbound.get("media_playfulness_score", 0),
                        "warmth_index_out": pair.get("warmth_index_out", outbound.get("warmth_index", 0)),
                        "warmth_index_in": pair.get("warmth_index_in", inbound.get("warmth_index", 0)),
                        "warmth_index_7d": pair.get("warmth_index_7d", 0),
                        "warmth_index_28d": pair.get("warmth_index_28d", 0),
                        "warmth_index_91d": pair.get("warmth_index_91d", 0),
                        "warmth_index": pair.get("warmth_index", 0),
                        "depth_out": outbound.get("depth_score", 0),
                        "depth_in": inbound.get("depth_score", 0),
                        "engagement_out": pair.get("engagement_out", 0),
                        "engagement_in": pair.get("engagement_in", 0),
                        "responsiveness_out": outbound.get("responsiveness_score", 0) or 0,
                        "responsiveness_in": inbound.get("responsiveness_score", 0) or 0,
                        "stability_score": pair.get("stability_score", pair.get("continuity_score", 0)),
                        "depth_score": pair.get("depth_score", 0),
                        "bond_index_out": pair.get("bond_index_out", 0),
                        "bond_index_in": pair.get("bond_index_in", 0),
                        "bond_index": pair.get("bond_index", pair.get("tie_strength_score", 0)),
                        "mutual_tension": pair.get("mutual_tension", 0),
                        "mutual_support": pair.get("mutual_support", 0),
                        "mutual_formality": pair.get("mutual_formality", 0),
                        "integrated_color_score": pair.get("integrated_color_score", pair.get("mutual_warmth", 0)),
                        "confidence_score": pair.get("confidence_score", 0),
                        "reciprocity": pair.get("reciprocity", 0),
                        "status": pair.get("status", "unknown"),
                        "messages_total_7d": pair.get("messages_total_7d", 0),
                        "messages_total_28d": pair.get("messages_total_28d", 0),
                        "messages_total_91d": pair.get("messages_total_91d", pair.get("messages_total_90d", 0)),
                        "messages_total_90d": pair.get("messages_total_90d", pair.get("messages_total", 0)),
                        "last_contact_at": pair.get("last_contact_at"),
                    }
                ],
            }
        )
    return series


def _available_dates(relationship_series: List[Dict[str, Any]], snapshot_now: Dict[str, Any]) -> List[str]:
    dates = sorted(
        {
            snapshot.get("as_of_date")
            for item in relationship_series
            for snapshot in item.get("snapshots", [])
            if snapshot.get("as_of_date")
        },
        reverse=True,
    )
    if dates:
        return dates
    as_of = snapshot_now.get("as_of_date")
    return [as_of] if as_of else []
