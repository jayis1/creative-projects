# Bubble sort program for RISC-V
# Sorts an array of 8 integers in ascending order

.text
.global _start

_start:
    la a0, array        # Array base address
    li a1, 8            # Array length
    
    jal ra, bubble_sort
    
    # Store sorted array starting at 0x20010200
    li t0, 0x20010200
    la t1, array
    li t2, 8
    
store_loop:
    lw t3, 0(t1)
    sw t3, 0(t0)
    addi t0, t0, 4
    addi t1, t1, 4
    addi t2, t2, -1
    bne t2, x0, store_loop
    
    ecall

# bubble_sort(a0: base, a1: n)
bubble_sort:
    addi sp, sp, -12
    sw ra, 8(sp)
    sw s0, 4(sp)
    sw s1, 0(sp)
    
    mv s0, a0           # s0 = base
    addi s1, a1, -1     # s1 = n - 1
    
outer_loop:
    bge x0, s1, sort_done
    li t0, 0             # swapped = false
    mv t1, x0            # i = 0
    
inner_loop:
    bge t1, s1, check_swap
    # Load arr[i] and arr[i+1]
    slli t2, t1, 2
    add t2, t2, s0       # addr = base + i*4
    lw t3, 0(t2)         # arr[i]
    lw t4, 4(t2)         # arr[i+1]
    
    bge t3, t4, no_swap  # if arr[i] > arr[i+1], swap
    
    sw t4, 0(t2)          # arr[i] = arr[i+1]
    sw t3, 4(t2)          # arr[i+1] = arr[i]
    li t0, 1              # swapped = true
    
no_swap:
    addi t1, t1, 1       # i++
    j inner_loop
    
check_swap:
    addi s1, s1, -1      # n--
    bne t0, x0, outer_loop  # if swapped, continue
    
sort_done:
    lw ra, 8(sp)
    lw s0, 4(sp)
    lw s1, 0(sp)
    addi sp, sp, 12
    jalr x0, ra, 0

.data
array:
    .word 64, 25, 12, 22, 11, 95, 3, 48