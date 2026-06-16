# String printing using UART MMIO
# Demonstrates: loops, character output, pseudo-instructions

.text
.global _start

_start:
    # Load UART base address
    lui t0, 0x10000

    # String data pointer
    la t1, hello_str

print_loop:
    # Load byte from string
    lb t2, 0(t1)

    # Check for null terminator
    beqz t2, done

    # Write character to UART
    sw t2, 0(t0)

    # Advance pointer
    addi t1, t1, 1

    # Loop back
    j print_loop

done:
    # Write newline
    li t2, 0x0A
    sw t2, 0(t0)

    # Halt
    ecall

hello_str:
    .string "Hello, RISC-V World!"