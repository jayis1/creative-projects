"""JPEG baseline (sequential) decoder.

Reads a JFIF-compatible JPEG byte stream and reconstructs the RGB or
grayscale numpy array.  Supports:

  - Quality-independent (reads quantization tables from the file)
  - Chroma subsampling: 4:4:4, 4:2:2, 4:2:0, 4:1:1
  - Standard and custom Huffman tables (reads from DHT segments)
  - Grayscale and 3-channel YCbCr images
  - Comment (COM) marker extraction
  - Restart interval (DRI) parsing
  - Restart markers (RST0-RST7) during decoding
  - Robust error handling with custom exceptions
"""

import struct
import numpy as np

from .color import ycbcr_to_rgb, unlevel_shift
from .quantize import dequantize_block
from .zigzag import izigzag_block
from .subsample import upsample_channel
from .huffman import build_huffman_table, HuffmanTree
from .bitio import BitReader
from .entropy import decode_block
from .exceptions import (
    DecodingError, InvalidMarkerError, UnsupportedFeatureError,
    TruncatedDataError,
)
from .logging_setup import get_logger

_log = get_logger()

# Marker codes (must match encoder).
_SOI = 0xFFD8
_APP0 = 0xFFE0
_DQT = 0xFFDB
_SOF0 = 0xFFC0
_DHT = 0xFFC4
_SOS = 0xFFDA
_EOI = 0xFFD9
_COM = 0xFFFE
_DRI = 0xFFDD

# Restart markers RST0..RST7.
_RST_MARKERS = set(0xFFD0 + i for i in range(8))


class _JPEGParser:
    """Parse the JPEG marker structure up to (and including) SOS."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.height = 0
        self.width = 0
        self.components = []        # list of dicts: id, h, v, qt_id
        self.qt_tables = {}         # qt_id -> 8x8 np.ndarray
        self.dc_trees = {}          # table_id -> HuffmanTree
        self.ac_trees = {}          # table_id -> HuffmanTree
        self.scan_components = []   # list of dicts: id, dc_id, ac_id
        self.scan_start = 0         # byte offset of entropy-coded data
        self.comment = None         # COM marker content (str or None)
        self.restart_interval = 0   # DRI value (0 = no restart markers)
        self.jfif_version = None    # (major, minor) or None
        self.density = (0, 0, 0)    # (units, x_density, y_density)
        self.sof_marker = _SOF0     # which SOF marker was used

    def _read_u8(self) -> int:
        if self.pos >= len(self.data):
            raise TruncatedDataError("Unexpected end of data")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def _read_u16(self) -> int:
        if self.pos + 2 > len(self.data):
            raise TruncatedDataError("Unexpected end of data")
        v = struct.unpack(">H", self.data[self.pos:self.pos + 2])[0]
        self.pos += 2
        return v

    def _read_marker(self) -> int:
        """Read a 2-byte marker (0xFF + non-zero byte)."""
        if self.pos >= len(self.data) or self.data[self.pos] != 0xFF:
            raise InvalidMarkerError(
                0, self.pos,
                f"Expected marker prefix 0xFF at offset {self.pos}"
            )
        marker = self._read_u16()
        return marker

    def parse(self):
        """Parse all markers from SOI through SOS."""
        marker = self._read_marker()
        if marker != _SOI:
            raise DecodingError("Not a JPEG file (missing SOI)")

        while True:
            # Skip fill bytes (0xFF 0xFF sequences).
            while (self.pos < len(self.data) - 1
                   and self.data[self.pos] == 0xFF
                   and self.data[self.pos + 1] == 0xFF):
                self.pos += 1

            marker = self._read_marker()

            if marker == _EOI:
                break
            elif marker == _SOS:
                self._parse_sos()
                self.scan_start = self.pos
                break
            elif marker == _DQT:
                self._parse_dqt()
            elif marker == _SOF0:
                self.sof_marker = marker
                self._parse_sof0()
            elif 0xFFC1 <= marker <= 0xFFCF and marker != 0xFFC4:
                # Non-baseline SOF markers.
                feature_map = {
                    0xFFC1: "extended sequential",
                    0xFFC2: "progressive",
                    0xFFC3: "lossless",
                    0xFFCA: "extended sequential arithmetic",
                    0xFFCB: "progressive arithmetic",
                }
                feat = feature_map.get(marker, f"SOF 0x{marker:04X}")
                raise UnsupportedFeatureError(feat)
            elif marker == _DHT:
                self._parse_dht()
            elif marker == _APP0:
                self._parse_app0()
            elif 0xFFE0 <= marker <= 0xFFEF:
                # APPn segments -- skip.
                self._skip_segment()
            elif marker == _COM:
                self._parse_com()
            elif marker == _DRI:
                self._parse_dri()
            elif marker in _RST_MARKERS:
                # Restart markers outside scan data -- skip.
                continue
            else:
                # Unknown / unsupported marker -- skip its payload.
                if marker not in (_SOI,):
                    self._skip_segment()

    def _skip_segment(self):
        length = self._read_u16()
        self.pos += length - 2

    def _parse_app0(self):
        """Parse APP0 segment, extracting JFIF metadata."""
        length = self._read_u16()
        end = self.pos + length - 2
        ident = self.data[self.pos:self.pos + 5]
        if ident == b"JFIF\x00":
            self.jfif_version = (
                self.data[self.pos + 5],
                self.data[self.pos + 6],
            )
            units = self.data[self.pos + 7]
            x_dens = struct.unpack(">H", self.data[self.pos + 8:self.pos + 10])[0]
            y_dens = struct.unpack(">H", self.data[self.pos + 10:self.pos + 12])[0]
            self.density = (units, x_dens, y_dens)
        self.pos = end

    def _parse_com(self):
        """Parse a COM (comment) marker segment."""
        length = self._read_u16()
        comment_bytes = self.data[self.pos:self.pos + length - 2]
        self.pos += length - 2
        try:
            self.comment = comment_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self.comment = comment_bytes.decode("latin-1", errors="replace")
        _log.debug("Comment: %s", self.comment)

    def _parse_dri(self):
        """Parse a DRI (Define Restart Interval) marker segment."""
        length = self._read_u16()
        if length >= 4:
            self.restart_interval = struct.unpack(
                ">H", self.data[self.pos:self.pos + 2]
            )[0]
        self.pos += length - 2
        _log.debug("Restart interval: %d MCUs", self.restart_interval)

    def _parse_dqt(self):
        length = self._read_u16()
        end = self.pos + length - 2
        while self.pos < end:
            pq_tq = self._read_u8()
            precision = (pq_tq >> 4) & 0xF
            table_id = pq_tq & 0xF
            if precision == 0:
                # 8-bit values, 64 bytes.
                vals = np.array(
                    list(self.data[self.pos:self.pos + 64]),
                    dtype=np.float64)
                self.pos += 64
            else:
                # 16-bit values, 128 bytes.
                vals = np.zeros(64, dtype=np.float64)
                for i in range(64):
                    vals[i] = struct.unpack(
                        ">H", self.data[self.pos:self.pos + 2])[0]
                    self.pos += 2
            # DQT stores values in zig-zag order; convert to 8x8 natural.
            from .zigzag import ZIGZAG_ORDER
            qt = np.zeros(64, dtype=np.float64)
            for i in range(64):
                qt[ZIGZAG_ORDER[i]] = vals[i]
            self.qt_tables[table_id] = qt.reshape(8, 8)

    def _parse_sof0(self):
        length = self._read_u16()
        precision = self._read_u8()
        self.height = self._read_u16()
        self.width = self._read_u16()
        n = self._read_u8()
        for _ in range(n):
            cid = self._read_u8()
            hv = self._read_u8()
            h = (hv >> 4) & 0xF
            v = hv & 0xF
            qt_id = self._read_u8()
            self.components.append({
                "id": cid, "h": h, "v": v, "qt_id": qt_id
            })

    def _parse_dht(self):
        length = self._read_u16()
        end = self.pos + length - 2
        while self.pos < end:
            tc_th = self._read_u8()
            table_class = (tc_th >> 4) & 0xF
            table_id = tc_th & 0xF
            bits = list(self.data[self.pos:self.pos + 16])
            self.pos += 16
            n_symbols = sum(bits)
            vals = list(self.data[self.pos:self.pos + n_symbols])
            self.pos += n_symbols
            table = build_huffman_table(bits, vals)
            tree = HuffmanTree.from_table(table)
            if table_class == 0:
                self.dc_trees[table_id] = tree
            else:
                self.ac_trees[table_id] = tree

    def _parse_sos(self):
        length = self._read_u16()
        n = self._read_u8()
        for _ in range(n):
            cid = self._read_u8()
            ta = self._read_u8()
            dc_id = (ta >> 4) & 0xF
            ac_id = ta & 0xF
            self.scan_components.append({
                "id": cid, "dc_id": dc_id, "ac_id": ac_id
            })
        # Ss Se AhAl (3 bytes) -- skip for baseline.
        self.pos += 3


def _find_eoi(data: bytes, start: int) -> int:
    """Find the EOI marker starting from *start*, accounting for stuffing."""
    i = start
    while i < len(data) - 1:
        if data[i] == 0xFF:
            if data[i + 1] == 0xD9:
                return i
            elif data[i + 1] == 0x00:
                i += 2
                continue
            elif data[i + 1] == 0xFF:
                i += 1
                continue
            else:
                # Other marker -- for baseline single-scan, this shouldn't
                # appear inside entropy data, but treat as end of scan.
                return i
        i += 1
    return len(data)


def decode_image(data: bytes) -> np.ndarray:
    """Decode JPEG bytes into an RGB or grayscale numpy array.

    Parameters
    ----------
    data : bytes
        Raw JPEG/JFIF file data.

    Returns
    -------
    np.ndarray
        (H, W, 3) uint8 for colour images, (H, W) uint8 for grayscale.

    Raises
    ------
    DecodingError
        If the data is not a valid baseline JPEG file.
    UnsupportedFeatureError
        If the JPEG uses progressive, arithmetic, or other non-baseline
        encoding.
    TruncatedDataError
        If the bit stream ends prematurely.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise DecodingError(
            f"Expected bytes, got {type(data).__name__}"
        )
    if len(data) < 4:
        raise DecodingError("Data too short to be a valid JPEG")

    parser = _JPEGParser(data)
    parser.parse()

    _log.info(
        "Decoding: %dx%d, %d components, restart=%d",
        parser.width, parser.height,
        len(parser.components),
        parser.restart_interval,
    )

    height = parser.height
    width = parser.width
    n_comp = len(parser.components)

    if height == 0 or width == 0:
        raise DecodingError("Image has zero dimensions")

    if n_comp == 1:
        return _decode_grayscale(parser, data, height, width)
    else:
        return _decode_color(parser, data, height, width)


def _decode_grayscale(parser, data, height, width):
    comp = parser.components[0]
    qt = parser.qt_tables[comp["qt_id"]]
    dc_tree = parser.dc_trees[parser.scan_components[0]["dc_id"]]
    ac_tree = parser.ac_trees[parser.scan_components[0]["ac_id"]]

    reader = BitReader(data, parser.scan_start)
    prev_dc = 0
    nbx = (width + 7) // 8
    nby = (height + 7) // 8
    out = np.zeros((nby * 8, nbx * 8), dtype=np.float64)
    rst_index = 0
    mcus_since_rst = 0

    for by in range(nby):
        for bx in range(nbx):
            try:
                coeffs, prev_dc = decode_block(prev_dc, dc_tree, ac_tree, reader)
            except EOFError:
                # Check for restart marker.
                if _handle_restart(data, reader, parser.restart_interval):
                    prev_dc = 0
                    coeffs, prev_dc = decode_block(prev_dc, dc_tree, ac_tree, reader)
                else:
                    raise TruncatedDataError(
                        "Bit stream exhausted during grayscale decode"
                    )

            block = izigzag_block(coeffs)
            dequant = dequantize_block(block, qt)
            spatial = idct2d_safe(dequant)
            spatial = unlevel_shift(spatial)
            out[by * 8:by * 8 + 8, bx * 8:bx * 8 + 8] = spatial

    out = np.clip(out[:height, :width], 0, 255).astype(np.uint8)
    _log.info("Grayscale decode complete: %s", out.shape)
    return out


def _decode_color(parser, data, height, width):
    from .dct import idct2d

    comps = parser.components
    max_h = max(c["h"] for c in comps)
    max_v = max(c["v"] for c in comps)
    mcu_w = 8 * max_h
    mcu_h = 8 * max_v
    mcu_cols = (width + mcu_w - 1) // mcu_w
    mcu_rows = (height + mcu_h - 1) // mcu_h

    # Map component id -> scan info.
    scan_map = {sc["id"]: sc for sc in parser.scan_components}

    # Prepare output channel planes (padded to MCU grid).
    channel_planes = []
    for c in comps:
        h, v = c["h"], c["v"]
        ch_w = mcu_cols * h * 8
        ch_h = mcu_rows * v * 8
        channel_planes.append(np.zeros((ch_h, ch_w), dtype=np.float64))

    reader = BitReader(data, parser.scan_start)
    n_comp = len(comps)
    prev_dcs = [0] * n_comp

    for my in range(mcu_rows):
        for mx in range(mcu_cols):
            for ci, c in enumerate(comps):
                h, v = c["h"], c["v"]
                qt = parser.qt_tables[c["qt_id"]]
                sc = scan_map[c["id"]]
                dc_tree = parser.dc_trees[sc["dc_id"]]
                ac_tree = parser.ac_trees[sc["ac_id"]]
                for vb in range(v):
                    for hb in range(h):
                        try:
                            coeffs, prev_dcs[ci] = decode_block(
                                prev_dcs[ci], dc_tree, ac_tree, reader)
                        except EOFError:
                            if _handle_restart(
                                data, reader, parser.restart_interval
                            ):
                                prev_dcs[ci] = 0
                                coeffs, prev_dcs[ci] = decode_block(
                                    prev_dcs[ci], dc_tree, ac_tree, reader)
                            else:
                                raise TruncatedDataError(
                                    "Bit stream exhausted during color decode"
                                )

                        block = izigzag_block(coeffs)
                        dequant = dequantize_block(block, qt)
                        spatial = idct2d(dequant)
                        spatial = unlevel_shift(spatial)
                        bx = mx * h + hb
                        by = my * v + vb
                        r0, c0 = by * 8, bx * 8
                        channel_planes[ci][r0:r0 + 8, c0:c0 + 8] = spatial

            # Handle restart markers at MCU boundaries.
            if parser.restart_interval > 0:
                mcus_since_rst = (mx + my * mcu_cols + 1) % parser.restart_interval
                if mcus_since_rst == 0 and (my * mcu_cols + mx + 1) > 0:
                    # Reset DC predictors at restart boundary.
                    prev_dcs = [0] * n_comp

    # Upsample chroma channels and convert back to RGB.
    y = channel_planes[0][:mcu_rows * max_v * 8, :mcu_cols * max_h * 8]
    cb = upsample_channel(channel_planes[1], max_h // comps[1]["h"],
                          max_v // comps[1]["v"],
                          (mcu_rows * max_v * 8, mcu_cols * max_h * 8))
    cr = upsample_channel(channel_planes[2], max_h // comps[2]["h"],
                          max_v // comps[2]["v"],
                          (mcu_rows * max_v * 8, mcu_cols * max_h * 8))

    ycbcr = np.stack([y, cb, cr], axis=-1)
    rgb = ycbcr_to_rgb(ycbcr)
    result = np.clip(rgb[:height, :width], 0, 255).astype(np.uint8)
    _log.info("Color decode complete: %s", result.shape)
    return result


def _handle_restart(data: bytes, reader: BitReader,
                    restart_interval: int) -> bool:
    """Check if the reader hit a restart marker and handle it.

    Returns True if a restart marker was found and consumed, allowing
    decoding to continue.  Returns False otherwise.
    """
    if restart_interval <= 0:
        return False

    pos = reader.position
    if pos >= len(data) - 1:
        return False

    # Look for a restart marker (0xFFD0-0xFFD7).
    if data[pos] == 0xFF and 0xD0 <= data[pos + 1] <= 0xD7:
        # Consume the restart marker (2 bytes).
        # We need to advance the reader's position past the marker.
        # The BitReader's position is at the byte level; we can
        # construct a new reader from the position past the marker.
        reader._pos = pos + 2
        reader._cur = 0
        reader._nbits = 0
        _log.debug("Restart marker consumed at offset %d", pos)
        return True
    return False


def idct2d_safe(block: np.ndarray) -> np.ndarray:
    """Wrapper for idct2d with a safety import to avoid circular deps."""
    from .dct import idct2d
    return idct2d(block)


# Public alias.
decode = decode_image