# Factorial computation — computes 10! using iterative approach
# Demonstrates: multiplication (RV32M), loops, function calls

.text
.global _start

_start:
    # Compute 10!
    li a0, 10
    jal ra, factorial

    # Store result at 0x20010000
    lui t0, 0x20010
    sw a0, 0(t0)

    # Halt
    ecall

# factorial(n) — computes n! iteratively
# a0: n (input/output)
factorial:
    addi sp, sp, -16
    sw ra, 12(sp)
    sw s0, 8(sp)
    sw s1, 4(sp)

    mv s0, a0         # s0 = n
    li s1, 1           # s1 = result = 1

    # If n <= 1, return 1
    li t0, 1
    ble s0, t0, fact_done

fact_loop:
    mul s1, s1, s0     # result *= n
    addi s0, s0, -1    # n--
    bgt s0, t0, fact_loop

fact_done:
    mv a0, s1          # return result

    lw ra, 12(sp)
    lw s0, 8(sp)
    lw s1, 4(sp)
    addi sp, sp, 16
    jalr x0, ra, 0