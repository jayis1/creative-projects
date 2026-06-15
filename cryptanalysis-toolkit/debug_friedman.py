from cryptanalysis_toolkit.analysis.ic import IndexOfCoincidence
from cryptanalysis_toolkit.ciphers import VigenereCipher

ic = IndexOfCoincidence()

# Long Vigenère ciphertext with key "KEY" (length 3)
plain = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOGTHERAININSPAINFALLSMAINLYINTHEPLAIN" * 20
ct = VigenereCipher(keyword="SECRET").encrypt(plain)

ic_val = ic.calculate(ct)
n = len(''.join(c for c in ct if c.isalpha()))
print(f"IC: {ic_val:.6f}")
print(f"Text length (alpha): {n}")
print(f"Friedman estimate: {ic.friedman_test(ct):.2f}")

# Manual calculation
numerator = 0.0266 * n
denominator = ic_val * (n - 1) - 0.0279 * n + 0.0385
print(f"Numerator: {numerator:.4f}")
print(f"Denominator: {denominator:.4f}")
print(f"Manual result: {numerator/denominator:.2f}")

# What should the IC be for key length 3?
# Expected IC for Vigenere with key length k ≈ (1/k) * ( (n-k)/(n-1) * 0.0667 + (k-1)*n/(n-1) * 0.0385 )
# For large n: ≈ (1/k) * (0.0667 + (k-1) * 0.0385) = (0.0667 + (k-1)*0.0385) / k
# For k=3: (0.0667 + 2*0.0385)/3 = 0.1437/3 = 0.0479
print(f"Expected IC for k=3: {(0.0667 + 2*0.0385)/3:.4f}")