from rs_codec import rs_encode, rs_decode, calc_syndromes, encode, decode, decode_message, encode_message

# Test 1: Basic encode/decode, no errors
msg = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
nsym = 10
encoded = rs_encode(msg, nsym)
print('Encoded:', encoded)
synd = calc_syndromes(encoded, nsym)
print('Syndromes (should be all 0):', synd)
assert all(s == 0 for s in synd), "Encoding produced nonzero syndromes!"
print("Test 1 PASS: encoding produces valid codeword")

# Test 2: No errors -> decode returns same
decoded = rs_decode(encoded, nsym)
assert decoded == encoded, "Decode corrupted a valid codeword!"
print("Test 2 PASS: no-error decode works")

# Test 3: 2 errors
corrupted = list(encoded)
corrupted[3] ^= 42
corrupted[7] ^= 99
decoded = rs_decode(corrupted, nsym)
assert decoded == encoded, f"Failed to correct 2 errors!\n  Expected: {encoded}\n  Got:      {decoded}"
print("Test 3 PASS: corrected 2 errors")

# Test 4: Max errors (nsym//2 = 5)
corrupted = list(encoded)
positions = [0, 4, 8, 12, 16]
for p in positions:
    corrupted[p] ^= (p * 17 + 3) & 0xFF
decoded = rs_decode(corrupted, nsym)
assert decoded == encoded, f"Failed to correct 5 errors!\n  Expected: {encoded}\n  Got:      {decoded}"
print("Test 4 PASS: corrected 5 errors (maximum)")

# Test 5: Erasure correction
corrupted = list(encoded)
erasures = [2, 5, 11, 14, 17]
for p in erasures:
    corrupted[p] = 0  # erased
decoded = rs_decode(corrupted, nsym, erasures=erasures)
assert decoded == encoded, f"Failed to correct 5 erasures!\n  Expected: {encoded}\n  Got:      {decoded}"
print("Test 5 PASS: corrected 5 erasures")

# Test 6: byte API
data = b"Hello, Reed-Solomon!"
enc = encode_message(data, 10)
print(f"Original: {data}")
print(f"Encoded:  {enc.hex()}")
# Corrupt 3 bytes
corrupted = bytearray(enc)
corrupted[5] ^= 0xAA
corrupted[10] ^= 0x55
corrupted[15] ^= 0x42
dec = decode_message(bytes(corrupted), 10)
print(f"Decoded:  {dec}")
assert dec == data, f"Byte API failed!\n  Expected: {data}\n  Got:      {dec}"
print("Test 6 PASS: byte API works")

print("\nAll tests passed!")