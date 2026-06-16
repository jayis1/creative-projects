# Counter program — counts from 0 to 9 and stores results
# Demonstrates: loops, arithmetic, memory operations

.text
.global _start

_start:
    # Initialize
    li t0, 0          # counter = 0
    li t1, 10         # limit = 10
    lui t2, 0x20010   # data address base = 0x20010000

count_loop:
    # Store counter value
    slli t3, t0, 2    # t3 = counter * 4 (word offset)
    add t3, t2, t3    # t3 = base + offset
    sw t0, 0(t3)      # store counter at address

    # Increment
    addi t0, t0, 1

    # Compare
    blt t0, t1, count_loop

    # Store final count
    li t3, 0x20010000
    sw t0, 0(t3)

    # Halt
    ecall