"""Codec pipeline: chain multiple compression codecs together.

Allows composing codecs like RLE → Huffman or Delta → LZ77 for
better compression on specific data types.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .rle import RLECodec
from .delta import DeltaCodec


CODEC_REGISTRY = {
    "huffman": HuffmanCodec,
    "lz77": LZ77Codec,
    "bwt": BWTCodec,
    "deflate": DeflateCodec,
    "rle": RLECodec,
    "delta": DeltaCodec,
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
        """
        self.codecs = []
        for name in codec_names:
            if name not in CODEC_REGISTRY:
                raise ValueError(f"Unknown codec: {name}. Available: {list(CODEC_REGISTRY.keys())}")
            kwargs = codec_kwargs.get(name, {})
            self.codecs.append(CODEC_REGISTRY[name](**kwargs))
        self.codec_names = codec_names

    def compress(self, data: bytes) -> bytes:
        """Compress data through the pipeline."""
        import struct

        # Header: number of codecs (1 byte), then for each codec: name length (1 byte) + name bytes
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
        """Decompress data through the pipeline (reverse order)."""
        # Parse header
        num_codecs = data[0]
        offset = 1
        codec_names = []
        for _ in range(num_codecs):
            name_len = data[offset]
            offset += 1
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


def create_pipeline(spec: str, **kwargs: dict) -> Pipeline:
    """Create a pipeline from a string specification.

    Args:
        spec: Codec names separated by '+', e.g. 'rle+huffman', 'delta+deflate'
        kwargs: Optional keyword arguments for specific codecs.

    Returns:
        Pipeline instance.
    """
    codec_names = [s.strip() for s in spec.split("+")]
    return Pipeline(codec_names, **kwargs)