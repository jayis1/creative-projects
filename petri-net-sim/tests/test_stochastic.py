"""Tests for stochastic Petri nets: CTMC, steady-state, Monte Carlo."""

import pytest
from petri import PetriNet, Place, Transition
from petri.stochastic import (
    StochasticPetriNet, build_ctmc, steady_state_probabilities,
    monte_carlo, expected_time_to_target,
)
from petri.presets import mutual_exclusion, workflow_net


class TestStochasticPetriNet:
    def test_set_get_rate(self):
        net = workflow_net()
        spn = StochasticPetriNet(net)
        spn.set_rate("submit", 2.0)
        assert spn.get_rate("submit") == 2.0
        assert spn.get_rate("review") == 1.0  # default

    def test_invalid_rate(self):
        net = workflow_net()
        spn = StochasticPetriNet(net)
        with pytest.raises(ValueError):
            spn.set_rate("submit", 0.0)
        with pytest.raises(ValueError):
            spn.set_rate("submit", -1.0)

    def test_unknown_transition(self):
        net = workflow_net()
        spn = StochasticPetriNet(net)
        with pytest.raises(KeyError):
            spn.set_rate("nonexistent", 1.0)

    def test_all_rates(self):
        net = workflow_net()
        spn = StochasticPetriNet(net)
        spn.set_rate("submit", 3.0)
        rates = spn.all_rates()
        assert rates["submit"] == 3.0
        assert rates["review"] == 1.0


class TestCTMC:
    def test_build_ctmc_states(self):
        net = workflow_net()
        spn = StochasticPetriNet(net)
        spn.set_rate("submit", 2.0)
        ctmc = build_ctmc(spn)
        assert ctmc.num_states > 0
        assert ctmc.initial_id != ""

    def test_generator_matrix(self):
        net = mutual_exclusion()
        spn = StochasticPetriNet(net)
        ctmc = build_ctmc(spn)
        n = ctmc.num_states
        assert len(ctmc.generator) == n
        # Diagonal should be negative (or zero for absorbing)
        for i in range(n):
            assert ctmc.generator[i][i] <= 0

    def test_steady_state_sums_to_one(self):
        net = mutual_exclusion()
        spn = StochasticPetriNet(net)
        ctmc = build_ctmc(spn)
        probs = steady_state_probabilities(ctmc)
        total = sum(probs.values())
        assert abs(total - 1.0) < 1e-6, f"Steady state probs sum to {total}, expected 1.0"

    def test_steady_state_nonneg(self):
        net = workflow_net()
        spn = StochasticPetriNet(net)
        ctmc = build_ctmc(spn)
        probs = steady_state_probabilities(ctmc)
        for sid, prob in probs.items():
            assert prob >= 0, f"Negative probability for {sid}"


class TestMonteCarlo:
    def test_deadlock_free_net(self):
        net = mutual_exclusion()
        result = monte_carlo(net, num_runs=100, max_steps=50, seed=42)
        assert result.num_runs == 100
        assert 0 <= result.deadlock_probability <= 1.0

    def test_marking_distribution(self):
        net = workflow_net()
        result = monte_carlo(net, num_runs=50, max_steps=20, seed=42)
        # Should have some marking distribution
        assert len(result.marking_distribution) > 0

    def test_reproducible(self):
        net = mutual_exclusion()
        r1 = monte_carlo(net, num_runs=50, max_steps=30, seed=42)
        r2 = monte_carlo(net, num_runs=50, max_steps=30, seed=42)
        assert r1.deadlock_count == r2.deadlock_count


class TestExpectedTime:
    def test_immediate_target(self):
        """If initial marking already matches target, expected time = 0."""
        net = PetriNet("immediate")
        net.add_place(Place("p", initial=1))
        net.add_transition(Transition("t"))
        spn = StochasticPetriNet(net)
        result = expected_time_to_target(spn, {"p": 1})
        assert result.expected_time == 0.0
        assert result.found_target

    def test_unreachable_target(self):
        """Unreachable target should return inf."""
        net = PetriNet("unreachable")
        net.add_place(Place("start", initial=1))
        net.add_place(Place("end", initial=0))
        net.add_transition(Transition("go"))
        net.add_arc("start", "go")
        net.add_arc("go", "end")
        spn = StochasticPetriNet(net)
        # "start" is consumed when "go" fires, so {start: 2} is unreachable
        result = expected_time_to_target(spn, {"start": 2})
        assert not result.found_target