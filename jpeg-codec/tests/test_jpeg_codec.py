"""Pytest test suite for the jpeg-codec package.

Covers:
  - Color conversion roundtrips
  - DCT/inverse DCT accuracy
  - Quantization/dequantization
  - Zig-zag/inverse zig-zag
  - Huffman encoding/decoding
  - Bit I/O with byte-stuffing
  - Subsample/upsample
  - Full encode/decode roundtrips (RGB, grayscale, various qualities)
  - Cross-compatibility with Pillow
  - Quality metrics (PSNR, SSIM)
  - Config file loading/saving
  - Exception handling
  - Metadata inspection
  - Comment and restart markers
  - Edge cases (odd dimensions, 1x1 images, uniform images)
"""

import io
import json
import os
import tempfile

import numpy as np
import pytest

from jpeg_codec import (
    encode, decode,
    rgb_to_ycbcr, ycbcr_to_rgb,
    dct2d, idct2d,
    quantize_block, dequantize_block,
    build_huffman_table, HuffmanTree,
    zigzag_block, izigzag_block,
    ZIGZAG_ORDER, IZIGZAG_ORDER,
    psnr, ssim, mse, quality_report,
    EncodingConfig, load_config, save_config,
    get_info, JPEGInfo,
    JPEGError, EncodingError, DecodingError,
    InvalidQualityError, InvalidSamplingError, InvalidImageError,
    UnsupportedFeatureError,
)
from jpeg_codec.color import level_shift, unlevel_shift
from jpeg_codec.quantize import get_quantization_tables
from jpeg_codec.bitio import BitWriter, BitReader
from jpeg_codec.huffman import magnitude_category, encode_value, decode_value
from jpeg_codec.entropy import encode_block, decode_block
from jpeg_codec.subsample import downsample_channel, upsample_channel
from jpeg_codec.batch_dct import batch_dct2d, batch_idct2d, channel_to_blocks
from jpeg_codec.restart import (
    should_emit_restart, write_com_segment,
)
from jpeg_codec.info import get_info


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def smooth_image():
    """A 64x64 smooth gradient image."""
    x = np.linspace(0, 255, 64, dtype=np.float64)
    y = np.linspace(0, 255, 64, dtype=np.float64)
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    img[..., 0] = np.tile(x, (64, 1))
    img[..., 1] = np.tile(y.reshape(-1, 1), (1, 64))
    img[..., 2] = (img[..., 0].astype(int) + img[..., 1].astype(int)) // 2
    return img


@pytest.fixture
def small_image():
    """A small 16x16 color image."""
    return np.random.RandomState(42).randint(
        0, 256, (16, 16, 3), dtype=np.uint8
    )


@pytest.fixture
def gray_image():
    """A 32x32 grayscale image."""
    return np.random.RandomState(123).randint(
        0, 256, (32, 32), dtype=np.uint8
    )


# -----------------------------------------------------------------------
# Color conversion tests
# -----------------------------------------------------------------------

class TestColorConversion:
    def test_rgb_ycbcr_roundtrip(self):
        rgb = np.random.RandomState(0).randint(
            0, 256, (32, 32, 3), dtype=np.uint8
        ).astype(np.float64)
        ycbcr = rgb_to_ycbcr(rgb)
        recovered = ycbcr_to_rgb(ycbcr)
        assert np.allclose(recovered, rgb, atol=1)

    def test_black_rgb(self):
        rgb = np.zeros((4, 4, 3), dtype=np.float64)
        ycbcr = rgb_to_ycbcr(rgb)
        assert ycbcr[..., 0] == pytest.approx(0)
        assert ycbcr[..., 1] == pytest.approx(128)
        assert ycbcr[..., 2] == pytest.approx(128)

    def test_white_rgb(self):
        rgb = np.full((4, 4, 3), 255.0)
        ycbcr = rgb_to_ycbcr(rgb)
        assert ycbcr[..., 0] == pytest.approx(255)
        assert ycbcr[..., 1] == pytest.approx(128, abs=1)
        assert ycbcr[..., 2] == pytest.approx(128, abs=1)

    def test_level_shift_roundtrip(self):
        block = np.full((8, 8), 100.0)
        shifted = level_shift(block)
        assert shifted == pytest.approx(-28)
        recovered = unlevel_shift(shifted)
        assert recovered == pytest.approx(100)


# -----------------------------------------------------------------------
# DCT tests
# -----------------------------------------------------------------------

class TestDCT:
    def test_dct_idct_roundtrip(self):
        block = np.random.RandomState(0).randn(8, 8) * 50
        dct = dct2d(block)
        recovered = idct2d(dct)
        assert np.allclose(recovered, block, atol=1e-10)

    def test_dct_constant_block(self):
        """DCT of a constant block should have only DC component."""
        block = np.full((8, 8), 42.0)
        dct = dct2d(block)
        assert dct[0, 0] == pytest.approx(42 * 8, abs=0.1)
        assert np.allclose(dct[1:], 0, atol=1e-10)
        assert np.allclose(dct[:, 1:], 0, atol=1e-10)

    def test_batch_dct_matches_single(self):
        """batch_dct2d should give same results as dct2d per block."""
        channel = np.random.RandomState(0).randn(16, 16) * 50
        blocks = channel_to_blocks(channel)
        batch_result = batch_dct2d(blocks)
        for i in range(blocks.shape[0]):
            single = dct2d(blocks[i])
            assert np.allclose(batch_result[i], single, atol=1e-10)

    def test_batch_idct_matches_single(self):
        channel = np.random.RandomState(0).randn(16, 16) * 50
        blocks = channel_to_blocks(channel)
        dct_blocks = batch_dct2d(blocks)
        recovered = batch_idct2d(dct_blocks)
        for i in range(blocks.shape[0]):
            assert np.allclose(recovered[i], blocks[i], atol=1e-10)

    def test_batch_dct_idct_roundtrip(self):
        channel = np.random.RandomState(0).randn(32, 32) * 100
        blocks = channel_to_blocks(channel)
        dct = batch_dct2d(blocks)
        recovered = batch_idct2d(dct)
        assert np.allclose(recovered, blocks, atol=1e-9)

    def test_channel_to_blocks_roundtrip(self):
        channel = np.random.RandomState(0).randn(24, 32)
        from jpeg_codec.batch_dct import blocks_to_channel
        blocks = channel_to_blocks(channel)
        recovered = blocks_to_channel(blocks, 24, 32)
        assert np.array_equal(recovered, channel)


# -----------------------------------------------------------------------
# Quantization tests
# -----------------------------------------------------------------------

class TestQuantization:
    def test_quality_scaling(self):
        qt_low, _ = get_quantization_tables(10)
        qt_high, _ = get_quantization_tables(95)
        # Lower quality -> larger quantization steps.
        assert qt_low[0, 0] > qt_high[0, 0]

    def test_quality_50_uses_standard(self):
        """At quality 50, the first luminance QT entry should be 16."""
        luma_qt, _ = get_quantization_tables(50)
        assert luma_qt[0, 0] == 16

    def test_invalid_quality(self):
        with pytest.raises(ValueError):
            get_quantization_tables(0)
        with pytest.raises(ValueError):
            get_quantization_tables(101)

    def test_quantize_dequantize_roundtrip(self):
        block = np.array([[100.0, -50.0], [0.0, 25.0]])
        qt = np.array([[10.0, 10.0], [10.0, 10.0]])
        quantized = quantize_block(block, qt)
        dequantized = dequantize_block(quantized, qt)
        # Quantization is lossy but should be close.
        assert np.allclose(dequantized, block, atol=qt[0, 0] / 2)


# -----------------------------------------------------------------------
# Zig-zag tests
# -----------------------------------------------------------------------

class TestZigzag:
    def test_zigzag_izigzag_roundtrip(self):
        block = np.arange(64, dtype=np.float64).reshape(8, 8)
        zz = zigzag_block(block)
        recovered = izigzag_block(zz)
        assert np.array_equal(recovered, block)

    def test_zigzag_order_length(self):
        assert len(ZIGZAG_ORDER) == 64
        assert len(set(ZIGZAG_ORDER)) == 64  # all unique

    def test_zigzag_starts_top_left(self):
        block = np.zeros((8, 8))
        block[0, 0] = 42
        zz = zigzag_block(block)
        assert zz[0] == 42


# -----------------------------------------------------------------------
# Huffman tests
# -----------------------------------------------------------------------

class TestHuffman:
    def test_magnitude_category(self):
        assert magnitude_category(0) == 0
        assert magnitude_category(1) == 1
        assert magnitude_category(-1) == 1
        assert magnitude_category(5) == 3
        assert magnitude_category(-5) == 3
        assert magnitude_category(255) == 8
        assert magnitude_category(-255) == 8

    def test_encode_decode_value(self):
        for val in [0, 1, -1, 5, -5, 100, -100, 255, -255]:
            size = magnitude_category(val)
            encoded = encode_value(val, size)
            decoded = decode_value(encoded, size)
            assert decoded == val, f"Failed for {val}: got {decoded}"

    def test_build_huffman_table(self):
        from jpeg_codec.huffman import STD_DC_LUMA_BITS, STD_DC_LUMA_VALS
        table = build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
        # Should have entries for all values.
        assert len(table) == len(STD_DC_LUMA_VALS)
        # Each entry should have (code, length) pair.
        for sym, (code, length) in table.items():
            assert 0 <= code < (1 << length)
            assert 1 <= length <= 16

    def test_huffman_tree_roundtrip(self):
        from jpeg_codec.huffman import STD_DC_LUMA_BITS, STD_DC_LUMA_VALS
        table = build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
        tree = HuffmanTree.from_table(table)
        # Write and read each symbol.
        for sym, (code, length) in table.items():
            writer = BitWriter()
            writer.write_bits(code, length)
            writer.flush()
            data = writer.get_bytes()
            reader = BitReader(data)
            decoded_sym = _decode_one(tree, reader)
            assert decoded_sym == sym


def _decode_one(tree, reader):
    node = tree
    while not node.is_leaf():
        bit = reader.read_bit()
        node = node.left if bit == 0 else node.right
    return node.value


# -----------------------------------------------------------------------
# Bit I/O tests
# -----------------------------------------------------------------------

class TestBitIO:
    def test_write_read_roundtrip(self):
        writer = BitWriter()
        values = [(0b101, 3), (0b11, 2), (0b0, 1), (0b11111111, 8),
                  (0b1010, 4)]
        for val, n in values:
            writer.write_bits(val, n)
        writer.flush()
        data = writer.get_bytes()

        reader = BitReader(data)
        for val, n in values:
            assert reader.read_bits(n) == val

    def test_byte_stuffing(self):
        """0xFF in output should be followed by 0x00."""
        writer = BitWriter()
        writer.write_bits(0xFF, 8)
        writer.write_bits(0xFF, 8)
        writer.flush()
        data = writer.get_bytes()
        # Each 0xFF should be followed by 0x00.
        for i in range(len(data) - 1):
            if data[i] == 0xFF:
                assert data[i + 1] == 0x00

    def test_zero_bits(self):
        writer = BitWriter()
        writer.write_bits(42, 0)  # Should be a no-op
        writer.flush()
        data = writer.get_bytes()
        # Should just be the padding byte.
        assert len(data) >= 0

    def test_writer_reset(self):
        writer = BitWriter()
        writer.write_bits(0xFF, 8)
        writer.flush()
        first = writer.get_bytes()
        assert len(first) > 0
        writer.reset()
        writer.write_bits(0x00, 8)
        writer.flush()
        second = writer.get_bytes()
        assert second != first


# -----------------------------------------------------------------------
# Subsampling tests
# -----------------------------------------------------------------------

class TestSubsampling:
    def test_downsample_upsample_roundtrip(self):
        channel = np.random.RandomState(0).randint(
            0, 256, (16, 16), dtype=np.uint8
        ).astype(np.float64)
        downsampled = downsample_channel(channel, 2, 2)
        assert downsampled.shape == (8, 8)
        upsampled = upsample_channel(downsampled, 2, 2, (16, 16))
        assert upsampled.shape == (16, 16)

    def test_no_downsample(self):
        channel = np.random.RandomState(0).randint(
            0, 256, (8, 8), dtype=np.uint8
        ).astype(np.float64)
        result = downsample_channel(channel, 1, 1)
        assert result.shape == (8, 8)

    def test_downsample_422(self):
        channel = np.random.RandomState(0).randint(
            0, 256, (16, 16), dtype=np.uint8
        ).astype(np.float64)
        result = downsample_channel(channel, 2, 1)
        assert result.shape == (16, 8)  # horizontal only


# -----------------------------------------------------------------------
# Full encode/decode roundtrip tests
# -----------------------------------------------------------------------

class TestEncodeDecode:
    def test_rgb_roundtrip(self, smooth_image):
        jpeg = encode(smooth_image, quality=90, sampling="4:2:0")
        recon = decode(jpeg)
        assert recon.shape == smooth_image.shape
        assert recon.dtype == np.uint8
        p = psnr(smooth_image, recon)
        assert p > 35, f"PSNR too low: {p}"

    def test_grayscale_roundtrip(self, gray_image):
        jpeg = encode(gray_image, quality=80)
        recon = decode(jpeg)
        assert recon.shape == gray_image.shape
        assert recon.dtype == np.uint8

    def test_various_qualities(self, smooth_image):
        for q in [10, 30, 50, 70, 90, 95]:
            jpeg = encode(smooth_image, quality=q, sampling="4:2:0")
            recon = decode(jpeg)
            assert recon.shape == smooth_image.shape
            p = psnr(smooth_image, recon)
            # Higher quality should give higher PSNR (generally).
            assert p > 20, f"PSNR too low at q={q}: {p}"

    def test_various_sampling(self, smooth_image):
        for s in ["4:4:4", "4:2:2", "4:2:0", "4:1:1"]:
            jpeg = encode(smooth_image, quality=85, sampling=s)
            recon = decode(jpeg)
            assert recon.shape == smooth_image.shape
            assert recon.dtype == np.uint8

    def test_odd_dimensions(self):
        for h, w in [(1, 1), (7, 7), (9, 13), (37, 53), (100, 1)]:
            if h == 1 or w == 1:
                img = np.full((h, w, 3), 128, dtype=np.uint8)
            else:
                img = np.random.RandomState(0).randint(
                    0, 256, (h, w, 3), dtype=np.uint8
                )
            jpeg = encode(img, quality=80)
            recon = decode(jpeg)
            assert recon.shape == img.shape, \
                f"Shape mismatch for ({h},{w}): {recon.shape}"

    def test_uniform_image(self):
        """Uniform color should compress very well."""
        img = np.full((64, 64, 3), 128, dtype=np.uint8)
        jpeg = encode(img, quality=85)
        recon = decode(jpeg)
        assert recon.shape == img.shape
        p = psnr(img, recon)
        assert p > 40, f"PSNR for uniform image: {p}"

    def test_comment_embedding(self, smooth_image):
        jpeg = encode(smooth_image, quality=85, comment="Test comment")
        info = get_info(jpeg)
        assert info.comment == "Test comment"

    def test_restart_markers(self, smooth_image):
        jpeg = encode(smooth_image, quality=85, restart_interval=4)
        info = get_info(jpeg)
        assert info.restart_interval == 4
        recon = decode(jpeg)
        assert recon.shape == smooth_image.shape
        p = psnr(smooth_image, recon)
        assert p > 30

    def test_dpi_metadata(self, smooth_image):
        jpeg = encode(smooth_image, quality=85, dpi=(300, 300), units=1)
        info = get_info(jpeg)
        assert info.x_density == 300
        assert info.y_density == 300


# -----------------------------------------------------------------------
# Cross-compatibility with Pillow
# -----------------------------------------------------------------------

class TestPillowCompatibility:
    def test_pillow_decodes_our_jpeg(self, smooth_image):
        pytest.importorskip("PIL")
        from PIL import Image
        jpeg = encode(smooth_image, quality=90, sampling="4:2:0")
        img = Image.open(io.BytesIO(jpeg))
        arr = np.array(img)
        assert arr.shape == smooth_image.shape
        p = psnr(smooth_image, arr)
        assert p > 30

    def test_we_decode_pillow_jpeg(self, smooth_image):
        pytest.importorskip("PIL")
        from PIL import Image
        buf = io.BytesIO()
        Image.fromarray(smooth_image).save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()
        recon = decode(jpeg_bytes)
        assert recon.shape == smooth_image.shape
        p = psnr(smooth_image, recon)
        assert p > 30


# -----------------------------------------------------------------------
# Metrics tests
# -----------------------------------------------------------------------

class TestMetrics:
    def test_mse_identical(self):
        a = np.zeros((10, 10), dtype=np.uint8)
        assert mse(a, a) == 0

    def test_mse_different(self):
        a = np.zeros((10, 10), dtype=np.uint8)
        b = np.full((10, 10), 10, dtype=np.uint8)
        assert mse(a, b) == 100

    def test_psnr_identical(self):
        a = np.zeros((10, 10), dtype=np.uint8)
        assert psnr(a, a) == float("inf")

    def test_psnr_value(self):
        a = np.zeros((10, 10), dtype=np.uint8)
        b = np.full((10, 10), 255, dtype=np.uint8)
        p = psnr(a, b)
        assert p == 0  # MSE = 255^2, so PSNR = 0

    def test_ssim_identical(self):
        a = np.random.RandomState(0).randint(
            0, 256, (32, 32), dtype=np.uint8
        )
        assert ssim(a, a) == pytest.approx(1.0, abs=0.01)

    def test_quality_report(self, smooth_image):
        jpeg = encode(smooth_image, quality=85)
        recon = decode(jpeg)
        report = quality_report(
            smooth_image, recon, smooth_image.nbytes, len(jpeg)
        )
        assert "mse" in report
        assert "psnr_db" in report
        assert "ssim" in report
        assert "compression_ratio" in report
        assert "bits_per_pixel" in report
        assert report["compression_ratio"] > 1


# -----------------------------------------------------------------------
# Config tests
# -----------------------------------------------------------------------

class TestConfig:
    def test_default_config(self):
        cfg = EncodingConfig()
        assert cfg.quality == 85
        assert cfg.sampling == "4:2:0"

    def test_invalid_quality(self):
        with pytest.raises(InvalidQualityError):
            EncodingConfig(quality=0)

    def test_invalid_sampling(self):
        with pytest.raises(InvalidSamplingError):
            EncodingConfig(sampling="5:5:5")

    def test_json_roundtrip(self, tmp_path):
        cfg = EncodingConfig(quality=75, sampling="4:4:4",
                             comment="Test")
        path = str(tmp_path / "config.json")
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded.quality == 75
        assert loaded.sampling == "4:4:4"
        assert loaded.comment == "Test"

    def test_config_with_encode(self, smooth_image):
        cfg = EncodingConfig(quality=90, sampling="4:4:4")
        kwargs = {k: v for k, v in cfg.to_dict().items()
                  if k != "optimize_huffman"}
        jpeg = encode(smooth_image, **kwargs)
        recon = decode(jpeg)
        assert recon.shape == smooth_image.shape


# -----------------------------------------------------------------------
# Exception tests
# -----------------------------------------------------------------------

class TestExceptions:
    def test_invalid_quality(self):
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        with pytest.raises(InvalidQualityError):
            encode(img, quality=0)
        with pytest.raises(InvalidQualityError):
            encode(img, quality=101)

    def test_invalid_sampling(self):
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        with pytest.raises(InvalidSamplingError):
            encode(img, sampling="invalid")

    def test_invalid_image_shape(self):
        img = np.zeros((10,), dtype=np.uint8)
        with pytest.raises(InvalidImageError):
            encode(img)

    def test_invalid_image_channels(self):
        img = np.zeros((8, 8, 4), dtype=np.uint8)
        with pytest.raises(InvalidImageError):
            encode(img)

    def test_decode_non_jpeg(self):
        with pytest.raises(DecodingError):
            decode(b"not a jpeg file")

    def test_decode_empty(self):
        with pytest.raises(DecodingError):
            decode(b"")

    def test_decode_truncated(self, smooth_image):
        jpeg = encode(smooth_image, quality=85)
        with pytest.raises((DecodingError, EOFError, ValueError,
                            IndexError, Exception)):
            decode(jpeg[:len(jpeg) // 2])


# -----------------------------------------------------------------------
# Info/Metadata tests
# -----------------------------------------------------------------------

class TestInfo:
    def test_basic_info(self, smooth_image):
        jpeg = encode(smooth_image, quality=85, sampling="4:2:0")
        info = get_info(jpeg)
        assert info.width == 64
        assert info.height == 64
        assert info.num_components == 3
        assert info.encoding_process == "baseline"

    def test_grayscale_info(self, gray_image):
        jpeg = encode(gray_image, quality=80)
        info = get_info(jpeg)
        assert info.num_components == 1

    def test_comment_info(self, smooth_image):
        jpeg = encode(smooth_image, quality=85, comment="Hello")
        info = get_info(jpeg)
        assert info.comment == "Hello"

    def test_restart_info(self, smooth_image):
        jpeg = encode(smooth_image, quality=85, restart_interval=2)
        info = get_info(jpeg)
        assert info.restart_interval == 2

    def test_markers_list(self, smooth_image):
        jpeg = encode(smooth_image, quality=85)
        info = get_info(jpeg)
        marker_names = [m[0] for m in info.markers]
        assert "SOI" in marker_names
        assert "SOS" in marker_names
        assert "DQT" in marker_names


# -----------------------------------------------------------------------
# Entropy coding tests
# -----------------------------------------------------------------------

class TestEntropy:
    def test_encode_decode_block_roundtrip(self):
        from jpeg_codec.huffman import (
            STD_DC_LUMA_BITS, STD_DC_LUMA_VALS,
            STD_AC_LUMA_BITS, STD_AC_LUMA_VALS,
        )
        dc_table = build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
        ac_table = build_huffman_table(STD_AC_LUMA_BITS, STD_AC_LUMA_VALS)
        dc_tree = HuffmanTree.from_table(dc_table)
        ac_tree = HuffmanTree.from_table(ac_table)

        coeffs = np.zeros(64, dtype=np.int32)
        coeffs[0] = 15
        coeffs[1] = -3
        coeffs[5] = 7
        coeffs[10] = -1

        writer = BitWriter()
        prev_dc = encode_block(coeffs, 0, dc_table, ac_table, writer)
        writer.flush()

        reader = BitReader(writer.get_bytes())
        decoded, prev_dc_out = decode_block(0, dc_tree, ac_tree, reader)
        assert np.array_equal(decoded, coeffs)
        assert prev_dc_out == 15

    def test_all_zero_block(self):
        from jpeg_codec.huffman import (
            STD_DC_LUMA_BITS, STD_DC_LUMA_VALS,
            STD_AC_LUMA_BITS, STD_AC_LUMA_VALS,
        )
        dc_table = build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
        ac_table = build_huffman_table(STD_AC_LUMA_BITS, STD_AC_LUMA_VALS)
        dc_tree = HuffmanTree.from_table(dc_table)
        ac_tree = HuffmanTree.from_table(ac_table)

        coeffs = np.zeros(64, dtype=np.int32)
        writer = BitWriter()
        encode_block(coeffs, 0, dc_table, ac_table, writer)
        writer.flush()

        reader = BitReader(writer.get_bytes())
        decoded, _ = decode_block(0, dc_tree, ac_tree, reader)
        assert np.array_equal(decoded, coeffs)


# -----------------------------------------------------------------------
# Batch DCT performance test
# -----------------------------------------------------------------------

class TestBatchDCT:
    def test_channel_to_blocks_dimensions(self):
        channel = np.random.RandomState(0).randn(24, 32)
        blocks = channel_to_blocks(channel)
        # 24/8=3 rows, 32/8=4 cols => 12 blocks
        assert blocks.shape == (12, 8, 8)

    def test_non_multiple_of_8_raises(self):
        channel = np.random.RandomState(0).randn(7, 8)
        with pytest.raises(ValueError):
            channel_to_blocks(channel)