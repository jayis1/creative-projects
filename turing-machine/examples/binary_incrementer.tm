# Binary incrementer: adds 1 to a binary number (MSB-first)
blank: _
start: s0
halt:  halt

# Scan right past all bits to the blank, then step left
s0  0 -> 0 R s0
s0  1 -> 1 R s0
s0  _ -> _ L add

# Add 1 with carry propagation
add 0 -> 1 S halt
add 1 -> 0 L add
add _ -> 1 S halt