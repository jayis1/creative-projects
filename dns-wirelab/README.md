# DNS Wirelab

A standard-library, offline DNS wire-format workbench: build deterministic query packets and inspect responses without making network requests. It is aimed at protocol learners, packet-fixture authors, and debugging tools that need explainable bytes.

## Why this exists

DNS tools usually hide the bytes behind a resolver. DNS Wirelab exposes the header, questions, compression pointers, and common records so small packet fixtures can be understood and tested locally.

## How it works

The encoder writes DNS labels and a question header. The decoder validates header/section bounds, follows compression pointers with cycle protection, and decodes A, AAAA, name, and TXT records; unknown RDATA is shown as hex. It never sends packets.

## Quick start

From this directory:

```sh
python3 dns_wirelab.py query example.com --type A
```

Inspect a packet with `python3 dns_wirelab.py inspect <hex>`. For example, this valid empty response is decoded as JSON:

```sh
python3 dns_wirelab.py inspect 123481800000000000000000
```

## Tests

`python3 -m unittest -v`

## Limitations

This is a wire-format teaching and fixture tool, not a resolver or a complete DNSSEC implementation. It decodes common record types and renders other record payloads as hex. It rejects trailing data and malformed compression rather than attempting recovery.
