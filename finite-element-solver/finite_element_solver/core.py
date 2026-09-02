from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
from typing import Iterable


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


@dataclass
class TrussModel:
    """Validated model for a small 2D truss analysis problem."""

    nodes: list[Node]
    elements: list[Element]
    supports: list[Support]
    load_cases: list[LoadCase] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "TrussModel":
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
        elements = []
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
        model = cls(
            nodes=nodes,
            elements=elements,
            supports=supports,
            load_cases=load_cases,
            metadata=dict(data.get("metadata", {})),
        )
        model.validate()
        return model

    @staticmethod
    def _load_case_from_dict(data: dict) -> LoadCase:
        node_loads: dict[str, tuple[float, float]] = {}
        for item in data.get("node_loads", []):
            node_loads[str(item["node"])] = _coerce_pair(item.get("load", [0.0, 0.0]))
        gravity = _coerce_pair(data.get("gravity", [0.0, 0.0]))
        return LoadCase(
            name=str(data["name"]),
            node_loads=node_loads,
            gravity=gravity,
            include_self_weight=bool(data.get("include_self_weight", False)),
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

    def get_load_case(self, name: str | None) -> LoadCase:
        if name is None:
            if self.load_cases:
                return self.load_cases[0]
            return LoadCase(name="default")
        for case in self.load_cases:
            if case.name == name:
                return case
        raise ValidationError(f"unknown load case: {name}")


class TrussSolver:
    """Direct stiffness solver with named load cases and self-weight support."""

    def __init__(self, model: TrussModel):
        self.model = model
        self._node_index = {node.id: idx for idx, node in enumerate(self.model.nodes)}

    def solve(self, case_name: str | None = None) -> SolveResult:
        load_case = self.model.get_load_case(case_name)
        node_count = len(self.model.nodes)
        dof_count = node_count * 2
        stiffness = [[0.0 for _ in range(dof_count)] for _ in range(dof_count)]
        loads = self._build_load_vector(load_case)

        for element in self.model.elements:
            self._assemble_element(stiffness, element)

        constrained = self._constrained_dofs()
        free = [dof for dof in range(dof_count) if dof not in constrained]
        if not free:
            raise ValidationError("model has no free degrees of freedom")

        reduced_k = [[stiffness[i][j] for j in free] for i in free]
        reduced_f = [loads[i] for i in free]
        reduced_u = _solve_linear_system(reduced_k, reduced_f)

        displacements = [0.0 for _ in range(dof_count)]
        for pos, dof in enumerate(free):
            displacements[dof] = reduced_u[pos]

        reactions_vector = _matvec(stiffness, displacements)
        reactions_vector = [reactions_vector[i] - loads[i] for i in range(dof_count)]

        displacement_map = {
            node.id: (displacements[2 * idx], displacements[2 * idx + 1])
            for idx, node in enumerate(self.model.nodes)
        }
        reactions = {}
        for support in self.model.supports:
            idx = self._node_index[support.node_id]
            rx = reactions_vector[2 * idx] if support.fix_x else 0.0
            ry = reactions_vector[2 * idx + 1] if support.fix_y else 0.0
            reactions[support.node_id] = (rx, ry)

        element_results = [self._element_result(element, displacements) for element in self.model.elements]
        max_displacement = max(math.hypot(dx, dy) for dx, dy in displacement_map.values())
        total_mass = sum(item.mass for item in element_results)
        total_length = sum(item.length for item in element_results)
        return SolveResult(
            case_name=load_case.name,
            displacements=displacement_map,
            reactions=reactions,
            element_results=element_results,
            max_displacement=max_displacement,
            total_mass=total_mass,
            total_length=total_length,
        )

    def solve_all_cases(self) -> list[SolveResult]:
        if not self.model.load_cases:
            return [self.solve()]
        return [self.solve(case.name) for case in self.model.load_cases]

    def _build_load_vector(self, load_case: LoadCase) -> list[float]:
        loads = [0.0 for _ in range(len(self.model.nodes) * 2)]
        for idx, node in enumerate(self.model.nodes):
            loads[2 * idx] += node.load_x
            loads[2 * idx + 1] += node.load_y
        for node_id, (fx, fy) in load_case.node_loads.items():
            idx = self._node_index[node_id]
            loads[2 * idx] += fx
            loads[2 * idx + 1] += fy
        if load_case.include_self_weight and load_case.gravity != (0.0, 0.0):
            gx, gy = load_case.gravity
            for element in self.model.elements:
                length = self._element_length(element)
                weight_x = element.density * element.area * length * gx
                weight_y = element.density * element.area * length * gy
                i = self._node_index[element.start]
                j = self._node_index[element.end]
                loads[2 * i] += 0.5 * weight_x
                loads[2 * i + 1] += 0.5 * weight_y
                loads[2 * j] += 0.5 * weight_x
                loads[2 * j + 1] += 0.5 * weight_y
        return loads

    def _assemble_element(self, stiffness: list[list[float]], element: Element) -> None:
        i = self._node_index[element.start]
        j = self._node_index[element.end]
        start = self.model.nodes[i]
        end = self.model.nodes[j]
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.hypot(dx, dy)
        cosine = dx / length
        sine = dy / length
        scale = element.youngs_modulus * element.area / length
        local = [
            [cosine * cosine, cosine * sine, -cosine * cosine, -cosine * sine],
            [cosine * sine, sine * sine, -cosine * sine, -sine * sine],
            [-cosine * cosine, -cosine * sine, cosine * cosine, cosine * sine],
            [-cosine * sine, -sine * sine, cosine * sine, sine * sine],
        ]
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        for row, global_row in enumerate(dofs):
            for col, global_col in enumerate(dofs):
                stiffness[global_row][global_col] += scale * local[row][col]

    def _constrained_dofs(self) -> set[int]:
        constrained: set[int] = set()
        for support in self.model.supports:
            idx = self._node_index[support.node_id]
            if support.fix_x:
                constrained.add(2 * idx)
            if support.fix_y:
                constrained.add(2 * idx + 1)
        return constrained

    def _element_length(self, element: Element) -> float:
        start = self.model.nodes[self._node_index[element.start]]
        end = self.model.nodes[self._node_index[element.end]]
        return math.hypot(end.x - start.x, end.y - start.y)

    def _element_result(self, element: Element, displacements: list[float]) -> ElementResult:
        i = self._node_index[element.start]
        j = self._node_index[element.end]
        start = self.model.nodes[i]
        end = self.model.nodes[j]
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.hypot(dx, dy)
        cosine = dx / length
        sine = dy / length
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        u = [displacements[dof] for dof in dofs]
        axial_extension = (-cosine) * u[0] + (-sine) * u[1] + cosine * u[2] + sine * u[3]
        strain = axial_extension / length
        stress = element.youngs_modulus * strain
        axial_force = stress * element.area
        utilization = None
        if element.yield_strength:
            utilization = abs(stress) / element.yield_strength
        mass = element.density * element.area * length
        return ElementResult(
            element_id=element.id,
            length=length,
            strain=strain,
            stress=stress,
            axial_force=axial_force,
            utilization=utilization,
            mass=mass,
        )


def summarize_model(model: TrussModel) -> dict[str, object]:
    """Return quick aggregate metrics for reporting and CLI summaries."""

    node_lookup = {node.id: node for node in model.nodes}
    lengths = []
    masses = []
    for element in model.elements:
        start = node_lookup[element.start]
        end = node_lookup[element.end]
        length = math.hypot(end.x - start.x, end.y - start.y)
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
        "total_length": sum(lengths),
        "total_mass": sum(masses),
        "bounding_box": bbox,
    }


def _coerce_pair(value: object) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValidationError("expected a two-value vector like [x, y]")
    return float(value[0]), float(value[1])


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


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    size = len(matrix)
    augmented = [row[:] + [rhs[idx]] for idx, row in enumerate(matrix)]
    for pivot in range(size):
        pivot_row = max(range(pivot, size), key=lambda row: abs(augmented[row][pivot]))
        if math.isclose(augmented[pivot_row][pivot], 0.0, abs_tol=1e-14):
            raise ValidationError("global stiffness matrix is singular; check supports and connectivity")
        if pivot_row != pivot:
            augmented[pivot], augmented[pivot_row] = augmented[pivot_row], augmented[pivot]
        pivot_value = augmented[pivot][pivot]
        for col in range(pivot, size + 1):
            augmented[pivot][col] /= pivot_value
        for row in range(size):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            if math.isclose(factor, 0.0, abs_tol=1e-18):
                continue
            for col in range(pivot, size + 1):
                augmented[row][col] -= factor * augmented[pivot][col]
    return [augmented[row][-1] for row in range(size)]


def _matvec(matrix: Iterable[Iterable[float]], vector: Iterable[float]) -> list[float]:
    vector_list = list(vector)
    return [sum(value * vector_list[idx] for idx, value in enumerate(row)) for row in matrix]
