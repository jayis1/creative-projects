#!/usr/bin/env python3
insn = 0x123450B7
opcode = insn & 0x7F
rd = (insn >> 7) & 0x1F
imm = insn & 0xFFFFF000
print(f'opcode: 0x{opcode:02x}')
print(f'rd: x{rd}')
print(f'imm: 0x{imm:08x}')

# What we want: LUI x5, 0x12345000
# LUI: opcode=0x37, rd=5, imm=0x12345000
desired = (0x12345000) | (5 << 7) | 0x37
print(f'Desired insn: 0x{desired:08x}')