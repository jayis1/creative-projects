# Fountain Code Lab

A dependency-free Python implementation of deterministic LT-style fountain packets. Split arbitrary bytes into fixed-size source blocks, emit reproducible XOR equations, and recover the original when packets contain enough singleton-derived information for peeling. It demonstrates the core rateless coding idea; it is not a production Raptor/RaptorQ implementation and does not promise recovery from every random packet set.

## How it works

The encoder zero-pads the final source block. A seeded pseudorandom generator picks a bounded degree and a unique set of block indices for each packet; the payload is the bytewise XOR of those blocks. The decoder repeatedly substitutes known blocks into equations and solves equations reduced to one unknown. If the remaining equations have no singleton, it reports rank deficiency rather than guessing.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
python3 fountain.py encode input.bin packets.json --block-size 128 --packets 30 --seed 42
python3 fountain.py decode packets.json recovered.bin
cmp input.bin recovered.bin
```

The JSON packet file carries block count, original byte length, block size, packet indices, and hex payloads. Encode is deterministic for a fixed input and seed. Decode rejects malformed packets, inconsistent equations, and unsolved systems.

Run tests from this directory:

```sh
python3 -m unittest discover -s tests -v
```

The CLI enforces maximum dimensions and packet counts. Packets are untrusted input; the JSON format is not authenticated, and decoder memory/runtime scale with packet count and payload size. Do not treat these educational packets as secure or production-grade error correction.
