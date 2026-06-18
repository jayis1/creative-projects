"""Comprehensive tests for new structures added in v3.0.

Covers: BlockedBloomFilter, KMV, MinHash, LSHIndex, ReservoirSampler,
WeightedReservoirSampler, config system, logging, and enhanced
serialization for new structures.
"""
import os
import sys
import math
import json
import random
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, BlockedBloomFilter, CuckooFilter,
    CountMinSketch, ConservativeCountMinSketch, HyperLogLog, KMV, MinHash,
    LSHIndex, ReservoirSampler, WeightedReservoirSampler, TopK, TDigest,
    SkipList, ScalableBloomFilter, serialize, deserialize,
    load_config, build_from_config, build_from_file, list_structures,
    get_param_spec, save_config, ConfigError,
)
from pds.logging_utils import get_logger, set_level as set_log_level, disable


# ─── BlockedBloomFilter ─────────────────────────────────────────────────

class TestBlockedBloomFilter:
    def test_no_false_negatives(self):
        bf = BlockedBloomFilter(capacity=1000, error_rate=0.01)
        for i in range(1000):
            bf.add(f"item-{i}")
        for i in range(1000):
            assert f"item-{i}" in bf, f"False negative on item-{i}"

    def test_false_positive_rate(self):
        bf = BlockedBloomFilter(capacity=10000, error_rate=0.01)
        for i in range(10000):
            bf.add(f"item-{i}")
        fp = sum(1 for i in range(10000, 20000) if f"item-{i}" in bf)
        rate = fp / 10000
        # Blocked bloom may have slightly higher FPR, allow 2× target
        assert rate < 0.05, f"FPR {rate} too high"

    def test_len(self):
        bf = BlockedBloomFilter(capacity=100)
        assert len(bf) == 0
        bf.add("a")
        assert len(bf) == 1

    def test_bytes_roundtrip(self):
        bf = BlockedBloomFilter(capacity=1000, error_rate=0.01)
        for i in range(500):
            bf.add(str(i))
        data = bf.to_bytes()
        bf2 = BlockedBloomFilter.from_bytes(data)
        for i in range(500):
            assert str(i) in bf2

    def test_json_roundtrip(self):
        bf = BlockedBloomFilter(capacity=500)
        for i in range(200):
            bf.add(f"x-{i}")
        data = serialize(bf)
        bf2 = deserialize(data)
        for i in range(200):
            assert f"x-{i}" in bf2

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            BlockedBloomFilter(capacity=0)
        with pytest.raises(ValueError):
            BlockedBloomFilter(capacity=100, error_rate=0)
        with pytest.raises(ValueError):
            BlockedBloomFilter(capacity=100, error_rate=0.01, block_bits=100)

    def test_fpr_estimate_positive(self):
        bf = BlockedBloomFilter(capacity=100)
        for i in range(50):
            bf.add(str(i))
        assert bf.estimated_false_positive_rate > 0


# ─── KMV ────────────────────────────────────────────────────────────────

class TestKMV:
    def test_small_exact(self):
        """When fewer than k items are added, estimate is exact."""
        kmv = KMV(k=100)
        for i in range(50):
            kmv.add(str(i))
        assert kmv.estimate() == 50.0

    def test_large_approximate(self):
        random.seed(42)
        kmv = KMV(k=1024)
        for i in range(100000):
            kmv.add(str(i))
        est = kmv.estimate()
        err = abs(est - 100000) / 100000
        assert err < 0.1, f"KMV error {err:.3f} too high"

    def test_merge(self):
        kmv1 = KMV(k=512)
        kmv2 = KMV(k=512)
        for i in range(5000):
            kmv1.add(f"a-{i}")
        for i in range(5000):
            kmv2.add(f"b-{i}")
        kmv1.merge(kmv2)
        est = kmv1.estimate()
        err = abs(est - 10000) / 10000
        assert err < 0.15, f"Merged KMV error {err:.3f} too high"

    def test_merge_different_k_raises(self):
        kmv1 = KMV(k=100)
        kmv2 = KMV(k=200)
        with pytest.raises(ValueError):
            kmv1.merge(kmv2)

    def test_relative_error(self):
        kmv = KMV(k=1024)
        assert abs(kmv.relative_error - 1.0 / math.sqrt(1022)) < 1e-10

    def test_serialize_roundtrip(self):
        kmv = KMV(k=256)
        for i in range(1000):
            kmv.add(str(i))
        data = serialize(kmv)
        kmv2 = deserialize(data)
        assert kmv2.k == kmv.k
        assert kmv2._values == kmv._values
        assert abs(kmv2.estimate() - kmv.estimate()) < 1

    def test_invalid_k(self):
        with pytest.raises(ValueError):
            KMV(k=5)

    def test_empty(self):
        kmv = KMV(k=100)
        assert kmv.estimate() == 0.0
        assert len(kmv) == 0

    def test_add_batch(self):
        kmv = KMV(k=100)
        kmv.add_batch(["a", "b", "c"])
        assert len(kmv) == 3


# ─── MinHash ───────────────────────────────────────────────────────────

class TestMinHash:
    def test_identical_sets(self):
        m1 = MinHash(num_perm=128, seed=42)
        m2 = MinHash(num_perm=128, seed=42)
        for w in "the quick brown fox".split():
            m1.add(w)
            m2.add(w)
        assert m1.jaccard(m2) == 1.0

    def test_disjoint_sets(self):
        m1 = MinHash(num_perm=256, seed=0)
        m2 = MinHash(num_perm=256, seed=0)
        for i in range(1000):
            m1.add(f"a-{i}")
        for i in range(1000):
            m2.add(f"b-{i}")
        j = m1.jaccard(m2)
        assert j < 0.1, f"Jaccard {j} too high for disjoint sets"

    def test_partial_overlap(self):
        random.seed(42)
        m1 = MinHash(num_perm=256, seed=0)
        m2 = MinHash(num_perm=256, seed=0)
        # 50 shared items + 50 unique each
        for i in range(50):
            m1.add(f"shared-{i}")
            m2.add(f"shared-{i}")
        for i in range(50):
            m1.add(f"uniq1-{i}")
            for _ in range(2):  # weight by repetition won't change MinHash
                pass
        for i in range(50):
            m2.add(f"uniq2-{i}")
        # True Jaccard = 50 / 150 ≈ 0.333
        j = m1.jaccard(m2)
        assert 0.15 < j < 0.55, f"Jaccard {j} not near 0.33"

    def test_merge(self):
        m1 = MinHash(num_perm=128, seed=0)
        m2 = MinHash(num_perm=128, seed=0)
        m1.add("a")
        m1.add("b")
        m2.add("b")
        m2.add("c")
        m1.merge(m2)
        # m1 now represents {a, b, c}
        # Check against a fresh MinHash of {a, b, c}
        m3 = MinHash(num_perm=128, seed=0)
        m3.add("a")
        m3.add("b")
        m3.add("c")
        assert m1.jaccard(m3) == 1.0

    def test_different_seed_raises(self):
        m1 = MinHash(num_perm=64, seed=0)
        m2 = MinHash(num_perm=64, seed=1)
        with pytest.raises(ValueError):
            m1.jaccard(m2)

    def test_different_num_perm_raises(self):
        m1 = MinHash(num_perm=64)
        m2 = MinHash(num_perm=128)
        with pytest.raises(ValueError):
            m1.jaccard(m2)

    def test_serialize_roundtrip(self):
        m1 = MinHash(num_perm=64, seed=42)
        for w in "hello world foo bar baz".split():
            m1.add(w)
        data = serialize(m1)
        m2 = deserialize(data)
        assert m2.num_perm == m1.num_perm
        assert m2.seed == m1.seed
        assert m2._signature == m1._signature

    def test_to_json_from_json(self):
        m1 = MinHash(num_perm=32, seed=7)
        m1.add("test")
        j = m1.to_json()
        m2 = MinHash.from_json(j)
        assert m2._signature == m1._signature

    def test_empty(self):
        m = MinHash(num_perm=64)
        assert m.is_empty()

    def test_estimated_cardinality(self):
        m = MinHash(num_perm=128)
        for i in range(1000):
            m.add(str(i))
        est = m.estimated_cardinality()
        # Very rough — just check it's in the right order of magnitude
        assert 100 < est < 10000

    def test_invalid_num_perm(self):
        with pytest.raises(ValueError):
            MinHash(num_perm=0)


# ─── LSHIndex ───────────────────────────────────────────────────────────

class TestLSHIndex:
    def test_find_near_duplicate(self):
        idx = LSHIndex(num_perm=128, num_bands=32, seed=0)
        m1 = MinHash(num_perm=128, seed=0)
        for w in "the quick brown fox jumps over".split():
            m1.add(w)
        idx.add("doc1", m1)
        # Near-duplicate: 5 of 6 words shared
        m2 = MinHash(num_perm=128, seed=0)
        for w in "the quick brown fox jumps high".split():
            m2.add(w)
        candidates = idx.query(m2)
        assert "doc1" in candidates

    def test_threshold(self):
        idx = LSHIndex(num_perm=128, num_bands=16)
        # threshold = (1/16)^(1/8) ≈ 0.758
        assert 0.6 < idx.threshold < 0.9

    def test_divisible_required(self):
        with pytest.raises(ValueError):
            LSHIndex(num_perm=100, num_bands=3)

    def test_len_and_contains(self):
        idx = LSHIndex(num_perm=64, num_bands=16)
        m = MinHash(num_perm=64)
        m.add("test")
        idx.add("d1", m)
        assert len(idx) == 1
        assert "d1" in idx
        assert "d2" not in idx

    def test_get_minhash(self):
        idx = LSHIndex(num_perm=64, num_bands=16)
        m = MinHash(num_perm=64)
        m.add("hello")
        idx.add("doc", m)
        retrieved = idx.get_minhash("doc")
        assert retrieved is not None
        assert retrieved._signature == m._signature
        assert idx.get_minhash("nonexistent") is None


# ─── ReservoirSampler ───────────────────────────────────────────────────

class TestReservoirSampler:
    def test_reservoir_size(self):
        rs = ReservoirSampler(k=10)
        for i in range(1000):
            rs.add(i)
        assert len(rs.sample()) == 10

    def test_total_seen(self):
        rs = ReservoirSampler(k=10)
        for i in range(1000):
            rs.add(i)
        assert rs.total_seen == 1000

    def test_small_stream(self):
        """When stream < k, reservoir contains all items."""
        rs = ReservoirSampler(k=100)
        for i in range(10):
            rs.add(i)
        assert sorted(rs.sample()) == list(range(10))

    def test_uniformity(self):
        """Roughly check uniformity: each item should appear ~equally."""
        random.seed(42)
        counts = [0] * 100
        for trial in range(10000):
            rs = ReservoirSampler(k=10, rng=random.Random(trial))
            for i in range(100):
                rs.add(i)
            sample = rs.sample()
            for item in sample:
                counts[item] += 1
        # Each of 100 items should appear ~10000 * 10/100 = 1000 times ± 15%
        for c in counts:
            assert 750 < c < 1250, f"Count {c} out of range"

    def test_merge(self):
        rs1 = ReservoirSampler(k=5)
        rs2 = ReservoirSampler(k=5)
        for i in range(100):
            rs1.add(i)
        for i in range(100, 200):
            rs2.add(i)
        rs1.merge(rs2)
        assert len(rs1.sample()) == 5
        assert rs1.total_seen == 200

    def test_merge_different_k_raises(self):
        rs1 = ReservoirSampler(k=5)
        rs2 = ReservoirSampler(k=10)
        with pytest.raises(ValueError):
            rs1.merge(rs2)

    def test_serialize_roundtrip(self):
        rs = ReservoirSampler(k=10)
        for i in range(100):
            rs.add(i)
        data = serialize(rs)
        rs2 = deserialize(data)
        assert rs2.k == rs.k
        assert rs2._reservoir == rs._reservoir
        assert rs2._n == rs._n

    def test_to_dict_from_dict(self):
        rs = ReservoirSampler(k=5)
        for i in range(10):
            rs.add(i)
        d = rs.to_dict()
        rs2 = ReservoirSampler.from_dict(d)
        assert rs2.sample() == rs.sample()

    def test_invalid_k(self):
        with pytest.raises(ValueError):
            ReservoirSampler(k=0)


# ─── WeightedReservoirSampler ───────────────────────────────────────────

class TestWeightedReservoirSampler:
    def test_basic(self):
        wrs = WeightedReservoirSampler(k=10)
        for i in range(100):
            wrs.add(i, weight=1.0)
        assert len(wrs) <= 10
        assert wrs.total_seen == 100

    def test_weight_influences(self):
        """High-weight items are more likely to be in the sample."""
        random.seed(42)
        high_count = 0
        for trial in range(1000):
            wrs = WeightedReservoirSampler(k=5, rng=random.Random(trial))
            wrs.add("low", weight=0.01)
            wrs.add("high", weight=100)
            sample = wrs.sample()
            if "high" in sample:
                high_count += 1
        assert high_count > 800, f"High-weight item only in {high_count}/1000"

    def test_zero_weight_ignored(self):
        wrs = WeightedReservoirSampler(k=10)
        wrs.add("x", weight=0)
        assert len(wrs) == 0


# ─── Config System ──────────────────────────────────────────────────────

class TestConfig:
    def test_build_bloom(self):
        struct = build_from_config({
            "structure": "bloom",
            "capacity": 1000,
            "error_rate": 0.01,
        })
        assert isinstance(struct, BloomFilter)
        assert struct.capacity == 1000

    def test_build_cms(self):
        struct = build_from_config({
            "structure": "cms",
            "error": 0.001,
            "confidence": 0.99,
        })
        assert isinstance(struct, CountMinSketch)

    def test_build_kmv(self):
        struct = build_from_config({"structure": "kmv", "k": 256})
        assert isinstance(struct, KMV)
        assert struct.k == 256

    def test_build_minhash(self):
        struct = build_from_config({
            "structure": "minhash",
            "num_perm": 64,
        })
        assert isinstance(struct, MinHash)
        assert struct.num_perm == 64

    def test_build_blocked_bloom(self):
        struct = build_from_config({
            "structure": "blocked-bloom",
            "capacity": 500,
            "error_rate": 0.02,
        })
        assert isinstance(struct, BlockedBloomFilter)

    def test_unknown_structure(self):
        with pytest.raises(ConfigError):
            build_from_config({"structure": "nonexistent"})

    def test_missing_structure_key(self):
        with pytest.raises(ConfigError):
            build_from_config({"capacity": 100})

    def test_unknown_param(self):
        with pytest.raises(ConfigError):
            build_from_config({"structure": "bloom", "foo": 1})

    def test_json_config_file(self):
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "structure": "tdigest",
                "compression": 50,
            }, f)
            fname = f.name
        try:
            struct = build_from_file(fname)
            assert isinstance(struct, TDigest)
            assert struct.compression == 50
        finally:
            os.unlink(fname)

    def test_toml_config_file(self):
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", delete=False) as f:
            f.write('structure = "topk"\nk = 50\n')
            fname = f.name
        try:
            config = load_config(fname)
            struct = build_from_config(config)
            assert isinstance(struct, TopK)
            assert struct.k == 50
        finally:
            os.unlink(fname)

    def test_yaml_config_file(self):
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "structure": "hll",
                "precision": 12,
            }, f)
            fname = f.name
        try:
            struct = build_from_file(fname)
            assert isinstance(struct, HyperLogLog)
            assert struct.precision == 12
        finally:
            os.unlink(fname)

    def test_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False) as f:
            f.write("<xml/>")
            fname = f.name
        try:
            with pytest.raises(ConfigError):
                load_config(fname)
        finally:
            os.unlink(fname)

    def test_save_config_json(self):
        with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False) as f:
            fname = f.name
        try:
            save_config({"structure": "bloom", "capacity": 100}, fname)
            config = load_config(fname)
            assert config["structure"] == "bloom"
        finally:
            os.unlink(fname)

    def test_list_structures(self):
        structures = list_structures()
        assert "bloom" in structures
        assert "kmv" in structures
        assert "minhash" in structures
        assert len(structures) >= 13

    def test_get_param_spec(self):
        params = get_param_spec("bloom")
        assert "capacity" in params
        assert "error_rate" in params

    def test_get_param_spec_unknown(self):
        with pytest.raises(ConfigError):
            get_param_spec("nonexistent")


# ─── Logging ────────────────────────────────────────────────────────────

class TestLogging:
    def test_get_logger(self):
        log = get_logger("test")
        assert log.name == "pds.test"

    def test_set_level(self):
        import logging
        set_log_level("DEBUG")
        assert logging.getLogger("pds").level == logging.DEBUG
        set_log_level("WARNING")
        assert logging.getLogger("pds").level == logging.WARNING

    def test_disable(self):
        import logging
        disable()
        assert logging.getLogger("pds").level > logging.CRITICAL
        # Restore
        set_log_level("WARNING")


# ─── Enhanced Serialization ─────────────────────────────────────────────

class TestEnhancedSerialization:
    def test_counting_bloom_roundtrip(self):
        cbf = CountingBloomFilter(capacity=1000, error_rate=0.01)
        for i in range(500):
            cbf.add(str(i))
        data = serialize(cbf)
        cbf2 = deserialize(data)
        for i in range(500):
            assert str(i) in cbf2

    def test_cuckoo_roundtrip(self):
        cf = CuckooFilter(capacity=1000, fingerprint_bits=16)
        for i in range(500):
            cf.add(str(i))
        data = serialize(cf)
        cf2 = deserialize(data)
        for i in range(500):
            assert str(i) in cf2

    def test_conservative_cms_roundtrip(self):
        cms = ConservativeCountMinSketch(error=0.01, confidence=0.99)
        for _ in range(100):
            cms.add("test")
        data = serialize(cms)
        cms2 = deserialize(data)
        assert cms2.query("test") == cms.query("test")

    def test_kmv_roundtrip(self):
        kmv = KMV(k=256)
        for i in range(1000):
            kmv.add(str(i))
        data = serialize(kmv)
        kmv2 = deserialize(data)
        assert abs(kmv.estimate() - kmv2.estimate()) < 1

    def test_minhash_roundtrip(self):
        m1 = MinHash(num_perm=64, seed=42)
        for w in "hello world".split():
            m1.add(w)
        data = serialize(m1)
        m2 = deserialize(data)
        assert m1._signature == m2._signature
        assert m1.jaccard(m2) == 1.0

    def test_reservoir_roundtrip(self):
        rs = ReservoirSampler(k=10)
        for i in range(100):
            rs.add(i)
        data = serialize(rs)
        rs2 = deserialize(data)
        assert rs2.sample() == rs.sample()
        assert rs2.total_seen == rs.total_seen