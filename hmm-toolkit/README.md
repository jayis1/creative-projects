# hmm-toolkit

[![Tests](https://img.shields.io/badge/tests-109%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.8+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Pure Python](https://img.shields.io/badge/dependencies-zero-orange)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-3.0.0-blue)](CHANGELOG)

A comprehensive **Hidden Markov Model (HMM)** toolkit implemented from scratch in pure Python — **zero third-party dependencies** for core functionality.

> Supports discrete-emission HMMs, continuous Gaussian-emission HMMs, and Profile HMMs for bioinformatics, with Forward/Backward/Viterbi/Baum-Welch, advanced training (cross-validation, random restarts, constrained EM, grid search), ASCII visualisation, a 18-command CLI, and 109 tests.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [CLI Reference](#cli-reference)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

### Core HMM (Discrete Emissions)
- **Forward algorithm** (scaled) — computes P(observations | model) with numerical stability
- **Backward algorithm** (scaled) — companion backward probabilities
- **Viterbi algorithm** (log-space) — most likely hidden state path
- **Baum-Welch** — EM parameter estimation (single + multi-sequence)
- **Posterior decoding** — forward-backward marginal decoding

### Gaussian HMM (Continuous Emissions)
- **Multivariate Gaussian emissions** — full covariance matrices
- **Forward / Backward / Viterbi** for continuous observations
- **Baum-Welch training** — learns means and covariances from data
- **Pure-Python linear algebra** — determinant, inverse, matrix multiply (no NumPy)

### Profile HMM (Bioinformatics)
- **MSA to HMM** — build a Profile HMM from a multiple sequence alignment
- **Match / Insert / Delete states** — standard three-state architecture
- **Log-odds scoring** — score sequences against a motif with background model
- **Automatic match-column detection** — configurable gap threshold

### Advanced Training
- **K-fold cross-validation** — model selection for number of hidden states
- **Random restarts** — avoid local optima with multiple initialisations
- **Constrained Baum-Welch** — lock specific transitions, emissions, or initial probs
- **Grid search** — sweep over smoothing and tolerance hyperparameters

### Analysis Utilities
- **Sequence classification** — classify observations by best-matching model
- **State entropy** — per-timestep Shannon entropy of the state posterior
- **Symmetric KL divergence** — compare two HMMs via log-likelihood ratio
- **State durations** — segment a state path into consecutive runs
- **Expected dwell time** — theoretical mean residence time per state

### Visualisation (ASCII)
- **Transition diagrams** — state-level edge visualisation
- **Viterbi path rendering** — grid showing decoded states vs observations
- **Posterior heatmaps** — 10-level grey-scale probability matrix
- **Entropy sparklines** — Unicode bar charts for uncertainty over time
- **Model formatting** — pretty-printed parameters with bars

### Infrastructure
- **18-subcommand CLI** — full command-line interface
- **JSON serialization** — save/load models and observation sequences
- **Config files** — JSON/YAML/TOML support
- **Structured logging** — configurable verbosity levels
- **GitHub Actions CI** — tested on Python 3.8–3.12
- **pip-installable** — `pip install -e .`
- **Pure Python (stdlib only)** — no NumPy, SciPy, or scikit-learn required

---

## Installation

### From source (development)

```bash
cd hmm-toolkit
pip install -e ".[dev]"
```

### Without installation

```bash
cd hmm-toolkit
PYTHONPATH=. python3 -m hmm <command> [args]
```

### Requirements

- Python ≥ 3.8
- No required dependencies (stdlib only)
- Optional: `pyyaml` for YAML config files, `pytest` for running tests

---

## Quick Start

### Discrete HMM — Dishonest Casino

```python
from hmm import HMM, forward, viterbi, baum_welch, generate_sequence

# A dealer sometimes switches between a fair and loaded die
states = ["F", "L"]
symbols = ["1", "2", "3", "4", "5", "6"]
A = [[0.95, 0.05], [0.10, 0.90]]           # F→F 95%, L→L 90%
B = [[1/6]*6, [0.10, 0.10, 0.10, 0.10, 0.10, 0.50]]  # loaded favours 6
pi = [0.5, 0.5]

model = HMM(states, symbols, A, B, pi)

# Generate 300 rolls
true_states, obs = generate_sequence(model, length=300, seed=42)

# Viterbi decode — recover the hidden state path
obs_idx = model.observation_sequence(obs)
path, logp = viterbi(model, obs_idx)

# Train a fresh model from observations only
fresh = HMM.random(states, symbols, seed=0)
final_ll, iters = baum_welch(fresh, obs_idx, iterations=200)
print(f"Converged in {iters} iterations, LL={final_ll:.2f}")
```

### Gaussian HMM — Signal Clustering

```python
from hmm.gaussian import GaussianHMM, random_gaussian_hmm

# 2-state 1-D Gaussian HMM
model = GaussianHMM(
    states=["Low", "High"],
    n_dim=1,
    A=[[0.92, 0.08], [0.10, 0.90]],
    means=[[0.0], [10.0]],
    covs=[[[1.0]], [[2.0]]],
    pi=[0.8, 0.2],
)

# Train from continuous data
fresh = random_gaussian_hmm(["Low", "High"], 1, seed=42)
signal = [[0.1], [0.2], [-0.1], [10.0], [10.1], [9.9], [0.05], [10.05]]
final_ll, iters = fresh.baum_welch(signal, iterations=50)
print(f"Learned means: {fresh.means}")  # ≈ [[0.0], [10.0]]
```

### Profile HMM — Motif Detection

```python
from hmm.profile import build_profile_hmm

# DNA multiple sequence alignment
alignment = ["ATGCGTAC", "AT-CGTAC", "A-GCGTAC", "ATGCGTAC"]

# Build a Profile HMM
ph = build_profile_hmm(alignment, list("ACGT"), threshold=0.5)

# Score new sequences (log-odds against uniform background)
score = ph.log_odds_score("ATGCGTAC")  # high — matches motif
score = ph.log_odds_score("GGGGCCCC")  # low  — unrelated
```

### Cross-Validation — Model Selection

```python
from hmm.training import k_fold_cross_validation, summarize_cv_results

results = k_fold_cross_validation(
    states=[], symbols=["A", "B", "C", "D"],
    obs_sequences=my_obs_list,
    n_states_options=[2, 3, 4],
    k=5, iterations=50, seed=42,
)
summary = summarize_cv_results(results)
# Pick the n_states with highest mean validation log-likelihood
```

### Visualisation

```python
from hmm.viz import transition_diagram, posterior_heatmap, format_model

print(transition_diagram(model))
print(posterior_heatmap(model, obs))
print(format_model(model))
```

---

## Architecture

```
hmm-toolkit/
├── hmm/
│   ├── __init__.py          # Public API exports (v3.0.0)
│   ├── __main__.py          # CLI entry point (python -m hmm)
│   ├── hmm.py               # HMM class: construction, validation, factories
│   ├── algorithms.py        # Forward, Backward, Viterbi, Baum-Welch (single+multi)
│   ├── analysis.py          # Classification, entropy, KL, dwell time
│   ├── sequences.py         # Sequence generation + JSON I/O
│   ├── gaussian.py          # GaussianHMM: continuous-emission HMM
│   ├── _linalg.py           # Pure-Python linalg: det, inv, matmul
│   ├── profile.py           # ProfileHMM: MSA → HMM for bioinformatics
│   ├── viz.py               # ASCII visualisation (diagrams, heatmaps, sparklines)
│   ├── training.py          # CV, restarts, constrained EM, grid search
│   ├── config.py            # JSON/YAML/TOML config loading
│   ├── logging_config.py    # Structured logging
│   └── cli.py               # 18-subcommand argparse CLI
├── examples/
│   ├── dishonest_casino.py      # Classic fair/loaded die HMM
│   ├── weather_prediction.py    # Weather → activity HMM
│   ├── gaussian_clustering.py   # Continuous signal regime detection
│   ├── profile_hmm_demo.py      # DNA motif detection
│   ├── advanced_training.py     # CV, restarts, grid search
│   └── visualization_demo.py    # ASCII visualisation showcase
├── tests/
│   ├── test_hmm.py          # 40 core tests (Phases 1–2)
│   ├── test_bug_hunt.py     # 12 bug hunt tests (Phase 3)
│   ├── test_gaussian.py     # 21 Gaussian HMM + linalg tests
│   ├── test_profile.py      # 12 Profile HMM tests
│   └── test_advanced.py     # 24 viz/training/config/CLI tests
├── pyproject.toml           # pip-installable package config
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Design Principles

1. **Zero dependencies** — everything runs on the Python standard library
2. **Numerical stability** — scaled forward/backward, log-space Viterbi
3. **Validation first** — constructors and algorithms validate inputs eagerly
4. **Structural typing** — algorithms use a Protocol so HMM, GaussianHMM, and ProfileHMM all work
5. **Modular architecture** — each concern in its own module, clean public API

### Algorithm Details

#### Forward Algorithm (Scaled)
The forward variable αₜ(i) = P(O₁...Oₜ, qₜ = Sᵢ | model) is computed recursively. Each time-step is scaled by its sum so α rows always sum to 1, preventing underflow. The log-likelihood is Σ log(scaleₜ).

#### Backward Algorithm (Scaled)
βₜ(i) = P(Oₜ₊₁...Oₜ | qₜ = Sᵢ, model) uses the same scaling factors from forward() for consistency, enabling γ = α·β computation.

#### Viterbi (Log-Space)
δₜ(i) = max over paths ending at state i at time t of P(path, O₁...Oₜ | model). Computed entirely in log-space. Backpointers ψ record the optimal predecessor for path reconstruction.

#### Baum-Welch (EM)
E-step: compute γ (state posteriors) and ξ (transition posteriors) via forward-backward. M-step: re-estimate A, B, π as normalised expected counts with additive smoothing. Converges to a local optimum.

---

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `HMM(states, symbols, A, B, pi)` | Discrete-emission HMM |
| `GaussianHMM(states, n_dim, A, means, covs, pi)` | Continuous Gaussian-emission HMM |
| `ProfileHMM(alphabet, match_columns, ...)` | Profile HMM for biological sequence alignment |

### Factory Methods

| Method | Description |
|--------|-------------|
| `HMM.random(states, symbols, seed=)` | Random valid HMM |
| `HMM.uniform(states, symbols)` | Uniform HMM |
| `random_gaussian_hmm(states, n_dim, seed=)` | Random Gaussian HMM |
| `build_profile_hmm(alignment, alphabet, threshold=)` | Profile HMM from MSA |

### Algorithms

| Function | Description |
|----------|-------------|
| `forward(hmm, obs)` | Scaled forward → (alpha, scales, log_likelihood) |
| `backward(hmm, obs, scales=)` | Scaled backward → beta |
| `viterbi(hmm, obs)` | Log-space Viterbi → (path, log_prob) |
| `baum_welch(hmm, obs, iterations=, tol=)` | EM training (single sequence) |
| `baum_welch_multi(hmm, obs_list, ...)` | EM training (multiple sequences) |
| `posterior_decode(hmm, obs)` | Forward-backward decoding → (path, gamma) |

### Advanced Training

| Function | Description |
|----------|-------------|
| `k_fold_cross_validation(...)` | K-fold CV for model selection |
| `summarize_cv_results(results)` | Summarise CV by n_states |
| `train_with_restarts(...)` | Multiple random restarts, keep best |
| `constrained_baum_welch(...)` | EM with locked transitions/emissions/pi |
| `grid_search(...)` | Sweep over smoothing and tolerance |

### Analysis

| Function | Description |
|----------|-------------|
| `sequence_log_likelihood(hmm, obs)` | Log P(O \| model) |
| `classify_sequence(models, obs)` | Best-matching model |
| `state_entropy(hmm, obs)` | Per-timestep Shannon entropy |
| `symmetric_kl(hmm_a, hmm_b, obs)` | Symmetric KL divergence |
| `state_durations(path)` | Segment path into runs |
| `expected_state_dwell_time(hmm)` | 1/(1-A[i][i]) per state |

### Visualisation

| Function | Description |
|----------|-------------|
| `transition_diagram(hmm)` | ASCII state-transition diagram |
| `viterbi_path_visualization(hmm, obs)` | Viterbi path grid |
| `posterior_heatmap(hmm, obs)` | 10-level grey-scale heatmap |
| `entropy_sparkline(hmm, obs)` | Unicode sparkline of entropy |
| `format_model(hmm)` | Pretty-printed model parameters |

---

## CLI Reference

```bash
# Create models
hmm-toolkit random --states "Sunny,Cloudy,Rainy" --symbols "Walk,Shop,Clean" --out model.json --seed 1
hmm-toolkit uniform --states "A,B" --symbols "x,y" --out uniform.json

# Inspect models
hmm-toolkit info --model model.json
hmm-toolkit visualize --model model.json --type transition
hmm-toolkit visualize --model model.json --obs obs.json --type heatmap
hmm-toolkit dwell --model model.json

# Generate and decode
hmm-toolkit generate --model model.json --length 20 --seed 3 --show-states
hmm-toolkit viterbi --model model.json --obs observations.json
hmm-toolkit forward --model model.json --obs observations.json
hmm-toolkit posterior --model model.json --obs observations.json
hmm-toolkit entropy --model model.json --obs observations.json

# Training
hmm-toolkit train --model model.json --obs obs.json --out trained.json --iterations 100 --verbose
hmm-toolkit train-multi --model model.json --obs obs1.json,obs2.json --out trained.json
hmm-toolkit restarts --states "F,L" --symbols "1,2,3,4,5,6" --obs obs.json --out best.json --n-restarts 10

# Model selection
hmm-toolkit cv --symbols "1,2,3,4,5,6" --obs obs1.json,obs2.json --n-states 2,3,4 --k 5
hmm-toolkit grid --states "F,L" --symbols "1,2,3,4,5,6" --obs obs.json --restarts 5

# Comparison and classification
hmm-toolkit classify --models model_a.json,model_b.json --obs obs.json
hmm-toolkit compare --model-a a.json --model-b b.json --obs obs.json

# Profile HMM
hmm-toolkit profile --alignment msa.json --alphabet ACGT --out profile.json --score-seq ATGCGTAC
```

---

## Examples

Run any example with:

```bash
cd hmm-toolkit
PYTHONPATH=. python3 examples/<name>.py
```

| Example | Description |
|---------|-------------|
| `dishonest_casino.py` | Classic fair/loaded die — generate, decode, train |
| `weather_prediction.py` | Weather → activities — Viterbi, posterior, training |
| `gaussian_clustering.py` | 1-D signal regime detection with GaussianHMM |
| `profile_hmm_demo.py` | DNA motif detection with Profile HMM |
| `advanced_training.py` | Cross-validation, random restarts, grid search |
| `visualization_demo.py` | ASCII visualisation showcase |

### Sample Output (Viterbi Path Visualisation)

```
Viterbi Path (log-prob = -3.9325)
==================================================
  Obs:  Walk   Walk   Shop   Shop

   Sunny: [Sunny]  [Sunny]    .      .
   Rainy:   .      .    [Rainy]  [Rainy]
```

### Sample Output (Posterior Heatmap)

```
Posterior Probability Heatmap
==================================================
  Scale: █ ≥0.9  ▇ ≥0.8  ▆ ≥0.7  ▅ ≥0.6  ▄ ≥0.5  ▃ ≥0.4  ▂ ≥0.3  │ ≥0.2  . ≥0.1  ( <0.1

  t  obs   Sunny  Rainy
  ---------------------
   0  Walk       (      █
   1  Walk       (      █
   2  Shop       ▃      ▄
   3  Shop       ▄      ▃
```

---

## Testing

```bash
cd hmm-toolkit
pip install pytest
python3 -m pytest tests/ -v
```

```
109 passed in 0.57s
```

Test breakdown:
- `test_hmm.py` — 40 tests (construction, forward/backward, Viterbi, Baum-Welch, generation, serialization, posterior, analysis, multi-sequence)
- `test_bug_hunt.py` — 12 tests (observation validation, duplicates, empty states, impossible paths, zero-prob sampling, KL edge cases, type fixes, set_parameters)
- `test_gaussian.py` — 21 tests (linear algebra, Gaussian PDF, construction, forward/Viterbi, Baum-Welch)
- `test_profile.py` — 12 tests (construction, match columns, forward/Viterbi, log-odds, gaps)
- `test_advanced.py` — 24 tests (visualisation, cross-validation, restarts, constrained EM, grid search, config, CLI)

---

## Known Issues (Resolved)

| # | Bug | Fix |
|---|-----|-----|
| 1 | `forward`/`backward`/`viterbi` accepted out-of-range observation indices, causing confusing `IndexError` | Added `_validate_observations()` that raises `ValueError` with a descriptive message |
| 2 | Duplicate state names silently accepted — `state_index()` would return wrong index | Constructor now rejects duplicate state/symbol names |
| 3 | Empty states/symbols not rejected — caused `ZeroDivisionError` in normalisation | Constructor now requires ≥1 state and ≥1 symbol |
| 4 | `viterbi()` returned `[0]*T` for impossible sequences, misleading callers | Now returns `[], -inf` for impossible sequences |
| 5 | `_sample_categorical` silently returned last index for all-zero probability vectors | Now raises `ValueError` with clear message |
| 6 | `state_durations` type annotation restricted to `str` but function works with any hashable type | Relaxed to accept `Sequence` of any type |
| 7 | `constrained_baum_welch` did not preserve locked parameters through `set_parameters` normalisation | Now saves and restores locked values after normalisation |
| 8 | Gaussian HMM mean-dimension mismatch not validated for all cases | Constructor now checks all mean vector lengths against `n_dim` |

---

## Roadmap

- [ ] **HMM topologies** — left-right (Bakis), ergodic, custom topology constraints
- [ ] **Continuous HMM extensions** — Gaussian mixture emissions, diagonal covariance
- [ ] **Online/incremental training** — streaming Baum-Welch for real-time data
- [ ] **Numba/Cython acceleration** — optional fast paths for large models
- [ ] **HTML/SVG visualisation** — interactive posterior plots, state diagrams
- [ ] **HMM networks** — coupled HMMs, hierarchical HMMs
- [ ] **Input formats** — FASTA, Stockholm, HMMER format for Profile HMMs
- [ ] **Model averaging** — ensemble methods for robust decoding

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on development, testing, and pull requests.

---

## Changelog

### v3.0.0 (2026-06-30) — Comprehensive Improvement

**New modules:**
- `gaussian.py` — Gaussian HMM with continuous multivariate emissions, Baum-Welch training
- `_linalg.py` — Pure-Python linear algebra (determinant, inverse, matrix multiply)
- `profile.py` — Profile HMM for biological sequence alignment (MSA → HMM, log-odds scoring)
- `viz.py` — ASCII visualisation (transition diagrams, Viterbi paths, posterior heatmaps, entropy sparklines)
- `training.py` — Advanced training (k-fold CV, random restarts, constrained EM, grid search)
- `config.py` — JSON/YAML/TOML configuration file support
- `logging_config.py` — Structured logging with configurable verbosity

**New CLI subcommands (9 added, 18 total):**
- `train-multi`, `uniform`, `visualize`, `compare`, `dwell`, `profile`, `cv`, `grid`, `restarts`

**New examples (4 added, 6 total):**
- `gaussian_clustering.py`, `profile_hmm_demo.py`, `advanced_training.py`, `visualization_demo.py`

**Infrastructure:**
- GitHub Actions CI (Python 3.8–3.12)
- LICENSE (MIT)
- CONTRIBUTING.md
- Type hints via structural Protocol (`_HMMLike`)
- pip-installable with optional dependencies
- 57 new tests (109 total, all passing)
- Bug fix: constrained Baum-Welch now correctly preserves locked parameters

### v2.0.0 — Enhanced

- Multi-sequence Baum-Welch, analysis utilities, 2 CLI subcommands, 13 new tests

### v1.0.0 — Initial

- Core HMM, Forward/Backward/Viterbi/Baum-Welch, generation, JSON I/O, CLI, 27 tests

---

## License

MIT — see [LICENSE](LICENSE).