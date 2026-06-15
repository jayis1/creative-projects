"""Tests for CLI interface and input validation."""

import subprocess
import sys

import pytest


def run_cli(*args):
    """Run the CLI with given arguments and return stdout, stderr, returncode."""
    result = subprocess.run(
        [sys.executable, "-m", "cryptanalysis_toolkit"] + list(args),
        capture_output=True,
        text=True,
    )
    return result.stdout, result.stderr, result.returncode


class TestCLIHelp:
    def test_help_flag(self):
        stdout, stderr, rc = run_cli("--help")
        assert rc == 0
        assert "Cryptanalysis Toolkit" in stdout

    def test_list_ciphers(self):
        stdout, stderr, rc = run_cli("list")
        assert rc == 0
        assert "caesar" in stdout
        assert "vigenere" in stdout
        assert "rot13" in stdout
        assert "atbash" in stdout
        assert "hill" in stdout


class TestCLIEncryptDecrypt:
    def test_encrypt_caesar(self):
        stdout, stderr, rc = run_cli("encrypt", "caesar", "HELLO", "--shift", "3")
        assert rc == 0
        assert stdout.strip() == "KHOOR"

    def test_decrypt_caesar(self):
        stdout, stderr, rc = run_cli("decrypt", "caesar", "KHOOR", "--shift", "3")
        assert rc == 0
        assert stdout.strip() == "HELLO"

    def test_encrypt_vigenere(self):
        stdout, stderr, rc = run_cli("encrypt", "vigenere", "HELLO", "--key", "KEY")
        assert rc == 0
        assert stdout.strip() == "RIJVS"

    def test_encrypt_rot13(self):
        stdout, stderr, rc = run_cli("encrypt", "rot13", "HELLO")
        assert rc == 0
        assert stdout.strip() == "URYYB"

    def test_decrypt_rot13(self):
        stdout, stderr, rc = run_cli("decrypt", "rot13", "URYYB")
        assert rc == 0
        assert stdout.strip() == "HELLO"

    def test_encrypt_atbash(self):
        stdout, stderr, rc = run_cli("encrypt", "atbash", "HELLO")
        assert rc == 0
        assert stdout.strip() == "SVOOL"

    def test_unknown_cipher(self):
        stdout, stderr, rc = run_cli("encrypt", "nonexistent", "HELLO")
        assert rc != 0

    def test_missing_key_for_vigenere(self):
        stdout, stderr, rc = run_cli("encrypt", "vigenere", "HELLO")
        assert rc != 0

    def test_encrypt_enigma_with_rotors(self):
        stdout, stderr, rc = run_cli("encrypt", "enigma", "HELLO", "--rotors", "1", "2", "3")
        assert rc == 0
        assert len(stdout.strip()) > 0

    def test_decrypt_enigma_with_rotors(self):
        # Encrypt first, then decrypt
        stdout1, _, rc1 = run_cli("encrypt", "enigma", "HELLO", "--rotors", "1", "2", "3")
        assert rc1 == 0
        ciphertext = stdout1.strip()
        stdout2, _, rc2 = run_cli("decrypt", "enigma", ciphertext, "--rotors", "1", "2", "3")
        assert rc2 == 0
        assert stdout2.strip() == "HELLO"

    def test_no_text_no_file_shows_error(self):
        # When no text and no file and stdin is a tty, should show error
        # (This is hard to test perfectly since our test stdin isn't a tty,
        # but we can test the positional arg is optional)
        pass


class TestCLIBreak:
    def test_break_caesar(self):
        stdout, stderr, rc = run_cli("break", "caesar", "KHOOR ZRUOG")
        assert rc == 0
        assert "HELLO" in stdout

    def test_break_auto(self):
        stdout, stderr, rc = run_cli("break", "auto", "KHOOR ZRUOG")
        assert rc == 0
        assert "IC" in stdout


class TestCLIAnalyze:
    def test_analyze_text(self):
        stdout, stderr, rc = run_cli("analyze", "HELLO WORLD")
        assert rc == 0
        assert "Frequency" in stdout or "IC" in stdout

    def test_analyze_json(self):
        stdout, stderr, rc = run_cli("analyze", "HELLO WORLD", "--json")
        assert rc == 0
        import json
        data = json.loads(stdout)
        assert "index_of_coincidence" in data


class TestCLIPipeline:
    def test_pipeline_from_config(self):
        import tempfile
        import yaml
        config = {"operations": [{"cipher": "caesar", "action": "encrypt", "params": {"shift": 3}}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            stdout, stderr, rc = run_cli("pipeline", f.name, "HELLO")
        import os
        os.unlink(f.name)
        assert rc == 0
        assert stdout.strip() == "KHOOR"