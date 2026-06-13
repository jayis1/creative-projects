# Assembly Guide — Canopy Listener

## Tools Required

- Soldering iron (fine tip, 0.2mm) or reflow oven
- Solder paste (for 0402 passives and QFN packages)
- Tweezers (ESD-safe, fine tip)
- Multimeter
- USB-C cable
- Computer with Pico SDK installed
- FTDI adapter or Picoprobe (for SWD debugging)
- LoRa antenna (868/915MHz whip)
- MicroSD card (FAT32 formatted, ≤32GB)

## Assembly Steps

### 1. PCB Fabrication

Order from JLCPCB or similar:
- 4-layer FR4, 1.6mm thickness
- 80mm × 50mm rectangular outline, 3mm corner radius
- ENIG surface finish (required for RP2040 QFN pads)
- Dark green solder mask, white silkscreen
- Castellated holes for antenna connector

### 2. SMT Component Placement

Order of assembly (by difficulty):

1. **0402 passives first** — R1-R8 (pullups and dividers), C1-C16 (decoupling and load caps)
2. **SOT packages** — U10 (RT9013 SOT-23-5)
3. **QFN/DFN ICs** — U2 (W25Q128JVSIQ SOIC-8), U9 (MCP73871 DFN-10)
4. **QFN-56** — U1 (RP2040) — largest and most critical component
5. **Sensors** — U7 (BME280 LGA-8), U3/U4 (ICS-43434 LGA-6)
6. **RF modules** — U5 (SX1262 QFN-24), U6 (L86-Q LCC)
7. **Display** — U8 (SSD1306 module, hand-solder)
8. **Connectors** — J1 (USB-C), J2 (microSD), J3 (SMA edge)
9. **LED** — D1 (WS2812B-2020)
10. **Crystal** — Y1 (12MHz 3225)

### 3. Reflow Profile

Use standard lead-free SAC305 profile:
- Ramp: 1-3°C/s to 150°C
- Soak: 150-200°C for 60-90s
- Peak: 235-245°C for 20-40s
- Cool: 1-4°C/s

**Important:** The ICS-43434 MEMS microphones have an acoustic opening on the top. Do NOT apply solder paste or flux on the acoustic port. Use a pick-and-place nozzle that avoids the port area.

### 4. Post-Reflow Inspection

- Check all 0402 joints under microscope
- Verify no solder bridges on RP2040 QFN-56 pads
- Check SX1262 ground pad for proper thermal connection
- Verify ICS-43434 acoustic ports are clear
- Check L86-Q GNSS module for proper seating
- Verify BME280 is not damaged by reflow (max 260°C, max 3x reflow)

### 5. Battery Connection

- Solder battery wires to BAT+ and GND pads
- Use strain relief (small dab of epoxy)
- Battery sits in pocket on bottom of PCB
- Route wires away from antenna and microphone areas

### 6. Solar Panel Connection

- Connect 5V solar panel to SOLAR+ and GND pads
- Use IP67 M8 connector or direct solder with weatherproof heatshrink
- Solar panel mounts on top of enclosure or separate pole

### 7. Antenna Assembly

- Thread 868/915MHz whip antenna onto SMA connector (J3)
- Ensure antenna is vertical and unobstructed
- LoRa range depends heavily on antenna placement

### 8. MicroSD Card

- Insert FAT32-formatted microSD card (≤32GB)
- Close rubber gasket cover firmly for weather seal
- The card stores detections.csv and audio WAV files

### 9. Initial Test

1. Connect USB-C (no battery initially)
2. Verify 3.3V on RT9013 output with multimeter
3. Check MCP73871 STAT LEDs for charge status
4. Flash firmware via UF2 (hold BOOT, plug USB)
5. Verify serial output at 115200 baud
6. Check I2C bus: BME280 should respond at 0x76, SSD1306 at 0x3C
7. Check SPI0: SX1262 should respond (read version register)
8. Check SPI1: SD card should mount
9. Verify audio capture: blow into microphone, see data in buffer

### 10. Enclosure Assembly

- Place PCB in bottom half of IP67 enclosure
- Thread antenna through top panel grommet
- Route USB-C port through side grommet
- Align microphone acoustic vents with enclosure holes (use acoustic mesh over holes)
- Place OLED display behind clear window
- Route solar panel cable through bottom grommet
- Place battery in designated pocket
- Seal enclosure with gasket properly seated
- Test IP67 seal (no water ingress)

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No serial output | Firmware not flashed | Hold BOOT, connect USB, copy UF2 file |
| BME280 not responding | I2C address conflict | Verify 0x76, check pullups R1/R2 |
| No audio data | ICS-43434 not clocked | Check PIO program loaded, BCLK on GP8 |
| LoRa TX fails | SX1262 not initialized | Check SPI0 wiring, NSS/GP5 connection |
| GPS no fix | Antenna obscured | Move to outdoor location, wait 60s for cold start |
| SD card mount fail | Wrong format | Format as FAT32 (≤32GB) |
| High power draw | WiFi not sleeping | RP2040 has no WiFi; check LoRa RX mode |
| Battery drains fast | Solar panel disconnected | Check solar connector, verify MCP73871 charging |
| OLED blank | I2C address wrong | Verify SSD1306 at 0x3C, check I2C pullups |

## Acoustic Considerations

The ICS-43434 MEMS microphones are sensitive to:
- **Wind noise** — Use foam windscreens over acoustic vents
- **Moisture** — The IP67 enclosure with acoustic mesh helps
- **Mechanical vibration** — Mount device on a tree with rubber isolation straps
- **Self-noise** — Keep RP2040 away from microphone traces on PCB layout

For optimal bird/frog detection:
- Mount at 1-3m height on a tree trunk
- Avoid placing near roads (anthropogenic noise)
- Orient microphones toward the expected sound source
- Use a 5-minute duty cycle in low-activity areas, continuous in high-activity areas