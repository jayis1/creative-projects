# EAG-7000 — Edge AI Gateway

A high-performance, fanless industrial Edge AI Gateway for real-time ML inference at the network edge. Targets smart factory, intelligent surveillance, and autonomous logistics with sub-10ms sensor-to-action latency.

## Specifications

| Parameter | Value |
|---|---|
| **AI Throughput** | ≥30 TOPS INT8 (2.3 TOPS SoC + 26 TOPS Hailo-8) |
| **CPU** | NXP i.MX8M Plus — 2× Cortex-A72 @ 2.0 GHz + 1× Cortex-M4F @ 800 MHz |
| **Memory** | 2× Micron MT53D512M32D4DS — 8GB LPDDR4X @ 4267 MT/s |
| **Storage** | 32GB eMMC 5.1 (boot) + 128GB NVMe M.2 2242 (data) |
| **Networking** | 2× 2.5GbE (AQR111C) + 1× 5GbE USB-C |
| **Industrial IO** | 2× CAN-FD, 3× SPI, 4× I2C, 5× UART, 1× MIPI-CSI2 |
| **Power** | 12V DC / PoE+ (802.3at), ≤15W typical, 25W peak |
| **Form Factor** | 100mm × 72mm × 25mm, DIN-rail mountable |
| **Operating Temp** | -40°C to +85°C (industrial) |
| **BOM Target** | ≤$180 @ 1K units |

## Documentation

| Phase | File | Contents |
|---|---|---|
| **Phase 1** | [`phase1_conceptual_architecture.md`](phase1_conceptual_architecture.md) | Requirements, block diagram, bus topology, power domains |
| **Phase 2** | [`phase2_component_selection_schematics.md`](phase2_component_selection_schematics.md) | BOM, pinouts, netlists, decoupling, impedance matching |
| **Phase 3** | [`phase3_pcb_blueprints_layout.md`](phase3_pcb_blueprints_layout.md) | 10-layer stackup, DDR/PCIe/USB routing, thermal management |
| **Phase 4** | [`phase4_software_stack_implementation.md`](phase4_software_stack_implementation.md) | MMIO defs, clock/GPIO init, MCP2518FD CAN-FD driver, device tree |

## Key Design Decisions

1. **i.MX8M Plus** over Rockchip RK3588 — 15-year industrial availability, verified -40°C to 85°C
2. **LPDDR4X** over DDR4 — 1.1V IO for passive cooling at 15W TDP
3. **eMMC boot** over SD card — vibration reliability in industrial environments
4. **Hailo-8 M.2** accelerator — 26 TOPS at 2.5W, best TOPS/W in form factor
5. **Dual CAN-FD via SPI** (MCP2518FD) — M4F handles real-time fieldbus with <1ms response