"""Configuration system for the RISC-V emulator.

Supports loading settings from YAML/TOML config files or programmatically.
Configuration covers CPU settings, memory map, UART, and logging.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryRegionConfig:
    """Configuration for a single memory region."""
    base: int
    size: int
    permissions: str = "rwx"
    description: str = ""

    def __post_init__(self):
        if isinstance(self.base, str):
            self.base = int(self.base, 0)
        if isinstance(self.size, str):
            self.size = int(self.size, 0)


@dataclass
class UARTConfig:
    """Configuration for UART MMIO device."""
    base_addr: int = 0x10000000
    size: int = 8
    enabled: bool = True
    description: str = "QEMU-virt compatible UART"

    def __post_init__(self):
        if isinstance(self.base_addr, str):
            self.base_addr = int(self.base_addr, 0)


@dataclass
class CPUConfig:
    """Configuration for CPU core."""
    pc: int = 0x20000000
    hart_id: int = 0
    enable_m_ext: bool = True
    max_instructions: int = 100000

    def __post_init__(self):
        if isinstance(self.pc, str):
            self.pc = int(self.pc, 0)


@dataclass
class TraceConfig:
    """Configuration for tracing."""
    enabled: bool = False
    max_entries: int = 100000
    output_file: Optional[str] = None
    format: str = "text"  # "text", "csv", "json"


@dataclass
class EmulatorConfig:
    """Top-level emulator configuration."""
    cpu: CPUConfig = field(default_factory=CPUConfig)
    uart: UARTConfig = field(default_factory=UARTConfig)
    memory_regions: List[MemoryRegionConfig] = field(default_factory=lambda: [
        MemoryRegionConfig(base=0x20000000, size=0x100000, permissions="rwx",
                          description="Code/data"),
        MemoryRegionConfig(base=0x7F000000, size=0x01000000, permissions="rw",
                          description="Stack"),
    ])
    trace: TraceConfig = field(default_factory=TraceConfig)
    log_level: str = "WARNING"

    def __post_init__(self):
        # Normalize log level
        level = getattr(logging, self.log_level.upper(), logging.WARNING)
        logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    def to_dict(self) -> dict:
        """Serialize config to a plain dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize config to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "EmulatorConfig":
        """Create config from a dictionary."""
        cpu_data = data.get("cpu", {})
        uart_data = data.get("uart", {})
        regions_data = data.get("memory_regions", [])
        trace_data = data.get("trace", {})

        cpu = CPUConfig(**{k: v for k, v in cpu_data.items() if k in CPUConfig.__dataclass_fields__})
        uart = UARTConfig(**{k: v for k, v in uart_data.items() if k in UARTConfig.__dataclass_fields__})
        regions = [MemoryRegionConfig(**{k: v for k, v in r.items() if k in MemoryRegionConfig.__dataclass_fields__})
                   for r in regions_data]
        trace = TraceConfig(**{k: v for k, v in trace_data.items() if k in TraceConfig.__dataclass_fields__})

        log_level = data.get("log_level", "WARNING")
        return cls(cpu=cpu, uart=uart, memory_regions=regions, trace=trace, log_level=log_level)

    @classmethod
    def from_json(cls, json_str: str) -> "EmulatorConfig":
        """Load config from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, path: str) -> "EmulatorConfig":
        """Load config from a JSON or TOML file."""
        with open(path, "r") as f:
            content = f.read()

        if path.endswith(".toml"):
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            data = tomllib.loads(content)
        elif path.endswith(".json"):
            data = json.loads(content)
        else:
            # Try JSON first, then TOML
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                data = tomllib.loads(content)

        return cls.from_dict(data)

    @classmethod
    def default(cls) -> "EmulatorConfig":
        """Return default configuration."""
        return cls()

    def save(self, path: str) -> None:
        """Save config to a file (JSON format)."""
        with open(path, "w") as f:
            f.write(self.to_json())
        logger.info(f"Config saved to {path}")


# Default config as a reference
DEFAULT_CONFIG_JSON = """{
  "cpu": {
    "pc": "0x20000000",
    "hart_id": 0,
    "enable_m_ext": true,
    "max_instructions": 100000
  },
  "uart": {
    "base_addr": "0x10000000",
    "size": 8,
    "enabled": true,
    "description": "QEMU-virt compatible UART"
  },
  "memory_regions": [
    {
      "base": "0x20000000",
      "size": "0x100000",
      "permissions": "rwx",
      "description": "Code/data"
    },
    {
      "base": "0x7F000000",
      "size": "0x01000000",
      "permissions": "rw",
      "description": "Stack"
    }
  ],
  "trace": {
    "enabled": false,
    "max_entries": 100000,
    "output_file": null,
    "format": "text"
  },
  "log_level": "WARNING"
}"""