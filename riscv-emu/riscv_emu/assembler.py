"""RISC-V assembler — two-pass assembler for RV32I instruction set.

Supports:
  - All RV32I base instructions
  - Pseudo-instructions (LI, LA, MV, NOP, NOT, NEG, BGT, BLE, BGTU, BLEU, J, RET, CALL)
  - Labels with forward references
  - Directives: .text, .data, .word, .half, .byte, .string, .align, .global, .org
  - Literals: decimal, hex (0x), binary (0b), character ('A')
"""

from __future__ import annotations
import re
import struct
from typing import Dict, List, Optional, Tuple, Union


class AssembleError(Exception):
    """Raised on assembly errors."""
    pass


class Assembler:
    """Two-pass RISC-V assembler.

    Pass 1: Collect labels and compute addresses.
    Pass 2: Encode instructions and data.
    """

    # Instruction encodings grouped by type
    R_TYPE_OPS = {
        "add":  (0b0110011, 0b000, 0b0000000),
        "sub":  (0b0110011, 0b000, 0b0100000),
        "sll":  (0b0110011, 0b001, 0b0000000),
        "slt":  (0b0110011, 0b010, 0b0000000),
        "sltu": (0b0110011, 0b011, 0b0000000),
        "xor":  (0b0110011, 0b100, 0b0000000),
        "srl":  (0b0110011, 0b101, 0b0000000),
        "sra":  (0b0110011, 0b101, 0b0100000),
        "or":   (0b0110011, 0b110, 0b0000000),
        "and":  (0b0110011, 0b111, 0b0000000),
        # RV32M extension (funct7=0b0000001)
        "mul":   (0b0110011, 0b000, 0b0000001),
        "mulh":  (0b0110011, 0b001, 0b0000001),
        "mulhsu":(0b0110011, 0b010, 0b0000001),
        "mulhu": (0b0110011, 0b011, 0b0000001),
        "div":   (0b0110011, 0b100, 0b0000001),
        "divu":  (0b0110011, 0b101, 0b0000001),
        "rem":   (0b0110011, 0b110, 0b0000001),
        "remu":  (0b0110011, 0b111, 0b0000001),
    }

    I_TYPE_OPS = {
        "addi":  0b000, "slti":  0b010, "sltiu": 0b011,
        "xori":  0b100, "ori":   0b110, "andi":  0b111,
        "slli":  0b001, "srli":  0b101,
        "srai":  0b101,  # funct7 distinguishes
    }

    LOAD_OPS = {"lb": 0b000, "lh": 0b001, "lw": 0b010, "lbu": 0b100, "lhu": 0b101}
    STORE_OPS = {"sb": 0b000, "sh": 0b001, "sw": 0b010}
    BRANCH_OPS = {
        "beq": 0b000, "bne": 0b001, "blt": 0b100,
        "bge": 0b101, "bltu": 0b110, "bgeu": 0b111,
    }

    # Pseudo-instructions that map to real instructions
    PSEUDO_INSTRUCTIONS = {
        "nop":  "addi x0, x0, 0",
        "mv":   None,  # rd, rs -> addi rd, rs, 0
        "not":  None,  # rd, rs -> xori rd, rs, -1
        "neg":  None,  # rd, rs -> sub rd, x0, rs
        "li":   None,  # rd, imm -> lui + addi (or just addi if small)
        "la":   None,  # rd, label -> auipc + addi
        "j":    None,  # label -> jal x0, label
        "jal":  None,  # label -> jal x1, label (already real, but single-arg form)
        "ret":  "jalr x0, x1, 0",
        "call": None,  # label -> auipc x1, + jalr x1, x1, offset
        "bgt":  None,  # rs1, rs2, offset -> blt rs2, rs1, offset
        "ble":  None,  # rs1, rs2, offset -> bge rs2, rs1, offset
        "bgtu": None,  # rs1, rs2, offset -> bltu rs2, rs1, offset
        "bleu": None,  # rs1, rs2, offset -> bgeu rs2, rs1, offset
        "beqz": None, # rs, offset -> beq rs, x0, offset
        "bnez": None, # rs, offset -> bne rs, x0, offset
        "bgez": None, # rs, offset -> bge rs, x0, offset
        "bltz": None, # rs, offset -> blt rs, x0, offset
    }

    def __init__(self, base_addr: int = 0x20000000):
        self.base_addr = base_addr
        self.labels: Dict[str, int] = {}
        self.code: List[int] = []  # Assembled 32-bit words
        self.data: bytearray = bytearray()  # Data section
        self.current_addr = base_addr
        self._text_start = base_addr
        self._data_start = 0
        self._in_data = False

    @staticmethod
    def parse_register(s: str) -> int:
        """Parse register name/number to index."""
        s = s.strip().lower()
        abi_names = {
            "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
            "t0": 5, "t1": 6, "t2": 7,
            "s0": 8, "fp": 8, "s1": 9,
            "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15,
            "a6": 16, "a7": 17,
            "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
            "s8": 24, "s9": 25, "s10": 26, "s11": 27,
            "t3": 28, "t4": 29, "t5": 30, "t6": 31,
        }
        if s in abi_names:
            return abi_names[s]
        # Try x0-x31
        m = re.match(r"x(\d+)", s)
        if m and 0 <= int(m.group(1)) <= 31:
            return int(m.group(1))
        raise AssembleError(f"Invalid register: '{s}'")

    @staticmethod
    def parse_immediate(s: str, labels: Optional[Dict[str, int]] = None) -> int:
        """Parse an immediate value (decimal, hex, binary, char)."""
        s = s.strip()
        # Character literal
        if len(s) == 3 and s[0] == "'" and s[2] == "'":
            return ord(s[1])
        # Label reference
        if s in (labels or {}):
            return labels[s]
        # Try numeric
        try:
            if s.startswith("0x") or s.startswith("0X"):
                return int(s, 16)
            elif s.startswith("0b") or s.startswith("0B"):
                return int(s, 2)
            else:
                return int(s)
        except ValueError:
            raise AssembleError(f"Invalid immediate: '{s}'")

    def _encode_r_type(self, rd: int, rs1: int, rs2: int, funct3: int, funct7: int) -> int:
        return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0b0110011

    def _encode_i_type(self, rd: int, rs1: int, imm: int, funct3: int) -> int:
        return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0b0010011

    def _encode_s_type(self, rs1: int, rs2: int, imm: int, funct3: int) -> int:
        imm11_5 = (imm >> 5) & 0x7F
        imm4_0 = imm & 0x1F
        return (imm11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm4_0 << 7) | 0b0100011

    def _encode_b_type(self, rs1: int, rs2: int, imm: int, funct3: int) -> int:
        imm12 = (imm >> 12) & 0x1
        imm10_5 = (imm >> 5) & 0x3F
        imm4_1 = (imm >> 1) & 0xF
        imm11 = (imm >> 11) & 0x1
        return (imm12 << 31) | (imm10_5 << 25) | (rs2 << 20) | (rs1 << 15) | \
               (funct3 << 12) | (imm4_1 << 8) | (imm11 << 7) | 0b1100011

    def _encode_u_type(self, rd: int, imm: int) -> int:
        """Encode U-type instruction (LUI/AUIPC).

        In RISC-V, the U-type immediate is the upper 20-bit value that gets
        placed in bits [31:12]. So `lui rd, N` means `rd = N << 12`.

        However, we also accept the full 32-bit form (e.g., 0x20010000) as a
        convenience, detecting it when lower 12 bits are zero and the value
        appears to be a shifted 20-bit quantity.
        """
        # If the value looks like a pre-shifted 32-bit value (lower 12 bits zero
        # and it's large enough to be a full address), use it as-is.
        # Otherwise treat it as the 20-bit upper value to be shifted.
        if (imm & 0xFFF) == 0 and imm != 0 and (imm >> 12) <= 0xFFFFF:
            # Could be either form. Check if the 20-bit interpretation gives
            # a different result than the 32-bit interpretation.
            # If (imm >> 12) == (imm & 0xFFFFF000) >> 12, they're equivalent.
            # Otherwise, prefer the 32-bit form (value as-is).
            # Heuristic: if the value has more than 20 significant bits,
            # it's likely meant as a full 32-bit value.
            bit_length = imm.bit_length()
            if bit_length > 20:
                # Likely a full 32-bit value already in position
                return (imm & 0xFFFFF000) | (rd << 7) | 0b0110111
            else:
                # Likely a 20-bit upper value to be shifted
                return ((imm << 12) & 0xFFFFF000) | (rd << 7) | 0b0110111
        elif (imm & 0xFFF) == 0 and imm == 0:
            # lui rd, 0 — both forms give 0
            return (rd << 7) | 0b0110111
        else:
            # Has non-zero lower 12 bits — must be a 20-bit upper value
            return ((imm << 12) & 0xFFFFF000) | (rd << 7) | 0b0110111

    def _encode_j_type(self, rd: int, imm: int) -> int:
        imm20 = (imm >> 20) & 0x1
        imm10_1 = (imm >> 1) & 0x3FF
        imm11 = (imm >> 11) & 0x1
        imm19_12 = (imm >> 12) & 0xFF
        return (imm20 << 31) | (imm10_1 << 21) | (imm11 << 20) | \
               (imm19_12 << 12) | (rd << 7) | 0b1101111

    def assemble(self, source: str, base_addr: int = 0x20000000) -> Tuple[bytearray, Dict[str, int]]:
        """Assemble source code into machine code.

        Returns:
            Tuple of (bytearray of machine code, dict of label addresses)
        """
        self.base_addr = base_addr
        self.current_addr = base_addr
        self.labels = {}
        self.code = []
        self.data = bytearray()
        self._in_data = False

        # Strip comments and blank lines
        lines = []
        for lineno, raw in enumerate(source.splitlines(), 1):
            # Remove comments (# style)
            line = raw.split("#")[0].strip()
            if not line:
                continue
            lines.append((lineno, line))

        # Pass 1: collect labels, compute addresses, expand pseudo-instructions
        expanded = self._pass1(lines)

        # Pass 2: encode instructions
        self._pass2(expanded)

        # Build output bytes
        output = bytearray()
        for word in self.code:
            output.extend(struct.pack("<I", word & 0xFFFFFFFF))
        output.extend(self.data)

        return output, dict(self.labels)

    def _pass1(self, lines: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """Collect labels and compute addresses. Expand pseudo-instructions."""
        expanded = []
        for lineno, line in lines:
            # Handle label
            while ":" in line:
                colon_pos = line.index(":")
                label = line[:colon_pos].strip()
                if not re.match(r"^[a-zA-Z_]\w*$", label):
                    raise AssembleError(f"Line {lineno}: Invalid label '{label}'")
                self.labels[label] = self.current_addr
                line = line[colon_pos + 1:].strip()

            if not line:
                continue

            # Handle directives
            if line.startswith("."):
                expanded.extend(self._handle_directive(lineno, line))
                continue

            # Expand pseudo-instructions
            parts = line.split(None, 1)
            mnemonic = parts[0].lower()
            operands = parts[1] if len(parts) > 1 else ""

            if mnemonic == "nop":
                expanded.append((lineno, "addi x0, x0, 0"))
                self.current_addr += 4
            elif mnemonic == "mv":
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 2:
                    raise AssembleError(f"Line {lineno}: MV requires 2 operands")
                expanded.append((lineno, f"addi {args[0]}, {args[1]}, 0"))
                self.current_addr += 4
            elif mnemonic == "not":
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 2:
                    raise AssembleError(f"Line {lineno}: NOT requires 2 operands")
                expanded.append((lineno, f"xori {args[0]}, {args[1]}, -1"))
                self.current_addr += 4
            elif mnemonic == "neg":
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 2:
                    raise AssembleError(f"Line {lineno}: NEG requires 2 operands")
                expanded.append((lineno, f"sub {args[0]}, x0, {args[1]}"))
                self.current_addr += 4
            elif mnemonic == "j":
                expanded.append((lineno, f"jal x0, {operands.strip()}"))
                self.current_addr += 4
            elif mnemonic == "ret":
                expanded.append((lineno, "jalr x0, x1, 0"))
                self.current_addr += 4
            elif mnemonic == "call":
                # call = auipc x1, offset[31:12] + jalr x1, x1, offset[11:0]
                expanded.append((lineno, f"_call_auipc x1, {operands.strip()}"))
                expanded.append((lineno, f"jalr x1, x1, {operands.strip()}"))
                self.current_addr += 8
            elif mnemonic == "li":
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 2:
                    raise AssembleError(f"Line {lineno}: LI requires 2 operands")
                rd = args[0]
                imm = self.parse_immediate(args[1])
                # If imm fits in 12-bit signed, use just addi
                if -2048 <= imm <= 2047:
                    expanded.append((lineno, f"addi {rd}, x0, {imm}"))
                    self.current_addr += 4
                else:
                    # Need LUI + ADDI
                    # upper bits (bits [31:12]) of the target value, adjusted
                    # for sign extension of the addi immediate
                    upper = (imm + 0x800) & 0xFFFFF000
                    lower = imm - upper
                    # Pass the upper 20-bit field value (unshifted) to lui
                    upper_field = (upper >> 12) & 0xFFFFF
                    expanded.append((lineno, f"lui {rd}, {upper_field}"))
                    expanded.append((lineno, f"addi {rd}, {rd}, {lower}"))
                    self.current_addr += 8
            elif mnemonic == "la":
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 2:
                    raise AssembleError(f"Line {lineno}: LA requires 2 operands")
                # la rd, label -> auipc rd, %pcrel_hi(label) + addi rd, rd, %pcrel_lo(label)
                expanded.append((lineno, f"auipc {args[0]}, {args[1]}"))
                expanded.append((lineno, f"addi {args[0]}, {args[0]}, {args[1]}"))
                self.current_addr += 8
            elif mnemonic in ("beqz", "bnez", "bgez", "bltz"):
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 2:
                    raise AssembleError(f"Line {lineno}: {mnemonic} requires 2 operands")
                branch_map = {"beqz": "beq", "bnez": "bne", "bgez": "bge", "bltz": "blt"}
                if mnemonic in ("beqz", "bnez"):
                    expanded.append((lineno, f"{branch_map[mnemonic]} {args[0]}, x0, {args[1]}"))
                else:
                    expanded.append((lineno, f"{branch_map[mnemonic]} {args[0]}, x0, {args[1]}"))
                self.current_addr += 4
            elif mnemonic in ("bgt", "ble", "bgtu", "bleu"):
                args = [a.strip() for a in operands.split(",")]
                if len(args) != 3:
                    raise AssembleError(f"Line {lineno}: {mnemonic} requires 3 operands")
                swap_map = {"bgt": "blt", "ble": "bge", "bgtu": "bltu", "bleu": "bgeu"}
                expanded.append((lineno, f"{swap_map[mnemonic]} {args[1]}, {args[0]}, {args[2]}"))
                self.current_addr += 4
            else:
                # Regular instruction
                expanded.append((lineno, line))
                self.current_addr += 4

        return expanded

    def _handle_directive(self, lineno: int, line: str) -> List[Tuple[int, str]]:
        """Handle assembler directives. Returns empty list (directives produce no instructions)."""
        parts = line.split(None, 1)
        directive = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if directive == ".text":
            self._in_data = False
        elif directive == ".data":
            self._in_data = True
        elif directive == ".word":
            for val_s in args.split(","):
                val = self.parse_immediate(val_s.strip())
                self.data.extend(struct.pack("<I", val & 0xFFFFFFFF))
                self.current_addr += 4
        elif directive == ".half":
            for val_s in args.split(","):
                val = self.parse_immediate(val_s.strip())
                self.data.extend(struct.pack("<H", val & 0xFFFF))
                self.current_addr += 2
        elif directive == ".byte":
            for val_s in args.split(","):
                val = self.parse_immediate(val_s.strip())
                self.data.append(val & 0xFF)
                self.current_addr += 1
        elif directive == ".string":
            s = args.strip()
            if s.startswith('"') and s.endswith('"'):
                s = s[1:-1]
            # Handle escape sequences
            s = s.replace("\\n", "\n").replace("\\t", "\t").replace("\\0", "\0").replace("\\\\", "\\")
            self.data.extend(s.encode("utf-8") + b"\0")
            self.current_addr += len(s) + 1
        elif directive == ".align":
            n = int(args.strip())
            alignment = 1 << n
            while self.current_addr % alignment != 0:
                self.data.append(0)
                self.current_addr += 1
        elif directive == ".global" or directive == ".globl":
            pass  # No-op in this assembler
        elif directive == ".org":
            self.current_addr = self.parse_immediate(args.strip())
        else:
            raise AssembleError(f"Line {lineno}: Unknown directive '{directive}'")
        return []

    def _pass2(self, expanded: List[Tuple[int, str]]) -> None:
        """Encode all instructions using resolved labels."""
        addr = self.base_addr
        for lineno, line in expanded:
            try:
                insn = self._encode_instruction(lineno, line, addr)
                if insn is not None:
                    self.code.append(insn)
                    addr += 4
            except AssembleError:
                raise
            except Exception as e:
                raise AssembleError(f"Line {lineno}: {e}") from e

    def _parse_mem_operand(self, operand: str) -> Tuple[int, str]:
        """Parse memory operand like 'offset(rs1)' or '(rs1)'.
        Returns (offset, rs1_reg_index).
        """
        m = re.match(r"(-?\w+)\((\w+)\)", operand)
        if m:
            offset = self.parse_immediate(m.group(1), self.labels)
            rs1 = self.parse_register(m.group(2))
            return offset, rs1
        m = re.match(r"\((\w+)\)", operand)
        if m:
            return 0, self.parse_register(m.group(1))
        raise AssembleError(f"Invalid memory operand: '{operand}'")

    def _encode_instruction(self, lineno: int, line: str, addr: int) -> Optional[int]:
        """Encode a single instruction line to a 32-bit word."""
        parts = line.split(None, 1)
        mnemonic = parts[0].lower()
        operands_str = parts[1] if len(parts) > 1 else ""

        # Split operands by comma, handle memory operands carefully
        operands = [o.strip() for o in operands_str.split(",")] if operands_str else []

        # R-type: add, sub, sll, slt, sltu, xor, srl, sra, or, and
        if mnemonic in self.R_TYPE_OPS:
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: {mnemonic} requires 3 operands, got {len(operands)}")
            opcode, funct3, funct7 = self.R_TYPE_OPS[mnemonic]
            rd = self.parse_register(operands[0])
            rs1 = self.parse_register(operands[1])
            rs2 = self.parse_register(operands[2])
            return self._encode_r_type(rd, rs1, rs2, funct3, funct7)

        # I-type ALU: addi, slti, sltiu, xori, ori, andi, slli, srli, srai
        if mnemonic in self.I_TYPE_OPS:
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: {mnemonic} requires 3 operands, got {len(operands)}")
            funct3 = self.I_TYPE_OPS[mnemonic]
            rd = self.parse_register(operands[0])
            rs1 = self.parse_register(operands[1])
            if mnemonic in ("slli", "srli", "srai"):
                imm = self.parse_immediate(operands[2])
                funct7 = 0x20 if mnemonic == "srai" else 0x00
                return (funct7 << 25) | ((imm & 0x1F) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0b0010011
            else:
                imm = self.parse_immediate(operands[2], self.labels)
                return self._encode_i_type(rd, rs1, imm, funct3)

        # Load: lb, lh, lw, lbu, lhu
        if mnemonic in self.LOAD_OPS:
            if len(operands) != 2:
                raise AssembleError(f"Line {lineno}: {mnemonic} requires 2 operands, got {len(operands)}")
            funct3 = self.LOAD_OPS[mnemonic]
            rd = self.parse_register(operands[0])
            offset, rs1 = self._parse_mem_operand(operands[1])
            # Encode as I-type but with Load opcode (0b0000011) instead of ALU opcode (0b0010011)
            insn = self._encode_i_type(rd, rs1, offset, funct3)
            insn = (insn & ~0x7F) | 0b0000011  # Replace opcode with Load opcode
            return insn

        # Store: sb, sh, sw
        if mnemonic in self.STORE_OPS:
            if len(operands) != 2:
                raise AssembleError(f"Line {lineno}: {mnemonic} requires 2 operands, got {len(operands)}")
            funct3 = self.STORE_OPS[mnemonic]
            rs2 = self.parse_register(operands[0])
            offset, rs1 = self._parse_mem_operand(operands[1])
            return self._encode_s_type(rs1, rs2, offset, funct3)

        # Branch: beq, bne, blt, bge, bltu, bgeu
        if mnemonic in self.BRANCH_OPS:
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: {mnemonic} requires 3 operands, got {len(operands)}")
            funct3 = self.BRANCH_OPS[mnemonic]
            rs1 = self.parse_register(operands[0])
            rs2 = self.parse_register(operands[1])
            target = self.parse_immediate(operands[2], self.labels)
            # Compute relative offset from current instruction
            offset = target - addr
            if offset % 2 != 0:
                raise AssembleError(f"Line {lineno}: Branch target misaligned")
            return self._encode_b_type(rs1, rs2, offset, funct3)

        # LUI
        if mnemonic == "lui":
            if len(operands) != 2:
                raise AssembleError(f"Line {lineno}: LUI requires 2 operands")
            rd = self.parse_register(operands[0])
            imm = self.parse_immediate(operands[1], self.labels)
            return self._encode_u_type(rd, imm)

        # AUIPC
        if mnemonic == "auipc":
            if len(operands) != 2:
                raise AssembleError(f"Line {lineno}: AUIPC requires 2 operands")
            rd = self.parse_register(operands[0])
            imm = self.parse_immediate(operands[1], self.labels)
            # Use same heuristic as LUI for the upper immediate
            insn = self._encode_u_type(rd, imm)
            # Replace opcode: AUIPC is 0b0010111, LUI is 0b0110111
            return (insn & ~0x7F) | 0b0010111

        # JAL
        if mnemonic == "jal":
            if len(operands) == 1:
                # Single-arg form: jal label (implicit x1)
                target = self.parse_immediate(operands[0], self.labels)
                offset = target - addr
                return self._encode_j_type(1, offset)
            elif len(operands) == 2:
                rd = self.parse_register(operands[0])
                target = self.parse_immediate(operands[1], self.labels)
                offset = target - addr
                return self._encode_j_type(rd, offset)
            else:
                raise AssembleError(f"Line {lineno}: JAL requires 1-2 operands")

        # JALR
        if mnemonic == "jalr":
            if len(operands) == 1:
                # Single-arg form: jalr rs1 (implicit x1 and offset 0)
                rs1 = self.parse_register(operands[0])
                insn = self._encode_i_type(1, rs1, 0, 0b000)
                return (insn & ~0x7F) | 0b1100111  # Replace opcode with JALR
            elif len(operands) == 2:
                rd = self.parse_register(operands[0])
                offset, rs1 = self._parse_mem_operand(operands[1])
                insn = self._encode_i_type(rd, rs1, offset, 0b000)
                return (insn & ~0x7F) | 0b1100111
            elif len(operands) == 3:
                rd = self.parse_register(operands[0])
                rs1 = self.parse_register(operands[1])
                imm = self.parse_immediate(operands[2])
                insn = self._encode_i_type(rd, rs1, imm, 0b000)
                return (insn & ~0x7F) | 0b1100111
            else:
                raise AssembleError(f"Line {lineno}: JALR requires 1-3 operands")

        # FENCE
        if mnemonic == "fence":
            return 0x0FF0000F

        # ECALL / EBREAK
        if mnemonic == "ecall":
            return 0x00000073
        if mnemonic == "ebreak":
            return 0x00100073

        # CSR instructions
        if mnemonic == "csrrw":
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: CSRRW requires 3 operands")
            rd = self.parse_register(operands[0])
            csr = self.parse_immediate(operands[1])
            rs1 = self.parse_register(operands[2])
            return ((csr & 0xFFF) << 20) | (rs1 << 15) | (0b001 << 12) | (rd << 7) | 0b1110011
        if mnemonic == "csrrs":
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: CSRRS requires 3 operands")
            rd = self.parse_register(operands[0])
            csr = self.parse_immediate(operands[1])
            rs1 = self.parse_register(operands[2])
            return ((csr & 0xFFF) << 20) | (rs1 << 15) | (0b010 << 12) | (rd << 7) | 0b1110011
        if mnemonic == "csrrc":
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: CSRRC requires 3 operands")
            rd = self.parse_register(operands[0])
            csr = self.parse_immediate(operands[1])
            rs1 = self.parse_register(operands[2])
            return ((csr & 0xFFF) << 20) | (rs1 << 15) | (0b011 << 12) | (rd << 7) | 0b1110011
        if mnemonic == "csrrwi":
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: CSRRWI requires 3 operands")
            rd = self.parse_register(operands[0])
            csr = self.parse_immediate(operands[1])
            zimm = self.parse_immediate(operands[2])
            return ((csr & 0xFFF) << 20) | ((zimm & 0x1F) << 15) | (0b101 << 12) | (rd << 7) | 0b1110011
        if mnemonic == "csrrsi":
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: CSRRSI requires 3 operands")
            rd = self.parse_register(operands[0])
            csr = self.parse_immediate(operands[1])
            zimm = self.parse_immediate(operands[2])
            return ((csr & 0xFFF) << 20) | ((zimm & 0x1F) << 15) | (0b110 << 12) | (rd << 7) | 0b1110011
        if mnemonic == "csrrci":
            if len(operands) != 3:
                raise AssembleError(f"Line {lineno}: CSRRCI requires 3 operands")
            rd = self.parse_register(operands[0])
            csr = self.parse_immediate(operands[1])
            zimm = self.parse_immediate(operands[2])
            return ((csr & 0xFFF) << 20) | ((zimm & 0x1F) << 15) | (0b111 << 12) | (rd << 7) | 0b1110011

        # Special pseudo: _call_auipc (internal)
        if mnemonic == "_call_auipc":
            rd = self.parse_register(operands[0])
            target = self.parse_immediate(operands[1], self.labels)
            offset = target - addr
            upper = (offset + 0x800) & 0xFFFFF000
            return self._encode_u_type(rd, upper)

        raise AssembleError(f"Line {lineno}: Unknown instruction '{mnemonic}'")