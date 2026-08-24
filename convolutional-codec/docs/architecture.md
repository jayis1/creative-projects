# Architecture

`convolutional-codec` is organized as a small research toolkit rather than a single script.

## Modules

- `convolutional_codec.codec`: trellis model, encoder, Viterbi decoder, framing helpers, and channel simulation entry points.
- `convolutional_codec.channels`: BSC, AWGN, and Gilbert-Elliott channel models plus BPSK helpers.
- `convolutional_codec.interleaver`: block interleaver implementation that works with bit and real-valued sample streams.
- `convolutional_codec.crc`: frame-level CRC computation and validation.
- `convolutional_codec.analysis`: free-distance estimation and Monte Carlo benchmark sweeps.
- `convolutional_codec.config`: JSON/TOML config loading for reproducible CLI runs.
- `convolutional_codec.cli`: thin orchestration layer over the library API.

## Data flow

1. Build a `Trellis` from octal generator polynomials.
2. Wrap it in a `ConvolutionalCodec` with an optional puncturing pattern.
3. Optionally append CRC bits and interleave the resulting coded stream.
4. Pass the stream through a channel model.
5. Optionally deinterleave and depuncture the noisy observations.
6. Run hard- or soft-decision Viterbi decoding.
7. Verify the CRC and summarize BER/FER metrics.

## Benchmarking

The benchmarking helpers generate repeated channel trials and aggregate:

- total decoded bits
- bit error count / BER
- frame error count / FER
- CRC failures when framing is enabled

This makes the project useful both as a teaching aid and as a lightweight experimentation harness.
