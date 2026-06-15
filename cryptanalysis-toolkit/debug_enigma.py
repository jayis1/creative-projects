from cryptanalysis_toolkit.ciphers.enigma import EnigmaCipher

# Test: default rotors [1,2,3], positions [0,0,0] — should work fine
e1 = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[0, 0, 0])
ct = e1.encrypt("HELLO")
e2 = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[0, 0, 0])
pt = e2.decrypt(ct)
print(f"Roundtrip: {pt}")  # Should be HELLO

# Test: with ring settings
e3 = EnigmaCipher(rotor_order=[1, 2, 3], ring_settings=[1, 2, 3], initial_positions=[0, 0, 0])
ct3 = e3.encrypt("HELLO")
e4 = EnigmaCipher(rotor_order=[1, 2, 3], ring_settings=[1, 2, 3], initial_positions=[0, 0, 0])
pt3 = e4.decrypt(ct3)
print(f"Roundtrip with ring settings: {pt3}")  # Should be HELLO

# Test: different rotor order
e5 = EnigmaCipher(rotor_order=[3, 1, 2], initial_positions=[5, 10, 15])
ct5 = e5.encrypt("TESTMESSAGE")
e6 = EnigmaCipher(rotor_order=[3, 1, 2], initial_positions=[5, 10, 15])
pt6 = e6.decrypt(ct5)
print(f"Roundtrip different rotors: {pt6}")  # Should be TESTMESSAGE