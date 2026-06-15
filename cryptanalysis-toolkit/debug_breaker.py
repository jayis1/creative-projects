# Test breaker edge cases
from cryptanalysis_toolkit import CipherBreaker
from cryptanalysis_toolkit.ciphers import CaesarCipher, AffineCipher, VigenereCipher

breaker = CipherBreaker()

# Test: break very short Caesar ciphertext
short_ct = CaesarCipher(shift=3).encrypt("HI")
result = breaker.break_caesar(short_ct)
print(f"Short Caesar break top shift: {result[0]['shift']}, text: {result[0]['plaintext'][:20]}")

# Test: break with empty ciphertext
try:
    result2 = breaker.break_caesar("")
    print(f"Empty Caesar break: {result2}")
except Exception as e:
    print(f"Empty Caesar break error: {type(e).__name__}: {e}")

# Test: break with non-alpha only
try:
    result3 = breaker.break_caesar("!!! 123")
    print(f"Non-alpha Caesar break: {result3}")
except Exception as e:
    print(f"Non-alpha Caesar break error: {type(e).__name__}: {e}")

# Test: Vigenere with very short ciphertext
short_vig = VigenereCipher(keyword="KEY").encrypt("AB")
result4 = breaker.break_vigenere(short_vig)
print(f"Short Vigenere break results: {len(result4)}")

# Test: identify cipher type
from cryptanalysis_toolkit.ciphers import SubstitutionCipher
plain = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
caesar_ct = CaesarCipher(shift=5).encrypt(plain)
print(f"Caesar IC type: {breaker.identify_cipher_type(caesar_ct)}")

vig_ct = VigenereCipher(keyword="SECRET").encrypt(plain)
print(f"Vigenere IC type: {breaker.identify_cipher_type(vig_ct)}")