"""Dependency-free static reports generated from scored artifacts."""

from __future__ import annotations

import html
import json
from pathlib import Path

from .replay import read_trace
from .tournament import TournamentSummary


def write_leaderboard_html(summary: TournamentSummary, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for rank, standing in enumerate(summary.standings, 1):
        rows.append(
            "<tr>"
            f"<td>{rank}</td><td>{html.escape(str(standing['name']))}</td>"
            f"<td>{standing['rating']}</td><td>{standing['played']}</td>"
            f"<td>{standing['wins']}-{standing['draws']}-{standing['losses']}</td>"
            f"<td>{standing['points']}</td><td>{standing['cost_usd']}</td>"
            f"<td>{standing['input_tokens']} / {standing['output_tokens']}</td>"
            f"<td>{standing['errors']}</td></tr>"
        )
    body = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OpenAgentArena leaderboard</title>
<style>{_STYLE}</style>
<main><p class="eyebrow">OPENAGENTARENA · {html.escape(summary.environment)}</p>
<h1>Tournament leaderboard</h1>
<p>{len(summary.matches)} matches · paired seeds {html.escape(str(summary.seeds))}
· seat swapped</p>
<div class="card"><table><thead><tr><th>#</th><th>Agent</th><th>Elo</th><th>Played</th>
<th>W-D-L</th><th>Points</th><th>Cost USD</th><th>Tokens in / out</th><th>Errors</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="note">Elo is a live display. Immutable traces remain the source of truth.</p>
</main></html>"""
    destination.write_text(body, encoding="utf-8")
    return destination


def write_replay_html(trace_path: str | Path, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = read_trace(trace_path)
    safe_data = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")
    body = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OpenAgentArena replay</title><style>{_STYLE}</style>
<main><p class="eyebrow">OPENAGENTARENA · TRACE REPLAY</p><h1 id="title">Match replay</h1>
<div class="controls"><button id="prev">← Previous</button><input id="turn" type="range">
<button id="next">Next →</button><strong id="counter"></strong></div>
<div class="grid"><section class="card"><h2>Observations</h2><pre id="observations"></pre></section>
<section class="card"><h2>Actions & result</h2><pre id="result"></pre></section></div></main>
<script>const records={safe_data};const steps=records.filter(r=>r.type==='step');
const started=records[0];
document.querySelector('#title').textContent=`${{started.environment}} · ${{started.match_id}}`;
const slider=document.querySelector('#turn');slider.min=0;
slider.max=Math.max(0,steps.length-1);slider.value=0;
function render(){{const i=Number(slider.value),s=steps[i];
document.querySelector('#counter').textContent=`Turn ${{i+1}} / ${{steps.length}}`;
document.querySelector('#observations').textContent=JSON.stringify(s?.observations??{{}},null,2);
document.querySelector('#result').textContent=JSON.stringify(s?{{actions:s.actions,rewards:s.rewards,info:s.info,telemetry:s.telemetry}}:{{}},null,2)}}
slider.oninput=render;document.querySelector('#prev').onclick=()=>{{slider.value=Math.max(0,+slider.value-1);render()}};
document.querySelector('#next').onclick=()=>{{slider.value=Math.min(+slider.max,+slider.value+1);render()}};render();</script></html>"""
    destination.write_text(body, encoding="utf-8")
    return destination


_STYLE = """
:root{font-family:Inter,ui-sans-serif,system-ui;color:#17202a;background:#f4f1ea}
body{margin:0}main{max-width:1180px;margin:auto;padding:48px 24px}.eyebrow{letter-spacing:.14em;
font-size:.76rem;color:#b64b2a;font-weight:800}h1{font-size:clamp(2rem,5vw,4rem);margin:.2em 0}
.card{background:#fff;border:1px solid #ded8cd;border-radius:14px;padding:20px;overflow:auto;
box-shadow:0 12px 35px #3b302010}table{width:100%;border-collapse:collapse}th,td{text-align:left;
padding:12px;border-bottom:1px solid #eee8dd;white-space:nowrap}
th{font-size:.75rem;text-transform:uppercase}.note{color:#6d655b}
.controls{display:flex;align-items:center;gap:12px;margin:24px 0}
.controls input{flex:1}button{padding:9px 14px;border:1px solid #bdb4a7;
background:#fff;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
pre{font-size:.78rem;white-space:pre-wrap;word-break:break-word}
@media(max-width:760px){.grid{grid-template-columns:1fr}table{font-size:.8rem}}
"""
