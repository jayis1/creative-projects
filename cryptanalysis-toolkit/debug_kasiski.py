from cryptanalysis_toolkit.analysis.kasiski import KasiskiExaminer
import time

k = KasiskiExaminer()

# Test with a known Vigenère ciphertext
from cryptanalysis_toolkit.ciphers import VigenereCipher
plain = "ATTACKATDAWNATTACKATDAWNATTACKATDAWNATTACKATDAWN" * 10
ct = VigenereCipher(keyword="KEY").encrypt(plain)

start = time.time()
result = k.find_repeated_sequences(ct)
elapsed = time.time() - start
print(f"Kasiski sequences found: {len(result)} in {elapsed:.3f}s")
print(f"First 5: {list(result.items())[:5]}")

# Performance test with longer text
long_ct = VigenereCipher(keyword="SECRETKEY").encrypt(plain * 10)
start = time.time()
result2 = k.find_repeated_sequences(long_ct)
elapsed2 = time.time() - start
print(f"Long Kasiski: {len(result2)} sequences in {elapsed2:.3f}s")

# Test Friedman test
from cryptanalysis_toolkit.analysis.ic import IndexOfCoincidence
ic_calc = IndexOfCoincidence()
friedman = ic_calc.friedman_test(ct)
print(f"Friedman test key length estimate: {friedman:.2f}")