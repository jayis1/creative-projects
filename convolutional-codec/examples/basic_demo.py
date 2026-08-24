from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from convolutional_codec.codec import ConvolutionalCodec, Trellis

codec = ConvolutionalCodec(Trellis(3, (0o7, 0o5)))
payload = [1, 0, 1, 1, 0, 1]
encoded = codec.encode(payload)
received = encoded.copy()
received[4] ^= 1
result = codec.decode(received)

print("payload ", payload)
print("encoded ", encoded)
print("received", received)
print("decoded ", result.bits)
