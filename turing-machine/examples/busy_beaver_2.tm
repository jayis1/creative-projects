# Two-state busy beaver (BB(2))
# Writes 4 ones and halts after 6 steps.
blank: 0
start: A
halt: [HALT]

A  0 -> 1 R B
A  1 -> 1 L HALT
B  0 -> 1 L A
B  1 -> 1 R B