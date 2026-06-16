#!/usr/bin/env python3
"""Debug load/store test."""
import sys
sys.path.insert(0, '/root/projects/creative-projects/riscv-emu')
from riscv_emu.assembler import Assembler
from riscv_emu.cpu import CPU
from riscv_emu.memory import Memory, MemoryRegion
import struct

asm = Assembler(base_addr=0x20000000)
source = """
    lui x4, 0x20010
    addi x5, x0, 42
    sw x5, 0(x4)
    lw x6, 0(x4)
"""
code, labels = asm.assemble(source, base_addr=0x20000000)
print(f"Assembled {len(code)} bytes")

# Hex dump the code
for i in range(0, len(code), 4):
    word = struct.unpack("<I", code[i:i+4])[0]
    print(f"  0x{0x20000000 + i:08x}: 0x{word:08x}")

mem = Memory([MemoryRegion(0x20000000, 0x100000, "rwx")])
mem.write_bytes(0x20000000, bytes(code))
mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
cpu = CPU(memory=mem, pc=0x20000000)
cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)

for i in range(10):
    old_pc = cpu.pc
    try:
        insn = mem.read_word(cpu.pc)
        print(f"Step {i}: PC=0x{old_pc:08x}, insn=0x{insn:08x}", end="")
        cpu.step()
        print(f" -> PC=0x{cpu.pc:08x}, x4={cpu.get_reg(4):08x}, x5={cpu.get_reg(5):08x}, x6={cpu.get_reg(6):08x}")
    except Exception as e:
        print(f" Exception: {e}")
        break