"""BPE Tokenizer — a from-scratch Byte Pair Encoding tokenizer for NLP."""

from .tokenizer import BPETokenizer, TrainingConfig, TokenizationResult, TokenizerStats
from .encoder import BPESentencePiece, UnigramScore, bpe_dropout, viterbi_segment
from .vocab import Vocab, Token, SpecialToken
from .pretokenize import (
    RegexPattern,
    WhitespacePretokenizer,
    WordPretokenizer,
    BytePretokenizer,
    GPT2_REGEX,
    GPT4_REGEX,
    LLAMA3_REGEX,
)
from .cache import EncodeCache
from .normalizer import Normalization, Normalizer
from .postprocess import TruncationStrategy, truncate, make_attention_mask, strip_specials
from .analyzer import TokenizerAnalyzer, AnalysisResult

__version__ = "2.0.0"

__all__ = [
    # Core
    "BPETokenizer",
    "TrainingConfig",
    "TokenizationResult",
    "TokenizerStats",
    # Advanced encoders
    "BPESentencePiece",
    "UnigramScore",
    "bpe_dropout",
    "viterbi_segment",
    # Vocab
    "Vocab",
    "Token",
    "SpecialToken",
    # Pre-tokenizers
    "RegexPattern",
    "WhitespacePretokenizer",
    "WordPretokenizer",
    "BytePretokenizer",
    "GPT2_REGEX",
    "GPT4_REGEX",
    "LLAMA3_REGEX",
    # Cache
    "EncodeCache",
    # Normalization
    "Normalization",
    "Normalizer",
    # Post-processing
    "TruncationStrategy",
    "truncate",
    "make_attention_mask",
    "strip_specials",
    # Analysis
    "TokenizerAnalyzer",
    "AnalysisResult",
]