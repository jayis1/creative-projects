# RISC-V RV32I Emulator

A full-featured RISC-V RV32I CPU emulator with assembler, interactive debugger, execution profiler, and trace recorder — written in pure Python.

## Features

- **Complete RV32I base instruction set** — all 40 instructions: LUI, AUIPC, JAL, JALR, branches (BEQ/BNE/BLT/BGE/BLTU/BGEU), loads (LB/LH/LW/LBU/LHU), stores (SB/SH/SW), I-type ALU (ADDI/SLTI/SLTIU/XORI/ORI/ANDI/SLLI/SRLI/SRAI), R-type ALU (ADD/SUB/SLL/SLT/SLTU/XOR/SRL/SRA/OR/AND), FENCE, ECALL, EBREAK
- **Zicsr extension** — CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI with full CSR file (mstatus, misa, mepc, mcause, mtvec, mip, mie, mscratch, cycle, instret)
- **Two-pass assembler** — labels, forward references, directives (`.word`/`.half`/`.byte`/`.string`/`.align`/`.org`/`.text`/`.data`), 15+ pseudo-instructions (LI/LA/MV/NOT/NEG/J/RET/CALL/BGT/BLE/BGTU/BLEU/BEQZ/BNEZ/BGEZ/BLTZ/NOP)
- **Interactive debugger** — GDB-like command interface with breakpoints, watchpoints, single-step, register/memory inspection, disassembly, undo, tracing, and profiling
- **ELF32 loader** — parses ELF headers and loads PT_LOAD segments with proper permissions
- **Sparse memory system** — region-based with configurable permissions, alignment checking, and MMIO callback support
- **Trap handling** — full exception/interrupt pipeline with mepc/mcause/mtval save and mtvec dispatch
- **Execution profiler** — instruction frequency and hot-address analysis
- **Trace recorder** — per-instruction state capture with address filtering and ring-buffer

## How It Works

### CPU Core (`cpu.py`)

The CPU implements a fetch-decode-execute cycle on the RV32I ISA. Each instruction is decoded from its 32-bit encoding by examining the opcode, funct3, and funct7 fields. The register file has 32 entries with x0 hardwired to zero. Traps (exceptions) update the CSR file and redirect execution to the trap vector (mtvec).

### Memory (`memory.py`)

Memory is organized as a list of non-overlapping regions, each with base address, size, and permissions (r/w/x). Alignment is enforced for half-word and word accesses. MMIO is supported via read/write callbacks on any region.

### Assembler (`assembler.py`)

A two-pass assembler: Pass 1 collects labels and computes addresses while expanding pseudo-instructions. Pass 2 resolves label references and encodes all instructions to 32-bit machine code.

### CSR File (`csrs.py`)

Implements the Zicsr extension with machine-mode CSRs. Read-only CSRs (mvendorid, marchid, mimpid, mhartid) are protected. Atomic read-modify-write operations (CSRRS/CSRRC) are supported.

### Debugger (`debugger.py`)

An interactive REPL with commands for stepping, continuing, setting breakpoints/watchpoints, inspecting registers and memory, disassembling, and profiling. Supports undo (reverse single-step) via state history.

## Usage

### Python API

```python
from riscv_emu import CPU, Memory, MemoryRegion, Assembler

# Assemble a program
asm = Assembler(base_addr=0x20000000)
source = """
    li x5, 42
    li x6, 8
    add x7, x5, x6
"""
code, labels = asm.assemble(source, base_addr=0x20000000)

# Load into memory and run
mem = Memory([MemoryRegion(0x20000000, 0x100000, "rwx", data=code)])
mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
cpu = CPU(memory=mem, pc=0x20000000)
cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)  # Stack pointer

count = cpu.run(max_instructions=100)
print(f"Executed {count} instructions")
print(f"x7 = {cpu.get_reg(7)}")  # x7 = 50
```

### Command Line

```bash
# Install
pip install -e .

# Assemble a source file
riscv-emu asm programs/fibonacci.asm -o fib.bin

# Run a binary
riscv-emu run fib.bin --base-addr 0x20000000

# Run with tracing
riscv-emu run fib.bin --trace

# Run with profiling
riscv-emu run fib.bin --profile

# Interactive debugger
riscv-emu debug fib.bin

# Disassemble a binary
riscv-emu dis fib.bin --count 20
```

### Debugger Commands

```
(riscv-dbg) step 1           # Single-step 1 instruction
(riscv-dbg) continue 1000    # Run 1000 instructions
(riscv-dbg) break 0x20000010 # Set breakpoint
(riscv-dbg) regs             # Show registers
(riscv-dbg) mem 0x20000000 64 # Hexdump memory
(riscv-dbg) dis 0x20000000 10 # Disassemble 10 instructions
(riscv-dbg) profile report   # Show profiling data
(riscv-dbg) quit              # Exit
```

### Sample Programs

The `programs/` directory contains:
- **fibonacci.asm** — Recursive Fibonacci computation
- **memtest.asm** — Memory write/read/verify test
- **bubble_sort.asm** — Bubble sort over an in-memory array

### MMIO Example

```python
# UART at 0x10000000
output = []
def uart_write(addr, value, size):
    output.append(chr(value))

mem = Memory([MemoryRegion(0x10000000, 16, "rw", io_write=uart_write)])
cpu = CPU(memory=mem, pc=0x20000000)
# Program that writes to UART...
```

## Architecture

```
riscv_emu/
├── __init__.py      # Package exports
├── cpu.py           # RV32I CPU core (fetch/decode/execute, trap handling)
├── memory.py        # Sparse memory system (regions, permissions, MMIO)
├── csrs.py          # CSR file (Zicsr extension, machine-mode CSRs)
├── assembler.py     # Two-pass assembler (RV32I + pseudo-instructions)
├── loader.py        # ELF32 and raw binary loader
├── debugger.py      # Interactive GDB-like debugger
├── profiler.py      # Execution profiler
├── tracer.py        # Instruction trace recorder
└── cli.py           # Command-line interface
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT