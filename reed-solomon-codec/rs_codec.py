"""Backward-compatibility shim — re-exports from reed_solomon.codec.

New code should import from ``reed_solomon`` directly:
    from reed_solomon import RSCode, rs_encode, rs_decode
"""
from reed_solomon.codec import (  # noqa: F401
    DecodeResult,
    RSCode,
    berlekamp_massey,
    calc_syndromes,
    chien_search,
    decode,
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