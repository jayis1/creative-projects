"""Tests for the visualizer and composition modules."""

import os
import pytest
from turing_machine.machine import TuringMachine
from turing_machine.machines import binary_incrementer, binary_decrementer
from turing_machine.visualizer import text_trace, html_animation, svg_diagram, csv_trace
from turing_machine.composition import Pipeline, Conditional, Loop, compose
from turing_machine.config import load_config, config_to_machine, save_config, ConfigError


class TestVisualizer:
    def _make_machine(self):
        prog = binary_incrementer()
        return TuringMachine(prog, initial_state="s0", tape=["1", "0", "1", "1"],
                             blank="_", halt_states={"halt"})

    def test_text_trace(self):
        tm = self._make_machine()
        result = text_trace(tm)
        assert "Step" in result
        assert "State" in result
        assert "halt" in result

    def test_html_animation(self, tmp_path):
        tm = self._make_machine()
        output = str(tmp_path / "anim.html")
        html = html_animation(tm, output, title="test")
        assert "<html" in html
        assert os.path.exists(output)

    def test_svg_diagram(self, tmp_path):
        tm = self._make_machine()
        output = str(tmp_path / "diag.svg")
        svg = svg_diagram(tm.program, "s0", {"halt"}, output)
        assert "<svg" in svg
        assert os.path.exists(output)

    def test_csv_trace(self):
        tm = self._make_machine()
        result = csv_trace(tm)
        assert "step" in result
        assert "state" in result


class TestComposition:
    def test_pipeline(self):
        pipe = Pipeline()
        pipe.add(binary_incrementer(), "s0", "halt", "_", "incr1")
        pipe.add(binary_incrementer(), "s0", "halt", "_", "incr2")
        result = pipe.run(["1", "0", "1"])  # 101 -> 110 -> 111
        assert result == ["1", "1", "1"]

    def test_pipeline_summary(self):
        pipe = Pipeline()
        pipe.add(binary_incrementer(), "s0", "halt", "_", "incr")
        pipe.run(["1"])
        summary = pipe.summary()
        assert "incr" in summary

    def test_conditional(self):
        cond = Conditional()
        cond.set_predicate(lambda tape: 0 if "1" in tape else 1)
        cond.add_branch(binary_incrementer(), "s0", "halt", "_", "incr")
        cond.add_branch(binary_decrementer(), "s0", "halt", "_", "decr")
        result = cond.run(["1", "0", "1"])
        assert result == ["1", "1", "0"]  # incremented

    def test_loop(self):
        loop = Loop()
        loop.set_machine(binary_incrementer(), "s0", "halt", "_")
        loop.set_condition(lambda tape, i: i < 3)
        result = loop.run(["0"])  # 0 -> 1 -> 10 -> 11
        assert result == ["1", "1"]

    def test_compose_helper(self):
        pipe = compose(
            (binary_incrementer(), "s0", "halt"),
            (binary_incrementer(), "s0", "halt"),
        )
        result = pipe.run(["1", "0"])  # 10 (2) -> 11 (3) -> 100 (4)
        assert result == ["1", "0", "0"]


class TestConfig:
    def test_load_json_config(self, tmp_path):
        config = {
            "name": "test_machine",
            "blank": "_",
            "start": "s0",
            "halt": ["halt"],
            "tapes": 1,
            "transitions": [
                {"state": "s0", "read": "1", "write": "0", "move": "R", "next": "halt"},
                {"state": "s0", "read": "0", "write": "1", "move": "R", "next": "halt"},
            ],
        }
        import json
        path = tmp_path / "test.json"
        path.write_text(json.dumps(config))

        data = load_config(str(path))
        assert data["name"] == "test_machine"

        tm = config_to_machine(data, tape=["1"])
        tm.run()
        assert tm.state == "halt"

    def test_config_missing_transitions(self):
        with pytest.raises(ConfigError):
            config_to_machine({"start": "s0"})

    def test_config_missing_start(self):
        with pytest.raises(ConfigError):
            config_to_machine({"transitions": []})

    def test_save_config(self, tmp_path):
        prog = binary_incrementer()
        tm = TuringMachine(prog, initial_state="s0", tape=["1"],
                           blank="_", halt_states={"halt"})
        path = str(tmp_path / "saved.json")
        save_config(tm, path, name="test_save")
        assert os.path.exists(path)

        # Reload.
        data = load_config(path)
        assert data["name"] == "test_save"
        assert len(data["transitions"]) > 0

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.json")