"""Command-line interface for the Cryptanalysis Toolkit."""

from __future__ import annotations
import argparse
import sys
from .ciphers import (
    CaesarCipher, SubstitutionCipher, VigenereCipher, AffineCipher,
    PlayfairCipher, RailFenceCipher, ColumnarTranspositionCipher,
    AutokeyCipher, BeaufortCipher, PortaCipher,
    XORCipher, EnigmaCipher,
)
from .analysis import FrequencyAnalyzer, IndexOfCoincidence, KasiskiExaminer, NgramScorer
from .breaker import CipherBreaker


CIPHERS = {
    "caesar": CaesarCipher,
    "substitution": SubstitutionCipher,
    "vigenere": VigenereCipher,
    "affine": AffineCipher,
    "playfair": PlayfairCipher,
    "railfence": RailFenceCipher,
    "columnar": ColumnarTranspositionCipher,
    "autokey": AutokeyCipher,
    "beaufort": BeaufortCipher,
    "porta": PortaCipher,
    "xor": XORCipher,
    "enigma": EnigmaCipher,
}


def cmd_encrypt(args):
    """Handle encrypt command."""
    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()

    cipher_name = args.cipher.lower()
    if cipher_name not in CIPHERS:
        print(f"Unknown cipher: {args.cipher}. Available: {', '.join(CIPHERS.keys())}")
        sys.exit(1)

    cipher_cls = CIPHERS[cipher_name]

    # Create cipher instance based on type
    if cipher_name == "caesar":
        cipher = cipher_cls(shift=args.shift or 3)
    elif cipher_name == "substitution":
        cipher = cipher_cls(key=args.key) if args.key else cipher_cls.from_keyword(args.keyword or "SECRET")
    elif cipher_name in ("vigenere", "autokey", "beaufort", "porta"):
        if not args.key:
            print(f"--key required for {cipher_name} cipher")
            sys.exit(1)
        cipher = cipher_cls(keyword=args.key)
    elif cipher_name == "affine":
        a = args.a or 5
        b = args.b or 8
        cipher = cipher_cls(a=a, b=b)
    elif cipher_name == "playfair":
        if not args.key:
            print("--key required for playfair cipher")
            sys.exit(1)
        cipher = cipher_cls(keyword=args.key)
    elif cipher_name == "railfence":
        cipher = cipher_cls(rails=args.rails or 3)
    elif cipher_name == "columnar":
        if not args.key:
            print("--key required for columnar transposition cipher")
            sys.exit(1)
        cipher = cipher_cls(key=args.key)
    elif cipher_name == "xor":
        if not args.key:
            print("--key required for XOR cipher")
            sys.exit(1)
        cipher = cipher_cls(key=args.key)
    elif cipher_name == "enigma":
        cipher = cipher_cls(
            rotor_order=args.rotors or [1, 2, 3],
            initial_positions=args.positions or [0, 0, 0],
        )

    result = cipher.encrypt(text)
    print(result)
def cmd_decrypt(args):
    """Handle decrypt command."""
    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()

    cipher_name = args.cipher.lower()
    if cipher_name not in CIPHERS:
        print(f"Unknown cipher: {args.cipher}. Available: {', '.join(CIPHERS.keys())}")
        sys.exit(1)

    cipher_cls = CIPHERS[cipher_name]

    if cipher_name == "caesar":
        cipher = cipher_cls(shift=args.shift or 3)
    elif cipher_name == "substitution":
        cipher = cipher_cls(key=args.key) if args.key else cipher_cls.from_keyword(args.keyword or "SECRET")
    elif cipher_name in ("vigenere", "autokey", "beaufort", "porta"):
        if not args.key:
            print(f"--key required for {cipher_name} cipher")
            sys.exit(1)
        cipher = cipher_cls(keyword=args.key)
    elif cipher_name == "affine":
        a = args.a or 5
        b = args.b or 8
        cipher = cipher_cls(a=a, b=b)
    elif cipher_name == "playfair":
        if not args.key:
            print("--key required for playfair cipher")
            sys.exit(1)
        cipher = cipher_cls(keyword=args.key)
    elif cipher_name == "railfence":
        cipher = cipher_cls(rails=args.rails or 3)
    elif cipher_name == "columnar":
        if not args.key:
            print("--key required for columnar transposition cipher")
            sys.exit(1)
        cipher = cipher_cls(key=args.key)
    elif cipher_name == "xor":
        if not args.key:
            print("--key required for XOR cipher")
            sys.exit(1)
        cipher = cipher_cls(key=args.key)
    elif cipher_name == "enigma":
        cipher = cipher_cls(
            rotor_order=args.rotors or [1, 2, 3],
            initial_positions=args.positions or [0, 0, 0],
        )

    result = cipher.decrypt(text)
    print(result)


def cmd_break_cipher(args):
    """Handle break command."""
    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()

    breaker = CipherBreaker()

    if args.cipher == "auto":
        # Try to identify the cipher type first
        result = breaker.identify_cipher_type(text)
        print(f"Cipher type identification:")
        print(f"  IC: {result['ic']:.4f}")
        print(f"  Likely type: {result['likely_type']}")
        print()

        # Try breaking as Caesar first (fastest)
        if result['ic'] > 0.055:
            print("Trying Caesar cipher...")
            caesar_results = breaker.break_caesar(text, top_n=3)
            for i, res in enumerate(caesar_results):
                print(f"  Shift {res['shift']}: correlation={res['correlation']:.4f}")
                print(f"    {res['plaintext'][:80]}...")
            print()

        # Try Vigenère
        print("Trying Vigenère cipher...")
        vig_results = breaker.break_vigenere(text, max_key_length=args.max_key_length, top_n=3)
        for i, res in enumerate(vig_results):
            print(f"  Key '{res['key']}' (length {res['key_length']}): score={res['score']:.4f}")
            print(f"    {res['plaintext'][:80]}...")
        print()

    elif args.cipher == "caesar":
        results = breaker.break_caesar(text, top_n=args.top_n)
        print(f"Top {len(results)} Caesar cipher decryptions:")
        for i, res in enumerate(results):
            print(f"\n  #{i+1}: Shift={res['shift']}, Correlation={res['correlation']:.4f}")
            print(f"  {res['plaintext'][:100]}")

    elif args.cipher == "affine":
        results = breaker.break_affine(text, top_n=args.top_n)
        print(f"Top {len(results)} Affine cipher decryptions:")
        for i, res in enumerate(results):
            print(f"\n  #{i+1}: a={res['a']}, b={res['b']}, Correlation={res['correlation']:.4f}")
            print(f"  {res['plaintext'][:100]}")

    elif args.cipher == "vigenere":
        results = breaker.break_vigenere(text, max_key_length=args.max_key_length, top_n=args.top_n)
        print(f"Top {len(results)} Vigenère cipher decryptions:")
        for i, res in enumerate(results):
            print(f"\n  #{i+1}: Key='{res['key']}' (length {res['key_length']}), Score={res['score']:.4f}")
            print(f"  {res['plaintext'][:100]}")

    elif args.cipher == "substitution":
        print("Breaking substitution cipher (this may take a moment)...")
        result = breaker.break_substitution(text, iterations=args.iterations, restarts=args.restarts)
        print(f"\nBest result (score={result['score']:.4f}):")
        print(f"  Key: {result['key']}")
        print(f"  Plaintext: {result['plaintext'][:200]}")

    else:
        print(f"Unknown cipher type for breaking: {args.cipher}")
        print("Available: caesar, affine, vigenere, substitution, auto")
        sys.exit(1)


def cmd_analyze(args):
    """Handle analyze command."""
    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()

    freq = FrequencyAnalyzer()
    ic = IndexOfCoincidence()
    kasiski = KasiskiExaminer()

    # Frequency analysis
    print(freq.frequency_report(text, top_n=args.top_n))
    print()

    # Index of Coincidence
    ic_value = ic.calculate(text)
    print(f"Index of Coincidence: {ic_value:.6f}")
    print(f"  English expected: 0.0667")
    print(f"  Random expected:  0.0385")
    print()

    # IC-based key length estimation
    print("IC-based key length estimates:")
    ic_results = ic.estimated_key_length(text, max_length=args.max_key_length)
    for kl, avg_ic in ic_results[:5]:
        print(f"  Key length {kl:2d}: average IC = {avg_ic:.6f}")
    print()

    # Kasiski examination
    print(kasiski.kasiski_report(text, max_key_length=args.max_key_length))


def main():
    parser = argparse.ArgumentParser(
        prog="cryptanalysis-toolkit",
        description="Cryptanalysis Toolkit — Classical cipher tools and automatic breaking",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Encrypt
    enc = subparsers.add_parser("encrypt", help="Encrypt text")
    enc.add_argument("cipher", help="Cipher name (caesar, substitution, vigenere, etc.)")
    enc.add_argument("text", nargs="?", help="Text to encrypt")
    enc.add_argument("--file", "-f", help="Read text from file")
    enc.add_argument("--key", "-k", help="Cipher key")
    enc.add_argument("--keyword", help="Keyword for substitution cipher")
    enc.add_argument("--shift", "-s", type=int, help="Shift for Caesar cipher")
    enc.add_argument("--a", type=int, help="Affine 'a' parameter")
    enc.add_argument("--b", type=int, help="Affine 'b' parameter")
    enc.add_argument("--rails", type=int, help="Number of rails for rail fence")

    # Decrypt
    dec = subparsers.add_parser("decrypt", help="Decrypt text")
    dec.add_argument("cipher", help="Cipher name")
    dec.add_argument("text", nargs="?", help="Text to decrypt")
    dec.add_argument("--file", "-f", help="Read text from file")
    dec.add_argument("--key", "-k", help="Cipher key")
    dec.add_argument("--keyword", help="Keyword for substitution cipher")
    dec.add_argument("--shift", "-s", type=int, help="Shift for Caesar cipher")
    dec.add_argument("--a", type=int, help="Affine 'a' parameter")
    dec.add_argument("--b", type=int, help="Affine 'b' parameter")
    dec.add_argument("--rails", type=int, help="Number of rails for rail fence")

    # Break
    brk = subparsers.add_parser("break", help="Break a cipher")
    brk.add_argument("cipher", help="Cipher type (caesar, affine, vigenere, substitution, auto)")
    brk.add_argument("text", nargs="?", help="Ciphertext to break")
    brk.add_argument("--file", "-f", help="Read ciphertext from file")
    brk.add_argument("--top-n", type=int, default=5, help="Number of top results")
    brk.add_argument("--max-key-length", type=int, default=20, help="Max key length for Vigenère")
    brk.add_argument("--iterations", type=int, default=5000, help="Iterations for substitution breaking")
    brk.add_argument("--restarts", type=int, default=5, help="Restarts for substitution breaking")

    # Analyze
    ana = subparsers.add_parser("analyze", help="Analyze ciphertext")
    ana.add_argument("text", nargs="?", help="Text to analyze")
    ana.add_argument("--file", "-f", help="Read text from file")
    ana.add_argument("--top-n", type=int, default=10, help="Number of top items to show")
    ana.add_argument("--max-key-length", type=int, default=20, help="Max key length for analysis")

    args = parser.parse_args()

    if args.command == "encrypt":
        cmd_encrypt(args)
    elif args.command == "decrypt":
        cmd_decrypt(args)
    elif args.command == "break":
        cmd_break_cipher(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()