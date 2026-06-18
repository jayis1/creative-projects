# Binary decrementer: subtracts 1 from a binary number (MSB-first)
blank: _
start: s0
halt:  halt

# Scan right past all bits to the blank, then step left
s0  0 -> 0 R s0
s0  1 -> 1 R s0
s0  _ -> _ L sub

# Subtract 1 with borrow propagation
sub 1 -> 0 S halt
sub 0 -> 1 L sub
sub _ -> _ R halt