# RISC-V RV32I Emulator

A full-featured RISC-V RV32I CPU emulator with assembler, disassembler, interactive debugger, execution profiler, and trace recorder — written in pure Python.

## Features

- **Complete RV32I base instruction set** — 40 instructions including LUI, AUIPC, JAL, JALR, all branches, loads, stores, and ALU ops
- **RV32M extension** — MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU (with proper division-by-zero and overflow handling)
- **Zicsr extension** — CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI with standard M-mode CSRs
- **Two-pass assembler** — labels, `.word`/`.string`/`.byte` directives, 15+ pseudo-instructions (LI, LA, MV, NOP, NOT, NEG, J, RET, CALL, BGT, BLE, BGTU, BLEU, BEQZ, BNEZ, etc.)
- **Disassembler** — converts binary instructions back to human-readable assembly with named registers
- **ELF32 loader** — load raw binaries, flat assembled binaries, and ELF32 little-endian executables
- **Interactive debugger** — breakpoints, watchpoints, single-step, register/memory inspection/modification, disassembly, continue, quit
- **UART MMIO** — QEMU-virt compatible UART at 0x10000000 for character output
- **Execution profiler** — instruction frequency, hot addresses, runtime statistics
- **Trace recorder** — ring buffer, address filtering, register change tracking, statistics
- **Proper trap handling** — ECALL/EBREAK, misaligned access, privilege mode transitions, mtvec vectoring
- **Division-by-zero** — DIV/DIVU return -1/0xFFFFFFFF, REM/REMU return dividend per spec

## Architecture

```
riscv_emu/
├── __init__.py       # Package exports
├── cpu.py            # CPU core (RV32I + RV32M + Zicsr)
├── memory.py         # Sparse memory with regions, permissions, MMIO
├── csrs.py           # Control and Status Register file
├── assembler.py      # Two-pass assembler with pseudo-instructions
├── disassembler.py   # Instruction disassembler
├── loader.py         # Binary and ELF32 loader
├── debugger.py       # Interactive GDB-like debugger
├── profiler.py       # Execution profiler
├── tracer.py         # Trace recorder
└── cli.py            # Command-line interface
```

## Installation

```bash
pip install -e .
```

## Usage

### Assemble and run a program

```bash
# Assemble source code
riscv-emu asm programs/fibonacci.asm -o fibonacci.bin

# Run the assembled binary
riscv-emu run fibonacci.bin --trace

# Run with profiling
riscv-emu run fibonacci.bin --profile

# Show UART output
riscv-emu run programs/hello_uart.bin --uart
```

### Interactive debugging

```bash
riscv-emu debug fibonacci.bin
(riscv-dbg) break 0x20000010
(riscv-dbg) continue
(riscv-dbg) step 5
(riscv-dbg) regs
(riscv-dbg) mem 0x20010000 16
(riscv-dbg) disassemble
```

### Disassemble a binary

```bash
riscv-emu dis fibonacci.bin --count 50
```

### Assemble with disassembly output

```bash
riscv-emu asm programs/fibonacci.asm --disassemble
```

## Python API

```python
from riscv_emu import CPU, Memory, MemoryRegion, Assembler, disassemble

# Create memory and CPU
mem = Memory([MemoryRegion(0x20000000, 0x100000, "rwx")])
mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
mem.add_region(MemoryRegion(0x10000000, 8, "rw"))  # UART MMIO

# Assemble and load
asm = Assembler(base_addr=0x20000000)
code, labels = asm.assemble("""
    li a0, 10
    jal ra, fib
    ecall
    
fib:
    addi sp, sp, -16
    sw ra, 12(sp)
    ...
""", base_addr=0x20000000)
mem.write_bytes(0x20000000, bytes(code))

# Run
cpu = CPU(memory=mem, pc=0x20000000)
cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)
count = cpu.run(max_instructions=10000)
print(f"Executed {count} instructions, a0 = {cpu.get_reg(10)}")
print(f"UART output: {cpu.uart_output}")

# Disassemble
insn = mem.read_word(0x20000000)
print(disassemble(insn, 0x20000000))
```

## Instruction Set

### RV32I Base (40 instructions)
LUI, AUIPC, JAL, JALR, BEQ, BNE, BLT, BGE, BLTU, BGEU, LB, LH, LW, LBU, LHU, SB, SH, SW, ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI, ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND, FENCE, ECALL, EBREAK

### RV32M Extension (8 instructions)
MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU

### Zicsr Extension (6 instructions)
CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI

### Pseudo-Instructions
NOP, MV, NOT, NEG, LI, LA, J, RET, CALL, BEQZ, BNEZ, BGT, BLE, BGTU, BLEU

## Supported CSRs

| CSR      | Address  | Description              |
|----------|----------|--------------------------|
| mstatus  | 0x300    | Machine status           |
| misa     | 0x301    | ISA and extensions        |
| mie      | 0x304    | Machine interrupt enable |
| mtvec    | 0x305    | Machine trap vector      |
| mscratch | 0x340    | Machine scratch          |
| mepc     | 0x341    | Machine exception PC     |
| mcause   | 0x342    | Machine cause            |
| mtval    | 0x343    | Machine trap value       |
| mip      | 0x344    | Machine interrupt pending|
| cycle    | 0xC00    | Cycle counter            |
| instret  | 0xC02    | Instructions retired     |

## Memory Map

| Region           | Size    | Permissions | Description       |
|------------------|---------|-------------|-------------------|
| 0x20000000       | 1 MB    | RWX         | Code/data        |
| 0x7F000000       | 16 MB   | RW          | Stack            |
| 0x10000000       | 8 B     | RW          | UART MMIO        |

## Test Suite

```bash
pip install pytest
pytest tests/ -v
```

101 tests covering: memory operations, CSR read/write, assembler encoding, CPU instruction execution, branch behavior, load/store, JAL/JALR, ECALL/EBREAK, UART MMIO, RV32M multiply/divide, and disassembly.

## Known Issues (Resolved)

See Phase 3 bug fixes in git history.