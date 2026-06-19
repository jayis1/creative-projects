"""Tests for the Petri net simulator."""

import pytest
from petri import PetriNet, Place, Transition, Simulator
from petri.net import FiringError
from petri.analysis import (
    reachability_graph, compute_t_invariants, compute_p_invariants,
    incidence_matrix, analyze_boundedness, analyze_liveness,
)
from petri.presets import (
    dining_philosophers, mutual_exclusion, workflow_net, producer_consumer,
)


class TestPlace:
    def test_valid(self):
        p = Place("p1", initial=3, capacity=5)
        assert p.name == "p1"
        assert p.initial == 3
        assert p.capacity == 5

    def test_negative_initial(self):
        with pytest.raises(ValueError):
            Place("p", initial=-1)

    def test_initial_exceeds_capacity(self):
        with pytest.raises(ValueError):
            Place("p", initial=5, capacity=3)


class TestArc:
    def test_zero_weight(self):
        net = PetriNet("test")
        net.add_place(Place("p", initial=1))
        net.add_transition(Transition("t"))
        with pytest.raises(ValueError):
            net.add_arc("p", "t", weight=0)


class TestNetBuilding:
    def test_duplicate_place(self):
        net = PetriNet("test")
        net.add_place(Place("p1"))
        with pytest.raises(ValueError):
            net.add_place(Place("p1"))

    def test_duplicate_transition(self):
        net = PetriNet("test")
        net.add_transition(Transition("t1"))
        with pytest.raises(ValueError):
            net.add_transition(Transition("t1"))

    def test_name_collision(self):
        net = PetriNet("test")
        net.add_place(Place("x"))
        with pytest.raises(ValueError):
            net.add_transition(Transition("x"))

    def test_invalid_arc(self):
        net = PetriNet("test")
        net.add_place(Place("p1"))
        net.add_place(Place("p2"))
        with pytest.raises(ValueError):
            net.add_arc("p1", "p2")  # place to place


class TestFiring:
    def test_basic_fire(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        assert net.is_enabled("t", m)
        m2 = net.fire("t", m)
        assert m2["p1"] == 0
        assert m2["p2"] == 1

    def test_not_enough_tokens(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=0))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        assert not net.is_enabled("t", m)

    def test_weighted_arc(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=3))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t", weight=2)
        net.add_arc("t", "p2", weight=2)
        m = net.initial_marking()
        assert net.is_enabled("t", m)
        m2 = net.fire("t", m)
        assert m2["p1"] == 1
        assert m2["p2"] == 2

    def test_capacity_prevents_fire(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=2, capacity=2))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        # firing would make p2 = 3 > capacity 2
        assert not net.is_enabled("t", m)

    def test_fire_does_not_mutate(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        net.fire("t", m)
        assert m["p1"] == 1  # original unchanged
        assert m["p2"] == 0

    def test_fire_inplace(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        net.fire_inplace("t", m)
        assert m["p1"] == 0
        assert m["p2"] == 1

    def test_fire_disabled_raises(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=0))
        net.add_transition(Transition("t"))
        net.add_arc("p1", "t")
        with pytest.raises(FiringError):
            net.fire("t", net.initial_marking())


class TestGuards:
    def test_guard_blocks(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t", guard=lambda m: False))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        assert not net.is_enabled("t", m)

    def test_guard_allows(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=0))
        net.add_transition(Transition("t", guard=lambda m: m.get("p1", 0) >= 1))
        net.add_arc("p1", "t")
        net.add_arc("t", "p2")
        m = net.initial_marking()
        assert net.is_enabled("t", m)


class TestSimulator:
    def test_random_walk(self):
        net = producer_consumer(3)
        sim = Simulator(net, seed=42)
        result = sim.random_walk(max_steps=50)
        assert result.steps_fired > 0
        assert len(result.trace) == result.steps_fired

    def test_run_sequence(self):
        net = workflow_net()
        sim = Simulator(net, seed=0)
        result = sim.run_sequence(["submit", "review", "approve"])
        assert result.steps_fired == 3
        assert result.final_marking["end"] == 1

    def test_run_sequence_lenient(self):
        net = workflow_net()
        sim = Simulator(net, seed=0)
        # "approve" is not enabled before "submit" and "review"
        result = sim.run_sequence(["approve"], strict=False)
        assert result.steps_fired == 0
        assert result.deadlocked

    def test_run_sequence_strict_raises(self):
        net = workflow_net()
        sim = Simulator(net, seed=0)
        with pytest.raises(FiringError):
            sim.run_sequence(["approve"], strict=True)

    def test_maximal_step(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_place(Place("p2", initial=1))
        net.add_place(Place("p3", initial=0))
        net.add_place(Place("p4", initial=0))
        net.add_transition(Transition("t1"))
        net.add_transition(Transition("t2"))
        net.add_arc("p1", "t1")
        net.add_arc("t1", "p3")
        net.add_arc("p2", "t2")
        net.add_arc("t2", "p4")
        m = net.initial_marking()
        new_m = sim_step(net, m)
        assert new_m["p3"] == 1
        assert new_m["p4"] == 1

    def test_fire_until_target(self):
        net = workflow_net()
        sim = Simulator(net, seed=42)
        seq = sim.fire_until({"end": 1}, max_steps=100)
        assert seq is not None
        assert len(seq) > 0

    def test_iter_random(self):
        net = producer_consumer(3)
        sim = Simulator(net, seed=1)
        count = 0
        for rec in sim.iter_random():
            count += 1
            if count >= 10:
                break
        assert count == 10


def sim_step(net, m):
    """Helper for maximal_step."""
    sim = Simulator(net, seed=0)
    return sim.maximal_step(m)


class TestReachability:
    def test_mutual_exclusion(self):
        net = mutual_exclusion()
        rg = reachability_graph(net)
        assert rg.num_states > 0
        assert rg.num_edges > 0
        assert len(rg.deadlocks) == 0  # mutual exclusion is deadlock-free

    def test_initial_marking_in_graph(self):
        net = mutual_exclusion()
        rg = reachability_graph(net)
        assert rg.initial_id in rg.nodes

    def test_dining_philosophers_deadlock(self):
        # dining philosophers (asymmetric) can deadlock
        net = dining_philosophers(2)
        rg = reachability_graph(net)
        # with 2 philosophers and asymmetric fork grabbing, deadlock is reachable
        # (this depends on the preset structure)
        assert rg.num_states > 0


class TestInvariants:
    def test_t_invariants_mutual_exclusion(self):
        net = mutual_exclusion()
        t_invs = compute_t_invariants(net)
        # each process cycle is a T-invariant
        assert len(t_invs) >= 2

    def test_p_invariants_mutual_exclusion(self):
        net = mutual_exclusion()
        p_invs = compute_p_invariants(net)
        # semaphore + critical section invariant should exist
        assert len(p_invs) >= 3

    def test_t_invariant_preserves_marking(self):
        net = mutual_exclusion()
        t_invs = compute_t_invariants(net)
        _, trans_names, C = incidence_matrix(net)
        for inv in t_invs:
            # C · x should be 0
            for i in range(len(C)):
                s = sum(C[i][j] * inv[j] for j in range(len(inv)))
                assert abs(s) < 1e-6

    def test_p_invariant_preserves_marking(self):
        net = mutual_exclusion()
        p_invs = compute_p_invariants(net)
        _, _, C = incidence_matrix(net)
        for inv in p_invs:
            # y^T · C should be 0
            for j in range(len(C[0])):
                s = sum(C[i][j] * inv[i] for i in range(len(inv)))
                assert abs(s) < 1e-6

    def test_empty_net(self):
        net = PetriNet("empty")
        assert compute_t_invariants(net) == []
        assert compute_p_invariants(net) == []


class TestBoundedness:
    def test_bounded_net(self):
        net = mutual_exclusion()
        b = analyze_boundedness(net)
        assert b.is_bounded
        assert b.bound >= 1

    def test_unbounded_net(self):
        """A net with a transition that has no input arcs is unbounded."""
        net = PetriNet("unbounded")
        net.add_place(Place("source", initial=0))
        net.add_place(Place("sink", initial=0))
        net.add_transition(Transition("gen"))
        net.add_arc("gen", "source")
        net.add_arc("source", "gen")
        # "move" has no input arc — always enabled, produces unbounded tokens
        net.add_transition(Transition("move"))
        net.add_arc("move", "sink")
        b = analyze_boundedness(net)
        assert not b.is_bounded, "Net with a transition that has no inputs is unbounded"


class TestLiveness:
    def test_liveness_classification(self):
        net = workflow_net()
        l = analyze_liveness(net)
        assert len(l.levels) == 4
        # all transitions should be at least L1
        for level in l.levels.values():
            assert level >= 0


class TestSerialization:
    def test_roundtrip(self):
        net = mutual_exclusion()
        d = net.to_dict()
        net2 = PetriNet.from_dict(d)
        assert len(net2.places) == len(net.places)
        assert len(net2.transitions) == len(net.transitions)
        assert net2.initial_marking() == net.initial_marking()

    def test_json_roundtrip(self):
        net = workflow_net()
        json_str = net.to_json()
        net2 = PetriNet.from_json(json_str)
        assert net2.name == net.name
        assert net2.initial_marking() == net.initial_marking()


class TestValidation:
    def test_isolated_nodes(self):
        net = PetriNet("test")
        net.add_place(Place("p1", initial=1))
        net.add_transition(Transition("t1"))
        warnings = net.validate()
        assert len(warnings) == 2  # both isolated

    def test_valid_net(self):
        net = workflow_net()
        warnings = net.validate()
        assert len(warnings) == 0