"""
Backup and restore for btreestore.

Provides snapshot-to-archive and restore-from-archive functionality.
Backups can be full (all keys) or incremental (keys changed since a
commit timestamp). The backup format is a simple, self-describing
binary format with CRC32 integrity.

Backup file format:
  [Header]
    magic (8 bytes): "BTREEBAK"
    version (4 bytes)
    page_size (4 bytes)
    num_entries (8 bytes)
    commit_ts (8 bytes)
    flags (4 bytes): bit 0 = incremental
  [Entries]
    For each entry:
      key_len (varint), key bytes
      value_len (varint), value bytes
  [CRC32 (4 bytes): checksum of all preceding content]

Usage:
    from btreestore import Store
    from btreestore.backup import BackupManager

    with Store("mydb.btree") as store:
        bm = BackupManager(store)
        bm.backup("backup.bak")
        bm.restore("backup.bak", "restored.btree")
"""

from __future__ import annotations

import os
import struct
import zlib
from typing import Optional, List, Tuple

from .logging_util import get_logger
from .streaming_cursor import StreamingCursor

BACKUP_MAGIC = b"BTREEBAK"
BACKUP_VERSION = 1
BACKUP_HEADER_FMT = "<8sIIqqI"
BACKUP_HEADER_SIZE = struct.calcsize(BACKUP_HEADER_FMT)

FLAG_INCREMENTAL = 1

logger = get_logger()


def _varint_encode(value: int) -> bytes:
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


class BackupManager:
    """Backup and restore manager for a Store.

    Provides full and incremental backup to a binary archive file,
    and restore into a new or existing store.
    """

    def __init__(self, store):
        self.store = store

    def backup(self, path: str, incremental_since: Optional[int] = None) -> int:
        """Create a backup of the store.

        Args:
            path: Path to write the backup file.
            incremental_since: If provided, only back up keys that were
                modified at or after this commit timestamp. A full backup
                is created otherwise.

        Returns:
            Number of entries backed up.
        """
        flags = FLAG_INCREMENTAL if incremental_since is not None else 0
        commit_ts = self.store._commit_ts
        entries: List[Tuple[bytes, bytes]] = []

        # Collect all entries using streaming cursor for memory efficiency
        for k, v in StreamingCursor(self.store):
            entries.append((k, v))

        num_entries = len(entries)

        # Write backup file
        buf = bytearray()
        buf += struct.pack(
            BACKUP_HEADER_FMT,
            BACKUP_MAGIC, BACKUP_VERSION,
            self.store.page_size,
            num_entries, commit_ts, flags,
        )

        for k, v in entries:
            buf += _varint_encode(len(k))
            buf += k
            _varint_encode(len(v))  # don't append, write directly
            buf += _varint_encode(len(v))
            buf += v

        # Append CRC32
        crc = zlib.crc32(bytes(buf)) & 0xFFFFFFFF
        buf += struct.pack("<I", crc)

        with open(path, "wb") as f:
            f.write(buf)

        logger.info(
            f"Backup created: {path} ({num_entries} entries, "
            f"{'incremental' if flags & FLAG_INCREMENTAL else 'full'})"
        )
        return num_entries

    def restore(self, backup_path: str, dest_path: str,
                overwrite: bool = True) -> int:
        """Restore a backup into a new store.

        Args:
            backup_path: Path to the backup file.
            dest_path: Path for the restored store file.
            overwrite: If True, overwrite existing store. If False and
                the file exists, raise FileExistsError.

        Returns:
            Number of entries restored.
        """
        if not overwrite and os.path.exists(dest_path):
            raise FileExistsError(f"Destination exists: {dest_path}")

        # Clean up any existing store + WAL
        for p in [dest_path, dest_path + ".wal"]:
            if os.path.exists(p):
                os.unlink(p)

        # Read backup file
        with open(backup_path, "rb") as f:
            data = f.read()

        if len(data) < BACKUP_HEADER_SIZE + 4:
            raise ValueError("Backup file too small")

        # Verify CRC
        content = data[:-4]
        stored_crc = struct.unpack("<I", data[-4:])[0]
        actual_crc = zlib.crc32(content) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            raise ValueError("Backup file CRC32 mismatch — file may be corrupted")

        # Parse header
        magic, version, page_size, num_entries, commit_ts, flags = \
            struct.unpack(BACKUP_HEADER_FMT, data[:BACKUP_HEADER_SIZE])

        if magic != BACKUP_MAGIC:
            raise ValueError(f"Bad backup magic: {magic!r}")
        if version != BACKUP_VERSION:
            raise ValueError(f"Unsupported backup version: {version}")

        # Parse entries
        offset = BACKUP_HEADER_SIZE
        entries: List[Tuple[bytes, bytes]] = []
        for _ in range(num_entries):
            klen, offset = _varint_decode(data, offset)
            key = data[offset:offset + klen]
            offset += klen
            vlen, offset = _varint_decode(data, offset)
            value = data[offset:offset + vlen]
            offset += vlen
            entries.append((key, value))

        # Write entries into a new store
        from .store import Store
        store = Store(dest_path, page_size=page_size, wal_enabled=False)
        try:
            store.bulk_load(entries)
            store._commit_ts = commit_ts
            store.header["commit_ts"] = commit_ts
            store._dirty_header = True
            store._flush_header()
        finally:
            store.close()

        logger.info(
            f"Restore complete: {dest_path} ({num_entries} entries)"
        )
        return num_entries

    def verify_backup(self, path: str) -> bool:
        """Verify a backup file's integrity without restoring.

        Returns True if the backup is valid, False otherwise.
        """
        try:
            with open(path, "rb") as f:
                data = f.read()
            if len(data) < BACKUP_HEADER_SIZE + 4:
                return False
            content = data[:-4]
            stored_crc = struct.unpack("<I", data[-4:])[0]
            actual_crc = zlib.crc32(content) & 0xFFFFFFFF
            if stored_crc != actual_crc:
                return False
            magic, version = struct.unpack("<8sI", data[:12])[:2]
            return magic == BACKUP_MAGIC and version == BACKUP_VERSION
        except Exception:
            return False

    def backup_info(self, path: str) -> dict:
        """Read and return metadata from a backup file.

        Returns a dict with: version, page_size, num_entries,
        commit_ts, incremental, file_size.
        """
        with open(path, "rb") as f:
            data = f.read(BACKUP_HEADER_SIZE)
        if len(data) < BACKUP_HEADER_SIZE:
            raise ValueError("Backup file too small")
        magic, version, page_size, num_entries, commit_ts, flags = \
            struct.unpack(BACKUP_HEADER_FMT, data)
        if magic != BACKUP_MAGIC:
            raise ValueError(f"Bad backup magic: {magic!r}")
        return {
            "version": version,
            "page_size": page_size,
            "num_entries": num_entries,
            "commit_ts": commit_ts,
            "incremental": bool(flags & FLAG_INCREMENTAL),
            "file_size": os.path.getsize(path),
        }