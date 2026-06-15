"""Quick start examples for the Cryptanalysis Toolkit."""

from cryptanalysis_toolkit import (
    CaesarCipher, VigenereCipher, SubstitutionCipher, XORCipher,
    EnigmaCipher, ROT13Cipher, AtbashCipher, HillCipher,
    FrequencyAnalyzer, IndexOfCoincidence, KasiskiExaminer,
    CipherBreaker, CipherPipeline, analyze_text,
)


def example_basic_ciphers():
    """Demonstrate basic cipher operations."""
    print("=" * 60)
    print("BASIC CIPHER OPERATIONS")
    print("=" * 60)

    # Caesar cipher
    caesar = CaesarCipher(shift=3)
    ct = caesar.encrypt("HELLO WORLD")
    pt = caesar.decrypt(ct)
    print(f"\nCaesar (shift=3): 'HELLO WORLD' → '{ct}' → '{pt}'")

    # Vigenère cipher
    vig = VigenereCipher(keyword="SECRET")
    ct = vig.encrypt("ATTACK AT DAWN")
    pt = vig.decrypt(ct)
    print(f"Vigenère (key=SECRET): 'ATTACK AT DAWN' → '{ct}' → '{pt}'")

    # ROT13
    rot13 = ROT13Cipher()
    ct = rot13.encrypt("Hello World")
    pt = rot13.decrypt(ct)
    print(f"ROT13: 'Hello World' → '{ct}' → '{pt}'")

    # Atbash
    atbash = AtbashCipher()
    ct = atbash.encrypt("HELLO")
    pt = atbash.decrypt(ct)
    print(f"Atbash: 'HELLO' → '{ct}' → '{pt}'")

    # Hill cipher (3x3 matrix)
    hill = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
    ct = hill.encrypt("ACT")
    pt = hill.decrypt(ct)
    print(f"Hill (3×3): 'ACT' → '{ct}' → '{pt}'")


def example_analysis():
    """Demonstrate analysis tools."""
    print("\n" + "=" * 60)
    print("ANALYSIS TOOLS")
    print("=" * 60)

    # Encrypt a known message with Vigenère
    vig = VigenereCipher(keyword="CIPHER")
    original = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
    ciphertext = vig.encrypt(original)
    print(f"\nOriginal:  {original}")
    print(f"Encrypted: {ciphertext}")

    # Frequency analysis
    freq = FrequencyAnalyzer()
    report = freq.frequency_report(ciphertext, top_n=5)
    print(f"\n{report}")

    # Index of Coincidence
    ic = IndexOfCoincidence()
    ic_value = ic.calculate(ciphertext)
    print(f"IC: {ic_value:.4f} (English≈0.0667, random≈0.0385)")

    # Friedman test
    friedman = ic.friedman_test(ciphertext)
    print(f"Friedman estimated key length: {friedman:.1f}")


def example_breaking():
    """Demonstrate automatic cipher breaking."""
    print("\n" + "=" * 60)
    print("AUTOMATIC CIPHER BREAKING")
    print("=" * 60)

    # Break Caesar
    caesar = CaesarCipher(shift=17)
    original = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
    ciphertext = caesar.encrypt(original)
    print(f"\nCaesar ciphertext: {ciphertext}")

    breaker = CipherBreaker()
    results = breaker.break_caesar(ciphertext, top_n=3)
    print("Top 3 Caesar breaks:")
    for r in results:
        marker = " ← CORRECT" if r["shift"] == 17 else ""
        print(f"  Shift {r['shift']:2d}: {r['plaintext'][:50]}... (corr={r['correlation']:.4f}){marker}")

    # Break Vigenère
    vig = VigenereCipher(keyword="KEY")
    ciphertext = vig.encrypt("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG AND THE DOG RAN AWAY")
    print(f"\nVigenère ciphertext (key='KEY'): {ciphertext[:60]}...")
    results = breaker.break_vigenere(ciphertext, max_key_length=10, top_n=3)
    print("Top 3 Vigenère breaks:")
    for r in results:
        print(f"  Key='{r['key']}' (len={r['key_length']}): {r['plaintext'][:50]}... (score={r['score']:.4f})")


def example_pipeline():
    """Demonstrate pipeline (chained cipher operations)."""
    print("\n" + "=" * 60)
    print("PIPELINE (CHAINED OPERATIONS)")
    print("=" * 60)

    pipeline = CipherPipeline([
        {"cipher": "caesar", "action": "encrypt", "params": {"shift": 7}},
        {"cipher": "vigenere", "action": "encrypt", "params": {"key": "SECRET"}},
    ])
    text = "ATTACK AT DAWN"
    encrypted = pipeline.run(text)
    print(f"\nDouble encryption (Caesar+Vigenère): '{text}' → '{encrypted}'")

    # Reverse pipeline
    reverse_pipeline = CipherPipeline([
        {"cipher": "vigenere", "action": "decrypt", "params": {"key": "SECRET"}},
        {"cipher": "caesar", "action": "decrypt", "params": {"shift": 7}},
    ])
    decrypted = reverse_pipeline.run(encrypted)
    print(f"Double decryption: '{encrypted}' → '{decrypted}'")


def example_structured_analysis():
    """Demonstrate structured JSON analysis output."""
    print("\n" + "=" * 60)
    print("STRUCTURED ANALYSIS (JSON)")
    print("=" * 60)

    import json
    vig = VigenereCipher(keyword="CODE")
    ciphertext = vig.encrypt("MEET ME AT THE USUAL PLACE AT EIGHT OCLOCK")
    result = analyze_text(ciphertext)
    print(f"\nAnalysis of Vigenère ciphertext (key='CODE'):")
    print(json.dumps(result, indent=2))


def example_enigma():
    """Demonstrate Enigma machine simulation."""
    print("\n" + "=" * 60)
    print("ENIGMA MACHINE")
    print("=" * 60)

    enigma = EnigmaCipher(
        rotor_order=[2, 4, 1],
        initial_positions=[0, 0, 0],
        plugboard_pairs=[("A", "B"), ("S", "Z"), ("U", "Y")],
    )
    plaintext = "SECRETMESSAGE"
    ciphertext = enigma.encrypt(plaintext)
    decrypted = enigma.decrypt(ciphertext)
    print(f"\nRotors: II-IV-I, Plugboard: AB SZ UY")
    print(f"Plaintext:  {plaintext}")
    print(f"Ciphertext: {ciphertext}")
    print(f"Decrypted:  {decrypted}")


if __name__ == "__main__":
    example_basic_ciphers()
    example_analysis()
    example_breaking()
    example_pipeline()
    example_structured_analysis()
    example_enigma()
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)