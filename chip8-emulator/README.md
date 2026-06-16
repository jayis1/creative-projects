# CHIP-8 Emulator

A full-featured CHIP-8 virtual machine emulator in Python, implementing all 35 standard opcodes with a clean, modular architecture.

## What is CHIP-8?

CHIP-8 is a simple interpreted programming language from the late 1970s, originally designed for the COSMAC VIP and Telmac 1800 computers. It's one of the most popular targets for emulator development due to its small instruction set (35 opcodes), simple 64×32 monochrome display, and 16-key hex keypad. Classic games like Pong, Space Invaders, Tetris, and Pac-Man were ported to CHIP-8.

## How It Works

The emulator implements a complete CHIP-8 virtual machine:

- **Memory**: 4 KiB address space with built-in font sprites at `0x050–0x09F`, ROMs loaded at `0x200`
- **CPU**: 16 8-bit registers (V0–VF), 16-bit address register (I), program counter, 16-level call stack
- **Display**: 64×32 monochrome buffer with XOR sprite drawing and collision detection
- **Timers**: Delay timer and sound timer, both counting down at 60 Hz
- **Keypad**: 16-key hex input with configurable physical key mapping
- **Opcodes**: All 35 standard CHIP-8 instructions fully implemented

### Opcode Groups

| Prefix | Instructions | Description |
|--------|-------------|-------------|
| `0xxx` | `00E0`, `00EE` | Clear screen, return from subroutine |
| `1xxx` | `1NNN` | Jump to address |
| `2xxx` | `2NNN` | Call subroutine |
| `3xxx` | `3xkk` | Skip if register equals byte |
| `4xxx` | `4xkk` | Skip if register not equals byte |
| `5xxx` | `5xy0` | Skip if register equals register |
| `6xxx` | `6xkk` | Load byte into register |
| `7xxx` | `7xkk` | Add byte to register (no carry) |
| `8xxx` | `8xy0–8xyE` | Register arithmetic: LD, OR, AND, XOR, ADD, SUB, SHR, SUBN, SHL |
| `9xxx` | `9xy0` | Skip if register not equals register |
| `Axxx` | `ANNN` | Load address into I |
| `Bxxx` | `BNNN` | Jump to address + V0 |
| `Cxxx` | `Cxkk` | Random byte AND mask |
| `Dxxx` | `Dxyn` | Draw sprite at (Vx, Vy) |
| `Exxx` | `Ex9E`, `ExA1` | Skip if key pressed / not pressed |
| `Fxxx` | `Fx07–Fx65` | Timer, key wait, font, BCD, register save/load |

### Design Decisions

- **8xy6/8xyE**: Uses CHIP-48/SUPER-CHIP convention (shift Vx directly, not Vy)
- **Fx55/Fx65**: Modern convention (I is NOT auto-incremented)
- **8xy1/8xy2/8xy3**: No VF reset (modern behavior)

## Usage

### As a Library

```python
from chip8_emulator import CPU, Display, Keypad, Memory

# Create and configure
cpu = CPU()
cpu.load_rom_from_file("game.ch8")

# Step through instructions
cpu.step()
cpu.step()

# Run for N cycles
cpu.run(cycles=100)

# Inspect state
print(f"PC: {cpu.pc:#06x}, V0: {cpu.V[0]:#04x}")
print(f"Display:\n{cpu.display.render()}")

# Simulate key input
cpu.keypad.press(0x5)  # Press hex key 5
```

### Command Line

```bash
# Run a ROM (with display dump on exit)
chip8-emulator run game.ch8 --dump-display

# Run with speed limit
chip8-emulator run game.ch8 --speed 500

# Disassemble a ROM
chip8-emulator disasm game.ch8

# Validate a ROM
chip8-emulator validate game.ch8
```

### Built-in Test ROMs

```python
from chip8_emulator.roms import ALL_ROMS

# Get a test ROM
rom = ALL_ROMS["hello"]()
cpu = CPU()
cpu.load_rom(rom)
```

Available test ROMs: `maze`, `counter`, `ibm_logo`, `hello`, `add_test`, `bcd_test`, `draw_test`, `key_test`, `scroll_test`

## Installation

```bash
pip install -e .
```

## Testing

```bash
pytest tests/ -v
```

## Architecture

```
chip8_emulator/
├── __init__.py      # Package exports
├── cpu.py           # CPU fetch-decode-execute loop + all opcode handlers
├── display.py       # 64×32 monochrome display with XOR drawing
├── keypad.py        # 16-key hex keypad with configurable mapping
├── memory.py        # 4 KiB address space + font sprites
├── opcodes.py       # Opcode dispatch table
├── sound.py         # Sound timer (60 Hz countdown)
├── timer.py         # Delay timer (60 Hz countdown)
├── cli.py           # CLI runner + disassembler
└── roms.py          # Built-in test ROMs
```

## License

MIT