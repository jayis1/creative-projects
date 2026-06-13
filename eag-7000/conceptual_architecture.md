# EDGE AI GATEWAY - EAG-7000
## Phase 1: Conceptual Architecture & Requirements

---

## 1.1 System Core Purpose

The **EAG-7000** (Edge AI Gateway, 7th Generation) is a compact, fanless industrial computer designed for real-time machine learning inference at the network edge. It targets smart factory, intelligent surveillance, and autonomous logistics applications.

**Primary Function:** Ingest multi-modal sensor data (camera, IMU, environmental), execute quantized neural network inference locally, and stream processed results over industrial Ethernet/5G with sub-10ms response latency.

---

## 1.2 Target Performance Metrics

| Parameter | Target | Notes |
|---|---|---|
| **AI Inference (INT8)** | ≥30 TOPS | Via NPU accelerator |
| **CPU Single-Thread** | ≥2.5 GHz | ARM Cortex-A72 class |
| **Memory Bandwidth** | ≥25.6 GB/s | Dual-channel LPDDR4X |
| **Storage Read** | ≥2000 MB/s | NVMe over PCIe Gen3 x2 |
| **Network Throughput** | ≥5 Gbps | 2x 2.5GbE + 1x 5GbE USB-C |
| **Sensor-to-Action Latency** | <10 ms | End-to-end, HW-accelerated path |
| **Power Consumption** | ≤15 W (typical), 25 W (peak) | Passive cooling, industrial temp |
| **Operating Temperature** | -40°C to +85°C | Industrial grade |
| **MTBF** | ≥100,000 hours | MIL-HDBK-217F, Gf |
| **Form Factor** | 100mm x 72mm x 25mm | DIN-rail mountable enclosure |

---

## 1.3 Design Constraints

| Constraint | Value | Rationale |
|---|---|---|
| **Thermal** | Passive only, TDP ≤15W sustained | No fans, no liquid; relies on thermal via arrays and heatsink spreader |
| **Power Supply** | 12V DC ±10%, PoE+ (802.3at) | Industrial DIN-rail supply or PoE+ via Port 0 |
| **Cost Target (BOM)** | ≤$180 @ 1K units | Cost-optimized mid-range industrial |
| **EMC** | IEC 61000-6-2/4, CE/FCC Class A | Industrial EMC compliance |
| **Security** | Secure Boot, TEE, hardware root-of-trust | Arm TrustZone + eFuse OTP keys |

---

## 1.4 High-Level Block Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        EAG-7000 SYSTEM ARCHITECTURE                 │
│                                                                      │
│  ┌──────────────┐    AXI4 Bus Matrix     ┌─────────────────────┐    │
│  │  SoC:        │◄──────────────────────►│  LPDDR4X (2x 4GB)  │    │
│  │  NXP i.MX8M │   (256-bit, 3200 MHz)  │  MT53D512M32D4DS    │    │
│  │  Plus        │                        └─────────────────────┘    │
│  │              │                                                    │
│  │  ┌────────┐  │   ┌─────────────┐   ┌──────────────────────┐    │
│  │  │Cortex- │  │   │ NPU:        │   │ eMMC 5.1 Boot Flash  │    │
│  │  │A72 x2  │  │   │ Hailo-8 M.2 │   │ 32GB (KLM8G2WACB)   │    │
│  │  │2.2 GHz │  │   │ 26 TOPS     │   └──────────────────────┘    │
│  │  └────────┘  │   │ via PCIe    │                                │
│  │  ┌────────┐  │   │ Gen3 x1     │   ┌──────────────────────┐    │
│  │  │Cortex- │  │   └─────────────┘   │ NVMe SSD (M.2 2242) │    │
│  │  │M4F x1  │◄────────────────────────│ 128GB, PCIe Gen3 x2 │    │
│  │  │800 MHz │  │   AXI Crossbar      └──────────────────────┘    │
│  │  └────────┘  │                                                    │
│  │  ┌────────┐  │   ┌─────────────────┐  ┌────────────────────┐  │
│  │  │GPU:    │  │   │ USB 3.1 Gen1    │  │ 2x 2.5GbE PHY     │  │
│  │  │GC7000L │  │   │ x2 Host+Device  │  │ AQR111C (RGMII)   │  │
│  │  │3D      │  │   │ + USB-C (DP)    │  │ + 1x USB-C 5GbE   │  │
│  │  └────────┘  │   └─────────────────┘  └────────────────────┘  │
│  └──────┬───────┘                                                    │
│         │                                                            │
│  ┌──────┴───────────────────────────────────────────────────────┐   │
│  │                    PERIPHERAL SUBSYSTEM                        │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  │   │
│  │  │ SPI x3   │  │ I2C x4    │  │ UART x5  │  │ CAN-FD x2  │  │   │
│  │  │ (Sensors)│  │ (EEPROM,  │  │ (Debug,  │  │ (Industrial│  │   │
│  │  │          │  │  RTC, PMIC│  │  Modbus) │  │  Fieldbus) │  │   │
│  │  └──────────┘  └───────────┘  └──────────┘  └────────────┘  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                    POWER MANAGEMENT                            │   │
│  │  PMIC: NXP PCA9450          PoE+ PD: TI TPS2378              │   │
│  │  LDO/DCDC: 3.3V, 1.8V, 1.1V, 0.9V core                      │   │
│  │  Battery-backed RTC: NXP PCF2129 (I2C)                       │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 1.5 Data Flow & Bus Topology

### 1.5.1 Primary Bus Architecture

| Bus | Protocol | Width | Clock | Bandwidth | Purpose |
|---|---|---|---|---|---|
| **AXI Bus 0** | AXI4 | 256-bit | 400 MHz | 25.6 GB/s | CPU ↔ DRAM (main memory) |
| **AXI Bus 1** | AXI4 | 128-bit | 333 MHz | 6.66 GB/s | GPU ↔ DRAM (frame buffer) |
| **AXI Bus 2** | AXI4-Lite | 32-bit | 166 MHz | 0.66 GB/s | NPU ↔ DRAM (weight streaming) |
| **AHB** | AHB-Lite | 32-bit | 133 MHz | 0.53 GB/s | M4F ↔ peripherals |
| **APB** | APB4 | 32-bit | 66 MHz | — | Low-speed peripheral register access |

### 1.5.2 DMA Data Paths

```
Camera MIPI-CSI ──► ISI (Image Sensor Interface) ──► DMA0 ──► DRAM
                                                           │
NPU (Hailo-8) ◄── DMA1 ◄── DRAM ◄── DMA2 ◄── Ethernet MAC ◄── Sensor Data
    │
    └──► DMA1 ──► DRAM ──► DMA3 ──► NVMe SSD (logging)
                              │
                              └──► DMA4 ──► Ethernet TX (2.5GbE)
```

### 1.5.3 Interrupt Architecture

| Priority | Source | IRQ # | Destination | Notes |
|---|---|---|---|---|
| Highest (0) | Watchdog / Fault | SPI 0 | A72 GIC-400 | System-critical |
| High (1) | NPU PCIe | SPI 1 | A72 GIC-400 | Inference completion |
| High (2) | Ethernet RX | SPI 2 | A72 GIC-400 | Packet processing |
| Medium (3) | MIPI-CSI | SPI 3 | A72 GIC-400 | Frame capture |
| Medium (4) | USB 3.1 | SPI 4 | A72 GIC-400 | Bulk data |
| Low (5) | SPI/I2C/UART | SPI 5-15 | A72 or M4F | Slow peripherals |
| Low (6) | CAN-FD | SPI 16-17 | M4F NVIC | Real-time fieldbus |
| Lowest (7) | RTC Tick | SPI 18 | M4F NVIC | Timekeeping |

### 1.5.4 Power Domains

| Domain | Voltage | Rail Source | Consumers |
|---|---|---|---|
| **VDD_CORE** | 0.9V | PCA9450 BUCK1 | CPU A72, GPU, NPU interconnect |
| **VDD_DDR** | 1.1V | PCA9450 BUCK2 | LPDDR4X VDD2 |
| **VDD_DDR_IO** | 1.8V | PCA9450 BUCK3 | LPDDR4X VDDQ, address/cmd |
| **VDD_SOC** | 1.0V | PCA9450 BUCK4 | SoC logic, peripheral IO |
| **VDD_3V3** | 3.3V | PCA9450 LDO1 | USB PHY, Ethernet PHY, GPIO |
| **VDD_1V8** | 1.8V | PCA9450 LDO2 | eMMC, SPI flash, I2C pull-ups |
| **VDD_0V8** | 0.8V | PCA9450 LDO3 | M4F core (low-power island) |
| **VDD_NPU** | 3.3V → 0.9V | On-board DCDC (TPS62A02) | Hailo-8 M.2 module |

---

## 1.6 Assumptions & Rationale

1. **NXP i.MX8M Plus** chosen over Rockchip RK3588 due to: longer industrial availability commitment (15-year), verified -40°C to 85°C operation, and integrated ISP/NPU (though we add Hailo-8 for dedicated high-TOPS inference).

2. **Hailo-8 M.2** accelerator provides 26 TOPS INT8 at <2.5W, complementing the i.MX8MP's built-in 2.3 TOPS NPU for a combined ~28 TOPS.

3. **LPDDR4X** over DDR4 for power efficiency (1.1V vs 1.2V IO) — critical for passive cooling.

4. **Dual 2.5GbE** for industrial network redundancy; USB-C 5GbE (via ASIX/Microchip) for management/debug port.

5. **Cortex-M4F** handles real-time CAN-FD and Modbus without A72 Linux involvement, ensuring deterministic <1ms fieldbus response.

6. **eMMC boot** (not SD card) for reliability in vibration environments.

7. **No HDMI/DisplayPort output** on main board — display served via USB-C alternate mode or remote web UI. This saves power and BOM.