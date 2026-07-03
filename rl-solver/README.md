# rl-solver

A **Markov Decision Process (MDP) & Reinforcement Learning (RL) solver toolkit** implemented from scratch in pure Python (no dependencies beyond the standard library).

The toolkit provides both **model-based dynamic programming** planners (which use the full transition model) and **model-free tabular RL** algorithms (which learn from sampled experience). It includes 7 classic benchmark environments, ASCII visualization, configuration system, serialization, structured logging, a CLI, and analysis/comparison utilities.

## Features

### Model-Based Planning (Dynamic Programming)
- **Value Iteration** — Bellman-optimal backups with convergence tracking
- **Policy Iteration** (Howard's) — evaluate → improve loop with linear or iterative evaluation
- **Modified Policy Iteration** — k partial evaluation backups for faster convergence
- **Policy Evaluation** — exact linear-system solver (Gaussian elimination with partial pivoting) and iterative backup solver
- **Q-value computation** and **greedy policy extraction**

### Model-Free Reinforcement Learning (One-Step)
- **Q-Learning** — off-policy TD(0) control
- **SARSA** — on-policy TD(0) control
- **Expected SARSA** — expectation over next action under ε-greedy
- **Double Q-Learning** — two-table approach to reduce overestimation bias
- **Monte-Carlo Control** — first-visit & every-visit with epsilon-soft policies

### Multi-Step & Eligibility Trace Methods
- **n-step SARSA** — on-policy n-step temporal-difference learning (Sutton & Barto §7.2)
- **n-step Tree Backup** — off-policy n-step without importance sampling (§7.5)
- **SARSA(λ)** — accumulating eligibility traces (backward view, §12.7), with optional replacing traces
- **Watkins' Q(λ)** — Q-learning with eligibility traces, traces reset on non-greedy actions

### Environments (Presets)
| Preset | Description |
|--------|-------------|
| `russell_norvig` | Classic 4×4 gridworld (AIMA §17.1) with goal (+1), trap (−1), step cost |
| `cliff_walking` | Sutton & Barto cliff walking — cliff penalty −100, goal +1 |
| `frozen_lake` | Slippery grid with holes (slip probability 1/3) |
| `chain` | 1D chain MDP with two actions |
| `taxi` | Simplified 5×5 Taxi problem (4 stands, pickup/dropoff) |
| `bridge_walking` | 1×n bridge over a chasm — reach far end (+10) or jump off (−10) |
| `random` | Random MDP generator (configurable states/actions/terminals) |

### Visualization
- **Value heatmap** — ASCII bar-chart rendering of V(s) for grid MDPs
- **Policy grid** — arrow-based policy visualization (↑↓→←)
- **Q-table** — formatted tabular Q-value display
- **Learning curves** — ASCII plots of episode reward over time

### Analysis Tools
- **Policy simulation** — Monte-Carlo rollouts with return statistics (mean, std, min, max, success rate)
- **Planner comparison** — run all DP methods, compare iterations/time/return
- **Learner comparison** — train all RL algorithms, compare learned policies

### Configuration & Serialization
- **Config files** — JSON/TOML/YAML support for experiment definitions
- **Value function serialization** — save/load V to JSON
- **Policy serialization** — save/load policies to JSON
- **Structured logging** — configurable log levels

## Installation

```bash
cd rl-solver
pip install -e .
```

## Usage

### Python API

```python
from rl_solver import (
    make_russell_norvig_grid, value_iteration, policy_iteration,
    QLearner, SARSALambdaLearner, simulate_policy,
    render_value_heatmap, render_policy_grid,
)

# Solve with value iteration
mdp = make_russell_norvig_grid()
V, pi, info = value_iteration(mdp)
print(f"Optimal V(start) = {V[(0,0)]:.4f}")

# Visualize
print(render_value_heatmap(mdp, V))
print(render_policy_grid(mdp, pi))

# Learn with SARSA(λ)
learner = SARSALambdaLearner(mdp, lam=0.7, alpha=0.1, epsilon=0.2, seed=42)
learner.train(n_episodes=5000)
sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
print(f"Learned policy return: {sim['mean_return']:.3f}")
```

### CLI

```bash
# Solve with value iteration (with visualization)
rl-solver plan --preset russell_norvig --method value --show-values --show-policy

# Learn with Q-learning
rl-solver learn --preset russell_norvig --algo q --episodes 10000 --simulate --verbose

# Learn with SARSA(λ)
rl-solver learn --preset cliff_walking --algo sarsa_lambda --lam 0.7 --episodes 10000 --simulate

# Learn with n-step SARSA
rl-solver learn --preset frozen_lake --algo nstep_sarsa --n-step 5 --episodes 10000 --simulate

# Compare all planners
rl-solver compare --preset russell_norvig --mode planners

# Compare all learners
rl-solver compare --preset russell_norvig --mode learners --episodes 5000

# Show MDP info
rl-solver info --preset cliff_walking

# List presets
rl-solver list
```

## Architecture

```
rl-solver/
├── rl_solver/
│   ├── __init__.py        # Public API exports
│   ├── mdp.py             # MDP & GridWorld core data structures
│   ├── planners.py        # DP algorithms (VI, PI, MPI, policy eval)
│   ├── learners.py        # One-step RL (Q, SARSA, Expected SARSA, Double Q, MC)
│   ├── nstep.py           # n-step & TD(λ) methods (n-step SARSA, Tree Backup, SARSA(λ), Q(λ))
│   ├── environments.py    # 7 preset MDP factories
│   ├── analysis.py        # Simulation & comparison tools
│   ├── visualization.py   # ASCII visualization (heatmap, policy grid, Q-table, curves)
│   ├── config.py          # Config system (JSON/TOML/YAML) & serialization
│   ├── logging_utils.py   # Structured logging
│   └── cli.py             # argparse CLI (5 subcommands, 9 algorithms)
├── tests/                 # pytest test suite
├── smoke_test.py          # Quick verification script
├── pyproject.toml
└── README.md
```

## How It Works

### MDP Formalism

An MDP is defined by:
- **States** S — a discrete set of possible situations
- **Actions** A — a discrete set of choices
- **Transitions** P(s'|s,a) — probability of landing in s' after taking a in s
- **Rewards** R(s,a,s') — immediate reward for a transition
- **Discount** γ ∈ [0,1) — weighting of future vs immediate rewards

The **optimal value function** V*(s) = max_π E[Σ γ^t R_t | s₀=s, π] satisfies the Bellman optimality equation:

```
V*(s) = max_a Σ_s' P(s'|s,a) [R(s,a,s') + γ V*(s')]
```

### Value Iteration

Repeatedly applies the Bellman optimality backup to all states until the maximum change (delta) falls below a threshold θ. Converges in O(log(1/θ) / (1-γ)) iterations.

### Policy Iteration

Alternates between (1) evaluating the current policy exactly (solving V^π = R + γPV^π via Gaussian elimination) and (2) improving the policy by acting greedily w.r.t. V^π. Converges in a small number of iterations (often < 20).

### Q-Learning

Off-policy TD control. Updates Q(s,a) toward the target r + γ·max_a' Q(s',a'), using an ε-greedy behaviour policy for exploration. Converges to Q* under standard conditions (sufficient exploration, decaying learning rate).

### SARSA

On-policy TD control. Updates Q(s,a) toward r + γ·Q(s',a') where a' is the action *actually chosen* by the behaviour policy. Learns the value of the policy being followed, not the optimal policy.

### n-Step Methods

Bridge one-step TD and Monte-Carlo. The n-step return combines n immediate rewards with a bootstrap from Q(s_{t+n}, a_{t+n}):
```
G_t:n = Σ_{k=0}^{n-1} γ^k r_{t+k+1} + γ^n Q(s_{t+n}, a_{t+n})
```
Larger n → lower bias, higher variance. n=∞ reduces to Monte-Carlo.

### TD(λ) with Eligibility Traces

Instead of looking back n steps, eligibility traces decay geometrically by γλ, crediting all recently-visited state-action pairs:
```
δ = r + γ Q(s',a') - Q(s,a)
e(s,a) += 1    (accumulating) or e(s,a) = 1    (replacing)
Q(s,a) += α δ e(s,a)   for all s,a
e(s,a) *= γλ
```
λ=0 → one-step TD; λ=1 → Monte-Carlo.

## License

MIT

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been fixed:

1. **`simulate_policy` double-counted successes** — `success_rate` could exceed 1.0 (observed 200%) because terminal-state detection incremented `successes` both inside the step loop and again after the loop. **Fix**: use a single `reached_terminal` flag to count success at most once per episode.

2. **`make_taxi` premature terminal marking** — States where the passenger was `in_taxi` and the taxi was at the destination stand were incorrectly marked as terminal *before* the agent could perform the `dropoff` action, making the +20 dropoff reward unreachable. **Fix**: only the post-dropoff state (passenger at destination stand) is terminal; the in-taxi-at-destination state is non-terminal and the agent must explicitly drop off.

3. **`make_taxi` dropoff self-loop** — The `dropoff` transition used `st` (self-loop) as the next state instead of the post-dropoff state `(r, c, d, d)`, leaving the passenger in the taxi even after a "successful" dropoff. **Fix**: transition to `(r, c, d, d)` with reward +20, and mark that state as terminal.

4. **`make_bridge_walking` terminal mismatch** — The docstring said jumping off "resets to start" but the implementation sent the agent to off-bridge terminal states (`(-1,0)` / `(-2,0)`), ending the episode. **Fix**: jumping off now transitions back to `(0,0)` with reward −10; the episode continues. Only the far-right goal is terminal.