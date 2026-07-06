"""Bug hunt tests for fm-index."""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fmindex import FMIndex, bwt_encode, bwt_decode, WaveletTree, WaveletMatrix, BitArray
from fmindex.suffix_array import build_suffix_array, build_suffix_array_naive
from fmindex import serialize, analysis


# ============================================================================
# BUG 1: extract() returns off-by-one characters
# ============================================================================
def test_extract_off_by_one():
    """extract(pos, len) should return text[pos:pos+len], but it returns
    text[pos-1:pos+len-1] due to BWT giving the char *before* the suffix start."""
    idx = FMIndex("banana")
    # text[1:4] = "ana"
    result = idx.extract(1, 3)
    expected = "ana"
    print(f"extract(1,3) = {result!r}, expected {expected!r}")
    assert result == expected, f"extract off-by-one: got {result!r}, expected {expected!r}"

def test_extract_full_text():
    """extract(0, len) should return the full text."""
    text = "mississippi"
    idx = FMIndex(text)
    result = idx.extract(0, len(text))
    print(f"extract(0,{len(text)}) = {result!r}, expected {text!r}")
    assert result == text, f"extract full text failed: got {result!r}, expected {text!r}"


# ============================================================================
# BUG 2: BitArray.count_ones() crashes on empty BitArray
# ============================================================================
def test_bitarray_empty_count_ones():
    """BitArray() with no bits should have count_ones() == 0, not raise."""
    ba = BitArray()
    assert ba.count_ones() == 0, f"empty BitArray count_ones should be 0, got {ba.count_ones()}"
    assert ba.count_zeros() == 0


# ============================================================================
# BUG 3: suffix_array naive doesn't handle empty string
# ============================================================================
def test_suffix_array_empty():
    """build_suffix_array('') should return [], not crash."""
    assert build_suffix_array("") == []
    assert build_suffix_array_naive("") == []


# ============================================================================
# BUG 4: search_approx has dead forward-search function
# ============================================================================
def test_search_approx_no_duplicates():
    """search_approx should not produce duplicate positions."""
    text = "banana"
    idx = FMIndex(text)
    matches = idx.search_approx("ana", max_mismatches=1)
    positions = [m.position for m in matches]
    assert len(positions) == len(set(positions)), f"duplicate positions: {positions}"


# ============================================================================
# BUG 5: wavelet tree rank with i=0 on single-symbol alphabet
# ============================================================================
def test_wavelet_single_symbol_rank():
    """rank(c, 0) should be 0 even for single-symbol alphabet."""
    wt = WaveletTree([65, 65, 65])  # all 'A'
    assert wt.rank(65, 0) == 0
    assert wt.rank(65, 3) == 3
    assert wt.rank(66, 3) == 0  # 'B' not in alphabet


# ============================================================================
# BUG 6: count_in_range doesn't handle pos_lo > pos_hi
# ============================================================================
def test_count_in_range_empty():
    """count_in_range with pos_lo > pos_hi should return 0."""
    idx = FMIndex("banana")
    assert idx.count_in_range("a", 5, 2) == 0  # empty range


# ============================================================================
# BUG 7: iter_kmers skips suffix at position 0 incorrectly
# ============================================================================
def test_iter_kmers_correctness():
    """iter_kmers should produce the same results as a brute-force count."""
    text = "mississippi"
    idx = FMIndex(text)
    # brute-force k-mer counts
    from collections import Counter
    for k in [1, 2, 3, 4]:
        bf = Counter()
        for i in range(len(text) - k + 1):
            bf[text[i:i+k]] += 1
        idx_kmers = dict(idx.iter_kmers(k))
        assert idx_kmers == dict(bf), f"k={k}: index={idx_kmers}, brute={dict(bf)}"


# ============================================================================
# BUG 8: longest_repeated_substring may return substring including sentinel
# ============================================================================
def test_longest_repeated_no_sentinel():
    """longest_repeated_substring should never include the sentinel."""
    text = "abab"
    idx = FMIndex(text)
    result = idx.longest_repeated_substring()
    if result:
        sub, length = result
        assert '$' not in sub, f"sentinel in repeated substring: {sub!r}"


# ============================================================================
# Run all tests
# ============================================================================
if __name__ == "__main__":
    tests = [
        test_extract_off_by_one,
        test_extract_full_text,
        test_bitarray_empty_count_ones,
        test_suffix_array_empty,
        test_search_approx_no_duplicates,
        test_wavelet_single_symbol_rank,
        test_count_in_range_empty,
        test_iter_kmers_correctness,
        test_longest_repeated_no_sentinel,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")