"""Execution profiler for the RISC-V emulator.

Tracks instruction frequency, hot addresses, and execution statistics.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .memory import Memory


class Profiler:
    """Execution profiler that tracks instruction-level statistics.

    Attributes:
        instruction_counts: Dict mapping instruction name -> count.
        address_counts: Dict mapping address -> count.
        total_instructions: Total instructions executed.
        start_cycle: Cycle counter when profiling started.
    """

    def __init__(self):
        self.instruction_counts: Dict[str, int] = {}
        self.address_counts: Dict[int, int] = {}
        self.total_instructions: int = 0
        self.start_cycle: int = 0
        self._active = False

    def start(self) -> None:
        """Start profiling."""
        self._active = True
        self.start_cycle = self.total_instructions

    def stop(self) -> None:
        """Stop profiling."""
        self._active = False

    def record(self, addr: int, insn_name: str) -> None:
        """Record execution of one instruction."""
        if not self._active:
            return
        self.instruction_counts[insn_name] = self.instruction_counts.get(insn_name, 0) + 1
        self.address_counts[addr] = self.address_counts.get(addr, 0) + 1
        self.total_instructions += 1

    def reset(self) -> None:
        """Reset all profiling data."""
        self.instruction_counts.clear()
        self.address_counts.clear()
        self.total_instructions = 0

    def top_instructions(self, n: int = 10) -> List[Tuple[str, int]]:
        """Return top N most-executed instructions."""
        return sorted(self.instruction_counts.items(), key=lambda x: -x[1])[:n]

    def top_addresses(self, n: int = 10) -> List[Tuple[int, int]]:
        """Return top N most-executed addresses."""
        return sorted(self.address_counts.items(), key=lambda x: -x[1])[:n]

    def summary(self, memory: Optional[Memory] = None) -> str:
        """Generate a profiling summary report."""
        lines = [f"=== Profiler Summary ==="]
        lines.append(f"Total instructions: {self.total_instructions}")
        lines.append("")
        lines.append("Top instructions:")
        for name, count in self.top_instructions(15):
            pct = 100.0 * count / max(self.total_instructions, 1)
            lines.append(f"  {name:>12s}: {count:8d} ({pct:5.1f}%)")
        lines.append("")
        lines.append("Hot addresses:")
        for addr, count in self.top_addresses(10):
            line = f"  0x{addr:08x}: {count:8d}"
            if memory:
                try:
                    insn = memory.read_word(addr)
                    line += f"  (insn=0x{insn:08x})"
                except Exception:
                    pass
            lines.append(line)
        return "\n".join(lines)