"""Command-line interface for the Cryptanalysis Toolkit."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from .ciphers import (
    CaesarCipher, SubstitutionCipher, VigenereCipher, AffineCipher,
    PlayfairCipher, RailFenceCipher, ColumnarTranspositionCipher,
    AutokeyCipher, BeaufortCipher, PortaCipher,
    XORCipher, EnigmaCipher,
    ROT13Cipher, AtbashCipher, HillCipher,
)
from .analysis import FrequencyAnalyzer, IndexOfCoincidence, KasiskiExaminer, NgramScorer
from .breaker import CipherBreaker
from .pipeline import CipherPipeline, build_cipher, load_config, process_file, analyze_text

logger = logging.getLogger(__name__)

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
    "rot13": ROT13Cipher,
    "atbash": AtbashCipher,
    "hill": HillCipher,
}


def _get_input_text(args) -> str:
    """Resolve input text from args, checking for --file or positional text.

    Args:
        args: Parsed argparse namespace.

    Returns:
        The resolved text string.

    Raises:
        SystemExit: If neither text nor --file is provided.
    """
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")
    if args.text is not None:
        return args.text
    # Try reading from stdin if no text/file provided and stdin is a pipe
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    print("Error: No input text provided. Use positional text argument, --file, or pipe stdin.", file=sys.stderr)
    sys.exit(1)


def _get_output_writer(args):
    """Return a function that writes output appropriately.

    If --output is specified, writes to file. Otherwise writes to stdout.
    """
    if hasattr(args, 'output') and args.output:
        output_path = Path(args.output)
        def write(text: str) -> None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text, encoding="utf-8")
            logger.info("Output written to %s", output_path)
        return write
    else:
        return lambda text: print(text)


def _build_cipher_instance(cipher_name: str, args) -> object:
    """Build a cipher instance from cipher name and CLI args.

    Args:
        cipher_name: Lowercase cipher name.
        args: Parsed argparse namespace.

    Returns:
        Cipher instance.
    """
    cipher_cls = CIPHERS[cipher_name]

    if cipher_name == "caesar":
        return cipher_cls(shift=args.shift or 3)
    elif cipher_name == "substitution":
        if args.key:
            return cipher_cls(key=args.key)
        return cipher_cls.from_keyword(args.keyword or "SECRET")
    elif cipher_name in ("vigenere", "autokey", "beaufort", "porta"):
        if not args.key:
            print(f"Error: --key required for {cipher_name} cipher", file=sys.stderr)
            sys.exit(1)
        return cipher_cls(keyword=args.key)
    elif cipher_name == "affine":
        return cipher_cls(a=args.a or 5, b=args.b or 8)
    elif cipher_name == "playfair":
        if not args.key:
            print("Error: --key required for playfair cipher", file=sys.stderr)
            sys.exit(1)
        return cipher_cls(keyword=args.key)
    elif cipher_name == "railfence":
        return cipher_cls(rails=args.rails or 3)
    elif cipher_name == "columnar":
        if not args.key:
            print("Error: --key required for columnar transposition cipher", file=sys.stderr)
            sys.exit(1)
        return cipher_cls(key=args.key)
    elif cipher_name == "xor":
        if not args.key:
            print("Error: --key required for XOR cipher", file=sys.stderr)
            sys.exit(1)
        return cipher_cls(key=args.key)
    elif cipher_name == "enigma":
        return cipher_cls(
            rotor_order=args.rotors or [1, 2, 3],
            initial_positions=args.positions or [0, 0, 0],
            plugboard_pairs=_parse_plugboard(args.plugboard) if args.plugboard else None,
        )
    elif cipher_name == "rot13":
        return cipher_cls()
    elif cipher_name == "atbash":
        return cipher_cls()
    elif cipher_name == "hill":
        return cipher_cls(key_matrix=args.key_matrix or [[6, 24, 1], [13, 16, 10], [20, 17, 15]])
    else:
        return cipher_cls()


def _parse_plugboard(pairs_str: Optional[str]) -> Optional[list]:
    """Parse plugboard pairs from a string like 'AB,CD,EF'.

    Args:
        pairs_str: Comma-separated letter pairs.

    Returns:
        List of (letter1, letter2) tuples, or None.
    """
    if not pairs_str:
        return None
    pairs = []
    for pair in pairs_str.split(","):
        pair = pair.strip()
        if len(pair) != 2 or not pair.isalpha():
            print(f"Error: Invalid plugboard pair: {pair!r}. Expected two letters (e.g., 'AB').", file=sys.stderr)
            sys.exit(1)
        pairs.append((pair[0].upper(), pair[1].upper()))
    return pairs


def cmd_encrypt(args):
    """Handle encrypt command."""
    text = _get_input_text(args)
    cipher_name = args.cipher.lower()
    if cipher_name not in CIPHERS:
        print(f"Error: Unknown cipher: {args.cipher}. Available: {', '.join(sorted(CIPHERS.keys()))}", file=sys.stderr)
        sys.exit(1)
    cipher = _build_cipher_instance(cipher_name, args)
    result = cipher.encrypt(text)
    _get_output_writer(args)(result)


def cmd_decrypt(args):
    """Handle decrypt command."""
    text = _get_input_text(args)
    cipher_name = args.cipher.lower()
    if cipher_name not in CIPHERS:
        print(f"Error: Unknown cipher: {args.cipher}. Available: {', '.join(sorted(CIPHERS.keys()))}", file=sys.stderr)
        sys.exit(1)
    cipher = _build_cipher_instance(cipher_name, args)
    result = cipher.decrypt(text)
    _get_output_writer(args)(result)


def cmd_break_cipher(args):
    """Handle break command."""
    text = _get_input_text(args)
    breaker = CipherBreaker()

    if args.cipher == "auto":
        result = breaker.identify_cipher_type(text)
        print("Cipher type identification:")
        print(f"  IC: {result['ic']:.4f}")
        print(f"  Likely type: {result['likely_type']}")
        print()

        if result['ic'] > 0.055:
            print("Trying Caesar cipher...")
            caesar_results = breaker.break_caesar(text, top_n=3)
            for i, res in enumerate(caesar_results):
                print(f"  Shift {res['shift']}: correlation={res['correlation']:.4f}")
                print(f"    {res['plaintext'][:80]}...")
            print()

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
        print(f"Error: Unknown cipher type for breaking: {args.cipher}", file=sys.stderr)
        print("Available: caesar, affine, vigenere, substitution, auto", file=sys.stderr)
        sys.exit(1)


def cmd_analyze(args):
    """Handle analyze command."""
    text = _get_input_text(args)

    if args.json:
        # Structured JSON output
        result = analyze_text(text, top_n=args.top_n, max_key_length=args.max_key_length)
        output = json.dumps(result, indent=2, ensure_ascii=False)
        _get_output_writer(args)(output)
        return

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

    # Friedman test
    friedman = ic.friedman_test(text)
    print(f"Friedman test key length estimate: {friedman:.2f}")
    print()

    # IC-based key length estimation
    print("IC-based key length estimates:")
    ic_results = ic.estimated_key_length(text, max_length=args.max_key_length)
    for kl, avg_ic in ic_results[:5]:
        print(f"  Key length {kl:2d}: average IC = {avg_ic:.6f}")
    print()

    # Kasiski examination
    print(kasiski.kasiski_report(text, max_key_length=args.max_key_length))


def cmd_pipeline(args):
    """Handle pipeline command."""
    try:
        pipeline = CipherPipeline.from_config(args.config, verbose=args.verbose)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error in pipeline config: {e}", file=sys.stderr)
        sys.exit(1)

    # Get input text
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read().strip() if not sys.stdin.isatty() else ""

    if not text:
        print("Error: No input text provided for pipeline.", file=sys.stderr)
        sys.exit(1)

    result = pipeline.run(text)
    _get_output_writer(args)(result)


def cmd_list_ciphers(args):
    """List all available ciphers."""
    print("Available ciphers:")
    print()
    for name in sorted(CIPHERS.keys()):
        cls = CIPHERS[name]
        doc = (cls.__doc__ or "").strip().split("\n")[0]
        print(f"  {name:15s}  {doc}")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a subparser."""
    parser.add_argument("text", nargs="?", help="Input text")
    parser.add_argument("--file", "-f", help="Read input from file")
    parser.add_argument("--output", "-o", help="Write output to file")
    parser.add_argument("--key", "-k", help="Cipher key")
    parser.add_argument("--keyword", help="Keyword for substitution cipher derivation")
    parser.add_argument("--shift", "-s", type=int, help="Shift for Caesar cipher")
    parser.add_argument("--a", type=int, help="Affine 'a' parameter")
    parser.add_argument("--b", type=int, help="Affine 'b' parameter")
    parser.add_argument("--rails", type=int, help="Number of rails for rail fence")
    parser.add_argument("--rotors", nargs=3, type=int, help="Enigma rotor order (3 integers)")
    parser.add_argument("--positions", nargs=3, type=int, help="Enigma initial positions (3 integers)")
    parser.add_argument("--plugboard", help="Enigma plugboard pairs (e.g., 'AB,CD,EF')")
    parser.add_argument("--key-matrix", dest="key_matrix", help="Hill cipher key matrix as JSON")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="cryptanalysis-toolkit",
        description="Cryptanalysis Toolkit — Classical cipher tools and automatic breaking",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-essential output")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Encrypt
    enc = subparsers.add_parser("encrypt", help="Encrypt text")
    enc.add_argument("cipher", help="Cipher name (caesar, vigenere, rot13, etc.)")
    _add_common_args(enc)

    # Decrypt
    dec = subparsers.add_parser("decrypt", help="Decrypt text")
    dec.add_argument("cipher", help="Cipher name")
    _add_common_args(dec)

    # Break
    brk = subparsers.add_parser("break", help="Break a cipher")
    brk.add_argument("cipher", help="Cipher type (caesar, affine, vigenere, substitution, auto)")
    brk.add_argument("text", nargs="?", help="Ciphertext to break")
    brk.add_argument("--file", "-f", help="Read ciphertext from file")
    brk.add_argument("--output", "-o", help="Write results to file")
    brk.add_argument("--top-n", type=int, default=5, help="Number of top results")
    brk.add_argument("--max-key-length", type=int, default=20, help="Max key length for Vigenère")
    brk.add_argument("--iterations", type=int, default=5000, help="Iterations for substitution breaking")
    brk.add_argument("--restarts", type=int, default=5, help="Restarts for substitution breaking")

    # Analyze
    ana = subparsers.add_parser("analyze", help="Analyze ciphertext")
    ana.add_argument("text", nargs="?", help="Text to analyze")
    ana.add_argument("--file", "-f", help="Read text from file")
    ana.add_argument("--output", "-o", help="Write results to file")
    ana.add_argument("--top-n", type=int, default=10, help="Number of top items to show")
    ana.add_argument("--max-key-length", type=int, default=20, help="Max key length for analysis")
    ana.add_argument("--json", action="store_true", help="Output analysis as JSON")

    # Pipeline
    pipe = subparsers.add_parser("pipeline", help="Run a pipeline of cipher operations from a config file")
    pipe.add_argument("config", help="Path to YAML/JSON pipeline config file")
    pipe.add_argument("text", nargs="?", help="Input text")
    pipe.add_argument("--file", "-f", help="Read input from file")
    pipe.add_argument("--output", "-o", help="Write output to file")

    # List ciphers
    subparsers.add_parser("list", help="List all available ciphers")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    elif args.quiet:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.command == "encrypt":
        cmd_encrypt(args)
    elif args.command == "decrypt":
        cmd_decrypt(args)
    elif args.command == "break":
        cmd_break_cipher(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "list":
        cmd_list_ciphers(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()