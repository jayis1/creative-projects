<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-196%2B-brightgreen.svg" alt="196+ Tests">
  <img src="https://img.shields.io/badge/opcodes-35%2B-orange.svg" alt="35+ Opcodes">
  <img src="https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey.svg" alt="Cross-platform">
</p>

# 🕹️ CHIP-8 Emulator

A full-featured **CHIP-8 virtual machine emulator** in Python, supporting all 35 standard opcodes, SUPER-CHIP extensions, a built-in assembler, execution profiler, trace recorder, step-through debugger, and ROM validator.

```
  ╔══════════════════════════════════════════╗
  ║  CHIP-8 Emulator v2.0.0                 ║
  ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
  ║  35 standard opcodes ✓                  ║
  ║  SUPER-CHIP extensions ✓                ║
  ║  Built-in assembler ✓                   ║
  ║  Execution profiler ✓                   ║
  ║  Trace recorder ✓                       ║
  ║  Step-through debugger ✓                ║
  ║  ROM validator ✓                         ║
  ║  Config file support ✓                  ║
  ╚══════════════════════════════════════════╝
```

## 📑 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Assembler](#assembler)
- [Profiler](#profiler)
- [Trace Recorder](#trace-recorder)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Opcode Reference](#opcode-reference)
- [Testing](#testing)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

### Core Emulation
- **Complete opcode set**: All 35 standard CHIP-8 opcodes implemented
- **4 KiB address space** with font sprites pre-loaded at 0x050–0x09F
- **64×32 monochrome display** with XOR sprite drawing and pixel wrapping
- **16-key hex keypad** (0–F) with configurable key mappings
- **Delay timer** and **sound timer** at 60 Hz
- **16-entry call stack** (24 in SUPER-CHIP mode)
- **16 general-purpose 8-bit registers** (V0–VF) and 16-bit address register (I)

### SUPER-CHIP Extensions
- **Extended mode flag** (00FF) for 128×64 display mode support
- **Scroll operations**: scroll down N lines (00Cn), scroll left (00FB), scroll right (00FC)
- **Exit interpreter** (00FD) — halts the CPU
- **Large font sprites** (Fx30) — 10-row fonts for digits 0–9 starting at 0x090
- **RPL flag registers** (Fx75/Fx85) — save/load 8 persistent flag registers
- **Extended jump** (BxNN) — in extended mode, uses Vx instead of V0 for offset
- **24-entry stack** in SUPER-CHIP mode

### Developer Tools
- **Assembler**: Write CHIP-8 programs in human-readable mnemonics
- **Profiler**: Track opcode frequency, hot addresses, and register usage
- **Recorder**: Record and replay execution traces, compare runs for regression testing
- **Debugger**: Step-through execution with breakpoints, register/memory/display inspection, and opcode tracing
- **ROM Validator**: Detect empty ROMs, oversized ROMs, odd byte counts, and invalid opcodes
- **Disassembler**: Full mnemonic disassembly for all opcodes including SUPER-CHIP extensions
- **CLI**: Run, debug, profile, record, disassemble, assemble, and validate from the command line
- **Config files**: YAML/JSON/TOML configuration for display, keypad, CPU, and logging settings

---

## Quick Start

```bash
# Install
pip install -e .

# Run a ROM
chip8-emulator run maze.ch8 --cycles 1000 --dump-display

# Assemble a program
chip8-emulator asm program.ch8asm -o program.ch8

# Disassemble a ROM
chip8-emulator disasm maze.ch8

# Profile a ROM
chip8-emulator profile maze.ch8 --cycles 1000

# Record a trace
chip8-emulator record maze.ch8 -o trace.json --cycles 500

# Validate a ROM
chip8-emulator validate maze.ch8

# Debug a ROM
chip8-emulator debug maze.ch8 --steps 20 --breakpoint 0x210

# Generate a config file
chip8-emulator config --generate yaml > chip8-config.yaml
```

Or use the Python API:

```python
from chip8_emulator import CPU

# Create and run
cpu = CPU()
cpu.load_rom_from_file("maze.ch8")
cpu.run(cycles=1000)
print(cpu.display.render())
print(f"V0={cpu.V[0]:02X}  cycles={cpu.cycles}")
```

---

## Installation

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/chip8-emulator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with core dependencies
pip install -e .

# Install with all optional dependencies
pip install -e ".[dev,yaml,toml]"
```

### Requirements

- **Python 3.10+**
- Optional:
  - `pyyaml` — for YAML config file support
  - `tomli` — for TOML config support (Python < 3.11)
  - `pytest` — for running tests

---

## CLI Reference

```
chip8-emulator [OPTIONS] COMMAND [ARGS]...

Commands:
  run        Run a CHIP-8 ROM
  disasm     Disassemble a CHIP-8 ROM
  validate   Validate a CHIP-8 ROM
  debug      Debug a CHIP-8 ROM step-by-step
  profile    Profile a CHIP-8 ROM execution
  record     Record a CHIP-8 execution trace
  asm        Assemble CHIP-8 source code into a ROM
  config     Generate or show configuration

Global Options:
  -v, --verbose    Enable verbose logging
  --config PATH    Path to config file (YAML/JSON/TOML)

Run Options:
  -c, --cycles N      Max cycles to run (0=infinite)
  -s, --speed N       Instructions per second (default: 700)
  --super-chip        Enable SUPER-CHIP extensions
  --dump-display      Print the display on halt
  --dump-registers    Print register state on halt

Debug Options:
  -n, --steps N         Number of steps to run (default: 10)
  -b, --breakpoint ADDR Add breakpoint at address

Profile Options:
  -c, --cycles N     Number of cycles to profile (default: 1000)
  --super-chip        Enable SUPER-CHIP extensions
  --json              Output profiling data as JSON

Record Options:
  -o, --output PATH   Output JSON trace file (required)
  -c, --cycles N      Number of cycles to record (default: 5000)

Assemble Options:
  -o, --output PATH   Output ROM file
  --origin ADDR        Origin address (default: 0x200)
```

---

## Python API

### Core Emulation

```python
from chip8_emulator import CPU, Memory, Display, Keypad

# Create components
memory = Memory()
display = Display()
keypad = Keypad()

# Create CPU with custom components
cpu = CPU(memory=memory, display=display, keypad=keypad)

# Load ROM from file or bytes
cpu.load_rom_from_file("maze.ch8")
# or: cpu.load_rom(rom_bytes)

# Run for N cycles
cpu.run(cycles=1000)

# Or step manually
opcode = cpu.step()

# Read state
print(f"V0={cpu.V[0]:02X}  I={cpu.I:04X}  PC={cpu.pc:04X}")
print(f"Cycles: {cpu.cycles}")
print(f"Display:\n{cpu.display.render()}")
```

### SUPER-CHIP Mode

```python
cpu = CPU(super_chip=True)
cpu.load_rom_from_file("scroll_test.ch8")
cpu.run(cycles=5000)
print(f"Extended mode: {cpu.extended_mode}")
```

### Step-by-Step with Callback

```python
def on_step(cpu, opcode):
    if opcode == 0xD015:
        print(f"Draw at PC={cpu.pc - 2:04X}")

cpu = CPU(on_step=on_step)
cpu.load_rom_from_file("maze.ch8")
cpu.run(cycles=100)
```

### Debugger

```python
from chip8_emulator import CPU, Debugger

cpu = CPU()
cpu.load_rom_from_file("maze.ch8")
dbg = Debugger(cpu)

# Set breakpoints
dbg.add_breakpoint(0x200)
dbg.add_breakpoint(0x210)

# Step through execution
opcode = dbg.step()
print(f"Executed: {opcode:04X}")
print(dbg.dump_registers())
print(dbg.dump_display())

# Run until breakpoint
dbg.run_until_break(max_cycles=1000)
```

### Assembler

```python
from chip8_emulator import assemble

source = """
    CLS
    LD V0, 0x0A
    LD V1, 0x0A
    LD I, sprite
    DRW V0, V1, 5
    JP loop
loop:
    JP loop
sprite:
    .db 0x90, 0x90, 0xF0, 0x90, 0x90
"""

result = assemble(source)
if result.ok:
    print(f"Assembled {len(result.rom)} bytes")
    print(f"Symbols: {result.symbols}")
    # Use the ROM
    cpu = CPU()
    cpu.load_rom(result.rom)
else:
    for err in result.errors:
        print(f"Error: {err}")
```

### Profiler

```python
from chip8_emulator import CPU
from chip8_emulator.tracer import Tracer

cpu = CPU()
tracer = Tracer(cpu)
tracer.attach()

cpu.load_rom_from_file("maze.ch8")
cpu.run(cycles=1000)
tracer.detach()

# Print profiling summary
print(tracer.summary())

# Export as JSON
json_data = tracer.stats.to_json()
```

### Trace Recorder

```python
from chip8_emulator import CPU
from chip8_emulator.recorder import Recorder

cpu = CPU()
recorder = Recorder(cpu)
recorder._rom_data = rom_bytes
recorder.attach()
recorder.start()

cpu.load_rom(rom_bytes)
cpu.run(cycles=5000)

recorder.stop()
recorder.detach()
recorder.save("trace.json")

# Load and compare traces
rec2 = Recorder.load("trace.json")
diffs = recorder.diff(rec2)
```

### ROM Validator

```python
from chip8_emulator import validate_rom, validate_rom_bytes

# Validate from file path
result = validate_rom("maze.ch8")
print(result)  # Shows errors, warnings, info
print(f"Valid: {result.ok}")

# Validate from bytes
result = validate_rom_bytes(rom_data, name="custom.rom")
```

---

## Assembler

The built-in assembler supports the full CHIP-8 instruction set plus SUPER-CHIP extensions.

### Syntax

```asm
; Comments start with ; or //
; Labels end with :
; Numbers: decimal (10), hex (0x0A, $0A)

; Simple instructions
CLS
LD V0, 0x0A      ; Load immediate
LD V1, V2        ; Register copy
ADD V0, 5         ; Add immediate
ADD V0, V1        ; Add register
JP loop           ; Jump to label

; Special LD forms
LD I, sprite       ; Load address
LD DT, V0          ; Set delay timer
LD V0, DT          ; Read delay timer
LD F, V0           ; Font sprite
LD [I], V3          ; Store registers
LD V3, [I]          ; Load registers

; Directives
.org 0x200         ; Set origin address
.db 0xFF, 0x81    ; Define byte data
.dw 0x00E0         ; Define word data

; SUPER-CHIP extensions
EXIT
EXMODE
SCROLL_DOWN 4
SCROLL_LEFT
SCROLL_RIGHT
LD HF, V0
LD R, V0
LD V0, R
```

### CLI Usage

```bash
# Assemble a source file
chip8-emulator asm program.ch8asm -o program.ch8

# Assemble with custom origin
chip8-emulator asm program.ch8asm --origin 0x300

# Assemble and check symbols
chip8-emulator asm program.ch8asm
# Output: Assembled 42 bytes → program.ch8
#         Symbols:
#           loop: 0x206
#           sprite: 0x21A
```

---

## Profiler

The profiler collects runtime statistics during execution:

```
============================================================
CHIP-8 Execution Profile
============================================================
Total cycles: 1000
Draw calls:   42
Key polls:    0

Top Opcodes:
  JP               428 (42.8%) ██████████████████████
  LD byte          214 (21.4%) ██████████
  RND              142 (14.2%) ███████
  DRW               71 ( 7.1%) ███
  SE byte           71 ( 7.1%) ███
  ADD byte          71 ( 7.1%) ███

Hot Addresses (most executed):
  0x0200:    142 hits
  0x0208:    142 hits
  0x020A:    142 hits

Register Write Frequency:
  V0: 213
  V2: 142
============================================================
```

---

## Trace Recorder

Record and replay execution traces for regression testing and debugging:

```bash
# Record a trace
chip8-emulator record maze.ch8 -o trace.json --cycles 5000

# The JSON trace includes:
# - Every opcode executed
# - Register state after each step
# - I register and SP values
# - Collision flags
```

### Comparing Traces in Python

```python
from chip8_emulator.recorder import Recorder

rec1 = Recorder.load("trace_v1.json")
rec2 = Recorder.load("trace_v2.json")
diffs = rec1.diff(rec2)
for d in diffs:
    print(d)
```

---

## Configuration

The emulator supports YAML, JSON, and TOML configuration files:

### Generate a default config

```bash
chip8-emulator config --generate yaml > chip8-config.yaml
```

### Example YAML Config

```yaml
# CHIP-8 Emulator Configuration
display:
  width: 64
  height: 32
  on_char: "█"
  off_char: " "

keypad:
  mapping:
    1: 0x1
    2: 0x2
    3: 0x3
    4: 0xC
    q: 0x4
    w: 0x5
    e: 0x6
    r: 0xD
    a: 0x7
    s: 0x8
    d: 0x9
    f: 0xE
    z: 0xA
    x: 0x0
    c: 0xB
    v: 0xF

cpu:
  super_chip: false
  speed: 700
  max_cycles: 0

logging:
  level: "WARNING"
  file: null
```

### Use a config file

```bash
chip8-emulator --config chip8-config.yaml run maze.ch8
```

### Python API

```python
from chip8_emulator.config import load_config, generate_default_config

# Load from file
config = load_config("chip8-config.yaml")
print(config.cpu.super_chip)
print(config.display.on_char)

# Generate default config
yaml_config = generate_default_config("yaml")
json_config = generate_default_config("json")
```

---

## Architecture

```
chip8_emulator/
├── __init__.py        # Package init, version, exports
├── cpu.py             # CPU with fetch-decode-execute, all opcodes
├── memory.py          # 4 KiB RAM, font sprites, ROM loading
├── display.py         # 64×32 display, XOR drawing, scrolling
├── keypad.py          # 16-key hex keypad with configurable mapping
├── timer.py           # Delay timer at 60 Hz
├── sound.py           # Sound timer with beep state
├── opcodes.py         # Dispatch table for opcode lookup
├── debugger.py        # Step-through debugger with breakpoints
├── validator.py       # ROM validation and analysis
├── assembler.py       # CHIP-8 assembler (mnemonics → bytes)
├── tracer.py          # Execution profiler (opcode frequency, hot paths)
├── recorder.py        # Trace recorder/replayer (record & diff)
├── config.py          # YAML/JSON/TOML configuration support
├── cli.py             # Command-line interface
└── roms.py            # Built-in test ROMs
```

### Data Flow

```
                ┌──────────┐
    ROM ────►   │  Memory   │ ◄──── CPU reads/writes
                └──────────┘
                     │
                     ▼
              ┌──────────────┐
              │     CPU       │ ◄── Fetch/Decode/Execute loop
              │  (cpu.py)     │
              └──────┬───────┘
                     │
           ┌─────────┼─────────┐
           ▼         ▼         ▼
    ┌──────────┐ ┌────────┐ ┌────────┐
    │ Display  │ │ Keypad │ │Timers  │
    │64×32 XOR │ │16-key  │ │Delay + │
    │ +scroll  │ │hex map │ │Sound   │
    └──────────┘ └────────┘ └────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │     Developer Tools          │
    │  ┌────────┐ ┌────────────┐  │
    │  │Debugger│ │  Profiler   │  │
    │  └────────┘ └────────────┘  │
    │  ┌────────┐ ┌────────────┐  │
    │  │Assembler│ │  Recorder  │  │
    │  └────────┘ └────────────┘  │
    │  ┌────────┐ ┌────────────┐  │
    │  │Validator│ │  Disassembler│ │
    │  └────────┘ └────────────┘  │
    └──────────────────────────────┘
```

### Execution Model

1. **Fetch**: Read 2-byte opcode from `Memory[PC]`
2. **Decode**: Look up opcode in dispatch table
3. **Execute**: Call handler method, modify CPU state
4. **Cycle**: Increment cycle counter, call `on_step` callback

The `CPU.step()` method handles all four phases. The `CPU.run()` method loops `step()` until halted or a cycle limit is reached.

---

## Opcode Reference

| Opcode | Mnemonic | Description |
|--------|----------|-------------|
| 00E0 | CLS | Clear display |
| 00EE | RET | Return from subroutine |
| 0NNN | SYS addr | System call (ignored) |
| 1NNN | JP addr | Jump to address |
| 2NNN | CALL addr | Call subroutine |
| 3xkk | SE Vx, byte | Skip if Vx == kk |
| 4xkk | SNE Vx, byte | Skip if Vx != kk |
| 5xy0 | SE Vx, Vy | Skip if Vx == Vy |
| 6xkk | LD Vx, byte | Set Vx = kk |
| 7xkk | ADD Vx, byte | Vx += kk (no carry) |
| 8xy0 | LD Vx, Vy | Vx = Vy |
| 8xy1 | OR Vx, Vy | Vx \|= Vy |
| 8xy2 | AND Vx, Vy | Vx &= Vy |
| 8xy3 | XOR Vx, Vy | Vx ^= Vy |
| 8xy4 | ADD Vx, Vy | Vx += Vy (carry in VF) |
| 8xy5 | SUB Vx, Vy | Vx -= Vy (borrow in VF) |
| 8xy6 | SHR Vx | Vx >>= 1 (LSB in VF) |
| 8xy7 | SUBN Vx, Vy | Vx = Vy - Vx (borrow in VF) |
| 8xyE | SHL Vx | Vx <<= 1 (MSB in VF) |
| 9xy0 | SNE Vx, Vy | Skip if Vx != Vy |
| ANNN | LD I, addr | I = NNN |
| BNNN | JP V0, addr | PC = NNN + V0 |
| Cxkk | RND Vx, byte | Vx = random & kk |
| Dxyn | DRW Vx, Vy, n | Draw n-byte sprite at (Vx, Vy) |
| Ex9E | SKP Vx | Skip if key Vx pressed |
| ExA1 | SKNP Vx | Skip if key Vx not pressed |
| Fx07 | LD Vx, DT | Vx = delay timer |
| Fx0A | LD Vx, K | Wait for key press |
| Fx15 | LD DT, Vx | delay timer = Vx |
| Fx18 | LD ST, Vx | sound timer = Vx |
| Fx1E | ADD I, Vx | I += Vx |
| Fx29 | LD F, Vx | I = font sprite for digit Vx |
| Fx30 | LD HF, Vx | I = large font sprite (SUPER-CHIP) |
| Fx33 | LD B, Vx | Store BCD of Vx at I |
| Fx55 | LD [I], Vx | Store V0..Vx starting at I |
| Fx65 | LD Vx, [I] | Load V0..Vx starting at I |
| Fx75 | LD R, Vx | Save V0..Vx to RPL flags (SUPER-CHIP) |
| Fx85 | LD Vx, R | Load V0..Vx from RPL flags (SUPER-CHIP) |
| 00FD | EXIT | Exit interpreter (SUPER-CHIP) |
| 00FF | EXMODE | Enable extended mode (SUPER-CHIP) |
| 00Cn | SCROLL DOWN n | Scroll display down n lines (SUPER-CHIP) |
| 00FB | SCROLL LEFT | Scroll display left 4 pixels (SUPER-CHIP) |
| 00FC | SCROLL RIGHT | Scroll display right 4 pixels (SUPER-CHIP) |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_cpu.py -v
python -m pytest tests/test_assembler.py -v
python -m pytest tests/test_tracer.py -v
python -m pytest tests/test_recorder.py -v
python -m pytest tests/test_config.py -v

# Run with coverage
python -m pytest tests/ --cov=chip8_emulator --cov-report=term-missing

# Run only core tests
python -m pytest tests/test_cpu.py tests/test_memory.py tests/test_display.py -v
```

The test suite covers:
- All CPU opcodes (35 standard + SUPER-CHIP extensions)
- Memory, display, keypad, and timer modules
- Assembler (all mnemonics, labels, directives, error handling)
- Tracer/profiler (opcode frequency, address tracking, JSON export)
- Recorder (record, save, load, diff)
- Configuration parsing (JSON, YAML, TOML, defaults)
- Debugger (breakpoints, tracing, state inspection)
- ROM validator
- CLI disassembler
- Built-in test ROMs
- Cycle counting and step callbacks
- Bug regression tests

---

## Examples

See the `examples/` directory for complete runnable examples:

| Example | Description |
|---------|-------------|
| `basic_run.py` | Load a ROM, execute cycles, read register state |
| `profiler_demo.py` | Profile execution with opcode frequency analysis |
| `assembler_demo.py` | Assemble mnemonics and run the result |
| `recorder_demo.py` | Record and replay execution traces |
| `debugger_demo.py` | Step-through debugging with breakpoints |
| `validator_demo.py` | Validate and disassemble ROM files |

---

## Known Issues (Resolved)

### Bug 1: MemoryError shadowing built-in (Fixed)
`chip8_emulator.memory.MemoryError` shadowed the Python built-in `MemoryError`. Renamed to `Chip8MemoryError` to avoid confusion and allow separate exception handling.

### Bug 2: Validator incorrectly flagging SUPER-CHIP opcodes (Fixed)
The ROM validator did not recognize SUPER-CHIP opcodes (Fx30, Fx75, Fx85, 00FD, 00FF, 00FB, 00FC, 00Cn) as valid, causing spurious "invalid opcode" warnings. Added all SUPER-CHIP opcodes to the validator's known-opcode list.

### Bug 3: Debugger step() bypassing CPU opcode storage (Fixed)
The debugger's `step()` method called `cpu._fetch()` and `cpu._decode_and_execute()` directly, bypassing `cpu.step()` which stores the current opcode in `self._opcode`. This meant opcode field extractors (`_x`, `_y`, `_kk`, `_nnn`, `_n`) read stale values. Fixed by having the debugger call `cpu.step()` instead.

### Edge Cases Verified (No Bug)
- **ADD/SUB with VF as destination**: VF correctly receives the carry/borrow flag, not the arithmetic result
- **Fx55/Fx65 with x=0xF**: Correctly stores/loads VF as part of the register range
- **Fx1E (ADD I, Vx)**: Correctly wraps I at 0xFFF
- **DRW with n=0**: Draws zero rows, no collision
- **scroll_down(0)**: No-op as expected
- **BNNN extended mode**: Correctly uses Vx instead of V0 for offset

---

## Roadmap

- [ ] **GUI display** — SDL2/Pygame-based visual display for interactive use
- [ ] **Audio output** — Real beep sound using `pygame.mixer` or `simpleaudio`
- [ ] **Interactive keypad** — Real-time keyboard input for games
- [ ] **CHIP-8 interpreter mode** — Step-through with full register display
- [ ] **Extended display (128×64)** — Full SUPER-CHIP extended mode rendering
- [ ] **HiRes (SCHIP 128×64) drawing** — Dxyn in extended mode draws 16×16 sprites
- [ ] **ROM collection** — Built-in library of classic CHIP-8 programs
- [ ] **Web UI** — Browser-based emulator using Pyodide
- [ ] **Performance benchmarking** — Compare against reference implementations
- [ ] **OCTO compatibility** — Support for Octo-style assembly syntax

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:

- Setting up the development environment
- Code style and conventions
- Testing requirements
- Adding new opcodes, CLI commands, and modules
- Project structure

---

## Changelog

### v2.0.0 (2026-06-16)
- **NEW**: Built-in CHIP-8 assembler (`assembler.py`) with label support, directives, and full mnemonic coverage
- **NEW**: Execution profiler (`tracer.py`) — opcode frequency, hot addresses, register usage stats
- **NEW**: Trace recorder (`recorder.py`) — record/replay execution, diff traces, JSON serialization
- **NEW**: Configuration file support (`config.py`) — YAML/JSON/TOML configs for display, keypad, CPU, logging
- **NEW**: CLI subcommands: `profile`, `record`, `asm`, `config`
- **NEW**: `--dump-registers` flag for `run` command
- **NEW**: `--breakpoint` flag for `debug` command
- **NEW**: `--offset` flag for `disasm` command
- **NEW**: GitHub Actions CI configuration (`.github/workflows/ci.yml`)
- **NEW**: `examples/` directory with 6 runnable demo scripts
- **NEW**: `CONTRIBUTING.md` and `LICENSE` (MIT)
- **NEW**: Comprehensive test suite for all new modules (assembler, tracer, recorder, config)
- **IMPROVED**: README.md — badges, TOC, architecture diagrams, extensive API docs, examples
- **IMPROVED**: pyproject.toml — proper dependencies, optional extras, Python version classifiers
- **IMPROVED**: CLI — config file support, verbose logging, better help text
- **FIXED**: MemoryError shadowing built-in → renamed to `Chip8MemoryError`
- **FIXED**: Validator not recognizing SUPER-CHIP opcodes
- **FIXED**: Debugger bypassing CPU opcode storage

### v1.1.0 (2026-06-16)
- Added SUPER-CHIP extensions (scroll, extended mode, large fonts, RPL flags, 24-entry stack)
- Added step-through debugger with breakpoints and tracing
- Added ROM validator
- Added cycle counter and on_step callback
- Enhanced CLI with disasm, validate, debug subcommands

### v1.0.0 (2026-06-16)
- Initial release
- All 35 standard CHIP-8 opcodes
- 64×32 display with XOR drawing
- 16-key hex keypad
- Delay and sound timers
- 9 built-in test ROMs
- 139 tests

---

## License

MIT License — see [LICENSE](LICENSE) for details.