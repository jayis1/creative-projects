"""Comprehensive regression tests for the fm-index bug hunt."""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex, bwt_encode, bwt_decode, WaveletTree, WaveletMatrix, BitArray
from fmindex.suffix_array import build_suffix_array, build_suffix_array_naive
from fmindex import serialize, analysis


# ============================================================================
# Bug 1 (FIXED): extract() off-by-one — BWT gives char *before* suffix start
# ============================================================================
def test_extract_randomized():
    """extract(pos, len) must match text[pos:pos+len] for random texts/positions."""
    random.seed(42)
    for trial in range(50):
        n = random.randint(1, 100)
        text = ''.join(random.choice("abcde") for _ in range(n))
        idx = FMIndex(text, sample_rate=random.choice([1, 2, 4, 8]))
        for _ in range(20):
            pos = random.randint(0, n - 1)
            length = random.randint(1, n - pos)
            expected = text[pos:pos + length]
            result = idx.extract(pos, length)
            assert result == expected, (
                f"trial {trial}: extract({pos},{length}) = {result!r}, "
                f"expected {expected!r} (text={text!r}, sr={idx.sample_rate})"
            )
    print("PASS: extract randomized")


# ============================================================================
# Bug 2 (FIXED): BitArray.count_ones() on empty BitArray
# ============================================================================
def test_bitarray_empty():
    ba = BitArray()
    assert ba.count_ones() == 0
    assert ba.count_zeros() == 0
    assert len(ba) == 0
    print("PASS: BitArray empty")


# ============================================================================
# Bug 3: SA construction matches naive for various texts
# ============================================================================
def test_sa_correctness():
    random.seed(7)
    for trial in range(30):
        n = random.randint(1, 50)
        text = ''.join(random.choice("abc") for _ in range(n)) + '$'
        sa_fast = build_suffix_array(text)
        sa_naive = build_suffix_array_naive(text)
        assert sa_fast == sa_naive, (
            f"trial {trial}: SA mismatch for {text!r}\n"
            f"  fast:  {sa_fast}\n  naive: {sa_naive}"
        )
    print("PASS: SA correctness")


# ============================================================================
# Bug 4: BWT round-trip
# ============================================================================
def test_bwt_roundtrip():
    random.seed(13)
    for trial in range(30):
        n = random.randint(1, 50)
        text = ''.join(random.choice("abcd") for _ in range(n)) + '$'
        bwt, sa = bwt_encode(text)
        decoded = bwt_decode(bwt)
        assert decoded == text, (
            f"trial {trial}: BWT round-trip failed for {text!r}: got {decoded!r}"
        )
    print("PASS: BWT round-trip")


# ============================================================================
# Bug 5: count/locate correctness vs brute force
# ============================================================================
def test_count_locate_bruteforce():
    random.seed(99)
    for trial in range(30):
        n = random.randint(1, 80)
        text = ''.join(random.choice("abc") for _ in range(n))
        idx = FMIndex(text, sample_rate=random.choice([1, 3, 7, 16]))
        for _ in range(15):
            k = random.randint(1, min(6, n))
            start = random.randint(0, n - k)
            pat = text[start:start + k]
            # brute force
            bf_pos = []
            for i in range(n - k + 1):
                if text[i:i + k] == pat:
                    bf_pos.append(i)
            # index
            assert idx.count(pat) == len(bf_pos), (
                f"trial {trial}: count({pat!r}) = {idx.count(pat)}, "
                f"expected {len(bf_pos)} (text={text!r})"
            )
            assert idx.locate(pat) == bf_pos, (
                f"trial {trial}: locate({pat!r}) = {idx.locate(pat)}, "
                f"expected {bf_pos} (text={text!r})"
            )
    print("PASS: count/locate brute force")


# ============================================================================
# Bug 6: wavelet tree/matrix parity
# ============================================================================
def test_wavelet_parity():
    random.seed(2024)
    for trial in range(20):
        sigma = random.randint(2, 10)
        n = random.randint(1, 100)
        data = [random.randint(0, sigma - 1) for _ in range(n)]
        if not data:
            continue
        codes = sorted(set(data))
        if len(codes) < 2:
            continue
        wt = WaveletTree(data)
        wm = WaveletMatrix(data)
        for i in range(n):
            assert wt.access(i) == wm.access(i), f"access mismatch at {i}"
        for c in codes:
            for i in range(0, n + 1):
                assert wt.rank(c, i) == wm.rank(c, i), f"rank mismatch c={c} i={i}"
            cnt = wt.rank(c, n)
            for k in range(1, cnt + 1):
                assert wt.select(c, k) == wm.select(c, k), f"select mismatch c={c} k={k}"
    print("PASS: wavelet parity")


# ============================================================================
# Bug 7: serialization round-trip
# ============================================================================
def test_serialization():
    random.seed(55)
    for trial in range(10):
        n = random.randint(1, 100)
        text = ''.join(random.choice("abcde") for _ in range(n))
        idx = FMIndex(text, sample_rate=4)
        # binary
        serialize.save_binary(idx, "/tmp/fm_bin_test.bin")
        idx2 = serialize.load_binary("/tmp/fm_bin_test.bin")
        assert idx2.count("a") == idx.count("a")
        assert idx2.locate("a") == idx.locate("a")
        # json
        serialize.save_json(idx, "/tmp/fm_json_test.json")
        idx3 = serialize.load_json("/tmp/fm_json_test.json")
        assert idx3.count("a") == idx.count("a")
        assert idx3.locate("a") == idx.locate("a")
    print("PASS: serialization")


# ============================================================================
# Bug 8: iter_kmers correctness
# ============================================================================
def test_kmers():
    from collections import Counter
    random.seed(33)
    for trial in range(15):
        n = random.randint(5, 50)
        text = ''.join(random.choice("ab") for _ in range(n))
        idx = FMIndex(text)
        for k in [1, 2, 3]:
            bf = Counter()
            for i in range(len(text) - k + 1):
                bf[text[i:i + k]] += 1
            result = dict(idx.iter_kmers(k))
            assert result == dict(bf), (
                f"trial {trial} k={k}: {result} != {dict(bf)}"
            )
    print("PASS: k-mers")


# ============================================================================
# Bug 9: extract at boundaries
# ============================================================================
def test_extract_boundaries():
    idx = FMIndex("hello")
    assert idx.extract(0, 1) == "h"
    assert idx.extract(4, 1) == "o"
    assert idx.extract(0, 5) == "hello"
    assert idx.extract(2, 3) == "llo"
    # out of range
    try:
        idx.extract(5, 1)
        assert False, "should have raised"
    except IndexError:
        pass
    try:
        idx.extract(-1, 1)
        assert False, "should have raised"
    except IndexError:
        pass
    print("PASS: extract boundaries")


# ============================================================================
# Bug 10: approximate search correctness
# ============================================================================
def test_approx_search():
    text = "banana"
    idx = FMIndex(text)
    # 0 mismatches should find exact matches
    m0 = idx.search_approx("ana", 0)
    assert sorted(m.position for m in m0) == [1, 3]
    # 1 mismatch should find more
    m1 = idx.search_approx("ana", 1)
    positions = sorted(m.position for m in m1)
    # brute force check
    bf = set()
    for i in range(len(text) - 2):
        mm = sum(1 for a, b in zip(text[i:i+3], "ana") if a != b)
        if mm <= 1:
            bf.add(i)
    assert set(positions) == bf, f"approx 1mm: {positions} != {sorted(bf)}"
    print("PASS: approx search")


if __name__ == "__main__":
    tests = [
        test_extract_randomized,
        test_bitarray_empty,
        test_sa_correctness,
        test_bwt_roundtrip,
        test_count_locate_bruteforce,
        test_wavelet_parity,
        test_serialization,
        test_kmers,
        test_extract_boundaries,
        test_approx_search,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")