"""JPEG baseline (sequential) encoder.

Produces a JFIF-compatible JPEG byte stream from an RGB or grayscale
numpy array.  The encoder supports:

  - Quality 1..100
  - Chroma subsampling modes: 4:4:4, 4:2:2, 4:2:0, 4:1:1
  - Standard JPEG Huffman and quantisation tables
  - Grayscale (single-channel) images
"""

import struct
import numpy as np

from .color import rgb_to_ycbcr, level_shift
from .dct import dct2d
from .quantize import quantize_block, get_quantization_tables
from .zigzag import zigzag_block
from .subsample import get_sampling_factors, downsample_channel
from .huffman import (
    build_huffman_table,
    STD_DC_LUMA_BITS, STD_DC_LUMA_VALS,
    STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS,
    STD_AC_LUMA_BITS, STD_AC_LUMA_VALS,
    STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS,
)
from .bitio import BitWriter
from .entropy import encode_block

# JPEG marker codes.
_SOI = 0xFFD8       # Start of image
_APP0 = 0xFFE0      # APP0 (JFIF)
_DQT = 0xFFDB       # Define quantisation table
_SOF0 = 0xFFC0      # Start of frame (baseline)
_DHT = 0xFFC4       # Define Huffman table
_SOS = 0xFFDA       # Start of scan
_EOI = 0xFFD9       # End of image


class _ByteStream:
    """Simple growable byte buffer with marker helpers."""

    def __init__(self):
        self.buf = bytearray()

    def write_marker(self, marker: int):
        self.buf += struct.pack(">H", marker)

    def write_segment(self, marker: int, payload: bytes):
        self.buf += struct.pack(">H", marker)
        self.buf += struct.pack(">H", len(payload) + 2)
        self.buf += payload

    def write_raw(self, data: bytes):
        self.buf += data


def _write_jfif_header(stream: _ByteStream, density: tuple, units: int = 0):
    """Write the APP0 JFIF segment."""
    ident = b"JFIF\x00"
    version = b"\x01\x01"          # JFIF 1.01
    xdpi, ydpi = density
    thumb_x = 0
    thumb_y = 0
    payload = ident + version + bytes([units]) + struct.pack(">HH", xdpi, ydpi)
    payload += bytes([thumb_x, thumb_y])
    stream.write_segment(_APP0, payload)


def _write_dqt(stream: _ByteStream, table_id: int, qt_8x8: np.ndarray):
    """Write a DQT segment for one quantisation table.

    The JPEG standard requires quantisation table values to be stored in
    zig-zag order within the DQT segment.
    """
    from .zigzag import ZIGZAG_ORDER
    # Precision (0 = 8-bit) in high nibble, table ID in low nibble.
    pq_tq = (0 << 4) | table_id
    # Flatten in zig-zag order (not row-major).
    qt_zz = qt_8x8.flatten()[ZIGZAG_ORDER]
    payload = bytes([pq_tq]) + qt_zz.astype(np.uint8).tobytes()
    stream.write_segment(_DQT, payload)


def _write_sof0(stream: _ByteStream, height: int, width: int,
                components: list, sampling: list):
    """Write the SOF0 (baseline) frame header.

    *components* is a list of (id, sampling_h, sampling_v, qt_id) tuples.
    """
    payload = bytes([8])  # precision: 8 bits
    payload += struct.pack(">HH", height, width)
    payload += bytes([len(components)])
    for cid, h, v, qt_id in components:
        payload += bytes([cid, (h << 4) | v, qt_id])
    stream.write_segment(_SOF0, payload)


def _write_dht(stream: _ByteStream, table_class: int, table_id: int,
               bits: list, vals: list):
    """Write one DHT segment.

    *table_class*: 0 = DC, 1 = AC.
    *table_id*: 0 or 1.
    """
    tc_th = (table_class << 4) | table_id
    payload = bytes([tc_th]) + bytes(bits[:16]) + bytes(vals)
    stream.write_segment(_DHT, payload)


def _write_sos(stream: _ByteStream, components: list):
    """Write the SOS (start of scan) header.

    *components* is a list of (id, dc_table_id, ac_table_id) tuples.
    """
    payload = bytes([len(components)])
    for cid, dc_id, ac_id in components:
        payload += bytes([cid, (dc_id << 4) | ac_id])
    # Start, end, Ah/Al (successive approximation -- not used in baseline).
    payload += bytes([0, 63, 0x00])
    stream.write_segment(_SOS, payload)


def _process_blocks(channel: np.ndarray, h: int, v: int,
                    qt: np.ndarray, dc_table: dict, ac_table: dict,
                    prev_dc: int, writer: BitWriter) -> int:
    """Process all 8x8 blocks of one (subsampled) channel plane.

    Blocks are traversed in MCU-aligned raster order, which for a channel
    with sampling factor (h, v) means h*v blocks per MCU, read row by
    row within each MCU.

    Returns the final ``prev_dc``.
    """
    rows, cols = channel.shape
    # Number of MCU columns / rows (based on the max sampling factor at
    # the caller level; here we receive a channel already sized so that
    # blocks divide evenly).
    n_blocks_x = (cols + 7) // 8
    n_blocks_y = (rows + 7) // 8

    for by in range(n_blocks_y):
        for bx in range(n_blocks_x):
            r0, c0 = by * 8, bx * 8
            block = channel[r0:r0 + 8, c0:c0 + 8]
            # Pad to 8x8 if at the edge.
            if block.shape != (8, 8):
                block = np.pad(block,
                               ((0, 8 - block.shape[0]),
                                (0, 8 - block.shape[1])),
                               mode="edge")
            shifted = level_shift(block)
            dct = dct2d(shifted)
            quant = quantize_block(dct, qt)
            zz = zigzag_block(quant)
            prev_dc = encode_block(zz, prev_dc, dc_table, ac_table, writer)
    return prev_dc


def encode_image(image: np.ndarray, quality: int = 50,
                 sampling: str = "4:2:0") -> bytes:
    """Encode an image array to JPEG bytes.

    Parameters
    ----------
    image : np.ndarray
        Either (H, W, 3) RGB uint8 or (H, W) grayscale uint8.
    quality : int
        1 (worst) .. 100 (best).  Default 50.
    sampling : str
        Chroma subsampling mode.  Ignored for grayscale images.

    Returns
    -------
    bytes
        Raw JPEG / JFIF file data.
    """
    if image.ndim not in (2, 3):
        raise ValueError("image must be 2D (grayscale) or 3D (RGB)")
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError("RGB image must have 3 channels")

    image = image.astype(np.float64)
    grayscale = image.ndim == 2
    height, width = image.shape[:2]

    if not 1 <= quality <= 100:
        raise ValueError(f"quality must be 1..100, got {quality}")

    # Build quantisation tables.
    luma_qt, chroma_qt = get_quantization_tables(quality)

    # Build Huffman tables (encoding side).
    dc_luma_enc = build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
    ac_luma_enc = build_huffman_table(STD_AC_LUMA_BITS, STD_AC_LUMA_VALS)
    dc_chroma_enc = build_huffman_table(STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS)
    ac_chroma_enc = build_huffman_table(STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS)

    # --- Colour transform & subsampling ---
    if grayscale:
        chan_ids = [1]
        chan_qt = [luma_qt]
        chan_dc = [dc_luma_enc]
        chan_ac = [ac_luma_enc]
        chan_sampling = [(1, 1)]
        n_components = 1
        sf = [(1, 1)]
    else:
        sf = get_sampling_factors(sampling)
        chan_ids = [1, 2, 3]
        chan_qt = [luma_qt, chroma_qt, chroma_qt]
        chan_dc = [dc_luma_enc, dc_chroma_enc, dc_chroma_enc]
        chan_ac = [ac_luma_enc, ac_chroma_enc, ac_chroma_enc]
        chan_sampling = [(h, v) for (h, v) in sf]
        n_components = 3

    # Pad image dimensions to MCU boundary *before* colour transform.
    mcu_w = 8 * max(s[0] for s in chan_sampling)
    mcu_h = 8 * max(s[1] for s in chan_sampling)
    pad_w = (mcu_w - width % mcu_w) % mcu_w
    pad_h = (mcu_h - height % mcu_h) % mcu_h
    if pad_w or pad_h:
        if grayscale:
            image = np.pad(image, ((0, pad_h), (0, pad_w)), mode="edge")
        else:
            image = np.pad(image,
                           ((0, pad_h), (0, pad_w), (0, 0)),
                           mode="edge")
    height_p, width_p = image.shape[:2]

    # Now build the channel planes from the (padded) image.
    max_h = max(s[0] for s in chan_sampling) if not grayscale else 1
    max_v = max(s[1] for s in chan_sampling) if not grayscale else 1
    if grayscale:
        channels = [image.astype(np.float64)]
    else:
        ycbcr = rgb_to_ycbcr(image)
        channels = []
        for c in range(3):
            h, v = sf[c]
            plane = ycbcr[..., c]
            channels.append(downsample_channel(plane, max_h // h,
                                                max_v // v))

    # Ensure each channel is exactly sized to its block grid
    # (mcu_cols * h * 8, mcu_rows * v * 8).  Crop or pad as needed.
    mcu_cols = width_p // mcu_w
    mcu_rows = height_p // mcu_h
    for c in range(n_components):
        h, v = chan_sampling[c]
        target_h = mcu_rows * v * 8
        target_w = mcu_cols * h * 8
        ch = channels[c]
        if ch.shape[0] < target_h or ch.shape[1] < target_w:
            channels[c] = np.pad(
                ch,
                ((0, max(0, target_h - ch.shape[0])),
                 (0, max(0, target_w - ch.shape[1]))),
                mode="edge")
        elif ch.shape[0] > target_h or ch.shape[1] > target_w:
            channels[c] = ch[:target_h, :target_w]

    # --- Write JPEG structure ---
    stream = _ByteStream()
    stream.write_marker(_SOI)
    _write_jfif_header(stream, (72, 72), units=1)

    # DQT: luma (table 0), chroma (table 1).
    _write_dqt(stream, 0, luma_qt)
    if not grayscale:
        _write_dqt(stream, 1, chroma_qt)

    # SOF0.
    if grayscale:
        _write_sof0(stream, height, width,
                    [(1, 1, 1, 0)], [(1, 1)])
    else:
        comps = [(cid, h, v, qt_id)
                 for cid, (h, v), qt_id
                 in zip(chan_ids, sf, [0, 1, 1])]
        _write_sof0(stream, height, width, comps, sf)

    # DHT.
    _write_dht(stream, 0, 0, STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
    _write_dht(stream, 1, 0, STD_AC_LUMA_BITS, STD_AC_LUMA_VALS)
    if not grayscale:
        _write_dht(stream, 0, 1, STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS)
        _write_dht(stream, 1, 1, STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS)

    # SOS.
    if grayscale:
        _write_sos(stream, [(1, 0, 0)])
    else:
        _write_sos(stream, [(1, 0, 0), (2, 1, 1), (3, 1, 1)])

    # --- Entropy code all blocks ---
    writer = BitWriter()
    prev_dcs = [0] * n_components

    if grayscale:
        prev_dcs[0] = _process_blocks(
            channels[0], 1, 1, chan_qt[0], chan_dc[0], chan_ac[0],
            prev_dcs[0], writer)
    else:
        # MCU-ordered traversal: for each MCU, encode h*v luma blocks,
        # then 1 Cb block, then 1 Cr block.
        mcu_cols = width_p // mcu_w
        mcu_rows = height_p // mcu_h
        for my in range(mcu_rows):
            for mx in range(mcu_cols):
                for c in range(n_components):
                    h, v = chan_sampling[c]
                    blocks_per_mcu = h * v
                    blk_w = 8
                    # Channel plane dimensions.
                    ch = channels[c]
                    # Block origin in the *channel* grid.
                    ch_bx0 = mx * h
                    ch_by0 = my * v
                    for vb in range(v):
                        for hb in range(h):
                            bx = ch_bx0 + hb
                            by = ch_by0 + vb
                            r0, c0 = by * 8, bx * 8
                            block = ch[r0:r0 + 8, c0:c0 + 8]
                            if block.shape != (8, 8):
                                block = np.pad(
                                    block,
                                    ((0, 8 - block.shape[0]),
                                     (0, 8 - block.shape[1])),
                                    mode="edge")
                            shifted = level_shift(block)
                            dct = dct2d(shifted)
                            quant = quantize_block(dct, chan_qt[c])
                            zz = zigzag_block(quant)
                            prev_dcs[c] = encode_block(
                                zz, prev_dcs[c],
                                chan_dc[c], chan_ac[c], writer)

    writer.flush()
    stream.write_raw(writer.get_bytes())
    stream.write_marker(_EOI)
    return bytes(stream.buf)


# Public alias.
encode = encode_image