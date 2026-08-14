"""
MARS (Memory Array Redcode Simulator) — the Core War virtual machine.

Executes warriors in a circular memory array, implementing the full
ICWS'94 instruction set semantics including all addressing modes,
modifiers, and process scheduling.
"""

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core_war.instruction import Instruction
from core_war.opcodes import Opcode, Modifier, AddressMode
from core_war.parser import ParsedWarrior


@dataclass
class WarriorState:
    """Runtime state of a warrior in the MARS."""

    name: str
    instructions: List[Instruction]
    start_offset: int
    load_address: int = 0          # Where in core the warrior was loaded
    processes: deque = field(default_factory=deque)  # Process queue (instruction pointers)
    alive: bool = True
    instructions_executed: int = 0
    max_processes_reached: int = 0


@dataclass
class BattleResult:
    """Result of a single battle."""

    winner: Optional[str] = None    # Warrior name, or None for a draw
    survivors: List[str] = field(default_factory=list)
    rounds: int = 0
    cycles: int = 0
    reason: str = ""                # How the battle ended
    warrior_results: Dict[str, str] = field(default_factory=dict)  # name → "win"/"loss"/"draw"


class MARS:
    """
    The Memory Array Redcode Simulator.

    Args:
        core_size: Size of the circular memory array (default 8000).
        max_cycles: Maximum cycles before a draw is declared (default 80000).
        max_processes: Maximum processes per warrior (default 8000).
        min_separation: Minimum distance between warrior load positions (default 100).
    """

    def __init__(
        self,
        core_size: int = 8000,
        max_cycles: int = 80000,
        max_processes: int = 8000,
        min_separation: int = 100,
        seed: Optional[int] = None,
    ):
        if core_size <= 0:
            raise ValueError("core_size must be positive")
        if max_cycles <= 0:
            raise ValueError("max_cycles must be positive")
        if max_processes <= 0:
            raise ValueError("max_processes must be positive")

        self.core_size = core_size
        self.max_cycles = max_cycles
        self.max_processes = max_processes
        self.min_separation = min_separation
        self.rng = random.Random(seed)

        # Core memory: list of Instruction objects
        self.core: List[Instruction] = []
        self.warriors: List[WarriorState] = []
        self.cycle: int = 0

        # For recording execution trace (optional debugging)
        self.trace: List[dict] = []
        self.trace_enabled = False

        # Access tracking: how many times each core address was executed
        self.access_counts: Dict[int, int] = {}

        # Callback hooks for event observation
        self.on_execute = None  # callable(warrior_name, pc, instruction)

    def reset(self) -> None:
        """Reset the MARS to initial state."""
        # Initialize core with DAT 0, 0 instructions
        self.core = [Instruction(Opcode.DAT, Modifier.F, AddressMode.DIRECT, 0,
                                  AddressMode.DIRECT, 0)
                     for _ in range(self.core_size)]
        self.warriors = []
        self.cycle = 0
        self.trace = []
        self.access_counts = {}

    def load_warrior(self, warrior: ParsedWarrior, position: Optional[int] = None) -> WarriorState:
        """
        Load a warrior into core memory at the given position.
        If position is None, a random valid position is chosen.
        """
        if position is None:
            position = self._find_load_position(len(warrior.instructions))

        # Copy warrior instructions into core
        for i, instr in enumerate(warrior.instructions):
            addr = (position + i) % self.core_size
            self.core[addr] = instr.copy()

        state = WarriorState(
            name=warrior.name,
            instructions=warrior.instructions,
            start_offset=warrior.start_offset,
            load_address=position,
        )

        # Initial process starts at the warrior's entry point
        entry = (position + warrior.start_offset) % self.core_size
        state.processes.append(entry)

        self.warriors.append(state)
        return state

    def _find_load_position(self, warrior_len: int) -> int:
        """Find a valid position to load a warrior, respecting min_separation."""
        if not self.warriors:
            return self.rng.randint(0, self.core_size - 1)

        for _ in range(1000):  # Try 1000 times
            pos = self.rng.randint(0, self.core_size - 1)
            if self._is_valid_position(pos, warrior_len):
                return pos
        # Fallback: just use a random position
        return self.rng.randint(0, self.core_size - 1)

    def _is_valid_position(self, pos: int, warrior_len: int) -> bool:
        """Check if a position is far enough from existing warriors."""
        for w in self.warriors:
            # Calculate circular distance between load positions
            diff = abs(pos - w.load_address)
            circular_dist = min(diff, self.core_size - diff)
            # Also check the end of the existing warrior
            w_end = w.load_address + len(w.instructions) - 1
            diff2 = abs(pos - w_end)
            circular_dist2 = min(diff2, self.core_size - diff2)
            if circular_dist < self.min_separation or circular_dist2 < self.min_separation:
                return False
        return True

    def run(self) -> BattleResult:
        """Run the battle until completion. Returns a BattleResult."""
        if not self.warriors:
            return BattleResult(reason="No warriors loaded")

        alive_warriors = [w for w in self.warriors if w.alive]
        if not alive_warriors:
            return BattleResult(reason="No alive warriors")

        # Execute round-robin: each alive warrior executes one instruction per cycle
        while self.cycle < self.max_cycles:
            alive_before = sum(1 for w in self.warriors if w.alive)
            if alive_before <= 1 and len(self.warriors) > 1:
                break
            if alive_before == 0:
                break

            # Each alive warrior executes one instruction
            for warrior in self.warriors:
                if not warrior.alive:
                    continue
                self._execute_one_instruction(warrior)

            self.cycle += 1

            # Check if only one warrior is alive (in multi-warrior battles)
            alive_count = sum(1 for w in self.warriors if w.alive)
            if len(self.warriors) > 1 and alive_count <= 1:
                break

        return self._make_result()

    def _execute_one_instruction(self, warrior: WarriorState) -> None:
        """Execute one instruction for the given warrior (one process step)."""
        if not warrior.processes:
            warrior.alive = False
            return

        # Get next process from the queue
        pc = warrior.processes.popleft()
        pc = pc % self.core_size
        instr = self.core[pc]

        # Track access
        self.access_counts[pc] = self.access_counts.get(pc, 0) + 1

        if self.trace_enabled:
            self.trace.append({
                "warrior": warrior.name,
                "pc": pc,
                "instruction": str(instr),
                "cycle": self.cycle,
            })

        if self.on_execute:
            self.on_execute(warrior.name, pc, instr)

        warrior.instructions_executed += 1

        # Execute the instruction
        next_pcs = self._execute_instruction(pc, instr, warrior)

        # Add resulting program counters to the process queue
        for npc in next_pcs:
            if len(warrior.processes) < self.max_processes:
                warrior.processes.append(npc % self.core_size)
            # If process limit reached, silently drop new processes

        # Check if warrior has no more processes (it's dead)
        if not warrior.processes:
            warrior.alive = False

    def step(self) -> bool:
        """
        Execute a single cycle (one instruction per alive warrior).

        Returns True if the battle is still running, False if finished.
        """
        if self.cycle >= self.max_cycles:
            return False

        alive_count = sum(1 for w in self.warriors if w.alive)
        if alive_count == 0:
            return False
        if len(self.warriors) > 1 and alive_count <= 1:
            return False

        for warrior in self.warriors:
            if not warrior.alive:
                continue
            self._execute_one_instruction(warrior)

        self.cycle += 1
        return True

    def _execute_instruction(
        self, pc: int, instr: Instruction, warrior: WarriorState
    ) -> List[int]:
        """
        Execute a single instruction and return the list of next PCs.

        Most instructions return [pc + 1].
        JMP, SPL, and conditional jumps may return different PCs.
        DAT kills the process (returns empty list).
        """
        core = self.core
        cs = self.core_size
        next_pc = (pc + 1) % cs

        # Resolve A and B operands to effective addresses
        a_addr = self._resolve_address(pc, instr.a_mode, instr.a_value, warrior)
        b_addr = self._resolve_address(pc, instr.b_mode, instr.b_value, warrior)

        # Apply predecrement / postincrement side effects
        a_val_a = core[a_addr].a_value
        a_val_b = core[a_addr].b_value
        b_val_a = core[b_addr].a_value
        b_val_b = core[b_addr].b_value

        op = instr.opcode
        mod = instr.modifier

        if op == Opcode.DAT:
            # DAT kills the executing process
            return []

        elif op == Opcode.NOP:
            return [next_pc]

        elif op == Opcode.MOV:
            self._do_move(mod, core, a_addr, b_addr)
            return [next_pc]

        elif op == Opcode.ADD:
            self._do_arithmetic(mod, core, a_addr, b_addr, lambda a, b: (a + b) % cs)
            return [next_pc]

        elif op == Opcode.SUB:
            self._do_arithmetic(mod, core, a_addr, b_addr, lambda a, b: (b - a) % cs)
            return [next_pc]

        elif op == Opcode.MUL:
            self._do_arithmetic(mod, core, a_addr, b_addr, lambda a, b: (a * b) % cs)
            return [next_pc]

        elif op == Opcode.DIV:
            self._do_arithmetic(mod, core, a_addr, b_addr,
                                lambda a, b: (b // a) % cs if a != 0 else 0)
            return [next_pc]

        elif op == Opcode.MOD:
            self._do_arithmetic(mod, core, a_addr, b_addr,
                                lambda a, b: (b % a) % cs if a != 0 else 0)
            return [next_pc]

        elif op == Opcode.JMP:
            return [a_addr]

        elif op == Opcode.SPL:
            # Split: current process continues, new process at A-address
            # The order matters: new process goes to back of queue
            return [next_pc, a_addr]

        elif op == Opcode.JMZ:
            if self._is_zero(mod, core, b_addr):
                return [a_addr]
            return [next_pc]

        elif op == Opcode.JMN:
            if not self._is_zero(mod, core, b_addr):
                return [a_addr]
            return [next_pc]

        elif op == Opcode.DJN:
            # Decrement B-field, then jump if non-zero
            core[b_addr].b_value = (core[b_addr].b_value - 1) % cs
            if core[b_addr].b_value != 0:
                return [a_addr]
            return [next_pc]

        elif op in (Opcode.CMP, Opcode.SEQ):
            if self._compare_equal(mod, core, a_addr, b_addr):
                return [(pc + 2) % cs]  # Skip next instruction
            return [next_pc]

        elif op == Opcode.SNE:
            if not self._compare_equal(mod, core, a_addr, b_addr):
                return [(pc + 2) % cs]
            return [next_pc]

        elif op == Opcode.SLT:
            if self._compare_less(mod, core, a_addr, b_addr):
                return [(pc + 2) % cs]
            return [next_pc]

        # Unknown opcode: treat as NOP
        return [next_pc]

    def _resolve_address(
        self, pc: int, mode: AddressMode, value: int, warrior: WarriorState
    ) -> int:
        """
        Resolve an operand to an effective core address.

        Handles all addressing modes including predecrement/postincrement.
        """
        cs = self.core_size
        base = (pc + value) % cs

        if mode == AddressMode.IMMEDIATE:
            # Immediate: value is used directly, address points to current instruction
            return pc
        elif mode == AddressMode.DIRECT:
            return base
        elif mode == AddressMode.INDIRECT_B:
            # Indirect via B-field of the pointed instruction
            ptr = (base + self.core[base].b_value) % cs
            return ptr
        elif mode == AddressMode.INDIRECT_A:
            ptr = (base + self.core[base].a_value) % cs
            return ptr
        elif mode == AddressMode.PREDEC_B:
            # Predecrement B-field, then use as pointer
            self.core[base].b_value = (self.core[base].b_value - 1) % cs
            ptr = (base + self.core[base].b_value) % cs
            return ptr
        elif mode == AddressMode.PREDEC_A:
            self.core[base].a_value = (self.core[base].a_value - 1) % cs
            ptr = (base + self.core[base].a_value) % cs
            return ptr
        elif mode == AddressMode.POSTINC_B:
            # Use B-field as pointer, then increment it
            ptr = (base + self.core[base].b_value) % cs
            self.core[base].b_value = (self.core[base].b_value + 1) % cs
            return ptr
        elif mode == AddressMode.POSTINC_A:
            ptr = (base + self.core[base].a_value) % cs
            self.core[base].a_value = (self.core[base].a_value + 1) % cs
            return ptr
        else:
            return base

    def _do_move(self, mod: Modifier, core: List[Instruction], a_addr: int, b_addr: int) -> None:
        """Execute MOV with the given modifier."""
        src = core[a_addr]
        dst = core[b_addr]

        if mod == Modifier.A:
            dst.a_value = src.a_value
        elif mod == Modifier.B:
            dst.b_value = src.b_value
        elif mod == Modifier.AB:
            dst.b_value = src.a_value
        elif mod == Modifier.BA:
            dst.a_value = src.b_value
        elif mod == Modifier.F:
            dst.a_value = src.a_value
            dst.b_value = src.b_value
        elif mod == Modifier.X:
            dst.b_value = src.a_value
            dst.a_value = src.b_value
        elif mod == Modifier.I:
            core[b_addr] = src.copy()

    def _do_arithmetic(
        self,
        mod: Modifier,
        core: List[Instruction],
        a_addr: int,
        b_addr: int,
        op,  # callable: (a: int, b: int) -> int
    ) -> None:
        """Execute an arithmetic operation with the given modifier.

        For ADD: op = lambda a, b: (a + b) % cs
        For SUB: op = lambda a, b: (b - a) % cs
        """
        src = core[a_addr]
        dst = core[b_addr]

        if mod == Modifier.A:
            dst.a_value = op(src.a_value, dst.a_value)
        elif mod == Modifier.B:
            dst.b_value = op(src.b_value, dst.b_value)
        elif mod == Modifier.AB:
            dst.b_value = op(src.a_value, dst.b_value)
        elif mod == Modifier.BA:
            dst.a_value = op(src.b_value, dst.a_value)
        elif mod in (Modifier.F, Modifier.I):
            dst.a_value = op(src.a_value, dst.a_value)
            dst.b_value = op(src.b_value, dst.b_value)
        elif mod == Modifier.X:
            dst.b_value = op(src.a_value, dst.b_value)
            dst.a_value = op(src.b_value, dst.a_value)

    def _is_zero(self, mod: Modifier, core: List[Instruction], addr: int) -> bool:
        """Check if the operand at addr is zero, per the modifier."""
        instr = core[addr]
        if mod in (Modifier.A, Modifier.BA):
            return instr.a_value == 0
        elif mod in (Modifier.B, Modifier.AB):
            return instr.b_value == 0
        elif mod in (Modifier.F, Modifier.I):
            return instr.a_value == 0 and instr.b_value == 0
        elif mod == Modifier.X:
            return instr.a_value == 0 and instr.b_value == 0
        return False

    def _compare_equal(self, mod: Modifier, core: List[Instruction], a_addr: int, b_addr: int) -> bool:
        """Compare two instructions for equality per modifier."""
        a = core[a_addr]
        b = core[b_addr]

        if mod == Modifier.A:
            return a.a_value == b.a_value
        elif mod == Modifier.B:
            return a.b_value == b.b_value
        elif mod == Modifier.AB:
            return a.a_value == b.b_value
        elif mod == Modifier.BA:
            return a.b_value == b.a_value
        elif mod in (Modifier.F,):
            return a.a_value == b.a_value and a.b_value == b.b_value
        elif mod == Modifier.X:
            return a.a_value == b.b_value and a.b_value == b.a_value
        elif mod == Modifier.I:
            return (a.opcode == b.opcode and a.modifier == b.modifier
                    and a.a_mode == b.a_mode and a.a_value == b.a_value
                    and a.b_mode == b.b_mode and a.b_value == b.b_value)
        return False

    def _compare_less(self, mod: Modifier, core: List[Instruction], a_addr: int, b_addr: int) -> bool:
        """Compare if A < B per modifier."""
        a = core[a_addr]
        b = core[b_addr]

        if mod in (Modifier.A, Modifier.BA):
            return a.a_value < b.a_value
        elif mod in (Modifier.B, Modifier.AB):
            return a.b_value < b.b_value
        elif mod in (Modifier.F, Modifier.I):
            return a.a_value < b.a_value and a.b_value < b.b_value
        elif mod == Modifier.X:
            return a.a_value < b.b_value and a.b_value < b.a_value
        return False

    def _make_result(self) -> BattleResult:
        """Create a BattleResult from the current state."""
        alive = [w.name for w in self.warriors if w.alive]
        dead = [w.name for w in self.warriors if not w.alive]

        warrior_results = {}
        for w in self.warriors:
            if w.alive and len(self.warriors) == 1:
                warrior_results[w.name] = "win"
            elif w.alive and len(alive) == 1 and len(self.warriors) > 1:
                warrior_results[w.name] = "win"
            elif not w.alive:
                warrior_results[w.name] = "loss"
            else:
                warrior_results[w.name] = "draw"

        if len(self.warriors) == 1:
            winner = self.warriors[0].name if self.warriors[0].alive else None
            reason = "single warrior survived" if winner else "warrior died"
        elif len(alive) == 1:
            winner = alive[0]
            reason = f"{', '.join(dead)} died"
        elif len(alive) == 0:
            winner = None
            reason = "all warriors died simultaneously"
        else:
            winner = None
            reason = f"draw after {self.cycle} cycles (time limit)"

        return BattleResult(
            winner=winner,
            survivors=alive,
            rounds=1,
            cycles=self.cycle,
            reason=reason,
            warrior_results=warrior_results,
        )


# Convenience class for loading warriors from source
class Warrior:
    """A convenience wrapper for loading and holding warrior source."""

    def __init__(self, name: str, source: str):
        from core_war.parser import RedcodeParser
        self.name = name
        self.source = source
        self._parsed: Optional[ParsedWarrior] = None
        self._parser = RedcodeParser()

    def parse(self) -> ParsedWarrior:
        """Parse the warrior source."""
        self._parsed = self._parser.parse(self.source, self.name)
        return self._parsed

    @property
    def parsed(self) -> ParsedWarrior:
        if self._parsed is None:
            self.parse()
        return self._parsed  # type: ignore