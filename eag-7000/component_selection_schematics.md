# EAG-7000 — Phase 2: Detailed Component Selection & Schematics

---

## 2.1 Bill of Materials — Key Silicon

| Ref | Part Number | Manufacturer | Function | Package | Qty | Unit Cost (1K) |
|---|---|---|---|---|---|---|
| U1 | MIMX8ML8CVNKZAB | NXP | SoC — i.MX8M Plus (2x A72, 1x M4F, GC7000L, 2.3 TOPS NPU, ISP) | FC-PBGA-780 | 1 | $38.00 |
| U2 | MT53D512M32D4DS-046 | Micron | LPDDR4X SDRAM, 4GB (128Mx32), 4267 MT/s | FBGA-200 | 2 | $8.50 |
| U3 | THGBMJG6C1LBAB7 | KIOXIA | eMMC 5.1 32GB, SLC mode boot | FBGA-153 | 1 | $4.20 |
| U4 | Hailo-8 M.2 (HM2180B1C3DA) | Hailo AI | NPU Accelerator, 26 TOPS INT8, PCIe Gen3 x1 | M.2 2242 Key-M | 1 | $45.00 |
| U5 | AQR111C | Marvell | 2.5GbE PHY, RGMII, SGMII | QFN-56 | 2 | $3.80 |
| U6 | TPS2378PW | Texas Instruments | PoE+ PD Controller, 802.3at, 25.5W | TSSOP-20 | 1 | $2.10 |
| U7 | PCA9450CHN | NXP | PMIC for i.MX8M Plus, 6 bucks, 6 LDOs | HVQFN-48 | 1 | $3.50 |
| U8 | PCF2129T/2,518 | NXP | RTC with battery backup, I2C | SO-8 | 1 | $0.90 |
| U9 | TPS62A02ADDCR | TI | DCDC Buck, 3.3V→0.9V @2A for NPU | SOT-23-6 | 1 | $0.60 |
| U10 | TCA9548APWR | TI | I2C Multiplexer, 8-channel | TSSOP-24 | 1 | $1.20 |
| U11 | MCP2518FD-E/SN | Microchip | CAN-FD Controller, SPI | SOIC-14 | 2 | $1.40 |
| U12 | FT4232HL | FTDI | USB to 4x UART/JTAG, debug port | LQFP-64 | 1 | $5.50 |
| U13 | SN65LVDS100DGKR | TI | LVDS Repeater, MIPI-CSI signal integrity | VSSOP-8 | 2 | $0.80 |
| U14 | W25Q512JVEIM | Winbond | SPI NOR Flash, 64MB, XiCC enabled | SOIC-8 | 1 | $1.10 |
| U15 | USB3320C-EZK | Microchip | USB 3.1 PHY, ULPI | QFN-32 | 1 | $2.30 |
| U16 | M.2 2242 Key-M connector | TE Connectivity | M.2 socket for Hailo-8 module | Surface Mount | 1 | $1.80 |
| U17 | SN74LVC1G34DCKR | TI | Single Buffer Gate (clock distribution) | SOT-353 | 3 | $0.08 |

**Estimated BOM Total (key silicon only):** ~$120.00  
**Full BOM with passives, connectors, PCB:** ~$165.00 (target: ≤$180.00)

---

## 2.2 SoC Pinout Configuration — i.MX8M Plus (FC-PBGA-780)

### 2.2.1 Memory Interface — LPDDR4X Channel A (U2-0)

| SoC Pin | Ball | Function | MUX Mode | Net Name | Connected To | Notes |
|---|---|---|---|---|---|---|
| DRAM_A0 | A5 | DRAM_ADDR[0] | ALT0 | DDR_A0 | U2-0 A0 | 40Ω series term |
| DRAM_A1 | A6 | DRAM_ADDR[1] | ALT0 | DDR_A1 | U2-0 A1 | |
| DRAM_A0_BA0 | B5 | DRAM_BA[0] | ALT0 | DDR_BA0 | U2-0 BA0 | |
| DRAM_A1_BA1 | B6 | DRAM_BA[1] | ALT0 | DDR_BA1 | U2-0 BA1 | |
| DRAM_CS0_B | C5 | DRAM_CS[0]_B | ALT0 | DDR_CS0 | U2-0 CS0 | Active LOW |
| DRAM_CKE0 | C6 | DRAM_CKE[0] | ALT0 | DDR_CKE0 | U2-0 CKE0 | |
| DRAM_CLK_B | D5 | DRAM_CLK | ALT0 | DDR_CLK_P | U2-0 CLK_P | Diff pair, 240Ω term |
| DRAM_CLK | D6 | DRAM_CLK | ALT0 | DDR_CLK_N | U2-0 CLK_N | Diff pair |
| DRAM_DQ0 | E5 | DRAM_DQ[0] | ALT0 | DDR_DQ0 | U2-0 DQ0 | Byte lane 0 |
| ... | ... | ... | ... | ... | ... | (DQ[0:31] + DM + DQS) |
| DRAM_DQS0_B | E8 | DRAM_DQS[0]_B | ALT0 | DDR_DQS0_P | U2-0 DQS0_P | Diff strobe |
| DRAM_DQS0 | E9 | DRAM_DQS[0] | ALT0 | DDR_DQS0_N | U2-0 DQS0_N | Diff strobe |

*Pattern repeats for DQ[32:63] on Channel B (U2-1), same MUX mode ALT0.*

### 2.2.2 PCIe Gen3 x1 — NPU (Hailo-8 M.2)

| SoC Pin | Ball | Function | MUX Mode | Net Name | Connected To | Notes |
|---|---|---|---|---|---|---|
| PCIE_TX_P | AE20 | PCIE1_TX_P | ALT0 | PCIE_TX_P | M.2 Key-M pin 23 | AC-coupled, 0.01µF series |
| PCIE_TX_N | AE21 | PCIE1_TX_N | ALT0 | PCIE_TX_N | M.2 Key-M pin 25 | Diff pair, 100Ω diff |
| PCIE_RX_P | AF20 | PCIE1_RX_P | ALT0 | PCIE_RX_P | M.2 Key-M pin 36 | AC-coupled, 0.01µF series |
| PCIE_RX_N | AF21 | PCIE1_RX_N | ALT0 | PCIE_RX_N | M.2 Key-M pin 38 | Diff pair, 100Ω diff |
| PCIE_CLKREF_P | AD18 | PCIE1_CLKREF_P | ALT0 | PCIE_CLK_P | M.2 Key-M pin 13 | 100MHz ref clock |
| PCIE_CLKREF_N | AD19 | PCIE1_CLKREF_N | ALT0 | PCIE_CLK_N | M.2 Key-M pin 15 | Diff pair |
| PCIE_RST_B | AC22 | GPIO1_IO10 | ALT3 | PCIE_RST | M.2 Key-M pin 10 | Active-LOW reset, 10kΩ PU to 3.3V |
| PCIE_WAKE_B | AC23 | GPIO1_IO11 | ALT3 | PCIE_WAKE | M.2 Key-M pin 53 | Active-LOW, 10kΩ PU |
| PCIE_CLKREQ_B | AD22 | GPIO1_IO12 | ALT3 | PCIE_CLKREQ | M.2 Key-M pin 7 | Active-LOW, 10kΩ PU |

### 2.2.3 Ethernet — 2x 2.5GbE (RGMII to AQR111C)

| SoC Pin | Ball | Function | MUX Mode | Net Name | Connected To |
|---|---|---|---|---|---|
| ENET0_TXC | AG22 | ENET1_TX_CLK | ALT0 | ETH0_TXC | U5-0 (TX_CLK) |
| ENET0_TX_CTL | AG23 | ENET1_TX_EN | ALT0 | ETH0_TX_EN | U5-0 (TX_CTL) |
| ENET0_TXD0 | AH22 | ENET1_TXD[0] | ALT0 | ETH0_TXD0 | U5-0 (TXD0) |
| ENET0_TXD1 | AH23 | ENET1_TXD[1] | ALT0 | ETH0_TXD1 | U5-0 (TXD1) |
| ENET0_TXD2 | AG24 | ENET1_TXD[2] | ALT0 | ETH0_TXD2 | U5-0 (TXD2) |
| ENET0_TXD3 | AG25 | ENET1_TXD[3] | ALT0 | ETH0_TXD3 | U5-0 (TXD3) |
| ENET0_RXC | AF24 | ENET1_RX_CLK | ALT0 | ETH0_RXC | U5-0 (RX_CLK) |
| ENET0_RX_CTL | AF25 | ENET1_RX_DV | ALT0 | ETH0_RX_DV | U5-0 (RX_CTL) |
| ENET0_RXD0 | AE24 | ENET1_RXD[0] | ALT0 | ETH0_RXD0 | U5-0 (RXD0) |
| ENET0_RXD1 | AE25 | ENET1_RXD[1] | ALT0 | ETH0_RXD1 | U5-0 (RXD1) |
| ENET0_RXD2 | AD24 | ENET1_RXD[2] | ALT0 | ETH0_RXD2 | U5-0 (RXD2) |
| ENET0_RXD3 | AD25 | ENET1_RXD[3] | ALT0 | ETH0_RXD3 | U5-0 (RXD3) |
| ENET0_MDIO | AC24 | ENET1_MDIO | ALT0 | ETH0_MDIO | U5-0 (MDIO), 4.7kΩ PU |
| ENET0_MDC | AC25 | ENET1_MDC | ALT0 | ETH0_MDC | U5-0 (MDC) |

*ENET1 pins map identically to U5-1 (second AQR111C).*

### 2.2.4 USB 3.1 (ULPI to USB3320C)

| SoC Pin | Ball | Function | MUX Mode | Net Name | Connected To |
|---|---|---|---|---|---|
| USB0_DATA0 | AB20 | USB_OTG1_DATA[0] | ALT0 | USB_ULPI_D0 | U15 (D0) |
| USB0_DATA1 | AB21 | USB_OTG1_DATA[1] | ALT0 | USB_ULPI_D1 | U15 (D1) |
| ... | ... | ... | ... | ... | |
| USB0_DATA7 | AC21 | USB_OTG1_DATA[7] | ALT0 | USB_ULPI_D7 | U15 (D7) |
| USB0_DIR | AB22 | USB_OTG1_DIR | ALT0 | USB_ULPI_DIR | U15 (DIR) |
| USB0_STP | AB23 | USB_OTG1_STP | ALT0 | USB_ULPI_STP | U15 (STP) |
| USB0_NXT | AB24 | USB_OTG1_NXT | ALT0 | USB_ULPI_NXT | U15 (NXT) |
| USB0_CLK | AB25 | USB_OTG1_CLK | ALT0 | USB_ULPI_CLK | U15 (CLK), 60MHz |

### 2.2.5 I2C, SPI, UART, CAN-FD Summary

| Interface | SoC Pins | MUX | Net | Target | Pull-ups |
|---|---|---|---|---|---|
| I2C1_SDA/SCL | AD5/AD6 | ALT0 | I2C1_SDA/SCL | PMIC (U7), RTC (U8) | 4.7kΩ to 3.3V |
| I2C2_SDA/SCL | AD7/AD8 | ALT0 | I2C2_SDA/SCL | I2C MUX (U10) → sensors | 4.7kΩ to 3.3V |
| I2C3_SDA/SCL | AD9/AD10 | ALT0 | I2C3_SDA/SCL | Hailo-8 M.2 I2C | 4.7kΩ to 3.3V |
| SPI1_CS0/SCK/MOSI/MISO | AE5/AE6/AE7/AE8 | ALT0 | SPI1_* | Boot Flash (U14) | — |
| SPI2_CS0/SCK/MOSI/MISO | AF5/AF6/AF7/AF8 | ALT0 | SPI2_* | CAN-FD #0 (U11-0) | — |
| SPI3_CS0/SCK/MOSI/MISO | AG5/AG6/AG7/AG8 | ALT0 | SPI3_* | CAN-FD #1 (U11-1) | — |
| UART1_TX/RX | AH5/AH6 | ALT0 | UART1_TX/RX | Debug console (FT4232HL) | — |
| UART2_TX/RX | AH7/AH8 | ALT0 | UART2_TX/RX | RS-485 transceiver | — |
| UART3_TX/RX | AH9/AH10 | ALT0 | UART3_TX/RX | Modbus RTU port | — |

---

## 2.3 Schematic Specifications — Decoupling & Termination Networks

### 2.3.1 SoC Power Decoupling (U1 — i.MX8M Plus)

| Power Rail | Bypass Cap | Value | Type | Qty | Placement | Notes |
|---|---|---|---|---|---|---|
| VDD_CORE (0.9V) | C101–C120 | 100nF | X7R, 0402, 6.3V | 20 | Within 5mm of balls | Low-ESL per power pin |
| VDD_CORE (0.9V) | C121–C124 | 10µF | X7R, 0603, 6.3V | 4 | Corner bulk | Low-freq bypass |
| VDD_CORE (0.9V) | C125 | 100µF | X5R, 0805, 6.3V | 1 | Near PMIC output | Ripple filter |
| VDD_SOC (1.0V) | C201–C212 | 100nF | X7R, 0402, 6.3V | 12 | Within 5mm of balls | |
| VDD_SOC (1.0V) | C213–C215 | 10µF | X7R, 0603, 6.3V | 3 | Corner bulk | |
| VDD_DDR_IO (1.8V) | C301–C308 | 100nF | X7R, 0402, 10V | 8 | DDR IO area | |
| VDD_DDR_IO (1.8V) | C309–C310 | 10µF | X7R, 0603, 10V | 2 | Bulk | |
| VDD_3V3 | C401–C416 | 100nF | X7R, 0402, 16V | 16 | Peripheral IO area | |
| VDD_3V3 | C417 | 47µF | X5R, 0805, 16V | 1 | Near USB PHY | |
| VDD_1V8 | C501–C508 | 100nF | X7R, 0402, 10V | 8 | eMMC / SPI area | |
| VDD_NPU (0.9V) | C601–C608 | 100nF | X7R, 0402, 6.3V | 8 | M.2 connector vicinity | |
| VDD_NPU (0.9V) | C609 | 22µF | X5R, 0805, 6.3V | 1 | Near TPS62A02 output | |

### 2.3.2 LPDDR4X Termination & Decoupling

| Component | Value | Type | Net | Notes |
|---|---|---|---|---|
| R201 | 240Ω ±1% | 0402 | DDR_VREF_CA | VREF divider (CA bus) |
| R202 | 240Ω ±1% | 0402 | DDR_VREF_DQ | VREF divider (DQ bus) |
| R203 | 4.7kΩ | 0402 | DDR_ZQ | ZQ calibration resistor to GND |
| R204–R207 | 40Ω ±5% | 0402 | DDR_A[0:3] | Series termination on address lines |
| R208 | 100Ω ±1% | 0402 | DDR_CLK_P/N | Diff clock termination |
| C351–C370 | 100nF | X7R, 0201, 10V | DDR_VDDQ per byte lane | One per DQS pair |
| C371–C374 | 10µF | X7R, 0603, 10V | DDR_VDD2 | Per-die bulk |
| C375 | 100µF | X5R, 0805, 10V | DDR_VDD | Board-level bulk |

### 2.3.3 Ethernet PHY (AQR111C) Impedance Matching

| Net | Requirement | Implementation |
|---|---|---|
| ETH0_TX_P/N | 100Ω differential, ±10% | Microstrip on L3, 6.5mil width, 4mil space |
| ETH0_RX_P/N | 100Ω differential, ±10% | Microstrip on L3, 6.5mil width, 4mil space |
| ETH0_MDIO | 4.7kΩ pull-up to 3.3V | R401 at PHY pin |
| ETH0_RST_B | 10kΩ pull-up to 3.3V, 100nF cap to GND | R402 + C401, ensures clean POR |
| ETH0_REF_CLK | 25MHz XTAL (ABM8-25.000MHZ) | C402, C403 = 12pF load caps |

### 2.3.4 USB 3.1 Impedance Matching

| Net | Requirement | Implementation |
|---|---|---|
| USB3_TX_P/N | 90Ω differential, ±10% | Stripline on L4, 4.5mil width, 6mil space |
| USB3_RX_P/N | 90Ω differential, ±10% | Stripline on L4, 4.5mil width, 6mil space |
| USB2_DP/DM | 90Ω differential | Stripline on L4, 5mil width, 7mil space |
| USB_VBUS | 10µF bulk + 100nF ceramic | C609 (10µF), C610 (100nF) near connector |
| USB_SS_RX_EQ | 100nF AC coupling caps | C604, C605 on RX pair (per USB 3.1 spec) |

### 2.3.5 PCIe Gen3 x1 (to Hailo-8)

| Net | Requirement | Implementation |
|---|---|---|
| PCIE_TX_P/N | 85Ω differential | Stripline L4, 3.5mil width, 5mil space |
| PCIE_RX_P/N | 85Ω differential | Stripline L4, 3.5mil width, 5mil space |
| AC Coupling | 0.01µF ±5% on TX and RX | C801–C804, placed near source pins |
| PCIE_RST_B | 10kΩ PU to 3.3V | R801 |
| PCIE_CLKREQ_B | 10kΩ PU to 3.3V | R802 |
| PCIE_WAKE_B | 10kΩ PU to 3.3V | R803 |

---

## 2.4 Netlist — Key Signal Connections

### 2.4.1 PMIC (U7 — PCA9450) to SoC (U1) Power Map

| Source Pin | Net Name | Destination Pin | Component | Value | Notes |
|---|---|---|---|---|---|
| U7.BUCK1_OUT | VDD_CORE | U1.VDD_CORE (A1, B1, ...) | C101–C125 | 0.9V @ 4A | Core supply, max ripple 10mV |
| U7.BUCK2_OUT | VDD_DDR | U2-0.VDD2, U2-1.VDD2 | C371–C374 | 1.1V @ 3A | DDR core |
| U7.BUCK3_OUT | VDD_DDR_IO | U2-0.VDDQ, U2-1.VDDQ | C351–C370 | 1.8V @ 1A | DDR IO |
| U7.BUCK4_OUT | VDD_SOC | U1.VDD_SOC (E1, F1, ...) | C201–C215 | 1.0V @ 3A | SoC logic |
| U7.BUCK5_OUT | VDD_1V8_DRAM | U2-0.VDDCA, U2-1.VDDCA | — | 1.8V @ 1A | DDR CA supply |
| U7.BUCK6_OUT | VDD_3V3 | U5-0, U5-1, U15, GPIO | C401–C417 | 3.3V @ 2A | Peripheral IO |
| U7.LDO1_OUT | VDD_1V8 | U14 (Flash), U10 (I2C MUX) | C501–C508 | 1.8V @ 0.5A | Low-speed IO |
| U7.LDO2_OUT | VDD_SNVS | U1.SNVS domain | C509 | 0.8V @ 0.3A | Always-on domain |
| U7.LDO3_OUT | VDD_0V8_M4 | U1.M4F core | — | 0.8V @ 0.3A | Low-power island |
| U7.LDO4_OUT | VDD_PHY | U15 (USB PHY), U5-0/1 (ETH PHY) | C510 | 1.0V @ 0.3A | Analog PHY supply |
| U9 (TPS62A02).OUT | VDD_NPU | M.2 Key-M pin 56 (VCC) | C601–C609 | 0.9V @ 2A | Hailo-8 core |
| U6 (TPS2378).VDD | VDD_12V_IN | Power jack + PoE | C700 (100µF) | 12V ±10% | System input |

### 2.4.2 Boot Configuration Straps

| SoC Pin | Net Name | Pull | Value | Boot Mode |
|---|---|---|---|---|
| BOOT_MODE0 | BOOT_CFG00 | PU | 10kΩ to 3.3V | 1 |
| BOOT_MODE1 | BOOT_CFG01 | PD | 10kΩ to GND | 0 |
| BOOT_MODE2 | BOOT_CFG02 | PU | 10kΩ to 3.3V | 1 |
| BOOT_MODE3 | BOOT_CFG03 | PD | 10kΩ to GND | 0 |
| — | — | — | — | **Result: 0b1010 = eMMC boot** |

| SoC Pin | Net Name | Pull | Value | Function |
|---|---|---|---|---|
| LCDIF_RESET | CFG_GPIO0 | PD | 10kΩ to GND | M4F disabled at boot |
| CSI_RESET | CFG_GPIO1 | PU | 10kΩ to 3.3V | NPU PCIe enabled |
| GPIO1_IO05 | CFG_GPIO2 | PD | 10kΩ to GND | USB host mode |
| GPIO1_IO06 | CFG_GPIO3 | PU | 10kΩ to 3.3V | 2.5GbE enabled |

---

## 2.5 Reset & Clock Distribution

### 2.5.1 Clock Tree

| Clock Source | Frequency | Accuracy | Driven Nets | Buffer |
|---|---|---|---|---|
| Y1 (ABM8-24.000MHZ) | 24 MHz | ±30 ppm | U1.XTALI (SoC main OSC) | Direct |
| Y2 (ABM8-25.000MHZ) | 25 MHz | ±30 ppm | U5-0.XTALI, U5-1.XTALI (ETH PHY) | SN74LVC1G34 (U17-0) fanout |
| Y3 (ECS-25.000MHZ) | 25 MHz | ±25 ppm | U15.XTALI (USB PHY) | Direct |
| Y4 (ASEMB-100.000MHZ) | 100 MHz | ±50 ppm | U1.PCIE_REFCLK, M.2 pin 13 | U17-1 buffer |
| U1.PLL1 (SYS_PLL) | 800 MHz | — | A72 core clocks | Internal PLL |
| U1.PLL2 (DRAM_PLL) | 1600 MHz | — | DDR4267 MT/s (4×400) | Internal PLL |
| U1.PLL3 (VIDEO_PLL) | 594 MHz | — | ISP, display | Internal PLL |

### 2.5.2 Reset Architecture

| Reset Source | Active Level | Target | Notes |
|---|---|---|---|
| U7.POR | LOW | U1.RESET_B | Power-on reset, 100ms min |
| U1.SYS_RESET_B | LOW | All peripherals | Global system reset |
| U1.M4_RESET_B | LOW | U1.M4F core | M4F independently reset |
| RST_BTN (front panel) | LOW (debounced) | U1.RESET_B | Manual reset, 4.7kΩ PU |
| U7.WDTRST | LOW | U1.RESET_B | Watchdog timeout reset |
| SW_RST (TP) | LOW | U4 (Hailo-8) | PCIe fundamental reset |