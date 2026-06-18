# Binary NOT: inverts all bits of a binary number
# 1010 -> 0101
blank: _
start: s0
halt: [halt]

s0  0 -> 1 R s0
s0  1 -> 0 R s0
s0  _ -> _ L s1
s1  0 -> 0 L s1
s1  1 -> 1 L s1
s1  _ -> _ R halt