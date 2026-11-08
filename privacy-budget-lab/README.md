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

The CLI emits one JSON object. The seed is not appropriate for a real release because predictable noise is not private. Always choose bounds, adjacency, and privacy parameters based on the data-release setting. This initial version offers a noisy sum and cost composition; later versions extend these capabilities.

## Limitations

No persistent budget ledger, advanced composition theorem, or protection against misuse of public bounds is provided. Clipping bounds and the adjacency model are part of the privacy claim, not mere input conveniences.
