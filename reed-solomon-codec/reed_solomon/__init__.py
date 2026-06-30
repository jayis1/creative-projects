"""reed-solomon — A from-scratch Reed-Solomon error-correcting code library.

Pure-Python implementation of Reed-Solomon codes over GF(2^8) with
systematic encoding, Berlekamp-Massey error locator, Chien search,
Forney algorithm, erasure correction, interleaving for burst errors,
logging, configuration, and a comprehensive CLI.
"""
from __future__ import annotations

__version__ = "2.0.0"
__author__ = "Creative Projects"
__license__ = "MIT"

from .gf import GF256, gf_poly_add, gf_poly_div, gf_poly_eval, gf_poly_mul, gf_poly_scale
from .codec import (
    DecodeResult,
    RSCode,
    berlekamp_massey,
    calc_syndromes,
    chien_search,
    decode,
    decode_interleaved,
    decode_message,
    deinterleave,
    encode,
    encode_interleaved,
    encode_message,
    forney,
    generator_poly,
    interleave,
    rs_decode,
    rs_decode_detailed,
    rs_encode,
)
from .config import CodecConfig, load_config

__all__ = [
    # version
    "__version__",
    # GF arithmetic
    "GF256",
    "gf_poly_add",
    "gf_poly_div",
    "gf_poly_eval",
    "gf_poly_mul",
    "gf_poly_scale",
    # codec
    "RSCode",
    "DecodeResult",
    "rs_encode",
    "rs_decode",
    "rs_decode_detailed",
    "generator_poly",
    "calc_syndromes",
    "berlekamp_massey",
    "chien_search",
    "forney",
    "encode",
    "decode",
    "encode_message",
    "decode_message",
    "interleave",
    "deinterleave",
    "encode_interleaved",
    "decode_interleaved",
    # config
    "CodecConfig",
    "load_config",
]