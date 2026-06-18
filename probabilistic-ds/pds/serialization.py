"""Serialization helpers for all probabilistic data structures.

Provides JSON-compatible serialization for checkpointing and
inter-process exchange.
"""
import json
import base64
from .bloom import BloomFilter, CountingBloomFilter
from .cuckoo import CuckooFilter
from .countmin import CountMinSketch
from .hll import HyperLogLog
from .topk import TopK
from .tdigest import TDigest


def serialize(obj) -> str:
    """Serialize a PDS structure to a JSON string.

    The format includes a ``type`` tag for deserialization dispatch.
    """
    if isinstance(obj, BloomFilter):
        return json.dumps({
            "type": "BloomFilter",
            "capacity": obj.capacity,
            "error_rate": obj.error_rate,
            "num_bits": obj.num_bits,
            "num_hashes": obj.num_hashes,
            "count": obj.count,
            "bits": base64.b64encode(bytes(obj._bits)).decode("ascii"),
        })
    if isinstance(obj, CountMinSketch):
        return json.dumps({
            "type": "CountMinSketch",
            "width": obj.width,
            "depth": obj.depth,
            "total": obj.total,
            "seeds": obj._seeds,
            "counts": obj._counts,
        })
    if isinstance(obj, HyperLogLog):
        return json.dumps({
            "type": "HyperLogLog",
            "precision": obj.precision,
            "registers": list(obj._registers),
        })
    if isinstance(obj, TopK):
        return json.dumps({
            "type": "TopK",
            "k": obj.k,
            "counts": obj._counts,
        })
    if isinstance(obj, TDigest):
        return json.dumps({
            "type": "TDigest",
            "compression": obj.compression,
            "total_count": obj._total_count,
            "min": obj._min if obj._min != float("inf") else None,
            "max": obj._max if obj._max != float("-inf") else None,
            "centroids": [[c.mean, c.count] for c in obj._centroids],
        })
    raise TypeError(f"Cannot serialize object of type {type(obj).__name__}")


def deserialize(data: str):
    """Deserialize a PDS structure from a JSON string."""
    obj = json.loads(data)
    t = obj["type"]
    if t == "BloomFilter":
        bf = BloomFilter(obj["capacity"], obj["error_rate"])
        bf.num_bits = obj["num_bits"]
        bf.num_hashes = obj["num_hashes"]
        bf.count = obj["count"]
        bf._bits = bytearray(base64.b64decode(obj["bits"]))
        return bf
    if t == "CountMinSketch":
        cms = CountMinSketch(width=obj["width"], depth=obj["depth"])
        cms.total = obj["total"]
        cms._seeds = obj["seeds"]
        cms._counts = obj["counts"]
        return cms
    if t == "HyperLogLog":
        hll = HyperLogLog(precision=obj["precision"])
        hll._registers = bytearray(obj["registers"])
        return hll
    if t == "TopK":
        tk = TopK(k=obj["k"])
        tk._counts = obj["counts"]
        return tk
    if t == "TDigest":
        td = TDigest(compression=obj["compression"])
        td._total_count = obj["total_count"]
        td._min = obj["min"] if obj["min"] is not None else float("inf")
        td._max = obj["max"] if obj["max"] is not None else float("-inf")
        from .tdigest import _Centroid
        td._centroids = [_Centroid(m, c) for m, c in obj["centroids"]]
        td._sorted = True
        return td
    raise ValueError(f"Unknown type: {t}")