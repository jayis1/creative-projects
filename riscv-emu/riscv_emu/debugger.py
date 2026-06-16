"""Interactive debugger for the RISC-V emulator.

Provides a GDB-like command-line interface with:
  - Breakpoints and watchpoints
  - Single-step execution
  - Register and memory inspection/modification
  - Disassembly
  - Execution tracing
  - Reverse debugging (undo last N steps)
"""

from __future__ import annotations
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

from .cpu import CPU, CPUHalt, Trap
from .memory import Memory, MemoryError


class Debugger:
    """Interactive RISC-V debugger with GDB-like commands.

    Commands:
      s, step [N]        — Step N instructions (default 1)
      c, continue [N]    — Continue for N instructions (default unlimited)
      b, break ADDR      — Set breakpoint at address
      wb, watch ADDR     — Set watchpoint on address
      info b             — List breakpoints
      info w             — List watchpoints
      del N              — Delete breakpoint/watchpoint N
      r, regs            — Show registers
      pc                 — Show program counter
      m, mem ADDR [LEN]  — Hexdump memory
      wr ADDR VAL        — Write word to memory
      set REG VAL        — Set register value
      dis [ADDR] [N]     — Disassemble N instructions at ADDR
      bt, backtrace      — Show backtrace (if frame pointers available)
      trace [on|off]     — Enable/disable instruction tracing
      profile [on|off]   — Enable/disable profiling
      q, quit            — Exit debugger
      h, help            — Show help
    """

    # Breakpoint counter
    BP_NONE = 0
    BP_BREAK = 1
    BP_WATCH = 2

    def __init__(self, cpu: CPU, memory: Optional[Memory] = None):
        self.cpu = cpu
        self.memory = memory or cpu.memory
        self.breakpoints: Dict[int, Tuple[int, str]] = {}  # id -> (address, type)
        self.watchpoints: Dict[int, Tuple[int, str]] = {}  # id -> (address, description)
        self._next_id = 1
        self._tracing = False
        self._trace_log: List[str] = []
        self._profiling = False
        self._profile_data: Dict[int, int] = {}  # addr -> count
        self._history: List[dict] = []  # For undo
        self._max_history = 1000

    def _save_state(self) -> dict:
        """Save CPU state for undo."""
        return {
            "regs": list(self.cpu.regs),
            "pc": self.cpu.pc,
        }

    def _restore_state(self, state: dict) -> None:
        """Restore CPU state from saved state."""
        self.cpu.regs = list(state["regs"])
        self.cpu.pc = state["pc"]

    def add_breakpoint(self, addr: int) -> int:
        """Add a breakpoint, returns ID."""
        bp_id = self._next_id
        self.breakpoints[bp_id] = (addr, "break")
        self._next_id += 1
        return bp_id

    def add_watchpoint(self, addr: int, desc: str = "") -> int:
        """Add a watchpoint, returns ID."""
        wp_id = self._next_id
        self.watchpoints[wp_id] = (addr, desc or f"watch 0x{addr:08x}")
        self._next_id += 1
        return wp_id

    def delete_bp(self, bp_id: int) -> bool:
        """Delete a breakpoint or watchpoint by ID."""
        if bp_id in self.breakpoints:
            del self.breakpoints[bp_id]
            return True
        if bp_id in self.watchpoints:
            del self.watchpoints[bp_id]
            return True
        return False

    def _check_breakpoints(self) -> Optional[int]:
        """Check if PC matches any breakpoint. Returns breakpoint ID or None."""
        for bp_id, (addr, _) in self.breakpoints.items():
            if self.cpu.pc == addr:
                return bp_id
        return None

    def _check_watchpoints(self) -> List[int]:
        """Check watchpoints (basic: triggered on every step for now)."""
        return []  # Simplified — real watchpoints require memory access hooks

    def disassemble_one(self, addr: int) -> str:
        """Disassemble a single instruction at `addr`."""
        try:
            insn = self.memory.read_word(addr)
        except MemoryError:
            return f"0x{addr:08x}  ????????  <unreadable>"

        opcode = insn & 0x7F
        rd = (insn >> 7) & 0x1F
        funct3 = (insn >> 12) & 0x7
        rs1 = (insn >> 15) & 0x1F
        rs2 = (insn >> 20) & 0x1F
        funct7 = (insn >> 25) & 0x7F
        imm_i = (insn >> 20) & 0xFFF
        imm_s = ((insn >> 7) & 0x1F) | (((insn >> 25) & 0x7F) << 5)
        imm_u = insn & 0xFFFFF000
        rn = CPU.REG_NAMES

        def sext(v, bits):
            return v - (1 << bits) if v & (1 << (bits - 1)) else v

        if opcode == 0x37:  # LUI
            return f"0x{addr:08x}  {insn:08x}  lui {rn[rd]}, {sext(imm_u, 32)}"
        elif opcode == 0x17:  # AUIPC
            return f"0x{addr:08x}  {insn:08x}  auipc {rn[rd]}, {sext(imm_u, 32)}"
        elif opcode == 0x6F:  # JAL
            imm_j = sext(
                (((insn >> 21) & 0x3FF) << 1) | (((insn >> 20) & 0x1) << 11) |
                (((insn >> 12) & 0xFF) << 12) | (((insn >> 31) & 0x1) << 20),
                21
            )
            target = (addr + imm_j) & 0xFFFFFFFF
            return f"0x{addr:08x}  {insn:08x}  jal {rn[rd]}, 0x{target:08x}"
        elif opcode == 0x67:  # JALR
            return f"0x{addr:08x}  {insn:08x}  jalr {rn[rd]}, {rn[rs1]}, {sext(imm_i, 12)}"
        elif opcode == 0x63:  # Branch
            bnames = {0: "beq", 1: "bne", 4: "blt", 5: "bge", 6: "bltu", 7: "bgeu"}
            name = bnames.get(funct3, f"b?{funct3}")
            imm_b = sext(
                (((insn >> 8) & 0xF) << 1) | (((insn >> 7) & 0x1) << 11) |
                (((insn >> 25) & 0x3F) << 5) | (((insn >> 31) & 0x1) << 12),
                13
            )
            target = (addr + imm_b) & 0xFFFFFFFF
            return f"0x{addr:08x}  {insn:08x}  {name} {rn[rs1]}, {rn[rs2]}, 0x{target:08x}"
        elif opcode == 0x03:  # Load
            lnames = {0: "lb", 1: "lh", 2: "lw", 4: "lbu", 5: "lhu"}
            name = lnames.get(funct3, f"l?{funct3}")
            return f"0x{addr:08x}  {insn:08x}  {name} {rn[rd]}, {sext(imm_i, 12)}({rn[rs1]})"
        elif opcode == 0x23:  # Store
            snames = {0: "sb", 1: "sh", 2: "sw"}
            name = snames.get(funct3, f"s?{funct3}")
            return f"0x{addr:08x}  {insn:08x}  {name} {rn[rs2]}, {sext(imm_s, 12)}({rn[rs1]})"
        elif opcode == 0x13:  # I-type ALU
            inames = {0: "addi", 2: "slti", 3: "sltiu", 4: "xori", 6: "ori", 7: "andi"}
            if funct3 in inames:
                return f"0x{addr:08x}  {insn:08x}  {inames[funct3]} {rn[rd]}, {rn[rs1]}, {sext(imm_i, 12)}"
            elif funct3 == 1:
                shamt = (insn >> 20) & 0x1F
                return f"0x{addr:08x}  {insn:08x}  slli {rn[rd]}, {rn[rs1]}, {shamt}"
            elif funct3 == 5:
                shamt = (insn >> 20) & 0x1F
                name = "srai" if funct7 & 0x20 else "srli"
                return f"0x{addr:08x}  {insn:08x}  {name} {rn[rd]}, {rn[rs1]}, {shamt}"
        elif opcode == 0x33:  # R-type ALU
            rnames = {
                (0, 0): "add", (0, 0x20): "sub", (1, 0): "sll", (2, 0): "slt",
                (3, 0): "sltu", (4, 0): "xor", (5, 0): "srl", (5, 0x20): "sra",
                (6, 0): "or", (7, 0): "and",
            }
            name = rnames.get((funct3, funct7), f"r?{funct3}_{funct7}")
            return f"0x{addr:08x}  {insn:08x}  {name} {rn[rd]}, {rn[rs1]}, {rn[rs2]}"
        elif opcode == 0x0F:
            return f"0x{addr:08x}  {insn:08x}  fence"
        elif opcode == 0x73:
            if insn == 0x00000073:
                return f"0x{addr:08x}  {insn:08x}  ecall"
            elif insn == 0x00100073:
                return f"0x{addr:08x}  {insn:08x}  ebreak"
            else:
                return f"0x{addr:08x}  {insn:08x}  csr_*"
        return f"0x{addr:08x}  {insn:08x}  <unknown opcode 0x{opcode:02x}>"

    def step(self, n: int = 1) -> Tuple[int, bool]:
        """Step N instructions. Returns (instructions_executed, hit_breakpoint)."""
        count = 0
        for _ in range(n):
            bp = self._check_breakpoints()
            if bp:
                return count, True

            # Save state for undo
            if len(self._history) < self._max_history:
                self._history.append(self._save_state())

            try:
                self.cpu.step()
            except Trap as t:
                self.cpu._handle_trap(t)
            except CPUHalt:
                return count, False

            count += 1

            # Profiling
            if self._profiling:
                self._profile_data[self.cpu.pc] = self._profile_data.get(self.cpu.pc, 0) + 1

            # Tracing
            if self._tracing:
                self._trace_log.append(self.cpu.state_dump())

        return count, False

    def run_command(self, cmd: str) -> bool:
        """Run a debugger command. Returns False to exit the debugger loop."""
        cmd = cmd.strip()
        if not cmd:
            return True

        parts = cmd.split()
        verb = parts[0].lower()
        args = parts[1:]

        if verb in ("q", "quit", "exit"):
            return False

        elif verb in ("h", "help", "?"):
            print(self._help_text())

        elif verb in ("s", "step"):
            n = int(args[0]) if args else 1
            count, bp = self.step(n)
            print(f"Stepped {count} instruction(s)")
            if bp:
                bp_id = self._check_breakpoints()
                print(f"Breakpoint {bp_id} hit at 0x{self.cpu.pc:08x}")
            print(self.cpu.state_dump())

        elif verb in ("c", "continue"):
            max_steps = int(args[0]) if args else 1000000
            count = 0
            while count < max_steps:
                bp = self._check_breakpoints()
                if bp:
                    print(f"Breakpoint {bp} hit at 0x{self.cpu.pc:08x}")
                    break
                try:
                    self.cpu.step()
                except Trap as t:
                    self.cpu._handle_trap(t)
                    continue
                except CPUHalt:
                    print(f"CPU halted after {count} instructions")
                    break
                count += 1
                if self._profiling:
                    self._profile_data[self.cpu.pc] = self._profile_data.get(self.cpu.pc, 0) + 1
            print(f"Executed {count} instructions")
            print(self.cpu.state_dump())

        elif verb in ("b", "break", "bp"):
            addr = int(args[0], 0) if args else self.cpu.pc
            bp_id = self.add_breakpoint(addr)
            print(f"Breakpoint {bp_id} at 0x{addr:08x}")

        elif verb in ("wb", "watch"):
            addr = int(args[0], 0) if args else 0
            wp_id = self.add_watchpoint(addr)
            print(f"Watchpoint {wp_id} at 0x{addr:08x}")

        elif verb == "del":
            if not args:
                print("Usage: del <id>")
            else:
                bp_id = int(args[0])
                if self.delete_bp(bp_id):
                    print(f"Deleted breakpoint/watchpoint {bp_id}")
                else:
                    print(f"No breakpoint/watchpoint {bp_id}")

        elif verb == "info":
            if args and args[0] in ("b", "bp", "break"):
                for bp_id, (addr, _) in sorted(self.breakpoints.items()):
                    print(f"  {bp_id}: 0x{addr:08x}")
            elif args and args[0] in ("w", "watch"):
                for wp_id, (addr, desc) in sorted(self.watchpoints.items()):
                    print(f"  {wp_id}: 0x{addr:08x} ({desc})")
            else:
                print("info b — list breakpoints")
                print("info w — list watchpoints")

        elif verb in ("r", "regs"):
            print(self.cpu.state_dump())

        elif verb == "pc":
            print(f"PC: 0x{self.cpu.pc:08x}")

        elif verb in ("m", "mem", "memory"):
            if not args:
                print("Usage: mem <addr> [len]")
            else:
                addr = int(args[0], 0)
                length = int(args[1], 16) if len(args) > 1 else 64
                try:
                    print(self.memory.dump(addr, length))
                except MemoryError as e:
                    print(f"Error: {e}")

        elif verb == "wr":
            if len(args) < 2:
                print("Usage: wr <addr> <value>")
            else:
                addr = int(args[0], 0)
                val = int(args[1], 0)
                try:
                    self.memory.write_word(addr, val)
                    print(f"Wrote 0x{val:08x} to 0x{addr:08x}")
                except MemoryError as e:
                    print(f"Error: {e}")

        elif verb == "set":
            if len(args) < 2:
                print("Usage: set <reg> <value>")
            else:
                reg_name = args[0]
                value = int(args[1], 0)
                try:
                    idx = self.cpu.parse_register(reg_name) if hasattr(self.cpu, 'parse_register') else int(reg_name)
                    if 0 <= idx < 32:
                        self.cpu.set_reg(idx, value)
                        print(f"x{idx} ({CPU.REG_NAMES[idx]}) = 0x{value:08x}")
                    else:
                        print(f"Invalid register index: {idx}")
                except (ValueError, AttributeError) as e:
                    print(f"Error: {e}")

        elif verb in ("dis", "disassemble"):
            addr = int(args[0], 0) if args else self.cpu.pc
            n = int(args[1]) if len(args) > 1 else 10
            for i in range(n):
                print(self.disassemble_one(addr + i * 4))

        elif verb == "undo":
            if self._history:
                self._restore_state(self._history.pop())
                print(f"Restored state: PC = 0x{self.cpu.pc:08x}")
            else:
                print("No history to undo")

        elif verb == "trace":
            if not args or args[0] == "on":
                self._tracing = True
                print("Tracing enabled")
            elif args[0] == "off":
                self._tracing = False
                print("Tracing disabled")
            elif args[0] == "dump":
                for line in self._trace_log[-100:]:
                    print(line)
            else:
                print("Usage: trace [on|off|dump]")

        elif verb == "profile":
            if not args or args[0] == "on":
                self._profiling = True
                print("Profiling enabled")
            elif args[0] == "off":
                self._profiling = False
                print("Profiling disabled")
            elif args[0] == "report":
                if not self._profile_data:
                    print("No profile data. Enable profiling first.")
                else:
                    sorted_addrs = sorted(self._profile_data.items(), key=lambda x: -x[1])
                    print("Top 20 hot addresses:")
                    for addr, count in sorted_addrs[:20]:
                        print(f"  0x{addr:08x}: {count} hits  {self.disassemble_one(addr)}")
            else:
                print("Usage: profile [on|off|report]")

        else:
            print(f"Unknown command: {verb}. Type 'help' for commands.")

        return True

    def interactive(self) -> None:
        """Run the interactive debugger loop."""
        print("RISC-V Debugger. Type 'help' for commands.")
        print(self.cpu.state_dump())
        while True:
            try:
                cmd = input("(riscv-dbg) ").strip()
            except EOFError:
                break
            if not self.run_command(cmd):
                break

    @staticmethod
    def _help_text() -> str:
        return """RISC-V Debugger Commands:
  s, step [N]        — Step N instructions (default 1)
  c, continue [N]    — Continue for N instructions (default unlimited)
  b, break ADDR      — Set breakpoint at address
  wb, watch ADDR     — Set watchpoint on address
  info b             — List breakpoints
  info w             — List watchpoints
  del N              — Delete breakpoint/watchpoint N
  r, regs            — Show registers
  pc                 — Show program counter
  m, mem ADDR [LEN]  — Hexdump memory
  wr ADDR VAL        — Write word to memory
  set REG VAL        — Set register value
  dis [ADDR] [N]     — Disassemble N instructions at ADDR
  undo               — Undo last step
  trace [on|off|dump] — Instruction tracing
  profile [on|off|report] — Profiling
  q, quit            — Exit debugger
  h, help            — Show this help"""