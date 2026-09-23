"""Tests for the Markov chain CLI integration."""

import json
import subprocess
import sys
import tempfile
import os


def run_cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "prose_forge", *args],
        capture_output=True, text=True, timeout=30,
    )


CORPUS = (
    "The quick brown fox jumps over the lazy dog. "
    "The lazy dog sleeps while the quick fox runs. "
    "A brown fox and a lazy dog are good friends. "
    "The fox is quick and the dog is lazy. "
    "Quick foxes and lazy dogs are everywhere."
)


class TestMarkovCLI:
    def test_markov_word_level(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(CORPUS)
            f.flush()
            path = f.name
        try:
            result = run_cli("markov", "--train", path, "--order", "2", "--length", "15", "--seed", "42")
            assert result.returncode == 0
            words = result.stdout.strip().split()
            assert len(words) <= 15
        finally:
            os.unlink(path)

    def test_markov_char_level(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(CORPUS)
            f.flush()
            path = f.name
        try:
            result = run_cli("markov", "--train", path, "--order", "3", "--level", "char", "--length", "50", "--seed", "42")
            assert result.returncode == 0
            assert len(result.stdout) > 0
        finally:
            os.unlink(path)

    def test_markov_reproducible(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(CORPUS)
            f.flush()
            path = f.name
        try:
            r1 = run_cli("markov", "--train", path, "--order", "2", "--length", "30", "--seed", "77")
            r2 = run_cli("markov", "--train", path, "--order", "2", "--length", "30", "--seed", "77")
            assert r1.stdout == r2.stdout
        finally:
            os.unlink(path)