# Unary addition: 111 + 11 = 11111
# Input format: 1^a _ 1^b  (blocks of 1s separated by a blank)
blank: _
start: s0
halt:  halt

# Walk right past first block of 1s
s0  1 -> 1 R s0
# Hit separator blank -> replace with 1
s0  _ -> 1 R s1

# Walk right past second block
s1  1 -> 1 R s1
# Hit end blank -> step left
s1  _ -> _ L s2

# Erase the last 1 to compensate for the separator we filled
s2  1 -> _ S halt