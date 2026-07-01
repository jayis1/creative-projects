"""
Web server for interactive nonogram solving in the browser.

Uses only the Python standard library (http.server) — no Flask or other
web framework needed. Serves a self-contained HTML/JS/CSS frontend that
lets users interactively solve puzzles, request hints, and validate their
progress.

Usage::

    python -m nonogram.web --file puzzles/heart.json --port 8080

Then open http://localhost:8080 in a browser.
"""

from __future__ import annotations

import json
import logging
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.player import Player
from nonogram.io import PuzzleIO

logger = logging.getLogger("nonogram.web")

# The HTML/JS/CSS template for the interactive solver page.
_PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nonogram Solver — {title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 10px; color: #e94560; }}
#info {{ text-align: center; margin-bottom: 15px; font-size: 14px; color: #aaa; }}
#board-container {{ display: flex; justify-content: center; margin: 20px auto; overflow-x: auto; }}
table {{ border-collapse: collapse; }}
td.clue {{ background: #16213e; color: #e94560; font-weight: bold; text-align: center;
           font-family: monospace; font-size: 13px; min-width: 24px; max-width: 30px;
           padding: 2px; border: 1px solid #0f3460; }}
td.cell {{ width: 36px; height: 36px; border: 1px solid #0f3460; cursor: pointer;
           transition: background 0.1s; }}
td.cell.filled {{ background: #e94560; }}
td.cell.empty {{ background: #0f3460; }}
td.cell.unknown {{ background: #1a1a2e; }}
td.cell.unknown:hover {{ background: #16213e; }}
#controls {{ text-align: center; margin: 15px; }}
#controls button {{ background: #e94560; color: white; border: none; padding: 10px 20px;
                   margin: 0 5px; border-radius: 5px; cursor: pointer; font-size: 14px; }}
#controls button:hover {{ background: #c73650; }}
#status {{ text-align: center; margin: 10px; font-size: 16px; font-weight: bold; }}
#status.win {{ color: #4ecca3; }}
#status.error {{ color: #e94560; }}
</style>
</head>
<body>
<h1>Nonogram Solver</h1>
<div id="info">{info}</div>
<div id="board-container">{board_html}</div>
<div id="controls">
  <button onclick="setMode('fill')">✏ Fill Mode</button>
  <button onclick="setMode('blank')">⬜ Blank Mode</button>
  <button onclick="setMode('erase')">🔄 Erase Mode</button>
  <button onclick="hint()">💡 Hint</button>
  <button onclick="check()">✓ Check</button>
  <button onclick="solve()">🔧 Solve</button>
  <button onclick="reset()">↺ Reset</button>
</div>
<div id="status"></div>
<script>
const rowClues = {row_clues};
const colClues = {col_clues};
const height = {height};
const width = {width};
let mode = 'fill';
let grid = Array({height}).fill(null).map(() => Array({width}).fill(-1));

function setMode(m) {{ mode = m; document.getElementById('status').textContent = 'Mode: ' + m; }}
function toggleCell(r, c) {{
  if (mode === 'fill') grid[r][c] = 1;
  else if (mode === 'blank') grid[r][c] = 0;
  else grid[r][c] = -1;
  render();
}}
function render() {{
  for (let r = 0; r < height; r++) {{
    for (let c = 0; c < width; c++) {{
      const td = document.getElementById('c_' + r + '_' + c);
      td.className = 'cell ' + (grid[r][c] === 1 ? 'filled' : grid[r][c] === 0 ? 'empty' : 'unknown');
    }}
  }}
}}
function hint() {{
  fetch('/api/hint', {{method:'POST',body:JSON.stringify({{grid: grid}}),headers:{{'Content-Type':'application/json'}}}})
    .then(r => r.json()).then(d => {{
      if (d.cell) {{
        grid[d.cell.r][d.cell.c] = d.cell.value;
        render();
        document.getElementById('status').textContent = 'Hint: (' + d.cell.r + ', ' + d.cell.c + ') = ' + (d.cell.value === 1 ? 'FILLED' : 'EMPTY');
        document.getElementById('status').className = '';
      }} else {{
        document.getElementById('status').textContent = 'No hint available.';
        document.getElementById('status').className = 'error';
      }}
    }});
}}
function check() {{
  fetch('/api/check', {{method:'POST',body:JSON.stringify({{grid: grid}}),headers:{{'Content-Type':'application/json'}}}})
    .then(r => r.json()).then(d => {{
      const s = document.getElementById('status');
      if (d.correct) {{ s.textContent = '✓ Correct so far!'; s.className = 'win'; }}
      else {{ s.textContent = '✗ Some cells are wrong.'; s.className = 'error'; }}
      if (d.won) {{ s.textContent = '🎉 Solved!'; s.className = 'win'; }}
    }});
}}
function solve() {{
  fetch('/api/solve', {{method:'POST',body:JSON.stringify({{grid: grid}}),headers:{{'Content-Type':'application/json'}}}})
    .then(r => r.json()).then(d => {{
      if (d.solution) {{ grid = d.solution; render();
        document.getElementById('status').textContent = 'Solved!'; document.getElementById('status').className = 'win'; }}
      else {{ document.getElementById('status').textContent = 'Could not solve.'; document.getElementById('status').className = 'error'; }}
    }});
}}
function reset() {{ grid = Array(height).fill(null).map(() => Array(width).fill(-1)); render();
  document.getElementById('status').textContent = ''; document.getElementById('status').className = ''; }}
render();
</script>
</body>
</html>"""


class _NonogramHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the interactive web solver."""

    # Class-level attributes set by serve().
    board: Board = None  # type: ignore
    player: Player = None  # type: ignore
    solver: Solver = None  # type: ignore

    def log_message(self, format, *args):  # pragma: no cover
        logger.debug("HTTP %s: %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._serve_page()
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/hint":
            self._handle_hint()
        elif self.path == "/api/check":
            self._handle_check()
        elif self.path == "/api/solve":
            self._handle_solve()
        else:
            self.send_error(404)

    # -- Helpers -- #

    def _serve_page(self) -> None:
        b = self.board
        # Build HTML table with clues.
        max_col_clue_len = max((len(c) for c in b.col_clues), default=1)
        html_parts = ["<table>"]
        # Column clues (vertical).
        for ci in range(max_col_clue_len):
            html_parts.append("<tr>")
            html_parts.append('<td class="clue"></td>')
            for c_idx in range(b.width):
                val = b.col_clues[c_idx][ci] if ci < len(b.col_clues[c_idx]) else ""
                html_parts.append(f'<td class="clue">{val}</td>')
            html_parts.append("</tr>")
        # Board rows.
        for r in range(b.height):
            html_parts.append("<tr>")
            clue_str = " ".join(str(x) for x in b.row_clues[r])
            html_parts.append(f'<td class="clue">{clue_str}</td>')
            for c_idx in range(b.width):
                html_parts.append(
                    f'<td class="cell unknown" id="c_{r}_{c_idx}" '
                    f'onclick="toggleCell({r},{c_idx})"></td>'
                )
            html_parts.append("</tr>")
        html_parts.append("</table>")
        board_html = "\n".join(html_parts)

        page = _PAGE_TEMPLATE.format(
            title=f"{b.width}×{b.height}",
            info=f"Grid: {b.width}×{b.height} — Click cells to fill/blank them.",
            row_clues=json.dumps(b.row_clues),
            col_clues=json.dumps(b.col_clues),
            height=b.height,
            width=b.width,
            board_html=board_html,
        )
        self._send_html(page)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(body)

    def _send_json(self, d: dict) -> None:
        body = json.dumps(d).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _grid_from_request(self) -> list[list[int]]:
        """Extract a 2D grid from the POST body."""
        data = self._read_body()
        return data.get("grid", [])

    def _apply_grid(self, grid: list[list[int]]) -> Board:
        """Apply a JSON grid to a fresh board and return it."""
        b = Board(self.board.row_clues, self.board.col_clues)
        for r in range(min(len(grid), b.height)):
            for c in range(min(len(grid[r]), b.width)):
                v = grid[r][c]
                b.grid[r][c] = Cell.FILLED if v == 1 else (
                    Cell.EMPTY if v == 0 else Cell.UNKNOWN
                )
        return b

    def _handle_hint(self) -> None:
        grid = self._grid_from_request()
        board = self._apply_grid(grid)
        player = Player(self.board)
        player.board = board
        hint = player.hint()
        if hint:
            r, c, cell = hint
            self._send_json({"cell": {"r": r, "c": c, "value": cell.value}})
        else:
            self._send_json({"cell": None})

    def _handle_check(self) -> None:
        grid = self._grid_from_request()
        board = self._apply_grid(grid)
        player = Player(self.board)
        player.board = board
        correct = player.check()
        won = board.is_solved()
        self._send_json({"correct": correct, "won": won})

    def _handle_solve(self) -> None:
        solver = Solver()
        board = Board(self.board.row_clues, self.board.col_clues)
        result = solver.solve(board)
        if result.solved:
            solution = [[board.grid[r][c].value for c in range(board.width)]
                        for r in range(board.height)]
            self._send_json({"solution": solution})
        else:
            self._send_json({"solution": None})


def serve(board: Board, port: int = 8080, open_browser: bool = True) -> None:
    """Start the web server for *board* on *port*.

    Parameters
    ----------
    board : Board
        The puzzle to serve (clues only — grid state is ignored).
    port : int
        TCP port to listen on.
    open_browser : bool
        If True, open a browser window automatically.
    """
    _NonogramHandler.board = board
    _NonogramHandler.player = Player(board)
    _NonogramHandler.solver = Solver()

    server = HTTPServer(("0.0.0.0", port), _NonogramHandler)
    logger.info("Starting web server on http://localhost:%d", port)
    if open_browser:
        url = f"http://localhost:{port}"
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down web server.")
        server.shutdown()