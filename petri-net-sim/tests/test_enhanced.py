"""Tests for enhanced analysis features."""

import pytest
from petri import (
    PetriNet, Place, Transition,
    is_reachable, is_reversible,
    coverability_tree, analyze_traps_siphons,
    find_traps, find_siphons,
)
from petri.presets import mutual_exclusion, workflow_net, producer_consumer


class TestReachability:
    def test_reachable_marking(self):
        net = workflow_net()
        # "end" should be reachable after submit -> review -> approve
        assert is_reachable(net, {"end": 1})

    def test_unreachable_marking(self):
        net = workflow_net()
        # Can't have 2 tokens in "start" (only 1 exists and net is safe)
        assert not is_reachable(net, {"start": 2})

    def test_partial_marking(self):
        net = mutual_exclusion()
        # Both in critical section simultaneously is impossible (mutual exclusion)
        assert not is_reachable(net, {"p1_cs": 1, "p2_cs": 1})


class TestReversibility:
    def test_reversible_net(self):
        net = mutual_exclusion()
        # Mutual exclusion is reversible (can always return to initial marking)
        assert is_reversible(net)

    def test_non_reversible_net(self):
        net = PetriNet("non_reversible")
        net.add_place(Place("start", initial=1))
        net.add_place(Place("end", initial=0))
        net.add_transition(Transition("go"))
        net.add_arc("start", "go")
        net.add_arc("go", "end")
        # Once we reach "end", we can't go back
        assert not is_reversible(net)


class TestCoverability:
    def test_bounded_net(self):
        net = mutual_exclusion()
        tree = coverability_tree(net)
        assert not tree.is_unbounded
        assert len(tree.nodes) > 0

    def test_unbounded_net(self):
        net = PetriNet("unbounded")
        net.add_place(Place("p", initial=1))
        net.add_place(Place("counter", initial=0))
        net.add_transition(Transition("inc"))
        net.add_arc("p", "inc")
        net.add_arc("inc", "p")
        net.add_arc("inc", "counter")
        tree = coverability_tree(net)
        assert tree.is_unbounded
        assert "counter" in tree.omega_places


class TestTrapsSiphons:
    def test_mutual_exclusion_traps(self):
        net = mutual_exclusion()
        traps = find_traps(net)
        assert len(traps) > 0
        # Each trap should be a valid trap
        for trap in traps:
            assert len(trap) > 0

    def test_mutual_exclusion_siphons(self):
        net = mutual_exclusion()
        siphons = find_siphons(net)
        assert len(siphons) > 0

    def test_traps_siphons_analysis(self):
        net = mutual_exclusion()
        result = analyze_traps_siphons(net)
        assert len(result.traps) > 0
        assert len(result.siphons) > 0
        # mutual exclusion has marked traps
        assert result.has_marked_trap

    def test_empty_net(self):
        net = PetriNet("empty")
        assert find_traps(net) == []
        assert find_siphons(net) == []
        result = analyze_traps_siphons(net)
        assert len(result.traps) == 0
        assert len(result.siphons) == 0
        assert not result.has_marked_trap
        assert not result.has_unmarked_siphon

    def test_trap_property(self):
        """A trap that's initially marked stays marked."""
        net = PetriNet("trap_test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        net.add_arc("p2", "t")  # p2 feeds back to t
        net.add_arc("t", "p1")
        traps = find_traps(net)
        assert len(traps) > 0
        # {p1} and {p2} are both traps (t produces back to each)
        assert {"p1"} in traps
        assert {"p2"} in traps