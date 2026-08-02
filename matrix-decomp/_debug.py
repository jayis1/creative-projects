import sys; sys.path.insert(0, '.')
from matrix_decomp.svd import pseudo_inverse, svd
A = [[1, 1]]
U, S, Vt = svd(A)
print('U shape', len(U.data), 'x', len(U.data[0]))
print('S', S)
print('Vt shape', len(Vt.data), 'x', len(Vt.data[0]))
P = pseudo_inverse(A)
print('P shape', len(P.data), 'x', len(P.data[0]))
print('P', P.data)