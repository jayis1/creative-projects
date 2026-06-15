"""
Cryptanalysis Toolkit — Classical cipher implementations and automatic breaking.

A comprehensive framework for implementing, analyzing, and breaking classical
ciphers using statistical methods including frequency analysis, Kasiski
examination, index of coincidence, and hill climbing.
"""

__version__ = "1.1.0"

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

__all__ = [
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
    "FrequencyAnalyzer",
    "IndexOfCoincidence",
    "KasiskiExaminer",
    "NgramScorer",
    "PatternMatcher",
    "word_pattern",
    "CipherBreaker",
]