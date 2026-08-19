"""Tests for range queries, serialization, config, and CLI."""

import pytest
import os
import tempfile
import json

from wavelet_tree import (
    WaveletTree,
    WaveletMatrix,
    HuffmanWaveletTree,
    HuffmanWaveletMatrix,
    save,
    load,
    Config,
)
from wavelet_tree.queries import (
    range_quantile,
    range_count,
    range_min,
    range_max,
    range_next_value,
    range_prev_value,
    interval_symbols,
    range_intersection,
    prefix_search,
    count_distinct,
)


class TestRangeQueries:
    """Test all range query functions."""

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi", "hello world", "abcdefg"])
    def test_range_count(self, seq):
        wt = WaveletTree(seq)
        for c in set(seq):
            for i in range(len(seq) + 1):
                for j in range(i, len(seq) + 1):
                    expected = seq[i:j].count(c)
                    assert range_count(wt, c, i, j) == expected

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi", "abcdefg"])
    def test_range_quantile(self, seq):
        wt = WaveletTree(seq)
        wm = WaveletMatrix(seq)
        for l in range(len(seq)):
            for r in range(l + 1, len(seq) + 1):
                for k in range(r - l):
                    expected = sorted(seq[l:r])[k]
                    assert range_quantile(wt, l, r, k) == expected
                    assert range_quantile(wm, l, r, k) == expected

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi", "abcdefg"])
    def test_range_min_max(self, seq):
        wt = WaveletTree(seq)
        for l in range(len(seq)):
            for r in range(l + 1, len(seq) + 1):
                expected_min = min(seq[l:r])
                expected_max = max(seq[l:r])
                assert range_min(wt, l, r) == expected_min
                assert range_max(wt, l, r) == expected_max

    def test_range_min_empty(self):
        wt = WaveletTree("abc")
        with pytest.raises(ValueError):
            range_min(wt, 0, 0)

    def test_range_max_empty(self):
        wt = WaveletTree("abc")
        with pytest.raises(ValueError):
            range_max(wt, 0, 0)

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi"])
    def test_range_next_value(self, seq):
        wt = WaveletTree(seq)
        alphabet = sorted(set(seq))
        for threshold in alphabet:
            result = range_next_value(wt, 0, len(seq), threshold)
            expected = None
            for sym in alphabet:
                if sym >= threshold and seq.count(sym) > 0:
                    expected = sym
                    break
            assert result == expected

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi"])
    def test_range_prev_value(self, seq):
        wt = WaveletTree(seq)
        alphabet = sorted(set(seq))
        for threshold in alphabet:
            result = range_prev_value(wt, 0, len(seq), threshold)
            expected = None
            for sym in reversed(alphabet):
                if sym <= threshold and seq.count(sym) > 0:
                    expected = sym
                    break
            assert result == expected

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi", "abcdefg"])
    def test_interval_symbols(self, seq):
        wt = WaveletTree(seq)
        for l in range(len(seq) + 1):
            for r in range(l, len(seq) + 1):
                result = interval_symbols(wt, l, r)
                expected = {}
                for c in set(seq):
                    count = seq[l:r].count(c)
                    if count > 0:
                        expected[c] = count
                assert result == expected

    @pytest.mark.parametrize("seq", ["abracadabra", "mississippi"])
    def test_count_distinct(self, seq):
        wt = WaveletTree(seq)
        for l in range(len(seq) + 1):
            for r in range(l, len(seq) + 1):
                expected = len(set(seq[l:r]))
                assert count_distinct(wt, l, r) == expected

    def test_range_intersection(self):
        seq = "abracadabra"
        wt = WaveletTree(seq)
        result = range_intersection(wt, 0, 5, 6, 11)
        # "abrac" and "dabra"
        for sym, (c1, c2) in result.items():
            assert seq[:5].count(sym) == c1
            assert seq[6:11].count(sym) == c2

    def test_prefix_search(self):
        seq = "abracadabra"
        wt = WaveletTree(seq)
        # Find "ab"
        positions = prefix_search(wt, "ab")
        expected = [i for i in range(len(seq) - 1) if seq[i:i+2] == "ab"]
        assert positions == expected

    def test_prefix_search_empty(self):
        wt = WaveletTree("abc")
        result = prefix_search(wt, "")
        assert result == [0, 1, 2]

    def test_prefix_search_not_found(self):
        wt = WaveletTree("abc")
        assert prefix_search(wt, "xyz") == []

    def test_range_count_invalid(self):
        wt = WaveletTree("abc")
        with pytest.raises(ValueError):
            range_count(wt, "a", -1, 2)
        with pytest.raises(ValueError):
            range_count(wt, "a", 2, 1)

    def test_range_quantile_invalid_k(self):
        wt = WaveletTree("abc")
        with pytest.raises(ValueError):
            range_quantile(wt, 0, 3, -1)
        with pytest.raises(ValueError):
            range_quantile(wt, 0, 3, 3)


class TestSerialization:
    """Test JSON save/load roundtrip."""

    @pytest.mark.parametrize("struct_name,struct_class", [
        ("WaveletTree", WaveletTree),
        ("WaveletMatrix", WaveletMatrix),
        ("HuffmanWaveletTree", HuffmanWaveletTree),
        ("HuffmanWaveletMatrix", HuffmanWaveletMatrix),
    ])
    def test_save_load_roundtrip(self, struct_name, struct_class):
        seq = "abracadabra"
        wt = struct_class(seq)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save(wt, path)
            wt2 = load(path)
            assert len(wt2) == len(wt)
            for i in range(len(seq)):
                assert wt2.access(i) == seq[i]
            for c in set(seq):
                assert wt2.rank(c, len(seq)) == seq.count(c)
        finally:
            os.unlink(path)

    def test_save_unknown_type(self):
        with pytest.raises(TypeError):
            save("not a wavelet tree", "/tmp/test.json")

    def test_load_unknown_type(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"type": "Unknown", "sequence": []}, f)
            path = f.name
        try:
            with pytest.raises(ValueError):
                load(path)
        finally:
            os.unlink(path)

    def test_serialization_integer_symbols(self):
        """Test save/load with integer symbols (not just chars)."""
        seq = [1, 2, 3, 1, 2, 1]
        wt = WaveletTree(seq)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save(wt, path)
            wt2 = load(path)
            assert len(wt2) == len(wt)
            for i in range(len(seq)):
                assert wt2.access(i) == seq[i]
        finally:
            os.unlink(path)


class TestConfig:
    """Test configuration system."""

    def test_defaults(self):
        config = Config()
        assert config.structure == "tree"
        assert config.use_blocked is True
        assert config.log_level == "INFO"
        assert config.log_format == "text"

    def test_custom(self):
        config = Config(structure="matrix", use_blocked=False)
        assert config.structure == "matrix"
        assert config.use_blocked is False

    def test_invalid_structure(self):
        with pytest.raises(ValueError):
            Config(structure="invalid")

    def test_invalid_log_level(self):
        with pytest.raises(ValueError):
            Config(log_level="INVALID")

    def test_invalid_use_blocked(self):
        with pytest.raises(ValueError):
            Config(use_blocked="not a bool")

    def test_to_dict(self):
        config = Config()
        d = config.to_dict()
        assert d["structure"] == "tree"
        assert d["use_blocked"] is True

    def test_from_dict(self):
        config = Config.from_dict({"structure": "matrix"})
        assert config.structure == "matrix"

    def test_json_roundtrip(self):
        config = Config(structure="matrix", use_blocked=False)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.save(path)
            config2 = Config.from_file(path)
            assert config2.structure == "matrix"
            assert config2.use_blocked is False
        finally:
            os.unlink(path)

    def test_toml_roundtrip(self):
        config = Config(structure="matrix")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            path = f.name
        try:
            config.save(path)
            config2 = Config.from_file(path)
            assert config2.structure == "matrix"
        finally:
            os.unlink(path)

    def test_yaml_roundtrip(self):
        config = Config(structure="matrix")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            config.save(path)
            config2 = Config.from_file(path)
            assert config2.structure == "matrix"
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Config.from_file("/nonexistent/path.json")

    def test_from_dict_coerces_string_bool(self):
        """Config.from_dict should coerce string booleans from fallback parsers."""
        config = Config.from_dict({"use_blocked": "true"})
        assert config.use_blocked is True
        config = Config.from_dict({"use_blocked": "false"})
        assert config.use_blocked is False

    def test_toml_fallback_coerces_bool(self):
        """TOML fallback parser should produce a valid config."""
        import tempfile
        config = Config(structure="matrix", use_blocked=False)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('structure = "matrix"\nuse_blocked = false\n')
            path = f.name
        try:
            config2 = Config.from_file(path)
            assert config2.structure == "matrix"
            assert config2.use_blocked is False
        finally:
            os.unlink(path)