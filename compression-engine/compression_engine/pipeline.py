"""Codec pipeline: chain multiple compression codecs together.

Allows composing codecs like RLE → Huffman or Delta → LZ77 for
better compression on specific data types.
"""

from __future__ import annotations

import struct
from typing import Dict, List, Optional, Tuple
from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .rle import RLECodec
from .delta import DeltaCodec
from .lzw import LZWCodec
from .arithmetic import ArithmeticCodec

CODEC_REGISTRY: Dict[str, type] = {
    "huffman": HuffmanCodec,
    "lz77": LZ77Codec,
    "bwt": BWTCodec,
    "deflate": DeflateCodec,
    "rle": RLECodec,
    "delta": DeltaCodec,
    "lzw": LZWCodec,
    "arithmetic": ArithmeticCodec,
}


class Pipeline:
    """A chain of codecs applied sequentially.

    Compression: data → codec1.compress → codec2.compress → ... → output
    Decompression: data → codecN.decompress → ... → codec1.decompress → output

    The pipeline header stores the codec names so decompression
    automatically knows which codecs to use and in what order.
    """

    def __init__(self, codec_names: List[str], **codec_kwargs: dict) -> None:
        """Create a codec pipeline.

        Args:
            codec_names: List of codec names to apply in order.
            codec_kwargs: Optional keyword arguments for specific codecs.

        Raises:
            ValueError: If a codec name is not in the registry.
        """
        self.codecs = []
        for name in codec_names:
            if name not in CODEC_REGISTRY:
                raise ValueError(f"Unknown codec: {name}. Available: {list(CODEC_REGISTRY.keys())}")
            kwargs = codec_kwargs.get(name, {})
            self.codecs.append(CODEC_REGISTRY[name](**kwargs))
        self.codec_names = codec_names

    def compress(self, data: bytes) -> bytes:
        """Compress data through the pipeline.

        Args:
            data: Raw input bytes.

        Returns:
            Compressed bytes with pipeline header.
        """
        # Header: number of codecs (1 byte), then for each codec:
        # name length (1 byte) + name bytes
        header = bytearray()
        header.append(len(self.codec_names))
        for name in self.codec_names:
            name_bytes = name.encode("ascii")
            header.append(len(name_bytes))
            header.extend(name_bytes)

        current = data
        for codec in self.codecs:
            current = codec.compress(current)

        return bytes(header) + current

    def decompress(self, data: bytes) -> bytes:
        """Decompress data through the pipeline (reverse order).

        Args:
            data: Compressed bytes with pipeline header.

        Returns:
            Original uncompressed bytes.

        Raises:
            ValueError: If the pipeline header is invalid.
        """
        if len(data) < 1:
            raise ValueError("Data too short for pipeline header")

        num_codecs = data[0]
        offset = 1
        codec_names = []
        for _ in range(num_codecs):
            if offset >= len(data):
                raise ValueError("Truncated pipeline header")
            name_len = data[offset]
            offset += 1
            if offset + name_len > len(data):
                raise ValueError("Truncated codec name in pipeline header")
            name = data[offset:offset + name_len].decode("ascii")
            offset += name_len
            codec_names.append(name)

        # Build codecs in reverse order for decompression
        codecs = []
        for name in reversed(codec_names):
            if name not in CODEC_REGISTRY:
                raise ValueError(f"Unknown codec in pipeline: {name}")
            codecs.append(CODEC_REGISTRY[name]())

        current = data[offset:]
        for codec in codecs:
            current = codec.decompress(current)

        return current

    def __repr__(self) -> str:
        return f"Pipeline({'+'.join(self.codec_names)})"


def create_pipeline(spec: str, **kwargs: dict) -> Pipeline:
    """Create a pipeline from a string specification.

    Args:
        spec: Codec names separated by '+', e.g. 'rle+huffman', 'delta+deflate'
        kwargs: Optional keyword arguments for specific codecs.

    Returns:
        Pipeline instance.

    Raises:
        ValueError: If spec contains unknown codec names.
    """
    codec_names = [s.strip() for s in spec.split("+")]
    return Pipeline(codec_names, **kwargs)