# Privacy Budget Lab

A dependency-free, inspectable differential-privacy sandbox for understanding contribution clipping, Laplace noise, and basic sequential composition. It releases noisy bounded sums; it is an educational reference, not a production privacy accountant.

## How it works

Each contribution is clipped to public bounds. Under add/remove-one adjacency, a single bounded contribution has L1 sensitivity `max(abs(lower), abs(upper))`. The mechanism draws Laplace noise with scale `sensitivity / epsilon`; smaller epsilon means more noise. `PrivacyCost` composes sequential guarantees by adding epsilon and delta. Sampling uses `SystemRandom` by default; seeded randomness is exposed only for reproducible demonstrations.

## Usage

From this directory:

```sh
python3 privacy_budget.py 2 3 99 --lower 0 --upper 10 --epsilon 0.8
python3 privacy_budget.py 2 3 --epsilon 1 --seed 7
python3 -m unittest discover -s tests -v
```

This enhancement adds two mechanisms. `private_mean` clips values and adds Laplace noise using range/n sensitivity under fixed-size replacement adjacency. `private_histogram` uses a caller-supplied public category domain; add/remove-one records increment one bin, giving vector L1 sensitivity one and noise scale 1/epsilon per bin. Both return their privacy cost and reject malformed inputs.

```python
from privacy_budget import private_histogram
released, cost = private_histogram(["red", "blue", "red"],
    categories=["red", "blue", "green"], epsilon=0.5)
```

The CLI still emits a noisy sum as JSON. `--seed` remains demo-only and is not safe for actual releases.

## Known Issues (Resolved)

- Sequential composition previously capped an accumulated delta just below one, which could understate a vacuous bound when component deltas summed to at least one. A regression test reproduced this; composition now rejects totals at or above one.
- Histogram domain validation previously attempted set conversion before confirming labels were strings, raising an incidental `TypeError` for unhashable malformed labels. A regression test reproduced it; validation now rejects non-string labels with the documented `ValueError`.

## Limitations

No persistent budget ledger, advanced composition theorem, or protection against misuse of public bounds is provided. Clipping bounds and the adjacency model are part of the privacy claim, not mere input conveniences.
