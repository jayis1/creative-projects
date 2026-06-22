"""JPEG file metadata inspection.

Provides :func:`get_info` which parses the JPEG marker structure
and returns a :class:`JPEGInfo` dataclass with useful metadata:
dimensions, number of components, quantization table details,
Huffman table presence, comment, restart interval, APP0/JFIF
info, and a marker map.

This is a richer alternative to the CLI's ``info`` command.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from .zigzag import ZIGZAG_ORDER

__all__ = ["JPEGInfo", "get_info"]


@dataclass
class ComponentInfo:
    """Information about one image component (channel)."""
    component_id: int
    sampling_h: int
    sampling_v: int
    quant_table_id: int


@dataclass
class JPEGInfo:
    """Metadata extracted from a JPEG file."""
    width: int = 0
    height: int = 0
    precision: int = 8
    num_components: int = 0
    components: List[ComponentInfo] = field(default_factory=list)
    quant_tables: Dict[int, List[int]] = field(default_factory=dict)
    huffman_dc_tables: Dict[int, int] = field(default_factory=dict)
    huffman_ac_tables: Dict[int, int] = field(default_factory=dict)
    comment: Optional[str] = None
    restart_interval: int = 0
    jfif_version: Optional[Tuple[int, int]] = None
    density_units: int = 0
    x_density: int = 0
    y_density: int = 0
    markers: List[Tuple[str, int]] = field(default_factory=list)
    file_size: int = 0
    encoding_process: str = "baseline"

    @property
    def sampling_string(self) -> str:
        """Human-readable subsampling string like '4:2:0'."""
        if self.num_components < 3:
            return "grayscale"
        comps = self.components
        h_max = max(c.sampling_h for c in comps)
        v_max = max(c.sampling_v for c in comps)
        y_h, y_v = comps[0].sampling_h, comps[0].sampling_v
        cb_h, cb_v = comps[1].sampling_h, comps[1].sampling_v
        cr_h, cr_v = comps[2].sampling_h, comps[2].sampling_v
        # Compute the 4:X:Y notation.
        j = y_h * y_v
        a = cb_h * cb_v
        b = cr_h * cr_v
        if h_max == 2 and v_max == 2:
            if a == 1 and b == 1:
                return "4:2:0" if y_h == 2 else "4:2:0"
            elif a == 2 and b == 2:
                return "4:4:4"
        if h_max == 4 and v_max == 1:
            return "4:1:1"
        if h_max == 2 and v_max == 1:
            return "4:2:2"
        return f"{j}:{a}:{b}"


_MARKER_NAMES = {
    0xFFD8: "SOI",
    0xFFD9: "EOI",
    0xFFE0: "APP0",
    0xFFE1: "APP1",
    0xFFE2: "APP2",
    0xFFDB: "DQT",
    0xFFC0: "SOF0",
    0xFFC1: "SOF1",
    0xFFC2: "SOF2",
    0xFFC3: "SOF3",
    0xFFC4: "DHT",
    0xFFC8: "JPG",
    0xFFCA: "SOF10",
    0xFFCC: "DAC",
    0xFFDA: "SOS",
    0xFFDD: "DRI",
    0xFFD0: "RST0", 0xFFD1: "RST1", 0xFFD2: "RST2",
    0xFFD3: "RST3", 0xFFD4: "RST4", 0xFFD5: "RST5",
    0xFFD6: "RST6", 0xFFD7: "RST7",
    0xFFFE: "COM",
}


def _marker_name(marker: int) -> str:
    if marker in _MARKER_NAMES:
        return _MARKER_NAMES[marker]
    if 0xFFE0 <= marker <= 0xFFEF:
        return f"APP{marker & 0xF}"
    return f"0x{marker:04X}"


def get_info(data: bytes) -> JPEGInfo:
    """Parse a JPEG byte stream and return metadata.

    Parameters
    ----------
    data : bytes
        Raw JPEG file data.

    Returns
    -------
    JPEGInfo
        Extracted metadata.

    Raises
    ------
    ValueError
        If the data is not a valid JPEG file.
    """
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError("Not a JPEG file (missing SOI marker)")

    info = JPEGInfo(file_size=len(data))
    info.markers.append(("SOI", 0))
    pos = 2  # Skip SOI.

    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue

        marker = (data[pos] << 8) | data[pos + 1]

        # Skip fill bytes (0xFF 0xFF).
        if marker == 0xFFFF:
            pos += 1
            continue

        # Standalone markers (no segment length).
        if marker == 0xFFD9:  # EOI
            info.markers.append(("EOI", pos))
            break
        if 0xFFD0 <= marker <= 0xFFD7:  # RSTn
            info.markers.append((_marker_name(marker), pos))
            pos += 2
            continue

        name = _marker_name(marker)
        info.markers.append((name, pos))

        if marker == 0xFFDA:  # SOS -- entropy data follows
            break

        if pos + 4 > len(data):
            break
        length = (data[pos + 2] << 8) | data[pos + 3]

        if marker == 0xFFE0:  # APP0 (JFIF)
            _parse_jfif(data, pos + 4, length - 2, info)
        elif marker == 0xFFDB:  # DQT
            _parse_dqt_info(data, pos + 4, length - 2, info)
        elif 0xFFC0 <= marker <= 0xFFCF and marker != 0xFFC4:
            _parse_sof(data, pos + 4, length - 2, marker, info)
        elif marker == 0xFFC4:  # DHT
            _parse_dht_info(data, pos + 4, length - 2, info)
        elif marker == 0xFFDD:  # DRI
            if pos + 6 <= len(data):
                info.restart_interval = struct.unpack(
                    ">H", data[pos + 4:pos + 6]
                )[0]
        elif marker == 0xFFFE:  # COM
            comment_bytes = data[pos + 4: pos + 2 + length]
            try:
                info.comment = comment_bytes.decode("utf-8")
            except UnicodeDecodeError:
                info.comment = comment_bytes.decode("latin-1", errors="replace")

        pos += 2 + length

    return info


def _parse_jfif(data, offset, length, info: JPEGInfo):
    """Parse APP0/JFIF segment."""
    if length < 14:
        return
    ident = data[offset:offset + 5]
    if ident != b"JFIF\x00":
        return
    info.jfif_version = (
        data[offset + 5],
        data[offset + 6],
    )
    info.density_units = data[offset + 7]
    info.x_density = (data[offset + 8] << 8) | data[offset + 9]
    info.y_density = (data[offset + 10] << 8) | data[offset + 11]


def _parse_dqt_info(data, offset, length, info: JPEGInfo):
    """Parse DQT segment for table info."""
    pos = offset
    end = offset + length
    while pos < end:
        if pos >= end:
            break
        pq_tq = data[pos]
        pos += 1
        table_id = pq_tq & 0xF
        precision = (pq_tq >> 4) & 0xF
        if precision == 0:
            vals = list(data[pos:pos + 64])
            pos += 64
        else:
            vals = []
            for i in range(64):
                v = (data[pos] << 8) | data[pos + 1]
                vals.append(v)
                pos += 2
        info.quant_tables[table_id] = vals


def _parse_sof(data, offset, length, marker, info: JPEGInfo):
    """Parse SOF segment."""
    info.precision = data[offset]
    info.height = (data[offset + 1] << 8) | data[offset + 2]
    info.width = (data[offset + 3] << 8) | data[offset + 4]
    n = data[offset + 5]
    info.num_components = n
    info.encoding_process = {
        0xFFC0: "baseline",
        0xFFC1: "extended sequential",
        0xFFC2: "progressive",
        0xFFC3: "lossless",
    }.get(marker, f"unknown (0x{marker:04X})")
    for i in range(n):
        base = offset + 6 + i * 3
        cid = data[base]
        hv = data[base + 1]
        qt_id = data[base + 2]
        info.components.append(ComponentInfo(
            component_id=cid,
            sampling_h=(hv >> 4) & 0xF,
            sampling_v=hv & 0xF,
            quant_table_id=qt_id,
        ))


def _parse_dht_info(data, offset, length, info: JPEGInfo):
    """Parse DHT segment for table info."""
    pos = offset
    end = offset + length
    while pos < end:
        tc_th = data[pos]
        pos += 1
        table_class = (tc_th >> 4) & 0xF
        table_id = tc_th & 0xF
        bits = list(data[pos:pos + 16])
        pos += 16
        n_symbols = sum(bits)
        pos += n_symbols
        if table_class == 0:
            info.huffman_dc_tables[table_id] = n_symbols
        else:
            info.huffman_ac_tables[table_id] = n_symbols