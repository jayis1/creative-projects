# convolutional-codec

A pure-Python toolkit for convolutional error-correcting codes with a trellis-based encoder, hard-decision Viterbi decoder, and binary symmetric channel simulation.

## Features

- Trellis specification using standard octal generator notation
- Rate `1/n` convolutional encoder with optional zero-tail termination
- Hard-decision Viterbi decoder
- Binary symmetric channel simulation with reproducible RNG seeds
- CLI for encode / decode / simulate workflows
- Unit tests for encoding, decoding, error correction, and CLI behavior

## How it works

A convolutional encoder shifts one input bit at a time through a finite memory register. Each generator polynomial selects taps from that register and emits a parity bit. The resulting trellis can be decoded with the Viterbi algorithm, which keeps the cheapest path into each state using Hamming distance as the branch metric.

This project currently focuses on classic binary hard-decision decoding:

1. Build a `Trellis` from the constraint length and octal generators.
2. `encode()` emits one code symbol per generator for each input bit.
3. `decode()` runs Viterbi dynamic programming over the trellis.
4. `simulate_bsc()` flips encoded bits independently with probability `p`.

## Usage

### Python

```python
from convolutional_codec.codec import ConvolutionalCodec, Trellis

codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)))
payload = [1, 0, 1, 1, 0, 1]
encoded = codec.encode(payload)
decoded = codec.decode(encoded)
print(decoded.bits)
```

### CLI

```bash
python3 -m convolutional_codec encode 101101
python3 -m convolutional_codec decode 111000010111011101
python3 -m convolutional_codec simulate-bsc 101101 --p 0.05 --seed 7
```

## Running tests

```bash
python3 -m unittest discover -s tests -v
```
