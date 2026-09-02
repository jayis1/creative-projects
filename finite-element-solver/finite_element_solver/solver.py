from __future__ import annotations

import math
from typing import Iterable

from .model import Element, ElementResult, LoadCase, SolveResult, TrussModel, ValidationError


class TrussSolver:
    """Direct stiffness solver with named load cases, combinations, and self-weight support."""

    def __init__(self, model: TrussModel):
        self.model = model
        self._node_index = {node.id: idx for idx, node in enumerate(self.model.nodes)}
        self._base_loads = self._build_base_load_vector()

    def solve(self, case_name: str | None = None) -> SolveResult:
        load_case = self.model.get_load_case(case_name)
        loads = self._combine_load_vectors([(1.0, load_case)], include_base_loads=True)
        return self._solve_from_loads(load_case.name, loads, result_kind="load_case")

    def solve_combination(self, name: str) -> SolveResult:
        combination = self.model.get_load_combination(name)
        weighted_cases = [(factor, self.model.get_load_case(case_name)) for case_name, factor in combination.factors.items()]
        loads = self._combine_load_vectors(weighted_cases, include_base_loads=True)
        return self._solve_from_loads(combination.name, loads, result_kind="load_combination")

    def solve_all_cases(self) -> list[SolveResult]:
        if not self.model.load_cases:
            return [self.solve()]
        return [self.solve(case.name) for case in self.model.load_cases]

    def solve_all_combinations(self) -> list[SolveResult]:
        return [self.solve_combination(combo.name) for combo in self.model.load_combinations]

    def _solve_from_loads(self, result_name: str, loads: list[float], result_kind: str) -> SolveResult:
        node_count = len(self.model.nodes)
        dof_count = node_count * 2
        stiffness = [[0.0 for _ in range(dof_count)] for _ in range(dof_count)]

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
            case_name=result_name,
            displacements=displacement_map,
            reactions=reactions,
            element_results=element_results,
            max_displacement=max_displacement,
            total_mass=total_mass,
            total_length=total_length,
            result_kind=result_kind,
        )

    def _build_base_load_vector(self) -> list[float]:
        loads = [0.0 for _ in range(len(self.model.nodes) * 2)]
        for idx, node in enumerate(self.model.nodes):
            loads[2 * idx] += node.load_x
            loads[2 * idx + 1] += node.load_y
        return loads

    def _combine_load_vectors(
        self,
        weighted_cases: list[tuple[float, LoadCase]],
        *,
        include_base_loads: bool,
    ) -> list[float]:
        loads = self._base_loads[:] if include_base_loads else [0.0 for _ in self._base_loads]
        for factor, load_case in weighted_cases:
            case_loads = self._build_case_load_vector(load_case)
            for idx, value in enumerate(case_loads):
                loads[idx] += factor * value
        return loads

    def _build_case_load_vector(self, load_case: LoadCase) -> list[float]:
        loads = [0.0 for _ in range(len(self.model.nodes) * 2)]
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
