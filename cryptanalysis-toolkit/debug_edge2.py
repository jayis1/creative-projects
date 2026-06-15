from cryptanalysis_toolkit.ciphers.autokey import AutokeyCipher

# Test autokey with case preservation
cipher = AutokeyCipher(keyword="KEY")
ct = cipher.encrypt("Hello World")
pt = cipher.decrypt(ct)
print(f"Autokey roundtrip: '{ct}' -> '{pt}'")
print(f"Match: {pt == 'Hello World'}")

# Test with long text
long_text = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
ct2 = cipher.encrypt(long_text)
pt2 = cipher.decrypt(ct2)
print(f"Autokey long roundtrip: {pt2 == long_text}")

# Test Beaufort roundtrip
from cryptanalysis_toolkit.ciphers.beaufort import BeaufortCipher
bc = BeaufortCipher(keyword="FORT")
ct3 = bc.encrypt("HELLO")
pt3 = bc.decrypt(ct3)
print(f"Beaufort roundtrip: encrypt={ct3}, decrypt={pt3}, match={pt3 == 'HELLO'}")

# Test Porta roundtrip  
from cryptanalysis_toolkit.ciphers.porta import PortaCipher
pc = PortaCipher(keyword="KEY")
ct4 = pc.encrypt("HELLO")
pt4 = pc.decrypt(ct4)
print(f"Porta roundtrip: encrypt={ct4}, decrypt={pt4}, match={pt4 == 'HELLO'}")

# Test rail fence with empty string
from cryptanalysis_toolkit.ciphers.railfence import RailFenceCipher
rf = RailFenceCipher(rails=3)
ct5 = rf.encrypt("")
print(f"Rail fence empty: '{ct5}'")
pt5 = rf.decrypt("")
print(f"Rail fence decrypt empty: '{pt5}'")

# Test rail fence with single char
ct6 = rf.encrypt("A")
pt6 = rf.decrypt(ct6)
print(f"Rail fence single: encrypt={ct6}, decrypt={pt6}, match={pt6 == 'A'}")