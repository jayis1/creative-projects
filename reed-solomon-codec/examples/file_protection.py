"""File protection example — encode a file, corrupt bytes, recover.

This simulates a real-world use case: protecting a file against data
corruption by adding RS parity, then recovering it after damage.

Since GF(2^8) limits codewords to 255 symbols, this example splits
the data into blocks and uses interleaving for burst-error protection.
"""
from reed_solomon import encode_interleaved, decode_interleaved


def main():
    nsym = 20      # 20 parity bytes → can correct up to 10 random errors per block
    depth = 4      # 4-way interleaving → bursts of up to 40 symbols correctable

    # Create some "original" data (larger than 255 bytes)
    original = b"The quick brown fox jumps over the lazy dog. " * 10
    print(f"Original: {len(original)} bytes")
    print(f"nsym:     {nsym} (max correctable errors per block: {nsym // 2})")
    print(f"depth:    {depth} (max burst: {depth * (nsym // 2)} symbols)")

    # Encode with interleaving
    encoded = bytearray(encode_interleaved(original, nsym, depth))
    print(f"Encoded:  {len(encoded)} bytes (interleaved)")

    # Simulate file corruption — 8 random byte errors
    error_positions = [5, 30, 55, 80, 105, 130, 155, 180]
    for pos in error_positions:
        if pos < len(encoded):
            encoded[pos] ^= 0xFF
    print(f"\nCorrupted 8 bytes at positions: {error_positions}")

    # Recover
    recovered = decode_interleaved(bytes(encoded), nsym, depth, original_len=len(original))
    print(f"Recovered: {len(recovered)} bytes")
    print(f"\n✓ Data perfectly recovered!" if recovered == original
          else "\n✗ Recovery failed!")

    # Show that the codec detects when there are too many errors
    print("\n--- Testing error detection ---")
    too_many = bytearray(encode_interleaved(original, nsym, depth))
    for i in range(50):  # 50 errors spread across — too many for some blocks
        if i < len(too_many):
            too_many[i] ^= 0xFF
    try:
        decode_interleaved(bytes(too_many), nsym, depth, original_len=len(original))
        print("✗ Should have raised an error!")
    except ValueError as e:
        print(f"✓ Correctly detected uncorrectable errors: {type(e).__name__}")


if __name__ == "__main__":
    main()