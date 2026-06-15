from cryptanalysis_toolkit.ciphers.columnar import ColumnarTranspositionCipher

# Test with KEY = 'ZEBRA'
cipher = ColumnarTranspositionCipher(key='ZEBRA')
print('Key order:', cipher._key_order)
pt = 'WEAREDISCOVEREDFLEEATONCE'
ct = cipher.encrypt(pt)
print(f'Encrypted: {ct}')
dec = cipher.decrypt(ct)
print(f'Decrypted: {dec}')
print(f'Match: {dec == pt}')
# Test with shorter text
ct2 = cipher.encrypt('HELLO')
print(f'HELLO encrypted: {ct2}')
dec2 = cipher.decrypt(ct2)
print(f'Decrypted: {dec2}')
print(f'Match: {dec2.startswith("HELLO")}')