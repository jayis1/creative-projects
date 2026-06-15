from cryptanalysis_toolkit.ciphers.xor import XORCipher

cipher = XORCipher(key=b"\x2a")
plaintext = b"the quick brown fox jumps over the lazy dog and this is a test"
ct = cipher.encrypt(plaintext)
print(f"Ciphertext bytes: {ct[:30]}")
print(f"Ciphertext hex: {ct[:30].hex()}")

# Try key 0
cipher0 = XORCipher(key=b"\x00")
ct0 = cipher0.encrypt(plaintext)
print(f"\nKey 0 decrypt: {ct0}")

# Try key 42
ct42 = cipher.decrypt(ct)
print(f"Key 42 decrypt: {ct42}")

# Check the scores
results = XORCipher.single_byte_xor_break(ct)
for r in results[:5]:
    print(f"Key {r['key']}: score={r['score']:.4f}, plaintext={r['plaintext'][:30]}")