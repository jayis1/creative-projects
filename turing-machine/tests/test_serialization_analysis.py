"""Tests for serialization, analysis, and debugger."""

import json
import pytest
from turing_machine.machine import TuringMachine, Tape, TMDirection, Program, Transition
from turing_machine.machines import binary_incrementer, palindrome_checker
from turing_machine.serialization import (
    serialize_machine, deserialize_machine,
    save_machine, load_machine,
    serialize_program, deserialize_program,
    serialize_tape, deserialize_tape,
)
from turing_machine.analysis import (
    reachable_states, dead_states, unused_states,
    analyze_machine, tape_statistics,
)
from turing_machine.debugger import Debugger, Breakpoint


class TestSerialization:
    def test_tape_roundtrip(self):
        t = Tape("_", ["1", "0", "1"], head=1)
        data = serialize_tape(t)
        t2 = deserialize_tape(data)
        assert t2.to_list() == t.to_list()
        assert t2.head == t.head

    def test_program_roundtrip(self):
        prog = binary_incrementer()
        data = serialize_program(prog)
        prog2 = deserialize_program(data)
        assert len(prog2) == len(prog)

    def test_machine_roundtrip(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1", "1"],
                           blank="_", halt_states={"halt"})
        tm.run()
        data = serialize_machine(tm)
        tm2 = deserialize_machine(data)
        assert tm2.state == tm.state
        assert tm2.steps == tm.steps
        assert tm2.tapes[0].to_list() == tm.tapes[0].to_list()

    def test_save_load_file(self, tmp_path):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1"],
                           blank="_", halt_states={"halt"})
        tm.run()
        path = str(tmp_path / "state.json")
        save_machine(tm, path)
        tm2 = load_machine(path)
        assert tm2.state == tm.state
        assert tm2.tapes[0].to_list() == tm.tapes[0].to_list()


class TestAnalysis:
    def test_reachable_states(self):
        prog = binary_incrementer()
        reach = reachable_states(prog, "s0")
        assert "s0" in reach
        assert "add" in reach
        assert "halt" in reach

    def test_dead_states_none(self):
        prog = binary_incrementer()
        dead = dead_states(prog, "s0", {"halt"})
        assert len(dead) == 0

    def test_unused_states(self):
        prog = Program([
            Transition("s0", "1", "0", "R", "s1"),
            Transition("s1", "0", "1", "L", "halt"),
            Transition("unused", "0", "0", "S", "unused"),
        ])
        unused = unused_states(prog, "s0")
        assert "unused" in unused

    def test_analyze_machine(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1"],
                           blank="_", halt_states={"halt"})
        tm.run()
        result = analyze_machine(tm)
        assert result["initial_state"] == "s0"
        assert result["halted"] == True
        assert result["steps_executed"] > 0
        assert "reachable_states" in result
        assert "dead_states" in result
        assert "transitions_per_state" in result

    def test_tape_statistics(self):
        t = Tape("_", ["1", "0", "1", "1", "_", "_"])
        stats = tape_statistics(t)
        assert stats["length"] >= 6
        assert stats["non_blank_count"] >= 4
        assert "symbol_counts" in stats


class TestDebugger:
    def test_basic_debugger(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1", "1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        dbg.run()
        assert tm.halted

    def test_breakpoint(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1", "1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        dbg.add_breakpoint("add")
        state = dbg.run()
        # Should stop at "add" or halt
        assert tm.state == "add" or tm.halted

    def test_conditional_breakpoint(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1", "1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        dbg.add_breakpoint("*", condition=lambda m: m.steps > 3)
        state = dbg.run()
        assert tm.steps >= 3

    def test_watch(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        dbg.watch("add")
        dbg.run()

    def test_status(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        status = dbg.status()
        assert "state" in status.lower()
        assert "steps" in status.lower()

    def test_reset(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        dbg.run()
        dbg.reset()
        assert tm.state == "s0"
        assert tm.steps == 0

    def test_step_and_continue(self):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1", "0", "1"],
                           blank="_", halt_states={"halt"})
        dbg = Debugger(tm)
        dbg.step()
        assert tm.steps == 1
        dbg.continue_run()
        assert tm.halted