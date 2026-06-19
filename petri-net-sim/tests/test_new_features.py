"""Tests for PNML export/import, config files, and batch simulation."""

import json
import os
import tempfile
import pytest
from petri import PetriNet, Place, Transition
from petri.pnml import to_pnml, from_pnml, validate_pnml
from petri.config import load_config, save_config, from_config_dict, to_config_dict
from petri.batch import batch_simulate
from petri.presets import workflow_net, mutual_exclusion, dining_philosophers


class TestPNML:
    def test_roundtrip(self):
        """Export to PNML and import back — net should be equivalent."""
        net = workflow_net()
        pnml = to_pnml(net)
        assert "<pnml" in pnml
        assert "workflow" in pnml

        imported = from_pnml(pnml)
        assert imported.name == "workflow"
        assert len(imported.places) == len(net.places)
        assert len(imported.transitions) == len(net.transitions)

    def test_validate_valid_pnml(self):
        net = mutual_exclusion()
        pnml = to_pnml(net)
        issues = validate_pnml(pnml)
        assert len(issues) == 0, f"Expected no issues, got: {issues}"

    def test_validate_invalid_xml(self):
        issues = validate_pnml("not valid xml")
        assert len(issues) > 0

    def test_pnml_with_weights(self):
        """Arcs with weight > 1 should have inscriptions."""
        net = PetriNet("weighted")
        net.add_place(Place("p", initial=3))
        net.add_place(Place("q"))
        net.add_transition(Transition("t"))
        net.add_arc("p", "t", weight=2)
        net.add_arc("t", "q", weight=3)
        pnml = to_pnml(net)
        assert "inscription" in pnml
        assert "2" in pnml
        assert "3" in pnml

    def test_pnml_capacity(self):
        """Capacity should be exported."""
        net = PetriNet("capped")
        net.add_place(Place("p", initial=1, capacity=5))
        net.add_transition(Transition("t"))
        net.add_arc("p", "t")
        pnml = to_pnml(net)
        assert "capacity" in pnml
        assert "5" in pnml

    def test_import_preserves_initial_marking(self):
        net = PetriNet("test_im")
        net.add_place(Place("p1", initial=3))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        pnml = to_pnml(net)
        imported = from_pnml(pnml)
        assert imported.place("p1").initial == 3
        assert imported.place("p2").initial == 0


class TestConfig:
    def test_from_config_dict(self):
        data = {
            "name": "test_net",
            "places": [
                {"name": "p1", "initial": 1},
                {"name": "p2", "initial": 0, "capacity": 5},
            ],
            "transitions": [
                {"name": "t1", "label": "do something"},
            ],
            "arcs": [
                {"source": "p1", "target": "t1", "weight": 1},
                {"source": "t1", "target": "p2", "weight": 1},
            ],
        }
        net = from_config_dict(data)
        assert net.name == "test_net"
        assert len(net.places) == 2
        assert len(net.transitions) == 1
        assert net.place("p2").capacity == 5

    def test_to_config_dict(self):
        net = workflow_net()
        d = to_config_dict(net)
        assert d["name"] == "workflow"
        assert len(d["places"]) == 4
        assert len(d["transitions"]) == 4
        assert len(d["arcs"]) > 0

    def test_save_load_json(self):
        net = workflow_net()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_config(net, path, format="json")
            loaded = load_config(path)
            assert loaded.name == "workflow"
            assert len(loaded.places) == len(net.places)
        finally:
            os.unlink(path)

    def test_invalid_place_def(self):
        with pytest.raises(ValueError):
            from_config_dict({"places": [{"no_name": True}]})

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.json")


class TestBatchSimulate:
    def test_basic_batch(self):
        net = mutual_exclusion()
        stats = batch_simulate(net, num_runs=50, max_steps=30, seed=42)
        assert stats.num_runs == 50
        assert 0 <= stats.deadlock_probability <= 1.0
        assert stats.mean_steps >= 0
        assert 0 <= stats.deadlock_ci_low <= stats.deadlock_ci_high <= 1.0

    def test_reproducible(self):
        net = mutual_exclusion()
        s1 = batch_simulate(net, num_runs=50, max_steps=30, seed=42)
        s2 = batch_simulate(net, num_runs=50, max_steps=30, seed=42)
        assert s1.deadlock_probability == s2.deadlock_probability
        assert s1.mean_steps == s2.mean_steps

    def test_transition_frequencies(self):
        net = dining_philosophers(3)
        stats = batch_simulate(net, num_runs=50, max_steps=50, seed=42)
        # If any transitions fired, frequencies should sum to ~1.0
        if stats.transition_fire_frequencies:
            total = sum(stats.transition_fire_frequencies.values())
            assert abs(total - 1.0) < 1e-6

    def test_repr(self):
        net = mutual_exclusion()
        stats = batch_simulate(net, num_runs=10, max_steps=10, seed=42)
        r = repr(stats)
        assert "BatchStats" in r
        assert "Deadlock" in r


class TestNewPresets:
    def test_token_ring(self):
        from petri.presets import token_ring
        net = token_ring(4)
        assert len(net.places) == 8  # 4 has_token + 4 wait
        assert len(net.transitions) == 8

    def test_database_transaction(self):
        from petri.presets import database_transaction
        net = database_transaction()
        assert len(net.places) == 5
        assert len(net.transitions) == 5

    def test_pipeline(self):
        from petri.presets import producer_consumer_chain
        net = producer_consumer_chain(3)
        assert len(net.places) > 0
        assert len(net.transitions) > 0