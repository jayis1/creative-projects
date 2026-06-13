# API Reference — Canopy Listener

## LoRa Detection Protocol

### Packet Format (18 bytes)

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 1 | Sync | uint8 | 0xAA (fixed sync byte) |
| 1 | 1 | Length | uint8 | Total packet length (18) |
| 2 | 4 | UTC Time | uint32 | Unix timestamp (seconds since epoch) |
| 6 | 4 | Latitude | int32 | Latitude × 10^7 (e.g., 51747840 = 51.747840°) |
| 10 | 4 | Longitude | int32 | Longitude × 10^7 (e.g., -1263520 = -0.126352°) |
| 14 | 1 | Class | uint8 | 0-7 detection class (see table below) |
| 15 | 1 | Confidence | uint8 | 0-100 (percentage) |
| 16 | 2 | CRC16 | uint16 | CRC16-CCITT of payload bytes (2-15) |

### Detection Classes

| Value | Class | Description | Key Frequency Range |
|-------|-------|-------------|---------------------|
| 0 | BIRD_CHIP | Small bird calls (chickadee, wren, tit) | 2-8 kHz |
| 1 | BIRD_SONG | Complex bird song (thrush, robin, blackbird) | 1-6 kHz |
| 2 | FROG_CALL | Frog/toad vocalization (croaking) | 0.5-4 kHz |
| 3 | BAT_ECHO | Bat echolocation (ultrasonic) | 20-80 kHz (96kHz mode) |
| 4 | INSECT_BUZZ | Cicada, cricket, mosquito buzzing | 4-16 kHz |
| 5 | RAIN | Rainfall on vegetation | Broadband |
| 6 | WIND | Wind noise (excluded from alerts) | Low frequency |
| 7 | ANTHROPOGENIC | Vehicle, machinery, human speech | Mixed |

### LoRa Radio Settings

| Parameter | Value |
|-----------|-------|
| Frequency | 868 MHz (EU) / 915 MHz (US) |
| Modulation | LoRa |
| Spreading Factor | SF7 |
| Bandwidth | 125 kHz |
| Coding Rate | 4/5 |
| TX Power | 22 dBm |
| Sync Word | 0x3444 (private network) |
| Preamble | 8 symbols |
| Range (line-of-sight) | Up to 15 km |
| Range (forest) | Up to 3 km |

---

## I2C Devices

| Device | I²C Address | Bus | Pins |
|--------|-------------|-----|------|
| BME280 | 0x76 | I2C0 | GP18 (SDA), GP19 (SCL) |
| SSD1306 | 0x3C | I2C0 | GP18 (SDA), GP19 (SCL) |

---

## SPI Devices

### SPI0 — SX1262 LoRa

| Pin | Function |
|-----|----------|
| GP2 | SPI0 CLK |
| GP3 | SPI0 MISO |
| GP4 | SPI0 MOSI |
| GP5 | SPI0 CS (active low) |
| GP6 | DIO1 (interrupt) |
| GP7 | RESET (active low) |
| GP11 | BUSY |

### SPI1 — microSD Card

| Pin | Function |
|-----|----------|
| GP14 | SPI1 CLK |
| GP15 | SPI1 MISO |
| GP16 | SPI1 MOSI |
| GP17 | SPI1 CS (active low) |

---

## UART Devices

### UART0 — L86-Q GNSS

| Pin | Function |
|-----|----------|
| GP0 | UART0 TX → L86-Q RX |
| GP1 | UART0 RX ← L86-Q TX |
| GP12 | PPS (1 pulse-per-second) |
| GP20 | FORCE_ON (keep GPS active) |

Baud rate: 9600, 8N1

---

## Firmware API

### `audio_capture_init(uint32_t sample_rate)`

Initialize PIO-driven I2S audio capture at specified sample rate (48000 or 96000 Hz).

### `audio_capture_record(int16_t *buffer, uint32_t max_samples, uint32_t sample_rate)`

Start recording mono 16-bit PCM audio. Returns immediately; use `audio_capture_wait()` to block.

### `audio_capture_wait(void)`

Block until audio capture is complete. Converts stereo I2S to mono.

### `wildlife_classify_init(void)`

Load wildlife CNN model from flash and allocate inference buffers.

### `wildlife_classify(const int16_t *samples, int num_samples)`

Classify a 512-sample audio chunk. Returns one of 8 wildlife classes.

### `wildlife_classify_get_confidence(void)`

Get confidence score (0.0-1.0) for last classification.

### `lora_radio_init(void)`

Initialize SX1262 LoRa radio with default parameters (868 MHz, SF7, BW125).

### `lora_radio_send_detection(const detection_t *det)`

Send an 18-byte detection packet via LoRa. Blocks until TX complete or timeout.

### `gps_module_init(void)`

Initialize L86-Q GNSS module on UART0 at 9600 baud.

### `gps_module_has_fix(void)`

Check if GPS currently has a valid position fix (reads pending NMEA data).

### `gps_module_get_latitude(void)` / `gps_module_get_longitude(void)`

Get last known position in decimal degrees.

### `gps_module_manage_power(void)`

Manage GPS power cycling: enables for 30s every 5 minutes to conserve battery.

### `env_sensor_init(void)` / `env_sensor_read(env_data_t *data)`

Initialize and read BME280 temperature/humidity/pressure.

### `sd_logger_init(void)`

Initialize SD card and mount FAT filesystem.

### `sd_logger_log_detection(const detection_t *det)`

Append a detection event to `detections.csv` on the SD card.

### `sd_logger_save_wav(const char *filename, const int16_t *samples, int num_samples, uint32_t sample_rate)`

Save audio samples as a WAV file on the SD card.

### `oled_display_init(void)` / `oled_display_update(void)`

Initialize SSD1306 and update display with current status information.

### `power_manager_read_battery_voltage(void)`

Read battery voltage via ADC and 1:2 voltage divider (0-8.4V range).

### `power_manager_deep_sleep_ms(uint32_t ms)`

Enter low-power sleep for specified duration (uses RP2040 sleep modes).

---

## SD Card File Format

### detections.csv

```csv
timestamp,latitude,longitude,class,confidence,temp_c,humidity_pct,battery_v
2026-06-13T14:30:22Z,51.747840,-1.263520,BIRD_SONG,0.87,18.2,65.3,3.91
2026-06-13T14:31:05Z,51.747842,-1.263518,FROG_CALL,0.92,17.8,72.1,3.89
```

### WAV Files

Located in `/audio/` directory:
```
20260613T143022_BIRD_SONG_87.wav    # 48kHz mono, 5 seconds
20260613T143105_FROG_CALL_92.wav     # 48kHz mono, 5 seconds
```

### config.txt

```
sample_rate=48000
capture_seconds=5
duty_cycle_seconds=60
confidence_threshold=0.7
lora_frequency=868
gps_power_cycle=true
```

---

## Serial Monitor

Connect USB-C and open serial at 115200 baud:

```
=== Canopy Listener v1.0 ===
RP2040 dual-core acoustic biodiversity monitor
[CORE0] All subsystems initialized
[BOARD] GPIO initialized
[AUDIO] I2S initialized at 48000 Hz (BCLK=8, LRCLK=9, DATA=10)
[CLASSIFY] Wildlife CNN initialized (8 classes, 512-sample chunks)
[GPS] L86-Q initialized (UART0 @ 9600 baud)
[LORA] SX1262 initialized (868MHz, SF7, BW125, CR4/5, 22dBm)
[SD_LOGGER] Initialized and mounted
[OLED] SSD1306 initialized (128x64)
[POWER] Initialized
[CORE0] Capture cycle #1
[CORE0] Detection: BIRD_SONG (87%) at chunk 7
[CORE0] Env: 18.2°C, 65.3%RH, 1013.2hPa, Bat: 3.91V
[LORA] TX: class=BIRD_SONG conf=87% lat=51.747840 lon=-1.263520
```