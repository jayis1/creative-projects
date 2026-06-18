# Unary multiplication: 1^a 0 1^b -> 1^(a*b)
# Multiplies two unary numbers separated by a blank.
# Example: 111 0 11 -> 111111  (3 * 2 = 6)
blank: _
start: s0
halt: [halt]

# This machine is complex; we use a marking approach.
# Phase 1: For each 1 in the first number, copy the second number to the end.
# Phase 2: Clean up intermediate markers.

s0  1 -> X R s1        # Mark a 1 in first number, go copy second
s0  0 -> _ R clean1    # All first-number 1s processed, clean up
# s1: skip to separator
s1  1 -> 1 R s1
s1  0 -> 0 R s2        # Found separator, go to second number
# s2: for each 1 in second number, write a 1 at the end
s2  1 -> Y R s2        # Mark a 1, continue to end
s2  0 -> 0 R s3        # End of second number, go write
# s3: skip past existing output 1s
s3  1 -> 1 R s3
s3  0 -> 1 R s4        # Write a 1, then go back
# s4: go back to find the Y we marked
s4  1 -> 1 L s4
s4  0 -> 0 L s4
s4  Y -> 1 R s2        # Restore Y to 1, go process next
s4  0 -> 0 L s4
# When second number is exhausted (all Y), restore and go back
s2  Y -> Y R s2
# After all Ys restored, go back to first number
# Actually s2 hits 0 when all 1s in second number are marked as Y
# We need: when s2 sees 0 (no more 1s), restore Ys and go back
# Let's handle: s2 sees 0 -> restore phase
s2  0 -> 0 L restore
# restore: change Ys back to 1s, moving left
restore  Y -> 1 L restore
restore  0 -> 0 L restore
restore  1 -> 1 L restore
restore  X -> X R s0   # Back to first number, next iteration
# clean1: remove separator and second number, keep only output
clean1  1 -> 0 R clean2
clean1  0 -> 0 R clean1
clean1  Y -> 0 R clean1
clean2  1 -> 0 R clean2
clean2  0 -> _ S halt  # Done: output 1s are to the right