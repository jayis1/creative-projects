#!/usr/bin/env python3
"""Deterministic LT-style fountain packets and bounded XOR peeling decoder."""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path


def encode(data: bytes, block_size: int, packets: int, seed: int = 0, systematic: bool = False) -> list[dict]:
    if block_size < 1 or packets < 0:
        raise ValueError("block_size must be positive and packets nonnegative")
    count = max(1, (len(data) + block_size - 1) // block_size)
    if count > 100_000 or packets > 1_000_000:
        raise ValueError("input exceeds configured limits")
    blocks = [data[i * block_size:(i + 1) * block_size].ljust(block_size, b"\0") for i in range(count)]
    rng = random.Random(seed)
    result = []
    for ident in range(packets):
        if systematic and ident < count:
            indexes = [ident]
        else:
            degree = 1 if count == 1 else rng.randint(1, min(count, max(2, int(count ** .5))))
            indexes = sorted(rng.sample(range(count), degree))
        payload = bytearray(block_size)
        for idx in indexes:
            for j, value in enumerate(blocks[idx]):
                payload[j] ^= value
        result.append({"id": ident, "indices": indexes, "payload": bytes(payload).hex()})
    return result


def decode(packets: list[dict], block_count: int, original_size: int, block_size: int) -> bytes:
    if not 1 <= block_count <= 100_000 or not 1 <= block_size <= 16_777_216:
        raise ValueError("invalid block dimensions")
    if not 0 <= original_size <= block_count * block_size or original_size <= (block_count - 1) * block_size:
        raise ValueError("original_size inconsistent with dimensions")
    if len(packets) > 1_000_000:
        raise ValueError("too many packets")
    equations = []
    for packet in packets:
        inds = packet.get("indices")
        try:
            payload = bytes.fromhex(packet["payload"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid packet payload") from exc
        if not isinstance(inds, list) or not inds or len(set(inds)) != len(inds) or any(type(i) is not int or not 0 <= i < block_count for i in inds):
            raise ValueError("invalid packet indices")
        if len(payload) != block_size:
            raise ValueError("packet payload has wrong size")
        equations.append((set(inds), bytearray(payload)))
    solved: dict[int, bytes] = {}
    while True:
        progress = False
        reduced = []
        for indices, payload in equations:
            indices = set(indices)
            for known, block in solved.items():
                if known in indices:
                    indices.remove(known)
                    for j, value in enumerate(block):
                        payload[j] ^= value
            if not indices:
                if any(payload):
                    raise ValueError("inconsistent packets")
            elif len(indices) == 1:
                idx = next(iter(indices))
                solved[idx] = bytes(payload)
                progress = True
            else:
                reduced.append((indices, payload))
        equations = reduced
        if len(solved) == block_count:
            return b"".join(solved[i] for i in range(block_count))[:original_size]
        if not progress:
            raise ValueError(f"insufficient independent packets: recovered {len(solved)}/{block_count} blocks")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    enc = sub.add_parser("encode"); enc.add_argument("input"); enc.add_argument("output"); enc.add_argument("--block-size", type=int, default=64); enc.add_argument("--packets", type=int); enc.add_argument("--seed", type=int, default=0); enc.add_argument("--systematic", action="store_true", help="emit each source block as an initial packet")
    dec = sub.add_parser("decode"); dec.add_argument("packets"); dec.add_argument("output")
    args = parser.parse_args()
    if args.command == "encode":
        data = Path(args.input).read_bytes()
        count = max(1, (len(data) + args.block_size - 1) // args.block_size)
        rows = encode(data, args.block_size, args.packets if args.packets is not None else count * 3, args.seed, args.systematic)
        Path(args.output).write_text(json.dumps({"block_count": count, "original_size": len(data), "block_size": args.block_size, "packets": rows}, separators=(",", ":")), encoding="utf-8")
    else:
        obj = json.loads(Path(args.packets).read_text(encoding="utf-8"))
        result = decode(obj["packets"], obj["block_count"], obj["original_size"], obj["block_size"])
        Path(args.output).write_bytes(result)

if __name__ == "__main__":
    main()
