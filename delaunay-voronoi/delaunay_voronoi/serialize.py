"""
JSON serialization for triangulations, point sets, and Voronoi diagrams.

Provides a compact, human-readable interchange format so diagrams can be
saved and reloaded for further processing or rendering in other tools.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .delaunay import DelaunayTriangulation
from .geometry import Edge, Point, Triangle
from .voronoi import VoronoiDiagram, VoronoiCell


def _point_to_list(p: Point) -> List[float]:
    return [p.x, p.y]


def _list_to_point(lst: List[float]) -> Point:
    return Point(float(lst[0]), float(lst[1]))


def triangulation_to_dict(dt: DelaunayTriangulation) -> Dict[str, Any]:
    """Serialize a Delaunay triangulation to a plain dict."""
    return {
        "points": [_point_to_list(p) for p in dt.points],
        "triangles": [
            [_point_to_list(v) for v in t.vertices()] for t in dt.triangles
        ],
    }


def triangulation_from_dict(data: Dict[str, Any]) -> DelaunayTriangulation:
    """Reconstruct a DelaunayTriangulation from a dict.

    Note: this reconstructs the triangle list directly rather than
    re-triangulating, so the topology is preserved exactly.
    """
    dt = DelaunayTriangulation()
    dt._points = [_list_to_point(p) for p in data["points"]]
    dt._triangles = [
        Triangle(
            _list_to_point(t[0]),
            _list_to_point(t[1]),
            _list_to_point(t[2]),
        )
        for t in data["triangles"]
    ]
    dt._super_vertices = set()
    return dt


def voronoi_to_dict(vd: VoronoiDiagram) -> Dict[str, Any]:
    """Serialize a Voronoi diagram to a plain dict."""
    return {
        "sites": [_point_to_list(p) for p in vd.sites],
        "vertices": [_point_to_list(v) for v in vd.vertices],
        "edges": [
            [_point_to_list(e.a), _point_to_list(e.b)] for e in vd.edges
        ],
        "cells": {
            f"{p.x},{p.y}": [_point_to_list(v) for v in cell.vertices]
            for p, cell in vd.cells.items()
        },
    }


def save_json(obj: Any, path: str) -> None:
    """Save *obj* (a dict/list or geometry object with to_dict) to *path*."""
    if isinstance(obj, DelaunayTriangulation):
        data = triangulation_to_dict(obj)
    elif isinstance(obj, VoronoiDiagram):
        data = voronoi_to_dict(obj)
    elif isinstance(obj, dict):
        data = obj
    else:
        data = obj
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_json(path: str) -> Dict[str, Any]:
    """Load a JSON file and return its contents as a dict."""
    with open(path) as f:
        return json.load(f)