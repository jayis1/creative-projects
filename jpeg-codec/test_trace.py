"""Trace the full encode/decode pipeline to find the bug."""
import sys; sys.path.insert(0, ".")
import numpy as np
from jpeg_codec.color import rgb_to_ycbcr, level_shift, unlevel_shift
from jpeg_codec.dct import dct2d, idct2d
from jpeg_codec.quantize import quantize_block, dequantize_block, get_quantization_tables
from jpeg_codec.zigzag import zigzag_block, izigzag_block
from jpeg_codec.bitio import BitWriter, BitReader
from jpeg_codec.huffman import (
    build_huffman_table, HuffmanTree,
    STD_DC_LUMA_BITS, STD_DC_LUMA_VALS,
    STD_AC_LUMA_BITS, STD_AC_LUMA_VALS,
    STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS,
    STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS,
)
from jpeg_codec.entropy import encode_block, decode_block

# 16x16, 4 constant blocks, 4:4:4
img = np.zeros((16, 16, 3), dtype=np.float64)
img[:8, :8] = [50, 100, 150]
img[:8, 8:] = [100, 150, 200]
img[8:, :8] = [150, 200, 50]
img[8:, 8:] = [200, 50, 100]

q = 90
luma_qt, chroma_qt = get_quantization_tables(q)

ycbcr = rgb_to_ycbcr(img)
channels = [ycbcr[..., c] for c in range(3)]
qt = [luma_qt, chroma_qt, chroma_qt]
dc_tables = [
    build_huffman_table(STD_DC_LUMA_BITS, STD_DC_LUMA_VALS),
    build_huffman_table(STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS),
    build_huffman_table(STD_DC_CHROMA_BITS, STD_DC_CHROMA_VALS),
]
ac_tables = [
    build_huffman_table(STD_AC_LUMA_BITS, STD_AC_LUMA_VALS),
    build_huffman_table(STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS),
    build_huffman_table(STD_AC_CHROMA_BITS, STD_AC_CHROMA_VALS),
]
dc_trees = [HuffmanTree.from_table(t) for t in dc_tables]
ac_trees = [HuffmanTree.from_table(t) for t in ac_tables]

# Manually encode each block and store the quantized coefficients
print("=== Encoding (4:4:4, Q=90) ===")
writer = BitWriter()
prev_dcs = [0, 0, 0]
orig_coeffs = []  # Store (channel, block_idx, zz_coeffs)

for by in range(2):
    for bx in range(2):
        for c in range(3):
            block = channels[c][by*8:by*8+8, bx*8:bx*8+8]
            shifted = level_shift(block)
            dct = dct2d(shifted)
            quant = quantize_block(dct, qt[c])
            zz = zigzag_block(quant)
            orig_coeffs.append((c, by*2+bx, zz.copy()))
            prev_dcs[c] = encode_block(zz, prev_dcs[c], dc_tables[c], ac_tables[c], writer)
            if zz[0] != 0 or np.count_nonzero(zz) > 1:
                print(f"  ch{c} block({by},{bx}): DC={zz[0]}, nonzeros={np.count_nonzero(zz)}, prev_dc_after={prev_dcs[c]}")

writer.flush()
encoded = writer.get_bytes()
print(f"Encoded: {len(encoded)} bytes")

# Decode
print("\n=== Decoding ===")
reader = BitReader(encoded)
prev_dcs = [0, 0, 0]
idx = 0
for by in range(2):
    for bx in range(2):
        for c in range(3):
            orig_c, orig_idx, orig_zz = orig_coeffs[idx]
            decoded_zz, prev_dcs[c] = decode_block(prev_dcs[c], dc_trees[c], ac_trees[c], reader)
            match = np.array_equal(orig_zz, decoded_zz)
            if not match:
                print(f"  MISMATCH ch{c} block({by},{bx}):")
                print(f"    orig:  {orig_zz[:16]}")
                print(f"    dec:   {decoded_zz[:16]}")
                print(f"    prev_dc: {prev_dcs[c]}")
            idx += 1

print("\nDone.")