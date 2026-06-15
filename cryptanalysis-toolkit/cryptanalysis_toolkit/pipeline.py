"""Pipeline for batch cipher operations and file processing."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .ciphers import (
    CaesarCipher,
    SubstitutionCipher,
    VigenereCipher,
    AffineCipher,
    PlayfairCipher,
    RailFenceCipher,
    ColumnarTranspositionCipher,
    AutokeyCipher,
    BeaufortCipher,
    PortaCipher,
    XORCipher,
    EnigmaCipher,
    ROT13Cipher,
    AtbashCipher,
    HillCipher,
)
from .analysis import FrequencyAnalyzer, IndexOfCoincidence, KasiskiExaminer, NgramScorer
from .breaker import CipherBreaker

logger = logging.getLogger(__name__)

CIPHER_REGISTRY: Dict[str, type] = {
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


def build_cipher(name: str, **params: Any):
    """Construct a cipher instance from name and parameters.

    Args:
        name: Cipher name (case-insensitive).
        **params: Cipher-specific parameters.

    Returns:
        Cipher instance.

    Raises:
        ValueError: If cipher name is unknown or parameters are invalid.
    """
    name_lower = name.lower()
    if name_lower not in CIPHER_REGISTRY:
        raise ValueError(
            f"Unknown cipher: {name!r}. "
            f"Available: {', '.join(sorted(CIPHER_REGISTRY.keys()))}"
        )

    cls = CIPHER_REGISTRY[name_lower]

    # Map common parameter names to constructor arguments
    if name_lower == "caesar":
        return cls(shift=params.get("shift", params.get("key", 3)))
    elif name_lower == "substitution":
        if "key" in params:
            return cls(key=params["key"])
        elif "keyword" in params:
            return cls.from_keyword(params["keyword"])
        return cls()
    elif name_lower in ("vigenere", "autokey", "beaufort", "porta"):
        return cls(keyword=params.get("key", params.get("keyword", "KEY")))
    elif name_lower == "affine":
        return cls(a=params.get("a", 5), b=params.get("b", 8))
    elif name_lower == "playfair":
        return cls(keyword=params.get("key", params.get("keyword", "KEY")))
    elif name_lower == "railfence":
        return cls(rails=params.get("rails", params.get("key", 3)))
    elif name_lower == "columnar":
        return cls(key=params.get("key", params.get("keyword", "KEY")))
    elif name_lower == "xor":
        return cls(key=params.get("key", b"key"))
    elif name_lower == "enigma":
        return cls(
            rotor_order=params.get("rotors", [1, 2, 3]),
            initial_positions=params.get("positions", [0, 0, 0]),
            plugboard_pairs=params.get("plugboard", None),
            ring_settings=params.get("ring_settings", [0, 0, 0]),
        )
    elif name_lower == "rot13":
        return cls()
    elif name_lower == "atbash":
        return cls()
    elif name_lower == "hill":
        return cls(key_matrix=params.get("key_matrix", [[6, 24, 1], [13, 16, 10], [20, 17, 15]]))
    else:
        return cls(**params)


def load_config(path: Union[str, Path]) -> Dict:
    """Load a pipeline configuration from a YAML or JSON file.

    The config file should contain operation specifications like::

        operations:
          - cipher: caesar
            action: encrypt
            params:
              shift: 7
          - cipher: vigenere
            action: decrypt
            params:
              key: SECRET

    Args:
        path: Path to the YAML or JSON config file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the file format is unsupported.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    content = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(content)
    elif path.suffix == ".json":
        return json.loads(content)
    else:
        # Try YAML first, fall back to JSON
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return json.loads(content)


class CipherPipeline:
    """Execute a chain of cipher operations on text.

    A pipeline applies one or more cipher operations in sequence,
    passing the output of one as the input to the next. This is useful
    for compound encryption (e.g., Caesar then Vigenère) or for
    automated analysis workflows.

    Example::

        pipeline = CipherPipeline([
            {"cipher": "caesar", "action": "encrypt", "params": {"shift": 7}},
            {"cipher": "vigenere", "action": "encrypt", "params": {"key": "SECRET"}},
        ])
        result = pipeline.run("HELLO WORLD")
    """

    def __init__(self, operations: List[Dict], verbose: bool = False) -> None:
        """Initialize the pipeline with a list of operation specs.

        Args:
            operations: List of dicts, each with keys:
                - cipher: cipher name (str)
                - action: "encrypt" or "decrypt" (str)
                - params: cipher parameters (dict, optional)
            verbose: If True, log each step.
        """
        self.operations = operations
        self.verbose = verbose
        self._validate_operations()

    def _validate_operations(self) -> None:
        """Validate that all operations are well-formed."""
        for i, op in enumerate(self.operations):
            if "cipher" not in op:
                raise ValueError(f"Operation {i}: missing 'cipher' key")
            if "action" not in op:
                raise ValueError(f"Operation {i}: missing 'action' key")
            if op["action"] not in ("encrypt", "decrypt"):
                raise ValueError(
                    f"Operation {i}: action must be 'encrypt' or 'decrypt', "
                    f"got {op['action']!r}"
                )
            name = op["cipher"].lower()
            if name not in CIPHER_REGISTRY:
                raise ValueError(
                    f"Operation {i}: unknown cipher {op['cipher']!r}"
                )

    def run(self, text: str) -> str:
        """Execute all pipeline operations on the input text.

        Args:
            text: Input text to process.

        Returns:
            Result text after all operations have been applied.
        """
        current = text
        for op in self.operations:
            cipher = build_cipher(op["cipher"], **op.get("params", {}))
            action = op["action"]
            if action == "encrypt":
                current = cipher.encrypt(current)
            else:
                current = cipher.decrypt(current)
            if self.verbose:
                logger.info(
                    "Step [%s %s]: %s",
                    op["cipher"], action,
                    current[:80] + "..." if len(current) > 80 else current,
                )
        return current

    @classmethod
    def from_config(cls, path: Union[str, Path], verbose: bool = False) -> "CipherPipeline":
        """Create a pipeline from a configuration file.

        Args:
            path: Path to YAML or JSON config file.
            verbose: If True, log each step.

        Returns:
            CipherPipeline instance.
        """
        config = load_config(path)
        operations = config.get("operations", [])
        return cls(operations, verbose=verbose)


def process_file(
    input_path: Union[str, Path],
    operation: str,
    cipher_name: str,
    params: Dict,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Read a file, apply a cipher operation, and optionally write to a file.

    Args:
        input_path: Path to the input file.
        operation: "encrypt" or "decrypt".
        cipher_name: Name of the cipher to use.
        params: Cipher parameters.
        output_path: If provided, write result to this file.

    Returns:
        The result text.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = input_path.read_text(encoding="utf-8")
    cipher = build_cipher(cipher_name, **params)

    if operation == "encrypt":
        result = cipher.encrypt(text)
    elif operation == "decrypt":
        result = cipher.decrypt(text)
    else:
        raise ValueError(f"Operation must be 'encrypt' or 'decrypt', got {operation!r}")

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        logger.info("Result written to %s", output_path)

    return result


def analyze_text(text: str, top_n: int = 10, max_key_length: int = 20) -> Dict:
    """Run a comprehensive analysis on text and return structured results.

    Args:
        text: Text to analyze.
        top_n: Number of top frequency items to include.
        max_key_length: Maximum key length for IC/Kasiski analysis.

    Returns:
        Dictionary with analysis results including:
        - letter_frequencies, bigram_frequencies
        - ic, friedman_key_length
        - chi_squared, correlation
        - kasiski_candidates, ic_key_length_candidates
    """
    freq = FrequencyAnalyzer()
    ic_analyzer = IndexOfCoincidence()
    kasiski = KasiskiExaminer()

    letter_freqs = freq.letter_frequencies(text)
    bigram_freqs = freq.bigram_frequencies(text)

    # Sort for top_n
    sorted_letters = sorted(letter_freqs.items(), key=lambda x: x[1], reverse=True)[:top_n]
    sorted_bigrams = sorted(bigram_freqs.items(), key=lambda x: x[1], reverse=True)[:top_n]

    ic_value = ic_analyzer.calculate(text)
    friedman = ic_analyzer.friedman_test(text)
    chi_sq = freq.chi_squared(text)
    correlation = freq.frequency_correlation(text)
    ic_key_lengths = ic_analyzer.estimated_key_length(text, max_key_length)
    kasiski_results = kasiski.analyze(text, max_key_length)

    return {
        "letter_frequencies": dict(sorted_letters),
        "bigram_frequencies": dict(sorted_bigrams),
        "index_of_coincidence": round(ic_value, 6),
        "friedman_key_length": round(friedman, 2),
        "chi_squared": round(chi_sq, 2),
        "correlation": round(correlation, 4),
        "ic_key_length_candidates": [(kl, round(avg_ic, 6)) for kl, avg_ic in ic_key_lengths[:5]],
        "kasiski_candidates": [(kl, score) for kl, score in kasiski_results[:5]],
    }