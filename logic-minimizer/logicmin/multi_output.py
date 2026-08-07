"""
Multi-output two-level minimization.

When several boolean functions share the same input variables, we can find
implicants that are useful for *multiple* outputs and share them, reducing
total literal cost compared to minimizing each output independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from .boolean import BooleanFunction, Implicant, cube_covers, cube_to_minterms, minterm_to_cube, var_names
from .quine_mccluskey import MinimizationResult, QuineMcCluskey


@dataclass
class SharedImplicant:
    """An implicant tagged with the set of outputs it serves."""

    implicant: Implicant
    outputs: FrozenSet[int]

    @property
    def cube(self) -> str:
        return self.implicant.cube

    def __repr__(self) -> str:
        return f"SharedImplicant({self.cube!r}, outputs={sorted(self.outputs)})"


@dataclass
class MultiOutputResult:
    """Result of multi-output minimization."""

    functions: List[BooleanFunction]
    per_output: List[List[Implicant]]
    shared_implicants: List[SharedImplicant]
    sop: List[str]
    total_literals: int
    total_terms: int
    method: str = "multi-output-qm"

    def __repr__(self) -> str:
        return (
            f"MultiOutputResult(outputs={len(self.functions)}, "
            f"total_terms={self.total_terms}, "
            f"total_literals={self.total_literals})"
        )


class MultiOutputMinimizer:
    """Multi-output Quine–McCluskey with output-tagged prime implicants.

    Parameters
    ----------
    n_vars : int
        Number of shared input variables.
    use_petrick : bool
        Use Petrick's method for the cyclic core (default True).
    """

    def __init__(self, n_vars: int, use_petrick: bool = True) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        if n_vars > 20:
            raise ValueError("multi-output mode supports at most 20 vars")
        self.n_vars = n_vars
        self.use_petrick = use_petrick

    def minimize(self, functions: Sequence[BooleanFunction]) -> MultiOutputResult:
        if not functions:
            raise ValueError("need at least one function")
        for f in functions:
            if f.n_vars != self.n_vars:
                raise ValueError(
                    f"function {f.name!r} has {f.n_vars} vars, expected {self.n_vars}"
                )
        # Build a "super-function" where each minterm is tagged with the set
        # of outputs that are 1 (or don't-care) there.
        # For prime generation we merge all minterms across outputs, but we
        # track which outputs each cube can serve.
        tagged = self._build_tagged(functions)
        primes = self._generate_tagged_primes(tagged, functions)
        # Per-output cover selection
        per_output: List[List[Implicant]] = []
        shared: List[SharedImplicant] = []
        shared_seen: Set[Tuple[str, FrozenSet[int]]] = set()
        for oi, func in enumerate(functions):
            # restrict primes to those whose output set includes oi and that
            # cover at least one onset minterm of this output
            usable = [p for p in primes if oi in p.outputs]
            # run QM cover selection on these
            qm = QuineMcCluskey(self.n_vars, use_petrick=self.use_petrick)
            # Build a temp function with only this output's minterms/dc
            # and use the usable primes as the prime set
            chosen = self._cover_output(func, usable, oi)
            per_output.append(chosen)
            for imp in chosen:
                key = (imp.cube, frozenset({oi}))
                if key not in shared_seen:
                    shared_seen.add(key)
                    shared.append(SharedImplicant(imp, frozenset({oi})))
        # Identify genuinely shared implicants (same cube used by >1 output)
        cube_outputs: Dict[str, Set[int]] = {}
        for oi, imps in enumerate(per_output):
            for imp in imps:
                cube_outputs.setdefault(imp.cube, set()).add(oi)
        shared_list: List[SharedImplicant] = []
        for cube, outs in cube_outputs.items():
            imp_obj = Implicant(cube)
            shared_list.append(SharedImplicant(imp_obj, frozenset(outs)))
        shared_list.sort(key=lambda s: s.cube)
        names = var_names(self.n_vars)
        sop_strings: List[str] = []
        total_lits = 0
        total_terms = 0
        for imps in per_output:
            terms = [imp.sop_term(names) for imp in imps]
            sop_strings.append(" + ".join(terms) if terms else "0")
            total_lits += sum(imp.n_literals for imp in imps)
            total_terms += len(imps)
        return MultiOutputResult(
            functions=list(functions),
            per_output=per_output,
            shared_implicants=shared_list,
            sop=sop_strings,
            total_literals=total_lits,
            total_terms=total_terms,
        )

    # -- tagged prime generation --------------------------------------------

    def _build_tagged(
        self, functions: Sequence[BooleanFunction]
    ) -> Dict[int, Set[int]]:
        """Map each minterm -> set of output indices where it's 1 or don't-care."""
        tagged: Dict[int, Set[int]] = {}
        for oi, f in enumerate(functions):
            for m in f.minterms:
                tagged.setdefault(m, set()).add(oi)
            for m in f.dontcare:
                tagged.setdefault(m, set()).add(oi)
        return tagged

    def _generate_tagged_primes(
        self,
        tagged: Dict[int, Set[int]],
        functions: Sequence[BooleanFunction],
    ) -> List[SharedImplicant]:
        """Generate prime implicants with output tags.

        Two cubes can merge only if they have the *same* output tag set,
        ensuring we don't create implicants that span incompatible outputs.
        """
        # Group cubes by output-tag
        # cube -> frozenset of outputs
        current: List[Tuple[str, FrozenSet[int]]] = []
        for m, outs in tagged.items():
            cube = minterm_to_cube(m, self.n_vars)
            current.append((cube, frozenset(outs)))
        primes: List[SharedImplicant] = []
        while current:
            used: Set[int] = set()
            next_level: List[Tuple[str, FrozenSet[int]]] = []
            # group by (output_tag, number_of_ones)
            from collections import defaultdict
            groups: Dict[Tuple[FrozenSet[int], int], List[str]] = defaultdict(list)
            idx_map: Dict[str, int] = {}
            for i, (cube, tag) in enumerate(current):
                idx_map[cube] = i
                groups[(tag, cube.count("1"))].append(cube)
            # try merging within adjacent groups of same tag
            tag_groups: Dict[FrozenSet[int], Dict[int, List[str]]] = defaultdict(dict)
            for (tag, ones), cubes in groups.items():
                tag_groups[tag][ones] = cubes
            for tag, by_ones in tag_groups.items():
                sorted_ones = sorted(by_ones.keys())
                for ki in range(len(sorted_ones) - 1):
                    a_ones = sorted_ones[ki]
                    b_ones = sorted_ones[ki + 1]
                    if b_ones != a_ones + 1:
                        continue
                    for a in by_ones[a_ones]:
                        for b in by_ones[b_ones]:
                            from .boolean import can_merge
                            merged = can_merge(a, b)
                            if merged is not None:
                                next_level.append((merged, tag))
                                used.add(idx_map[a])
                                used.add(idx_map[b])
            for i, (cube, tag) in enumerate(current):
                if i not in used:
                    primes.append(SharedImplicant(Implicant(cube), tag))
            # deduplicate next_level
            seen: Set[Tuple[str, FrozenSet[int]]] = set()
            dedup: List[Tuple[str, FrozenSet[int]]] = []
            for item in next_level:
                if item not in seen:
                    seen.add(item)
                    dedup.append(item)
            current = dedup
        # deduplicate primes
        seen_p: Set[str] = set()
        unique: List[SharedImplicant] = []
        for p in primes:
            if p.cube not in seen_p:
                seen_p.add(p.cube)
                unique.append(p)
        return unique

    def _cover_output(
        self, func: BooleanFunction, primes: List[SharedImplicant], oi: int
    ) -> List[Implicant]:
        """Select a minimum cover for one output from tagged primes."""
        onset = func.minterms
        if not onset:
            return []
        # Filter primes that actually cover onset minterms of this output
        relevant = [p for p in primes if (p.implicant.minterms & onset)]
        if not relevant:
            # fallback: singleton cubes
            return [Implicant(minterm_to_cube(m, self.n_vars)) for m in sorted(onset)]
        # Build coverage
        coverage: Dict[int, List[int]] = {m: [] for m in onset}
        for idx, p in enumerate(relevant):
            for m in p.implicant.minterms:
                if m in coverage:
                    coverage[m].append(idx)
        # essentials
        essential_idx: Set[int] = set()
        covered: Set[int] = set()
        for m, lst in coverage.items():
            if len(lst) == 1:
                essential_idx.add(lst[0])
        for idx in essential_idx:
            covered |= (relevant[idx].implicant.minterms & onset)
        remaining = onset - covered
        chosen = set(essential_idx)
        # greedy for the rest
        while remaining:
            best_idx = -1
            best_gain = -1
            best_lits = 10 ** 9
            for idx, p in enumerate(relevant):
                if idx in chosen:
                    continue
                gain = len(p.implicant.minterms & remaining)
                lits = p.implicant.n_literals
                if gain > best_gain or (gain == best_gain and lits < best_lits):
                    best_gain = gain
                    best_lits = lits
                    best_idx = idx
            if best_idx == -1 or best_gain == 0:
                break
            chosen.add(best_idx)
            remaining -= relevant[best_idx].implicant.minterms
        return [relevant[i].implicant for i in sorted(chosen)]