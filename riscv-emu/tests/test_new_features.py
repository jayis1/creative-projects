"""Tests for new features: config, state serialization, MMIO devices, logging."""

import json
import os
import tempfile

import pytest

from riscv_emu.memory import Memory, MemoryRegion, MemoryError
from riscv_emu.cpu import CPU, Trap, CPUHalt
from riscv_emu.assembler import Assembler, AssembleError
from riscv_emu.config import (
    EmulatorConfig, CPUConfig, UARTConfig, MemoryRegionConfig, TraceConfig,
)
from riscv_emu.state import StateSerializer
from riscv_emu.devices import UARTDevice, CLINTDevice, DeviceBus, MMIODevice
from riscv_emu.csrs import CSR_MSTATUS, CSR_MIE, CSR_MIP, CSR_MTVEC, CSR_MEPC
from riscv_emu.disassembler import disassemble, disassemble_to_string


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
    cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)
    return cpu


# ============================================================
# Configuration tests
# ============================================================

class TestConfig:
    def test_default_config(self):
        config = EmulatorConfig.default()
        assert config.cpu.pc == 0x20000000
        assert config.cpu.enable_m_ext is True
        assert config.uart.enabled is True
        assert len(config.memory_regions) >= 2

    def test_config_from_dict(self):
        data = {
            "cpu": {"pc": "0x30000000", "hart_id": 2, "enable_m_ext": False},
            "uart": {"enabled": False},
            "memory_regions": [{"base": "0x30000000", "size": "0x200000", "permissions": "rwx"}],
            "log_level": "DEBUG",
        }
        config = EmulatorConfig.from_dict(data)
        assert config.cpu.pc == 0x30000000
        assert config.cpu.hart_id == 2
        assert config.cpu.enable_m_ext is False
        assert config.uart.enabled is False
        assert len(config.memory_regions) == 1

    def test_config_json_roundtrip(self):
        config = EmulatorConfig.default()
        json_str = config.to_json()
        config2 = EmulatorConfig.from_json(json_str)
        assert config2.cpu.pc == config.cpu.pc
        assert config2.uart.base_addr == config.uart.base_addr
        assert len(config2.memory_regions) == len(config.memory_regions)

    def test_config_save_and_load(self):
        config = EmulatorConfig.default()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.save(path)
            loaded = EmulatorConfig.from_file(path)
            assert loaded.cpu.pc == config.cpu.pc
            assert loaded.uart.base_addr == config.uart.base_addr
        finally:
            os.unlink(path)

    def test_config_to_dict(self):
        config = EmulatorConfig.default()
        d = config.to_dict()
        assert "cpu" in d
        assert "uart" in d
        assert "memory_regions" in d


# ============================================================
# State serialization tests
# ============================================================

class TestStateSerializer:
    def test_save_and_restore_state(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 42
            addi x6, x0, 99
        """)
        cpu.step()
        cpu.step()

        # Save state
        state = StateSerializer.save_state(cpu)

        # Verify state contents
        assert state["pc"] == cpu.pc
        assert state["registers"]["x5"] == 42
        assert state["registers"]["x6"] == 99
        assert state["instructions_executed"] == 2

    def test_save_to_file_and_restore(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 42
            addi x6, x0, 100
        """)
        cpu.step()
        cpu.step()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            StateSerializer.save_state(cpu, path)
            restored = StateSerializer.load_state(path)

            assert restored.pc == cpu.pc
            assert restored.get_reg(5) == 42
            assert restored.get_reg(6) == 100
        finally:
            os.unlink(path)

    def test_state_diff(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 10
            addi x6, x0, 20
        """)

        state_before = StateSerializer.save_state(cpu)
        cpu.step()
        cpu.step()
        state_after = StateSerializer.save_state(cpu)

        diff = StateSerializer.state_diff(state_before, state_after)
        assert "pc" in diff
        assert "registers" in diff
        assert "x5" in diff["registers"]
        assert "x6" in diff["registers"]

    def test_restore_preserves_memory(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xAB
            sw x5, 0(x4)
        """)
        # Set x4 to a valid address
        cpu.memory.add_region(MemoryRegion(0x20010000, 0x100, "rw"))
        cpu.set_reg(4, 0x20010000)
        cpu.step()
        cpu.step()

        state = StateSerializer.save_state(cpu)
        restored = StateSerializer.load_state(state)

        # Check memory was preserved
        assert restored.memory.read_word(0x20010000) == 0xAB


# ============================================================
# MMIO Devices tests
# ============================================================

class TestUARTDevice:
    def test_basic_write_read(self):
        uart = UARTDevice()
        assert uart.name == "UART"
        assert uart.base_addr == 0x10000000

    def test_uart_output(self):
        uart = UARTDevice()
        uart.write(0, ord('H'), 1)
        uart.write(0, ord('i'), 1)
        assert uart.output == "Hi"

    def test_uart_lsr_read(self):
        uart = UARTDevice()
        lsr = uart.read(5, 1)  # LSR offset
        assert lsr & 0x60  # THRE and TEMT bits set

    def test_uart_input(self):
        uart = UARTDevice()
        uart.feed_input(b"ABC")
        assert uart.read(0, 1) == ord('A')
        assert uart.read(0, 1) == ord('B')
        assert uart.read(0, 1) == ord('C')

    def test_uart_reset(self):
        uart = UARTDevice()
        uart.write(0, ord('X'), 1)
        uart.reset()
        assert len(uart._output_buffer) == 0
        assert uart.output == ""

    def test_uart_contains(self):
        uart = UARTDevice(base_addr=0x10000000, size=8)
        assert uart.contains(0x10000000)
        assert uart.contains(0x10000007)
        assert not uart.contains(0x10000008)

    def test_uart_output_bytes(self):
        uart = UARTDevice()
        uart.write(0, 0x48, 1)
        uart.write(0, 0x69, 1)
        assert uart.output_bytes == b"Hi"


class TestCLINTDevice:
    def test_mtime_counter(self):
        clint = CLINTDevice()
        assert clint.mtime == 0
        clint.mtime = 100
        assert clint.mtime == 100

    def test_mtimecmp(self):
        clint = CLINTDevice()
        # Default mtimecmp is max
        assert not clint.timer_interrupt

        clint.mtime = 100
        # Set mtimecmp low word to 40 (high word stays max, so mtimecmp = 0xFFFFFFFF00000028)
        # This is still larger than mtime=100, so timer not pending.
        # Set low and high together: mtimecmp = 40
        clint.write(0x4000, 40, 4)
        clint.write(0x4004, 0, 4)
        assert clint.timer_interrupt

    def test_clint_read_write_mtime(self):
        clint = CLINTDevice()
        clint.mtime = 0xDEADBEEF

        # Read low word
        low = clint.read(0xBFF8, 4)
        assert low == 0xDEADBEEF & 0xFFFFFFFF

        # Read high word
        high = clint.read(0xBFFC, 4)
        assert high == (0xDEADBEEF >> 32) & 0xFFFFFFFF

    def test_clint_reset(self):
        clint = CLINTDevice()
        clint.mtime = 1000
        clint.reset()
        assert clint.mtime == 0


class TestDeviceBus:
    def test_add_and_find_device(self):
        bus = DeviceBus()
        uart = UARTDevice(0x10000000, 8)
        bus.add_device(uart)
        assert bus.find_device(0x10000000) is uart
        assert bus.find_device(0x10000005) is uart
        assert bus.find_device(0x20000000) is None

    def test_device_read_write(self):
        bus = DeviceBus()
        uart = UARTDevice(0x10000000, 8)
        bus.add_device(uart)

        result = bus.write(0x10000000, ord('A'), 1)
        assert result is True

        val = bus.read(0x10000005, 1)  # LSR
        assert val is not None

        # Non-device address
        assert bus.read(0x20000000, 4) is None
        assert bus.write(0x20000000, 0, 4) is False

    def test_multiple_devices(self):
        bus = DeviceBus()
        uart = UARTDevice(0x10000000, 8)
        clint = CLINTDevice(0x2000000, 0x10000)
        bus.add_device(uart)
        bus.add_device(clint)

        assert len(bus.devices) == 2
        assert bus.find_device(0x10000000) is uart
        assert bus.find_device(0x2000000) is clint

    def test_reset_all(self):
        bus = DeviceBus()
        uart = UARTDevice(0x10000000, 8)
        bus.add_device(uart)
        uart.write(0, ord('X'), 1)
        assert uart.output == "X"

        bus.reset_all()
        assert uart.output == ""


# ============================================================
# Additional instruction tests
# ============================================================

class TestAdditionalInstructions:
    def test_slti(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, -1
            slti x6, x5, 0
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 1  # -1 < 0

    def test_sltiu(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 5
            sltiu x6, x5, 10
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 1  # 5 < 10 unsigned

    def test_xori(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xFF
            xori x6, x5, 0x0F
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 0xF0

    def test_ori(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xF0
            ori x6, x5, 0x0F
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 0xFF

    def test_andi(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 0xFF
            andi x6, x5, 0x0F
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 0x0F

    def test_slli(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 1
            slli x6, x5, 4
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 16

    def test_srli(self):
        cpu = make_cpu_with_code("""
            addi x5, x0, 16
            srli x6, x5, 4
        """)
        cpu.step()
        cpu.step()
        assert cpu.get_reg(6) == 1

    def test_srai(self):
        """Test arithmetic right shift."""
        source = """
            addi x5, x0, -16
            srai x6, x5, 2
        """
        asm = Assembler()
        code, labels = asm.assemble(source)
        mem = Memory([MemoryRegion(0x20000000, 0x100000, "rwx")])
        mem.write_bytes(0x20000000, bytes(code))
        mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
        cpu = CPU(memory=mem, pc=0x20000000)
        cpu.set_reg(2, 0x7F000000 + 0x01000000 - 16)
        cpu.step()
        cpu.step()
        # -16 >> 2 = -4 (arithmetic shift preserves sign)
        assert cpu.get_reg_signed(6) == -4

    def test_jalr(self):
        """Test JALR instruction."""
        cpu = make_cpu_with_code("""
            auipc x5, 0
            addi x5, x5, 8
            jalr x1, x5, 0
            addi x7, x0, 1
            addi x7, x0, 2
        """)
        cpu.step()  # auipc x5, 0  -> x5 = 0x20000000
        cpu.step()  # addi x5, x5, 8 -> x5 = 0x20000008
        cpu.step()  # jalr x1, x5, 0 -> jumps to x5, x1 = PC+4 = 0x2000000C
        # x1 should contain return address (PC of instruction after JALR)
        assert cpu.get_reg(1) == 0x2000000C

    def test_load_store_multiple(self):
        """Test store then load back different sizes."""
        cpu = make_cpu_with_code("""
            lui x4, 0x20010
            addi x5, x0, 0x41
            sw x5, 0(x4)
            lb x6, 0(x4)
            li x5, 0x1234
            sh x5, 4(x4)
            lhu x7, 4(x4)
        """)
        for _ in range(8):
            cpu.step()
        assert cpu.get_reg(6) == 0x41  # lb
        assert cpu.get_reg(7) == 0x1234  # lhu

    def test_ebreak(self):
        """Test that EBREAK causes a breakpoint trap."""
        cpu = make_cpu_with_code("ebreak")
        # Should trap — with no mtvec set, CPU halts
        count = cpu.run(max_instructions=10)
        assert cpu.halted

    def test_csr_rw(self):
        """Test CSR read/write via assembly."""
        cpu = make_cpu_with_code("""
            addi x5, x0, 0x88
            csrrw x6, 0x300, x5
        """)
        cpu.step()  # addi
        cpu.step()  # csrrw (0x300 = mstatus)
        assert cpu.get_reg(6) == 0  # old mstatus value
        assert cpu.csrs.read(0x300) == 0x88  # new mstatus value


# ============================================================
# Disassembler additional tests
# ============================================================

class TestDisassemblerAdditional:
    def test_disassemble_lui(self):
        result = disassemble(0x12345137, 0)
        assert "lui" in result

    def test_disassemble_auipc(self):
        result = disassemble(0x00010117, 0)
        assert "auipc" in result

    def test_disassemble_jal(self):
        result = disassemble(0x008000EF, 0x20000000)
        assert "jal" in result

    def test_disassemble_branch(self):
        result = disassemble(0x00108663, 0x20000000)
        assert "beq" in result

    def test_disassemble_load(self):
        result = disassemble(0x00042203, 0x20000000)
        assert "lw" in result

    def test_disassemble_store(self):
        result = disassemble(0x00542023, 0x20000000)
        assert "sw" in result

    def test_disassemble_mul(self):
        insn = (0b0000001 << 25) | (5 << 20) | (3 << 15) | (0b000 << 12) | (7 << 7) | 0b0110011
        result = disassemble(insn, 0)
        assert "mul" in result

    def test_disassemble_block(self):
        code = bytes.fromhex("93000000" "13000000")
        results = disassemble_to_string(code, 0)
        assert "lui" in results or "addi" in results

    def test_disassemble_unknown(self):
        result = disassemble(0xFFFFFFFF, 0)
        # Should not crash
        assert result is not None


# ============================================================
# Assembler additional tests
# ============================================================

class TestAssemblerAdditional:
    def test_assemble_auipc(self):
        a = Assembler()
        code, _ = a.assemble("auipc x5, 0x1000")
        assert len(code) == 4

    def test_assemble_jalr(self):
        a = Assembler()
        code, _ = a.assemble("jalr x1, x5, 0")
        assert len(code) == 4

    def test_assemble_store_load(self):
        a = Assembler()
        code, _ = a.assemble("""
            sw x5, 12(x2)
            lw x6, 12(x2)
        """)
        assert len(code) == 8

    def test_assemble_beqz_bnez(self):
        a = Assembler()
        code, _ = a.assemble("""
            beqz x5, target
            addi x7, x0, 1
target:
            nop
        """)
        assert len(code) == 12

    def test_assemble_bgt_ble(self):
        a = Assembler()
        code, _ = a.assemble("""
            bgt x5, x6, target
            ble x5, x6, target
target:
            nop
        """)
        assert len(code) == 12

    def test_assemble_byte_directive(self):
        a = Assembler()
        code, _ = a.assemble('.byte 0x41, 0x42, 0x43')
        assert len(code) == 3
        assert code[0] == 0x41

    def test_assemble_half_directive(self):
        a = Assembler()
        code, _ = a.assemble('.half 0x1234')
        assert len(code) == 2

    def test_assemble_multiple_errors(self):
        a = Assembler()
        with pytest.raises(AssembleError):
            a.assemble("addi x99, x0, 0")

    def test_assemble_org_directive(self):
        a = Assembler()
        code, _ = a.assemble("""
            .org 0x20000100
            nop
        """)
        assert len(code) == 4


# ============================================================
# Integration tests with UART device
# ============================================================

class TestUARTIntegration:
    def test_uart_device_with_cpu(self):
        """Test UART device bus integration with CPU."""
        bus = DeviceBus()
        uart = UARTDevice(0x10000000, 8)
        bus.add_device(uart)

        mem = Memory([MemoryRegion(0x20000000, 0x100000, "rwx")])
        mem.add_region(MemoryRegion(0x7F000000, 0x01000000, "rw"))
        mem.add_region(MemoryRegion(0x10000000, 8, "rw"))

        cpu = make_cpu_with_code("""
            lui t0, 0x10000
            li t1, 0x48
            sw t1, 0(t0)
            li t1, 0x69
            sw t1, 0(t0)
        """)

        cpu.run(max_instructions=10)
        assert "Hi" in cpu.uart_output


# ============================================================
# Config + CLI integration
# ============================================================

class TestConfigIntegration:
    def test_config_creates_memory(self):
        config = EmulatorConfig.default()
        mem = Memory([MemoryRegion(r.base, r.size, r.permissions)
                      for r in config.memory_regions])
        assert len(mem.regions) >= 2

    def test_config_custom_memory(self):
        config = EmulatorConfig(
            memory_regions=[
                MemoryRegionConfig(base=0x30000000, size=0x10000, permissions="rwx"),
            ]
        )
        assert config.memory_regions[0].base == 0x30000000

    def test_config_uart_disabled(self):
        config = EmulatorConfig(uart=UARTConfig(enabled=False))
        assert config.uart.enabled is False