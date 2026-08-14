# Core War — MARS Redcode Simulator

A full implementation of Core War, the classic programming game where assembly-like programs ("warriors") battle for control of a virtual computer's memory. This project implements the **ICWS'94 standard** with a complete MARS (Memory Array Redcode Simulator), Redcode parser, battle scheduler, tournament system, disassembler, and core memory visualizer.

## How It Works

Core War was invented by D.G. Jones and A.K. Dewdney in 1984. Warriors are written in Redcode, a simple assembly language. They are loaded into a circular memory array (the "core") and executed by a virtual machine. Warriors battle by:

- **Bombs**: Overwriting enemy code with `DAT` instructions to kill their processes
- **Replication**: Copying themselves to multiple locations to survive attacks
- **Scanning**: Searching core for enemy code and bombing it
- **Imps**: Simple self-replicating code that's nearly impossible to kill but can't kill either

A warrior loses when all its processes have executed a `DAT` instruction (or been bombed). The last warrior standing wins.

### Architecture

```
core-war/
├── core_war/
│   ├── __init__.py        # Package exports
│   ├── opcodes.py         # Opcode, Modifier, AddressMode enums + defaults
│   ├── instruction.py     # Instruction dataclass (one cell of core memory)
│   ├── parser.py          # Redcode parser (labels, EQU, ORG, END, expressions)
│   ├── mars.py            # MARS virtual machine (execution engine + step mode)
│   ├── scheduler.py       # Battle scheduler (multi-round, tournaments)
│   ├── disassembler.py    # Disassembler (instruction → Redcode text)
│   ├── visualizer.py      # Core memory heatmap, summary, battle log
│   ├── loader.py          # Warrior file loading utilities
│   └── cli.py             # Command-line interface (7 subcommands)
├── warriors/              # Built-in warrior files (.red)
│   ├── imp.red            # Simple self-replicator
│   ├── imp-spiral.red     # Multi-process imp variant
│   ├── dwarf.red          # Classic bomber
│   ├── stone.red          # Compact bomber
│   ├── paper.red          # Replicator
│   ├── scanner.red        # Scan-and-bomb warrior
│   └── kamikaze.red       # Aggressive self-destructing bomber
├── examples/
│   └── tournament.py      # Run a full tournament
├── tests/
│   └── test_*.py          # Test suite
└── pyproject.toml         # Package configuration
```

### Instruction Set (ICWS'94)

| Opcode | Description |
|--------|-------------|
| `DAT`  | Data / terminate process |
| `MOV`  | Copy instruction |
| `ADD`  | Add |
| `SUB`  | Subtract |
| `MUL`  | Multiply |
| `DIV`  | Divide |
| `MOD`  | Modulo |
| `JMP`  | Jump |
| `JMZ`  | Jump if zero |
| `JMN`  | Jump if non-zero |
| `DJN`  | Decrement and jump if non-zero |
| `SPL`  | Split into new process |
| `CMP`/`SEQ` | Skip if equal |
| `SNE`  | Skip if not equal |
| `SLT`  | Skip if less than |
| `NOP`  | No operation |

**Modifiers**: `.A`, `.B`, `.AB`, `.BA`, `.F`, `.X`, `.I` — specify which fields an opcode operates on.

**Addressing Modes**: `#` (immediate), `$` (direct), `@` (indirect via B), `*` (indirect via A), `{` (predec B), `<` (predec A), `}` (postinc B), `>` (postinc A).

## Usage

### CLI

```bash
# Validate a warrior file
python3 -m core_war.cli validate warriors/dwarf.red

# Dump parsed warrior instructions
python3 -m core_war.cli dump warriors/dwarf.red

# Run a battle between warriors
python3 -m core_war.cli --rounds 10 --max-cycles 20000 battle warriors/imp.red warriors/dwarf.red

# Run a round-robin tournament
python3 -m core_war.cli --rounds 5 tournament warriors/imp.red warriors/dwarf.red warriors/stone.red

# Trace a single warrior's execution
python3 -m core_war.cli --max-cycles 50 trace warriors/dwarf.red

# Run a battle and show the final core memory state
python3 -m core_war.cli --max-cycles 500 core-dump warriors/imp.red warriors/dwarf.red

# Run a battle with heatmap visualization
python3 -m core_war.cli --max-cycles 500 core-dump --heatmap warriors/imp.red warriors/dwarf.red

# Step through a battle one cycle at a time
python3 -m core_war.cli --max-cycles 100 step warriors/imp.red warriors/dwarf.red --steps 10
```

### Python API

```python
from core_war import load_warrior, MARS, BattleScheduler, disassemble

# Load warriors from files
imp = load_warrior("warriors/imp.red")
dwarf = load_warrior("warriors/dwarf.red")

# Run a single battle
mars = MARS(core_size=8000, max_cycles=80000, seed=42)
mars.reset()
mars.load_warrior(imp)
mars.load_warrior(dwarf)
result = mars.run()
print(f"Winner: {result.winner}, Cycles: {result.cycles}")

# Step through execution one cycle at a time
mars.reset()
mars.load_warrior(imp)
mars.load_warrior(dwarf)
while mars.step():
    alive = [w.name for w in mars.warriors if w.alive]
    print(f"Cycle {mars.cycle}: {alive}")

# Access execution trace
mars.trace_enabled = True
mars.run()
for entry in mars.trace[:10]:
    print(f"  {entry['warrior']} PC={entry['pc']}: {entry['instruction']}")

# View core memory summary
from core_war import core_summary, format_core_summary
summary = core_summary(mars.core)
print(format_core_summary(summary, len(mars.core)))

# Disassemble a region of core
from core_war import disassemble_around
print(disassemble_around(mars.core, mars.warriors[0].load_address, radius=5))
```

### Tournament

```python
from core_war import load_warrior, BattleScheduler

warriors = [
    load_warrior("warriors/imp.red"),
    load_warrior("warriors/dwarf.red"),
    load_warrior("warriors/stone.red"),
]

scheduler = BattleScheduler(rounds=10, seed=42)
result = scheduler.run_tournament(warriors)
for rank, stat in enumerate(result.standings, 1):
    print(f"#{rank} {stat.name}: {stat.wins}W {stat.losses}L {stat.draws}D (score={stat.score:.0f})")
```

### Writing Your Own Warrior

Warriors are written in Redcode, saved as `.red` files:

```redcode
; My Warrior - A comment
        ORG     start       ; Entry point

step    EQU     4           ; Constant definition

start   ADD     #step, bomb ; Increment bomb pointer
        MOV     bomb, @bomb ; Drop bomb
        JMP     start       ; Loop
bomb    DAT     #0, #0      ; The bomb
```

### Features

- **Full ICWS'94 instruction set**: 16 opcodes, 7 modifiers, 8 addressing modes
- **Redcode parser**: Labels, EQU constants, ORG/END pseudo-ops, arithmetic expressions, case-insensitive
- **Process scheduling**: Round-robin with SPL for multi-process warriors, configurable max processes
- **Battle scheduler**: Multi-round battles with randomized positions, round-robin tournaments
- **Step-through mode**: `step()` method for single-cycle execution control
- **Execution trace**: Optional trace recording for debugging
- **Access tracking**: Per-address execution count for heatmaps
- **Core memory visualization**: Heatmap, opcode frequency summary, battle log
- **Disassembler**: Convert core instructions back to Redcode text
- **Warrior loader**: Load from files, strings, or directories
- **7 built-in warriors**: Imp, Imp-Spiral, Dwarf, Stone, Paper, Scanner, Kamikaze
- **CLI**: 7 subcommands (battle, tournament, trace, dump, core-dump, step, validate)
- **Event hooks**: `on_execute` callback for real-time observation

## Built-in Warriors

| Warrior | Type | Description |
|---------|------|-------------|
| **Imp** | Replicator | Copies itself forward each cycle. Nearly unkillable but can't kill. |
| **Imp-Spiral** | Replicator | Uses SPL to create multiple imp processes. Harder to kill. |
| **Dwarf** | Bomber | Drops DAT bombs at regular intervals. Classic beginner warrior. |
| **Stone** | Bomber | Compact bomber using indirect addressing. |
| **Paper** | Replicator | Copies itself to new locations and splits. Spreads exponentially. |
| **Scanner** | Hunter | Scans core for non-empty cells and bombs them. |
| **Kamikaze** | Bomber | Aggressive bomber that self-destructs after dropping all bombs. |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `core_size` | 8000 | Size of circular memory array |
| `max_cycles` | 80000 | Cycles before draw is declared |
| `max_processes` | 8000 | Max processes per warrior |
| `min_separation` | 100 | Min distance between warrior load positions |

## Known Issues (Resolved)

The following bugs were found and fixed during the bug hunt phase:

1. **Label named "end" treated as END pseudo-op** — Labels matching pseudo-op names (like `end`) were incorrectly skipped during the first pass, causing "undefined label" errors. Fixed by checking if the token following `END` is an opcode — if so, `END` is treated as a label, not a pseudo-op.

2. **Immediate addressing in comparisons (SEQ/SNE/SLT)** — When using immediate addressing mode (`#`), comparison instructions compared the instruction against itself (since immediate resolves to `pc`), making `SNE #5, #3` always fail to skip. Fixed by adding `_compare_with_modes` and `_compare_less_with_modes` methods that use the immediate operand value directly for comparison.

3. **Immediate addressing in conditional jumps (JMZ/JMN/DJN)** — Same issue as comparisons: `JMZ 0, #0` didn't check the immediate value `0` but instead read the B-field of the instruction at `pc`. Fixed by special-casing immediate mode in JMZ, JMN, and DJN to use the operand value directly.

4. **Dead code in `_execute_instruction`** — Four variables (`a_val_a`, `a_val_b`, `b_val_a`, `b_val_b`) were fetched but never used. Removed.

5. **`_safe_eval` uses `eval()` with restricted character set** — The expression evaluator uses Python's `eval()` but restricts the input to digits, operators, parentheses, and whitespace only. Verified that code injection attempts (e.g., `__import__('os')`) are rejected by the character filter.

6. **Division by zero in arithmetic expressions** — Expressions like `1/0` in Redcode operands are caught and raise a `ParseError` instead of crashing.

7. **Division/modulo by zero in DIV/MOD opcodes** — `DIV` and `MOD` with a zero A-field return 0 instead of crashing, per ICWS'94 standard.

8. **Warrior loading wrap-around** — Warriors loaded near the end of core correctly wrap instructions to the beginning. Verified with core_size=20 and 3-instruction warrior at position 18.

9. **SPL at max processes** — When the process limit is reached, new processes from SPL are silently dropped instead of crashing.

10. **Arithmetic overflow wrapping** — ADD, SUB, MUL, DIV, MOD results are all wrapped via mod core_size to prevent overflow.

## License

MIT