# Grammar Inference

A small corpus-to-grammar laboratory. It learns a probabilistic context-free grammar from whitespace-tokenized sentences by recursively splitting spans into observed binary rules, then emits bounded samples. Its novelty twist: unlike a simple n-gram generator, it exposes the learned derivation tree and rule probabilities for inspection.

## How it works

For every sentence span, the learner records its terminal yield and all binary split points. A compact grammar is induced from repeated spans; terminal spans become lexical rules and longer spans select an observed split. Sampling chooses alternatives weighted by corpus frequency, with a seeded RNG for reproducibility. This intentionally favors transparent, inspectable rules over broad linguistic coverage.

## Usage

From the repository root:

    python3 grammar-inference/cli.py --help
    python3 grammar-inference/cli.py demo
    python3 grammar-inference/cli.py learn 'red birds fly' 'small birds fly' --samples 2 --seed 7

Example:

    $ python3 grammar-inference/cli.py demo
    corpus sentences: 4
    learned span rules: 17
    sample: red birds sing

## Limitations

Tokenization is whitespace based; the model does not infer syntax categories or guarantee grammaticality. Training corpus and generated sentence lengths are bounded by CLI validation. No third-party packages are required.

## Testing

    python3 -m unittest discover -s grammar-inference/tests -v

## Known Issues (Resolved)

The Phase 3 review found and fixed the empty-corpus issue: the CLI now rejects missing training sentences with an actionable error instead of constructing an unusable model. A regression test covers it.
