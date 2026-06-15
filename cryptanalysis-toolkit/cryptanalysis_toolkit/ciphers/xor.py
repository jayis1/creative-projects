"""XOR cipher — byte-level XOR encryption."""

from __future__ import annotations
from typing import List, Optional


class XORCipher:
    """XOR cipher implementation.

    Applies XOR operation between plaintext bytes and a repeating key.
    Common in simple encryption and as a building block in more complex
    ciphers. Works on arbitrary bytes, not just alphabetic characters.

    Args:
        key: The XOR key as bytes or a string (which will be UTF-8 encoded).

    Raises:
        ValueError: If key is empty.
    """

    def __init__(self, key: bytes | str) -> None:
        if isinstance(key, str):
            self.key = key.encode('utf-8')
        else:
            self.key = key

        if len(self.key) == 0:
            raise ValueError("Key cannot be empty")

    def encrypt(self, plaintext: bytes | str) -> bytes:
        """Encrypt data using XOR cipher.

        Args:
            plaintext: Data to encrypt. Strings are UTF-8 encoded.

        Returns:
            Encrypted data as bytes.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        return bytes(p ^ self.key[i % len(self.key)] for i, p in enumerate(plaintext))

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data using XOR cipher.

        Since XOR is its own inverse, this is identical to encrypt().

        Args:
            ciphertext: Data to decrypt.

        Returns:
            Decrypted data as bytes.
        """
        return bytes(c ^ self.key[i % len(self.key)] for i, c in enumerate(ciphertext))

    @staticmethod
    def single_byte_xor_break(data: bytes, min_key: int = 0, max_key: int = 255) -> List[dict]:
        """Attempt to break single-byte XOR encryption.

        Tries all 256 possible single-byte keys and scores each
        decryption by how many printable ASCII characters it produces.

        Args:
            data: XOR-encrypted data.
            min_key: Minimum key value to try.
            max_key: Maximum key value to try.

        Returns:
            List of dicts with keys: 'key', 'plaintext', 'score'.
            Sorted by score (highest first).
        """
        results = []
        for k in range(min_key, max_key + 1):
            decrypted = bytes(b ^ k for b in data)
            # Score by printable ASCII ratio
            printable = sum(1 for b in decrypted if 32 <= b <= 126 or b in (9, 10, 13))
            score = printable / max(len(decrypted), 1)
            results.append({
                "key": k,
                "plaintext": decrypted,
                "score": score,
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def __repr__(self) -> str:
        key_repr = self.key.decode('utf-8', errors='replace') if len(self.key) < 20 else f"<{len(self.key)} bytes>"
        return f"XORCipher(key={key_repr!r})"