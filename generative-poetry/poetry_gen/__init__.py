"""Generative Poetry Engine — procedural poem generation for multiple forms."""

from .engine import PoetryEngine
from .vocabulary import Vocabulary
from .syllables import syllable_count
from .rhyme import rhymes

__version__ = "1.0.0"
__all__ = ["PoetryEngine", "Vocabulary", "syllable_count", "rhymes"]
