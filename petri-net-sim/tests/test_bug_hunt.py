"""Tests for bug hunt — verifying bugs before and after fixes."""

import pytest
from petri import (
    PetriNet, Place, Transition, Simulator,
    analyze_boundedness, is_reversible, coverability_tree,
    is_reachable, reachability_graph,
)
from petri.analysis import _marking_key
from petri.presets import mutual_exclusion, workflow_net


class TestBug1BoundednessUnbounded:
    """Bug: analyze_boundedness never detects unbounded nets because
    it uses detect_omega=False but checks rg.omega_markings."""

    def test_unbounded_net_detected(self):
        """An unbounded net should be detected as unbounded."""
        net = PetriNet("unbounded")
        net.add_place(Place("p", initial=1))
        net.add_place(Place("counter", initial=0))
        net.add_transition(Transition("inc"))
        net.add_arc("p", "inc")
        net.add_arc("inc", "p")
        net.add_arc("inc", "counter")
        # "counter" grows without bound
        b = analyze_boundedness(net, max_states=1000)
        assert not b.is_bounded, "Unbounded net should be detected as unbounded"


class TestBug2FireUntilFinalCheck:
    """Bug: fire_until doesn't check target after the last firing."""

    def test_target_reached_on_last_step(self):
        """If target is reached on the last step, should return the sequence."""
        net = workflow_net()
        sim = Simulator(net, seed=42)
        # Fire until {"end": 1} — the random walk may take varying steps
        # due to possible reject->review loops. Use enough steps.
        seq = sim.fire_until({"end": 1}, max_steps=20)
        assert seq is not None, "Should find the target within 20 steps"
        assert len(seq) > 0, "Should take at least 1 step"

    def test_target_reached_exactly_at_limit(self):
        """Target reached on the very last allowed step should still be found.

        With the fix, fire_until checks after each firing, so a target
        reached on step N with max_steps=N is detected.
        """
        net = PetriNet("simple_chain")
        net.add_place(Place("p0", initial=1))
        net.add_place(Place("p1", initial=0))
        net.add_place(Place("p2", initial=0))
        net.add_place(Place("p3", initial=0))
        net.add_transition(Transition("t0"))
        net.add_transition(Transition("t1"))
        net.add_transition(Transition("t2"))
        net.add_arc("p0", "t0")
        net.add_arc("t0", "p1")
        net.add_arc("p1", "t1")
        net.add_arc("t1", "p2")
        net.add_arc("p2", "t2")
        net.add_arc("t2", "p3")
        sim = Simulator(net, seed=0)
        # Only one enabled transition at each step, so deterministic
        # Target p3=1 is reached after exactly 3 firings
        seq = sim.fire_until({"p3": 1}, max_steps=3)
        assert seq is not None, "Should find target at exactly step limit"
        assert len(seq) == 3, f"Should take exactly 3 steps, took {len(seq)}"


class TestBug3MarkingKeyConsistency:
    """Bug: _marking_key uses dict keys instead of all place names."""

    def test_marking_key_consistent(self):
        """_marking_key should be consistent with reachability_graph's mk_key."""
        net = mutual_exclusion()
        rg = reachability_graph(net)
        # All markings in the reachability graph should have the same key
        # regardless of which function is used
        for node in rg.nodes.values():
            # _marking_key should use ALL place names, not just dict keys
            key1 = _marking_key(node.marking)
            # Manually compute using all places
            all_places = sorted(net.places)
            key2 = tuple(node.marking.get(p, 0) for p in all_places)
            assert key1 == key2, f"Key mismatch for marking {node.marking}"

    def test_marking_key_missing_place(self):
        """_marking_key should handle markings that don't include all places.

        When place_names is provided, missing places are treated as 0.
        """
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_place(Place("p3", initial=0))
        # A marking that's missing p3
        marking = {"p1": 1, "p2": 0}
        # Using place_names ensures all places are included
        place_names = sorted(net.places)  # ["p1", "p2", "p3"]
        key = _marking_key(marking, place_names)
        # Should include p3 as 0
        expected = (1, 0, 0)  # p1=1, p2=0, p3=0
        assert key == expected, f"Key {key} doesn't match expected {expected}"

    def test_marking_key_without_place_names(self):
        """Without place_names, _marking_key uses dict keys (backward compat)."""
        marking = {"p1": 1, "p2": 0}
        key = _marking_key(marking)
        expected = (1, 0)  # sorted keys: p1, p2
        assert key == expected


class TestBug4CoverabilityReExpansion:
    """Bug: coverability_tree doesn't re-expand nodes when their marking is updated."""

    def test_coverability_finds_all_omega(self):
        """Coverability tree should find all unbounded places."""
        net = PetriNet("multi_unbounded")
        net.add_place(Place("p", initial=1))
        net.add_place(Place("c1", initial=0))
        net.add_place(Place("c2", initial=0))
        net.add_transition(Transition("inc1"))
        net.add_transition(Transition("inc2"))
        net.add_arc("p", "inc1")
        net.add_arc("inc1", "p")
        net.add_arc("inc1", "c1")
        net.add_arc("p", "inc2")
        net.add_arc("inc2", "p")
        net.add_arc("inc2", "c2")
        tree = coverability_tree(net, max_nodes=1000)
        assert tree.is_unbounded, "Net should be unbounded"
        assert "c1" in tree.omega_places, "c1 should be ω"
        assert "c2" in tree.omega_places, "c2 should be ω"


class TestBug5ReversibleSingleState:
    """Edge case: a net with only one reachable marking should be reversible."""

    def test_single_marking_reversible(self):
        net = PetriNet("single")
        net.add_place(Place("p", initial=1))
        # No transitions — only one marking reachable
        assert is_reversible(net)


class TestBug6EmptyMarkingTarget:
    """Edge case: fire_until with empty target should match immediately."""

    def test_empty_target(self):
        net = workflow_net()
        sim = Simulator(net, seed=0)
        seq = sim.fire_until({}, max_steps=10)
        # Empty target matches any marking, should return empty sequence
        assert seq == []