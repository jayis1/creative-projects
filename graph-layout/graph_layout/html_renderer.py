"""HTML renderer — produces a self-contained HTML page with embedded SVG.

The HTML page includes CSS styling, a legend, optional metric annotations,
and the SVG embedded inline so the file is portable.
"""

from __future__ import annotations

from typing import Optional

from .graph import Graph
from .metrics import LayoutMetrics
from .render import SVGRenderer


class HTMLRenderer:
    """Render a positioned graph as a self-contained HTML page with embedded SVG.

    Args:
        width: SVG canvas width.
        height: SVG canvas height.
        title: page title.
        show_metrics: if True, include a metrics summary table.
        theme: ``"light"`` or ``"dark"``.
    """

    def __init__(self, width: int = 800, height: int = 600,
                 title: str = "Graph Layout",
                 show_metrics: bool = True,
                 theme: str = "light") -> None:
        self.width = width
        self.height = height
        self.title = title
        self.show_metrics = show_metrics
        self.theme = theme

    def render(self, graph: Graph) -> str:
        svg = SVGRenderer(width=self.width, height=self.height).render(graph)

        bg = "#1a1a2e" if self.theme == "dark" else "#ffffff"
        fg = "#e0e0e0" if self.theme == "dark" else "#333333"
        card_bg = "#16213e" if self.theme == "dark" else "#f8f9fa"
        border = "#0f3460" if self.theme == "dark" else "#dee2e6"

        metrics_html = ""
        if self.show_metrics:
            m = LayoutMetrics.all_metrics(graph)
            rows = "\n".join(
                f"      <tr><td>{k}</td><td>{v:.4f}</td></tr>"
                for k, v in m.items()
            )
            metrics_html = f"""
    <div class="card">
      <h2>Layout Metrics</h2>
      <table>
        <thead><tr><th>Metric</th><th>Value</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{self.title}</title>
  <style>
    body {{
      background: {bg};
      color: {fg};
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    h1 {{ margin-bottom: 8px; }}
    .info {{ opacity: 0.7; font-size: 0.9em; margin-bottom: 20px; }}
    .card {{
      background: {card_bg};
      border: 1px solid {border};
      border-radius: 8px;
      padding: 16px 24px;
      margin-top: 20px;
      max-width: 600px;
      width: 100%;
      box-sizing: border-box;
    }}
    h2 {{ font-size: 1.1em; margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 6px 12px; border-bottom: 1px solid {border}; }}
    th {{ font-weight: 600; }}
    .svg-container {{
      background: {card_bg};
      border: 1px solid {border};
      border-radius: 8px;
      padding: 16px;
    }}
  </style>
</head>
<body>
  <h1>{self.title}</h1>
  <div class="info">{graph.node_count} nodes &middot; {graph.edge_count} edges</div>
  <div class="svg-container">
  {svg}
  </div>
{metrics_html}
</body>
</html>"""

    def save(self, graph: Graph, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render(graph))


__all__ = ["HTMLRenderer"]