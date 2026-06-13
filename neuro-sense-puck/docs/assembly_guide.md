# Assembly Guide — Neuro Sense Puck

## Tools Required

- Soldering iron (fine tip, 0.2mm) or reflow oven
- Solder paste (for 0402 passives and QFN packages)
- Tweezers (ESD-safe, fine tip)
- Multimeter
- USB-C cable
- Computer with ESP-IDF v5.3+ installed

## Assembly Steps

### 1. PCB Fabrication
Order from JLCPCB or similar:
- 4-layer FR4, 1.6mm thickness
- 35mm diameter round outline
- ENIG surface finish (required for BME680/SGP40 pads)
- Green solder mask, white silkscreen

### 2. SMT Component Placement
Order of assembly (by difficulty):

1. **0402 passives first** — R1, R2 (4.7k I2C pullups), C1-C6 (100nF decoupling), C7-C8 (10µF bulk)
2. **SOT packages** — U8 (MCP73831 SOT-23-5), U9 (AP2112 SOT-223)
3. **QFN/DFN sensors** — U2 (BME680 LGA-8), U3 (SGP40 DFN-6), U5 (ICM-42688 LGA-14), U6 (TSL2591 TMB-6), U7 (MAX9814 DFN-10)
4. **Module** — U1 (ESP32-C6-MINI-1) — largest component, place last
5. **Custom package** — U4 (SPS30) — has airflow requirements, place in center cutout
6. **LED** — D1 (WS2812B-2020)
7. **USB-C connector** — J1 — hand-solder or reflow with care

### 3. Reflow Profile
Use standard lead-free SAC305 profile:
- Ramp: 1-3°C/s to 150°C
- Soak: 150-200°C for 60-90s
- Peak: 235-245°C for 20-40s
- Cool: 1-4°C/s

### 4. Post-Reflow Inspection
- Check all 0402 joints under microscope
- Verify no solder bridges on QFN pads
- Check SPS30 airflow channel is clear of solder

### 5. Battery Connection
- Solder battery wires to BAT+ and GND pads
- Use strain relief (small dab of epoxy)
- Battery sits in pocket on bottom of PCB

### 6. Initial Test
1. Connect USB-C (no battery)
2. Verify 3.3V on AP2112 output with multimeter
3. Check MCP73831 STAT LED behavior
4. Flash firmware via UART (GPIO18/19)
5. Verify BLE advertising with phone app (nRF Connect)

### 7. Enclosure Assembly (Optional)
- 3D print PETG shell (files in `hardware/enclosure/`)
- Snap PCB into shell, USB-C port aligned
- Light sensor aperture over TSL2591
- Mic port over MAX9814/SPH0645
- Airflow vents for SPS30

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No BLE advertising | Firmware not flashed | Check UART connection, re-flash |
| BME680 not responding | I2C address conflict | Verify 0x77, check pullups |
| SPS30 read failures | Not enough warm-up time | Wait 30s after power-on |
| Battery not charging | MCP73831 PROG resistor wrong | Check R_PROG = 5k for 200mA charge |
| LED not lighting | WS2812B data direction | Verify GPIO15 → DIN connection |
| High power consumption | WiFi not sleeping | Disable WiFi in deep sleep config |