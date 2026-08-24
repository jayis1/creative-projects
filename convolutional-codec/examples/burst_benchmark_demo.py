from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from convolutional_codec import CRC, BlockInterleaver, ConvolutionalCodec, Trellis
from convolutional_codec.analysis import benchmark_burst

codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)), puncture_pattern=(1, 1, 0, 1))
crc = CRC(0b10011, width=4)
interleaver = BlockInterleaver(3, 7)

series = benchmark_burst(
    codec,
    [0.08, 0.16, 0.24],
    p_good_to_bad=0.05,
    p_bad_to_good=0.3,
    good_error_probability=0.002,
    bits=[1, 0, 1, 1, 0, 1, 0, 0],
    trials=20,
    seed=17,
    crc=crc,
    interleaver=interleaver,
)

for point in series:
    print(point)
