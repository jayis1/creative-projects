"""
Cryptanalysis Toolkit — Classical cipher implementations and automatic breaking.

A comprehensive framework for implementing, analyzing, and breaking classical
ciphers using statistical methods including frequency analysis, Kasiski
examination, index of coincidence, and hill climbing.
"""

__version__ = "2.0.0"

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
    BaseCipher,
)
from .analysis import (
    FrequencyAnalyzer,
    IndexOfCoincidence,
    KasiskiExaminer,
    NgramScorer,
    PatternMatcher,
    word_pattern,
)
from .breaker import CipherBreaker
from .pipeline import (
    CipherPipeline,
    build_cipher,
    load_config,
    process_file,
    analyze_text,
    CIPHER_REGISTRY,
)

__all__ = [
    # Ciphers
    "CaesarCipher",
    "SubstitutionCipher",
    "VigenereCipher",
    "AffineCipher",
    "PlayfairCipher",
    "RailFenceCipher",
    "ColumnarTranspositionCipher",
    "AutokeyCipher",
    "BeaufortCipher",
    "PortaCipher",
    "XORCipher",
    "EnigmaCipher",
    "ROT13Cipher",
    "AtbashCipher",
    "HillCipher",
    "BaseCipher",
    # Analysis
    "FrequencyAnalyzer",
    "IndexOfCoincidence",
    "KasiskiExaminer",
    "NgramScorer",
    "PatternMatcher",
    "word_pattern",
    # Breaking
    "CipherBreaker",
    # Pipeline
    "CipherPipeline",
    "build_cipher",
    "load_config",
    "process_file",
    "analyze_text",
    "CIPHER_REGISTRY",
]