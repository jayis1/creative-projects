<div align="center">

# 🖥️ RISC-V RV32I Emulator

**A full-featured 32-bit RISC-V CPU emulator with assembler, debugger, profiler, and MMIO devices**

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-159%20passing-brightgreen.svg)](./tests)

*A pure-Python implementation of the RISC-V RV32I base integer instruction set, RV32M multiply/divide extension, and Zicsr CSR extension — complete with a two-pass assembler, interactive GDB-like debugger, execution profiler, trace recorder, and UART/CLINT MMIO device emulation.*

</div>

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Running Programs](#running-programs)
  - [Assembling Source Code](#assembling-source-code)
  - [Interactive Debugging](#interactive-debugging)
  - [Disassembly](#disassembly)
  - [Configuration](#configuration)
  - [Self-Testing](#self-testing)
- [Python API](#python-api)
- [Instruction Set](#instruction-set)
- [MMIO Devices](#mmio-devices)
- [Memory Map](#memory-map)
- [Example Programs](#example-programs)
- [Testing](#testing)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

- **Complete RV32I base instruction set** — 40 instructions including LUI, AUIPC, JAL, JALR, all branches, loads, stores, and ALU ops
- **RV32M extension** — MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU with proper division-by-zero and overflow handling
- **Zicsr extension** — CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI with standard M-mode CSRs
- **Two-pass assembler** — labels, `.word`/`.string`/`.byte`/`.half`/`.align`/`.org` directives, 15+ pseudo-instructions
- **Disassembler** — converts binary instructions back to human-readable assembly with named registers
- **ELF32 loader** — load raw binaries, flat assembled binaries, and ELF32 little-endian executables
- **Interactive debugger** — breakpoints, watchpoints, single-step, register/memory inspection/modification, disassembly, continue, undo
- **UART MMIO** — QEMU-virt compatible 16550 UART at 0x10000000 for character I/O
- **CLINT device** — Core Local Interruptor with mtime/mtimecmp for timer interrupts
- **Execution profiler** — instruction frequency, hot addresses, runtime statistics
- **Trace recorder** — ring buffer, address filtering, register change tracking, CSV/JSON export
- **State serialization** — save/load CPU checkpoints as JSON for debugging and analysis
- **Configurable** — JSON configuration files for CPU, memory, and device settings
- **Proper trap handling** — ECALL/EBREAK, misaligned access, privilege mode transitions, mtvec vectoring
- **Comprehensive test suite** — 159 tests covering all instruction categories, assembler, memory, devices, config, and serialization

---

## 🏗 Architecture

```
riscv_emu/
├── __init__.py         # Package exports & version
├── cpu.py              # CPU core (RV32I + RV32M + Zicsr)
├── memory.py           # Sparse memory with regions, permissions, MMIO
├── csrs.py             # Control and Status Register file
├── assembler.py        # Two-pass assembler with pseudo-instructions
├── disassembler.py     # Instruction disassembler
├── loader.py           # Binary and ELF32 loader
├── debugger.py         # Interactive GDB-like debugger
├── profiler.py         # Execution profiler
├── tracer.py           # Trace recorder with filtering
├── devices.py          # MMIO device framework (UART, CLINT)
├── config.py           # Configuration system (JSON/TOML)
├── state.py            # State serialization (save/load)
├── logging_utils.py    # Structured logging utilities
└── cli.py              # Command-line interface
```

---

## 📦 Installation

### From Source (Recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/riscv-emu
pip install -e ".[dev]"
```

### Quick Install

```bash
pip install -e .
```

### Development Setup

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 🚀 Quick Start

### Run a Program

```bash
# Assemble and run Fibonacci
riscv-emu asm programs/fibonacci.asm -o fib.bin
riscv-emu run fib.bin

# With tracing and profiling
riscv-emu run fib.bin --trace --profile

# Show UART output
riscv-emu run programs/hello_uart.asm --uart
```

### Assemble Source Code

```bash
# Assemble to binary
riscv-emu asm programs/fibonacci.asm -o fibonacci.bin

# Assemble and show disassembly
riscv-emu asm programs/fibonacci.asm --disassemble

# Assemble with custom base address
riscv-emu asm programs/fibonacci.asm --base-addr 0x10000000 -o fib.bin
```

### Interactive Debugging

```bash
riscv-emu debug fibonacci.bin
```

```
RISC-V Debugger. Type 'help' for commands.
PC: 0x20000000  Priv: M  Insns: 0
(riscv-dbg) break 0x20000010
(riscv-dbg) continue
(riscv-dbg) step 5
(riscv-dbg) regs
(riscv-dbg) mem 0x20010000 16
(riscv-dbg) dis
(riscv-dbg) quit
```

---

## 📖 Usage

### Running Programs

```bash
# Basic execution
riscv-emu run <binary> [options]

# Options:
#   --base-addr ADDR      Base load address (default: 0x20000000)
#   --max-instructions N  Maximum instructions to execute
#   --trace              Enable instruction tracing
#   --profile            Enable profiling
#   --uart               Print UART MMIO output
#   --timer              Enable CLINT timer interrupts
#   --save-state FILE    Save CPU state to JSON at exit
#   --trace-json FILE    Export trace to JSON
#   --config-file FILE   Load configuration from JSON/TOML
#   --log-level LEVEL    Set log level (DEBUG/INFO/WARNING/ERROR)
#   --log-file FILE      Log to file
```

### Assembling Source Code

```bash
riscv-emu asm <source.asm> [options]

# Options:
#   --base-addr ADDR   Base address (default: 0x20000000)
#   -o, --output FILE  Output binary file
#   --disassemble      Show disassembly of assembled output
```

### Interactive Debugging

```bash
riscv-emu debug <binary> [options]
```

**Debugger Commands:**
| Command | Alias | Description |
|---------|-------|-------------|
| `step [N]` | `s` | Step N instructions |
| `continue [N]` | `c` | Continue for N instructions |
| `break ADDR` | `b` | Set breakpoint |
| `watch ADDR` | `wb` | Set watchpoint |
| `info b` | | List breakpoints |
| `del N` | | Delete breakpoint/watchpoint |
| `regs` | `r` | Show registers |
| `pc` | | Show program counter |
| `mem ADDR [LEN]` | `m` | Hexdump memory |
| `wr ADDR VAL` | | Write word to memory |
| `set REG VAL` | | Set register value |
| `dis [ADDR] [N]` | | Disassemble instructions |
| `undo` | | Undo last step |
| `trace [on\|off\|dump]` | | Tracing control |
| `profile [on\|off\|report]` | | Profiling control |
| `quit` | `q` | Exit debugger |

### Disassembly

```bash
# Disassemble first 20 instructions
riscv-emu dis <binary> --count 20

# Disassemble entire region
riscv-emu dis <binary> --all
```

### Configuration

```bash
# Generate default config
riscv-emu config init -o riscv-emu-config.json

# Validate a config file
riscv-emu config validate --config-file riscv-emu-config.json

# Show current config
riscv-emu config show
```

### Self-Testing

```bash
riscv-emu test
```

### Show Info

```bash
riscv-emu info
```

---

## 🐍 Python API

```python
from riscv_emu import (
    CPU, Memory, MemoryRegion, Assembler,
    disassemble, disassemble_to_string,
    load_elf, load_binary, Debugger, Profiler,
    Tracer, StateSerializer, EmulatorConfig,
    UARTDevice, CLINTDevice, DeviceBus,
)

# Quick setup — assemble and run
asm = Assembler(base_addr=0x20000000)
code, labels = asm.assemble("""
    li a0, 10
    jal ra, fib
    ecall

fib:
    addi sp, sp, -16
    sw ra, 12(sp)
    mv s0, a0
    li s1, 0
    li a0, 1
    bge s1, s0, fib_done
fib_loop:
    addi sp, sp, -4
    sw a0, 0(sp)
    add a0, s1, a0
    lw s1, 0(sp)
    addi sp, sp, 4
    addi s0, s0, -1
    bgt s0, x0, fib_loop
fib_done:
    lw ra, 12(sp)
    addi sp, sp, 16
    jalr x0, ra, 0
""", base_addr=0x20000000)

# Create memory and CPU
mem = Memory([MemoryRegion(0x20000000, 0x100000, "rwx")])
mem.write_bytes(0x20000000, bytes(code))
mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
mem.add_region(MemoryRegion(0x10000000, 8, "rw"))  # UART

cpu = CPU(memory=mem, pc=0x20000000)
cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)  # Stack pointer

# Run and check result
count = cpu.run(max_instructions=10000)
print(f"Executed {count} instructions, a0 = {cpu.get_reg(10)}")
print(f"UART output: {cpu.uart_output}")

# Save/load state
state = StateSerializer.save_state(cpu)
restored = StateSerializer.load_state(state)

# Disassemble
insn = mem.read_word(0x20000000)
print(disassemble(insn, 0x20000000))

# Use configuration
config = EmulatorConfig.default()
config.to_json()  # Export as JSON
config2 = EmulatorConfig.from_file("config.json")  # Load from file

# MMIO device bus
bus = DeviceBus()
uart = UARTDevice(0x10000000, 8)
clint = CLINTDevice(0x2000000)
bus.add_device(uart)
bus.add_device(clint)
```

---

## 📚 Instruction Set

### RV32I Base (40 instructions)

| Category | Instructions |
|----------|-------------|
| **LUI/AUIPC** | LUI, AUIPC |
| **Jumps** | JAL, JALR |
| **Branches** | BEQ, BNE, BLT, BGE, BLTU, BGEU |
| **Loads** | LB, LH, LW, LBU, LHU |
| **Stores** | SB, SH, SW |
| **I-type ALU** | ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI |
| **R-type ALU** | ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND |
| **System** | FENCE, ECALL, EBREAK |

### RV32M Extension (8 instructions)

MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU

### Zicsr Extension (6 instructions)

CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI

### Pseudo-Instructions

NOP, MV, NOT, NEG, LI, LA, J, RET, CALL, BEQZ, BNEZ, BGT, BLE, BGTU, BLEU

---

## 🔌 MMIO Devices

### UART (0x10000000)

QEMU-virt compatible 16550 UART with character I/O:
- **THR (0x00)**: Transmit Holding Register — write characters here
- **LSR (0x05)**: Line Status Register — THRE and TEMT bits

### CLINT (0x02000000)

Core Local Interruptor for timer interrupts:
- **mtime (0xBFF8)**: 64-bit machine timer
- **mtimecmp (0x4000)**: 64-bit timer compare register

---

## 🗺 Memory Map

| Region | Size | Permissions | Description |
|--------|------|-------------|-------------|
| 0x20000000 | 1 MB | RWX | Code/data |
| 0x7F000000 | 16 MB | RW | Stack |
| 0x10000000 | 8 B | RW | UART MMIO |
| 0x02000000 | 64 KB | RW | CLINT (configurable) |

---

## 📝 Example Programs

| Program | Description |
|---------|-------------|
| `programs/fibonacci.asm` | Recursive Fibonacci (10!) |
| `programs/bubble_sort.asm` | Bubble sort demonstration |
| `programs/hello_uart.asm` | UART character output |
| `programs/memtest.asm` | Memory read/write test |
| `programs/uart_hello.asm` | String printing via UART loop |
| `programs/counter.asm` | Counter with memory storage |
| `programs/factorial.asm` | Iterative factorial (uses MUL) |
| `programs/gcd.asm` | GCD using Euclidean algorithm (uses REM) |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=riscv_emu

# Run only new feature tests
pytest tests/test_new_features.py -v

# Self-test via CLI
riscv-emu test
```

**159 tests** covering:
- Memory operations (byte, half, word, dword, alignment, permissions)
- CSR read/write and bit manipulation
- Assembler encoding (all instruction types, pseudo-instructions, directives)
- CPU instruction execution (ALU, branches, loads, stores, jumps)
- RV32M multiply/divide operations
- Trap handling (ECALL, EBREAK, misaligned access)
- UART MMIO output
- Disassembler
- Configuration system
- State serialization (save/load/diff)
- MMIO devices (UART, CLINT, DeviceBus)
- Profiler and tracer

---

## 📜 Changelog

### v2.0.0 — Comprehensive Improvement

**New Features:**
- **Configuration system** — JSON/TOML config files for CPU, memory, UART, and trace settings
- **State serialization** — Save/load CPU state to JSON, state diffing for debugging
- **MMIO device framework** — Pluggable device bus with UART 16550 and CLINT timer
- **Enhanced CLI** — `riscv-emu test`, `riscv-emu config init/show/validate`, `riscv-emu info`, `--timer`, `--save-state`, `--trace-json`, `--config-file`
- **Logging** — Structured logging with colored terminal output and file logging
- **58 new tests** — Configuration, state serialization, devices, additional instructions

**Bug Fixes:**
- **LI pseudo-instruction** — Fixed incorrect LUI encoding for 20-bit upper immediates (was double-shifting)

**Improvements:**
- Updated `pyproject.toml` with proper metadata, classifiers, and optional dependencies
- Expanded example programs (counter, factorial, GCD, UART hello)
- Added GitHub Actions CI configuration
- Added CONTRIBUTING.md and LICENSE (MIT)
- Professional README with badges, TOC, architecture diagram, and API reference

### v1.1.0 — Enhancement & Bug Hunt

- Added RV32M extension (MUL/DIV)
- Added disassembler module
- Added UART MMIO output
- Fixed LUI/AUIPC encoding
- Fixed Load/Store opcode encoding
- Fixed JALR address calculation overflow
- Fixed `la` and `call` pseudo-instructions
- 101 tests passing

### v1.0.0 — Initial Release

- Complete RV32I instruction set
- Two-pass assembler with 15+ pseudo-instructions
- ELF32 loader
- Interactive debugger
- Profiler and tracer
- 81 tests passing

---

## 🗺 Roadmap

- [ ] **RV32C extension** — Compressed instruction support (16-bit instructions)
- [ ] **RV32F extension** — Single-precision floating-point
- [ ] **Privilege modes** — U-mode and S-mode support
- [ ] **Virtual memory** — SV32 page table walker
- [ ] **More MMIO devices** — PLIC, DMA, block device
- [ ] **Performance** — JIT compilation via Dynarmic or similar
- [ ] **GDB remote protocol** — Connect real GDB to the emulator
- [ ] **ELF relocation** — Full relocation processing for linked binaries
- [ ] **Assembler named CSRs** — Support `csrrw x1, mstatus, x2` (named CSRs)
- [ ] **Web interface** — Browser-based debugger with register/memory views
- [ ] **RISC-V compliance tests** — Pass the official RISC-V compliance suite

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up the development environment
- Adding new instructions, MMIO devices, and CLI commands
- Code style and testing requirements
- Pull request process

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.