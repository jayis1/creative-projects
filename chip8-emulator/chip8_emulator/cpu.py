"""CHIP-8 CPU — fetch-decode-execute loop with all 35 standard opcodes."""

from __future__ import annotations

import logging
import random
from typing import List, Optional

from .display import Display
from .keypad import Keypad
from .memory import Memory, PROGRAM_START
from .opcodes import OpcodeTable
from .sound import SoundTimer
from .timer import DelayTimer

logger = logging.getLogger(__name__)

STACK_SIZE = 16  # Standard CHIP-8 call stack depth
NUM_REGISTERS = 16  # V0–VF


class CpuError(Exception):
    """Raised on invalid CPU state or unhandled opcode."""


class CPU:
    """CHIP-8 central processing unit.

    Attributes:
        V: 16 general-purpose 8-bit registers (V0–VF).
        I: 16-bit address register.
        pc: Program counter.
        sp: Stack pointer.
        stack: 16-level return address stack.
        dt: Delay timer.
        st: Sound timer.
    """

    def __init__(
        self,
        memory: Optional[Memory] = None,
        display: Optional[Display] = None,
        keypad: Optional[Keypad] = None,
    ) -> None:
        self.memory = memory or Memory()
        self.display = display or Display()
        self.keypad = keypad or Keypad()

        # Registers
        self.V: List[int] = [0] * NUM_REGISTERS  # V0–VF
        self.I: int = 0  # Address register
        self.pc: int = PROGRAM_START  # Program counter
        self.sp: int = 0  # Stack pointer (next free slot)
        self.stack: List[int] = [0] * STACK_SIZE

        # Timers
        self.dt = DelayTimer()
        self.st = SoundTimer()

        # Opcode dispatch table
        self._opcodes = OpcodeTable(self)

        # Current opcode (set during fetch, used by handlers)
        self._opcode: int = 0

        # State
        self._running: bool = False
        self._rng = random.Random()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_rom(self, data: bytes, offset: int = PROGRAM_START) -> None:
        """Load a ROM into memory and reset the CPU."""
        self.memory.load_rom(data, offset)
        self.reset()

    def load_rom_from_file(self, path: str, offset: int = PROGRAM_START) -> None:
        """Load a ROM from file and reset the CPU."""
        self.memory.load_rom_from_file(path, offset)
        self.reset()

    def reset(self) -> None:
        """Reset all CPU state (registers, stack, timers, display)."""
        self.V = [0] * NUM_REGISTERS
        self.I = 0
        self.pc = PROGRAM_START
        self.sp = 0
        self.stack = [0] * STACK_SIZE
        self.dt.set(0)
        self.st.set(0)
        self.display.clear()
        self._running = False

    def step(self) -> None:
        """Fetch, decode, and execute a single instruction."""
        self._opcode = self._fetch()
        self._decode_and_execute(self._opcode)

    def run(self, cycles: int = 0) -> None:
        """Run *cycles* instruction cycles (0 = run until halted)."""
        self._running = True
        count = 0
        while self._running:
            self.step()
            count += 1
            if cycles > 0 and count >= cycles:
                break

    def halt(self) -> None:
        """Stop the CPU."""
        self._running = False

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def _fetch(self) -> int:
        """Fetch a 2-byte opcode from memory at PC, incrementing PC."""
        if self.pc + 1 >= len(self.memory):
            raise CpuError(f"PC {self.pc:#06x} out of memory bounds")
        opcode = self.memory.read_word(self.pc)
        self.pc += 2
        return opcode

    # ------------------------------------------------------------------
    # Decode helpers
    # ------------------------------------------------------------------

    def _decode_and_execute(self, opcode: int) -> None:
        """Decode *opcode* and dispatch to the appropriate handler."""
        prefix = (opcode >> 12) & 0xF
        if prefix == 0x8:
            key = 0x8000 | (opcode & 0xF)
            handler = self._opcodes._table.get(key)
            if handler is None:
                raise CpuError(f"Unknown 8-prefixed opcode: {opcode:04X}")
            handler()
        elif prefix == 0xE:
            key = 0xE000 | (opcode & 0xFF)
            handler = self._opcodes._table.get(key)
            if handler is None:
                raise CpuError(f"Unknown E-prefixed opcode: {opcode:04X}")
            handler()
        elif prefix == 0xF:
            key = 0xF000 | (opcode & 0xFF)
            handler = self._opcodes._table.get(key)
            if handler is None:
                raise CpuError(f"Unknown F-prefixed opcode: {opcode:04X}")
            handler()
        elif prefix == 0x0:
            # 0-prefixed: need exact match for 00E0 and 00EE
            if opcode == 0x00E0:
                self.op_00E0()
            elif opcode == 0x00EE:
                self.op_00EE()
            else:
                self.op_0NNN()
        else:
            handler = self._opcodes._table.get(prefix)
            if handler is None:
                raise CpuError(f"Unknown opcode: {opcode:04X}")
            handler()

    # ------------------------------------------------------------------
    # Handy opcode field extractors
    # ------------------------------------------------------------------

    @property
    def _x(self) -> int:
        """Second nibble of current opcode (register index)."""
        return (self._opcode >> 8) & 0xF

    @property
    def _y(self) -> int:
        """Third nibble of current opcode (register index)."""
        return (self._opcode >> 4) & 0xF

    @property
    def _nnn(self) -> int:
        """Lower 12 bits of current opcode (address)."""
        return self._opcode & 0x0FFF

    @property
    def _kk(self) -> int:
        """Lower byte of current opcode (immediate value)."""
        return self._opcode & 0xFF

    @property
    def _n(self) -> int:
        """Fourth nibble of current opcode (nibble value)."""
        return self._opcode & 0xF

    # ------------------------------------------------------------------
    # Opcode handlers — 0-prefixed
    # ------------------------------------------------------------------

    def op_00E0(self) -> None:
        """00E0 — CLS. Clear the display."""
        self.display.clear()

    def op_00EE(self) -> None:
        """00EE — RET. Return from subroutine."""
        self._ret()

    def op_0NNN(self) -> None:
        """0NNN — SYS addr. Machine code call (ignored on modern systems)."""
        logger.debug("Ignoring machine code call: %04X", self._opcode)

    # ------------------------------------------------------------------
    # Opcode handlers — 1-prefixed
    # ------------------------------------------------------------------

    def op_1xxx(self) -> None:
        """1NNN — JP addr."""
        self.pc = self._nnn

    # ------------------------------------------------------------------
    # Opcode handlers — 2-prefixed
    # ------------------------------------------------------------------

    def op_2xxx(self) -> None:
        """2NNN — CALL addr."""
        self._call(self._nnn)

    # ------------------------------------------------------------------
    # Opcode handlers — 3-prefixed
    # ------------------------------------------------------------------

    def op_3xxx(self) -> None:
        """3xkk — SE Vx, byte. Skip next if Vx == kk."""
        if self.V[self._x] == self._kk:
            self.pc += 2

    # ------------------------------------------------------------------
    # Opcode handlers — 4-prefixed
    # ------------------------------------------------------------------

    def op_4xxx(self) -> None:
        """4xkk — SNE Vx, byte. Skip next if Vx != kk."""
        if self.V[self._x] != self._kk:
            self.pc += 2

    # ------------------------------------------------------------------
    # Opcode handlers — 5-prefixed
    # ------------------------------------------------------------------

    def op_5xxx(self) -> None:
        """5xy0 — SE Vx, Vy. Skip next if Vx == Vy."""
        if self.V[self._x] == self.V[self._y]:
            self.pc += 2

    # ------------------------------------------------------------------
    # Opcode handlers — 6-prefixed
    # ------------------------------------------------------------------

    def op_6xxx(self) -> None:
        """6xkk — LD Vx, byte."""
        self.V[self._x] = self._kk

    # ------------------------------------------------------------------
    # Opcode handlers — 7-prefixed
    # ------------------------------------------------------------------

    def op_7xxx(self) -> None:
        """7xkk — ADD Vx, byte. Vx = Vx + kk (no carry flag)."""
        self.V[self._x] = (self.V[self._x] + self._kk) & 0xFF

    # ------------------------------------------------------------------
    # Opcode handlers — 8-prefixed
    # ------------------------------------------------------------------

    def op_8xy0(self) -> None:
        """8xy0 — LD Vx, Vy."""
        self.V[self._x] = self.V[self._y]

    def op_8xy1(self) -> None:
        """8xy1 — OR Vx, Vy."""
        self.V[self._x] = self.V[self._x] | self.V[self._y]

    def op_8xy2(self) -> None:
        """8xy2 — AND Vx, Vy."""
        self.V[self._x] = self.V[self._x] & self.V[self._y]

    def op_8xy3(self) -> None:
        """8xy3 — XOR Vx, Vy."""
        self.V[self._x] = self.V[self._x] ^ self.V[self._y]

    def op_8xy4(self) -> None:
        """8xy4 — ADD Vx, Vy. VF = carry."""
        result = self.V[self._x] + self.V[self._y]
        self.V[self._x] = result & 0xFF
        self.V[0xF] = 1 if result > 0xFF else 0

    def op_8xy5(self) -> None:
        """8xy5 — SUB Vx, Vy. VF = NOT borrow."""
        flag = 1 if self.V[self._x] >= self.V[self._y] else 0
        self.V[self._x] = (self.V[self._x] - self.V[self._y]) & 0xFF
        self.V[0xF] = flag

    def op_8xy6(self) -> None:
        """8xy6 — SHR Vx {, Vy}. VF = LSB; Vx >>= 1.

        Uses CHIP-48 convention (shift Vx, not Vy).
        """
        lsb = self.V[self._x] & 1
        self.V[self._x] = self.V[self._x] >> 1
        self.V[0xF] = lsb

    def op_8xy7(self) -> None:
        """8xy7 — SUBN Vx, Vy. VF = NOT borrow."""
        flag = 1 if self.V[self._y] >= self.V[self._x] else 0
        self.V[self._x] = (self.V[self._y] - self.V[self._x]) & 0xFF
        self.V[0xF] = flag

    def op_8xyE(self) -> None:
        """8xyE — SHL Vx {, Vy}. VF = MSB; Vx <<= 1.

        Uses CHIP-48 convention (shift Vx, not Vy).
        """
        msb = (self.V[self._x] >> 7) & 1
        self.V[self._x] = (self.V[self._x] << 1) & 0xFF
        self.V[0xF] = msb

    # ------------------------------------------------------------------
    # Opcode handlers — 9-prefixed
    # ------------------------------------------------------------------

    def op_9xxx(self) -> None:
        """9xy0 — SNE Vx, Vy. Skip next if Vx != Vy."""
        if self.V[self._x] != self.V[self._y]:
            self.pc += 2

    # ------------------------------------------------------------------
    # Opcode handlers — A-prefixed
    # ------------------------------------------------------------------

    def op_Axxx(self) -> None:
        """ANNN — LD I, addr."""
        self.I = self._nnn

    # ------------------------------------------------------------------
    # Opcode handlers — B-prefixed
    # ------------------------------------------------------------------

    def op_Bxxx(self) -> None:
        """BNNN — JP V0, addr. PC = NNN + V0."""
        self.pc = (self._nnn + self.V[0]) & 0xFFF

    # ------------------------------------------------------------------
    # Opcode handlers — C-prefixed
    # ------------------------------------------------------------------

    def op_Cxxx(self) -> None:
        """Cxkk — RND Vx, byte. Vx = random_byte & kk."""
        self.V[self._x] = self._rng.randint(0, 255) & self._kk

    # ------------------------------------------------------------------
    # Opcode handlers — D-prefixed
    # ------------------------------------------------------------------

    def op_Dxxx(self) -> None:
        """Dxyn — DRW Vx, Vy, nibble. Draw sprite at (Vx, Vy)."""
        n = self._n
        vx = self.V[self._x]
        vy = self.V[self._y]

        # Read n bytes of sprite data starting at I
        sprite_data = bytes(self.memory.read(self.I + i) for i in range(n))
        collision = self.display.draw_sprite(vx, vy, sprite_data)
        self.V[0xF] = 1 if collision else 0

    # ------------------------------------------------------------------
    # Opcode handlers — E-prefixed
    # ------------------------------------------------------------------

    def op_Ex9E(self) -> None:
        """Ex9E — SKP Vx. Skip if key Vx is pressed."""
        if self.keypad.is_pressed(self.V[self._x] & 0xF):
            self.pc += 2

    def op_ExA1(self) -> None:
        """ExA1 — SKNP Vx. Skip if key Vx is NOT pressed."""
        if not self.keypad.is_pressed(self.V[self._x] & 0xF):
            self.pc += 2

    # ------------------------------------------------------------------
    # Opcode handlers — F-prefixed
    # ------------------------------------------------------------------

    def op_Fx07(self) -> None:
        """Fx07 — LD Vx, DT."""
        self.V[self._x] = self.dt.get()

    def op_Fx0A(self) -> None:
        """Fx0A — LD Vx, K. Wait for key press."""
        # In a real emulator with event loop, this would block.
        # For headless mode, we scan pressed keys.
        for key in range(16):
            if self.keypad.is_pressed(key):
                self.V[self._x] = key
                return
        # No key pressed — back up PC to loop on this instruction
        self.pc -= 2

    def op_Fx15(self) -> None:
        """Fx15 — LD DT, Vx."""
        self.dt.set(self.V[self._x])

    def op_Fx18(self) -> None:
        """Fx18 — LD ST, Vx."""
        self.st.set(self.V[self._x])

    def op_Fx1E(self) -> None:
        """Fx1E — ADD I, Vx."""
        self.I = (self.I + self.V[self._x]) & 0xFFF

    def op_Fx29(self) -> None:
        """Fx29 — LD F, Vx. Set I to sprite location for digit Vx."""
        self.I = self.memory.font_sprite_addr(self.V[self._x] & 0xF)

    def op_Fx33(self) -> None:
        """Fx33 — LD B, Vx. Store BCD of Vx at I, I+1, I+2."""
        value = self.V[self._x]
        self.memory.write(self.I, value // 100)
        self.memory.write(self.I + 1, (value % 100) // 10)
        self.memory.write(self.I + 2, value % 10)

    def op_Fx55(self) -> None:
        """Fx55 — LD [I], Vx. Store V0..Vx in memory starting at I."""
        x = self._x
        for i in range(x + 1):
            self.memory.write(self.I + i, self.V[i])
        # Modern convention: I is NOT incremented

    def op_Fx65(self) -> None:
        """Fx65 — LD Vx, [I]. Load V0..Vx from memory starting at I."""
        x = self._x
        for i in range(x + 1):
            self.V[i] = self.memory.read(self.I + i)
        # Modern convention: I is NOT incremented

    # ------------------------------------------------------------------
    # Stack helpers
    # ------------------------------------------------------------------

    def _call(self, addr: int) -> None:
        """Push return address and jump to *addr*."""
        if self.sp >= STACK_SIZE:
            raise CpuError("Stack overflow")
        self.stack[self.sp] = self.pc
        self.sp += 1
        self.pc = addr

    def _ret(self) -> None:
        """Return from subroutine."""
        if self.sp <= 0:
            raise CpuError("Stack underflow")
        self.sp -= 1
        self.pc = self.stack[self.sp]

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"CPU(pc={self.pc:#06x}, I={self.I:#06x}, "
            f"sp={self.sp}, V={[hex(v) for v in self.V]})"
        )