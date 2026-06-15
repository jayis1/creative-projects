"""Performance benchmarking utilities for compression codecs.

Provides comprehensive benchmarking with timing, memory estimation,
and comparison reports.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .rle import RLECodec
from .delta import DeltaCodec
from .pipeline import Pipeline, create_pipeline

# Import optional codecs
try:
    from .lzw import LZWCodec
    from .arithmetic import ArithmeticCodec
    _OPTIONAL_CODECS = {
        "lzw": LZWCodec,
        "arithmetic": ArithmeticCodec,
    }
except ImportError:
    _OPTIONAL_CODECS = {}


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single codec on a single input."""
    codec_name: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time_ms: float
    decompression_time_ms: float
    roundtrip_ok: bool
    throughput_mbps: float = 0.0

    @property
    def space_saving(self) -> float:
        """Space saving as a percentage (0-100)."""
        if self.original_size == 0:
            return 0.0
        return (1.0 - self.compressed_size / self.original_size) * 100


@dataclass
class BenchmarkReport:
    """Full benchmark report for multiple codecs on one or more inputs."""
    results: List[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult) -> None:
        """Add a benchmark result."""
        self.results.append(result)

    def best_ratio(self) -> Optional[BenchmarkResult]:
        """Get the result with the best compression ratio."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.compression_ratio)

    def fastest_compress(self) -> Optional[BenchmarkResult]:
        """Get the result with the fastest compression time."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.compression_time_ms)

    def fastest_decompress(self) -> Optional[BenchmarkResult]:
        """Get the result with the fastest decompression time."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.decompression_time_ms)

    def best_throughput(self) -> Optional[BenchmarkResult]:
        """Get the result with the best throughput."""
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.throughput_mbps)

    def to_table(self) -> str:
        """Format results as a text table."""
        lines = []
        lines.append(
            f"{'Codec':<18} {'Original':<10} {'Compressed':<10} "
            f"{'Ratio':<8} {'Saving':<8} {'Cmp ms':<8} {'Dec ms':<8} "
            f"{'OK?':<5} {'MB/s':<8}"
        )
        lines.append("-" * 87)

        for r in self.results:
            ok_str = "✓" if r.roundtrip_ok else "✗"
            lines.append(
                f"{r.codec_name:<18} {_fmt_size(r.original_size):<10} "
                f"{_fmt_size(r.compressed_size):<10} "
                f"{r.compression_ratio:.1%}   "
                f"{r.space_saving:.1f}%  "
                f"{r.compression_time_ms:.1f}    "
                f"{r.decompression_time_ms:.1f}    "
                f"{ok_str:<5} {r.throughput_mbps:.1f}"
            )

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "results": [
                {
                    "codec": r.codec_name,
                    "original_size": r.original_size,
                    "compressed_size": r.compressed_size,
                    "compression_ratio": r.compression_ratio,
                    "space_saving_pct": r.space_saving,
                    "compression_time_ms": r.compression_time_ms,
                    "decompression_time_ms": r.decompression_time_ms,
                    "roundtrip_ok": r.roundtrip_ok,
                    "throughput_mbps": r.throughput_mbps,
                }
                for r in self.results
            ]
        }


def _fmt_size(n: int) -> str:
    """Format a byte size with appropriate unit."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    elif n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    else:
        return f"{n / (1024 * 1024 * 1024):.2f} GB"


# Standard codecs available for benchmarking
STANDARD_CODECS = {
    "huffman": HuffmanCodec,
    "lz77": LZ77Codec,
    "bwt": BWTCodec,
    "deflate": DeflateCodec,
    "rle": RLECodec,
    "delta": DeltaCodec,
}

STANDARD_PIPELINES = [
    "rle+huffman",
    "rle+lz77",
    "rle+deflate",
    "delta+huffman",
    "delta+deflate",
]


def benchmark_codec(
    codec_name: str,
    codec,
    data: bytes,
    repeat: int = 1,
) -> BenchmarkResult:
    """Benchmark a single codec on data.

    Args:
        codec_name: Name identifier for the codec.
        codec: Codec instance with compress/decompress methods.
        data: Input data to benchmark on.
        repeat: Number of times to repeat for timing accuracy.

    Returns:
        BenchmarkResult with timing and compression metrics.
    """
    # Warm up
    try:
        compressed = codec.compress(data)
        decompressed = codec.decompress(compressed)
        roundtrip_ok = decompressed == data
    except Exception:
        return BenchmarkResult(
            codec_name=codec_name,
            original_size=len(data),
            compressed_size=0,
            compression_ratio=float("inf"),
            compression_time_ms=0,
            decompression_time_ms=0,
            roundtrip_ok=False,
            throughput_mbps=0,
        )

    # Timed runs
    total_compress_time = 0.0
    total_decompress_time = 0.0

    for _ in range(repeat):
        start = time.perf_counter()
        compressed = codec.compress(data)
        total_compress_time += time.perf_counter() - start

        start = time.perf_counter()
        decompressed = codec.decompress(compressed)
        total_decompress_time += time.perf_counter() - start

    compress_ms = (total_compress_time / repeat) * 1000
    decompress_ms = (total_decompress_time / repeat) * 1000

    # Throughput: original_size / total_time in MB/s
    total_time_s = total_compress_time / repeat + total_decompress_time / repeat
    throughput = (len(data) / (1024 * 1024)) / total_time_s if total_time_s > 0 else 0

    ratio = len(compressed) / len(data) if len(data) > 0 else 0

    return BenchmarkResult(
        codec_name=codec_name,
        original_size=len(data),
        compressed_size=len(compressed),
        compression_ratio=ratio,
        compression_time_ms=compress_ms,
        decompression_time_ms=decompress_ms,
        roundtrip_ok=roundtrip_ok,
        throughput_mbps=throughput,
    )


def run_benchmark(
    data: bytes,
    codecs: Optional[List[str]] = None,
    pipelines: Optional[List[str]] = None,
    include_pipelines: bool = True,
    repeat: int = 1,
) -> BenchmarkReport:
    """Run a comprehensive benchmark of codecs on input data.

    Args:
        data: Input data to benchmark on.
        codecs: List of codec names to test, or None for all standard codecs.
        pipelines: List of pipeline specs to test, or None for standard pipelines.
        include_pipelines: Whether to include pipeline benchmarks.
        repeat: Number of timing repetitions for accuracy.

    Returns:
        BenchmarkReport with results for all codecs.
    """
    all_codecs = {**STANDARD_CODECS, **_OPTIONAL_CODECS}

    report = BenchmarkReport()

    # Test individual codecs
    codec_list = codecs or list(all_codecs.keys())
    for name in codec_list:
        if name not in all_codecs:
            continue
        try:
            codec = all_codecs[name]()
            result = benchmark_codec(name, codec, data, repeat=repeat)
            report.add(result)
        except Exception as e:
            report.add(BenchmarkResult(
                codec_name=name,
                original_size=len(data),
                compressed_size=0,
                compression_ratio=float("inf"),
                compression_time_ms=0,
                decompression_time_ms=0,
                roundtrip_ok=False,
                throughput_mbps=0,
            ))

    # Test pipelines
    if include_pipelines:
        pipe_list = pipelines or STANDARD_PIPELINES
        for spec in pipe_list:
            try:
                pipe = create_pipeline(spec)
                result = benchmark_codec(spec, pipe, data, repeat=repeat)
                report.add(result)
            except Exception:
                report.add(BenchmarkResult(
                    codec_name=spec,
                    original_size=len(data),
                    compressed_size=0,
                    compression_ratio=float("inf"),
                    compression_time_ms=0,
                    decompression_time_ms=0,
                    roundtrip_ok=False,
                    throughput_mbps=0,
                ))

    return report