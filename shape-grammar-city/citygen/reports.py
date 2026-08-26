from __future__ import annotations

import json
from html import escape

from .districts import District
from .generator import CityMap
from .render import render_svg


def render_report_html(
    city: CityMap,
    *,
    stats: dict[str, object],
    districts: list[District],
    title: str = "Shape Grammar City Report",
    cell_size: int = 18,
) -> str:
    """Render a self-contained HTML report for a city."""

    svg = render_svg(city, cell_size=cell_size)
    district_rows = "".join(
        "<tr>"
        f"<td>{escape(district.name)}</td>"
        f"<td>{escape(district.tile)}</td>"
        f"<td>{district.size}</td>"
        f"<td>{district.road_access}</td>"
        f"<td>{'yes' if district.waterfront else 'no'}</td>"
        "</tr>"
        for district in districts[:12]
    )
    stats_json = escape(json.dumps(stats, indent=2))
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin: 2rem; background: #f7f7f5; color: #222; }}
    h1, h2 {{ margin-bottom: 0.4rem; }}
    .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; align-items: start; }}
    .panel {{ background: white; border-radius: 14px; padding: 1rem 1.2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 0.45rem; border-bottom: 1px solid #e8e8e8; text-align: left; }}
    pre {{ white-space: pre-wrap; overflow-x: auto; }}
    .svg-wrap svg {{ max-width: 100%; height: auto; border-radius: 12px; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>Mode: <strong>{escape(city.mode)}</strong> · Seed: <strong>{city.seed}</strong> · Size: <strong>{city.width}×{city.height}</strong></p>
  <div class=\"grid\">
    <section class=\"panel svg-wrap\">
      <h2>Map</h2>
      {svg}
    </section>
    <section class=\"panel\">
      <h2>Districts</h2>
      <table>
        <thead><tr><th>Name</th><th>Tile</th><th>Cells</th><th>Road edges</th><th>Waterfront</th></tr></thead>
        <tbody>{district_rows}</tbody>
      </table>
    </section>
  </div>
  <section class=\"panel\" style=\"margin-top: 1.5rem;\">
    <h2>Statistics</h2>
    <pre>{stats_json}</pre>
  </section>
</body>
</html>
"""
