"""
Write-Ahead Log (WAL) for crash recovery in btreestore.

The WAL records all write operations (put/delete) before they are applied
to the main B+Tree file. On startup, if the WAL contains uncommitted entries,
they are replayed to recover the last committed state.

WAL file format:
  [record_1][record_2]...
  
Each record:
  - CRC32 (4 bytes): checksum of the record body
  - Length (4 bytes): length of the record body
  - Body: serialized operation (op_type + key + value)
  
Operation encoding:
  - op_type (1 byte): 1=put, 2=delete, 3=commit_marker
  - key_len (varint), key bytes
  - value_len (varint), value bytes (only for put)
"""

from __future__ import annotations

import os
import struct
import zlib
import threading
from typing import List, Optional, Tuple, Iterator
from .logging_util import get_logger

WAL_MAGIC = b"WAL\x01"
WAL_HEADER_FMT = "<4sI"
WAL_HEADER_SIZE = struct.calcsize(WAL_HEADER_FMT)

OP_PUT = 1
OP_DELETE = 2
OP_COMMIT = 3

CRC_SIZE = 4
LENGTH_SIZE = 4

logger = get_logger()


def _varint_encode(value: int) -> bytes:
    """LEB128 unsigned varint encoding."""
    buf = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break
    return bytes(buf)


def _varint_decode(data: bytes, offset: int) -> Tuple[int, int]:
    """Decode LEB128 unsigned varint, return (value, new_offset)."""
    result = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, offset


class WAL:
    """Write-Ahead Log for crash recovery.

    The WAL records operations before they are applied to the store.
    On recovery, the WAL is replayed to reconstruct the last committed state.

    Usage:
        wal = WAL("mydb.wal")
        wal.append_put(b"key", b"value")
        wal.append_commit()
        wal.checkpoint()  # truncate after successful flush
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._fd = None
        self._closed = False
        self._open()

    def _open(self) -> None:
        """Open or create the WAL file."""
        exists = os.path.exists(self.path) and os.path.getsize(self.path) >= WAL_HEADER_SIZE
        if exists:
            self._fd = open(self.path, "r+b")
            # Verify magic
            header = self._fd.read(WAL_HEADER_SIZE)
            magic, _ = struct.unpack(WAL_HEADER_FMT, header)
            if magic != WAL_MAGIC:
                # Old or corrupt WAL — truncate and start fresh
                logger.warning(f"WAL file {self.path} has bad magic, truncating")
                self._fd.close()
                self._fd = open(self.path, "w+b")
                self._write_header()
        else:
            self._fd = open(self.path, "w+b")
            self._write_header()

    def _write_header(self) -> None:
        """Write the WAL file header."""
        self._fd.seek(0)
        self._fd.write(struct.pack(WAL_HEADER_FMT, WAL_MAGIC, 1))
        self._fd.flush()

    def _encode_op(self, op_type: int, key: bytes, value: Optional[bytes]) -> bytes:
        """Encode a WAL operation record body."""
        body = bytearray()
        body.append(op_type)
        body += _varint_encode(len(key))
        body += key
        if op_type == OP_PUT and value is not None:
            body += _varint_encode(len(value))
            body += value
        return bytes(body)

    def _write_record(self, body: bytes) -> None:
        """Write a record to the WAL file."""
        crc = zlib.crc32(body) & 0xFFFFFFFF
        record = struct.pack("<II", crc, len(body)) + body
        with self._lock:
            if self._fd is None or self._closed:
                raise RuntimeError("WAL is closed")
            self._fd.seek(0, 2)  # seek to end
            self._fd.write(record)
            self._fd.flush()

    def append_put(self, key: bytes, value: bytes) -> None:
        """Append a put operation to the WAL."""
        body = self._encode_op(OP_PUT, key, value)
        self._write_record(body)
        logger.debug(f"WAL put: key={key!r}, value_len={len(value)}")

    def append_delete(self, key: bytes) -> None:
        """Append a delete operation to the WAL."""
        body = self._encode_op(OP_DELETE, key, b"")
        self._write_record(body)
        logger.debug(f"WAL delete: key={key!r}")

    def append_commit(self) -> None:
        """Append a commit marker to the WAL."""
        body = self._encode_op(OP_COMMIT, b"", b"")
        self._write_record(body)
        logger.debug("WAL commit marker written")

    def replay(self) -> List[Tuple[int, bytes, Optional[bytes]]]:
        """Read and return all records from the WAL.

        Returns a list of (op_type, key, value) tuples.
        Records after the last commit marker are discarded (uncommitted).
        """
        with self._lock:
            self._fd.seek(0)
            # Skip header
            self._fd.read(WAL_HEADER_SIZE)

            operations: List[Tuple[int, bytes, Optional[bytes]]] = []
            committed_ops: List[Tuple[int, bytes, Optional[bytes]]] = []

            while True:
                header = self._fd.read(CRC_SIZE + LENGTH_SIZE)
                if len(header) < CRC_SIZE + LENGTH_SIZE:
                    break
                crc, body_len = struct.unpack("<II", header)
                body = self._fd.read(body_len)
                if len(body) < body_len:
                    logger.warning("WAL truncated record, stopping replay")
                    break

                # Verify CRC
                if (zlib.crc32(body) & 0xFFFFFFFF) != crc:
                    logger.warning("WAL CRC mismatch, stopping replay")
                    break

                # Decode operation
                offset = 0
                op_type = body[offset]
                offset += 1

                if op_type == OP_COMMIT:
                    committed_ops = list(operations)
                    operations = []
                    continue

                klen, offset = _varint_decode(body, offset)
                key = body[offset:offset + klen]
                offset += klen

                value: Optional[bytes] = None
                if op_type == OP_PUT:
                    vlen, offset = _varint_decode(body, offset)
                    value = body[offset:offset + vlen]
                    offset += vlen

                operations.append((op_type, key, value))

            # If there are uncommitted operations after the last commit, discard them
            logger.info(f"WAL replay: {len(committed_ops)} committed operations recovered")
            return committed_ops

    def checkpoint(self) -> None:
        """Truncate the WAL after all data has been flushed to the main file.

        This is called after a successful flush of dirty pages to the store file.
        """
        with self._lock:
            if self._fd is None or self._closed:
                return
            self._fd.close()
            self._fd = open(self.path, "w+b")
            self._write_header()
            logger.debug("WAL checkpointed (truncated)")

    def close(self) -> None:
        """Close the WAL file."""
        with self._lock:
            if self._fd is not None:
                self._fd.flush()
                self._fd.close()
                self._fd = None
            self._closed = True

    def __enter__(self) -> "WAL":
        return self

    def __exit__(self, *args) -> None:
        self.close()