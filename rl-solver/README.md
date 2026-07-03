# rl-solver

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests: 79](https://img.shields.io/badge/tests-79%20passed-brightgreen.svg)
![Pure stdlib](https://img.shields.io/badge/pure-stdlib-orange.svg)

A comprehensive **Markov Decision Process (MDP) & Reinforcement Learning (RL)** solver toolkit implemented from scratch in pure Python — no external dependencies beyond the standard library.

The toolkit provides both **model-based dynamic programming** planners (which use the full transition model) and **model-free tabular RL** algorithms (which learn from sampled experience). It includes 12 benchmark environments, ASCII visualization, a configuration system, serialization, structured logging, a CLI with 7 subcommands, 13 algorithms, 79 tests, and analysis/comparison utilities.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Config Files](#config-files)
- [Environments](#environments)
- [Algorithms](#algorithms)
  - [Model-Based Planning (Dynamic Programming)](#model-based-planning-dynamic-programming)
  - [Model-Free Reinforcement Learning](#model-free-reinforcement-learning)
  - [Advanced Methods](#advanced-methods)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [License](#license)
- [Known Issues (Resolved)](#known-issues-resolved)

---

## Features

### Model-Based Planning (Dynamic Programming)
- **Value Iteration** — Bellman-optimal backups with convergence tracking
- **Policy Iteration** (Howard's) — evaluate → improve loop with linear or iterative evaluation
- **Modified Policy Iteration** — k partial evaluation backups for faster convergence
- **Policy Evaluation** — exact linear-system solver (Gaussian elimination with partial pivoting) and iterative backup solver
- **Linear Programming** — optimal value via a pure-Python Simplex solver with Big-M method
- **Gauss-Seidel Value Iteration** — asynchronous in-place sweeps (often fewer iterations)
- **Prioritized Sweeping** — priority-queue-driven asynchronous backups
- **Real-Time Dynamic Programming (RTDP)** — trial-based asynchronous VI
- **Q-value computation** and **greedy policy extraction**

### Model-Free Reinforcement Learning
- **Q-Learning** — off-policy TD(0) control
- **SARSA** — on-policy TD(0) control
- **Expected SARSA** — expectation over next action under ε-greedy
- **Double Q-Learning** — two-table approach to reduce overestimation bias
- **Monte-Carlo Control** — first-visit & every-visit with epsilon-soft policies
- **n-step SARSA** — on-policy n-step temporal-difference learning (Sutton & Barto §7.2)
- **n-step Tree Backup** — off-policy n-step without importance sampling (§7.5)
- **SARSA(λ)** — accumulating eligibility traces (backward view, §12.7), with optional replacing traces
- **Watkins' Q(λ)** — Q-learning with eligibility traces, traces reset on non-greedy actions

### Advanced Methods
- **Dyna-Q** — model-based Q-learning with simulated planning steps (§8.2)
- **R-Max** — optimistic-initialization model-based algorithm ("knows what it knows")
- **Boltzmann Q-Learning** — softmax temperature-controlled exploration
- **Gradient Q-Learning** — semi-gradient Q-learning with linear function approximation and tile coding

### Environments (12 Presets)
| Preset | Description |
|--------|-------------|
| `russell_norvig` | Classic 4×4 gridworld (AIMA §17.1) with goal (+1), trap (−1), step cost |
| `cliff_walking` | Sutton & Barto cliff walking — cliff penalty −100, goal +1 |
| `frozen_lake` | Slippery grid with holes (slip probability 1/3) |
| `chain` | 1D chain MDP with two actions |
| `taxi` | Simplified 5×5 Taxi problem (4 stands, pickup/dropoff) |
| `bridge_walking` | 1×n bridge over a chasm — reach far end (+10) or jump off (−10) |
| `random` | Random MDP generator (configurable states/actions/terminals) |
| `maze` | Gridworld with interior walls/obstacles |
| `windy` | Windy Gridworld (Sutton & Barto §6.5) with column-based wind |
| `blackjack` | Simplified, fully-observable Blackjack MDP |
| `dice` | One-state "Alice's dice" toy MDP with risk/reward tradeoffs |
| `pendulum` | Discretised pendulum swing-up (continuous control made tabular) |

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

---

## Installation

```bash
cd rl-solver
pip install -e .
```

Or without installation (add to path):
```bash
export PYTHONPATH=/path/to/rl-solver:$PYTHONPATH
```

**Requirements:** Python 3.10+ (uses `tomllib` from stdlib in 3.11+, falls back to `tomli`)

---

## Quick Start

```python
from rl_solver import make_russell_norvig_grid, value_iteration, render_value_heatmap

# Solve a 4×4 gridworld
mdp = make_russell_norvig_grid()
V, pi, info = value_iteration(mdp)
print(f"Optimal V(start) = {V[(0,0)]:.4f}  ({info['iterations']} iterations)")
print(render_value_heatmap(mdp, V))
```

```
Optimal V(start) = 0.7550  (7 iterations)
0.755███░ 0.803███░ 0.851███░ 0.900███░
0.803███░ 0.851███░ 0.900███░ 0.950███░
0.851███░ 0.900███░ 0.950███░ 1.000████
0.000█░░░ 0.950███░ 1.000████ 0.000█░░░
```

---

## Usage

### Python API

```python
from rl_solver import (
    make_russell_norvig_grid, value_iteration, policy_iteration,
    linear_programming_solve, rtdp,
    QLearner, SARSALambdaLearner, DynaQLearner, RMaxLearner,
    simulate_policy, render_value_heatmap, render_policy_grid,
)

# 1. Solve with DP — compare all planners
mdp = make_russell_norvig_grid()
V_vi, pi_vi, info_vi = value_iteration(mdp)
V_lp, pi_lp, info_lp = linear_programming_solve(mdp)
V_rtdp, pi_rtdp, info_rtdp = rtdp(mdp, n_trials=2000, seed=42)

# 2. Learn with RL — compare algorithms
learner = SARSALambdaLearner(mdp, lam=0.7, alpha=0.1, epsilon=0.2, seed=42)
learner.train(n_episodes=5000)
sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
print(f"Learned policy return: {sim['mean_return']:.3f}, success: {sim['success_rate']:.1%}")

# 3. Model-based RL with Dyna-Q
dyna = DynaQLearner(mdp, alpha=0.5, epsilon=0.1, n_planning=20, seed=42)
dyna.train(n_episodes=2000)
sim_dyna = simulate_policy(mdp, dyna.greedy_policy(), n_episodes=500, seed=42)
print(f"Dyna-Q return: {sim_dyna['mean_return']:.3f}")
```

### CLI

```bash
# Solve with value iteration (with visualization)
rl-solver plan --preset russell_norvig --method value --show-values --show-policy

# Solve with linear programming
rl-solver plan --preset cliff_walking --method lp --show-values

# Solve with RTDP
rl-solver plan --preset maze --method rtdp --trials 5000 --show-policy

# Learn with Q-learning
rl-solver learn --preset russell_norvig --algo q --episodes 10000 --simulate --verbose

# Learn with Dyna-Q (model-based RL)
rl-solver learn --preset cliff_walking --algo dyna_q --n-planning 20 --episodes 5000 --simulate

# Learn with R-Max
rl-solver learn --preset maze --algo rmax --r-max 1.0 --threshold 5 --episodes 5000 --simulate

# Learn with SARSA(λ)
rl-solver learn --preset cliff_walking --algo sarsa_lambda --lam 0.7 --episodes 10000 --simulate

# Learn with n-step SARSA
rl-solver learn --preset frozen_lake --algo nstep_sarsa --n-step 5 --episodes 10000 --simulate

# Learn with Boltzmann Q-learning
rl-solver learn --preset russell_norvig --algo boltzmann_q --temperature 0.5 --episodes 10000 --simulate

# Compare all planners
rl-solver compare --preset russell_norvig --mode planners

# Compare all learners
rl-solver compare --preset russell_norvig --mode learners --episodes 5000

# Show MDP info
rl-solver info --preset blackjack --json

# List all presets
rl-solver list

# Run from config file
rl-solver config experiment.json
```

### Config Files

```json
{
  "env": {"preset": "russell_norvig", "gamma": 0.99},
  "planner": {"method": "value_iteration", "theta": 1e-8},
  "learner": {
    "algo": "q", "alpha": 0.1, "epsilon": 0.1,
    "epsilon_decay": 0.999, "epsilon_min": 0.01,
    "episodes": 5000, "max_steps": 1000
  },
  "simulation": {"episodes": 500, "seed": 42}
}
```

---

## Environments

### Core Environments (7)
| Preset | States | Actions | Description |
|--------|--------|---------|-------------|
| `russell_norvig` | 16 | 4 | 4×4 gridworld, goal +1, trap −1, step cost −0.04 |
| `cliff_walking` | 48 | 4 | 12×4 grid, cliff penalty −100, goal +1 |
| `frozen_lake` | 16 | 4 | 4×4 slippery grid with holes |
| `chain` | 5 | 2 | 1D chain, reach end for +1 |
| `taxi` | 700 | 6 | 5×5 grid, 4 stands, pickup/dropoff, +20/-10/-1 |
| `bridge_walking` | 10 | 4 | 1×10 bridge, +10 goal, −10 jump |
| `random` | varies | varies | Random MDP generator |

### Extended Environments (5)
| Preset | States | Actions | Description |
|--------|--------|---------|-------------|
| `maze` | varies | 4 | Gridworld with interior walls |
| `windy` | 70 | 4/8 | Windy Gridworld (S&B §6.5), column-based wind |
| `blackjack` | 203 | 2 | Simplified Blackjack, hit/stand |
| `dice` | 2 | 3 | One-state risk/reward toy MDP |
| `pendulum` | 192 | 3 | Discretised pendulum swing-up |

---

## Algorithms

### Model-Based Planning (Dynamic Programming)

| Algorithm | Method | Complexity | Notes |
|-----------|--------|------------|-------|
| Value Iteration | Synchronous Bellman backup | O(\|S\|²\|A\|) per iter | Guaranteed convergence |
| Policy Iteration | Evaluate + Improve | O(\|S\|³) per eval | Few iterations, exact eval |
| Modified PI | k partial evals + Improve | O(k\|S\|²\|A\|) | Tradeoff vs PI/VI |
| Linear Programming | Simplex on Bellman constraints | O(\|S\|³\|A\|) | Exact optimal |
| Gauss-Seidel VI | In-place async backup | O(\|S\|²\|A\|) per sweep | Fewer sweeps |
| Prioritized Sweeping | Priority-queue backups | varies | Focuses on high-error states |
| RTDP | Trial-based async VI | varies | Efficient for sparse MDPs |

### Model-Free Reinforcement Learning

| Algorithm | Type | On/Off Policy | Key Feature |
|-----------|------|---------------|-------------|
| Q-Learning | TD(0) | Off-policy | max bootstrap |
| SARSA | TD(0) | On-policy | Uses actual next action |
| Expected SARSA | TD(0) | Off-policy | Expected next Q |
| Double Q-Learning | TD(0) | Off-policy | Reduces overestimation |
| Monte-Carlo | MC | On-policy | Full episode returns |
| n-step SARSA | n-step TD | On-policy | Bias-variance tradeoff |
| n-step Tree Backup | n-step TD | Off-policy | No importance sampling |
| SARSA(λ) | TD(λ) | On-policy | Eligibility traces |
| Watkins' Q(λ) | TD(λ) | Off-policy | Traces reset on non-greedy |

### Advanced Methods

| Algorithm | Type | Key Feature |
|-----------|------|-------------|
| Dyna-Q | Model-based RL | Planning via learned model |
| R-Max | Model-based RL | Optimistic init, "knows what it knows" |
| Boltzmann Q | TD(0) | Softmax exploration |
| Gradient Q | Function approximation | Tile coding, linear FA |

---

## Architecture

```
rl-solver/
├── rl_solver/
│   ├── __init__.py            # Public API exports (v3.0)
│   ├── mdp.py                 # MDP & GridWorld core data structures
│   ├── planners.py            # Core DP (VI, PI, MPI, policy eval)
│   ├── advanced_planners.py   # LP, Gauss-Seidel, Prioritized Sweeping, RTDP
│   ├── learners.py            # One-step RL (Q, SARSA, Double Q, MC)
│   ├── nstep.py               # n-step & TD(λ) methods
│   ├── advanced_learners.py    # Dyna-Q, R-Max, Boltzmann, Gradient Q
│   ├── environments.py        # 7 core preset MDP factories
│   ├── extra_environments.py  # 5 additional environments
│   ├── analysis.py            # Simulation & comparison tools
│   ├── visualization.py      # ASCII visualization (heatmap, policy, Q, curves)
│   ├── config.py             # Config system (JSON/TOML/YAML) & serialization
│   ├── logging_utils.py      # Structured logging
│   └── cli.py                # argparse CLI (7 subcommands, 13 algorithms)
├── tests/
│   ├── test_bug_hunt.py       # 8 original bug regression tests
│   └── test_comprehensive.py  # 71 comprehensive tests
├── examples/
│   ├── 01_compare_planners.py # Compare all 7 DP planners
│   ├── 02_compare_learners.py # Compare all 9 RL learners
│   ├── 03_blackjack_strategy.py # Blackjack optimal strategy table
│   ├── 04_windy_gridworld.py  # Windy gridworld (standard vs king moves)
│   └── 05_maze_dyna_q.py     # Maze solving with Dyna-Q
├── .github/workflows/ci.yml  # GitHub Actions CI
├── smoke_test.py              # Quick verification script
├── pyproject.toml             # Installable package config
├── CONTRIBUTING.md            # Contribution guidelines
├── LICENSE                    # MIT License
└── README.md                  # This file
```

---

## How It Works

### MDP Formalism

An MDP is defined by:
- **States** S — a discrete set of possible situations
- **Actions** A — a discrete set of choices
- **Transitions** P(s'|s,a) — probability of landing in s' after taking a in s
- **Rewards** R(s,a,s') — immediate reward for a transition
- **Discount** γ ∈ [0,1] — weighting of future vs immediate rewards

The **optimal value function** V*(s) = max_π E[Σ γ^t R_t | s₀=s, π] satisfies the Bellman optimality equation:

```
V*(s) = max_a Σ_s' P(s'|s,a) [R(s,a,s') + γ V*(s')]
```

### Value Iteration

Repeatedly applies the Bellman optimality backup to all states until the maximum change (delta) falls below a threshold θ. Converges in O(log(1/θ) / (1-γ)) iterations.

### Policy Iteration

Alternates between (1) evaluating the current policy exactly (solving V^π = R + γPV^π via Gaussian elimination) and (2) improving the policy by acting greedily w.r.t. V^π. Converges in a small number of iterations (often < 20).

### Linear Programming

Formulates the MDP as a linear program: minimise Σ V(s) subject to V(s) ≥ Q(s,a) for all (s,a). Solved via a pure-Python Simplex method with Big-M artificial variables for handling negative right-hand sides.

### Gauss-Seidel Value Iteration

Updates each state's value *in place*, so later states in the same sweep already see updated values of earlier states. Typically converges in fewer sweeps than synchronous value iteration.

### Prioritized Sweeping

Maintains a priority queue of states whose Bellman error exceeds a threshold, processing the highest-priority state first. Uses a predecessor map so that updating one state enqueues all states whose transitions depend on it.

### RTDP

Runs repeated simulated trials from the start state. At each visited state the agent takes the greedy action w.r.t. current V and performs a Bellman backup in place. Only states visited during trials are updated, making RTDP efficient for large MDPs with sparse relevant regions.

### Dyna-Q

After each real environment step, performs `n_planning` additional Q updates using *simulated* experience drawn from a learned tabular model. The model maps (s,a) → observed outcomes, enabling faster convergence than pure model-free Q-learning.

### R-Max

Assumes that any (s,a) pair visited fewer than `threshold` times yields the maximum possible reward `r_max`. Once a pair has been sampled enough, it switches to model-based planning on the known model. Provides the "knows what it knows" property.

### Boltzmann Exploration

Instead of ε-greedy, samples actions from a softmax distribution: `π(a|s) ∝ exp(Q(s,a)/T)`. As temperature T → 0 the policy becomes greedy; as T → ∞ it becomes uniform. Uses the log-sum-exp trick for numerical stability.

### Tile Coding & Gradient Q-Learning

Tile coding maps continuous states to sparse binary features via multiple offset tilings. The gradient Q-learner maintains a weight vector w such that Q(s,a) ≈ w · φ(s,a), updating w via semi-gradient TD:

```
δ = r + γ max_a' Q(s',a') - Q(s,a)
w += α δ φ(s,a)
```

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

---

## Examples

See the `examples/` directory for runnable demos:

```bash
# Compare all 7 DP planners on the Russell-Norvig gridworld
python examples/01_compare_planners.py

# Compare all 9 RL learners on Cliff Walking
python examples/02_compare_learners.py

# Print the optimal Blackjack strategy table
python examples/03_blackjack_strategy.py

# Windy Gridworld: standard vs king moves
python examples/04_windy_gridworld.py

# Maze solving with Dyna-Q
python examples/05_maze_dyna_q.py
```

### Sample Output: Planner Comparison

```
Solving the Russell-Norvig 4×4 Gridworld
======================================================================
States: 16, Actions: 4, Gamma: 0.99

  Value Iteration           iters=    7  time=    0.27ms  V(start)=0.754950  diff=0.00e+00
  Policy Iteration          iters=    5  time=   54.34ms  V(start)=0.754950  diff=0.00e+00
  Modified PI               iters=    1  time=    0.39ms  V(start)=0.754950  diff=0.00e+00
  LP Solver                 iters=   58  time=   22.52ms  V(start)=0.754950  diff=6.87e-14
  Gauss-Seidel VI           iters=    7  time=    0.26ms  V(start)=0.754950  diff=0.00e+00
  Prioritized Sweeping      iters=   19  time=    1.03ms  V(start)=0.754950  diff=0.00e+00
  RTDP                      iters=   10  time=    0.40ms  V(start)=0.754950  diff=9.90e-01
```

### Sample Output: Optimal Policy Grid

```
  ↓    ↓    ↓    ↓
  ↓    ↓    ↓    ↓
  →    ↓    ↓    ↓
  ·    →    →    ·
```

---

## Testing

```bash
# Run all 79 tests
python -m pytest tests/ -v

# Run specific test classes
python -m pytest tests/test_comprehensive.py::TestPlanners -v
python -m pytest tests/test_comprehensive.py::TestLearners -v
python -m pytest tests/test_comprehensive.py::TestEnvironments -v

# Run the smoke test
python smoke_test.py
```

Test coverage:
- **TestMDPCore** (10 tests) — validation, transitions, serialization, GridWorld
- **TestPlanners** (13 tests) — all 7 DP planners, convergence, agreement
- **TestLearners** (14 tests) — all 12 RL learners, improvement, edge cases
- **TestGradientQLearner** (2 tests) — tile coding, function approximation
- **TestEnvironments** (15 tests) — all 12 presets, validity, solvability
- **TestAnalysis** (4 tests) — simulation, comparison tools
- **TestVisualization** (5 tests) — all rendering functions
- **TestConfig** (3 tests) — serialization, config validation
- **TestBugRegressions** (6 tests) — verification of all fixed bugs

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and guidelines for adding new algorithms, environments, or features.

---

## Changelog

### v3.0.0 (2026-07-03) — Comprehensive Improvement

**New Planners (4):**
- Linear Programming solver (pure-Python Simplex with Big-M method)
- Gauss-Seidel (asynchronous in-place) value iteration
- Prioritized Sweeping (priority-queue-driven asynchronous backups)
- Real-Time Dynamic Programming (RTDP, trial-based async VI)

**New Learners (4):**
- Dyna-Q (model-based Q-learning with simulated planning)
- R-Max (optimistic initialization, "knows what it knows")
- Boltzmann Q-Learning (softmax exploration with temperature decay)
- Gradient Q-Learning (semi-gradient TD with tile coding, linear FA)

**New Environments (5):**
- Maze (gridworld with interior walls)
- Windy Gridworld (S&B §6.5, standard + king moves)
- Blackjack (simplified, fully-observable)
- Dice Game (one-state risk/reward toy MDP)
- Pendulum (discretised pendulum swing-up)

**Improvements:**
- CLI expanded to 7 subcommands with 13 algorithms
- Config file subcommand (`rl-solver config experiment.json`)
- `gamma=1.0` now supported (episodic tasks)
- NaN guard in ε-greedy action selection
- DoubleQLearner.greedy_policy crash fix
- 71 new comprehensive tests (79 total)
- 5 example scripts
- GitHub Actions CI (Python 3.10–3.13)
- CONTRIBUTING.md, LICENSE (MIT)
- Dramatically improved README with badges, ToC, architecture, roadmap

### v2.0.0 — Enhanced

- n-step SARSA, n-step Tree Backup, SARSA(λ), Watkins' Q(λ)
- ASCII visualization (value heatmap, policy grid, Q-table, learning curves)
- Config system (JSON/TOML/YAML), value/policy serialization
- Structured logging, 2 new environments (bridge walking, random MDP)
- Expanded CLI to 9 algorithms

### v1.0.0 — Initial

- Model-based DP (VI, PI, MPI, linear-system policy evaluation)
- Model-free RL (Q-learning, SARSA, Expected SARSA, Double Q, MC)
- 5 preset environments
- Policy simulation, planner/learner comparison
- CLI

---

## Roadmap

- **Function approximation**: DQN-style neural network Q-learner (pure Python)
- **Policy gradient methods**: REINFORCE, Actor-Critic, PPO (tabular)
- **More environments**: GridWorld with lava, multi-agent gridworld, CartPole (discretised)
- **Visualization**: SVG/HTML output for value functions and policies
- **Benchmarking**: Automated hyperparameter sweeps, learning curve export to CSV
- **Partial observability**: POMDP support with belief-state methods
- **Multi-objective RL**: Pareto-optimal policy learning

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been fixed:

1. **`simulate_policy` double-counted successes** — `success_rate` could exceed 1.0 (observed 200%) because terminal-state detection incremented `successes` both inside the step loop and again after the loop. **Fix**: use a single `reached_terminal` flag to count success at most once per episode.

2. **`make_taxi` premature terminal marking** — States where the passenger was `in_taxi` and the taxi was at the destination stand were incorrectly marked as terminal *before* the agent could perform the `dropoff` action, making the +20 dropoff reward unreachable. **Fix**: only the post-dropoff state (passenger at destination stand) is terminal; the in-taxi-at-destination state is non-terminal and the agent must explicitly drop off.

3. **`make_taxi` dropoff self-loop** — The `dropoff` transition used `st` (self-loop) as the next state instead of the post-dropoff state `(r, c, d, d)`, leaving the passenger in the taxi even after a "successful" dropoff. **Fix**: transition to `(r, c, d, d)` with reward +20, and mark that state as terminal.

4. **`make_bridge_walking` terminal mismatch** — The docstring said jumping off "resets to start" but the implementation sent the agent to off-bridge terminal states (`(-1,0)` / `(-2,0)`), ending the episode. **Fix**: jumping off now transitions back to `(0,0)` with reward −10; the episode continues. Only the far-right goal is terminal.

### v3.0 Bug Fixes

5. **`DoubleQLearner.greedy_policy` crash on empty dict** — `max(combined.get(s, {}), key=...)` raised `ValueError` when the Q-table was empty. **Fix**: fallback to first available action.

6. **`_eps_greedy_action` crash on NaN** — If Q-values contained NaN (from numerical instability), `best_actions` would remain empty, causing `IndexError`. **Fix**: NaN guard converts NaN to 0.0, plus a fallback to uniform random.

7. **`build-backend` typo in pyproject.toml** — `setuptools.backends._legacy:_Backend` is not a valid build backend. **Fix**: changed to `setuptools.build_meta`.