"""Batch rendering: execute multiple meshing jobs from a config file or preset.

This module ties together the config system, the three meshing algorithms,
the transforms/subdivision/simplification post-processing, and the export
writers to provide a high-level ``render_job`` / ``render_config`` API.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from . import (
    MarchingCubes, MarchingTetrahedra, DualContouring,
    analyze_mesh, write_obj, write_off, write_ply_ascii, write_ply_binary,
    write_stl_ascii, write_stl_binary, write_gltf_minimal,
)
from .ascii_preview import render_ascii_preview
from .simplify import simplify_mesh
from .subdivision import subdivide_n
from .transforms import translate, scale, rotate_x, rotate_y, rotate_z, mirror, normalize_size
from .config import (
    _make_sampler, _parse_bounds, normalize_job, load_config, get_preset,
)
from .logging_util import get_logger

ALGO_MAP = {
    "mc": MarchingCubes,
    "mt": MarchingTetrahedra,
    "dc": DualContouring,
}

EXPORTERS = {
    "obj": write_obj,
    "off": write_off,
    "ply-ascii": write_ply_ascii,
    "ply-binary": write_ply_binary,
    "stl-ascii": write_stl_ascii,
    "stl-binary": write_stl_binary,
    "gltf": write_gltf_minimal,
}


def _detect_format(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".obj": "obj", ".off": "off", ".ply": "ply-binary",
        ".stl": "stl-binary", ".gltf": "gltf",
    }.get(ext, "obj")


def _apply_transforms(mesh, transform_cfg: Dict[str, Any]):
    """Apply transformations from a config dict to a mesh."""
    if not transform_cfg:
        return mesh
    if "translate" in transform_cfg:
        t = transform_cfg["translate"]
        mesh = translate(mesh, t.get("x", 0), t.get("y", 0), t.get("z", 0))
    if "scale" in transform_cfg:
        s = transform_cfg["scale"]
        if isinstance(s, (int, float)):
            mesh = scale(mesh, s, s, s)
        else:
            mesh = scale(mesh, s.get("x", 1), s.get("y", 1), s.get("z", 1))
    if "rotate_x" in transform_cfg:
        mesh = rotate_x(mesh, float(transform_cfg["rotate_x"]))
    if "rotate_y" in transform_cfg:
        mesh = rotate_y(mesh, float(transform_cfg["rotate_y"]))
    if "rotate_z" in transform_cfg:
        mesh = rotate_z(mesh, float(transform_cfg["rotate_z"]))
    if "mirror" in transform_cfg:
        mesh = mirror(mesh, transform_cfg["mirror"])
    if transform_cfg.get("normalize_size", False):
        mesh = normalize_size(mesh, transform_cfg.get("target_size", 2.0))
    return mesh


def render_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single render job and return a result dict.

    The returned dict contains:
        - ``name``: job name
        - ``mesh``: the produced :class:`Mesh`
        - ``diagnostics``: :class:`MeshDiagnostics`
        - ``elapsed``: wall-clock time in seconds
        - ``output``: output file path (if written)
    """
    logger = get_logger()
    job = normalize_job(job)
    name = job["name"]

    logger.info(f"Starting job: {name}")
    t0 = time.time()

    # Build sampler
    sampler = _make_sampler(job["sampler"], job["sampler_params"])
    bounds = _parse_bounds(job["bounds"])
    res = job["resolution"]
    if isinstance(res, int):
        res = (res, res, res)

    # Run algorithm
    algo_cls = ALGO_MAP[job["algorithm"]]
    algo = algo_cls(sampler=sampler, bounds=bounds, resolution=res, isolevel=job["isolevel"])
    mesh = algo.run()

    # Post-processing: simplify
    if job.get("simplify_target", 0) and job["simplify_target"] < mesh.num_faces:
        mesh = simplify_mesh(mesh, target_faces=job["simplify_target"])

    # Post-processing: subdivide
    if job.get("subdivide", 0) > 0:
        mesh = subdivide_n(mesh, job["subdivide"])

    # Post-processing: transforms
    mesh = _apply_transforms(mesh, job.get("transform", {}))

    # Diagnostics
    diag = analyze_mesh(mesh)
    elapsed = time.time() - t0

    logger.info(f"Job '{name}' done: V={mesh.num_vertices} F={mesh.num_faces} ({elapsed:.2f}s)")

    result = {
        "name": name,
        "mesh": mesh,
        "diagnostics": diag,
        "elapsed": elapsed,
        "output": None,
    }

    # Export
    output = job.get("output")
    if output:
        fmt = job.get("format") or _detect_format(output)
        if fmt not in EXPORTERS:
            raise ValueError(f"unknown export format: {fmt!r}")
        EXPORTERS[fmt](mesh, output)
        result["output"] = output
        logger.info(f"Exported to {output} ({fmt})")

    # Preview
    if job.get("preview", False):
        preview = render_ascii_preview(
            mesh,
            width=job.get("preview_width", 60),
            height=job.get("preview_height", 20),
        )
        result["preview"] = preview

    return result


def render_config(config_path: str) -> List[Dict[str, Any]]:
    """Load a config file and execute all jobs in it.

    Returns a list of result dicts (one per job).
    """
    config = load_config(config_path)
    jobs = config.get("jobs", [])
    if not jobs:
        raise ValueError("config file contains no jobs")
    results = []
    for job in jobs:
        results.append(render_job(job))
    return results


def render_preset(preset_name: str, output: Optional[str] = None,
                  preview: bool = False) -> Dict[str, Any]:
    """Render using a built-in preset."""
    job = get_preset(preset_name)
    if output:
        job["output"] = output
    if preview:
        job["preview"] = True
    return render_job(job)