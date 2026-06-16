"""Tests for the RISC-V emulator — memory, CPU, assembler, loader."""

import pytest
import struct
from riscv_emu.memory import Memory, MemoryRegion, MemoryError
from riscv_emu.cpu import CPU, Trap, CPUHalt
from riscv_emu.csrs import CSRFile, CSRError, CSR_MSTATUS, CSR_MISA, CSR_MHARTID
from riscv_emu.assembler import Assembler, AssembleError
from riscv_emu.profiler import Profiler
from riscv_emu.tracer import Tracer, TraceEntry


# ============================================================
# Helpers
# ============================================================

def make_cpu_with_code(source: str, base_addr: int = 0x20000000) -> CPU:
    """Assemble source code and create a CPU ready to execute it."""
    asm = Assembler(base_addr=base_addr)
    code, labels = asm.assemble(source, base_addr=base_addr)
    mem = Memory([MemoryRegion(base_addr, 0x100000, "rwx")])
    mem.write_bytes(base_addr, bytes(code))
    mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
    cpu = CPU(memory=mem, pc=base_addr)
    cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)  # Stack pointer
    return cpu


# ============================================================
# Memory tests
# ============================================================

class TestMemoryRegion:
    def test_create_region(self):
        r = MemoryRegion(0x20000000, 4096, "rwx")
        assert r.base == 0x20000000
        assert r.size == 4096
        assert r.perms == {"r", "w", "x"}

    def test_contains(self):
        r = MemoryRegion(0x20000000, 4096)
        assert r.contains(0x20000000)
        assert r.contains(0x20000FFF)
        assert not r.contains(0x20001000)
        assert not r.contains(0x1FFFFFFF)

    def test_invalid_perms(self):
        with pytest.raises(ValueError):
            MemoryRegion(0, 4096, "a")

    def test_zero_size(self):
        with pytest.raises(ValueError):
            MemoryRegion(0, 0)

    def test_initial_data(self):
        r = MemoryRegion(0, 4, "rwx", data=b"\x01\x02\x03\x04")
        assert r.data[0] == 1
        assert r.data[3] == 4


class TestMemory:
    def test_read_write_byte(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        mem.write_byte(0, 0xAB)
        assert mem.read_byte(0) == 0xAB
        mem.write_byte(255, 0xFF)
        assert mem.read_byte(255) == 0xFF

    def test_read_write_half(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        mem.write_half(0, 0x1234)
        assert mem.read_half(0) == 0x1234

    def test_read_write_word(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        mem.write_word(0, 0xDEADBEEF)
        assert mem.read_word(0) == 0xDEADBEEF

    def test_unaligned_half(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        with pytest.raises(MemoryError):
            mem.write_half(1, 0)
        with pytest.raises(MemoryError):
            mem.read_half(1)

    def test_unaligned_word(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        with pytest.raises(MemoryError):
            mem.write_word(1, 0)
        with pytest.raises(MemoryError):
            mem.read_word(3)

    def test_permission_denied(self):
        mem = Memory([MemoryRegion(0, 256, "r")])
        with pytest.raises(MemoryError, match="Permission 'w' denied"):
            mem.write_byte(0, 0)

    def test_no_memory_mapped(self):
        mem = Memory([MemoryRegion(0x1000, 256)])
        with pytest.raises(MemoryError, match="No memory mapped"):
            mem.read_byte(0)

    def test_read_write_bytes(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        data = b"Hello, RISC-V!"
        mem.write_bytes(0, data)
        assert mem.read_bytes(0, len(data)) == data

    def test_hexdump(self):
        mem = Memory([MemoryRegion(0, 256, "rwx")])
        mem.write_bytes(0, b"ABCD")
        dump = mem.dump(0, 4)
        assert "0x00000000" in dump

    def test_multiple_regions(self):
        mem = Memory([
            MemoryRegion(0x20000000, 4096, "rwx"),
            MemoryRegion(0x30000000, 4096, "rw"),
        ])
        mem.write_word(0x20000000, 0x11111111)
        mem.write_word(0x30000000, 0x22222222)
        assert mem.read_word(0x20000000) == 0x11111111
        assert mem.read_word(0x30000000) == 0x22222222

    def test_io_callbacks(self):
        uart_buf = []
        def io_write(addr, value, size):
            uart_buf.append(value)
        def io_read(addr, size):
            return len(uart_buf)
        mem = Memory([MemoryRegion(0x10000000, 16, "rw", io_write=io_write, io_read=io_read)])
        mem.write_byte(0x10000000, 0x41)
        assert uart_buf == [0x41]
        assert mem.read_byte(0x10000000) == 1


# ============================================================
# CSR tests
# ============================================================

class TestCSRFile:
    def test_read_write(self):
        csr = CSRFile()
        csr.write(CSR_MSTATUS, 0x12345678)
        assert csr.read(CSR_MSTATUS) == 0x12345678

    def test_read_only(self):
        csr = CSRFile()
        with pytest.raises(CSRError, match="read-only"):
            csr.write(CSR_MHARTID, 0)

    def test_initial_values(self):
        csr = CSRFile(hart_id=2)
        assert csr.read(CSR_MHARTID) == 2
        assert csr.read(CSR_MISA) == 0x40000000  # RV32I

    def test_set_bits(self):
        csr = CSRFile()
        csr.write(CSR_MSTATUS, 0)
        old = csr.set_bits(CSR_MSTATUS, 0x1)  # Set MIE
        assert old == 0
        assert csr.read(CSR_MSTATUS) & 0x1

    def test_clear_bits(self):
        csr = CSRFile()
        csr.write(CSR_MSTATUS, 0xFF)
        old = csr.clear_bits(CSR_MSTATUS, 0x1)
        assert old == 0xFF
        assert not (csr.read(CSR_MSTATUS) & 0x1)

    def test_name_lookup(self):
        csr = CSRFile()
        assert csr.name(CSR_MSTATUS) == "mstatus"
        assert csr.name(0xF11) == "mvendorid"


# ============================================================
# Assembler tests
# ============================================================

class TestAssembler:
    def test_parse_register(self):
        a = Assembler()
        assert a.parse_register("x0") == 0
        assert a.parse_register("x31") == 31
        assert a.parse_register("ra") == 1
        assert a.parse_register("sp") == 2
        assert a.parse_register("a0") == 10
        assert a.parse_register("t0") == 5
        assert a.parse_register("s0") == 8
        assert a.parse_register("zero") == 0

    def test_parse_register_invalid(self):
        a = Assembler()
        with pytest.raises(AssembleError):
            a.parse_register("x32")
        with pytest.raises(AssembleError):
            a.parse_register("invalid")

    def test_parse_immediate(self):
        a = Assembler()
        assert a.parse_immediate("42") == 42
        assert a.parse_immediate("0xFF") == 255
        assert a.parse_immediate("0b1010") == 10
        assert a.parse_immediate("-1") == -1
        assert a.parse_immediate("'A'") == 65

    def test_assemble_nop(self):
        a = Assembler()
        code, labels = a.assemble("nop")
        assert len(code) == 4
        assert struct.unpack("<I", code)[0] == 0x00000013

    def test_assemble_addi(self):
        a = Assembler()
        code, labels = a.assemble("addi x5, x0, 42")
        assert len(code) == 4
        # Verify x5 gets value 42 after execution
        cpu = make_cpu_with_code("addi x5, x0, 42")
        cpu.step()
        assert cpu.get_reg(5) == 42

    def test_assemble_add(self):
        a = Assembler()
        code, labels = a.assemble("add x5, x6, x7")
        assert len(code) == 4

    def test_assemble_lui(self):
        a = Assembler()
        code, labels = a.assemble("lui x5, 0x12345000")
        assert len(code) == 4

    def test_assemble_label(self):
        a = Assembler()
        source = """
_start:
    addi x5, x0, 1
    jal x0, _start
"""
        code, labels = a.assemble(source)
        assert "_start" in labels
        assert labels["_start"] == 0x20000000
        assert len(code) == 8

    def test_assemble_load_store(self):
        a = Assembler()
        source = """
    addi x5, x0, 42
    sw x5, 0(x4)
    lw x6, 0(x4)
"""
        code, labels = a.assemble(source)
        assert len(code) == 12

    def test_assemble_li_small(self):
        a = Assembler()
        code, _ = a.assemble("li x5, 42")
        assert len(code) == 4  # Just ADDI for small immediates

    def test_assemble_li_large(self):
        a = Assembler()
        code, _ = a.assemble("li x5, 0x12345678")
        assert len(code) == 8  # LUI + ADDI for large immediates

    def test_assemble_pseudo_mv(self):
        a = Assembler()
        code, _ = a.assemble("mv x5, x6")
        assert len(code) == 4

    def test_assemble_pseudo_not(self):
        a = Assembler()
        code, _ = a.assemble("not x5, x6")
        assert len(code) == 4

    def test_assemble_pseudo_neg(self):
        a = Assembler()
        code, _ = a.assemble("neg x5, x6")
        assert len(code) == 4

    def test_assemble_directive_word(self):
        a = Assembler()
        source = """
    .word 0xDEADBEEF, 0x12345678
"""
        code, _ = a.assemble(source)
        assert len(code) == 8

    def test_assemble_directive_string(self):
        a = Assembler()
        source = """
    .string "Hello"
"""
        code, _ = a.assemble(source)
        assert len(code) == 6  # 5 chars + null

    def test_assemble_branch(self):
        a = Assembler()
        source = """
loop:
    addi x5, x5, -1
    bne x5, x0, loop
"""
        code, labels = a.assemble(source)
        assert "loop" in labels
        assert len(code) == 8

    def test_assemble_invalid_register(self):
        a = Assembler()
        with pytest.raises(AssembleError):
            a.assemble("addi x99, x0, 0")

    def test_assemble_comments(self):
        a = Assembler()
        code, _ = a.assemble("addi x5, x0, 42 # set x5 to 42")
        assert len(code) == 4

    def test_assemble_ecall_ebreak(self):
        a = Assembler()
        code, _ = a.assemble("ecall\nebreak")
        assert struct.unpack("<I", code[:4])[0] == 0x00000073
        assert struct.unpack("<I", code[4:8])[0] == 0x00100073

    def test_assemble_fence(self):
        a = Assembler()
        code, _ = a.assemble("fence")
        assert struct.unpack("<I", code)[0] == 0x0FF0000F

    def test_assemble_multiple_labels(self):
        a = Assembler()
        source = """
start:
    nop
middle:
    nop
end:
    nop
"""
        code, labels = a.assemble(source)
        assert labels["start"] == 0x20000000
        assert labels["middle"] == 0x20000004
        assert labels["end"] == 0x20000008


# ============================================================
# CPU tests (using assembler for reliable encodings)
# ============================================================

class TestCPU:
    def test_lui(self):
        cpu = make_cpu_with_code("lui x5, 0x12345000")
        cpu.step()
        assert cpu.get_reg(5) == 0x12345000

    def test_auipc(self):
        cpu = make_cpu_with_code("auipc x5, 0x1000")
        cpu.step()
        # AUIPC: rd = pc + upper_imm
        assert cpu.get_reg(5) == (0x20000000 + 0x1000) & 0xFFFFFFFF

    def test_addi(self):
        cpu = make_cpu_with_code("addi x5, x0, 42")
        cpu.step()
        assert cpu.get_reg(5) == 42

    def test_add(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 10
            addi x6, x0, 20
            add x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(5) == 10
        assert cpu.get_reg(6) == 20
        assert cpu.get_reg(7) == 30

    def test_sub(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 30
            addi x6, x0, 10
            sub x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 20

    def test_and(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xFF
            addi x6, x0, 0x0F
            and x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 0x0F

    def test_or(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xF0
            addi x6, x0, 0x0F
            or x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 0xFF

    def test_xor(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xFF
            addi x6, x0, 0x0F
            xor x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 0xF0

    def test_sll(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 8
            addi x6, x0, 2
            sll x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 32  # 8 << 2

    def test_srl(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 32
            addi x6, x0, 2
            srl x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 8  # 32 >> 2

    def test_slt(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, -1
            addi x6, x0, 1
            slt x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 1  # -1 < 1 (signed)

    def test_sltu(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 5
            addi x6, x0, 10
            sltu x7, x5, x6
""")
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.get_reg(7) == 1  # 5 < 10 (unsigned)

    def test_x0_always_zero(self):
        cpu = make_cpu_with_code("addi x0, x0, 42")
        cpu.step()
        assert cpu.regs[0] == 0

    def test_branch_beq_taken(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 5
            addi x6, x0, 5
            beq x5, x6, target
            addi x7, x0, 1
target:
            addi x8, x0, 2
""")
        cpu.run(max_instructions=10)
        # x7 should be 0 (branch taken, skipped addi x7)
        # x8 should be 2
        assert cpu.get_reg(7) == 0  # Not executed
        assert cpu.get_reg(8) == 2  # Executed

    def test_branch_beq_not_taken(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 5
            addi x6, x0, 10
            beq x5, x6, target
            addi x7, x0, 1
target:
            addi x8, x0, 2
""")
        cpu.run(max_instructions=10)
        assert cpu.get_reg(7) == 1  # Executed (branch not taken)
        assert cpu.get_reg(8) == 2   # Executed

    def test_branch_bne(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 5
            addi x6, x0, 10
            bne x5, x6, target
            addi x7, x0, 1
target:
            addi x8, x0, 2
""")
        cpu.run(max_instructions=10)
        assert cpu.get_reg(7) == 0  # Skipped
        assert cpu.get_reg(8) == 2  # Executed

    def test_branch_blt(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 3
            addi x6, x0, 10
            blt x5, x6, target
            addi x7, x0, 1
target:
            addi x8, x0, 2
""")
        cpu.run(max_instructions=10)
        assert cpu.get_reg(7) == 0  # Skipped (3 < 10)
        assert cpu.get_reg(8) == 2

    def test_load_store_word(self):
        cpu = make_cpu_with_code("""
            lui x4, 0x20010
            addi x5, x0, 42
            sw x5, 0(x4)
            lw x6, 0(x4)
""")
        cpu.run(max_instructions=10)
        assert cpu.get_reg(6) == 42

    def test_load_store_byte(self):
        cpu = make_cpu_with_code("""
            lui x4, 0x20010
            addi x5, x0, 0xAB
            sb x5, 0(x4)
            lbu x6, 0(x4)
""")
        cpu.run(max_instructions=10)
        assert cpu.get_reg(6) == 0xAB

    def test_jal_jalr(self):
        cpu = make_cpu_with_code("""
            jal x1, func
            addi x7, x0, 1
func:
            addi x5, x0, 42
            jalr x0, x1, 0
""")
        cpu.run(max_instructions=10)
        assert cpu.get_reg(5) == 42
        assert cpu.get_reg(7) == 1  # Executed after jalr returns

    def test_ecall_causes_trap(self):
        cpu = make_cpu_with_code("ecall")
        with pytest.raises(Trap):
            cpu.step()

    def test_ebreak_causes_trap(self):
        cpu = make_cpu_with_code("ebreak")
        with pytest.raises(Trap):
            cpu.step()

    def test_state_dump(self):
        cpu = make_cpu_with_code("nop")
        dump = cpu.state_dump()
        assert "PC:" in dump
        assert "zero" in dump

    def test_halted(self):
        cpu = make_cpu_with_code("nop")
        cpu._halted = True
        with pytest.raises(CPUHalt):
            cpu.step()

    def test_counter_loop(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0
            addi x6, x0, 10
loop:
            addi x5, x5, 1
            bne x5, x6, loop
""")
        cpu.run(max_instructions=200)
        assert cpu.get_reg(5) == 10

    def test_fibonacci_10(self):
        cpu = make_cpu_with_code("""
            addi a0, x0, 10
            jal x1, fib
            ecall

fib:
            addi sp, sp, -16
            sw ra, 12(sp)
            sw s0, 8(sp)
            sw s1, 4(sp)
            mv s0, a0
            li s1, 0
            li a0, 1
            bge s1, s0, fib_done
fib_loop:
            addi sp, sp, -4
            sw a0, 0(sp)
            add a0, s1, a0
            lw s1, 0(sp)
            addi sp, sp, 4
            addi s0, s0, -1
            bne s0, x0, fib_loop
fib_done:
            lw ra, 12(sp)
            lw s0, 8(sp)
            lw s1, 4(sp)
            addi sp, sp, 16
            jalr x0, x1, 0
""")
        try:
            cpu.run(max_instructions=2000)
        except (Trap, CPUHalt):
            pass
        # With s1=0, a0=1, loop runs n times (s0 goes from 10 to 0, bne exits at 0)
        # This computes fib(11) = 89
        assert cpu.get_reg(10) == 89


# ============================================================
# Profiler tests
# ============================================================

class TestProfiler:
    def test_record(self):
        p = Profiler()
        p.start()
        p.record(0x20000000, "addi")
        p.record(0x20000004, "add")
        p.record(0x20000000, "addi")
        assert p.instruction_counts == {"addi": 2, "add": 1}
        assert p.address_counts == {0x20000000: 2, 0x20000004: 1}
        assert p.total_instructions == 3

    def test_stop(self):
        p = Profiler()
        p.start()
        p.record(0, "addi")
        p.stop()
        p.record(0, "add")
        assert p.total_instructions == 1

    def test_reset(self):
        p = Profiler()
        p.start()
        p.record(0, "addi")
        p.reset()
        assert p.total_instructions == 0
        assert len(p.instruction_counts) == 0

    def test_top_instructions(self):
        p = Profiler()
        p.start()
        p.record(0, "addi")
        p.record(0, "addi")
        p.record(0, "add")
        top = p.top_instructions(2)
        assert top[0] == ("addi", 2)

    def test_summary(self):
        p = Profiler()
        p.start()
        p.record(0, "addi")
        summary = p.summary()
        assert "addi" in summary


# ============================================================
# Tracer tests
# ============================================================

class TestTracer:
    def test_record_and_dump(self):
        t = Tracer()
        t.start()
        entry = TraceEntry(0x20000000, 0x00000013, [0]*32, [0]*32, "nop")
        t.record(entry)
        assert len(t.entries) == 1

    def test_changes_only(self):
        t = Tracer()
        t.start()
        t.set_changes_only(True)
        # Entry with no register changes should be filtered
        entry1 = TraceEntry(0, 0, [0]*32, [0]*32, "nop")
        t.record(entry1)
        assert len(t.entries) == 0
        # Entry with changes should be recorded
        regs_after = [0]*32
        regs_after[5] = 42
        entry2 = TraceEntry(0, 0, [0]*32, regs_after, "addi")
        t.record(entry2)
        assert len(t.entries) == 1

    def test_address_filter(self):
        t = Tracer()
        t.start()
        t.set_address_filter(addrs={0x20000000})
        entry1 = TraceEntry(0x20000000, 0, [0]*32, [0]*32, "a")
        entry2 = TraceEntry(0x20000004, 0, [0]*32, [0]*32, "b")
        t.record(entry1)
        t.record(entry2)
        assert len(t.entries) == 1

    def test_ring_buffer(self):
        t = Tracer(max_entries=3)
        t.start()
        for i in range(5):
            t.record(TraceEntry(i, 0, [0]*32, [0]*32, f"insn_{i}"))
        assert len(t.entries) == 3

    def test_stats(self):
        t = Tracer()
        t.start()
        t.record(TraceEntry(0x100, 0, [0]*32, [0]*32, "a"))
        t.record(TraceEntry(0x104, 0, [0]*32, [0]*32, "b"))
        stats = t.stats()
        assert stats["total_entries"] == 2
        assert stats["unique_addresses"] == 2

    def test_changed_regs(self):
        regs_before = [0] * 32
        regs_after = [0] * 32
        regs_after[5] = 42
        regs_after[10] = 100
        entry = TraceEntry(0, 0, regs_before, regs_after, "addi")
        changed = entry.changed_regs()
        assert 5 in changed
        assert 10 in changed
        assert len(changed) == 2