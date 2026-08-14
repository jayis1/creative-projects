# Core War — MARS Redcode Simulator

A full implementation of Core War, the classic programming game where assembly-like programs ("warriors") battle for control of a virtual computer's memory. This project implements the **ICWS'94 standard** with a complete MARS (Memory Array Redcode Simulator), Redcode parser, battle scheduler, and tournament system.

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
│   ├── instruction.py    # Instruction dataclass (one cell of core memory)
│   ├── parser.py          # Redcode parser (labels, EQU, ORG, END, expressions)
│   ├── mars.py            # MARS virtual machine (execution engine)
│   ├── scheduler.py       # Battle scheduler (multi-round, tournaments)
│   └── cli.py             # Command-line interface
├── warriors/              # Built-in warrior files (.red)
│   ├── imp.red            # Simple self-replicator
│   ├── dwarf.red          # Classic bomber
│   ├── stone.red          # Compact bomber
│   ├── paper.red          # Replicator
│   └── scanner.red        # Scan-and-bomb warrior
├── examples/
│   └── tournament.py      # Run a full tournament
└── tests/
    └── test_*.py          # Test suite
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
# Dump parsed warrior instructions
python3 -m core_war.cli dump warriors/dwarf.red

# Run a battle between warriors
python3 -m core_war.cli --rounds 10 --max-cycles 20000 battle warriors/imp.red warriors/dwarf.red

# Run a round-robin tournament
python3 -m core_war.cli --rounds 5 tournament warriors/imp.red warriors/dwarf.red warriors/stone.red

# Trace a single warrior's execution
python3 -m core_war.cli --max-cycles 50 trace warriors/dwarf.red
```

### Python API

```python
from core_war.parser import RedcodeParser
from core_war.mars import MARS

# Parse warrior source
parser = RedcodeParser()
imp = parser.parse("ORG start\nstart MOV 0, 1", name="Imp")
dwarf = parser.parse(open("warriors/dwarf.red").read(), name="Dwarf")

# Run a battle
mars = MARS(core_size=8000, max_cycles=80000, seed=42)
mars.reset()
mars.load_warrior(imp)
mars.load_warrior(dwarf)
result = mars.run()

print(f"Winner: {result.winner}")
print(f"Cycles: {result.cycles}")
```

### Tournament

```python
from core_war.parser import RedcodeParser
from core_war.scheduler import BattleScheduler

parser = RedcodeParser()
warriors = [
    parser.parse(open("warriors/imp.red").read(), "Imp"),
    parser.parse(open("warriors/dwarf.red").read(), "Dwarf"),
    parser.parse(open("warriors/stone.red").read(), "Stone"),
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

## Built-in Warriors

| Warrior | Type | Description |
|---------|------|-------------|
| **Imp** | Replicator | Copies itself forward each cycle. Nearly unkillable but can't kill. |
| **Dwarf** | Bomber | Drops DAT bombs at regular intervals. Classic beginner warrior. |
| **Stone** | Bomber | Compact bomber using indirect addressing. |
| **Paper** | Replicator | Copies itself to new locations and splits. Spreads exponentially. |
| **Scanner** | Hunter | Scans core for non-empty cells and bombs them. |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `core_size` | 8000 | Size of circular memory array |
| `max_cycles` | 80000 | Cycles before draw is declared |
| `max_processes` | 8000 | Max processes per warrior |
| `min_separation` | 100 | Min distance between warrior load positions |

## License

MIT