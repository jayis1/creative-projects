from cryptanalysis_toolkit.ciphers.columnar import ColumnarTranspositionCipher

c = ColumnarTranspositionCipher(key="KEY")
ct = c.encrypt("")
print(f"Empty encrypt: '{ct}'")
pt = c.decrypt("")
print(f"Empty decrypt: '{pt}'")