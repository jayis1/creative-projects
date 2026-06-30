"""Backward-compatibility shim — re-exports from reed_solomon.gf.

New code should import from ``reed_solomon`` directly:
    from reed_solomon.gf import GF256, gf_poly_mul
"""
from reed_solomon.gf import (  # noqa: F401
    GF256,
    PRIMARY_POLY,
    gf_poly_add,
    gf_poly_div,
    gf_poly_eval,
    gf_poly_mul,
    gf_poly_scale,
)