"""Core de Bruijn graph construction and Eulerian assembly."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_VALID_BASES = frozenset("ACGTN")


@dataclass(frozen=True)
class AssemblyResult:
    """Assembled contigs and reproducible graph/assembly statistics."""
    contigs: tuple[str, ...]
    k: int
    reads: int
    kmers: int
    graph_nodes: int = 0
    n50: int = 0

    @property
    def total_bases(self) -> int:
        return sum(map(len, self.contigs))


def _read_text(source: str | Path) -> str:
    """Distinguish literal sequence text from a path without path-length errors."""
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    candidate = str(source)
    try:
        path = Path(candidate)
        if len(candidate) < 4096 and path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        pass
    return candidate


def parse_reads(source: str | Path, *, strict: bool = True) -> list[str]:
    """Read newline-delimited, FASTA, or FASTQ sequences.

    FASTQ records are validated in strict mode, including sequence/quality length.
    Blank lines are ignored in all formats.
    """
    lines = [line.strip() for line in _read_text(source).splitlines() if line.strip()]
    if not lines:
        return []
    if lines[0].startswith(">"):
        reads: list[str] = []
        current: list[str] = []
        for line in lines:
            if line.startswith(">"):
                if current:
                    reads.append("".join(current).upper())
                    current = []
            else:
                current.append(line)
        if current:
            reads.append("".join(current).upper())
        return reads
    if lines[0].startswith("@"):
        if len(lines) % 4:
            raise ValueError("FASTQ input must contain complete four-line records")
        reads = []
        for i in range(0, len(lines), 4):
            header, sequence, plus, quality = lines[i : i + 4]
            if not header.startswith("@") or not plus.startswith("+"):
                raise ValueError(f"invalid FASTQ record near line {i + 1}")
            if strict and len(sequence) != len(quality):
                raise ValueError(f"FASTQ sequence/quality length mismatch near line {i + 1}")
            reads.append(sequence.upper())
        return reads
    return [line.upper() for line in lines if not line.startswith("+")]


def build_graph(reads: Iterable[str], k: int, *, min_count: int = 1) -> tuple[dict[str, Counter[str]], int]:
    """Build a directed weighted de Bruijn graph, optionally dropping rare k-mers."""
    if k < 2:
        raise ValueError("k must be at least 2")
    if min_count < 1:
        raise ValueError("min_count must be at least 1")
    kmer_counts: Counter[str] = Counter()
    for read in reads:
        sequence = read.strip().upper()
        for i in range(max(0, len(sequence) - k + 1)):
            kmer = sequence[i : i + k]
            if len(kmer) == k and set(kmer) <= _VALID_BASES:
                kmer_counts[kmer] += 1
    graph: dict[str, Counter[str]] = defaultdict(Counter)
    for kmer, count in kmer_counts.items():
        if count >= min_count:
            graph[kmer[:-1]][kmer[1:]] = count
    return dict(graph), sum(graph[node][target] for node in graph for target in graph[node])


def graph_stats(graph: dict[str, Counter[str]]) -> dict[str, int]:
    """Return node, edge, and branching counts for diagnostics."""
    edges = sum(sum(edges_for_node.values()) for edges_for_node in graph.values())
    targets = {target for edges_for_node in graph.values() for target in edges_for_node}
    nodes = set(graph) | targets
    branching = sum(1 for node in nodes if len(graph.get(node, {})) > 1)
    return {"nodes": len(nodes), "edges": edges, "branching_nodes": branching}


def _n50(contigs: list[str]) -> int:
    total = sum(map(len, contigs))
    running = 0
    for length in sorted((len(c) for c in contigs), reverse=True):
        running += length
        if running * 2 >= total:
            return length
    return 0


def _eulerian_contigs(graph: dict[str, Counter[str]]) -> list[str]:
    """Walk every weighted edge on maximal non-branching paths."""
    indegree: Counter[str] = Counter()
    outdegree: Counter[str] = Counter()
    for node, edges in graph.items():
        outdegree[node] += len(edges)
        for target, count in edges.items():
            indegree[target] += 1
    starts = [node for node in graph if outdegree[node] != 1 or indegree[node] != 1]
    contigs: list[str] = []
    for start in starts:
        for target in list(graph.get(start, {})):
            while graph[start][target]:
                graph[start][target] = 0
                node, sequence = target, start + target[-1]
                while indegree[node] == 1 and outdegree[node] == 1:
                    next_node = next(n for n, count in graph.get(node, {}).items() if count)
                    graph[node][next_node] = 0
                    node, sequence = next_node, sequence + next_node[-1]
                contigs.append(sequence)
    for start, edges in graph.items():
        for target in list(edges):
            while graph[start][target]:
                graph[start][target] = 0
                node, sequence = target, start + target[-1]
                while node != start:
                    next_node = next(n for n, count in graph.get(node, {}).items() if count)
                    graph[node][next_node] = 0
                    node, sequence = next_node, sequence + next_node[-1]
                contigs.append(sequence)
    return sorted(contigs, key=lambda value: (-len(value), value))


def assemble(reads: Iterable[str], k: int = 21, *, min_count: int = 1) -> AssemblyResult:
    """Assemble reads into maximal non-branching contigs."""
    materialized = list(reads)
    graph, kmer_count = build_graph(materialized, k, min_count=min_count)
    stats = graph_stats(graph)
    contigs = _eulerian_contigs({node: Counter(edges) for node, edges in graph.items()})
    return AssemblyResult(tuple(contigs), k, len(materialized), kmer_count, stats["nodes"], _n50(contigs))
