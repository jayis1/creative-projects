"""Execution tracer for the RISC-V emulator.

Records instruction-by-instruction execution traces with register states.
Supports filtering by address range, register changes, and conditional tracing.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from .cpu import CPU


class TraceEntry:
    """A single trace entry capturing CPU state at one instruction."""
    __slots__ = ("pc", "insn", "regs_before", "regs_after", "insn_name")

    def __init__(self, pc: int, insn: int, regs_before: List[int],
                 regs_after: List[int], insn_name: str = ""):
        self.pc = pc
        self.insn = insn
        self.regs_before = list(regs_before)
        self.regs_after = list(regs_after)
        self.insn_name = insn_name

    def changed_regs(self) -> List[int]:
        """Return indices of registers that changed."""
        result = []
        for i in range(32):
            if self.regs_before[i] != self.regs_after[i]:
                result.append(i)
        return result

    def __repr__(self) -> str:
        changes = self.changed_regs()
        reg_str = " ".join(
            f"x{i}({CPU.REG_NAMES[i]}):0x{self.regs_after[i]:08x}"
            for i in changes
        ) if changes else "(no reg change)"
        return f"0x{self.pc:08x}: 0x{self.insn:08x}  {reg_str}"


class Tracer:
    """Execution tracer that records instruction traces.

    Supports:
      - Full trace recording
      - Address-range filtering
      - Register-change-only mode
      - Max entry limit with ring-buffer behavior
    """

    def __init__(self, max_entries: int = 100000):
        self.entries: List[TraceEntry] = []
        self.max_entries = max_entries
        self._active = False
        self._filter_addrs: Optional[Set[int]] = None
        self._filter_range: Optional[Tuple[int, int]] = None
        self._changes_only = False

    def start(self) -> None:
        """Start tracing."""
        self._active = True

    def stop(self) -> None:
        """Stop tracing."""
        self._active = False

    def set_address_filter(self, addrs: Optional[Set[int]] = None,
                          addr_range: Optional[Tuple[int, int]] = None) -> None:
        """Set address filter. Only trace instructions at specified addresses or within range."""
        self._filter_addrs = addrs
        self._filter_range = addr_range

    def set_changes_only(self, enabled: bool = True) -> None:
        """Only record entries where at least one register changed."""
        self._changes_only = enabled

    def record(self, entry: TraceEntry) -> None:
        """Record a trace entry."""
        if not self._active:
            return
        # Apply filters
        if self._filter_addrs is not None and entry.pc not in self._filter_addrs:
            return
        if self._filter_range is not None:
            lo, hi = self._filter_range
            if not (lo <= entry.pc <= hi):
                return
        if self._changes_only and not entry.changed_regs():
            return
        # Ring buffer behavior
        if len(self.entries) >= self.max_entries:
            self.entries.pop(0)
        self.entries.append(entry)

    def clear(self) -> None:
        """Clear all trace entries."""
        self.entries.clear()

    def dump(self, last_n: Optional[int] = None) -> str:
        """Dump trace as a string. If last_n, only show the last N entries."""
        entries = self.entries[-last_n:] if last_n else self.entries
        lines = [f"=== Trace ({len(entries)} entries) ==="]
        for e in entries:
            lines.append(str(e))
        return "\n".join(lines)

    def to_csv(self, path: str) -> None:
        """Export trace to CSV file."""
        import csv
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["pc", "insn", "insn_name", "changed_regs",
                           "reg_values_after"])
            for e in self.entries:
                changes = e.changed_regs()
                reg_str = " ".join(f"x{i}:0x{e.regs_after[i]:08x}" for i in changes)
                writer.writerow([
                    f"0x{e.pc:08x}", f"0x{e.insn:08x}", e.insn_name,
                    ",".join(str(i) for i in changes), reg_str
                ])

    def stats(self) -> Dict[str, int]:
        """Return trace statistics."""
        addr_freq: Dict[int, int] = {}
        for e in self.entries:
            addr_freq[e.pc] = addr_freq.get(e.pc, 0) + 1
        return {
            "total_entries": len(self.entries),
            "unique_addresses": len(addr_freq),
            "max_address": max(addr_freq) if addr_freq else 0,
            "min_address": min(addr_freq) if addr_freq else 0,
        }