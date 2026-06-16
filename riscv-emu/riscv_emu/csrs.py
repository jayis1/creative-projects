"""CSR (Control and Status Register) file for the RISC-V emulator.

Implements the standard Zicsr extension CSRs for RV32I:
  - mstatus, misa, mdeleg, medeleg, mie, mip, mtvec, mepc, mcause, mtval, mscratch
  - cycle, time, instret (performance counters)
  - mvendorid, marchid, mimpid, mhartid (identification)
"""

from __future__ import annotations
from typing import Dict, Optional


class CSRError(Exception):
    """Raised on invalid CSR access."""
    pass


# CSR address constants (RV32I standard)
CSR_MSTATUS   = 0x300
CSR_MISA      = 0x301
CSR_MEDELEG   = 0x302
CSR_MIDELEG   = 0x303
CSR_MIE       = 0x304
CSR_MTVEC     = 0x305
CSR_MSCRATCH  = 0x340
CSR_MEPC      = 0x341
CSR_MCAUSE    = 0x342
CSR_MTVAL     = 0x343
CSR_MIP       = 0x344
CSR_CYCLE     = 0xC00
CSR_TIME      = 0xC01
CSR_INSTRET   = 0xC02
CSR_MVENDORID = 0xF11
CSR_MARCHID   = 0xF12
CSR_MIMPID    = 0xF13
CSR_MHARTID   = 0xF14

# mstatus bits
MSTATUS_UIE   = 1 << 0
MSTATUS_SIE   = 1 << 1
MSTATUS_MIE   = 1 << 3
MSTATUS_UPIE  = 1 << 4
MSTATUS_SPIE  = 1 << 5
MSTATUS_MPIE  = 1 << 7
MSTATUS_SPP   = 1 << 8
MSTATUS_MPP   = 3 << 11

# Interrupt/Exception cause codes
CAUSE_MISALIGNED_FETCH = 0
CAUSE_FETCH_ACCESS     = 1
CAUSE_ILLEGAL_INSN     = 2
CAUSE_BREAKPOINT       = 3
CAUSE_MISALIGNED_LOAD  = 4
CAUSE_LOAD_ACCESS      = 5
CAUSE_MISALIGNED_STORE = 6
CAUSE_STORE_ACCESS     = 7
CAUSE_ECALL_U          = 8
CAUSE_ECALL_S          = 9
CAUSE_ECALL_M          = 11
CAUSE_FETCH_PAGE_FAULT = 12
CAUSE_LOAD_PAGE_FAULT  = 13
CAUSE_STORE_PAGE_FAULT = 15


class CSRFile:
    """RISC-V Control and Status Register file."""

    # Names for known CSRs
    NAMES: Dict[int, str] = {
        CSR_MSTATUS: "mstatus", CSR_MISA: "misa", CSR_MEDELEG: "medeleg",
        CSR_MIDELEG: "mideleg", CSR_MIE: "mie", CSR_MTVEC: "mtvec",
        CSR_MSCRATCH: "mscratch", CSR_MEPC: "mepc", CSR_MCAUSE: "mcause",
        CSR_MTVAL: "mtval", CSR_MIP: "mip", CSR_CYCLE: "cycle",
        CSR_TIME: "time", CSR_INSTRET: "instret",
        CSR_MVENDORID: "mvendorid", CSR_MARCHID: "marchid",
        CSR_MIMPID: "mimpid", CSR_MHARTID: "mhartid",
    }

    def __init__(self, hart_id: int = 0):
        self._regs: Dict[int, int] = {}
        # Initialize defaults per spec
        self._regs[CSR_MSTATUS] = 0
        self._regs[CSR_MISA] = 0x40000000  # RV32I
        self._regs[CSR_MEDELEG] = 0
        self._regs[CSR_MIDELEG] = 0
        self._regs[CSR_MIE] = 0
        self._regs[CSR_MTVEC] = 0
        self._regs[CSR_MSCRATCH] = 0
        self._regs[CSR_MEPC] = 0
        self._regs[CSR_MCAUSE] = 0
        self._regs[CSR_MTVAL] = 0
        self._regs[CSR_MIP] = 0
        # Performance counters
        self._regs[CSR_CYCLE] = 0
        self._regs[CSR_TIME] = 0
        self._regs[CSR_INSTRET] = 0
        # Identification
        self._regs[CSR_MVENDORID] = 0  # Not a commercial impl
        self._regs[CSR_MARCHID] = 0  # Open-source, no arch ID
        self._regs[CSR_MIMPID] = 0
        self._regs[CSR_MHARTID] = hart_id
        # Track which CSRs are read-only
        self._readonly: Dict[int, bool] = {
            CSR_MVENDORID: True, CSR_MARCHID: True,
            CSR_MIMPID: True, CSR_MHARTID: True,
        }

    def read(self, addr: int) -> int:
        """Read a CSR by address. Returns 32-bit unsigned value."""
        if addr not in self._regs:
            raise CSRError(f"Unknown CSR 0x{addr:03x}")
        return self._regs[addr] & 0xFFFFFFFF

    def write(self, addr: int, value: int) -> None:
        """Write a CSR by address. Value is masked to 32 bits."""
        if addr in self._readonly and self._readonly[addr]:
            raise CSRError(f"CSR 0x{addr:03x} ({self.NAMES.get(addr, '???')}) is read-only")
        self._regs[addr] = value & 0xFFFFFFFF

    def set_bits(self, addr: int, mask: int) -> None:
        """CSRRS: read CSR, set bits in mask, write back. Returns old value."""
        old = self.read(addr)
        new = old | (mask & 0xFFFFFFFF)
        if mask != 0:  # Only write if mask is nonzero (otherwise it's just a read)
            self.write(addr, new)
        return old

    def clear_bits(self, addr: int, mask: int) -> None:
        """CSRRC: read CSR, clear bits in mask, write back. Returns old value."""
        old = self.read(addr)
        new = old & ~(mask & 0xFFFFFFFF)
        if mask != 0:
            self.write(addr, new)
        return old

    def write_bits(self, addr: int, value: int, mask: int) -> None:
        """CSRRCWI/CSRRSI: write value to bits specified by mask."""
        old = self.read(addr)
        new = (old & ~mask) | (value & mask)
        self.write(addr, new)
        return old

    def name(self, addr: int) -> str:
        """Return human-readable name for a CSR address."""
        return self.NAMES.get(addr, f"csr_0x{addr:03x}")

    def increment_counter(self, csr: int, amount: int = 1) -> None:
        """Increment a performance counter CSR (cycle, instret, time)."""
        if csr in self._regs:
            self._regs[csr] = (self._regs[csr] + amount) & 0xFFFFFFFF

    def __repr__(self) -> str:
        lines = []
        for addr in sorted(self._regs):
            name = self.NAMES.get(addr, f"0x{addr:03x}")
            val = self._regs[addr]
            lines.append(f"  {name:>12s} = 0x{val:08x}")
        return "CSRFile(\n" + "\n".join(lines) + "\n)"