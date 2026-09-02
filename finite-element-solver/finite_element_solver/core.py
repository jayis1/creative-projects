from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


class ValidationError(ValueError):
    """Raised when a model is invalid or unsolvable."""


@dataclass(frozen=True)
class Node:
    id: str
    x: float
    y: float
    load_x: float = 0.0
    load_y: float = 0.0


@dataclass(frozen=True)
class Support:
    node_id: str
    fix_x: bool
    fix_y: bool


@dataclass(frozen=True)
class Element:
    id: str
    start: str
    end: str
    youngs_modulus: float
    area: float


@dataclass(frozen=True)
class ElementResult:
    element_id: str
    length: float
    strain: float
    stress: float
    axial_force: float


@dataclass(frozen=True)
class SolveResult:
    displacements: dict[str, tuple[float, float]]
    reactions: dict[str, tuple[float, float]]
    element_results: list[ElementResult]
    max_displacement: float


@dataclass
class TrussModel:
    nodes: list[Node]
    elements: list[Element]
    supports: list[Support]

    @classmethod
    def from_dict(cls, data: dict) -> "TrussModel":
        nodes = [
            Node(
                id=str(node["id"]),
                x=float(node["x"]),
                y=float(node["y"]),
                load_x=float(node.get("load", [0.0, 0.0])[0]),
                load_y=float(node.get("load", [0.0, 0.0])[1]),
            )
            for node in data.get("nodes", [])
        ]
        elements = [
            Element(
                id=str(element["id"]),
                start=str(element["start"]),
                end=str(element["end"]),
                youngs_modulus=float(element["E"]),
                area=float(element["A"]),
            )
            for element in data.get("elements", [])
        ]
        supports = [
            Support(
                node_id=str(support["node"]),
                fix_x=bool(support.get("fix", [False, False])[0]),
                fix_y=bool(support.get("fix", [False, False])[1]),
            )
            for support in data.get("supports", [])
        ]
        return cls(nodes=nodes, elements=elements, supports=supports)

    def validate(self) -> None:
        if not self.nodes:
            raise ValidationError("model must contain at least one node")
        if not self.elements:
            raise ValidationError("model must contain at least one element")
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValidationError("node ids must be unique")
        support_nodes = {support.node_id for support in self.supports}
        unknown_supports = support_nodes.difference(node_ids)
        if unknown_supports:
            raise ValidationError(f"supports reference unknown nodes: {sorted(unknown_supports)}")
        node_lookup = {node.id: node for node in self.nodes}
        constrained_dofs = 0
        for support in self.supports:
            constrained_dofs += int(support.fix_x) + int(support.fix_y)
        if constrained_dofs < 3:
            raise ValidationError("model is underconstrained; at least three reaction constraints are required")
        for element in self.elements:
            if element.start not in node_lookup or element.end not in node_lookup:
                raise ValidationError(f"element {element.id} references an unknown node")
            if element.start == element.end:
                raise ValidationError(f"element {element.id} has identical endpoints")
            if element.area <= 0.0 or element.youngs_modulus <= 0.0:
                raise ValidationError(f"element {element.id} must have positive area and modulus")
            start = node_lookup[element.start]
            end = node_lookup[element.end]
            if math.isclose(start.x, end.x) and math.isclose(start.y, end.y):
                raise ValidationError(f"element {element.id} has zero length")


class TrussSolver:
    """Solves small 2D pin-jointed truss systems using the direct stiffness method."""

    def __init__(self, model: TrussModel):
        self.model = model
        self.model.validate()
        self._node_index = {node.id: idx for idx, node in enumerate(self.model.nodes)}

    def solve(self) -> SolveResult:
        node_count = len(self.model.nodes)
        dof_count = node_count * 2
        stiffness = [[0.0 for _ in range(dof_count)] for _ in range(dof_count)]
        loads = [0.0 for _ in range(dof_count)]

        for idx, node in enumerate(self.model.nodes):
            loads[2 * idx] = node.load_x
            loads[2 * idx + 1] = node.load_y

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

        displacement_map = {}
        for node_id, idx in self._node_index.items():
            displacement_map[node_id] = (displacements[2 * idx], displacements[2 * idx + 1])

        reactions = {}
        for support in self.model.supports:
            idx = self._node_index[support.node_id]
            rx = reactions_vector[2 * idx] if support.fix_x else 0.0
            ry = reactions_vector[2 * idx + 1] if support.fix_y else 0.0
            reactions[support.node_id] = (rx, ry)

        element_results = [self._element_result(element, displacements) for element in self.model.elements]
        max_displacement = max(math.hypot(dx, dy) for dx, dy in displacement_map.values())
        return SolveResult(
            displacements=displacement_map,
            reactions=reactions,
            element_results=element_results,
            max_displacement=max_displacement,
        )

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
        force = stress * element.area
        return ElementResult(
            element_id=element.id,
            length=length,
            strain=strain,
            stress=stress,
            axial_force=force,
        )


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
