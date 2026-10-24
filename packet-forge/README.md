# Packet Forge

Packet Forge is a dependency-free, deterministic teaching decoder for bounded Ethernet II / IPv4 traffic. It turns raw frames into compact flow and protocol summaries without storing payloads. This is an offline parser, not a live capture tool.

## Try it

```sh
python3 packet_forge.py --demo
```

The demo reports one UDP frame from `192.0.2.1:53000` to `198.51.100.2:9000`, with five payload bytes.

## How it works

The decoder checks Ethernet framing, IPv4 version/header length/total length and fragmentation, then validates UDP's declared length before exposing metadata. `DecodeError` rejects malformed or unsupported frames. `summarize` aggregates protocol and endpoint counts while discarding input buffers after each frame. Parsing is linear in frame size and the largest accepted frame is 65,535 bytes.

## Usage

Decode a frame represented as hexadecimal:

```sh
python3 packet_forge.py --hex 00112233445566778899aabb0800
```

Read a classic Ethernet pcap capture:

```sh
python3 packet_forge.py --pcap capture.pcap
```

The pcap reader supports classic pcap v2.4 in either byte order, requires Ethernet link type, caps files at 64 MiB and frames at 10,000 by default, and rejects truncated/oversized records. It does not support pcapng, VLAN-tagged IPv4, IPv6, or fragmented IPv4.

## Tests

Run `python3 -m unittest discover -s tests -v` from this directory. No third-party packages or network access are required.

## Known Issues (Resolved)

The Phase 3 adversarial review found no reproducible implementation defects. No bug fixes are claimed. Added regression coverage for malformed pcap lengths, capture record truncation, IPv4 fragments, and invalid UDP lengths. Remaining unsupported formats and protocols are listed above.
