"""Erasure correction example.

Erasures are errors with known positions (e.g., a scratched CD where
the read head knows which sectors failed). Erasures are "cheaper" to
correct than unknown errors: nsym erasures vs nsym/2 errors.
"""
from reed_solomon import RSCode


def main():
    rs = RSCode(nsym=10)
    message = list(b"Erasure demo data!!")
    codeword = rs.encode(message)

    print(f"Message:   {bytes(message).decode()!r}")
    print(f"Codeword:  {len(codeword)} bytes")
    print(f"Max errors:   {rs.max_errors}")
    print(f"Max erasures: {rs.max_erasures}")
    print()

    # Erase 8 symbols (would need 16 parity for error correction,
    # but only 10 for erasure correction since positions are known)
    erasures = [0, 1, 5, 8, 12, 15, 17, 19]
    corrupted = list(codeword)
    for pos in erasures:
        if pos < len(corrupted):
            corrupted[pos] = 0  # value doesn't matter, position is known

    print(f"Erased {len(erasures)} positions: {erasures}")
    print(f"(That's {len(erasures)} erasures — only {rs.max_errors} unknown errors would be correctable!)")

    result = rs.decode_detailed(corrupted, erasures=erasures)
    print(f"\nSuccess:       {result.success}")
    print(f"Corrections:   {len(result.error_positions) + len(result.erasure_positions)}")
    print(f"Recovered:      {bytes(result.corrected[rs.nsym:]).decode()!r}")


if __name__ == "__main__":
    main()