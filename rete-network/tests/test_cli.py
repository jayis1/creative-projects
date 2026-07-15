"""Tests for CLI commands (smoke tests using subprocess)."""
import subprocess
import sys
import pytest


def run_cli(*args, cwd=None):
    """Run the rete CLI and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "rete.cli", *args]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def examples_dir():
    import os
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(d, "examples")


class TestCLI:
    def test_version(self):
        rc, out, err = run_cli("version")
        assert rc == 0
        assert "rete-network" in out

    def test_run_social(self, examples_dir):
        rc, out, err = run_cli("run", f"{examples_dir}/social.json")
        assert rc == 0
        assert "Fired" in out

    def test_run_with_trace(self, examples_dir):
        rc, out, err = run_cli("run", f"{examples_dir}/social.json", "--trace")
        assert rc == 0
        assert "Step" in out or "Fired" in out

    def test_run_ancestry(self, examples_dir):
        rc, out, err = run_cli("run", f"{examples_dir}/ancestry.json")
        assert rc == 0
        assert "Fired" in out

    def test_agenda(self, examples_dir):
        rc, out, err = run_cli("agenda", f"{examples_dir}/social.json")
        assert rc == 0

    def test_validate(self, examples_dir):
        rc, out, err = run_cli("validate", f"{examples_dir}/social.json")
        assert rc == 0
        assert "OK" in out

    def test_validate_nonexistent(self):
        rc, out, err = run_cli("validate", "nonexistent.json")
        assert rc == 1

    def test_network_summary(self, examples_dir):
        rc, out, err = run_cli("network", f"{examples_dir}/social.json")
        assert rc == 0
        assert "Rete Network Summary" in out

    def test_network_dot(self, examples_dir):
        rc, out, err = run_cli("network", f"{examples_dir}/social.json", "--dot")
        assert rc == 0
        assert "digraph" in out

    def test_network_json_summary(self, examples_dir):
        rc, out, err = run_cli("network", f"{examples_dir}/social.json", "--summary")
        assert rc == 0
        import json
        data = json.loads(out)
        assert "rules" in data

    def test_stats(self, examples_dir):
        rc, out, err = run_cli("stats", f"{examples_dir}/social.json")
        assert rc == 0

    def test_run_with_strategy(self, examples_dir):
        rc, out, err = run_cli(
            "run", f"{examples_dir}/social.json", "--strategy", "fifo"
        )
        assert rc == 0

    def test_run_save_facts(self, examples_dir, tmp_path):
        out_file = tmp_path / "output.json"
        rc, out, err = run_cli(
            "run", f"{examples_dir}/social.json",
            "--save-facts", str(out_file),
        )
        assert rc == 0
        assert out_file.exists()