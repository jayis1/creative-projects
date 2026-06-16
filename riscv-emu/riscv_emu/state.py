"""State serialization for the RISC-V emulator.

Supports saving and loading complete CPU/memory state to/from JSON files.
Enables checkpoint/restore functionality and state inspection.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional

from .cpu import CPU
from .memory import Memory, MemoryRegion

logger = logging.getLogger(__name__)


class StateSerializer:
    """Serialize and deserialize emulator state to/from JSON.

    Supports:
      - CPU register state
      - Program counter and privilege mode
      - CSR values
      - Memory contents
      - UART output buffer
    """

    # State format version for forward compatibility
    VERSION = 2

    @staticmethod
    def save_state(cpu: CPU, path: Optional[str] = None) -> dict:
        """Serialize CPU state to a dictionary (and optionally save to file).

        Args:
            cpu: CPU instance to serialize.
            path: Optional file path to write JSON state to.

        Returns:
            Dictionary containing the full emulator state.
        """
        state = {
            "version": StateSerializer.VERSION,
            "pc": cpu.pc,
            "priv": cpu.priv,
            "halted": cpu._halted,
            "instructions_executed": cpu._instructions_executed,
            "registers": {f"x{i}": cpu.regs[i] & 0xFFFFFFFF for i in range(32)},
            "csrs": {f"0x{addr:03x}": val & 0xFFFFFFFF
                     for addr, val in cpu.csrs._regs.items()},
            "uart_output": cpu._uart_output,
            "uart_buffer": list(cpu._uart_buf),
            "memory_regions": [],
        }

        # Serialize memory regions
        for region in cpu.memory.regions:
            region_data = {
                "base": region.base,
                "size": region.size,
                "permissions": "".join(sorted(region.perms)),
                "data": list(region.data[:min(len(region.data), 65536)]),
                "has_io": region.io_read is not None or region.io_write is not None,
            }
            # For very large regions, only save first 64KB (configurable)
            if len(region.data) > 65536:
                region_data["truncated"] = True
                region_data["full_size"] = len(region.data)
                logger.warning(
                    f"Truncating memory region at 0x{region.base:08x} "
                    f"({len(region.data)} bytes) to 64KB for serialization"
                )
            state["memory_regions"].append(region_data)

        if path:
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"State saved to {path}")

        return state

    @staticmethod
    def load_state(path_or_dict) -> CPU:
        """Deserialize CPU state from a JSON file or dictionary.

        Args:
            path_or_dict: Path to JSON file, or a state dictionary.

        Returns:
            Restored CPU instance with memory.
        """
        if isinstance(path_or_dict, str):
            with open(path_or_dict, "r") as f:
                state = json.load(f)
            logger.info(f"State loaded from {path_or_dict}")
        else:
            state = path_or_dict

        version = state.get("version", 1)
        if version > StateSerializer.VERSION:
            logger.warning(
                f"State version {version} is newer than supported "
                f"({StateSerializer.VERSION}). Some data may be lost."
            )

        # Reconstruct memory
        regions = []
        for rdata in state["memory_regions"]:
            data = bytes(rdata.get("data", []))
            if rdata.get("truncated", False):
                # Expand truncated data with zeros
                full_size = rdata.get("full_size", rdata["size"])
                data = data + b"\x00" * (full_size - len(data))

            region = MemoryRegion(
                base=rdata["base"],
                size=rdata.get("full_size", rdata["size"]),
                perms=rdata["permissions"],
                data=data,
            )
            regions.append(region)

        mem = Memory(regions)

        # Reconstruct CPU
        entry = state.get("pc", 0x20000000)
        cpu = CPU(
            memory=mem,
            pc=entry,
            hart_id=state.get("csrs", {}).get("0xf14", 0),
            enable_m_ext=True,
        )

        # Restore registers
        regs_data = state.get("registers", {})
        for i in range(32):
            key = f"x{i}"
            if key in regs_data:
                cpu.set_reg(i, regs_data[key])

        # Restore PC
        cpu.pc = state.get("pc", cpu.pc)

        # Restore privilege mode
        cpu.priv = state.get("priv", 3)

        # Restore halted state
        cpu._halted = state.get("halted", False)
        cpu._instructions_executed = state.get("instructions_executed", 0)

        # Restore CSRs
        csrs_data = state.get("csrs", {})
        for addr_str, val in csrs_data.items():
            addr = int(addr_str, 16) if isinstance(addr_str, str) else addr_str
            try:
                cpu.csrs.write(addr, val)
            except Exception:
                pass  # Skip read-only CSRs

        # Restore UART state
        cpu._uart_output = state.get("uart_output", "")
        cpu._uart_buf = state.get("uart_buffer", [])

        return cpu

    @staticmethod
    def state_diff(state1: dict, state2: dict) -> dict:
        """Compare two emulator states and return the differences.

        Useful for debugging: find what changed between two snapshots.
        """
        diff = {}

        # PC
        if state1.get("pc") != state2.get("pc"):
            diff["pc"] = {
                "before": state1.get("pc"),
                "after": state2.get("pc"),
            }

        # Registers
        reg_diff = {}
        regs1 = state1.get("registers", {})
        regs2 = state2.get("registers", {})
        for i in range(32):
            key = f"x{i}"
            v1 = regs1.get(key, 0)
            v2 = regs2.get(key, 0)
            if v1 != v2:
                reg_diff[key] = {"before": v1, "after": v2}
        if reg_diff:
            diff["registers"] = reg_diff

        # Instructions
        i1 = state1.get("instructions_executed", 0)
        i2 = state2.get("instructions_executed", 0)
        if i1 != i2:
            diff["instructions_executed"] = {"before": i1, "after": i2}

        return diff