"""RISC-V RV32I + RV32M disassembler.

Decodes 32-bit RISC-V instruction words into human-readable assembly.
Supports RV32I base instruction set and RV32M extension.
"""

from __future__ import annotations
from typing import Optional, Dict

# Register name mapping
REG_NAMES = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
]


def _reg(idx: int) -> str:
    """Format register name."""
    if 0 <= idx <= 31:
        return REG_NAMES[idx]
    return f"x{idx}"


def _sign_extend(value: int, bits: int) -> int:
    """Sign-extend value from given bit width."""
    if value & (1 << (bits - 1)):
        return value - (1 << bits)
    return value


def disassemble(insn: int, pc: int = 0) -> str:
    """Disassemble a single 32-bit RISC-V instruction.

    Args:
        insn: 32-bit instruction word.
        pc: Program counter (for computing branch targets).

    Returns:
        Human-readable assembly string.
    """
    opcode = insn & 0x7F
    rd = (insn >> 7) & 0x1F
    funct3 = (insn >> 12) & 0x7
    rs1 = (insn >> 15) & 0x1F
    rs2 = (insn >> 20) & 0x1F
    funct7 = (insn >> 25) & 0x7F

    # I-type immediate
    imm_i = _sign_extend((insn >> 20) & 0xFFF, 12)
    # S-type immediate
    imm_s = _sign_extend(((insn >> 7) & 0x1F) | (((insn >> 25) & 0x7F) << 5), 12)
    # B-type immediate
    imm_b = _sign_extend(
        (((insn >> 8) & 0xF) << 1) |
        (((insn >> 7) & 0x1) << 11) |
        (((insn >> 25) & 0x3F) << 5) |
        (((insn >> 31) & 0x1) << 12),
        13
    )
    # U-type immediate
    imm_u = _sign_extend(insn & 0xFFFFF000, 32)
    # J-type immediate
    imm_j = _sign_extend(
        (((insn >> 21) & 0x3FF) << 1) |
        (((insn >> 20) & 0x1) << 11) |
        (((insn >> 12) & 0xFF) << 12) |
        (((insn >> 31) & 0x1) << 20),
        21
    )

    # Shamt for shifts
    shamt = (insn >> 20) & 0x1F

    # --- LUI ---
    if opcode == 0x37:
        return f"lui {_reg(rd)}, {imm_u}"

    # --- AUIPC ---
    if opcode == 0x17:
        return f"auipc {_reg(rd)}, {imm_u}"

    # --- JAL ---
    if opcode == 0x6F:
        target = pc + imm_j
        return f"jal {_reg(rd)}, 0x{target:08x}"

    # --- JALR ---
    if opcode == 0x67:
        return f"jalr {_reg(rd)}, {_reg(rs1)}, {imm_i}"

    # --- Branch ---
    if opcode == 0x63:
        branch_names = {
            0b000: "beq", 0b001: "bne", 0b100: "blt",
            0b101: "bge", 0b110: "bltu", 0b111: "bgeu",
        }
        name = branch_names.get(funct3)
        if name is None:
            return f".word 0x{insn:08x}"
        target = pc + imm_b
        return f"{name} {_reg(rs1)}, {_reg(rs2)}, 0x{target:08x}"

    # --- Load ---
    if opcode == 0x03:
        load_names = {
            0b000: "lb", 0b001: "lh", 0b010: "lw",
            0b100: "lbu", 0b101: "lhu",
        }
        name = load_names.get(funct3)
        if name is None:
            return f".word 0x{insn:08x}"
        return f"{name} {_reg(rd)}, {imm_i}({_reg(rs1)})"

    # --- Store ---
    if opcode == 0x23:
        store_names = {0b000: "sb", 0b001: "sh", 0b010: "sw"}
        name = store_names.get(funct3)
        if name is None:
            return f".word 0x{insn:08x}"
        return f"{name} {_reg(rs2)}, {imm_s}({_reg(rs1)})"

    # --- I-type ALU ---
    if opcode == 0x13:
        if funct3 == 0b000:
            return f"addi {_reg(rd)}, {_reg(rs1)}, {imm_i}"
        elif funct3 == 0b010:
            return f"slti {_reg(rd)}, {_reg(rs1)}, {imm_i}"
        elif funct3 == 0b011:
            return f"sltiu {_reg(rd)}, {_reg(rs1)}, {imm_i & 0xFFFFFFFF}"
        elif funct3 == 0b100:
            return f"xori {_reg(rd)}, {_reg(rs1)}, {imm_i & 0xFFFFFFFF}"
        elif funct3 == 0b110:
            return f"ori {_reg(rd)}, {_reg(rs1)}, {imm_i & 0xFFFFFFFF}"
        elif funct3 == 0b111:
            return f"andi {_reg(rd)}, {_reg(rs1)}, {imm_i & 0xFFFFFFFF}"
        elif funct3 == 0b001:
            return f"slli {_reg(rd)}, {_reg(rs1)}, {shamt}"
        elif funct3 == 0b101:
            if funct7 & 0x20:
                return f"srai {_reg(rd)}, {_reg(rs1)}, {shamt}"
            else:
                return f"srli {_reg(rd)}, {_reg(rs1)}, {shamt}"
        return f".word 0x{insn:08x}"

    # --- R-type ALU / M extension ---
    if opcode == 0x33:
        # M extension
        if funct7 == 0x01:
            m_names = {
                0b000: "mul", 0b001: "mulh", 0b010: "mulhsu",
                0b011: "mulhu", 0b100: "div", 0b101: "divu",
                0b110: "rem", 0b111: "remu",
            }
            name = m_names.get(funct3)
            if name:
                return f"{name} {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
            return f".word 0x{insn:08x}"

        if funct3 == 0b000:
            if funct7 == 0x00:
                return f"add {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
            elif funct7 == 0x20:
                return f"sub {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b001:
            return f"sll {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b010:
            return f"slt {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b011:
            return f"sltu {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b100:
            return f"xor {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b101:
            if funct7 == 0x00:
                return f"srl {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
            elif funct7 == 0x20:
                return f"sra {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b110:
            return f"or {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        elif funct3 == 0b111:
            return f"and {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        return f".word 0x{insn:08x}"

    # --- FENCE ---
    if opcode == 0x0F:
        return "fence"

    # --- SYSTEM ---
    if opcode == 0x73:
        if funct3 == 0b000:
            if insn == 0x00000073:
                return "ecall"
            elif insn == 0x00100073:
                return "ebreak"
            else:
                return f".word 0x{insn:08x}"
        csr_names = {
            0x300: "mstatus", 0x304: "mie", 0x305: "mtvec",
            0x340: "mscratch", 0x341: "mepc", 0x342: "mcause",
            0x343: "mtval", 0x344: "mip",
            0xC00: "cycle", 0xC02: "instret",
        }
        csr_addr = (insn >> 20) & 0xFFF
        csr_name = csr_names.get(csr_addr, f"0x{csr_addr:03x}")
        if funct3 == 0b001:
            return f"csrrw {_reg(rd)}, {csr_name}, {_reg(rs1)}"
        elif funct3 == 0b010:
            return f"csrrs {_reg(rd)}, {csr_name}, {_reg(rs1)}"
        elif funct3 == 0b011:
            return f"csrrc {_reg(rd)}, {csr_name}, {_reg(rs1)}"
        elif funct3 == 0b101:
            zimm = (insn >> 15) & 0x1F
            return f"csrrwi {_reg(rd)}, {csr_name}, {zimm}"
        elif funct3 == 0b110:
            zimm = (insn >> 15) & 0x1F
            return f"csrrsi {_reg(rd)}, {csr_name}, {zimm}"
        elif funct3 == 0b111:
            zimm = (insn >> 15) & 0x1F
            return f"csrrci {_reg(rd)}, {csr_name}, {zimm}"
        return f".word 0x{insn:08x}"

    # Unknown instruction
    return f".word 0x{insn:08x}"


def disassemble_block(code: bytes, base_addr: int = 0) -> list:
    """Disassemble a block of RISC-V instructions.

    Args:
        code: Raw bytes (little-endian 32-bit words).
        base_addr: Starting address.

    Returns:
        List of (address, instruction_word, assembly_string) tuples.
    """
    results = []
    for i in range(0, len(code), 4):
        if i + 4 > len(code):
            break
        insn_word = int.from_bytes(code[i:i+4], 'little')
        addr = base_addr + i
        asm = disassemble(insn_word, addr)
        results.append((addr, insn_word, asm))
    return results


def disassemble_to_string(code: bytes, base_addr: int = 0) -> str:
    """Disassemble a block and return as formatted string.

    Args:
        code: Raw bytes (little-endian 32-bit words).
        base_addr: Starting address.

    Returns:
        Formatted disassembly string with address, hex, and assembly.
    """
    lines = []
    for addr, insn_word, asm in disassemble_block(code, base_addr):
        lines.append(f"  0x{addr:08x}:  0x{insn_word:08x}  {asm}")
    return "\n".join(lines)