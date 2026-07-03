# rl-solver

A **Markov Decision Process (MDP) & Reinforcement Learning (RL) solver toolkit** implemented from scratch in pure Python (no dependencies beyond the standard library).

The toolkit provides both **model-based dynamic programming** planners (which use the full transition model) and **model-free tabular RL** algorithms (which learn from sampled experience). It includes 5 classic benchmark environments, a CLI, and analysis/ comparison utilities.

## Features

### Model-Based Planning (Dynamic Programming)
- **Value Iteration** — Bellman-optimal backups with convergence tracking
- **Policy Iteration** (Howard's) — evaluate → improve loop with linear or iterative evaluation
- **Modified Policy Iteration** — k partial evaluation backups for faster convergence
- **Policy Evaluation** — exact linear-system solver (Gaussian elimination) and iterative backup solver
- **Q-value computation** and **greedy policy extraction**

### Model-Free Reinforcement Learning
- **Q-Learning** — off-policy TD(0) control
- **SARSA** — on-policy TD(0) control
- **Expected SARSA** — expectation over next action under ε-greedy
- **Double Q-Learning** — two-table approach to reduce overestimation bias
- **Monte-Carlo Control** — first-visit & every-visit with epsilon-soft policies

### Environments (Presets)
| Preset | Description |
|--------|-------------|
| `russell_norvig` | Classic 4×4 gridworld (AIMA §17.1) with goal (+1), trap (−1), step cost |
| `cliff_walking` | Sutton & Barto cliff walking — cliff penalty −100, goal +1 |
| `frozen_lake` | Slippery grid with holes (slip probability 1/3) |
| `chain` | 1D chain MDP with two actions |
| `taxi` | Simplified 5×5 Taxi problem (4 stands, pickup/dropoff) |

### Analysis Tools
- **Policy simulation** — Monte-Carlo rollouts with return statistics
- **Planner comparison** — run all DP methods, compare iterations/time/return
- **Learner comparison** — train all RL algorithms, compare learned policies

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
    QLearner, simulate_policy,
)

# Solve with value iteration
mdp = make_russell_norvig_grid()
V, pi, info = value_iteration(mdp)
print(f"Optimal V(start) = {V[(0,0)]:.4f}")
print(f"Converged in {info['iterations']} iterations")

# Learn with Q-learning
learner = QLearner(mdp, alpha=0.1, epsilon=0.2, seed=42)
learner.train(n_episodes=5000)
learned_pi = learner.greedy_policy()
sim = simulate_policy(mdp, learned_pi, n_episodes=500, seed=42)
print(f"Learned policy return: {sim['mean_return']:.3f}")
```

### CLI

```bash
# Solve with value iteration
rl-solver plan --preset russell_norvig --method value --show-values --show-policy

# Learn with Q-learning
rl-solver learn --preset russell_norvig --algo q --episodes 10000 --simulate --verbose

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
│   ├── __init__.py       # Public API exports
│   ├── mdp.py            # MDP & GridWorld core data structures
│   ├── planners.py       # DP algorithms (VI, PI, MPI, policy eval)
│   ├── learners.py       # Model-free RL (Q, SARSA, Expected SARSA, Double Q, MC)
│   ├── environments.py   # Preset MDP factories
│   ├── analysis.py       # Simulation & comparison tools
│   └── cli.py            # argparse CLI (5 subcommands)
├── tests/                # pytest test suite
├── smoke_test.py         # Quick verification script
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

Alternates between (1) evaluating the current policy exactly (solving V^π = R + γPV^π) and (2) improving the policy by acting greedily w.r.t. V^π. Converges in a small number of iterations (often < 20).

### Q-Learning

Off-policy TD control. Updates Q(s,a) toward the target r + γ·max_a' Q(s',a'), using an ε-greedy behaviour policy for exploration. Converges to Q* under standard conditions (sufficient exploration, decaying learning rate).

### SARSA

On-policy TD control. Updates Q(s,a) toward r + γ·Q(s',a') where a' is the action *actually chosen* by the behaviour policy. Learns the value of the policy being followed, not the optimal policy.

## License

MIT