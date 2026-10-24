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

This short input is accepted as a frame candidate but counted as rejected because its Ethernet header is truncated. As a library, call `decode_frame(bytes)` or `summarize(iterable_of_frames)`.

## Tests

Run `python3 -m unittest discover -s tests -v` from this directory. No third-party packages or network access are required.
