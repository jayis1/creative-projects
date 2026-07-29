"""BPE Tokenizer — a from-scratch Byte Pair Encoding tokenizer for NLP."""

from .tokenizer import BPETokenizer, TrainingConfig, TokenizationResult, TokenizerStats
from .encoder import BPESentencePiece, UnigramScore, bpe_dropout, viterbi_segment
from .wordpiece import WordPieceEncoder, wordpiece_encode
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
from .comparison import TokenizerComparison, ComparisonResult
from .config import TokenizerConfig, load_config, save_config
from .progress import ProgressInfo, ProgressCallback, create_print_callback
from .exceptions import (
    BPETokenizerError,
    TrainingError,
    EncodingError,
    DecodingError,
    SerializationError,
    ConfigError,
    VocabError,
)

__version__ = "3.0.0"

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
    # WordPiece
    "WordPieceEncoder",
    "wordpiece_encode",
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
    # Comparison
    "TokenizerComparison",
    "ComparisonResult",
    # Config
    "TokenizerConfig",
    "load_config",
    "save_config",
    # Progress
    "ProgressInfo",
    "ProgressCallback",
    "create_print_callback",
    # Exceptions
    "BPETokenizerError",
    "TrainingError",
    "EncodingError",
    "DecodingError",
    "SerializationError",
    "ConfigError",
    "VocabError",
]