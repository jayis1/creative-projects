import struct
from pathlib import Path

from errors import DecodeError


def read_pcap(path: str | Path, *, max_packets: int = 10000) -> list[bytes]:
    """Read classic pcap (micro/nanosecond, either byte order), Ethernet only.

    Rejects unsupported link types, truncated records, oversized captures, and
    capture files above 64 MiB before materializing packet data.
    """
    source = Path(path)
    if source.stat().st_size > 64 * 1024 * 1024:
        raise DecodeError("capture exceeds 64 MiB limit")
    data = source.read_bytes()
    if len(data) < 24:
        raise DecodeError("truncated pcap global header")
    magic = data[:4]
    formats = {b"\xd4\xc3\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">",
               b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\x3c\x4d": ">"}
    if magic not in formats:
        raise DecodeError("unsupported pcap magic")
    endian = formats[magic]
    major, minor, _zone, _sigfigs, snaplen, network = struct.unpack_from(endian + "HHIIII", data, 4)
    if (major, minor) != (2, 4) or snaplen == 0 or network != 1:
        raise DecodeError("unsupported pcap version, snaplen, or link type (need Ethernet)")
    if max_packets < 0:
        raise DecodeError("max_packets cannot be negative")
    frames: list[bytes] = []
    offset = 24
    while offset < len(data):
        if len(frames) >= max_packets:
            raise DecodeError(f"capture exceeds packet limit ({max_packets})")
        if offset + 16 > len(data):
            raise DecodeError("truncated pcap packet header")
        _sec, _frac, incl_len, orig_len = struct.unpack_from(endian + "IIII", data, offset)
        offset += 16
        if incl_len > snaplen or incl_len > 65535 or incl_len > orig_len:
            raise DecodeError("invalid pcap captured/original packet length")
        if offset + incl_len > len(data):
            raise DecodeError("truncated pcap packet data")
        frames.append(data[offset:offset + incl_len])
        offset += incl_len
    return frames
