from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from convolutional_codec import CRC, BlockInterleaver, ConvolutionalCodec, Trellis
from convolutional_codec.analysis import analyze_codec

codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)), puncture_pattern=(1, 1, 0, 1))
crc = CRC(0b10011, width=4)
interleaver = BlockInterleaver(3, 7)
payload = [1, 0, 1, 1, 0, 1, 0, 0]

result = codec.simulate_burst(
    payload,
    p_good_to_bad=0.08,
    p_bad_to_good=0.35,
    good_error_probability=0.0,
    bad_error_probability=0.18,
    crc=crc,
    interleaver=interleaver,
    seed=11,
)
analysis = analyze_codec(codec, max_input_bits=6)

print("payload       ", payload)
print("decoded       ", result["decoded_bits"])
print("crc ok        ", result["crc_ok"])
print("bit errors    ", result["bit_errors"])
print("distance est. ", analysis["distance_estimate"]["estimated_free_distance"])
