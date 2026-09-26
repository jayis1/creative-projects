"""Core de Bruijn graph construction and Eulerian assembly."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AssemblyResult:
    """Assembled contigs and basic graph statistics."""
    contigs: tuple[str, ...]
    k: int
    reads: int
    kmers: int


def parse_reads(source: str | Path) -> list[str]:
    """Read newline-delimited, FASTA, or FASTQ sequences."""
    text = Path(source).read_text() if isinstance(source, Path) or Path(str(source)).exists() else str(source)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    if lines[0].startswith(">"):
        return ["".join(lines[i + 1 : j]).upper() for i, line in enumerate(lines) if line.startswith(">") for j in [next((x for x in range(i + 1, len(lines)) if lines[x].startswith(">")), len(lines))]]
    if lines[0].startswith("@") and len(lines) >= 4:
        return [lines[i + 1].upper() for i in range(0, len(lines) - 3, 4) if lines[i].startswith("@")] 
    return [line.upper() for line in lines if not line.startswith(("+", "@"))]


def build_graph(reads: Iterable[str], k: int) -> tuple[dict[str, Counter[str]], int]:
    """Build a directed multigraph represented by adjacency counters."""
    if k < 2:
        raise ValueError("k must be at least 2")
    graph: dict[str, Counter[str]] = defaultdict(Counter)
    count = 0
    for read in reads:
        sequence = read.strip().upper()
        if len(sequence) < k:
            continue
        for i in range(len(sequence) - k + 1):
            kmer = sequence[i : i + k]
            if any(base not in "ACGTN" for base in kmer):
                continue
            graph[kmer[:-1]][kmer[1:]] += 1
            count += 1
    return dict(graph), count


def _eulerian_contigs(graph: dict[str, Counter[str]]) -> list[str]:
    """Walk non-branching paths, consuming each edge exactly once."""
    indegree: Counter[str] = Counter()
    outdegree: Counter[str] = Counter()
    for node, edges in graph.items():
        outdegree[node] += sum(edges.values())
        for target, count in edges.items():
            indegree[target] += count
    starts = [node for node in graph if outdegree[node] != 1 or indegree[node] != 1]
    contigs: list[str] = []
    for start in starts:
        for target, count in list(graph.get(start, {}).items()):
            while graph[start][target]:
                graph[start][target] -= 1
                node = target
                sequence = start + node[-1]
                while indegree[node] == 1 and outdegree[node] == 1:
                    next_node = next(n for n, c in graph.get(node, {}).items() if c)
                    graph[node][next_node] -= 1
                    node = next_node
                    sequence += node[-1]
                contigs.append(sequence)
    # Remaining isolated cycles have no branch start; emit one cycle per component.
    for start, edges in graph.items():
        for target, count in list(edges.items()):
            while graph[start][target]:
                graph[start][target] -= 1
                node, sequence = target, start + target[-1]
                while node != start:
                    next_node = next(n for n, c in graph.get(node, {}).items() if c)
                    graph[node][next_node] -= 1
                    node, sequence = next_node, sequence + next_node[-1]
                contigs.append(sequence)
    return sorted(contigs, key=lambda value: (-len(value), value))


def assemble(reads: Iterable[str], k: int = 21) -> AssemblyResult:
    """Assemble reads into maximal non-branching contigs."""
    materialized = list(reads)
    graph, kmer_count = build_graph(materialized, k)
    contigs = _eulerian_contigs({node: Counter(edges) for node, edges in graph.items()})
    return AssemblyResult(tuple(contigs), k, len(materialized), kmer_count)
