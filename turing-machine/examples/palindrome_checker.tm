# Palindrome checker: accepts iff the tape is a binary palindrome
blank: _
start: s0
halt:  accept reject

# Start: read leftmost symbol
s0  0 -> _ R m0
s0  1 -> _ R m1
s0  _ -> _ S accept

# Move right to find the last non-blank
m0  0 -> 0 R m0
m0  1 -> 1 R m0
m0  _ -> _ L c0
m1  0 -> 0 R m1
m1  1 -> 1 R m1
m1  _ -> _ L c1

# Compare last symbol with remembered symbol
c0  0 -> _ L back
c0  1 -> 1 S reject
c0  _ -> _ S accept
c1  1 -> _ L back
c1  0 -> 0 S reject
c1  _ -> _ S accept

# Go back left to start
back  0 -> 0 L back
back  1 -> 1 L back
back  _ -> _ R s0