"""CPU core for the RISC-V RV32I emulator.

Implements the full RV32I base integer instruction set plus Zicsr extension.
Handles fetch-decode-execute cycle, trap handling, and privilege modes.
"""

from __future__ import annotations
import struct
from typing import Dict, List, Optional, Tuple

from .memory import Memory, MemoryError
from .csrs import (
    CSRFile, CSRError,
    CSR_MSTATUS, CSR_MEPC, CSR_MCAUSE, CSR_MTVAL, CSR_MTVEC,
    CSR_MIE, CSR_MIP, CSR_MSCRATCH,
    MSTATUS_MIE, MSTATUS_MPIE, MSTATUS_MPP,
    CAUSE_MISALIGNED_FETCH, CAUSE_FETCH_ACCESS, CAUSE_ILLEGAL_INSN,
    CAUSE_BREAKPOINT, CAUSE_MISALIGNED_LOAD, CAUSE_LOAD_ACCESS,
    CAUSE_MISALIGNED_STORE, CAUSE_STORE_ACCESS,
    CAUSE_ECALL_U, CAUSE_ECALL_M,
)


class Trap(Exception):
    """Raised internally to signal a trap (exception or interrupt)."""
    def __init__(self, cause: int, tval: int = 0):
        self.cause = cause
        self.tval = tval


class CPUHalt(Exception):
    """Raised when the CPU executes a halt instruction or runs out of instructions."""
    pass


class CPU:
    """RISC-V RV32I CPU emulator.

    Attributes:
        regs: General-purpose registers x0-x31 (x0 always 0).
        pc: Program counter.
        csrs: Control and Status Register file.
        memory: Memory subsystem.
        priv: Current privilege level (0=User, 3=Machine).
    """

    # Privilege levels
    PRIV_U = 0
    PRIV_S = 1
    PRIV_M = 3

    NUM_REGS = 32

    # Register name map for debugging
    REG_NAMES = [
        "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
        "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
        "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
        "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
    ]

    def __init__(
        self,
        memory: Optional[Memory] = None,
        pc: int = 0x20000000,
        hart_id: int = 0,
    ):
        self.regs = [0] * self.NUM_REGS
        self.pc = pc
        self.csrs = CSRFile(hart_id)
        self.memory = memory or Memory()
        self.priv = self.PRIV_M
        self._halted = False
        self._instructions_executed = 0
        # Callback for ECALL
        self.ecall_callback = None
        # MMIO UART at 0x10000000 (qemu-virt style)
        self._uart_buf: List[int] = []

    def set_reg(self, rd: int, value: int) -> None:
        """Set register, keeping x0 hardwired to 0."""
        if rd != 0:
            self.regs[rd] = value & 0xFFFFFFFF

    def get_reg(self, rs: int) -> int:
        """Get register value (unsigned 32-bit)."""
        return self.regs[rs] & 0xFFFFFFFF

    def get_reg_signed(self, rs: int) -> int:
        """Get register value as signed 32-bit."""
        v = self.regs[rs] & 0xFFFFFFFF
        return v - 0x100000000 if v >= 0x80000000 else v

    @staticmethod
    def sign_extend(value: int, bits: int) -> int:
        """Sign-extend `value` from `bits` width to Python int."""
        if value & (1 << (bits - 1)):
            return value - (1 << bits)
        return value

    @staticmethod
    def mask32(value: int) -> int:
        """Mask to 32 bits."""
        return value & 0xFFFFFFFF

    def step(self) -> None:
        """Execute a single instruction. Raises Trap on exceptions, CPUHalt on stop."""
        if self._halted:
            raise CPUHalt("CPU is halted")

        # Fetch
        try:
            insn_word = self.memory.read_word(self.pc)
        except MemoryError as e:
            raise Trap(CAUSE_FETCH_ACCESS, self.pc)

        # Decode and Execute
        old_pc = self.pc
        try:
            self._execute(insn_word)
        except Trap:
            raise
        except Exception as e:
            raise Trap(CAUSE_ILLEGAL_INSN, insn_word)

        # x0 stays zero
        self.regs[0] = 0

        # Update counters
        self._instructions_executed += 1
        self.csrs.increment_counter(CSR_MIE, 0)  # no-op placeholder
        # Actually count cycle/instret
        self.csrs._regs[0xC00] = (self.csrs._regs.get(0xC00, 0) + 1) & 0xFFFFFFFF  # cycle
        self.csrs._regs[0xC02] = (self.csrs._regs.get(0xC02, 0) + 1) & 0xFFFFFFFF  # instret

        # If PC didn't change (no branch/jump), advance to next instruction
        if self.pc == old_pc:
            self.pc = (self.pc + 4) & 0xFFFFFFFF

    def run(self, max_instructions: int = 100_000) -> int:
        """Run up to max_instructions. Returns number of instructions executed."""
        count = 0
        while count < max_instructions:
            try:
                self.step()
                count += 1
            except Trap as t:
                try:
                    self._handle_trap(t)
                except CPUHalt:
                    break
            except CPUHalt:
                break
        return count

    def _handle_trap(self, trap: Trap) -> None:
        """Handle a trap: update CSRs and jump to trap vector."""
        # Save current state
        self.csrs.write(CSR_MEPC, self.pc & ~0b11 if trap.cause != CAUSE_MISALIGNED_FETCH else self.pc)
        self.csrs.write(CSR_MCAUSE, trap.cause)
        self.csrs.write(CSR_MTVAL, trap.tval)

        # Update mstatus: disable MIE, save old MIE to MPIE
        mstatus = self.csrs.read(CSR_MSTATUS)
        old_mie = (mstatus & MSTATUS_MIE) != 0
        mstatus &= ~MSTATUS_MIE  # Disable interrupts
        if old_mie:
            mstatus |= MSTATUS_MPIE  # Save old MIE
        else:
            mstatus &= ~MSTATUS_MPIE
        mstatus = (mstatus & ~MSTATUS_MPP) | (self.priv << 11)  # Save old privilege
        self.csrs.write(CSR_MSTATUS, mstatus)

        # Set privilege to M-mode
        self.priv = self.PRIV_M

        # Jump to trap vector
        mtvec = self.csrs.read(CSR_MTVEC)
        if mtvec == 0:
            # No trap handler: halt
            self._halted = True
            raise CPUHalt(f"Unresolved trap: cause={trap.cause}, tval=0x{trap.tval:08x}")
        self.pc = mtvec

    def _execute(self, insn: int) -> None:
        """Decode and execute a single 32-bit instruction."""
        opcode = insn & 0x7F
        rd = (insn >> 7) & 0x1F
        funct3 = (insn >> 12) & 0x7
        rs1 = (insn >> 15) & 0x1F
        rs2 = (insn >> 20) & 0x1F
        funct7 = (insn >> 25) & 0x7F

        # I-type immediate
        imm_i = self.sign_extend((insn >> 20) & 0xFFF, 12)
        # S-type immediate
        imm_s = self.sign_extend(((insn >> 7) & 0x1F) | (((insn >> 25) & 0x7F) << 5), 12)
        # B-type immediate
        imm_b = self.sign_extend(
            (((insn >> 8) & 0xF) << 1) |
            (((insn >> 7) & 0x1) << 11) |
            (((insn >> 25) & 0x3F) << 5) |
            (((insn >> 31) & 0x1) << 12),
            13
        )
        # U-type immediate
        imm_u = self.sign_extend(insn & 0xFFFFF000, 32)
        # J-type immediate
        imm_j = self.sign_extend(
            (((insn >> 21) & 0x3FF) << 1) |
            (((insn >> 20) & 0x1) << 11) |
            (((insn >> 12) & 0xFF) << 12) |
            (((insn >> 31) & 0x1) << 20),
            21
        )

        if opcode == 0x37:  # LUI
            self.set_reg(rd, imm_u & 0xFFFFFFFF)
            self.pc += 4

        elif opcode == 0x17:  # AUIPC
            self.set_reg(rd, self.mask32(self.pc + imm_u))
            self.pc += 4

        elif opcode == 0x6F:  # JAL
            self.set_reg(rd, self.pc + 4)
            self.pc = self.mask32(self.pc + imm_j)

        elif opcode == 0x67:  # JALR
            target = self.mask32((self.get_reg(rs1) + imm_i) & ~1)
            self.set_reg(rd, self.pc + 4)
            self.pc = target

        elif opcode == 0x63:  # Branch
            taken = False
            a = self.get_reg_signed(rs1)
            b = self.get_reg_signed(rs2)
            if funct3 == 0b000:  # BEQ
                taken = self.get_reg(rs1) == self.get_reg(rs2)
            elif funct3 == 0b001:  # BNE
                taken = self.get_reg(rs1) != self.get_reg(rs2)
            elif funct3 == 0b100:  # BLT
                taken = a < b
            elif funct3 == 0b101:  # BGE
                taken = a >= b
            elif funct3 == 0b110:  # BLTU
                taken = self.get_reg(rs1) < self.get_reg(rs2)
            elif funct3 == 0b111:  # BGEU
                taken = self.get_reg(rs1) >= self.get_reg(rs2)
            else:
                raise Trap(CAUSE_ILLEGAL_INSN, insn)
            if taken:
                self.pc = self.mask32(self.pc + imm_b)
            else:
                self.pc += 4

        elif opcode == 0x03:  # Load
            addr = self.mask32(self.get_reg(rs1) + imm_i)
            if funct3 == 0b000:  # LB
                val = self.memory.read_byte(addr)
                self.set_reg(rd, self.sign_extend(val, 8) & 0xFFFFFFFF)
            elif funct3 == 0b001:  # LH
                val = self.memory.read_half(addr)
                self.set_reg(rd, self.sign_extend(val, 16) & 0xFFFFFFFF)
            elif funct3 == 0b010:  # LW
                val = self.memory.read_word(addr)
                self.set_reg(rd, val)
            elif funct3 == 0b100:  # LBU
                self.set_reg(rd, self.memory.read_byte(addr))
            elif funct3 == 0b101:  # LHU
                self.set_reg(rd, self.memory.read_half(addr))
            else:
                raise Trap(CAUSE_ILLEGAL_INSN, insn)
            self.pc += 4

        elif opcode == 0x23:  # Store
            addr = self.mask32(self.get_reg(rs1) + imm_s)
            val = self.get_reg(rs2)
            if funct3 == 0b000:  # SB
                self.memory.write_byte(addr, val)
            elif funct3 == 0b001:  # SH
                self.memory.write_half(addr, val)
            elif funct3 == 0b010:  # SW
                self.memory.write_word(addr, val)
            else:
                raise Trap(CAUSE_ILLEGAL_INSN, insn)
            self.pc += 4

        elif opcode == 0x13:  # I-type ALU
            src = self.get_reg(rs1)
            if funct3 == 0b000:  # ADDI
                result = self.mask32(src + imm_i)
            elif funct3 == 0b010:  # SLTI
                result = 1 if self.get_reg_signed(rs1) < imm_i else 0
            elif funct3 == 0b011:  # SLTIU
                result = 1 if self.get_reg(rs1) < (imm_i & 0xFFFFFFFF) else 0
            elif funct3 == 0b100:  # XORI
                result = self.mask32(src ^ (imm_i & 0xFFFFFFFF))
            elif funct3 == 0b110:  # ORI
                result = self.mask32(src | (imm_i & 0xFFFFFFFF))
            elif funct3 == 0b111:  # ANDI
                result = self.mask32(src & (imm_i & 0xFFFFFFFF))
            elif funct3 == 0b001:  # SLLI
                shamt = (insn >> 20) & 0x1F
                result = self.mask32(src << shamt)
            elif funct3 == 0b101:  # SRLI / SRAI
                shamt = (insn >> 20) & 0x1F
                if funct7 & 0x20:  # SRAI
                    result = self.mask32(self.get_reg_signed(rs1) >> shamt)
                else:  # SRLI
                    result = src >> shamt
            else:
                raise Trap(CAUSE_ILLEGAL_INSN, insn)
            self.set_reg(rd, result)
            self.pc += 4

        elif opcode == 0x33:  # R-type ALU
            a = self.get_reg(rs1)
            b = self.get_reg(rs2)
            a_s = self.get_reg_signed(rs1)
            b_s = self.get_reg_signed(rs2)

            if funct3 == 0b000:
                if funct7 == 0x00:  # ADD
                    result = self.mask32(a + b)
                elif funct7 == 0x20:  # SUB
                    result = self.mask32(a - b)
                else:
                    raise Trap(CAUSE_ILLEGAL_INSN, insn)
            elif funct3 == 0b001:  # SLL
                result = self.mask32(a << (b & 0x1F))
            elif funct3 == 0b010:  # SLT
                result = 1 if a_s < b_s else 0
            elif funct3 == 0b011:  # SLTU
                result = 1 if a < b else 0
            elif funct3 == 0b100:  # XOR
                result = a ^ b
            elif funct3 == 0b101:
                shamt = b & 0x1F
                if funct7 == 0x00:  # SRL
                    result = a >> shamt
                elif funct7 == 0x20:  # SRA
                    result = self.mask32(a_s >> shamt)
                else:
                    raise Trap(CAUSE_ILLEGAL_INSN, insn)
            elif funct3 == 0b110:  # OR
                result = a | b
            elif funct3 == 0b111:  # AND
                result = a & b
            else:
                raise Trap(CAUSE_ILLEGAL_INSN, insn)
            self.set_reg(rd, result & 0xFFFFFFFF)
            self.pc += 4

        elif opcode == 0x0F:  # FENCE
            # No-op in emulator (no memory ordering needed)
            self.pc += 4

        elif opcode == 0x73:  # SYSTEM
            if funct3 == 0b000:
                if insn == 0x00100073:  # EBREAK
                    raise Trap(CAUSE_BREAKPOINT, self.pc)
                elif insn == 0x00000073:  # ECALL
                    if self.priv == self.PRIV_U:
                        raise Trap(CAUSE_ECALL_U, 0)
                    else:
                        raise Trap(CAUSE_ECALL_M, 0)
                else:
                    raise Trap(CAUSE_ILLEGAL_INSN, insn)
            elif funct3 in (0b001, 0b010, 0b011, 0b101, 0b110, 0b111):
                # CSR instructions
                csr_addr = (insn >> 20) & 0xFFF
                if funct3 == 0b001:  # CSRRW
                    old = self.csrs.read(csr_addr)
                    self.csrs.write(csr_addr, self.get_reg(rs1))
                    self.set_reg(rd, old)
                elif funct3 == 0b010:  # CSRRS
                    old = self.csrs.set_bits(csr_addr, self.get_reg(rs1))
                    self.set_reg(rd, old)
                elif funct3 == 0b011:  # CSRRC
                    old = self.csrs.clear_bits(csr_addr, self.get_reg(rs1))
                    self.set_reg(rd, old)
                elif funct3 == 0b101:  # CSRRWI
                    old = self.csrs.read(csr_addr)
                    zimm = (insn >> 15) & 0x1F
                    self.csrs.write(csr_addr, zimm)
                    self.set_reg(rd, old)
                elif funct3 == 0b110:  # CSRRSI
                    zimm = (insn >> 15) & 0x1F
                    old = self.csrs.set_bits(csr_addr, zimm)
                    self.set_reg(rd, old)
                elif funct3 == 0b111:  # CSRRCI
                    zimm = (insn >> 15) & 0x1F
                    old = self.csrs.clear_bits(csr_addr, zimm)
                    self.set_reg(rd, old)
                self.pc += 4
            else:
                raise Trap(CAUSE_ILLEGAL_INSN, insn)

        elif opcode == 0x1B:  # RV32I-only: MUL/DIV extension not implemented
            # This is actually the COMPRESSED instruction space in full RVC,
            # but for RV32I only, treat as illegal
            raise Trap(CAUSE_ILLEGAL_INSN, insn)

        else:
            raise Trap(CAUSE_ILLEGAL_INSN, insn)

    def state_dump(self) -> str:
        """Return a string dump of CPU state."""
        lines = [f"PC: 0x{self.pc:08x}  Priv: {'M' if self.priv == 3 else 'U'}"]
        for i in range(0, 32, 4):
            parts = []
            for j in range(4):
                idx = i + j
                name = self.REG_NAMES[idx]
                val = self.regs[idx] & 0xFFFFFFFF
                parts.append(f"x{idx:2d}({name:>4s})=0x{val:08x}")
            lines.append("  ".join(parts))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"CPU(pc=0x{self.pc:08x}, halted={self._halted})"