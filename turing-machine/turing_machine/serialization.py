"""
turing_machine.serialization
============================

JSON serialization for Turing machines, programs, and tapes.

Supports saving/loading complete machine states, program definitions,
and tape snapshots.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Hashable, List, Optional, Tuple

from .machine import Program, Tape, TMDirection, Transition, TuringMachine, MultiTapeTM


def serialize_tape(tape: Tape) -> Dict[str, Any]:
    """Serialize a tape to a JSON-compatible dict."""
    return {
        "blank": str(tape.blank),
        "cells": [str(c) for c in tape._cells],
        "head": tape.head,
    }


def deserialize_tape(data: Dict[str, Any]) -> Tape:
    """Deserialize a tape from a dict."""
    return Tape(
        blank=data["blank"],
        tape=data["cells"],
        head=data["head"],
    )


def serialize_transition(t: Transition) -> Dict[str, Any]:
    """Serialize a transition to a JSON-compatible dict."""
    d = t.direction
    if isinstance(d, tuple):
        d = [str(x) for x in d]
    else:
        d = str(d)
    w = t.write
    if isinstance(w, tuple):
        w = [str(x) for x in w]
    else:
        w = str(w)
    r = t.read
    if isinstance(r, tuple):
        r = [str(x) for x in r]
    else:
        r = str(r)
    return {
        "state": t.state,
        "read": r,
        "write": w,
        "direction": d,
        "new_state": t.new_state,
    }


def deserialize_transition(data: Dict[str, Any]) -> Transition:
    """Deserialize a transition from a dict."""
    read = data["read"]
    if isinstance(read, list):
        read = tuple(read)
    write = data["write"]
    if isinstance(write, list):
        write = tuple(write)
    direction = data["direction"]
    if isinstance(direction, list):
        direction = tuple(direction)
    return Transition(
        state=data["state"],
        read=read,
        write=write,
        direction=direction,
        new_state=data["new_state"],
    )


def serialize_program(program: Program) -> Dict[str, Any]:
    """Serialize a program to a JSON-compatible dict."""
    return {
        "transitions": [serialize_transition(t) for t in program],
        "wildcards": [serialize_transition(t) for t in program._wildcards],
    }


def deserialize_program(data: Dict[str, Any]) -> Program:
    """Deserialize a program from a dict."""
    prog = Program()
    for tdata in data.get("transitions", []):
        prog.add(deserialize_transition(tdata))
    return prog


def serialize_machine(tm: TuringMachine) -> Dict[str, Any]:
    """Serialize a complete machine state to a JSON-compatible dict."""
    return {
        "initial_state": tm.initial_state,
        "state": tm.state,
        "steps": tm.steps,
        "halted": tm.halted,
        "max_steps": tm.max_steps,
        "num_tapes": tm.num_tapes,
        "halt_states": list(tm.halt_states),
        "program": serialize_program(tm.program),
        "tapes": [serialize_tape(t) for t in tm.tapes],
    }


def deserialize_machine(data: Dict[str, Any]) -> TuringMachine:
    """Deserialize a machine from a dict, restoring full state."""
    program = deserialize_program(data["program"])
    tapes = [deserialize_tape(t) for t in data["tapes"]]
    tm = TuringMachine(
        program=program,
        initial_state=data["initial_state"],
        tape=tapes if len(tapes) > 1 else tapes[0],
        halt_states=set(data["halt_states"]),
        max_steps=data["max_steps"],
        num_tapes=data["num_tapes"],
    )
    # Restore runtime state
    tm.state = data["state"]
    tm.steps = data["steps"]
    tm.halted = data["halted"]
    if data["num_tapes"] > 1:
        tm.tapes = tapes
    return tm


def save_machine(tm: TuringMachine, path: str) -> None:
    """Save a machine to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialize_machine(tm), f, indent=2)


def load_machine(path: str) -> TuringMachine:
    """Load a machine from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return deserialize_machine(json.load(f))