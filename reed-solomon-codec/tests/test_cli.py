"""Tests for the CLI interface.

Tests cover:
- Help text and version output
- Encode/decode round-trip via CLI
- Demo subcommand
- Config generation and validation
- Stream mode
- Benchmark subcommand
- Info subcommand
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

from reed_solomon.cli import main, build_parser
from reed_solomon import __version__


# ---------------------------------------------------------------------------
# Helper to run CLI in-process
# ---------------------------------------------------------------------------


def run_cli(*args: str) -> tuple[int, str, str]:
    """Run the CLI with given args, returning (exit_code, stdout, stderr)."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        code = main(list(args))
    return code, out_buf.getvalue(), err_buf.getvalue()


# ---------------------------------------------------------------------------
# Version and help
# ---------------------------------------------------------------------------


class TestCLIBasic:
    """Basic CLI tests."""

    def test_version_flag(self):
        code, out, _ = run_cli("--version")
        assert code == 0
        assert __version__ in out

    def test_version_subcommand(self):
        code, out, _ = run_cli("version")
        assert code == 0
        assert __version__ in out

    def test_no_command_prints_help(self):
        code, out, _ = run_cli()
        assert code == 1
        assert "usage:" in out.lower() or "rsc" in out.lower()

    def test_parser_help(self):
        parser = build_parser()
        help_text = parser.format_help()
        assert "encode" in help_text
        assert "decode" in help_text
        assert "demo" in help_text
        assert "bench" in help_text


# ---------------------------------------------------------------------------
# Encode / decode round-trip
# ---------------------------------------------------------------------------


class TestCLIEncodeDecode:
    """Test encode/decode subcommands."""

    def test_encode_decode_roundtrip(self, tmp_path):
        data = b"Hello, Reed-Solomon!"
        in_file = tmp_path / "input.txt"
        enc_file = tmp_path / "encoded.rs"
        dec_file = tmp_path / "decoded.txt"

        in_file.write_bytes(data)

        # Encode
        code, out, err = run_cli("encode", str(in_file), str(enc_file), "--nsym", "10")
        assert code == 0, f"Encode failed: {err}"
        assert enc_file.exists()
        encoded = enc_file.read_bytes()
        assert len(encoded) == len(data) + 10

        # Decode
        code, out, err = run_cli("decode", str(enc_file), str(dec_file), "--nsym", "10")
        assert code == 0, f"Decode failed: {err}"
        assert dec_file.read_bytes() == data

    def test_encode_decode_with_errors(self, tmp_path):
        data = b"Error correction is amazing!"
        in_file = tmp_path / "input.bin"
        enc_file = tmp_path / "encoded.rs"
        dec_file = tmp_path / "decoded.bin"

        in_file.write_bytes(data)

        # Encode
        run_cli("encode", str(in_file), str(enc_file), "--nsym", "16")
        encoded = bytearray(enc_file.read_bytes())

        # Inject 5 errors (max for nsym=16 is 8)
        for i in [0, 5, 10, 15, 20]:
            if i < len(encoded):
                encoded[i] ^= 0xFF
        enc_file.write_bytes(bytes(encoded))

        # Decode
        code, out, err = run_cli("decode", str(enc_file), str(dec_file), "--nsym", "16")
        assert code == 0, f"Decode failed: {err}"
        assert dec_file.read_bytes() == data

    def test_encode_default_output_name(self, tmp_path):
        in_file = tmp_path / "myfile.txt"
        in_file.write_bytes(b"test data")
        code, out, _ = run_cli("encode", str(in_file), "--nsym", "10")
        assert code == 0
        assert (tmp_path / "myfile.txt.rs").exists()

    def test_decode_strips_rs_extension(self, tmp_path):
        in_file = tmp_path / "data.txt"
        enc_file = tmp_path / "data.rs"
        in_file.write_bytes(b"strip test")
        run_cli("encode", str(in_file), str(enc_file), "--nsym", "10")
        # Decode without explicit output → should strip .rs
        code, out, _ = run_cli("decode", str(enc_file), "--nsym", "10")
        assert code == 0
        assert (tmp_path / "data").exists()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


class TestCLIDemo:
    """Test demo subcommands."""

    def test_demo_runs(self):
        code, out, _ = run_cli("demo", "--nsym", "10")
        assert code == 0
        assert "SUCCESS" in out

    def test_burst_demo_runs(self):
        code, out, _ = run_cli("burst-demo", "--nsym", "10", "--depth", "4")
        assert code == 0
        assert "SUCCESS" in out


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------


class TestCLIInfo:
    """Test info subcommand."""

    def test_info_runs(self):
        code, out, _ = run_cli("info", "--nsym", "16")
        assert code == 0
        assert "Reed-Solomon" in out
        assert "16" in out


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestCLIConfig:
    """Test config subcommand."""

    def test_config_generate_json(self, tmp_path):
        path = tmp_path / "config.json"
        code, out, _ = run_cli("config", "--generate", str(path), "--nsym", "20")
        assert code == 0
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["nsym"] == 20

    def test_config_validate(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"nsym": 16, "interleaving_depth": 4, "log_level": "INFO",
                                     "log_file": None, "log_format": "%(message)s"}))
        code, out, _ = run_cli("config", "--validate", str(path))
        assert code == 0
        assert "valid" in out.lower()

    def test_config_validate_bad(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"nsym": -5}))
        code, _, err = run_cli("config", "--validate", str(path))
        assert code == 1

    def test_config_defaults(self):
        code, out, _ = run_cli("config")
        assert code == 0
        assert "nsym" in out


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------


class TestCLIStream:
    """Test stream subcommand."""

    def test_stream_encode_decode(self, tmp_path):
        """Test stream encode then decode via temp files to avoid stdin mocking."""
        data = b"Stream test data!"
        # Write input to a temp file and use it as stdin
        in_file = tmp_path / "stdin.bin"
        enc_file = tmp_path / "stdout.bin"
        dec_file = tmp_path / "dec_in.bin"
        out_file = tmp_path / "dec_out.bin"

        in_file.write_bytes(data)

        # Encode: simulate stdin from file, stdout to file
        import shutil
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        # Encode
        sys.stdin = _BinaryStdin(in_file)
        sys.stdout = _BinaryStdout(enc_file)
        try:
            code = main(["stream", "encode", "--nsym", "10"])
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        assert code == 0
        encoded = enc_file.read_bytes()
        assert len(encoded) == len(data) + 10

        # Decode
        dec_file.write_bytes(encoded)
        sys.stdin = _BinaryStdin(dec_file)
        sys.stdout = _BinaryStdout(out_file)
        try:
            code = main(["stream", "decode", "--nsym", "10"])
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        assert code == 0
        assert out_file.read_bytes() == data


class _BinaryStdin:
    """Helper to mock sys.stdin with a .buffer attribute."""

    def __init__(self, path: Path):
        self._buf = open(path, "rb")

    @property
    def buffer(self):
        return self._buf


class _BinaryStdout:
    """Helper to mock sys.stdout with a .buffer attribute."""

    def __init__(self, path: Path):
        self._buf = open(path, "wb")

    @property
    def buffer(self):
        return self._buf

    def write(self, s):
        pass  # discard text output

    def flush(self):
        pass


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


class TestCLIBench:
    """Test bench subcommand."""

    def test_bench_runs(self):
        code, out, _ = run_cli("bench", "--nsym", "10", "--size", "50", "--iterations", "5")
        assert code == 0
        assert "Benchmark" in out
        assert "Throughput" in out


# ---------------------------------------------------------------------------
# Interleaved encode/decode via CLI
# ---------------------------------------------------------------------------


class TestCLIInterleave:
    """Test interleaved encode/decode."""

    def test_interleaved_roundtrip(self, tmp_path):
        data = b"Interleaved burst protection test data!!"  # 40 bytes
        in_file = tmp_path / "input.bin"
        enc_file = tmp_path / "encoded.rs"
        dec_file = tmp_path / "decoded.bin"

        in_file.write_bytes(data)

        # Encode with interleaving
        code, _, err = run_cli("encode", str(in_file), str(enc_file),
                               "--nsym", "10", "--interleave", "4")
        assert code == 0, err

        # Inject a burst error
        encoded = bytearray(enc_file.read_bytes())
        for i in range(15):  # burst of 15 (depth=4 * nsym//2=5 = 20 max)
            if 5 + i < len(encoded):
                encoded[5 + i] ^= 0xFF
        enc_file.write_bytes(bytes(encoded))

        # Decode with interleaving
        code, _, err = run_cli("decode", str(enc_file), str(dec_file),
                               "--nsym", "10", "--interleave", "4")
        assert code == 0, err
        assert dec_file.read_bytes() == data