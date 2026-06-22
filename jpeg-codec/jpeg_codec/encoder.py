"""JPEG baseline (sequential) encoder.

Produces a JFIF-compatible JPEG byte stream from an RGB or grayscale
numpy array.  The encoder supports:

  - Quality 1..100 (libjpeg-compatible scaling)
  - Chroma subsampling modes: 4:4:4, 4:2:2, 4:2:0, 4:1:1
  - Standard JPEG Huffman and quantization tables
  - Grayscale (single-channel) images
  - Comment (COM) marker embedding
  - Restart markers (DRI/RST0-RST7) for error-resilient streaming
  - DPI/pixel density metadata in JFIF header
  - Optional vectorized batch DCT for performance
"""

import struct
import numpy as np

from .color import rgb_to_ycbcr, level_shift
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
from .exceptions import (
    EncodingError, InvalidQualityError, InvalidSamplingError,
    InvalidImageError,
)
from .restart import (
    should_emit_restart, emit_restart_marker, write_dri_segment,
    write_com_segment, RST_MARKERS,
)
from .logging_setup import get_logger

_log = get_logger()

# JPEG marker codes.
_SOI = 0xFFD8       # Start of image
_APP0 = 0xFFE0      # APP0 (JFIF)
_DQT = 0xFFDB       # Define quantization table
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


def _write_jfif_header(stream: _ByteStream, density: tuple,
                       units: int = 1):
    """Write the APP0 JFIF segment.

    Parameters
    ----------
    density : tuple
        (x_density, y_density) in units specified by *units*.
    units : int
        0 = no units, 1 = DPI, 2 = DPCM.
    """
    ident = b"JFIF\x00"
    version = b"\x01\x01"          # JFIF 1.01
    xdpi, ydpi = density
    thumb_x = 0
    thumb_y = 0
    payload = ident + version + bytes([units]) + struct.pack(">HH", xdpi, ydpi)
    payload += bytes([thumb_x, thumb_y])
    stream.write_segment(_APP0, payload)


def _write_dqt(stream: _ByteStream, table_id: int, qt_8x8: np.ndarray):
    """Write a DQT segment for one quantization table.

    The JPEG standard requires quantization table values to be stored in
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


def _process_block_inplace(block: np.ndarray, qt: np.ndarray,
                           prev_dc: int, dc_table: dict,
                           ac_table: dict,
                           writer: BitWriter) -> int:
    """Process a single 8x8 block: DCT → quantize → zigzag → entropy encode.

    Returns the new prev_dc value.
    """
    from .dct import dct2d
    shifted = level_shift(block)
    dct = dct2d(shifted)
    quant = quantize_block(dct, qt)
    zz = zigzag_block(quant)
    return encode_block(zz, prev_dc, dc_table, ac_table, writer)


def _validate_image(image: np.ndarray) -> None:
    """Validate the input image array."""
    if not isinstance(image, np.ndarray):
        raise InvalidImageError(f"expected numpy array, got {type(image).__name__}")
    if image.ndim not in (2, 3):
        raise InvalidImageError(
            f"must be 2D (grayscale) or 3D (RGB), got {image.ndim}D"
        )
    if image.ndim == 3 and image.shape[2] != 3:
        raise InvalidImageError(
            f"RGB image must have 3 channels, got {image.shape[2]}"
        )
    if image.size == 0:
        raise InvalidImageError("image is empty (zero pixels)")


def encode_image(image: np.ndarray, quality: int = 85,
                 sampling: str = "4:2:0",
                 comment: str = None,
                 restart_interval: int = 0,
                 dpi: tuple = (72, 72),
                 units: int = 1) -> bytes:
    """Encode an image array to JPEG bytes.

    Parameters
    ----------
    image : np.ndarray
        Either (H, W, 3) RGB uint8 or (H, W) grayscale uint8.
    quality : int
        1 (worst) .. 100 (best).  Default 85.
    sampling : str
        Chroma subsampling mode.  Ignored for grayscale images.
        One of: "4:4:4", "4:2:2", "4:2:0", "4:1:1".
    comment : str, optional
        Comment to embed in the JPEG COM marker.
    restart_interval : int
        MCU restart interval (0 = disabled).  When > 0, RST markers
        are inserted every *restart_interval* MCUs for error resilience.
    dpi : tuple of (int, int)
        Horizontal and vertical pixel density (default (72, 72)).
    units : int
        Density units: 0 = no units, 1 = DPI (default), 2 = DPCM.

    Returns
    -------
    bytes
        Raw JPEG / JFIF file data.

    Raises
    ------
    InvalidImageError
        If the image has an unsupported shape or dtype.
    InvalidQualityError
        If quality is outside [1, 100].
    InvalidSamplingError
        If sampling mode is not recognized.
    """
    # --- Validation ---
    _validate_image(image)
    if not 1 <= quality <= 100:
        raise InvalidQualityError(quality)
    if sampling not in ("4:4:4", "4:2:2", "4:2:0", "4:1:1"):
        raise InvalidSamplingError(sampling)
    if not isinstance(restart_interval, int) or restart_interval < 0:
        raise ValueError("restart_interval must be non-negative")
    if not isinstance(dpi, (tuple, list)) or len(dpi) != 2:
        raise ValueError("dpi must be a (x, y) tuple")
    if units not in (0, 1, 2):
        raise ValueError("units must be 0, 1, or 2")

    _log.info(
        "Encoding: shape=%s, quality=%d, sampling=%s, restart=%d",
        image.shape, quality, sampling, restart_interval,
    )

    image = image.astype(np.float64)
    # Clip values to valid range.
    image = np.clip(image, 0, 255)
    grayscale = image.ndim == 2
    height, width = image.shape[:2]

    # Build quantization tables.
    luma_qt, chroma_qt = get_quantization_tables(quality)
    _log.debug("Quantization tables built for quality=%d", quality)

    # Build Huffman tables (encoding side).
    dc_luma_enc = build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS)
    ac_luma_enc = build_huffman_table(STD_AC_LUMA_BITS, STD_AC_LUMA_VALS)
    dc_chroma_enc = build_huffman_table(STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS)
    ac_chroma_enc = build_huffman_table(STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS)

    # --- Color transform & subsampling ---
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

    # Pad image dimensions to MCU boundary *before* color transform.
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
    _log.debug("Padded image: %dx%d -> %dx%d", width, height, width_p, height_p)

    # Now build the channel planes from the (padded) image.
    if grayscale:
        channels = [image.astype(np.float64)]
    else:
        ycbcr = rgb_to_ycbcr(image)
        max_h = max(s[0] for s in sf)
        max_v = max(s[1] for s in sf)
        channels = []
        for c in range(3):
            h, v = sf[c]
            plane = ycbcr[..., c]
            channels.append(downsample_channel(plane, max_h // h,
                                                max_v // v))

    # Ensure each channel is exactly sized to its block grid.
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
    _write_jfif_header(stream, dpi, units=units)

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

    # Comment (COM marker).
    if comment is not None and len(comment) > 0:
        write_com_segment(stream, comment)

    # Restart interval (DRI marker).
    if restart_interval > 0:
        write_dri_segment(stream, restart_interval)

    # SOS.
    if grayscale:
        _write_sos(stream, [(1, 0, 0)])
    else:
        _write_sos(stream, [(1, 0, 0), (2, 1, 1), (3, 1, 1)])

    # --- Entropy code all blocks ---
    writer = BitWriter()
    prev_dcs = [0] * n_components

    if grayscale:
        _encode_grayscale(channels, chan_qt, chan_dc, chan_ac,
                          prev_dcs, writer,
                          restart_interval, 0, 0, stream)
    else:
        _encode_color_mcus(channels, chan_sampling, chan_qt, chan_dc,
                           chan_ac, prev_dcs, writer,
                           mcu_cols, mcu_rows, n_components,
                           restart_interval, stream)

    writer.flush()
    stream.write_raw(writer.get_bytes())
    stream.write_marker(_EOI)

    _log.info("Encoding complete: %d bytes", len(stream.buf))
    return bytes(stream.buf)


def _encode_grayscale(channels, chan_qt, chan_dc, chan_ac,
                      prev_dcs, writer,
                      restart_interval, rst_index, mcus_since_rst,
                      stream):
    """Encode a grayscale image's blocks.

    Handles restart markers by flushing the BitWriter, writing the
    RST marker to the stream, and resetting DC predictors.
    """
    channel = channels[0]
    rows, cols = channel.shape
    n_blocks_x = (cols + 7) // 8
    n_blocks_y = (rows + 7) // 8

    rst_idx = 0
    mcus_rst = 0
    for by in range(n_blocks_y):
        for bx in range(n_blocks_x):
            r0, c0 = by * 8, bx * 8
            block = channel[r0:r0 + 8, c0:c0 + 8]
            if block.shape != (8, 8):
                block = np.pad(block,
                               ((0, 8 - block.shape[0]),
                                (0, 8 - block.shape[1])),
                                mode="edge")
            prev_dcs[0] = _process_block_inplace(
                block, chan_qt[0], prev_dcs[0],
                chan_dc[0], chan_ac[0], writer)

            # Restart marker handling.
            if restart_interval > 0:
                mcus_rst += 1
                if should_emit_restart(mcus_rst, restart_interval):
                    writer.flush()
                    stream.write_raw(writer.get_bytes())
                    writer.reset()
                    marker = RST_MARKERS[rst_idx % 8]
                    stream.write_marker(marker)
                    prev_dcs[0] = 0
                    mcus_rst = 0
                    rst_idx = (rst_idx + 1) % 8


def _encode_color_mcus(channels, chan_sampling, chan_qt, chan_dc,
                       chan_ac, prev_dcs, writer,
                       mcu_cols, mcu_rows, n_components,
                       restart_interval, stream):
    """Encode a color image's MCU-ordered blocks.

    When restart_interval > 0, RST markers are interleaved in the
    entropy data stream by flushing the BitWriter, writing the RST
    marker directly to the stream, and resetting the writer and
    DC predictors.
    """
    rst_idx = 0
    mcus_rst = 0

    for my in range(mcu_rows):
        for mx in range(mcu_cols):
            for c in range(n_components):
                h, v = chan_sampling[c]
                ch = channels[c]
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
                        prev_dcs[c] = _process_block_inplace(
                            block, chan_qt[c], prev_dcs[c],
                            chan_dc[c], chan_ac[c], writer)

            # Restart marker handling (per-MCU).
            if restart_interval > 0:
                mcus_rst += 1
                if should_emit_restart(mcus_rst, restart_interval):
                    writer.flush()
                    stream.write_raw(writer.get_bytes())
                    writer.reset()
                    # Emit RST marker.
                    marker = RST_MARKERS[rst_idx % 8]
                    stream.write_marker(marker)
                    prev_dcs[:] = [0] * n_components
                    mcus_rst = 0
                    rst_idx = (rst_idx + 1) % 8
                    _log.debug("RST%d at MCU (%d, %d)", rst_idx, mx, my)


# Public alias.
encode = encode_image