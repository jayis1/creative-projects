# Field Deployment Guide — Canopy Listener

## Choosing a Deployment Site

### Optimal Conditions
- **Forest edge or clearing** — best for bird and amphibian detection
- **Away from roads** — minimize anthropogenic noise (>50m from roads)
- **Near water** — excellent for frog and aquatic insect detection
- **Open sky** — needed for GPS fix and LoRa transmission
- **Sun exposure** — at least 4 hours direct sun for solar charging

### Avoid
- Directly under dense canopy (GPS won't fix, solar won't charge)
- Within 10m of running water (constant noise interference)
- Near high-voltage power lines (EMI can affect LoRa)
- In flood zones (below seasonal water level)

## Physical Installation

### Tree/Pole Mounting

1. **Select a tree or pole** at 1.5-3m height
2. **Attach mounting straps** through the enclosure's strap slots
3. **Orient the device** so:
   - Microphone vents face the area you want to monitor
   - Solar panel faces south (northern hemisphere) or north (southern hemisphere)
   - LoRa antenna points vertically upward
4. **Secure cables** — solar panel cable along the tree, USB-C accessible

### Antenna Considerations

- The LoRa antenna must be **vertical** for best range
- Keep antenna **away from the tree trunk** by at least 20cm
- Use the SMA whip antenna provided, or upgrade to a dipole for longer range
- In dense forest, range drops to ~1-3km; in open areas, up to 15km

## Power Management

### Battery Life Estimation

| Mode | Current Draw | Duration (2000mAh) |
|------|-------------|---------------------|
| Deep Sleep | 0.5 mA | ~167 days |
| Idle (display off) | 8 mA | ~10 days |
| Recording (5s/60s cycle) | ~12 mA avg | ~7 days |
| Recording + GPS | ~20 mA avg | ~4 days |
| Recording + LoRa TX | ~15 mA avg | ~5.5 days |
| Full active | 85 mA | ~23 hours |

### Solar Charging

With a 2W (5V, 400mA) solar panel:
- **Good sun (6 effective hours/day)**: 6h × 400mA = 2400mAh/day
- **Average sun (3 effective hours/day)**: 3h × 400mA = 1200mAh/day
- **Cloudy (1 effective hour/day)**: 1h × 150mA = 150mAh/day

At 12mA average consumption, you need ~288mAh/day. So even moderate sun provides indefinite operation.

### Low Battery Behavior

- **< 3.6V**: Reduce duty cycle to 5 minutes
- **< 3.4V**: Stop LoRa transmissions (save 120mA bursts)
- **< 3.3V**: Enter deep sleep, wake every 5 minutes for solar check only
- **< 3.0V**: Complete shutdown to protect battery

## Configuration

### config.txt (on SD card)

```
# Audio settings
sample_rate=48000         # 48000 (normal) or 96000 (bat mode)
capture_seconds=5         # Duration of each audio capture (1-30)
duty_cycle_seconds=60     # Time between captures (10-3600)

# Detection settings
confidence_threshold=0.7  # Minimum confidence to log (0.0-1.0)
log_wind=false            # Whether to log WIND detections

# LoRa settings
lora_frequency=868        # 868 (EU) or 915 (US)
lora_tx_enabled=true      # Enable LoRa transmissions
lora_tx_power=22           # TX power in dBm (2-22)

# GPS settings
gps_power_cycle=true      # Cycle GPS power for battery saving
gps_fix_interval=300       # Seconds between GPS power-ons (30-3600)
gps_fix_timeout=60         # Max seconds to wait for fix

# Display settings
display_brightness=207     # SSD1306 contrast (0-255)
display_timeout=30         # Seconds before display turns off (0=always on)

# Storage
max_audio_files=1000       # Max WAV files before rotation
sd_log_interval=1          # Log every Nth detection (1=all)
```

## Monitoring and Data Retrieval

### Via LoRa Gateway

Set up a second Canopy Listener or SX1262-based gateway device to receive detection packets:

```bash
python3 scripts/gateway_receiver.py --port /dev/ttyUSB0 --freq 868
```

Gateway outputs JSON:
```json
{
  "timestamp": 1718200000,
  "latitude": 51.747840,
  "longitude": -1.263520,
  "class": "BIRD_SONG",
  "confidence": 87,
  "crc_valid": true
}
```

### Via SD Card

Remove microSD card and copy files:
- `detections.csv` — all detections with timestamps and coordinates
- `audio/*.wav` — audio recordings of each detection event
- `diagnostics/boot_log.txt` — boot logs

### Via Serial USB

Connect USB-C and monitor at 115200 baud:
```bash
minicom -b 115200 -D /dev/ttyACM0
```

## Wildlife Detection Tips

### Bird Monitoring
- Deploy during dawn chorus (4:00-7:00 AM) for maximum detection
- Use 48kHz sample rate (birds are mostly below 12kHz)
- Mount at 2-3m height, microphone vents facing outward

### Bat Monitoring
- Switch to 96kHz mode in config.txt for bat echolocation (20-80kHz)
- Deploy near known bat roosts or water crossings
- Monitor from dusk to midnight (peak bat activity)
- Note: 96kHz mode doubles audio buffer size and halves battery life

### Frog/Amphibian Monitoring
- Deploy near ponds, streams, or wetlands
- Best detection during breeding season (spring-summer evenings)
- Lower confidence threshold to 0.5 for frogs (calls can be faint)

### Insect Monitoring
- Cicadas are detected at high confidence in summer
- Mosquito detection requires close proximity (<5m)
- Cricket choruses are easily distinguished from birds

## Maintenance

### Monthly
- Check solar panel for debris or bird droppings
- Verify SD card has free space (rotate if >80% full)
- Check battery voltage via serial monitor

### Quarterly
- Replace desiccant packs in enclosure
- Inspect acoustic mesh for clogging
- Verify antenna connection is secure
- Update firmware via UF2 if new version available

### Annually
- Replace LiPo battery (2000mAh cells degrade after ~500 cycles)
- Check enclosure gasket seal
- Clean microphone vents with compressed air
- Verify LoRa range from gateway position