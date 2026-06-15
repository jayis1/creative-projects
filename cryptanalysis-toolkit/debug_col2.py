from cryptanalysis_toolkit.ciphers.columnar import ColumnarTranspositionCipher

# Test: columnar transposition roundtrip with various text lengths
c = ColumnarTranspositionCipher(key="KEY")

for text in ["A", "AB", "ABC", "ABCD", "ABCDE", "ABCDEF", "ABCDEFGHI"]:
    ct = c.encrypt(text)
    pt = c.decrypt(ct)
    match = pt.startswith(text.upper())
    print(f"Text: '{text}' ({len(text)} chars) -> Encrypt: '{ct}' -> Decrypt: '{pt}' -> Match: {match}")

# Test with key "ZEBRA"
c2 = ColumnarTranspositionCipher(key="ZEBRA")
for text in ["HELLO", "WORLD", "ATTACKATDAWN", "SHORT"]:
    ct = c2.encrypt(text)
    pt = c2.decrypt(ct)
    match = pt.startswith(text.upper())
    print(f"ZEBRA: '{text}' ({len(text)} chars) -> Encrypt: '{ct}' -> Decrypt: '{pt}' -> Match: {match}")