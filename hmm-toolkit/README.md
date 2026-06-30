# hmm-toolkit

A Hidden Markov Model (HMM) toolkit implemented **from scratch** in pure Python — no third-party dependencies.

## Features

### Core Algorithms
- **Forward algorithm** (scaled) — computes P(observations | model) with numerical stability
- **Backward algorithm** (scaled) — companion backward probabilities
- **Viterbi algorithm** (log-space) — most likely hidden state path
- **Baum-Welch** — EM parameter estimation / training (single sequence)
- **Multi-sequence Baum-Welch** — train on multiple i.i.d. observation sequences
- **Posterior decoding** — forward-backward marginal decoding

### Analysis Utilities
- **Sequence classification** — classify observations by selecting the best-matching model
- **State entropy** — per-timestep Shannon entropy of the state posterior
- **Symmetric KL divergence** — compare two HMMs via log-likelihood ratio
- **State durations** — segment a state path into consecutive runs
- **Expected dwell time** — theoretical mean residence time per state (1/(1-A[i][i]))

### Other
- **Sequence generation** — sample state + observation sequences from a model
- **JSON serialization** — save/load models and observation sequences
- **CLI** — 9 subcommands (generate, viterbi, forward, train, posterior, random, info, classify, entropy)
- Pure Python (stdlib only), Python ≥ 3.8

## Quick Start

```python
from hmm import HMM, forward, viterbi, baum_welch, generate_sequence

# Dishonest Casino: fair die (F) and loaded die (L)
states = ["F", "L"]
symbols = ["1", "2", "3", "4", "5", "6"]
A = [[0.95, 0.05], [0.10, 0.90]]
B = [[1/6]*6, [0.10, 0.10, 0.10, 0.10, 0.10, 0.50]]
pi = [0.5, 0.5]

model = HMM(states, symbols, A, B, pi)

# Generate a sample
true_states, obs = generate_sequence(model, length=300, seed=42)

# Viterbi decode
obs_idx = model.observation_sequence(obs)
path, logp = viterbi(model, obs_idx)

# Train a fresh random model
fresh = HMM.random(states, symbols, seed=0)
final_ll, iters = baum_welch(fresh, obs_idx, iterations=200)
```

### Multi-sequence training

```python
from hmm import baum_welch_multi

# Train on multiple observation sequences
obs_list = [model.observation_sequence(generate_sequence(model, 50, seed=i)[1]) for i in range(10)]
fresh = HMM.random(states, symbols, seed=0)
final_ll, iters = baum_welch_multi(fresh, obs_list, iterations=100)
```

### Classification

```python
from hmm import classify_sequence

# Classify an observation sequence against multiple models
idx, name, ll = classify_sequence([model_a, model_b], obs, model_names=["A", "B"])
```

## CLI

```bash
# Create a random HMM
python3 -m hmm random --states "Sunny,Cloudy,Rainy" --symbols "Walk,Shop,Clean" --out model.json --seed 1

# Print model parameters
python3 -m hmm info --model model.json

# Generate observations
python3 -m hmm generate --model model.json --length 20 --seed 3

# Viterbi decode
python3 -m hmm viterbi --model model.json --obs observations.json

# Baum-Welch training
python3 -m hmm train --model model.json --obs observations.json --out trained.json --iterations 100 --verbose

# Posterior decoding
python3 -m hmm posterior --model model.json --obs observations.json

# Classify against multiple models
python3 -m hmm classify --models model_a.json,model_b.json --obs observations.json

# Per-timestep entropy
python3 -m hmm entropy --model model.json --obs observations.json
```

## How It Works

### Forward Algorithm (Scaled)

The forward variable α_t(i) = P(O₁...O_t, q_t = S_i | model) is computed recursively. To prevent underflow on long sequences, each time-step is scaled by its sum so α rows always sum to 1. The log-likelihood is the sum of log scaling factors.

### Backward Algorithm (Scaled)

β_t(i) = P(O_{t+1}...O_T | q_t = S_i, model) uses the same scaling factors from forward() for consistency, enabling gamma = α·β computation.

### Viterbi (Log-Space)

δ_t(i) = max over paths ending at state i at time t of P(path, O₁...O_t | model). Computed entirely in log-space to avoid underflow. Backpointers ψ record the optimal predecessor for path reconstruction.

### Baum-Welch (EM)

E-step: compute γ (state posteriors) and ξ (transition posteriors) via forward-backward. M-step: re-estimate A, B, π as normalized expected counts with additive smoothing. Converges to a local optimum. The multi-sequence variant accumulates expected counts across all sequences before the M-step.

## Examples

- `examples/dishonest_casino.py` — The classic Dishonest Casino HMM (fair/loaded die)
- `examples/weather_prediction.py` — Weather prediction (Sunny/Cloudy/Rainy → Walk/Shop/Clean)

## Project Structure

```
hmm-toolkit/
├── hmm/
│   ├── __init__.py      # Public API exports
│   ├── __main__.py      # CLI entry point
│   ├── hmm.py           # HMM data structure + validation
│   ├── algorithms.py    # Forward, Backward, Viterbi, Baum-Welch, posterior
│   ├── analysis.py       # Classification, entropy, KL, dwell time
│   ├── sequences.py      # Generation + JSON I/O
│   └── cli.py           # Argparse CLI (9 subcommands)
├── examples/
│   ├── dishonest_casino.py
│   └── weather_prediction.py
├── tests/
│   └── test_hmm.py      # 40 tests
├── pyproject.toml
└── README.md
```

## Testing

```bash
cd hmm-toolkit
PYTHONPATH=. python3 -m pytest tests/ -v
```

## Known Issues (Resolved)

| # | Bug | Fix |
|---|-----|-----|
| 1 | `forward`/`backward`/`viterbi` accepted out-of-range observation indices, causing confusing `IndexError` | Added `_validate_observations()` that raises `ValueError` with a descriptive message |
| 2 | Duplicate state names silently accepted — `state_index()` would return wrong index (last duplicate) | Constructor now rejects duplicate state/symbol names |
| 3 | Empty states/symbols not rejected — caused `ZeroDivisionError` in normalisation | Constructor now requires ≥1 state and ≥1 symbol |
| 4 | `viterbi()` returned `[0]*T` for impossible sequences, misleading callers into thinking a valid path exists | Now returns `[], -inf` for impossible sequences |
| 5 | `_sample_categorical` silently returned last index for all-zero probability vectors | Now raises `ValueError` with clear message |
| 6 | `state_durations` type annotation restricted to `str` but function works with any hashable type | Relaxed to accept `Sequence` of any type |

## License

MIT