"""
turing_machine.visualizer
=========================

Generate visual representations of Turing machine executions.

This module provides:

* :func:`text_trace` – a plain-text trace of every step.
* :func:`html_animation` – a self-contained HTML file with an animated
  step-by-step replay of the machine's execution.
* :func:`svg_diagram` – an SVG state-transition diagram of the machine's
  program.
* :func:`csv_trace` – a CSV export of the execution history.
"""

from __future__ import annotations

import html
import os
from typing import Any, Dict, List, Optional, Tuple

from .machine import Program, Tape, TMDirection, Transition, TuringMachine


# ---------------------------------------------------------------------------
# Text trace
# ---------------------------------------------------------------------------

def text_trace(
    tm: TuringMachine,
    max_steps: int = 1000,
    show_transitions: bool = True,
) -> str:
    """Run *tm* with history recording and return a formatted text trace.

    Parameters
    ----------
    tm : TuringMachine
        The machine to trace (will be reset and re-run).
    max_steps : int
        Maximum number of steps to trace.
    show_transitions : bool
        If True, include the transition rule that fired at each step.
    """
    tm.reset()
    tm.run(record=True)
    lines: List[str] = []
    lines.append(f"{'Step':>5}  {'State':<12}  {'Tape':<40}  {'Rule'}")
    lines.append("-" * 80)

    for i, step in enumerate(tm.history):
        tape_str = "".join(str(c) for c in step.tapes[0].to_list())
        rule = str(step.transition) if step.transition and show_transitions else ""
        lines.append(f"{step.step:>5}  {step.state:<12}  {tape_str:<40}  {rule}")
        if i >= max_steps:
            lines.append(f"  ... (truncated at {max_steps} steps)")
            break

    lines.append("-" * 80)
    lines.append(f"Final state: {tm.state}  Steps: {tm.steps}  Halted: {tm.halted}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV trace
# ---------------------------------------------------------------------------

def csv_trace(tm: TuringMachine) -> str:
    """Run *tm* and return the execution history as CSV."""
    import csv
    import io

    tm.reset()
    tm.run(record=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["step", "state", "tape", "head", "transition"])

    for step in tm.history:
        tape_str = ",".join(str(c) for c in step.tapes[0].to_list(strip_blanks=False))
        head = step.tapes[0].head
        rule = str(step.transition) if step.transition else ""
        writer.writerow([step.step, step.state, tape_str, head, rule])

    return output.getvalue()


# ---------------------------------------------------------------------------
# HTML animation
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Turing Machine Trace — {title}</title>
<style>
{styles}
</style>
</head>
<body>
<h1>Turing Machine Trace</h1>
<p>Machine: <code>{title}</code> — {num_steps} steps — Final state: <strong>{final_state}</strong></p>
<div id="player">
  <div id="controls">
    <button onclick="prev()">&#9664; Prev</button>
    <button onclick="toggle()">&#9658; Play/Pause</button>
    <button onclick="next()">Next &#9655;</button>
    <button onclick="reset()">&#8634; Reset</button>
    <span id="step-label">Step 0 / 0</span>
    <input type="range" id="scrubber" min="0" max="0" value="0" oninput="seek(this.value)">
  </div>
  <div id="state-display"></div>
  <div id="tape-display"></div>
</div>
<script>
const steps = {steps_json};
let current = 0;
let playing = false;
let timer = null;

function renderStep(i) {{
  if (i < 0) i = 0;
  if (i >= steps.length) i = steps.length - 1;
  current = i;
  const s = steps[i];
  document.getElementById('step-label').textContent = `Step ${{i}} / ${{steps.length - 1}}`;
  document.getElementById('scrubber').value = i;
  document.getElementById('scrubber').max = steps.length - 1;

  let stateHtml = `<div class="state-info">`;
  stateHtml += `<span class="label">State:</span> <span class="value">${{s.state}}</span>`;
  stateHtml += ` <span class="label">Steps:</span> <span class="value">${{s.step}}</span>`;
  if (s.halted) stateHtml += ` <span class="halted">HALTED</span>`;
  stateHtml += `</div>`;
  if (s.rule) stateHtml += `<div class="rule"><span class="label">Rule:</span> ${{s.rule}}</div>`;

  document.getElementById('state-display').innerHTML = stateHtml;

  let tapeHtml = '<div class="tape">';
  const head = s.head;
  const tape = s.tape;
  const start = Math.max(0, head - 8);
  const end = Math.min(tape.length, head + 9);
  for (let j = start; j < end; j++) {{
    const sym = tape[j] !== undefined ? tape[j] : '_';
    const cls = j === head ? 'cell head' : 'cell';
    tapeHtml += `<span class="${{cls}}">${{sym}}</span>`;
  }}
  tapeHtml += '</div>';
  document.getElementById('tape-display').innerHTML = tapeHtml;
}}

function next() {{ renderStep(current + 1); }}
function prev() {{ renderStep(current - 1); }}
function reset() {{ renderStep(0); }}
function seek(i) {{ renderStep(parseInt(i)); }}

function toggle() {{
  playing = !playing;
  if (playing) {{
    timer = setInterval(() => {{
      if (current < steps.length - 1) {{
        next();
      }} else {{
        playing = false;
        clearInterval(timer);
      }}
    }}, {delay_ms});
  }} else {{
    clearInterval(timer);
  }}
}}

renderStep(0);
</script>
</body>
</html>"""

_STYLES = """
body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #e0e0e0; }
h1 { color: #00d4ff; }
code { background: #16213e; padding: 2px 6px; border-radius: 4px; }
#player { max-width: 800px; margin: 20px auto; }
#controls { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
button { background: #0f3460; color: #e0e0e0; border: 1px solid #00d4ff; border-radius: 4px;
         padding: 8px 16px; cursor: pointer; font-size: 14px; }
button:hover { background: #1a1a3e; }
#scrubber { flex-grow: 1; min-width: 200px; }
#step-label { font-family: monospace; font-size: 14px; color: #aaa; }
.state-info { font-size: 18px; margin-bottom: 10px; }
.label { color: #888; }
.value { color: #00d4ff; font-weight: bold; }
.halted { color: #ff4444; font-weight: bold; animation: pulse 1s infinite; }
@keyframes pulse { 50% { opacity: 0.5; } }
.rule { font-family: monospace; font-size: 13px; color: #888; margin-bottom: 15px; }
.tape { display: flex; gap: 2px; justify-content: center; padding: 20px; background: #0f0f23; border-radius: 8px; }
.cell { display: inline-block; width: 40px; height: 40px; line-height: 40px; text-align: center;
        background: #16213e; border: 1px solid #333; border-radius: 4px; font-family: monospace;
        font-size: 18px; color: #e0e0e0; }
.cell.head { background: #0f3460; border-color: #00d4ff; box-shadow: 0 0 10px #00d4ff; color: #00d4ff; }
"""


def html_animation(
    tm: TuringMachine,
    output_path: Optional[str] = None,
    title: str = "Turing Machine",
    delay_ms: int = 500,
) -> str:
    """Run *tm* with recording and produce an interactive HTML animation.

    Parameters
    ----------
    tm : TuringMachine
        The machine to animate (will be reset and re-run).
    output_path : str, optional
        If given, write the HTML to this file.  Returns the HTML in any case.
    title : str
        Title shown in the HTML.
    delay_ms : int
        Delay between steps during auto-play, in milliseconds.

    Returns
    -------
    str
        The complete HTML document.
    """
    import json

    tm.reset()
    tm.run(record=True)

    steps_data: List[Dict[str, Any]] = []
    # Initial state (step 0).
    steps_data.append({
        "step": 0,
        "state": tm.initial_state,
        "tape": [str(c) for c in tm.tapes[0].to_list(strip_blanks=False)],
        "head": 0,
        "rule": "",
        "halted": False,
    })

    for step in tm.history:
        steps_data.append({
            "step": step.step + 1,
            "state": step.state,
            "tape": [str(c) for c in step.tapes[0].to_list(strip_blanks=False)],
            "head": step.tapes[0].head,
            "rule": str(step.transition) if step.transition else "",
            "halted": step.step + 1 >= tm.steps and tm.halted,
        })

    # Ensure final state is represented.
    if tm.halted and (not steps_data or steps_data[-1]["state"] != tm.state):
        steps_data.append({
            "step": tm.steps,
            "state": tm.state,
            "tape": [str(c) for c in tm.tapes[0].to_list(strip_blanks=False)],
            "head": tm.tapes[0].head,
            "rule": "",
            "halted": True,
        })

    html_doc = _HTML_TEMPLATE.format(
        title=html.escape(title),
        styles=_STYLES,
        steps_json=json.dumps(steps_data),
        num_steps=tm.steps,
        final_state=html.escape(tm.state),
        delay_ms=delay_ms,
    )

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_doc)

    return html_doc


# ---------------------------------------------------------------------------
# SVG state diagram
# ---------------------------------------------------------------------------

def svg_diagram(
    program: Program,
    initial_state: Optional[str] = None,
    halt_states: Optional[set] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate an SVG state-transition diagram for *program*.

    Returns the SVG as a string; if *output_path* is given, also writes it.
    """
    import math

    states = program.states()
    if initial_state and initial_state not in states:
        states = [initial_state] + states
    n = len(states)
    if n == 0:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>'

    halt = halt_states or set()
    radius = max(200, n * 60)
    cx, cy = radius + 50, radius + 50
    node_r = 28

    # Place nodes on a circle.
    positions: Dict[str, Tuple[float, float]] = {}
    for i, s in enumerate(states):
        angle = 2 * math.pi * i / n - math.pi / 2
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        positions[s] = (x, y)

    svg_parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * (radius + 60)}" height="{2 * (radius + 60)}">',
        '<style>',
        '  text { font-family: Arial, sans-serif; font-size: 13px; fill: #333; text-anchor: middle; }',
        '  .state-circle { fill: #e8f0fe; stroke: #4a90d9; stroke-width: 2; }',
        '  .halt-circle { fill: #ffe0e0; stroke: #d94a4a; stroke-width: 2; }',
        '  .initial-circle { fill: #e0ffe0; stroke: #4ad94a; stroke-width: 2; }',
        '  .arrow { stroke: #555; stroke-width: 1.5; fill: none; }',
        '  .arrow-label { font-size: 10px; fill: #666; }',
        '</style>',
    ]

    # Draw arrows (transitions).
    for t in program:
        if t.state not in positions or t.new_state not in positions:
            continue
        x1, y1 = positions[t.state]
        x2, y2 = positions[t.new_state]
        # Shorten arrow at both ends.
        dx, dy = x2 - x1, y2 - y1
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            # Self-loop.
            svg_parts.append(
                f'<path class="arrow" d="M {x1},{y1 - node_r} '
                f'C {x1 + 40},{y1 - 60} {x1 - 40},{y1 - 60} {x1 - 0.01},{y1 - node_r}" '
                f'marker-end="url(#arrowhead)"/>'
            )
            label = f"{t.read}→{t.write},{t.direction}"
            svg_parts.append(
                f'<text class="arrow-label" x="{x1}" y="{y1 - 65}">{html.escape(label)}</text>'
            )
            continue
        ux, uy = dx / dist, dy / dist
        sx, sy = x1 + ux * node_r, y1 + uy * node_r
        ex, ey = x2 - ux * node_r, y2 - uy * node_r
        svg_parts.append(
            f'<line class="arrow" x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'marker-end="url(#arrowhead)"/>'
        )
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        label = f"{t.read}→{t.write},{t.direction}"
        svg_parts.append(
            f'<text class="arrow-label" x="{mx:.1f}" y="{my - 5:.1f}">{html.escape(label)}</text>'
        )

    # Arrowhead marker.
    svg_parts.append(
        '<defs><marker id="arrowhead" markerWidth="8" markerHeight="6" '
        'refX="7" refY="3" orient="auto">'
        '<polygon points="0 0, 8 3, 0 6" fill="#555"/>'
        '</marker></defs>'
    )

    # Draw state nodes.
    for s, (x, y) in positions.items():
        cls = "state-circle"
        if s in halt:
            cls = "halt-circle"
        elif s == initial_state:
            cls = "initial-circle"
        svg_parts.append(
            f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="{node_r}"/>'
        )
        svg_parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}">{html.escape(s)}</text>'
        )

    svg_parts.append('</svg>')
    svg = "\n".join(svg_parts)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg)

    return svg