"""Abstract base class for all cipher implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseCipher(ABC):
    """Abstract base class that all cipher implementations must inherit from.

    Enforces a consistent interface: every cipher must implement
    ``encrypt()`` and ``decrypt()`` methods, and provide a ``__repr__``.
    """

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt the given plaintext.

        Args:
            plaintext: The text to encrypt.

        Returns:
            Encrypted ciphertext string.
        """
        ...

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt the given ciphertext.

        Args:
            ciphertext: The text to decrypt.

        Returns:
            Decrypted plaintext string.
        """
        ...

    @abstractmethod
    def __repr__(self) -> str:
        ...