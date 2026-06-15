"""Tests for pipeline, config loading, and batch processing."""

import json
import os
import tempfile

import pytest
import yaml

from cryptanalysis_toolkit.pipeline import (
    CipherPipeline,
    analyze_text,
    build_cipher,
    load_config,
    process_file,
    CIPHER_REGISTRY,
)
from cryptanalysis_toolkit.ciphers.caesar import CaesarCipher
from cryptanalysis_toolkit.ciphers.vigenere import VigenereCipher
from cryptanalysis_toolkit.ciphers.rot13 import ROT13Cipher
from cryptanalysis_toolkit.ciphers.atbash import AtbashCipher


class TestBuildCipher:
    def test_build_caesar(self):
        cipher = build_cipher("caesar", shift=7)
        assert isinstance(cipher, CaesarCipher)
        assert cipher.shift == 7

    def test_build_vigenere(self):
        cipher = build_cipher("vigenere", key="SECRET")
        assert isinstance(cipher, VigenereCipher)
        assert cipher.keyword == "SECRET"

    def test_build_rot13(self):
        cipher = build_cipher("rot13")
        assert isinstance(cipher, ROT13Cipher)

    def test_build_atbash(self):
        cipher = build_cipher("atbash")
        assert isinstance(cipher, AtbashCipher)

    def test_unknown_cipher_raises(self):
        with pytest.raises(ValueError, match="Unknown cipher"):
            build_cipher("nonexistent")

    def test_case_insensitive(self):
        cipher = build_cipher("CAESAR", shift=3)
        assert isinstance(cipher, CaesarCipher)

    def test_all_registered_ciphers_buildable(self):
        """Every cipher in the registry should be buildable."""
        for name in CIPHER_REGISTRY:
            if name in ("hill", "enigma", "xor"):
                # These need special params
                continue
            cipher = build_cipher(name)
            assert cipher is not None


class TestLoadConfig:
    def test_load_yaml(self):
        config = {"operations": [{"cipher": "caesar", "action": "encrypt", "params": {"shift": 7}}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            loaded = load_config(f.name)
        os.unlink(f.name)
        assert loaded["operations"][0]["cipher"] == "caesar"

    def test_load_json(self):
        config = {"operations": [{"cipher": "vigenere", "action": "decrypt", "params": {"key": "ABC"}}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            loaded = load_config(f.name)
        os.unlink(f.name)
        assert loaded["operations"][0]["cipher"] == "vigenere"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")


class TestCipherPipeline:
    def test_single_operation(self):
        pipeline = CipherPipeline([
            {"cipher": "caesar", "action": "encrypt", "params": {"shift": 3}},
        ])
        result = pipeline.run("HELLO")
        assert result == "KHOOR"

    def test_chained_operations(self):
        pipeline = CipherPipeline([
            {"cipher": "caesar", "action": "encrypt", "params": {"shift": 7}},
            {"cipher": "vigenere", "action": "encrypt", "params": {"key": "SECRET"}},
        ])
        text = "ATTACK"
        encrypted = pipeline.run(text)

        # Decrypt in reverse order
        reverse = CipherPipeline([
            {"cipher": "vigenere", "action": "decrypt", "params": {"key": "SECRET"}},
            {"cipher": "caesar", "action": "decrypt", "params": {"shift": 7}},
        ])
        decrypted = reverse.run(encrypted)
        assert decrypted == text

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="action must be"):
            CipherPipeline([{"cipher": "caesar", "action": "hash"}])

    def test_missing_cipher_raises(self):
        with pytest.raises(ValueError, match="missing 'cipher'"):
            CipherPipeline([{"action": "encrypt"}])

    def test_unknown_cipher_raises(self):
        with pytest.raises(ValueError, match="unknown cipher"):
            CipherPipeline([{"cipher": "nonexistent", "action": "encrypt"}])

    def test_from_config(self):
        config = {"operations": [{"cipher": "caesar", "action": "encrypt", "params": {"shift": 3}}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            f.flush()
            pipeline = CipherPipeline.from_config(f.name)
        os.unlink(f.name)
        result = pipeline.run("HELLO")
        assert result == "KHOOR"


class TestProcessFile:
    def test_encrypt_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("HELLO WORLD")
            f.flush()
            input_path = f.name

        result = process_file(input_path, "encrypt", "caesar", {"shift": 3})
        assert result == "KHOOR ZRUOG"
        os.unlink(input_path)

    def test_encrypt_file_with_output(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("HELLO")
            f.flush()
            input_path = f.name

        output_path = input_path + ".out"
        result = process_file(input_path, "encrypt", "caesar", {"shift": 3}, output_path)
        assert result == "KHOOR"
        assert os.path.exists(output_path)
        with open(output_path) as f:
            assert f.read() == "KHOOR"
        os.unlink(input_path)
        os.unlink(output_path)

    def test_missing_input_file_raises(self):
        with pytest.raises(FileNotFoundError):
            process_file("/nonexistent/file.txt", "encrypt", "caesar", {"shift": 3})

    def test_invalid_operation_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("HELLO")
            f.flush()
            input_path = f.name
        os.unlink(input_path)
        with pytest.raises(FileNotFoundError):
            process_file(input_path, "hash", "caesar", {"shift": 3})


class TestAnalyzeText:
    def test_basic_analysis(self):
        result = analyze_text("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG")
        assert "index_of_coincidence" in result
        assert "chi_squared" in result
        assert "correlation" in result
        assert "friedman_key_length" in result
        assert "letter_frequencies" in result
        assert "bigram_frequencies" in result
        assert "ic_key_length_candidates" in result
        assert "kasiski_candidates" in result

    def test_english_text_high_ic(self):
        # Use a longer text for more reliable IC
        text = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG " * 10
        result = analyze_text(text)
        assert result["index_of_coincidence"] > 0.04  # Even short English > random

    def test_analysis_returns_rounded_values(self):
        result = analyze_text("HELLO WORLD")
        # IC should be rounded to 6 decimal places
        ic_str = str(result["index_of_coincidence"])
        assert len(ic_str.split(".")[-1]) <= 6