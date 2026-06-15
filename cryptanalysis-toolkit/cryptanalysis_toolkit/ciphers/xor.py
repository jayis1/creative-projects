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
        decryption using English letter frequency analysis combined
        with space ratio and printable ASCII ratio.

        Args:
            data: XOR-encrypted data.
            min_key: Minimum key value to try.
            max_key: Maximum key value to try.

        Returns:
            List of dicts with keys: 'key', 'plaintext', 'score'.
            Sorted by score (highest first).
        """
        # English letter frequency distribution (percentage)
        english_freq = {
            'A': 8.167, 'B': 1.492, 'C': 2.782, 'D': 4.253, 'E': 12.702,
            'F': 2.228, 'G': 2.015, 'H': 6.094, 'I': 6.966, 'J': 0.153,
            'K': 0.772, 'L': 4.025, 'M': 2.406, 'N': 6.749, 'O': 7.507,
            'P': 1.929, 'Q': 0.095, 'R': 5.987, 'S': 6.327, 'T': 9.056,
            'U': 2.758, 'V': 0.978, 'W': 2.360, 'X': 0.150, 'Y': 1.974,
            'Z': 0.074,
        }

        results = []
        for k in range(min_key, max_key + 1):
            decrypted = bytes(b ^ k for b in data)

            # Compute English frequency score
            text = decrypted.decode('ascii', errors='replace')
            alpha_chars = [ch for ch in text.upper() if ch.isalpha()]
            if alpha_chars:
                total_alpha = len(alpha_chars)
                from collections import Counter
                counts = Counter(alpha_chars)
                freq_score = 0.0
                for ch, count in counts.items():
                    if ch in english_freq:
                        observed = (count / total_alpha) * 100
                        freq_score -= abs(observed - english_freq[ch])
                # Normalize by text length for fair comparison
                freq_score = freq_score / max(total_alpha, 1)
            else:
                freq_score = -100.0

            # Space ratio bonus (English text typically ~15-20% spaces)
            space_ratio = sum(1 for b in decrypted if b == 32) / max(len(decrypted), 1)
            space_bonus = 0.0
            if 0.10 <= space_ratio <= 0.25:
                space_bonus = 2.0

            # Printable ASCII penalty for non-printable characters
            printable = sum(1 for b in decrypted if 32 <= b <= 126 or b in (9, 10, 13))
            printable_ratio = printable / max(len(decrypted), 1)
            printable_score = printable_ratio * 5.0

            # Combined score
            score = freq_score + space_bonus + printable_score
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