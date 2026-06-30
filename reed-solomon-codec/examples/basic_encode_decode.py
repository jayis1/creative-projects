"""Basic encode/decode example.

Demonstrates the simplest usage of the Reed-Solomon codec:
encoding a message, corrupting it, and recovering it.
"""
from reed_solomon import RSCode


def main():
    rs = RSCode(nsym=10)
    print(rs)
    print()

    # Encode a message
    message = list(b"Hello, Reed-Solomon!")
    codeword = rs.encode(message)
    print(f"Message:   {bytes(message).decode()!r} ({len(message)} bytes)")
    print(f"Codeword:  {len(codeword)} bytes (message + {rs.nsym} parity)")

    # Introduce 3 random errors (max correctable: 5)
    corrupted = list(codeword)
    for pos in [2, 10, 18]:
        corrupted[pos] ^= 0x55
    print(f"\nCorrupted 3 positions: [2, 10, 18]")

    # Decode and correct
    result = rs.decode_detailed(corrupted)
    print(f"Success:        {result.success}")
    print(f"Errors fixed:  {result.errors_corrected}")
    print(f"At positions:  {result.error_positions}")
    print(f"\nRecovered:  {bytes(result.corrected[rs.nsym:]).decode()!r}")


if __name__ == "__main__":
    main()