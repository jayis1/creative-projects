# Memory test — writes and reads patterns to verify memory system
# Writes values 0-15 to addresses 0x20010000-0x2001003C
# Then reads them back and compares

.text
.global _start

_start:
    li t0, 0x20010000   # Base address
    li t1, 16           # Count
    li t2, 0            # Index / value
    
write_loop:
    sw t2, 0(t0)        # Store value at address
    addi t0, t0, 4      # Next address
    addi t2, t2, 1      # Next value
    bne t2, t1, write_loop
    
    # Read back
    li t0, 0x20010000   # Reset base address
    li t2, 0            # Index
    li t3, 0            # Error count
    
read_loop:
    lw t4, 0(t0)        # Read value
    bne t4, t2, error   # Compare with expected
    addi t0, t0, 4      # Next address
    addi t2, t2, 1      # Next expected value
    bne t2, t1, read_loop
    
    # Success: t3 should be 0
    sw t3, 0x100(t0)    # Store error count
    j end
    
error:
    addi t3, t3, 1      # Increment error count
    addi t0, t0, 4
    addi t2, t2, 1
    bne t2, t1, read_loop
    
end:
    # Store final result at 0x20010400
    li t5, 0x20010400
    sw t3, 0(t5)
    ecall