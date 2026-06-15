from cryptanalysis_toolkit import IndexOfCoincidence, CaesarCipher

ic = IndexOfCoincidence()

# A long English text should have IC ~0.067
plain = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOGTHERAININSPAINFALLSMAINLYINTHEPLAIN" * 5
print(f"Plain text IC: {ic.calculate(plain):.4f}")

# Caesar shifted should have same IC
shifted = CaesarCipher(shift=5).encrypt(plain)
print(f"Caesar shifted IC: {ic.calculate(shifted):.4f}")

# With spaces
plain_with_spaces = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG THE RAIN IN SPAIN FALLS MAINLY IN THE PLAIN " * 5
print(f"Plain with spaces IC: {ic.calculate(plain_with_spaces):.4f}")

shifted_with_spaces = CaesarCipher(shift=5).encrypt(plain_with_spaces)
print(f"Caesar shifted with spaces IC: {ic.calculate(shifted_with_spaces):.4f}")