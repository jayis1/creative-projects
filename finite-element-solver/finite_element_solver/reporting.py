from __future__ import annotations

from typing import Any

from .model import SolveResult, TrussModel


def summarize_model(model: TrussModel) -> dict[str, object]:
    """Return quick aggregate metrics for reporting and CLI summaries."""

    node_lookup = {node.id: node for node in model.nodes}
    lengths = []
    masses = []
    for element in model.elements:
        start = node_lookup[element.start]
        end = node_lookup[element.end]
        length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
        lengths.append(length)
        masses.append(element.density * element.area * length)
    bbox = {
        "min_x": min(node.x for node in model.nodes),
        "max_x": max(node.x for node in model.nodes),
        "min_y": min(node.y for node in model.nodes),
        "max_y": max(node.y for node in model.nodes),
    }
    return {
        "title": model.metadata.get("title", "untitled"),
        "node_count": len(model.nodes),
        "element_count": len(model.elements),
        "support_count": len(model.supports),
        "load_case_count": max(1, len(model.load_cases)),
        "load_combination_count": len(model.load_combinations),
        "total_length": sum(lengths),
        "total_mass": sum(masses),
        "bounding_box": bbox,
    }


def serialize_result(result: SolveResult) -> dict[str, Any]:
    return {
        "name": result.case_name,
        "result_kind": result.result_kind,
        "displacements": {node: [dx, dy] for node, (dx, dy) in result.displacements.items()},
        "reactions": {node: [rx, ry] for node, (rx, ry) in result.reactions.items()},
        "elements": [
            {
                "id": item.element_id,
                "length": item.length,
                "strain": item.strain,
                "stress": item.stress,
                "axial_force": item.axial_force,
                "utilization": item.utilization,
                "mass": item.mass,
            }
            for item in result.element_results
        ],
        "max_displacement": result.max_displacement,
        "total_mass": result.total_mass,
        "total_length": result.total_length,
    }


def format_text(result: SolveResult) -> str:
    label = "Load combination" if result.result_kind == "load_combination" else "Load case"
    lines = [f"{label}: {result.case_name}", "Displacements:"]
    for node_id, (dx, dy) in result.displacements.items():
        lines.append(f"  {node_id}: dx={dx:.6e} m, dy={dy:.6e} m")
    lines.append("Reactions:")
    for node_id, (rx, ry) in result.reactions.items():
        lines.append(f"  {node_id}: Rx={rx:.3f} N, Ry={ry:.3f} N")
    lines.append("Element forces:")
    for item in result.element_results:
        util = "n/a" if item.utilization is None else f"{item.utilization:.3%}"
        lines.append(
            "  "
            f"{item.element_id}: axial={item.axial_force:.3f} N, stress={item.stress:.3f} Pa, "
            f"strain={item.strain:.6e}, utilization={util}, mass={item.mass:.3f} kg"
        )
    lines.append(f"Total length: {result.total_length:.3f} m")
    lines.append(f"Total mass: {result.total_mass:.3f} kg")
    lines.append(f"Max displacement magnitude: {result.max_displacement:.6e} m")
    return "\n".join(lines)


def format_summary(summary: dict[str, Any]) -> str:
    bbox = summary["bounding_box"]
    return "\n".join(
        [
            f"Title: {summary['title']}",
            f"Nodes: {summary['node_count']}",
            f"Elements: {summary['element_count']}",
            f"Supports: {summary['support_count']}",
            f"Load cases: {summary['load_case_count']}",
            f"Load combinations: {summary['load_combination_count']}",
            f"Total length: {summary['total_length']:.3f} m",
            f"Total mass: {summary['total_mass']:.3f} kg",
            f"Bounding box: x=[{bbox['min_x']:.3f}, {bbox['max_x']:.3f}], y=[{bbox['min_y']:.3f}, {bbox['max_y']:.3f}]",
        ]
    )


def build_envelope(results: list[SolveResult]) -> dict[str, Any]:
    if not results:
        return {
            "result_count": 0,
            "global_max_displacement": {"node": None, "magnitude": 0.0, "source": None},
            "nodes": {},
            "elements": {},
        }

    node_names = results[0].displacements.keys()
    element_names = [item.element_id for item in results[0].element_results]
    envelope_nodes: dict[str, dict[str, Any]] = {}
    envelope_elements: dict[str, dict[str, Any]] = {}

    global_node = None
    global_value = -1.0
    global_source = None
    for node in node_names:
        best_source = None
        best_value = -1.0
        for result in results:
            dx, dy = result.displacements[node]
            magnitude = (dx * dx + dy * dy) ** 0.5
            if magnitude > best_value:
                best_value = magnitude
                best_source = result.case_name
        envelope_nodes[node] = {"max_displacement": best_value, "source": best_source}
        if best_value > global_value:
            global_value = best_value
            global_node = node
            global_source = best_source

    for element_name in element_names:
        best_axial = {"value": 0.0, "source": None}
        best_stress = {"value": 0.0, "source": None}
        best_util = {"value": None, "source": None}
        for result in results:
            element = next(item for item in result.element_results if item.element_id == element_name)
            if abs(element.axial_force) > abs(best_axial["value"]):
                best_axial = {"value": element.axial_force, "source": result.case_name}
            if abs(element.stress) > abs(best_stress["value"]):
                best_stress = {"value": element.stress, "source": result.case_name}
            if element.utilization is not None and (
                best_util["value"] is None or element.utilization > best_util["value"]
            ):
                best_util = {"value": element.utilization, "source": result.case_name}
        envelope_elements[element_name] = {
            "max_abs_axial_force": best_axial,
            "max_abs_stress": best_stress,
            "max_utilization": best_util,
        }

    return {
        "result_count": len(results),
        "global_max_displacement": {"node": global_node, "magnitude": global_value, "source": global_source},
        "nodes": envelope_nodes,
        "elements": envelope_elements,
    }
