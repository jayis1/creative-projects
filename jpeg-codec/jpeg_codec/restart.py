"""Restart markers (DRI/RST) and comment (COM) marker support.

Restart markers divide the entropy-coded data into independent
segments, allowing error-resilient decoding: if a bit error
corrupts one segment, the decoder can resync at the next
restart marker instead of losing the rest of the image.

This module provides:
  - :func:`should_emit_restart` — check if a restart marker is due
  - :func:`emit_restart` — write a RST marker to the bit stream
  - :func:`reset_dc` — reset DC predictors at restart boundaries
  - :func:`write_com` — write a COM (comment) marker segment
  - :func:`parse_com` — read a COM marker's payload

Restart marker codes are RST0=0xFFD0 through RST7=0xFFD7,
cycling modulo 8.
"""

import struct

__all__ = [
    "RST_MARKERS",
    "COM_MARKER",
    "DRI_MARKER",
    "should_emit_restart",
    "emit_restart_marker",
    "write_dri_segment",
    "write_com_segment",
    "parse_com_segment",
]


# RST0..RST7 marker codes.
RST_MARKERS = [0xFFD0 + i for i in range(8)]

COM_MARKER = 0xFFFE
DRI_MARKER = 0xFFDD


def should_emit_restart(mcus_since_restart: int,
                        restart_interval: int) -> bool:
    """Return True if a restart marker should be emitted.

    Parameters
    ----------
    mcus_since_restart : int
        Number of MCUs encoded since the last restart marker (or start).
    restart_interval : int
        Number of MCUs between restart markers (from DRI segment).
        0 disables restart markers.
    """
    if restart_interval <= 0:
        return False
    return mcus_since_restart >= restart_interval


def emit_restart_marker(stream, rst_index: int) -> int:
    """Emit a RST marker to the byte stream and cycle the index.

    Parameters
    ----------
    stream
        Object with a ``write_marker(marker: int)`` method, or a
        bytearray-like object.
    rst_index : int
        Current restart marker index (0-7, cycles modulo 8).

    Returns
    -------
    int
        The next restart index (rst_index + 1) % 8.
    """
    marker = RST_MARKERS[rst_index % 8]
    if hasattr(stream, "write_marker"):
        stream.write_marker(marker)
    else:
        stream += struct.pack(">H", marker)
    return (rst_index + 1) % 8


def write_dri_segment(stream, restart_interval: int) -> None:
    """Write a DRI (Define Restart Interval) marker segment.

    Parameters
    ----------
    stream
        Object with a ``write_segment(marker, payload)`` method.
    restart_interval : int
        Number of MCUs between restart markers.
    """
    payload = struct.pack(">H", restart_interval)
    if hasattr(stream, "write_segment"):
        stream.write_segment(DRI_MARKER, payload)
    else:
        raise TypeError("stream must have write_segment method")


def write_com_segment(stream, comment: str) -> None:
    """Write a COM (comment) marker segment.

    Parameters
    ----------
    stream
        Object with a ``write_segment(marker, payload)`` method.
    comment : str
        Comment text (encoded as UTF-8).
    """
    payload = comment.encode("utf-8")
    if hasattr(stream, "write_segment"):
        stream.write_segment(COM_MARKER, payload)
    else:
        raise TypeError("stream must have write_segment method")


def parse_com_segment(data: bytes, offset: int) -> tuple:
    """Parse a COM marker segment.

    Parameters
    ----------
    data : bytes
        The full JPEG data buffer.
    offset : int
        Byte offset of the marker (pointing at the 0xFF byte).

    Returns
    -------
    (str, int)
        The decoded comment string and the offset past the segment.
    """
    # Skip the 0xFF marker byte and the marker code byte.
    marker = (data[offset] << 8) | data[offset + 1]
    if marker != COM_MARKER:
        raise ValueError(
            f"Expected COM marker 0x{COM_MARKER:04X}, got 0x{marker:04X}"
        )
    length = (data[offset + 2] << 8) | data[offset + 3]
    comment_bytes = data[offset + 4: offset + 2 + length]
    try:
        comment = comment_bytes.decode("utf-8")
    except UnicodeDecodeError:
        comment = comment_bytes.decode("latin-1")
    return comment, offset + 2 + length