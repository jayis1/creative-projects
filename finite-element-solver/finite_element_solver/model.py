from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
from typing import Any


class ValidationError(ValueError):
    """Raised when a truss model is invalid or unsolvable."""


@dataclass(frozen=True)
class Node:
    """Nodal coordinates and optional base load."""

    id: str
    x: float
    y: float
    load_x: float = 0.0
    load_y: float = 0.0


@dataclass(frozen=True)
class Support:
    """Boundary conditions for a node's translational degrees of freedom."""

    node_id: str
    fix_x: bool
    fix_y: bool


@dataclass(frozen=True)
class Material:
    """Linear elastic material properties."""

    id: str
    youngs_modulus: float
    density: float = 0.0
    yield_strength: float | None = None


@dataclass(frozen=True)
class Section:
    """Cross-section properties for a truss bar."""

    id: str
    area: float


@dataclass(frozen=True)
class Element:
    """Pin-jointed 2D truss bar."""

    id: str
    start: str
    end: str
    youngs_modulus: float
    area: float
    density: float = 0.0
    yield_strength: float | None = None


@dataclass(frozen=True)
class LoadCase:
    """Named set of nodal loads and optional gravity."""

    name: str
    node_loads: dict[str, tuple[float, float]] = field(default_factory=dict)
    gravity: tuple[float, float] = (0.0, 0.0)
    include_self_weight: bool = False


@dataclass(frozen=True)
class LoadCombination:
    """Linear load combination expressed as factors of named load cases."""

    name: str
    factors: dict[str, float]


@dataclass(frozen=True)
class ElementResult:
    element_id: str
    length: float
    strain: float
    stress: float
    axial_force: float
    utilization: float | None
    mass: float


@dataclass(frozen=True)
class SolveResult:
    case_name: str
    displacements: dict[str, tuple[float, float]]
    reactions: dict[str, tuple[float, float]]
    element_results: list[ElementResult]
    max_displacement: float
    total_mass: float
    total_length: float
    result_kind: str = "load_case"


@dataclass
class TrussModel:
    """Validated model for a small 2D truss analysis problem."""

    nodes: list[Node]
    elements: list[Element]
    supports: list[Support]
    load_cases: list[LoadCase] = field(default_factory=list)
    load_combinations: list[LoadCombination] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrussModel":
        _ensure_unique_records(data.get("materials", []), "materials")
        _ensure_unique_records(data.get("sections", []), "sections")

        materials = {
            str(item["id"]): Material(
                id=str(item["id"]),
                youngs_modulus=float(item["E"]),
                density=float(item.get("density", 0.0)),
                yield_strength=(float(item["yield_strength"]) if item.get("yield_strength") is not None else None),
            )
            for item in data.get("materials", [])
        }
        sections = {
            str(item["id"]): Section(id=str(item["id"]), area=float(item["A"]))
            for item in data.get("sections", [])
        }

        nodes = [
            Node(
                id=str(node["id"]),
                x=float(node["x"]),
                y=float(node["y"]),
                load_x=_coerce_pair(node.get("load", [0.0, 0.0]))[0],
                load_y=_coerce_pair(node.get("load", [0.0, 0.0]))[1],
            )
            for node in data.get("nodes", [])
        ]
        elements: list[Element] = []
        for raw in data.get("elements", []):
            material = materials.get(str(raw.get("material"))) if raw.get("material") is not None else None
            section = sections.get(str(raw.get("section"))) if raw.get("section") is not None else None
            if raw.get("material") is not None and material is None:
                raise ValidationError(f"unknown material reference on element {raw.get('id')}")
            if raw.get("section") is not None and section is None:
                raise ValidationError(f"unknown section reference on element {raw.get('id')}")
            yield_strength = raw.get("yield_strength")
            elements.append(
                Element(
                    id=str(raw["id"]),
                    start=str(raw["start"]),
                    end=str(raw["end"]),
                    youngs_modulus=float(raw.get("E", material.youngs_modulus if material else 0.0)),
                    area=float(raw.get("A", section.area if section else 0.0)),
                    density=float(raw.get("density", material.density if material else 0.0)),
                    yield_strength=(
                        float(yield_strength)
                        if yield_strength is not None
                        else material.yield_strength if material else None
                    ),
                )
            )

        supports = [
            Support(
                node_id=str(support["node"]),
                fix_x=bool(_coerce_pair(support.get("fix", [False, False]))[0]),
                fix_y=bool(_coerce_pair(support.get("fix", [False, False]))[1]),
            )
            for support in data.get("supports", [])
        ]
        load_cases = [cls._load_case_from_dict(item) for item in data.get("load_cases", [])]
        load_combinations = [cls._load_combination_from_dict(item) for item in data.get("load_combinations", [])]
        model = cls(
            nodes=nodes,
            elements=elements,
            supports=supports,
            load_cases=load_cases,
            load_combinations=load_combinations,
            metadata=dict(data.get("metadata", {})),
        )
        model.validate()
        return model

    @staticmethod
    def _load_case_from_dict(data: dict[str, Any]) -> LoadCase:
        node_loads: dict[str, tuple[float, float]] = {}
        for item in data.get("node_loads", []):
            node_id = str(item["node"])
            load_x, load_y = _coerce_pair(item.get("load", [0.0, 0.0]))
            previous_x, previous_y = node_loads.get(node_id, (0.0, 0.0))
            node_loads[node_id] = (previous_x + load_x, previous_y + load_y)
        gravity = _coerce_pair(data.get("gravity", [0.0, 0.0]))
        return LoadCase(
            name=str(data["name"]),
            node_loads=node_loads,
            gravity=gravity,
            include_self_weight=bool(data.get("include_self_weight", False)),
        )

    @staticmethod
    def _load_combination_from_dict(data: dict[str, Any]) -> LoadCombination:
        factors = data.get("cases")
        if not isinstance(factors, dict) or not factors:
            raise ValidationError("load combinations require a non-empty 'cases' mapping")
        return LoadCombination(
            name=str(data["name"]),
            factors={str(case_name): float(factor) for case_name, factor in factors.items()},
        )

    def validate(self) -> None:
        if not self.nodes:
            raise ValidationError("model must contain at least one node")
        if not self.elements:
            raise ValidationError("model must contain at least one element")

        node_ids = [node.id for node in self.nodes]
        element_ids = [element.id for element in self.elements]
        support_ids = [support.node_id for support in self.supports]
        if len(node_ids) != len(set(node_ids)):
            raise ValidationError("node ids must be unique")
        if len(element_ids) != len(set(element_ids)):
            raise ValidationError("element ids must be unique")
        if len(support_ids) != len(set(support_ids)):
            raise ValidationError("supports must not duplicate nodes")

        node_lookup = {node.id: node for node in self.nodes}
        unknown_supports = set(support_ids).difference(node_lookup)
        if unknown_supports:
            raise ValidationError(f"supports reference unknown nodes: {sorted(unknown_supports)}")

        constrained_dofs = sum(int(item.fix_x) + int(item.fix_y) for item in self.supports)
        if constrained_dofs < 3:
            raise ValidationError("model is underconstrained; at least three reaction constraints are required")

        adjacency: dict[str, set[str]] = {node.id: set() for node in self.nodes}
        for element in self.elements:
            if element.start not in node_lookup or element.end not in node_lookup:
                raise ValidationError(f"element {element.id} references an unknown node")
            if element.start == element.end:
                raise ValidationError(f"element {element.id} has identical endpoints")
            if element.area <= 0.0 or element.youngs_modulus <= 0.0:
                raise ValidationError(f"element {element.id} must have positive area and modulus")
            if element.density < 0.0:
                raise ValidationError(f"element {element.id} density must be non-negative")
            if element.yield_strength is not None and element.yield_strength <= 0.0:
                raise ValidationError(f"element {element.id} yield strength must be positive")
            start = node_lookup[element.start]
            end = node_lookup[element.end]
            if math.isclose(start.x, end.x) and math.isclose(start.y, end.y):
                raise ValidationError(f"element {element.id} has zero length")
            adjacency[element.start].add(element.end)
            adjacency[element.end].add(element.start)

        floating = sorted(node_id for node_id, neighbours in adjacency.items() if not neighbours)
        if floating:
            raise ValidationError(f"disconnected free nodes without elements: {floating}")

        seeded = {support.node_id for support in self.supports}
        if seeded:
            visited = _bfs(seeded, adjacency)
            if len(visited) != len(self.nodes):
                missing = sorted(set(node_ids).difference(visited))
                raise ValidationError(f"nodes are not connected to the supported structure: {missing}")

        case_names = [case.name for case in self.load_cases]
        if len(case_names) != len(set(case_names)):
            raise ValidationError("load case names must be unique")
        for case in self.load_cases:
            for node_id in case.node_loads:
                if node_id not in node_lookup:
                    raise ValidationError(f"load case {case.name} references unknown node {node_id}")

        combination_names = [combo.name for combo in self.load_combinations]
        if len(combination_names) != len(set(combination_names)):
            raise ValidationError("load combination names must be unique")
        available_cases = set(case_names)
        for combo in self.load_combinations:
            if not combo.factors:
                raise ValidationError(f"load combination {combo.name} must define at least one factor")
            missing = sorted(set(combo.factors).difference(available_cases))
            if missing:
                raise ValidationError(f"load combination {combo.name} references unknown load cases: {missing}")

    def get_load_case(self, name: str | None) -> LoadCase:
        if name is None:
            if self.load_cases:
                return self.load_cases[0]
            return LoadCase(name="default")
        for case in self.load_cases:
            if case.name == name:
                return case
        raise ValidationError(f"unknown load case: {name}")

    def get_load_combination(self, name: str) -> LoadCombination:
        for combo in self.load_combinations:
            if combo.name == name:
                return combo
        raise ValidationError(f"unknown load combination: {name}")


def _coerce_pair(value: object) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValidationError("expected a two-value vector like [x, y]")
    return float(value[0]), float(value[1])


def _ensure_unique_records(records: object, label: str) -> None:
    if not isinstance(records, list):
        raise ValidationError(f"{label} must be a list")
    ids: list[str] = []
    duplicates: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or "id" not in record:
            raise ValidationError(f"every entry in {label} must be a mapping with an id")
        record_id = str(record["id"])
        if record_id in ids:
            duplicates.add(record_id)
        ids.append(record_id)
    if duplicates:
        raise ValidationError(f"duplicate {label} ids: {sorted(duplicates)}")


def _bfs(seeds: set[str], adjacency: dict[str, set[str]]) -> set[str]:
    visited = set(seeds)
    queue = deque(seeds)
    while queue:
        current = queue.popleft()
        for neighbour in adjacency[current]:
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)
    return visited
