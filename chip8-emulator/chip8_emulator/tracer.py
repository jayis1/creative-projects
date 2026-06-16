"""CHIP-8 execution tracer and profiler.

Collects runtime statistics during execution for analysis:
- Opcode frequency counts
- Address access patterns (hot paths)
- Register usage statistics
- Memory access patterns
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cpu import CPU
from .opcodes import OpcodeTable


# Map opcode keys to human-readable names
MNEMONIC_NAMES: Dict[int, str] = {
    0x00E0: "CLS", 0x00EE: "RET", 0x1: "JP", 0x2: "CALL",
    0x3: "SE byte", 0x4: "SNE byte", 0x5: "SE reg", 0x6: "LD byte",
    0x7: "ADD byte", 0x9: "SNE reg", 0xA: "LD I", 0xB: "JP V0",
    0xC: "RND", 0xD: "DRW",
    0x8000: "LD reg", 0x8001: "OR", 0x8002: "AND", 0x8003: "XOR",
    0x8004: "ADD reg", 0x8005: "SUB", 0x8006: "SHR", 0x8007: "SUBN",
    0x800E: "SHL",
    0xE09E: "SKP", 0xE0A1: "SKNP",
    0xF007: "LD Vx DT", 0xF00A: "LD Vx K", 0xF015: "LD DT Vx",
    0xF018: "LD ST Vx", 0xF01E: "ADD I Vx", 0xF029: "LD F",
    0xF030: "LD HF", 0xF033: "LD B", 0xF055: "LD [I]", 0xF065: "LD Vx [I]",
    0xF075: "LD R", 0xF085: "LD Vx R",
}


def _classify_opcode(opcode: int) -> str:
    """Classify an opcode into a human-readable category."""
    prefix = (opcode >> 12) & 0xF
    if prefix == 0:
        if opcode == 0x00E0: return "CLS"
        if opcode == 0x00EE: return "RET"
        if opcode == 0x00FD: return "EXIT"
        if opcode == 0x00FF: return "EXMODE"
        if opcode == 0x00FB: return "SCROLL_LEFT"
        if opcode == 0x00FC: return "SCROLL_RIGHT"
        if (opcode & 0xFFF0) == 0x00C0: return "SCROLL_DOWN"
        return "SYS"
    if prefix == 8:
        return MNEMONIC_NAMES.get(0x8000 | (opcode & 0xF), f"8xy{opcode & 0xF:X}")
    if prefix == 0xE:
        kk = opcode & 0xFF
        return MNEMONIC_NAMES.get(0xE000 | kk, f"E{opcode >> 8:X}{kk:02X}")
    if prefix == 0xF:
        kk = opcode & 0xFF
        return MNEMONIC_NAMES.get(0xF000 | kk, f"F{opcode >> 8 & 0xF:X}{kk:02X}")
    return MNEMONIC_NAMES.get(prefix, f"? ({opcode:04X})")


@dataclass
class TraceEntry:
    """A single trace entry recording one instruction execution."""

    cycle: int
    pc: int
    opcode: int
    mnemonic: str


@dataclass
class ProfileStats:
    """Aggregated profiling statistics."""

    total_cycles: int = 0
    opcode_counts: Counter = field(default_factory=Counter)
    address_counts: Counter = field(default_factory=Counter)
    register_writes: Counter = field(default_factory=Counter)
    memory_writes: Counter = field(default_factory=Counter)
    draw_calls: int = 0
    key_polls: int = 0
    call_stack_depths: List[int] = field(default_factory=list)

    def top_opcodes(self, n: int = 10) -> List[Tuple[str, int]]:
        """Return the top N most frequent opcodes."""
        return self.opcode_counts.most_common(n)

    def top_addresses(self, n: int = 10) -> List[Tuple[int, int]]:
        """Return the top N most frequently executed addresses."""
        return self.address_counts.most_common(n)

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""
        return {
            "total_cycles": self.total_cycles,
            "opcode_counts": dict(self.opcode_counts.most_common()),
            "top_addresses": [
                {"address": f"0x{addr:04X}", "hits": count}
                for addr, count in self.address_counts.most_common(20)
            ],
            "draw_calls": self.draw_calls,
            "key_polls": self.key_polls,
            "register_writes": dict(self.register_writes.most_common()),
            "memory_writes": dict(self.memory_writes.most_common(20)),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class Tracer:
    """Execution tracer that records instruction-level events.

    Attach to a CPU via ``on_step`` callback to collect a trace log
    during execution.

    Usage::

        from chip8_emulator import CPU
        from chip8_emulator.tracer import Tracer

        cpu = CPU()
        tracer = Tracer(cpu)
        cpu.load_rom_from_file("maze.ch8")
        cpu.run(cycles=1000)
        print(tracer.summary())
    """

    def __init__(self, cpu: CPU, *, max_entries: int = 0) -> None:
        """Initialize the tracer.

        Args:
            cpu: The CPU instance to trace.
            max_entries: Maximum trace entries to keep (0 = unlimited).
        """
        self.cpu = cpu
        self.max_entries = max_entries
        self._trace: List[TraceEntry] = []
        self._stats = ProfileStats()
        self._prev_vx = [0] * 16  # Track register changes

    def on_step(self, cpu: CPU, opcode: int) -> None:
        """Callback for CPU on_step — records execution events."""
        entry = TraceEntry(
            cycle=cpu.cycles,
            pc=cpu.pc - 2,
            opcode=opcode,
            mnemonic=_classify_opcode(opcode),
        )

        # Track trace entries
        if self.max_entries == 0 or len(self._trace) < self.max_entries:
            self._trace.append(entry)

        # Update stats
        self._stats.total_cycles = cpu.cycles
        self._stats.opcode_counts[entry.mnemonic] += 1
        self._stats.address_counts[entry.pc] += 1

        # Track register writes
        for i in range(16):
            if cpu.V[i] != self._prev_vx[i]:
                self._stats.register_writes[f"V{i:X}"] += 1
                self._prev_vx[i] = cpu.V[i]

        # Track draw calls
        prefix = (opcode >> 12) & 0xF
        if prefix == 0xD:
            self._stats.draw_calls += 1

        # Track key polls
        if opcode & 0xFFF in (0x9E, 0xA1) and (opcode >> 12) == 0xE:
            self._stats.key_polls += 1

    def attach(self) -> None:
        """Attach this tracer to the CPU's on_step callback."""
        self.cpu._on_step = self.on_step

    def detach(self) -> None:
        """Detach the tracer from the CPU."""
        self.cpu._on_step = None

    def clear(self) -> None:
        """Clear all trace data."""
        self._trace.clear()
        self._stats = ProfileStats()
        self._prev_vx = list(self.cpu.V)

    @property
    def stats(self) -> ProfileStats:
        """Return the aggregated profiling statistics."""
        return self._stats

    @property
    def trace(self) -> List[TraceEntry]:
        """Return the raw trace log."""
        return list(self._trace)

    def summary(self) -> str:
        """Generate a human-readable profiling summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("CHIP-8 Execution Profile")
        lines.append("=" * 60)
        lines.append(f"Total cycles: {self._stats.total_cycles}")
        lines.append(f"Draw calls:   {self._stats.draw_calls}")
        lines.append(f"Key polls:    {self._stats.key_polls}")
        lines.append("")

        # Top opcodes
        lines.append("Top Opcodes:")
        for name, count in self._stats.top_opcodes(15):
            pct = count / max(self._stats.total_cycles, 1) * 100
            bar = "█" * int(pct / 2)
            lines.append(f"  {name:<16s} {count:>6d} ({pct:5.1f}%) {bar}")

        # Top addresses
        lines.append("")
        lines.append("Hot Addresses (most executed):")
        for addr, count in self._stats.top_addresses(10):
            lines.append(f"  0x{addr:04X}: {count:>6d} hits")

        # Register usage
        if self._stats.register_writes:
            lines.append("")
            lines.append("Register Write Frequency:")
            for reg, count in self._stats.register_writes.most_common(16):
                lines.append(f"  {reg}: {count}")

        lines.append("=" * 60)
        return "\n".join(lines)