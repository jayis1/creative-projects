# convolutional-codec

A pure-Python toolkit for convolutional error-correcting codes with trellis-based encoding, hard/soft Viterbi decoding, puncturing, CRC framing, interleaving, and noisy channel simulation.

## Features

- Trellis specification using standard octal generator notation
- Rate `1/n` convolutional encoder with optional zero-tail termination
- Hard-decision and soft-decision Viterbi decoding
- Optional puncturing for higher-rate derived codes
- CRC framing for residual error detection
- Rectangular block interleaver / deinterleaver
- Binary symmetric channel and AWGN channel simulation
- CLI for encode / decode / frame / simulation workflows
- Unit tests for encoding, decoding, puncturing, CRC, interleaving, channels, and CLI behavior

## How it works

A convolutional encoder shifts one input bit at a time through a finite memory register. Each generator polynomial selects taps from that register and emits a parity bit. The result is a trellis: a layered state graph whose best path can be recovered with the Viterbi algorithm.

This project supports two decoding modes:

1. **Hard decision**: incoming bits are compared with expected branch symbols using Hamming distance.
2. **Soft decision**: incoming BPSK samples are compared with expected symbols using squared Euclidean distance.

It also layers several practical channel-coding tools on top of the core trellis machinery:

- **Puncturing** deletes selected parity bits to derive higher-rate codes from a lower-rate mother code.
- **CRC framing** appends a frame check sequence to detect uncorrected errors.
- **Block interleaving** spreads adjacent coded bits across time so burst errors act more like random errors.
- **BSC / AWGN simulation** lets you test the code against bit flips or Gaussian noise.

## Usage

### Python

```python
from convolutional_codec import BlockInterleaver, CRC, ConvolutionalCodec, Trellis

codec = ConvolutionalCodec(
    Trellis(3, (0o7, 0o5)),
    puncture_pattern=(1, 1, 0, 1),
)
crc = CRC(0b10011, width=4)
interleaver = BlockInterleaver(2, 14)

payload = [1, 0, 1, 1, 0, 1, 0, 0]
encoded = codec.encode_frame(payload, crc=crc)
interleaved = interleaver.interleave(encoded)
decoded = codec.decode_frame(interleaver.deinterleave(interleaved), crc=crc)
print(decoded["payload_bits"], decoded["crc_ok"])
```

### CLI

```bash
python3 -m convolutional_codec encode 101101
python3 -m convolutional_codec decode 111000010111011101
python3 -m convolutional_codec decode-soft -- "1.0,0.8,-0.9,-1.2,0.7,-0.6"
python3 -m convolutional_codec --puncture-pattern 1101 simulate-bsc 101101 --p 0.05 --seed 7
python3 -m convolutional_codec --crc-poly 0b10011 --crc-width 4 simulate-awgn 10110100 --snr-db 4.0 --seed 7 --frame
python3 -m convolutional_codec --crc-poly 0b10011 --crc-width 4 --interleave-rows 2 --interleave-cols 14 simulate-bsc 10110100 --p 0.02 --frame
```

## Design notes

- The default trellis is the classic rate-1/2 `(7, 5)_8` code with constraint length 3.
- Soft decoding assumes BPSK mapping `0 -> +1` and `1 -> -1`.
- Punctured streams are depunctured with neutral erasures before Viterbi decoding.
- CRC is optional and can be enabled only when frame-level integrity checking is needed.

## Running tests

```bash
python3 -m unittest discover -s tests -v
```

## Example

```bash
python3 examples/basic_demo.py
```

## Known Issues (Resolved)

- **Punctured hard-decision decode could mis-handle truncated final puncturing cycles.** Fixed by depuncturing at trellis-symbol granularity and trimming incomplete final symbols safely.
- **AWGN + interleaver simulation discarded soft information during deinterleaving.** Fixed by allowing the block interleaver to round-trip real-valued samples directly.
- **`decode-soft` CLI accepted malformed comma lists like `1.0,,2.0`.** Fixed by stricter input validation.
