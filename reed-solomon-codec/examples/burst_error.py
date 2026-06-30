"""Burst-error correction with interleaving.

Block interleaving spreads a contiguous burst of errors across multiple
RS codewords, so each individual codeword sees at most one error from the
burst. With depth *d* and *nsym* parity, bursts of up to *d * (nsym//2)*
symbols can be corrected.
"""
from reed_solomon import encode_interleaved, decode_interleaved


def main():
    nsym = 6
    depth = 5
    message = b"Interleaving protects against long burst errors!"

    print(f"Message:  {message.decode()!r} ({len(message)} bytes)")
    print(f"nsym:     {nsym}, depth: {depth}")
    print(f"Without interleaving: max burst = {nsym // 2} symbols")
    print(f"With interleaving:    max burst = {depth * (nsym // 2)} symbols")
    print()

    # Encode with interleaving
    encoded = bytearray(encode_interleaved(message, nsym, depth))
    print(f"Encoded:  {len(encoded)} bytes")

    # Inject a burst of 15 errors (would be uncorrectable without interleaving)
    burst_start = 10
    burst_len = depth * (nsym // 2)  # = 15
    print(f"\nInjecting burst of {burst_len} errors at position {burst_start}")
    for i in range(burst_len):
        if burst_start + i < len(encoded):
            encoded[burst_start + i] ^= 0xFF

    # Decode
    recovered = decode_interleaved(bytes(encoded), nsym, depth, original_len=len(message))
    print(f"Recovered: {recovered.decode()!r}")
    print(f"\n✓ Success: burst of {burst_len} symbols corrected!" if recovered == message
          else "\n✗ Failed!")


if __name__ == "__main__":
    main()