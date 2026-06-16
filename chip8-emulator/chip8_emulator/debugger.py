"""CHIP-8 debugger — step-through debugging with register/memory inspection."""

from __future__ import annotations

import sys
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cpu import CPU


class Debugger:
    """Interactive debugger for the CHIP-8 CPU.

    Provides step-by-step execution with register dumps, memory
    inspection, breakpoints, and opcode tracing.
    """

    def __init__(self, cpu: "CPU") -> None:
        self.cpu = cpu
        self._breakpoints: List[int] = []
        self._trace: List[str] = []
        self._trace_enabled: bool = False
        self._step_count: int = 0

    # ------------------------------------------------------------------
    # Breakpoints
    # ------------------------------------------------------------------

    def add_breakpoint(self, addr: int) -> None:
        """Add a breakpoint at *addr*."""
        if addr not in self._breakpoints:
            self._breakpoints.append(addr)
            self._breakpoints.sort()

    def remove_breakpoint(self, addr: int) -> None:
        """Remove a breakpoint at *addr*."""
        self._breakpoints = [bp for bp in self._breakpoints if bp != addr]

    def clear_breakpoints(self) -> None:
        """Remove all breakpoints."""
        self._breakpoints.clear()

    def list_breakpoints(self) -> List[int]:
        """Return sorted list of current breakpoints."""
        return list(self._breakpoints)

    def should_break(self) -> bool:
        """Check if the CPU is at a breakpoint."""
        return self.cpu.pc in self._breakpoints

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------

    def enable_trace(self) -> None:
        """Enable opcode tracing."""
        self._trace_enabled = True

    def disable_trace(self) -> None:
        """Disable opcode tracing."""
        self._trace_enabled = False

    def get_trace(self) -> List[str]:
        """Return the current trace log."""
        return list(self._trace)

    def clear_trace(self) -> None:
        """Clear the trace log."""
        self._trace.clear()

    def log_trace(self, opcode: int, description: str) -> None:
        """Log an opcode execution if tracing is enabled."""
        if self._trace_enabled:
            self._trace.append(
                f"[{self._step_count:06d}] {self.cpu.pc - 2:04X}: "
                f"{opcode:04X} {description}"
            )

    # ------------------------------------------------------------------
    # Stepping with breakpoints
    # ------------------------------------------------------------------

    def step(self) -> int:
        """Execute one instruction via CPU.step(). Returns the opcode executed."""
        opcode = self.cpu.step()

        # Log trace if enabled
        if self._trace_enabled:
            from .cli import _disassemble_opcode
            desc = _disassemble_opcode(opcode)
            pc_addr = self.cpu.pc - 2
            self._trace.append(
                f"[{self._step_count:06d}] {pc_addr:04X}: {opcode:04X} {desc}"
            )

        self._step_count += 1
        return opcode

    def run_until_break(self, max_cycles: int = 100000) -> int:
        """Run until a breakpoint is hit or *max_cycles* exceeded.

        Returns the number of cycles executed.
        """
        count = 0
        while count < max_cycles:
            self.step()
            count += 1
            if self.should_break():
                break
        return count

    # ------------------------------------------------------------------
    # State inspection
    # ------------------------------------------------------------------

    def dump_registers(self) -> str:
        """Return a formatted string of all CPU registers."""
        lines = []
        lines.append(f"PC: {self.cpu.pc:04X}  I: {self.cpu.I:04X}  SP: {self.cpu.sp}")
        for i in range(0, 16, 4):
            row = "  ".join(f"V{j:X}: {self.cpu.V[j]:02X}" for j in range(i, i + 4))
            lines.append(row)
        lines.append(f"DT: {self.cpu.dt.get():02X}  ST: {self.cpu.st.get():02X}")
        return "\n".join(lines)

    def dump_stack(self) -> str:
        """Return a formatted string of the call stack."""
        lines = [f"SP: {self.cpu.sp}"]
        for i in range(self.cpu.sp):
            lines.append(f"  [{i}] {self.cpu.stack[i]:04X}")
        return "\n".join(lines)

    def dump_memory(self, start: int, length: int = 16) -> str:
        """Hex-dump *length* bytes from *start*."""
        lines = []
        for offset in range(0, length, 16):
            addr = start + offset
            chunk = min(16, length - offset)
            bytes_str = " ".join(
                f"{self.cpu.memory.read(addr + j):02X}" for j in range(chunk)
            )
            ascii_str = "".join(
                chr(self.cpu.memory.read(addr + j))
                if 32 <= self.cpu.memory.read(addr + j) < 127
                else "."
                for j in range(chunk)
            )
            lines.append(f"  {addr:04X}: {bytes_str:<48s} {ascii_str}")
        return "\n".join(lines)

    def dump_display(self) -> str:
        """Return the display as an ASCII rendering."""
        return self.cpu.display.render(on="█", off="·")

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Debugger(pc={self.cpu.pc:04X}, breakpoints={len(self._breakpoints)})"