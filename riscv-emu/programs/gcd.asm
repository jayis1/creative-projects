# GCD (Greatest Common Divisor) using Euclidean algorithm
# Computes GCD(48, 18) = 6
# Demonstrates: division (RV32M), loops, register conventions

.text
.global _start

_start:
    li a0, 48
    li a1, 18
    jal ra, gcd

    # Store result at 0x20010000
    lui t0, 0x20010
    sw a0, 0(t0)

    # Halt
    ecall

# gcd(a, b) — computes GCD using Euclidean algorithm
# a0: first number (input), result (output)
# a1: second number (input)
gcd:
    addi sp, sp, -12
    sw ra, 8(sp)
    sw s0, 4(sp)
    sw s1, 0(sp)

    mv s0, a0         # s0 = a
    mv s1, a1         # s1 = b

gcd_loop:
    beqz s1, gcd_done  # if b == 0, done
    rem s0, s0, s1     # a = a % b (uses RV32M REM)
    mv a0, s0          # swap: a = old b
    mv s0, s1          # swap
    mv s1, a0          # b = old a % b
    j gcd_loop

gcd_done:
    mv a0, s0          # return a (the GCD)

    lw ra, 8(sp)
    lw s0, 4(sp)
    lw s1, 0(sp)
    addi sp, sp, 12
    jalr x0, ra, 0