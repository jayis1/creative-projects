"""Deterministic packet-capture teaching lab: decode bounded Ethernet/IPv4/UDP bytes."""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import struct
from typing import Iterable


class DecodeError(ValueError):
    """A packet is truncated or contains unsupported framing."""


@dataclass(frozen=True)
class Packet:
    source: str
    destination: str
    protocol: str
    source_port: int | None
    destination_port: int | None
    payload_length: int
    ttl: int


def _need(data: bytes, offset: int, size: int, label: str) -> bytes:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise DecodeError(f"truncated {label}")
    return data[offset:offset + size]


def decode_frame(frame: bytes) -> Packet:
    """Decode one Ethernet II IPv4 frame; reject fragments/non-UDP safely."""
    if len(frame) > 65535:
        raise DecodeError("frame exceeds 65535-byte safety limit")
    eth = _need(frame, 0, 14, "Ethernet header")
    ethertype = struct.unpack_from("!H", eth, 12)[0]
    if ethertype != 0x0800:
        raise DecodeError(f"unsupported EtherType 0x{ethertype:04x}")
    ip = _need(frame, 14, 20, "IPv4 header")
    version, ihl = ip[0] >> 4, (ip[0] & 15) * 4
    if version != 4 or ihl < 20:
        raise DecodeError("invalid IPv4 version or header length")
    ip = _need(frame, 14, ihl, "IPv4 options")
    total = struct.unpack_from("!H", ip, 2)[0]
    if total < ihl or total > len(frame) - 14:
        raise DecodeError("invalid IPv4 total length")
    flags_offset = struct.unpack_from("!H", ip, 6)[0]
    if flags_offset & 0x3fff:
        raise DecodeError("fragmented IPv4 packets are unsupported")
    proto = ip[9]
    src = ".".join(str(x) for x in ip[12:16])
    dst = ".".join(str(x) for x in ip[16:20])
    payload = total - ihl
    if proto == 17:
        udp = _need(frame, 14 + ihl, 8, "UDP header")
        sport, dport, ulen = struct.unpack_from("!HHH", udp)
        if ulen < 8 or ulen > payload:
            raise DecodeError("invalid UDP length")
        return Packet(src, dst, "UDP", sport, dport, ulen - 8, ip[8])
    return Packet(src, dst, f"IP-{proto}", None, None, payload, ip[8])


def summarize(frames: Iterable[bytes]) -> dict:
    """Summarize decoded frames without retaining payload bytes."""
    counts: dict[str, int] = {}
    flows: dict[str, int] = {}
    accepted = rejected = 0
    for frame in frames:
        try:
            p = decode_frame(frame)
        except DecodeError:
            rejected += 1
            continue
        accepted += 1
        counts[p.protocol] = counts.get(p.protocol, 0) + 1
        flow = f"{p.source}:{p.source_port or 0} -> {p.destination}:{p.destination_port or 0}"
        flows[flow] = flows.get(flow, 0) + 1
    return {"accepted": accepted, "rejected": rejected, "protocols": dict(sorted(counts.items())),
            "flows": dict(sorted(flows.items()))}


def demo_frame() -> bytes:
    """A tiny deterministic UDP/IPv4 Ethernet fixture (documentation demo)."""
    payload = b"hello"
    udp = struct.pack("!HHHH", 53000, 9000, 8 + len(payload), 0) + payload
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 7, 0, 64, 17, 0,
                     bytes((192, 0, 2, 1)), bytes((198, 51, 100, 2)))
    return bytes.fromhex("00112233445566778899aabb0800") + ip + udp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="decode the built-in sample")
    parser.add_argument("--hex", help="decode one Ethernet frame supplied as hex")
    args = parser.parse_args(argv)
    if args.demo:
        frames = [demo_frame()]
    elif args.hex:
        try:
            frames = [bytes.fromhex(args.hex)]
        except ValueError as exc:
            parser.error(f"invalid hex input: {exc}")
    else:
        parser.error("choose --demo or --hex")
    try:
        print(json.dumps(summarize(frames), indent=2, sort_keys=True))
    except DecodeError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
