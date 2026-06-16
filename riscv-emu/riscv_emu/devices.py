"""MMIO device framework for the RISC-V emulator.

Provides a pluggable device system for memory-mapped I/O,
including CLINT (Core Local Interruptor) for timer interrupts
and a generic MMIO device interface.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MMIODevice:
    """Base class for memory-mapped I/O devices.

    Subclasses should override read() and write() to implement
    device-specific behavior.
    """

    def __init__(self, name: str, base_addr: int, size: int):
        self.name = name
        self.base_addr = base_addr
        self.size = size

    def read(self, offset: int, size: int) -> int:
        """Handle a read from this device. Override in subclasses.

        Args:
            offset: Offset from base_addr (0 to size-1).
            size: Access width in bytes (1, 2, 4).

        Returns:
            Value read from device.
        """
        raise NotImplementedError(f"{self.name}: read at offset 0x{offset:x} not implemented")

    def write(self, offset: int, value: int, size: int) -> None:
        """Handle a write to this device. Override in subclasses.

        Args:
            offset: Offset from base_addr (0 to size-1).
            value: Value to write.
            size: Access width in bytes (1, 2, 4).
        """
        raise NotImplementedError(f"{self.name}: write at offset 0x{offset:x} not implemented")

    def contains(self, addr: int) -> bool:
        """Check if an address falls within this device's range."""
        return self.base_addr <= addr < self.base_addr + self.size

    def tick(self, cpu: 'CPU') -> None:
        """Called once per CPU cycle. Override for periodic device behavior.

        Args:
            cpu: The CPU instance (for raising interrupts, etc.).
        """
        pass

    def reset(self) -> None:
        """Reset device to initial state."""
        pass

    def __repr__(self) -> str:
        return f"{self.name}(base=0x{self.base_addr:08x}, size=0x{self.size:x})"


class UARTDevice(MMIODevice):
    """QEMU-virt compatible 16550 UART for character I/O.

    Memory map (simplified):
      0x00: THR/RBR — Transmit Holding Register / Receive Buffer Register
      0x01: IER      — Interrupt Enable Register
      0x02: IIR/FCR  — Interrupt Identification / FIFO Control Register
      0x03: LCR      — Line Control Register
      0x04: MCR      — Modem Control Register
      0x05: LSR      — Line Status Register
      0x06: MSR      — Modem Status Register
      0x07: SCR      — Scratch Register
    """

    # LSR bits
    LSR_DR = 0x01    # Data Ready
    LSR_OE = 0x02    # Overrun Error
    LSR_PE = 0x04    # Parity Error
    LSR_FE = 0x08    # Framing Error
    LSR_BI = 0x10    # Break Indicator
    LSR_THRE = 0x20  # Transmitter Holding Register Empty
    LSR_TEMT = 0x40  # Transmitter Empty
    LSR_FIFOE = 0x80 # FIFO Error

    def __init__(self, base_addr: int = 0x10000000, size: int = 8):
        super().__init__("UART", base_addr, size)
        self._output_buffer: List[int] = []
        self._input_buffer: List[int] = []
        self._ier: int = 0
        self._lcr: int = 0
        self._mcr: int = 0
        self._lsr: int = self.LSR_THRE | self.LSR_TEMT
        self._msr: int = 0
        self._scr: int = 0

    @property
    def output(self) -> str:
        """Get all UART output as a string."""
        return "".join(
            chr(b) if 0x20 <= b < 0x7F or b in (0x0A, 0x0D) else f"\\x{b:02x}"
            for b in self._output_buffer
        )

    @property
    def output_bytes(self) -> bytes:
        """Get all UART output as bytes."""
        return bytes(self._output_buffer)

    def feed_input(self, data: bytes) -> None:
        """Feed input data to the UART (simulates keyboard input)."""
        self._input_buffer.extend(data)
        self._lsr |= self.LSR_DR

    def read(self, offset: int, size: int) -> int:
        if offset == 0x00:  # RBR
            if self._input_buffer:
                val = self._input_buffer.pop(0)
                if not self._input_buffer:
                    self._lsr &= ~self.LSR_DR
                return val
            return 0
        elif offset == 0x01:  # IER
            return self._ier
        elif offset == 0x02:  # IIR
            return 0x01  # No interrupt pending
        elif offset == 0x03:  # LCR
            return self._lcr
        elif offset == 0x04:  # MCR
            return self._mcr
        elif offset == 0x05:  # LSR
            return self._lsr
        elif offset == 0x06:  # MSR
            return self._msr
        elif offset == 0x07:  # SCR
            return self._scr
        return 0

    def write(self, offset: int, value: int, size: int) -> None:
        if offset == 0x00:  # THR
            ch = value & 0xFF
            self._output_buffer.append(ch)
        elif offset == 0x01:  # IER
            self._ier = value & 0x0F
        elif offset == 0x02:  # FCR
            pass  # FIFO control, ignore for now
        elif offset == 0x03:  # LCR
            self._lcr = value
        elif offset == 0x04:  # MCR
            self._mcr = value
        elif offset == 0x05:  # LSR (read-only)
            pass
        elif offset == 0x06:  # MSR (read-only)
            pass
        elif offset == 0x07:  # SCR
            self._scr = value

    def reset(self) -> None:
        self._output_buffer.clear()
        self._input_buffer.clear()
        self._ier = 0
        self._lcr = 0
        self._mcr = 0
        self._lsr = self.LSR_THRE | self.LSR_TEMT
        self._msr = 0
        self._scr = 0


class CLINTDevice(MMIODevice):
    """Core Local Interruptor (CLINT) for RISC-V timer interrupts.

    Provides mtime and mtimecmp registers for timer interrupt generation.

    Memory map:
      0x0000-0x3FFF: Reserved / MSIP registers (per-hart)
      0x4000-0xBFFF: mtimecmp registers (per-hart, 64-bit)
      0xBFF8-0xBFFF: mtime register (64-bit)
    """

    def __init__(self, base_addr: int = 0x2000000, num_harts: int = 1):
        super().__init__("CLINT", base_addr, 0x10000)
        self._mtime: int = 0
        self._mtimecmp: List[int] = [0xFFFFFFFFFFFFFFFF] * num_harts
        self._msip: List[int] = [0] * num_harts
        self._num_harts = num_harts
        self._timer_interrupt_pending: bool = False

    @property
    def mtime(self) -> int:
        """Current mtime value."""
        return self._mtime

    @mtime.setter
    def mtime(self, value: int) -> None:
        self._mtime = value & 0xFFFFFFFFFFFFFFFF

    @property
    def timer_interrupt(self) -> bool:
        """Whether a timer interrupt is pending."""
        return self._mtime >= self._mtimecmp[0]

    def tick(self, cpu: 'CPU') -> None:
        """Increment mtime and check for timer interrupt."""
        self._mtime += 1
        if self._mtime >= self._mtimecmp[0]:
            self._timer_interrupt_pending = True
            # Set MTIP bit in mip
            from .csrs import CSR_MIP
            mip = cpu.csrs.read(CSR_MIP)
            cpu.csrs.write(CSR_MIP, mip | (1 << 7))  # MTIP
        else:
            self._timer_interrupt_pending = False
            from .csrs import CSR_MIP
            mip = cpu.csrs.read(CSR_MIP)
            cpu.csrs.write(CSR_MIP, mip & ~(1 << 7))

    def read(self, offset: int, size: int) -> int:
        # mtimecmp for hart 0
        if 0x4000 <= offset < 0x4008:
            val = self._mtimecmp[0]
            if size == 4:
                if offset == 0x4000:
                    return val & 0xFFFFFFFF
                else:
                    return (val >> 32) & 0xFFFFFFFF
            return val & 0xFFFFFFFFFFFFFFFF
        # mtime
        elif 0xBFF8 <= offset < 0xC000:
            if size == 4:
                if offset == 0xBFF8:
                    return self._mtime & 0xFFFFFFFF
                else:
                    return (self._mtime >> 32) & 0xFFFFFFFF
            return self._mtime & 0xFFFFFFFFFFFFFFFF
        # msip
        elif offset < 0x4000:
            hart = offset // 4
            if hart < self._num_harts:
                return self._msip[hart]
        return 0

    def write(self, offset: int, value: int, size: int) -> None:
        # msip
        if offset < 0x4000:
            hart = offset // 4
            if hart < self._num_harts:
                self._msip[hart] = value & 1
        # mtimecmp for hart 0
        elif 0x4000 <= offset < 0x4008:
            if size == 4:
                if offset == 0x4000:
                    self._mtimecmp[0] = (self._mtimecmp[0] & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
                else:
                    self._mtimecmp[0] = (self._mtimecmp[0] & 0xFFFFFFFF) | ((value & 0xFFFFFFFF) << 32)
            else:
                self._mtimecmp[0] = value & 0xFFFFFFFFFFFFFFFF
        # mtime
        elif 0xBFF8 <= offset < 0xC000:
            if size == 4:
                if offset == 0xBFF8:
                    self._mtime = (self._mtime & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)
                else:
                    self._mtime = (self._mtime & 0xFFFFFFFF) | ((value & 0xFFFFFFFF) << 32)
            else:
                self._mtime = value & 0xFFFFFFFFFFFFFFFF

    def reset(self) -> None:
        self._mtime = 0
        self._mtimecmp = [0xFFFFFFFFFFFFFFFF] * self._num_harts
        self._msip = [0] * self._num_harts
        self._timer_interrupt_pending = False


class DeviceBus:
    """Manages MMIO devices and routes read/write requests.

    Devices are checked in order for address matching.
    Provides a unified interface for the CPU to interact with devices.
    """

    def __init__(self):
        self._devices: List[MMIODevice] = []

    def add_device(self, device: MMIODevice) -> None:
        """Register an MMIO device on the bus."""
        self._devices.append(device)
        logger.debug(f"Added device: {device}")

    def find_device(self, addr: int) -> Optional[MMIODevice]:
        """Find the device that handles the given address."""
        for dev in self._devices:
            if dev.contains(addr):
                return dev
        return None

    def read(self, addr: int, size: int) -> Optional[int]:
        """Read from an MMIO device at the given address.

        Returns None if no device handles the address.
        """
        dev = self.find_device(addr)
        if dev:
            offset = addr - dev.base_addr
            return dev.read(offset, size)
        return None

    def write(self, addr: int, value: int, size: int) -> bool:
        """Write to an MMIO device at the given address.

        Returns True if a device handled the write, False otherwise.
        """
        dev = self.find_device(addr)
        if dev:
            offset = addr - dev.base_addr
            dev.write(offset, value, size)
            return True
        return False

    def tick_all(self, cpu: 'CPU') -> None:
        """Tick all devices (call once per CPU cycle)."""
        for dev in self._devices:
            dev.tick(cpu)

    def reset_all(self) -> None:
        """Reset all devices to initial state."""
        for dev in self._devices:
            dev.reset()

    @property
    def devices(self) -> List[MMIODevice]:
        """List all registered devices."""
        return list(self._devices)

    def __repr__(self) -> str:
        return f"DeviceBus(devices={self._devices})"