from cryptanalysis_toolkit.ciphers.playfair import PlayfairCipher

# Test: Playfair with text containing XX
cipher = PlayfairCipher(keyword="KEYWORD")
# "XRAY" -> X,R,A,Y - no repeated letters, should work
ct = cipher.encrypt("XRAY")
pt = cipher.decrypt(ct)
print(f"XRAY roundtrip: {pt}")

# Test: repeated letters where one is X
# "FOOD" -> F,O,O,D -> F,O,X,D and O stays alone? 
ct2 = cipher.encrypt("FOOD")
pt2 = cipher.decrypt(ct2)
print(f"FOOD encrypt: {ct2}, decrypt: {pt2}")

# Test: "XX" as input - repeated X's
ct3 = cipher.encrypt("XX")
pt3 = cipher.decrypt(ct3)
print(f"XX encrypt: {ct3}, decrypt: {pt3}")

# Edge case: single letter
ct4 = cipher.encrypt("A")
pt4 = cipher.decrypt(ct4)
print(f"A encrypt: {ct4}, decrypt: {pt4}")

# Edge case: empty string
ct5 = cipher.encrypt("")
print(f"Empty encrypt: '{ct5}'")

# Test columnar transposition with non-alpha chars
from cryptanalysis_toolkit.ciphers.columnar import ColumnarTranspositionCipher
c2 = ColumnarTranspositionCipher(key="KEY")
ct6 = c2.encrypt("Hello World 123")
print(f"Columnar non-alpha: {ct6}")