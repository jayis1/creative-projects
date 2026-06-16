# UART hello world — writes "Hello" to MMIO UART at 0x10000000
# Uses the store instruction to write characters one at a time

.text
.global _start

_start:
    # UART base address
    lui t0, 0x10000
    
    # Write 'H' (0x48)
    li t1, 0x48
    sw t1, 0(t0)
    
    # Write 'e' (0x65)
    li t1, 0x65
    sw t1, 0(t0)
    
    # Write 'l' (0x6C)
    li t1, 0x6C
    sw t1, 0(t0)
    
    # Write 'l' (0x6C)
    li t1, 0x6C
    sw t1, 0(t0)
    
    # Write 'o' (0x6F)
    li t1, 0x6F
    sw t1, 0(t0)
    
    # Write newline (0x0A)
    li t1, 0x0A
    sw t1, 0(t0)
    
    # Halt via ecall
    ecall