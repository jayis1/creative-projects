from quantum_sim.algorithms import deutsch_jozsa
r = deutsch_jozsa('constant', n=2)
print('Probabilities:', r.probabilities)
print('Counts:', r.counts)
# For DJ, qubit 0 (LSB) and qubit 1 should be 0; ancilla qubit 2 is random.
# In the bitstring format(i, '03b'), the leftmost char is qubit 2 (MSB).
# So input register 00 means indices where qubits 0,1 are 0:
#   index 0 = '000', index 4 = '100' (only qubit 2 is 1)
print('P(000)+P(100):', r.counts.get('000', 0)/r.shots + r.counts.get('100', 0)/r.shots)