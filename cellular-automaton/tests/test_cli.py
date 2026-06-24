"""Tests for the CLI interface.

Run with: PYTHONPATH=. python -m pytest tests/test_cli.py -v
"""

import json
import os
import sys
import tempfile
from io import StringIO
from contextlib import redirect_stdout

import numpy as np
import pytest

from cellular_automaton.cli import build_parser, main


class TestCLIParser:
    """Tests for CLI parser construction."""

    def test_parser_builds(self):
        """Parser should build without errors."""
        parser = build_parser()
        assert parser.prog == "cellular-automaton"

    def test_version(self):
        """--version should print the version."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_no_command_fails(self):
        """No command should fail (required subcommand)."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestCLIRules:
    """Tests for the rules command."""

    def test_rules_command(self):
        """rules command should list all rules."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["rules"])
        output = buf.getvalue()
        assert "Named 2D rules:" in output
        assert "GameOfLife" in output
        assert "Elementary 1D rules" in output
        assert "Multi-state rules:" in output
        assert "Wireworld" in output
        assert rc == 0


class TestCLIPatterns:
    """Tests for the patterns command."""

    def test_patterns_command(self):
        """patterns command should list all patterns."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["patterns"])
        output = buf.getvalue()
        assert "Patterns:" in output
        assert "blinker" in output
        assert "glider" in output
        assert "gosper_gun" in output
        assert rc == 0


class TestCLIInfo:
    """Tests for the info command."""

    def test_info_elementary(self):
        """info command for an elementary rule."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["info", "--rule", "Rule30"])
        output = buf.getvalue()
        assert "Rule: Rule30" in output
        assert "Number: 30" in output
        assert "Wolfram table:" in output
        assert rc == 0

    def test_info_life_like(self):
        """info command for a Life-like rule."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["info", "--rule", "GameOfLife"])
        output = buf.getvalue()
        assert "Rule: GameOfLife" in output
        assert "Rule string:" in output
        assert "B3/S23" in output
        assert rc == 0

    def test_info_multistate(self):
        """info command for a multi-state rule."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["info", "--rule", "Wireworld"])
        output = buf.getvalue()
        assert "Rule: Wireworld" in output
        assert "States: 4" in output
        assert "State colors:" in output
        assert rc == 0


class TestCLISimulate:
    """Tests for the simulate command."""

    def test_simulate_basic(self):
        """simulate command should produce stats."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main([
                "simulate", "--rule", "GameOfLife",
                "--width", "10", "--height", "10",
                "--pattern", "blinker", "--px", "3", "--py", "4",
                "--steps", "20",
            ])
        output = buf.getvalue()
        assert "Steps run:" in output
        assert "Final alive:" in output
        assert rc == 0

    def test_simulate_json(self):
        """simulate --json should produce JSON stats."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main([
                "simulate", "--rule", "GameOfLife",
                "--width", "10", "--height", "10",
                "--pattern", "block", "--px", "3", "--py", "3",
                "--steps", "5", "--json",
            ])
        output = buf.getvalue()
        # Should contain JSON with braces.
        json_part = output[output.index("{"):]
        data = json.loads(json_part)
        assert "steps" in data
        assert "final_alive" in data
        assert rc == 0


class TestCLIRun:
    """Tests for the run command."""

    def test_run_rule30(self):
        """run command for Rule30 should produce output."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main([
                "run", "--rule", "Rule30",
                "--width", "20", "--steps", "3",
                "--boundary", "zero",
            ])
        output = buf.getvalue()
        assert len(output) > 0
        assert rc == 0


class TestCLIClassify:
    """Tests for the classify command."""

    def test_classify_single(self):
        """classify command for a single rule."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["classify", "--rule", "30", "--width", "21", "--steps", "50"])
        output = buf.getvalue()
        assert "Classification:" in output
        assert "Entropy:" in output
        assert rc == 0

    def test_classify_rule_0(self):
        """Rule 0 should classify as Class I."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main(["classify", "--rule", "0", "--width", "21", "--steps", "30"])
        output = buf.getvalue()
        assert "I" in output
        assert rc == 0


class TestCLIMultistate:
    """Tests for the multistate command."""

    def test_multistate_wireworld(self):
        """multistate command for Wireworld should run."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main([
                "multistate", "--rule", "Wireworld",
                "--width", "10", "--height", "5",
                "--random", "0.3", "--seed", "42",
                "--steps", "3",
            ])
        # Should produce some output (may be empty if all cells are 0).
        assert rc == 0

    def test_multistate_forest_fire(self):
        """multistate command for ForestFire should run."""
        buf = StringIO()
        with redirect_stdout(buf):
            rc = main([
                "multistate", "--rule", "ForestFire",
                "--width", "10", "--height", "5",
                "--random", "0.3", "--seed", "42",
                "--steps", "3", "--params", "p=0.01,g=0.1",
            ])
        assert rc == 0


class TestCLIConfig:
    """Tests for the config command."""

    def test_config_json(self):
        """config command with a JSON config file."""
        config_data = {
            "rule": "Rule30",
            "width": 20,
            "boundary": "zero",
            "initial": {"center": True},
            "steps": 5,
            "output": {"format": "ascii"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            path = f.name
        try:
            buf = StringIO()
            with redirect_stdout(buf):
                rc = main(["config", path])
            output = buf.getvalue()
            assert "Completed" in output
            assert rc == 0
        finally:
            os.unlink(path)


class TestCLISaveLoad:
    """Tests for save and load commands."""

    def test_save_and_load(self):
        """save then load should round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "state.json")
            # Save
            buf = StringIO()
            with redirect_stdout(buf):
                rc = main([
                    "save", "--rule", "Rule30",
                    "--width", "20", "--steps", "5",
                    "--boundary", "zero",
                    "-o", save_path,
                ])
            assert rc == 0
            assert os.path.exists(save_path)
            # Load
            buf = StringIO()
            with redirect_stdout(buf):
                rc = main(["load", save_path])
            output = buf.getvalue()
            assert "Loaded:" in output
            assert rc == 0