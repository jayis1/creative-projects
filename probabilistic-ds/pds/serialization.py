"""Serialization helpers for all probabilistic data structures.

Provides JSON-compatible serialization for checkpointing and
inter-process exchange.  All structures that have meaningful state
support round-trip serialization.
"""
import json
import base64
from .bloom import BloomFilter, CountingBloomFilter
from .blocked_bloom import BlockedBloomFilter
from .cuckoo import CuckooFilter
from .countmin import CountMinSketch
from .conservative_cms import ConservativeCountMinSketch
from .hll import HyperLogLog
from .kmv import KMV
from .minhash import MinHash
from .sampling import ReservoirSampler
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
    if isinstance(obj, BlockedBloomFilter):
        return json.dumps({
            "type": "BlockedBloomFilter",
            "capacity": obj.capacity,
            "error_rate": obj.error_rate,
            "num_bits": obj.num_bits,
            "num_blocks": obj.num_blocks,
            "block_bits": obj.block_bits,
            "num_hashes": obj.num_hashes,
            "count": obj.count,
            "bits": base64.b64encode(bytes(obj._bits)).decode("ascii"),
        })
    if isinstance(obj, CountingBloomFilter):
        return json.dumps({
            "type": "CountingBloomFilter",
            "capacity": obj.capacity,
            "error_rate": obj.error_rate,
            "num_bits": obj.num_bits,
            "num_hashes": obj.num_hashes,
            "count": obj.count,
            "counters": base64.b64encode(bytes(obj._counters)).decode("ascii"),
        })
    if isinstance(obj, CuckooFilter):
        return json.dumps({
            "type": "CuckooFilter",
            "bucket_size": obj.bucket_size,
            "fingerprint_bits": obj.fingerprint_bits,
            "num_buckets": obj.num_buckets,
            "max_kicks": obj.max_kicks,
            "count": obj.count,
            "table": obj._table,
        })
    if isinstance(obj, ConservativeCountMinSketch):
        return json.dumps({
            "type": "ConservativeCountMinSketch",
            "width": obj.width,
            "depth": obj.depth,
            "total": obj.total,
            "seeds": obj._seeds,
            "counts": obj._counts,
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
    if isinstance(obj, KMV):
        return json.dumps({
            "type": "KMV",
            "k": obj.k,
            "values": list(obj._values),
        })
    if isinstance(obj, MinHash):
        return json.dumps({
            "type": "MinHash",
            "num_perm": obj.num_perm,
            "seed": obj.seed,
            "signature": obj._signature,
        })
    if isinstance(obj, ReservoirSampler):
        return json.dumps({
            "type": "ReservoirSampler",
            "k": obj.k,
            "reservoir": obj._reservoir,
            "total_seen": obj._n,
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
    if t == "BlockedBloomFilter":
        bf = BlockedBloomFilter(obj["capacity"], obj["error_rate"],
                                obj.get("block_bits", 512))
        bf.num_bits = obj["num_bits"]
        bf.num_blocks = obj["num_blocks"]
        bf.num_hashes = obj["num_hashes"]
        bf.count = obj["count"]
        bf._bits = bytearray(base64.b64decode(obj["bits"]))
        return bf
    if t == "CountingBloomFilter":
        cbf = CountingBloomFilter(obj["capacity"], obj["error_rate"])
        cbf.num_bits = obj["num_bits"]
        cbf.num_hashes = obj["num_hashes"]
        cbf.count = obj["count"]
        cbf._counters = bytearray(base64.b64decode(obj["counters"]))
        return cbf
    if t == "CuckooFilter":
        cf = CuckooFilter(
            capacity=obj["num_buckets"] * obj["bucket_size"],
            bucket_size=obj["bucket_size"],
            fingerprint_bits=obj["fingerprint_bits"],
            max_kicks=obj["max_kicks"],
        )
        cf.count = obj["count"]
        cf._table = [list(bucket) for bucket in obj["table"]]
        return cf
    if t == "ConservativeCountMinSketch":
        cms = ConservativeCountMinSketch(width=obj["width"], depth=obj["depth"])
        cms.total = obj["total"]
        cms._seeds = obj["seeds"]
        cms._counts = obj["counts"]
        return cms
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
    if t == "KMV":
        kmv = KMV(k=obj["k"])
        kmv._values = set(obj["values"])
        if kmv._values:
            kmv._max_in_set = max(kmv._values)
            kmv._has_max = True
        return kmv
    if t == "MinHash":
        mh = MinHash(num_perm=obj["num_perm"], seed=obj["seed"])
        mh._signature = list(obj["signature"])
        return mh
    if t == "ReservoirSampler":
        rs = ReservoirSampler(k=obj["k"])
        rs._reservoir = list(obj["reservoir"])
        rs._n = obj["total_seen"]
        return rs
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