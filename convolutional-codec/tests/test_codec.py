from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from convolutional_codec import (
    CRC,
    AWGNChannel,
    BinarySymmetricChannel,
    BlockInterleaver,
    ConvolutionalCodec,
    GilbertElliottChannel,
    Trellis,
    analyze_codec,
    benchmark_awgn,
    benchmark_bsc,
    benchmark_burst,
    bpsk_modulate,
    hard_decide,
)
from convolutional_codec.cli import _parse_float_list
from convolutional_codec.config import load_config

PROJECT_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def codec() -> ConvolutionalCodec:
    return ConvolutionalCodec(Trellis(3, (0o7, 0o5)))


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "convolutional_codec", *args],
        cwd=PROJECT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )


def test_encode_known_sequence(codec: ConvolutionalCodec) -> None:
    assert codec.encode([1, 0, 1, 1]) == [1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1]


def test_round_trip_without_noise(codec: ConvolutionalCodec) -> None:
    payload = [1, 0, 1, 1, 0, 0, 1]
    encoded = codec.encode(payload)
    decoded = codec.decode(encoded)
    assert decoded.bits == payload
    assert decoded.path_metric == 0


def test_corrects_single_bit_error(codec: ConvolutionalCodec) -> None:
    payload = [1, 1, 0, 1, 0, 0]
    encoded = codec.encode(payload)
    encoded[3] ^= 1
    assert codec.decode(encoded).bits == payload


def test_channel_validation() -> None:
    with pytest.raises(ValueError):
        BinarySymmetricChannel(1.1)
    with pytest.raises(ValueError):
        GilbertElliottChannel(0.1, 0.2, good_error_probability=0.3, bad_error_probability=0.2)


def test_awgn_channel_emits_soft_values() -> None:
    samples = AWGNChannel(6.0, seed=3).transmit([0, 1, 0, 1])
    assert len(samples) == 4
    assert any(not float(sample).is_integer() for sample in samples)


def test_soft_decode_round_trip_without_noise(codec: ConvolutionalCodec) -> None:
    payload = [1, 0, 0, 1, 1]
    decoded = codec.decode_soft(bpsk_modulate(codec.encode(payload)))
    assert decoded.bits == payload


def test_punctured_codec_round_trip() -> None:
    codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)), puncture_pattern=(1, 1, 0, 1))
    payload = [1, 0, 1, 1, 0, 1]
    encoded = codec.encode(payload)
    assert codec.decode(encoded).bits == payload
    assert codec.decode_soft(bpsk_modulate(encoded)).bits == payload


def test_crc_frame_round_trip(codec: ConvolutionalCodec) -> None:
    crc = CRC(0b10011, width=4)
    payload = [1, 0, 1, 1, 0, 1, 0, 0]
    encoded = codec.encode_frame(payload, crc=crc)
    decoded = codec.decode_frame(encoded, crc=crc)
    assert decoded["payload_bits"] == payload
    assert decoded["crc_ok"] is True


def test_block_interleaver_round_trip() -> None:
    interleaver = BlockInterleaver(2, 3)
    payload = [0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1]
    assert interleaver.deinterleave(interleaver.interleave(payload)) == payload
    samples = [1.0, -0.2, 0.5, 0.7, -1.3, 0.1]
    assert interleaver.deinterleave(interleaver.interleave(samples)) == samples


def test_simulate_bsc_with_interleaver_and_crc(codec: ConvolutionalCodec) -> None:
    crc = CRC(0b10011, width=4)
    interleaver = BlockInterleaver(2, 14)
    payload = [1, 0, 1, 1, 0, 1, 0, 0]
    result = codec.simulate_bsc(payload, 0.0, seed=9, crc=crc, interleaver=interleaver)
    assert result["decoded_bits"] == payload
    assert result["crc_ok"] is True


def test_simulate_burst_with_interleaver_and_crc(codec: ConvolutionalCodec) -> None:
    crc = CRC(0b10011, width=4)
    interleaver = BlockInterleaver(2, 14)
    payload = [1, 0, 1, 1, 0, 1, 0, 0]
    result = codec.simulate_burst(
        payload,
        p_good_to_bad=0.05,
        p_bad_to_good=0.3,
        good_error_probability=0.0,
        bad_error_probability=0.1,
        seed=19,
        crc=crc,
        interleaver=interleaver,
    )
    assert result["decoded_bits"] == payload
    assert result["crc_ok"] is True


def test_hard_decision_helper() -> None:
    assert hard_decide([1.5, -0.1, 0.0, -2.0]) == [0, 1, 0, 1]


def test_parse_float_list_rejects_empty_fields() -> None:
    with pytest.raises(Exception):
        _parse_float_list("1.0,,2.0")


def test_benchmark_helpers(codec: ConvolutionalCodec) -> None:
    bits = [1, 0, 1, 1, 0, 1, 0, 0]
    bsc = benchmark_bsc(codec, [0.0, 0.03], bits=bits, trials=4, seed=4)
    awgn = benchmark_awgn(codec, [2.0, 4.0], bits=bits, trials=4, seed=5)
    burst = benchmark_burst(codec, [0.08, 0.16], bits=bits, trials=4, seed=6, p_good_to_bad=0.05, p_bad_to_good=0.3)
    assert len(bsc) == len(awgn) == len(burst) == 2
    assert bsc[0]["ber"] == 0.0


def test_analyze_codec(codec: ConvolutionalCodec) -> None:
    report = analyze_codec(codec, max_input_bits=5)
    assert report["state_count"] == 4
    assert report["distance_estimate"]["estimated_free_distance"] >= 1


def test_load_config() -> None:
    config = load_config(str(PROJECT_DIR / "examples" / "benchmark_config.toml"))
    assert config["command"]["name"] == "benchmark-burst"


def test_cli_encode() -> None:
    completed = run_cli("encode", "1011")
    assert completed.stdout.strip() == "111000010111"


def test_cli_decode() -> None:
    payload = json.loads(run_cli("decode", "111000010111", "--pretty").stdout)
    assert payload["bits"] == [1, 0, 1, 1]


def test_cli_decode_soft() -> None:
    payload = json.loads(run_cli("decode-soft", "--", "-1.0,1.0,-1.0,1.0,1.0,-1.0,1.0,-1.0,1.0,1.0").stdout)
    assert "bits" in payload


def test_cli_benchmark_burst() -> None:
    payload = json.loads(
        run_cli(
            "--pretty",
            "--crc-poly",
            "0b10011",
            "--crc-width",
            "4",
            "--interleave-rows",
            "2",
            "--interleave-cols",
            "14",
            "benchmark-burst",
            "--bits",
            "10110100",
            "--bad-error-prob",
            "0.08,0.16",
            "--p-good-to-bad",
            "0.05",
            "--p-bad-to-good",
            "0.3",
            "--trials",
            "4",
            "--frame",
            "--seed",
            "7",
        ).stdout
    )
    assert payload["channel"] == "gilbert-elliott"
    assert len(payload["series"]) == 2


def test_cli_run_config() -> None:
    payload = json.loads(run_cli("run-config", "examples/benchmark_config.toml").stdout)
    assert payload["channel"] == "gilbert-elliott"
    assert len(payload["series"]) == 3
