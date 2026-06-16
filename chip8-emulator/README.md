# CHIP-8 Emulator

A full-featured CHIP-8 virtual machine emulator in Python, supporting all 35 standard opcodes plus SUPER-CHIP extensions.

## Features

### Core Emulation
- **Complete opcode set**: All 35 standard CHIP-8 opcodes implemented
- **4 KiB address space** with font sprites pre-loaded at 0x050–0x09F
- **64×32 monochrome display** with XOR sprite drawing and pixel wrapping
- **16-key hex keypad** (0–F) with press/release tracking
- **Delay timer** and **sound timer** at 60 Hz with configurable beeping
- **16-entry call stack** (24 in SUPER-CHIP mode)
- **16 general-purpose 8-bit registers** (V0–VF) and 16-bit address register (I)

### SUPER-CHIP Extensions
- **Extended mode flag** (00FF) for 128×64 display mode support
- **Scroll operations**: scroll down N lines (00Cn), scroll left (00FB), scroll right (00FC)
- **Exit interpreter** (00FD) — halts the CPU
- **Large font sprites** (Fx30) — 10-row fonts for digits 0–9 starting at 0x090
- **RPL flag registers** (Fx75/Fx85) — save/load 8 persistent flag registers
- **Extended jump** (BxNN) — in extended mode, uses Vx instead of V0 for offset
- **24-entry stack** in SUPER-CHIP mode (vs. standard 16)

### Developer Tools
- **Debugger**: Step-through execution with breakpoints, register/memory/display inspection, and opcode tracing
- **ROM Validator**: Detects empty ROMs, oversized ROMs, odd byte counts, common issues, and near-limit warnings
- **Disassembler**: Full mnemonic disassembly for all opcodes including SUPER-CHIP extensions
- **CLI**: Run, debug, disassemble, and validate ROMs from the command line
- **Cycle counter**: Track total instructions executed since reset
- **Step callback**: Optional `on_step` callback for custom monitoring or profiling

## Architecture

```
chip8_emulator/
├── __init__.py      # Package init, version, exports
├── cpu.py           # CPU with fetch-decode-execute, all opcodes
├── memory.py        # 4 KiB RAM, font sprites, ROM loading
├── display.py       # 64×32 display, XOR drawing, scrolling
├── keypad.py        # 16-key hex keypad
├── timer.py         # Delay timer at 60 Hz
├── sound.py         # Sound timer with beep state
├── opcodes.py       # Dispatch table for opcode lookup
├── debugger.py      # Step-through debugger
├── validator.py     # ROM validation and analysis
├── cli.py           # Command-line interface
└── roms.py          # Built-in test ROMs
```

## Usage

### Command Line

```bash
# Run a ROM
chip8-emulator run roms/maze.ch8

# Run with cycle limit and display dump
chip8-emulator run roms/maze.ch8 --cycles 1000 --dump-display

# Disassemble a ROM
chip8-emulator disasm roms/maze.ch8

# Validate a ROM
chip8-emulator validate roms/maze.ch8

# Debug a ROM step-by-step
chip8-emulator debug roms/maze.ch8 --steps 20

# Enable SUPER-CHIP mode
chip8-emulator run roms/maze.ch8 --super-chip
```

### Python API

```python
from chip8_emulator import CPU, Memory, Display, Keypad, Debugger, validate_rom

# Create and run a CPU
cpu = CPU()
cpu.load_rom_from_file("roms/maze.ch8")
cpu.run(cycles=1000)

# SUPER-CHIP mode
cpu = CPU(super_chip=True)
cpu.load_rom_from_file("roms/scroll_test.ch8")

# Step-by-step with cycle tracking
cpu = CPU()
cpu.load_rom_from_file("roms/maze.ch8")
while cpu.cycles < 5000:
    cpu.step()

# Monitor with on_step callback
def on_step(cpu, opcode):
    print(f"PC={cpu.pc:04X} opcode={opcode:04X}")

cpu = CPU(on_step=on_step)
cpu.load_rom_from_file("roms/maze.ch8")
cpu.run(cycles=100)

# Use the debugger
dbg = Debugger(cpu)
dbg.add_breakpoint(0x200)
dbg.enable_trace()
dbg.step()
print(dbg.dump_registers())
print(dbg.dump_display())

# Validate a ROM
result = validate_rom("roms/maze.ch8")
print(result)  # Shows errors, warnings, info
```

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

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_cpu.py -v
python -m pytest tests/test_extensions.py -v
python -m pytest tests/test_debugger.py -v
python -m pytest tests/test_validator.py -v
python -m pytest tests/test_bugfixes.py -v
```

The test suite includes 196 tests covering:
- All CPU opcodes
- Memory, display, keypad, and timer modules
- SUPER-CHIP extensions (scrolling, RPL flags, large fonts, extended mode)
- Debugger (breakpoints, tracing, state inspection)
- ROM validator
- CLI disassembler
- Built-in test ROMs
- Cycle counting and step callbacks
- Bug fixes (see Known Issues below)

## Known Issues (Resolved)

### Bug 1: MemoryError shadowing built-in (Fixed)
`chip8_emulator.memory.MemoryError` shadowed the Python built-in `MemoryError`. Renamed to `Chip8MemoryError` to avoid confusion and allow separate exception handling.

### Bug 2: Validator incorrectly flagging SUPER-CHIP opcodes (Fixed)
The ROM validator did not recognize SUPER-CHIP opcodes (Fx30, Fx75, Fx85, 00FD, 00FF, 00FB, 00FC, 00Cn) as valid, causing spurious "invalid opcode" warnings. Added all SUPER-CHIP opcodes to the validator's known-opcode list.

### Bug 3: Debugger step() bypassing CPU opcode storage (Fixed)
The debugger's `step()` method called `cpu._fetch()` and `cpu._decode_and_execute()` directly, bypassing `cpu.step()` which stores the current opcode in `self._opcode`. This meant opcode field extractors (`_x`, `_y`, `_kk`, `_nnn`, `_n`) read stale values. Fixed by having the debugger call `cpu.step()` instead.

### Edge Cases Verified (No Bug)
- **ADD/SUB with VF as destination**: VF correctly receives the carry/borrow flag, not the arithmetic result (verified by tests).
- **Fx55/Fx65 with x=0xF**: Correctly stores/loads VF as part of the register range.
- **Fx1E (ADD I, Vx)**: Correctly wraps I at 0xFFF.
- **DRW with n=0**: Draws zero rows, no collision.
- **scroll_down(0)**: No-op as expected.
- **BNNN extended mode**: Correctly uses Vx instead of V0 for offset.

## Implementation Notes

- Uses **CHIP-48 shift convention**: SHR/SHL operate on Vx directly (not Vy)
- Uses **modern I convention**: Fx55/Fx65 do NOT increment I
- Sprites wrap at display boundaries using modular arithmetic
- Timer `set()` clamps values to 0–255 (handles negative inputs correctly)
- All register values are masked to 0–255 to prevent overflow