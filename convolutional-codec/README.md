# convolutional-codec

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/convolutional-codec.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/convolutional-codec.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

A pure-Python convolutional coding toolkit for experimentation, teaching, and lightweight research. It includes trellis-based encoding, hard/soft Viterbi decoding, puncturing, CRC framing, interleaving, burst/noise channel models, Monte Carlo benchmarking, and reproducible config-driven runs.

## Table of Contents

- [Highlights](#highlights)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Configuration Files](#configuration-files)
- [Architecture](#architecture)
- [Examples](#examples)
- [Recent Improvements](#recent-improvements)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## Highlights

- Trellis specification using standard octal generator notation
- Rate `1/n` convolutional encoder with optional zero-tail termination
- Hard-decision and soft-decision Viterbi decoding
- Optional puncturing for higher-rate derived codes
- CRC framing for residual error detection
- Rectangular block interleaver / deinterleaver
- Channel models:
  - Binary symmetric channel (BSC)
  - AWGN channel with BPSK modulation
  - Gilbert-Elliott burst-error channel
- Monte Carlo benchmark helpers for BER / FER sweeps
- CLI support for simulation, analysis, and config-driven execution
- Installable package with pytest suite and GitHub Actions workflow

## Installation

### Option 1: local editable install

```bash
cd convolutional-codec
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .[dev]
```

### Option 2: run without installation

```bash
cd convolutional-codec
python3 -m convolutional_codec --help
```

## Quick Start

### Python API

```python
from convolutional_codec import CRC, BlockInterleaver, ConvolutionalCodec, Trellis
from convolutional_codec.analysis import analyze_codec, benchmark_awgn

codec = ConvolutionalCodec(
    Trellis(3, (0o7, 0o5)),
    puncture_pattern=(1, 1, 0, 1),
)
crc = CRC(0b10011, width=4)
interleaver = BlockInterleaver(3, 7)

payload = [1, 0, 1, 1, 0, 1, 0, 0]
encoded = codec.encode_frame(payload, crc=crc)
interleaved = interleaver.interleave(encoded)
decoded = codec.decode_frame(interleaver.deinterleave(interleaved), crc=crc)
report = analyze_codec(codec, max_input_bits=6)
curve = benchmark_awgn(codec, [2.0, 3.0, 4.0], bits=payload, trials=25, crc=crc, interleaver=interleaver)

print(decoded["payload_bits"], decoded["crc_ok"])
print(report["distance_estimate"])
print(curve)
```

### CLI quick examples

```bash
python3 -m convolutional_codec encode 101101
python3 -m convolutional_codec decode 111000010111011101 --pretty
python3 -m convolutional_codec decode-soft -- "1.0,0.8,-0.9,-1.2,0.7,-0.6"
python3 -m convolutional_codec analyze --pretty
python3 -m convolutional_codec --crc-poly 0b10011 --crc-width 4 simulate-awgn 10110100 --snr-db 4.0 --seed 7 --frame --pretty
python3 -m convolutional_codec --crc-poly 0b10011 --crc-width 4 --puncture-pattern 1101 --interleave-rows 3 --interleave-cols 7 simulate-burst 10110100 --p-good-to-bad 0.05 --p-bad-to-good 0.3 --bad-error-prob 0.18 --seed 11 --frame --pretty
```

## CLI Usage

```text
encode            Encode a bit string
decode            Decode a hard-decision bit stream
decode-soft       Decode comma-separated soft samples
simulate-bsc      Simulate a BSC transmission
simulate-awgn     Simulate an AWGN transmission
simulate-burst    Simulate a Gilbert-Elliott burst channel
benchmark-bsc     Estimate BER/FER across BSC crossover probabilities
benchmark-awgn    Estimate BER/FER across SNR points
benchmark-burst   Estimate BER/FER across burst severities
analyze           Report trellis properties and distance estimates
run-config        Run any supported command from a JSON or TOML config
```

### Benchmarking example

```bash
python3 -m convolutional_codec \
  --crc-poly 0b10011 --crc-width 4 \
  --puncture-pattern 1101 --interleave-rows 3 --interleave-cols 7 \
  benchmark-burst \
  --bits 10110100 \
  --bad-error-prob 0.08,0.16,0.24 \
  --p-good-to-bad 0.05 \
  --p-bad-to-good 0.3 \
  --trials 20 \
  --frame --pretty
```

Example output shape:

```json
{
  "channel": "gilbert-elliott",
  "series": [
    {"parameter": 0.08, "ber": 0.0, "fer": 0.0, "crc_failures": 0},
    {"parameter": 0.16, "ber": 0.0125, "fer": 0.05, "crc_failures": 1}
  ]
}
```

## Configuration Files

Reproducible experiment runs can be stored as JSON or TOML.

Example TOML (`examples/benchmark_config.toml`):

```toml
log_level = "INFO"
pretty = true

[codec]
constraint_length = 3
generators = ["7", "5"]
puncture_pattern = "1101"

[crc]
polynomial = "0b10011"
width = 4

[interleaver]
rows = 3
columns = 7

[command]
name = "benchmark-burst"
bits = "10110100"
bad_error_prob = [0.08, 0.14, 0.22]
p_good_to_bad = 0.05
p_bad_to_good = 0.3
good_error_prob = 0.002
trials = 10
seed = 7
frame = true
```

Run it with:

```bash
python3 -m convolutional_codec run-config examples/benchmark_config.toml
```

## Architecture

```text
payload bits
   │
   ├─> optional CRC append
   ├─> convolutional encoder
   ├─> optional puncturing
   ├─> optional block interleaver
   ├─> channel model (BSC / AWGN / Gilbert-Elliott)
   ├─> optional deinterleaver
   ├─> depuncture with erasures
   ├─> Viterbi decoder (hard or soft)
   └─> optional CRC verification + metrics
```

Project modules:

- `convolutional_codec.codec` — trellis, encoder/decoder, frame and simulation entry points
- `convolutional_codec.channels` — BSC, AWGN, Gilbert-Elliott, BPSK helpers
- `convolutional_codec.interleaver` — typed rectangular block interleaver
- `convolutional_codec.crc` — CRC append/verify utilities
- `convolutional_codec.analysis` — free-distance estimation and benchmark sweeps
- `convolutional_codec.config` — JSON/TOML automation support
- `convolutional_codec.cli` — command orchestration and logging

See also [`docs/architecture.md`](docs/architecture.md).

## Examples

```bash
python3 examples/basic_demo.py
python3 examples/burst_benchmark_demo.py
```

## Recent Improvements

- Added a **Gilbert-Elliott burst channel** for correlated-error simulations
- Added **benchmark-bsc**, **benchmark-awgn**, and **benchmark-burst** Monte Carlo sweep commands
- Added **config-file execution** via `run-config` with JSON/TOML support
- Added **codec analysis** with free-distance estimation over bounded input searches
- Refactored the package into focused modules: codec, channels, interleaver, analysis, config, utils
- Added **logging**, richer validation, more structured JSON output, and `final_state` reporting
- Replaced the original unittest suite with a broader **pytest** suite
- Added **examples**, **architecture docs**, **CONTRIBUTING.md**, **LICENSE**, and **GitHub Actions CI**

## Known Issues (Resolved)

- **Punctured hard-decision decode could mis-handle truncated final puncturing cycles.** Fixed by depuncturing at trellis-symbol granularity and trimming incomplete final symbols safely.
- **AWGN + interleaver simulation discarded soft information during deinterleaving.** Fixed by allowing the block interleaver to round-trip real-valued samples directly.
- **`decode-soft` CLI accepted malformed comma lists like `1.0,,2.0`.** Fixed by stricter input validation.

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for environment setup and contribution guidelines.

## Roadmap

- Add tail-biting convolutional code support
- Add punctured soft-output decoding and survivor-path introspection
- Add more analytical tools, including transfer-function estimates
- Add notebook-based visualization of trellis paths and BER curves
- Add optional NumPy acceleration while keeping the pure-Python reference path

## License

Released under the [MIT License](LICENSE).
