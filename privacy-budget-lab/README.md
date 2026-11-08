# Privacy Budget Lab

A dependency-free, inspectable differential-privacy sandbox for clipped sums, fixed-size means, categorical histograms, and basic sequential composition. It is an educational reference—not a production privacy accountant or a substitute for a formal privacy review.

## Table of contents

- [What it does](#what-it-does)
- [Requirements and installation](#requirements-and-installation)
- [Quick start](#quick-start)
- [Command-line interface](#command-line-interface)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Privacy assumptions and limitations](#privacy-assumptions-and-limitations)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)

## What it does

| Mechanism | Adjacency / sensitivity | Result |
| --- | --- | --- |
| `private_sum` | Add/remove one; bounded contribution sensitivity `max(abs(lower), abs(upper))` | Clipped sum plus Laplace noise |
| `private_mean` | Fixed-size replacement; sensitivity `(upper - lower) / n` | Clipped mean plus Laplace noise |
| `private_histogram` | Add/remove one; one record increments one public-domain bin, vector L1 sensitivity 1 | Noisy count for each declared category |
| `PrivacyCost.compose` | Basic sequential composition | Adds epsilon and delta; rejects total delta >= 1 |

All mechanisms return their released value and the corresponding `PrivacyCost`. Invalid bounds, epsilon values, empty means, duplicate histogram categories, and undeclared histogram values are rejected.

## Requirements and installation

- Python 3.10 or newer
- No third-party runtime dependencies

Clone the monorepo and enter this project directory:

```sh
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/privacy-budget-lab
```

No package installation is needed. Run the script directly or import `privacy_budget.py` from this directory. There is no separate project license file or automated status badge; consult the repository-level license and policy before reuse.

## Quick start

```sh
# Existing default: clipped sum, emitted as one JSON object
python3 privacy_budget.py 2 3 99 --lower 0 --upper 10 --epsilon 0.8 --seed 7

# Fixed-size mean
python3 privacy_budget.py --mode mean 2 3 9 --lower 0 --upper 10 --epsilon 0.8 --seed 7

# Histogram: define the complete public category domain explicitly
python3 privacy_budget.py --mode histogram red blue red \
  --category red --category blue --category green --epsilon 0.5 --seed 7
```

`--seed` exists only to make demonstrations reproducible. A seeded pseudo-random generator is predictable and must not be used for real privacy releases. With no seed, sampling uses `random.SystemRandom`.

## Command-line interface

```text
privacy_budget.py [-h] [--mode {sum,mean,histogram}]
                  [--category CATEGORIES] [--lower LOWER] [--upper UPPER]
                  [--epsilon EPSILON] [--seed SEED] [values ...]
```

- `--mode sum` (default) and `--mode mean` accept numeric positional values. With no values, they use the demonstration values `1 2 3 4`.
- `--mode histogram` accepts category values as positionals and requires one or more repeated `--category` flags for the public domain. Values not in that domain are errors.
- `--lower` and `--upper` configure clipping bounds for sum and mean.
- `--epsilon` must be finite and positive.
- `--seed` makes output deterministic for demos only.

Each successful invocation prints JSON with the mechanism name, released result, epsilon, delta, and contribution count. Invalid arguments produce an argparse error and a nonzero exit status.

## Python API

```python
from privacy_budget import PrivacyCost, private_histogram, private_mean, private_sum

noisy_total, sum_cost = private_sum([2, 3, 99], lower=0, upper=10, epsilon=0.8)
noisy_average, mean_cost = private_mean([2, 3, 9], lower=0, upper=10, epsilon=0.8)
noisy_counts, histogram_cost = private_histogram(
    ["red", "blue", "red"],
    categories=["red", "blue", "green"],
    epsilon=0.5,
)
combined = sum_cost.compose(mean_cost).compose(histogram_cost)
```

Pass a `random.Random` instance as `rng=` only for deterministic tests and demonstrations. Otherwise the mechanism creates a system-backed random source. Remember that composing costs accounts for sequential releases only when each mechanism's stated adjacency assumptions apply to the same privacy unit and dataset setting.

## Architecture

The project is intentionally a small single-module Python program:

- `PrivacyCost` validates a basic `(epsilon, delta)` guarantee and performs conservative sequential composition.
- `clamp_count` validates finite values and clips a contribution to public bounds.
- `laplace_noise` samples centered Laplace noise using inverse-CDF sampling.
- `private_sum`, `private_mean`, and `private_histogram` implement and return three distinct releases and their costs.
- `main` validates CLI options, dispatches to the selected mechanism, and serializes results as JSON.
- `tests/test_privacy_budget.py` uses the standard-library `unittest` runner for mechanism, validation, and CLI behavior.

## Privacy assumptions and limitations

Bounds and histogram categories must be public and selected independently of the protected data. The sum uses add/remove-one adjacency; the mean uses fixed-size replacement adjacency; the histogram uses add/remove-one adjacency. These guarantees are not interchangeable. The mechanisms do not provide a persistent budget ledger, advanced composition, subsampling amplification, automatic bound selection, or protection against misuse of the adjacency model. Histogram outputs are not post-processed (for example, to non-negative integers or normalized probabilities), and noise can produce negative counts.

This code is intended for learning and local experiments. Before using any mechanism for a real release, validate the privacy unit, neighboring-dataset definition, sensitivity, random-number generation, cumulative budget, and applicable legal or organizational requirements with a qualified reviewer.

## Testing

From this directory:

```sh
python3 -m unittest discover -s tests -v
python3 privacy_budget.py --help
python3 privacy_budget.py --mode mean 0 10 --lower 0 --upper 10 --seed 9
python3 privacy_budget.py --mode histogram red blue --category red --category blue --seed 9
```

Tests are deterministic and require only the Python standard library.

## Contributing

Keep changes dependency-free where practical. For mechanism changes, document adjacency and sensitivity assumptions, add tests for valid and invalid inputs, and verify CLI output when the interface changes. Run the complete unittest suite before submitting. Do not add claims of production privacy or modify licensing terms without project-owner review.

## Roadmap

- Add opt-in CSV/JSON input with strict schema and domain validation.
- Explore a small explicit budget ledger with safe persistence semantics.
- Add property-based checks for sensitivity and numerical edge cases if a test dependency is approved.
- Consider a package/installation interface if the project grows beyond this educational single-module tool.

## Changelog

- Expanded the CLI to select the sum, mean, or histogram mechanism and return consistent structured JSON.
- Added repeated `--category` arguments to declare a histogram's public domain; missing domains and undeclared values now fail with clear CLI errors.
- Added CLI regression tests and documented command usage, algorithm assumptions, architecture, and limitations.
- Earlier project work added clipped mean and public-domain histogram mechanisms, plus guards against vacuous delta composition and malformed category domains.
