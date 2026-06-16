# Fibonacci sequence program for RISC-V
# Computes fib(10) and stores result at address 0x20010000
# a0 = fib(10)

.text
.global _start

_start:
    li a0, 10          # n = 10
    jal ra, fib         # call fib(n)
    # Store result
    li t0, 0x20010000
    sw a0, 0(t0)        # store result
    li a7, 10           # ecall exit (halt simulation)
    ecall

# fib(n) — computes nth Fibonacci number
# a0: n (input/output)
fib:
    # Prologue
    addi sp, sp, -16
    sw ra, 12(sp)
    sw s0, 8(sp)
    sw s1, 4(sp)
    
    mv s0, a0           # s0 = n
    li s1, 0            # s1 = fib(0) = 0
    li a0, 1            # a0 = fib(1) = 1
    
    # If n <= 1, return n
    bge s1, s0, fib_done
    
fib_loop:
    addi sp, sp, -4
    sw a0, 0(sp)        # push current fib
    add a0, s1, a0      # a0 = next fib
    lw s1, 0(sp)        # s1 = prev fib
    addi sp, sp, 4
    addi s0, s0, -1     # n--
    bgt s0, x0, fib_loop
    
fib_done:
    # Epilogue
    lw ra, 12(sp)
    lw s0, 8(sp)
    lw s1, 4(sp)
    addi sp, sp, 16
    jalr x0, ra, 0