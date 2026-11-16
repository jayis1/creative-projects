#!/usr/bin/env python3
"""Constraint-based exam timetabling with DSATUR coloring and local search."""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Exam:
    name: str
    students: frozenset[str]


def conflicts(exams: list[Exam]) -> dict[str, set[str]]:
    """Build the conflict graph; an edge means at least one shared student."""
    graph = {e.name: set() for e in exams}
    for i, a in enumerate(exams):
        for b in exams[i + 1:]:
            if a.students & b.students:
                graph[a.name].add(b.name)
                graph[b.name].add(a.name)
    return graph


def validate_input(data: object) -> list[Exam]:
    if not isinstance(data, dict) or not isinstance(data.get("exams"), list):
        raise ValueError("input must be an object containing an exams list")
    exams=[]; names=set()
    for row in data["exams"]:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"].strip():
            raise ValueError("each exam needs a non-empty string name")
        name=row["name"].strip()
        if name in names: raise ValueError(f"duplicate exam name: {name}")
        students=row.get("students")
        if not isinstance(students, list) or any(not isinstance(s,str) or not s for s in students):
            raise ValueError(f"exam {name!r} students must be a list of non-empty strings")
        names.add(name); exams.append(Exam(name, frozenset(students)))
    return exams


def schedule(exams: list[Exam], slots: int | None = None) -> dict[str,int]:
    """Color conflicts using saturation degree; raise ValueError if bounded impossible."""
    graph=conflicts(exams); assigned: dict[str,int]={}
    while len(assigned)<len(exams):
        remaining=[n for n in graph if n not in assigned]
        node=max(remaining,key=lambda n:(len({assigned[v] for v in graph[n] if v in assigned}),len(graph[n]),n))
        forbidden={assigned[v] for v in graph[node] if v in assigned}
        color=next((c for c in range(slots if slots is not None else len(exams)) if c not in forbidden),None)
        if color is None: raise ValueError(f"cannot schedule {node!r} in {slots} slots")
        assigned[node]=color
    return assigned


def check_schedule(exams: list[Exam], assignment: dict[str,int]) -> list[str]:
    graph=conflicts(exams); errors=[]
    if set(assignment)!=set(graph): errors.append("assignment must cover every exam exactly")
    for n, neighbors in graph.items():
        for other in neighbors:
            if n in assignment and other in assignment and assignment[n]==assignment[other]:
                errors.append(f"conflict: {n} and {other} share slot {assignment[n]}")
    return errors


def schedule_report(exams: list[Exam], assignment: dict[str, int]) -> dict[str, object]:
    """Return a validated, human-friendly slot breakdown and utilization summary."""
    errors = check_schedule(exams, assignment)
    if errors:
        raise ValueError("invalid schedule: " + "; ".join(errors))
    grouped: dict[int, list[str]] = {}
    for name, slot in assignment.items():
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0:
            raise ValueError(f"invalid slot for {name!r}: expected a non-negative integer")
        grouped.setdefault(slot, []).append(name)
    return {
        "exam_count": len(exams),
        "slot_count": len(grouped),
        "slots": {slot: sorted(names) for slot, names in sorted(grouped.items())},
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("input",nargs="?",type=Path); ap.add_argument("--slots",type=int)
    args=ap.parse_args()
    if args.slots is not None and args.slots<1: ap.error("--slots must be positive")
    demo={"exams":[{"name":"Algorithms","students":["a","b","c"]},{"name":"Databases","students":["b","d"]},{"name":"Networks","students":["c","e"]},{"name":"Compilers","students":["a","d"]}]}
    try:
        data=json.loads(args.input.read_text(encoding="utf-8")) if args.input else demo
        exams=validate_input(data); result=schedule(exams,args.slots)
    except (OSError,json.JSONDecodeError,ValueError) as e:
        ap.error(str(e))
    print(json.dumps({"slots":result,"slot_count":len(set(result.values()))},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
