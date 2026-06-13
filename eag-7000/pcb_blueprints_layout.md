# EAG-7000 — Phase 3: Physical PCB Blueprints & Layout Guidelines

---

## 3.1 PCB Stackup Definition

**Board Dimensions:** 100mm × 72mm (DIN-rail compatible footprint)  
**Total Layers:** 10 (6 signal + 2 ground + 2 power)

| Layer | Type | Material | Thickness | Copper | Dk | Purpose |
|---|---|---|---|---|---|---|
| L1 (Top) | Signal | FR-4 (Isola 370HR) | 0.035mm (1oz) | 1 oz | 4.04 | Component placement, high-speed routing |
| L2 | Ground | FR-4 | 0.035mm (1oz) | 1 oz | — | Continuous ground plane, EMI shield |
| L3 | Signal (Inner) | FR-4 | 0.100mm prepreg | 0.5 oz | 3.94 | DDR routing, controlled impedance |
| L4 | Signal (Inner) | FR-4 | 0.100mm core | 0.5 oz | 3.94 | PCIe/USB differential pairs |
| L5 | Power (1.0V) | FR-4 | 0.035mm (1oz) | 1 oz | — | VDD_CORE, VDD_SOC solid planes |
| L6 | Ground | FR-4 | 0.035mm (1oz) | 1 oz | — | Stitching ground, EMI return |
| L7 | Signal (Inner) | FR-4 | 0.100mm prepreg | 0.5 oz | 3.94 | Ethernet RGMII, MIPI-CSI |
| L8 | Signal (Inner) | FR-4 | 0.100mm core | 0.5 oz | 3.94 | Low-speed IO, SPI, I2C, UART |
| L9 | Power (3.3V/1.8V) | FR-4 | 0.035mm (1oz) | 1 oz | — | VDD_3V3, VDD_1V8 split planes |
| L10 (Bottom) | Signal | FR-4 | 0.035mm (1oz) | 1 oz | 4.04 | Bottom-side passives, BGA fanout |

**Total Board Thickness:** 1.60mm ± 0.10mm (standard 1.6mm for M.2 compatibility zone)

### 3.1.1 Impedance Control Summary

| Layer | Trace Type | Target Z₀ | Width | Spacing | Reference Plane |
|---|---|---|---|---|---|
| L1 | Single-ended | 50Ω | 4.5 mil | — | L2 |
| L1 | Differential (USB) | 90Ω diff | 4.5 mil | 6 mil | L2 |
| L1 | Differential (PCIe) | 85Ω diff | 3.5 mil | 5 mil | L2 |
| L3 | Single-ended | 50Ω | 5.0 mil | — | L2/L4 (coplanar) |
| L3 | Differential (DDR DQS) | 100Ω diff | 3.5 mil | 4 mil | L2 |
| L4 | Differential (PCIe/USB) | 85/90Ω diff | 3.5/4.5 mil | 5/6 mil | L5 |
| L7 | Single-ended (RGMII) | 50Ω | 5.0 mil | — | L6/L8 |

---

## 3.2 High-Speed Routing Rules

### 3.2.1 LPDDR4X (4267 MT/s) — DDR Interface

| Parameter | Requirement | Notes |
|---|---|---|
| **Max trace length** | ≤50mm (SoC to DRAM) | Keep DRAM within 50mm of SoC |
| **Length matching** | Within byte lane: ±10ps (≈±1.5mm) | DQ[0:7] + DM0 + DQS0_P/N |
| **Length matching** | Between byte lanes: ±25ps (≈±3.5mm) | Lane 0 to Lane 1 to Lane 2 to Lane 3 |
| **Address/Cmd matching** | ±25ps relative to CLK | CA bus to clock |
| **CK diff pair matching** | ≤5ps skew within pair | CLK_P to CLK_N |
| **Via count** | Max 2 per signal | Prefer single via if possible |
| **Via stub length** | ≤10mil (use back-drill on L1→L3 transitions) | Eliminate stub resonances |
| **Ground via stitching** | 1 ground via per 3 signal vias, ≤1mm away | Return path continuity |
| **Serial termination resistors** | 40Ω ±5% on CA/CMD lines | Place within 5mm of SoC pin |
| **ODT settings** | 48Ω RTT_NOM at DRAM | ZQ cal with 240Ω ±1% resistor |

**DDR Layout Sketch:**
```
    ┌───────────┐
    │  U1 SoC   │    Fly-by topology:
    │  i.MX8MP  │    CA/CMD traces route first,
    │           │    then DQ byte lanes group
    └──┬────┬───┘    by lane with matched lengths.
       │    │
  ┌────┘    └─────┐      ┌───────────┐
  │  DDR Ch A     │      │  DDR Ch B │
  │  (U2-0)       │      │  (U2-1)  │
  │  DQ[0:31]     │      │  DQ[32:63]│
  └───────────────┘      └───────────┘
       ≤50mm each
```

### 3.2.2 PCIe Gen3 x1 (8 GT/s)

| Parameter | Requirement | Notes |
|---|---|---|
| **Max trace length** | ≤100mm (SoC to M.2 connector) | Hailo-8 M.2 module |
| **Diff pair impedance** | 85Ω ±10% | Stripline on L4 |
| **Intra-pair skew** | ≤5ps (≤0.8mm) | TX pair, RX pair |
| **Inter-pair skew** | N/A (single lane x1) | — |
| **AC coupling caps** | 0.01µF ±5%, 0402, on both TX and RX | Place near source (≤10mm from SoC pin) |
| **Via transition** | Max 2 vias per diff pair | Use ground-stitched via pairs |
| **Ground void** | No voids under AC coupling caps | Keep reference plane continuous |
| **Tx de-emphasis** | -6dB (programmed in SoC PHY) | PCIe Gen3 preset P4 |

### 3.2.3 USB 3.1 Gen1 (5 Gbps)

| Parameter | Requirement | Notes |
|---|---|---|
| **Max trace length** | ≤150mm (to USB-C connector) | |
| **Diff pair impedance** | 90Ω ±10% | Stripline on L4 |
| **Intra-pair skew** | ≤5ps (≤0.8mm) | |
| **ESD protection** | TPD4E05U06 (TVS diode array) | At connector, <2mm from pins |
| **AC coupling** | 100nF on RX pair only (per spec) | C604, C605 near PHY side |
| **Ground stitching** | Via fence around USB-C connector | Every 1mm |

### 3.2.4 2.5GbE RGMII (to AQR111C)

| Parameter | Requirement | Notes |
|---|---|---|
| **Max trace length** | ≤75mm | SoC to each PHY |
| **Single-ended impedance** | 50Ω ±10% | |
| **Length matching** | All RGMII signals within ±50ps (≈±7mm) | TX and RX groups separately |
| **CLK skew** | TXC intentionally delayed 1.5–2ns | Series 22Ω + 2.7pF cap to GND on TXC |
| **MDIO pull-up** | 4.7kΩ to 3.3V on MDIO line | At PHY pin |
| **PHY isolation** | 1kV isolation via center-tapped transformers | Hanrun HR911105A integrated magnetics |

---

## 3.3 Analog/Digital Isolation

### 3.3.1 Ground Plane Strategy

```
┌────────────────────────────────────────────────────┐
│                    L2 (GND PLANE)                    │
│  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  AGND Zone        │  │  DGND Zone            │   │
│  │  (Ethernet PHY    │  │  (SoC, DDR, NPU,     │   │
│  │   analog section, │  │   digital IO)         │   │
│  │   crystal osc,    │  │                       │   │
│  │   PLL filters)    │  │                       │   │
│  │                   │  │                       │   │
│  │      ┃ ┃ ┃ ┃     │  │                       │   │
│  │      ┃ ┃ ┃ ┃  <--│--│-- Star-point ground   │   │
│  │      ┃ ┃ ┃ ┃     │  │   tie (0Ω resistor    │   │
│  │                   │  │   R950, single point) │   │
│  └──────────────────┘  └──────────────────────┘   │
│                                                      │
│  No slot cuts in ground planes except:               │
│  - Around Ethernet transformer isolation barrier     │
│  - Under USB-C connector ESD array                  │
│  - Clock crystal guard ring (L1 ground pour)        │
└────────────────────────────────────────────────────┘
```

### 3.3.2 Isolation Barriers

| Zone | Isolation Method | Details |
|---|---|---|
| **Ethernet magnetics** | Transformer isolation | 1.5kV minimum, Bob-Smith termination on RJ45 center taps |
| **USB-C PD** | No isolation needed | Same ground domain as system |
| **CAN-FD** | Digital isolator (ISO1050) | 5kV isolation, separate CAN_GND plane |
| **Analog sensors** | I2C isolator (ISO1541) | 3kV isolation on I2C MUX downstream |
| **PoE input** | Isolated DC-DC (TPS2378 → flyback) | 1.5kV input-output isolation |

### 3.3.3 Clock Guard Rings

Each crystal oscillator (Y1–Y4) gets a guard ring on L1:
- Continuous ground pour ring around crystal, ≥2mm clearance to signal traces
- Ground vias stitching guard ring to L2 every 1mm
- No signal traces routing under crystal area on any layer

---

## 3.4 Via Strategy

| Via Type | Usage | Drill | Pad | Anti-pad | Cost Impact |
|---|---|---|---|---|---|
| **Through-hole (PTH)** | General signal routing, power routing | 0.2mm | 0.4mm | 0.5mm | Baseline (included) |
| **Via-in-pad (VIP)** | BGA fanout for U1 (0.5mm pitch) | 0.1mm | 0.3mm | 0.4mm | +15% board cost |
| **Blind via L1→L3** | DDR breakout, avoids L4-L10 stubs | 0.1mm | — | — | +20% board cost |
| **Blind via L1→L5** | Power via from decoupling to L5 plane | 0.1mm | — | — | +20% board cost |
| **Back-drilled via** | DDR and high-speed signals on L1/L3 | 0.2mm | — | — | +10% board cost |

**Via allocation for U1 (FC-PBGA-780):**
- Total BGA pins: 780
- Ground pins: ~180 (direct PTH to L2/L6)
- Power pins: ~120 (VIP to L5/L9)
- Signal pins: ~480 (VIP + PTH combination)
- Decoupling via strategy: 1 ground via per 2 decoupling capacitors, placed within 1mm of cap pad

---

## 3.5 Thermal Management

### 3.5.1 Thermal Zone Map

```
┌─────────────────────────────────────────────────────────────┐
│                    EAG-7000 TOP VIEW                         │
│                                                               │
│  ┌─────────┐                    ┌──────────────┐            │
│  │  Y1-Y4  │    LOW HEAT        │   M.2 Slot   │            │
│  │ Crystals │    (<0.5W each)    │   (Hailo-8)  │  HIGH HEAT│
│  └─────────┘                    │   2.5W TDP   │  (Zone A) │
│                                  └──────────────┘            │
│  ┌──────────────────────────────────┐                       │
│  │         U1 — i.MX8M Plus         │      HIGH HEAT       │
│  │           7W TDP                  │      (Zone B)        │
│  │  [Thermal via array: 8×8 grid]   │                       │
│  │  [Each via: 0.3mm drill,        │                       │
│  │   filled with copper epoxy]     │                       │
│  └──────────────────────────────────┘                       │
│                                                               │
│  ┌──────┐  ┌──────┐  ┌──────────┐  ┌──────────┐          │
│  │ U2-0 │  │ U2-1 │  │ U5-0     │  │ U5-1     │          │
│  │ DDR  │  │ DDR  │  │ ETH PHY  │  │ ETH PHY  │          │
│  │0.5W  │  │0.5W  │  │ 0.8W     │  │ 0.8W     │          │
│  │MED   │  │MED   │  │MED       │  │MED       │          │
│  └──────┘  └──────┘  └──────────┘  └──────────┘          │
│                                                               │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌────────────────┐        │
│  │ U7   │  │ U9   │  │ U15  │  │   U3 (eMMC)     │        │
│  │PMIC  │  │DCDC  │  │USB-P │  │   0.3W          │        │
│  │1.5W  │  │0.3W  │  │0.4W  │  │   LOW            │        │
│  └──────┘  └──────┘  └──────┘  └────────────────┘        │
│                                                               │
│  Total board power: ~15W typical, 25W peak (NPU burst)      │
└─────────────────────────────────────────────────────────────┘
```

### 3.5.2 Thermal Solution

| Feature | Specification |
|---|---|
| **Heatsink** | Custom aluminum spreader, 100×72×8mm, anodized black |
| **Heatsink mounting** | 4× M2.5 threaded inserts at PCB corners |
| **Thermal interface material** | Bergquist GP6000 (6.0 W/mK), 0.5mm, 100×72mm sheet |
| **Thermal via array under U1** | 8×8 grid, 0.3mm drill, copper-filled, 1.5mm pitch |
| **Thermal via array under M.2** | 4×6 grid, 0.3mm drill, copper-filled, 2mm pitch |
| **L2/L6 copper pour** | 2oz copper on both ground planes for heat spreading |
| **Thermal relief** | Thermal spokes on all power plane connections (4 spokes, 0.3mm width) |
| **Max junction temps** | SoC: 95°C, NPU: 85°C, DRAM: 85°C (per datasheet limits) |
| **Thermal monitoring** | SoC internal TMU, NPU internal sensor, thermistor on PMIC rail |

### 3.5.3 Airflow & Convection (Passive)

- No forced airflow; relies on natural convection from DIN-rail mounting orientation
- Heatsink fin orientation: vertical fins aligned with expected convection path
- 2mm air gap between PCB bottom and DIN-rail bracket for bottom-side cooling
- All high-power components placed on top side (L1) for direct heatsink contact

---

## 3.6 Design-for-Manufacturing (DFM) Notes

| Constraint | Value | Reason |
|---|---|---|
| **Minimum trace width** | 4 mil (0.1mm) | Standard PCB fab capability |
| **Minimum trace spacing** | 4 mil (0.1mm) | Standard |
| **Minimum via drill** | 0.1mm (micro-via for VIP) | HDI process required |
| **Minimum PTH drill** | 0.2mm | Standard |
| **BGA pitch (U1)** | 0.5mm | Requires VIP + PTH combination |
| **BGA pitch (U2)** | 0.4mm | Requires VIP only (LPDDR4X FBGA-200) |
| **Solder mask** | LDI (Laser Direct Imaging) | For fine-pitch BGA registration |
| **Surface finish** | ENIG (Au 0.03µm / Ni 3µm) | Wire-bond compatible, RoHS |
| **Minimum silkscreen** | 6 mil line/8 mil text | Reference designators only |
| **Panel size** | 110mm × 82mm (with rails and tooling holes) | V-scored single-up |
| **AOI coverage** | 100% post-reflow | All BGA/QFN joints |
| **ICT** | Bed-of-nails test points on L10 | Minimum 50 test points |