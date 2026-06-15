"""Tests for benchmarking module."""

import pytest
from compression_engine.benchmark import (
    BenchmarkResult, BenchmarkReport, run_benchmark, benchmark_codec,
    _fmt_size,
)
from compression_engine.deflate import DeflateCodec
from compression_engine.huffman import HuffmanCodec


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_space_saving(self):
        result = BenchmarkResult(
            codec_name="test", original_size=1000, compressed_size=400,
            compression_ratio=0.4, compression_time_ms=10.0,
            decompression_time_ms=5.0, roundtrip_ok=True, throughput_mbps=50.0,
        )
        assert result.space_saving == 60.0

    def test_space_saving_zero_size(self):
        result = BenchmarkResult(
            codec_name="test", original_size=0, compressed_size=0,
            compression_ratio=0.0, compression_time_ms=10.0,
            decompression_time_ms=5.0, roundtrip_ok=True, throughput_mbps=0.0,
        )
        assert result.space_saving == 0.0


class TestBenchmarkReport:
    """Test BenchmarkReport."""

    def test_empty_report(self):
        report = BenchmarkReport()
        assert report.best_ratio() is None
        assert report.fastest_compress() is None

    def test_add_result(self):
        report = BenchmarkReport()
        result = BenchmarkResult(
            codec_name="deflate", original_size=1000, compressed_size=400,
            compression_ratio=0.4, compression_time_ms=10.0,
            decompression_time_ms=5.0, roundtrip_ok=True, throughput_mbps=50.0,
        )
        report.add(result)
        assert report.best_ratio() == result
        assert report.fastest_compress() == result

    def test_to_table(self):
        report = BenchmarkReport()
        result = BenchmarkResult(
            codec_name="deflate", original_size=1000, compressed_size=400,
            compression_ratio=0.4, compression_time_ms=10.0,
            decompression_time_ms=5.0, roundtrip_ok=True, throughput_mbps=50.0,
        )
        report.add(result)
        table = report.to_table()
        assert "deflate" in table
        assert "1000 B" in table

    def test_to_dict(self):
        report = BenchmarkReport()
        result = BenchmarkResult(
            codec_name="deflate", original_size=1000, compressed_size=400,
            compression_ratio=0.4, compression_time_ms=10.0,
            decompression_time_ms=5.0, roundtrip_ok=True, throughput_mbps=50.0,
        )
        report.add(result)
        d = report.to_dict()
        assert "results" in d
        assert len(d["results"]) == 1
        assert d["results"][0]["codec"] == "deflate"


class TestBenchmarkCodec:
    """Test benchmark_codec function."""

    def test_benchmark_deflate(self):
        codec = DeflateCodec()
        data = b"hello world! " * 100
        result = benchmark_codec("deflate", codec, data)
        assert result.codec_name == "deflate"
        assert result.original_size == len(data)
        assert result.roundtrip_ok is True
        assert result.compression_ratio < 1.0

    def test_benchmark_huffman(self):
        codec = HuffmanCodec()
        data = b"a" * 500 + b"b" * 300 + b"c" * 200
        result = benchmark_codec("huffman", codec, data)
        assert result.roundtrip_ok is True


class TestRunBenchmark:
    """Test run_benchmark function."""

    def test_run_benchmark_specific_codecs(self):
        data = b"test data for benchmarking" * 50
        report = run_benchmark(data, codecs=["deflate", "huffman"], include_pipelines=False)
        assert len(report.results) >= 2

    def test_run_benchmark_with_pipelines(self):
        data = b"test data" * 50
        report = run_benchmark(data, include_pipelines=True)
        # Should have individual codecs + pipelines
        assert len(report.results) > 6


class TestFmtSize:
    """Test size formatting."""

    def test_bytes(self):
        assert _fmt_size(100) == "100 B"

    def test_kilobytes(self):
        assert "KB" in _fmt_size(2048)

    def test_megabytes(self):
        assert "MB" in _fmt_size(5 * 1024 * 1024)