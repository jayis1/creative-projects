# Canopy Listener

**A solar-powered acoustic biodiversity monitor that records, classifies, and reports wildlife sounds in real time.**

---

## What It Does

The Canopy Listener is a rugged, weatherproof device that straps to a tree or pole in forests, wetlands, or fields and continuously listens to the acoustic environment. Using dual MEMS microphones and a lightweight CNN running on the RP2040's dual Cortex-M0+ cores, it:

- **Records ultrasonic audio** — stereo 48kHz (up to 96kHz in bat mode) via ICS-43434 MEMS mics
- **Classifies wildlife sounds** — birds, frogs, bats, insects, and anthropogenic noise using a 5-layer quantized CNN (8 classes)
- **Timestamps with GPS** — L86-Q GNSS provides UTC time and location for every detection
- **Logs to SD card** — WAV files saved per detection event, plus a detections.csv summary
- **Uplinks via LoRa** — SX1262 sends detection summaries over 868/915MHz to a gateway up to 15km away
- **Displays status** — SSD1306 OLED shows species count, battery, storage, and GNSS fix
- **Runs on solar** — MCP73871 manages solar panel + USB-C charging of a 2000mAh LiPo; runs indefinitely in good sun

### Detection Classes

| Class | Meaning | Key Frequency |
|-------|---------|---------------|
| BIRD_CHIP | Small bird calls (chickadee, wren) | 2-8 kHz |
| BIRD_SONG | Complex bird song (thrush, robin) | 1-6 kHz |
| FROG_CALL | Frog/toad vocalization | 0.5-4 kHz |
| BAT_ECHO | Bat echolocation (ultrasonic) | 20-80 kHz |
| INSECT_BUZZ | Cicada, cricket, mosquito | 4-16 kHz |
| RAIN | Rainfall on vegetation | Broadband |
| WIND | Wind noise (to exclude) | Low freq |
| ANTHROPOGENIC | Vehicle, machinery, speech | Mixed |

Battery life: **10 days** on 2000mAh LiPo (no sun), **indefinite** with solar in moderate climate.

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                       CANOPY LISTENER                             │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐               │
│  │ ICS-43434   │  │ ICS-43434   │  │  L86-Q     │               │
│  │ Mic L (I2S) │  │ Mic R (I2S) │  │  GNSS      │               │
│  │ WS0221/L/R  │  │ WS0221/L/R  │  │  UART0     │               │
│  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘               │
│         │ I2S DATA        │                │ UART                 │
│  ┌──────┴─────────────────┴──────┐   ┌────┴─────┐               │
│  │     RP2040 (QFN-56)          │   │ PPS →    │               │
│  │  ┌───────────┐ ┌──────────┐  │   │ GP23     │               │
│  │  │ Core 0:   │ │ PIO SM0  │  │   └──────────┘               │
│  │  │ CNN infer │ │ I2S BCLK │  │                               │
│  │  │ + logging │ │ + LRCLK  │  │   ┌────────────┐            │
│  │  ├───────────┤ ├──────────┤  │   │ BME280      │            │
│  │  │ Core 1:   │ │ PIO SM1  │  │   │ T/H/P       │            │
│  │  │ LoRa TX   │ │ WS2812B  │  │   │ I²C 0x76    │            │
│  │  │ + display │ │          │  │   └──────┬─────┘            │
│  │  └───────────┘ └──────────┘  │          │ I²C               │
│  │  ┌───────────────────────┐   │   ┌──────┴─────┐            │
│  │  │ 264KB SRAM            │   │   │ SSD1306     │            │
│  │  │ 16MB QSPI Flash      │   │   │ 128×64 OLED │            │
│  │  │ (W25Q128JVSIQ)       │   │   │ I²C 0x3C    │            │
│  │  └───────────────────────┘   │   └──────┬─────┘            │
│  └──────────┬───────────────────┘          │ I²C               │
│             │ SPI0+GPIO               ┌─────┴──────┐           │
│  ┌──────────┴──────────────┐          │ Shared I²C │           │
│  │       SX1262            │          │ Bus (SDA18 │           │
│  │  LoRa 868/915MHz        │          │      SCL19)│           │
│  │  SPI0 + CS/IRQ/RST/BUSY│          └────────────┘           │
│  └─────────────────────────┘                                    │
│             │ SPI1+GPIO                                         │
│  ┌──────────┴──────────────┐                                    │
│  │   microSD Card Slot     │                                    │
│  │   SPI1 + CS             │                                    │
│  └─────────────────────────┘                                    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Power: MCP73871 (solar+USB) → LiPo 2000mAh → RT9013 3.3V│  │
│  │  Solar: 5V 2W panel (USB-C or barrel jack)                │  │
│  │  USB-C: charging + firmware flash (UF2)                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (RP2040 QFN-56)

| Pin | Function | Connected To |
|-----|----------|-------------|
| GP0 | UART0 TX | L86-Q GNSS RX |
| GP1 | UART0 RX | L86-Q GNSS TX |
| GP2 | SPI0 CLK | SX1262 SCLK |
| GP3 | SPI0 MISO | SX1262 MISO |
| GP4 | SPI0 MOSI | SX1262 MOSI |
| GP5 | SPI0 CS | SX1262 NSS (active low) |
| GP6 | GPIO IRQ | SX1262 DIO1 (interrupt) |
| GP7 | GPIO OUT | SX1262 RESET (active low) |
| GP8 | PIO SM0 OUT | I2S BCLK (both mics) |
| GP9 | PIO SM0 OUT | I2S LRCLK (both mics) |
| GP10 | PIO SM0 IN | I2S DATA (daisy-chained mics) |
| GP11 | GPIO IN | SX1262 BUSY |
| GP12 | GPIO IN | L86-Q PPS (1 pulse-per-second) |
| GP13 | PIO SM1 OUT | WS2812B DIN (RGB LED) |
| GP14 | SPI1 CLK | SD card CLK |
| GP15 | SPI1 MISO | SD card DO |
| GP16 | SPI1 MOSI | SD card DI |
| GP17 | SPI1 CS | SD card CS (active low) |
| GP18 | I²C0 SDA | BME280 + SSD1306 SDA |
| GP19 | I²C0 SCL | BME280 + SSD1306 SCL |
| GP20 | GPIO OUT | L86-Q FORCE_ON (keep GPS active) |
| GP21 | GPIO IN | User button (active low, internal pull-up) |
| GP22 | GPIO OUT | Power enable (boost converter) |
| GP23 | GPIO IN | MCP73871 PG (power good) |
| GP24 | GPIO IN | MCP73871 STAT2 (charge status) |
| GP25 | ADC (GP25) | Battery voltage divider (1:2 ratio) |
| GP26 | ADC (GP26) | Solar voltage divider (1:3 ratio) |
| GP27 | GPIO OUT | Mic enable (L/R select on ICS-43434) |
| GP28 | GPIO IN | BOOT button (active low) |
| RUN | Reset | Reset button |
| QSPI_SS | QSPI | W25Q128 CS |
| QSPI_SCLK | QSPI | W25Q128 CLK |
| QSPI_SD0-SD3 | QSPI | W25Q128 D0-D3 |

---

## Power Architecture

```
Solar Panel (5V 2W) ──┐
                       ├──► MCP73871 ──► LiPo (3.7V 2000mAh) ──► RT9013-3.3V ──► VDD (3.3V)
USB-C (5V) ───────────┘     (MPPT)          │                    (LDO)
                                            │
                                     ┌──────┴──────┐
                                     │  VBAT_SENSE │─► GP26 (ADC, voltage divider)
                                     └─────────────┘

Quiescent:  ~0.5mA  (deep sleep, RTC + watchdog)
Idle:        ~8mA    (RP2040 idle, OLED off, LoRa sleep)
Recording:   ~45mA   (RP2040 active, mics on, SD card writing)
LoRa TX:     ~120mA  (burst, 2s max)
LoRa RX:     ~10mA   (continuous receive)
GPS active:  ~25mA   (acquiring fix)
GPS tracking: ~18mA  (continuous fix)
Full active:  ~85mA  (recording + GPS + display)

2000mAh LiPo at 85mA avg → ~23.5 hours (no solar)
With 2W solar (6 effective hours) → indefinite deployment
```

Duty cycle in field deployment:
1. Deep sleep (RTC wake every 60s) → 59.5s
2. Wake on RTC alarm
3. Read BME280 + check battery (~2ms)
4. Start I2S capture for 5 seconds (~5s)
5. Run CNN inference on audio chunks (~15ms per 512-sample chunk)
6. If detection: log to SD card, send LoRa packet
7. Every 5 minutes: enable GPS for 30s to get fix
8. Update OLED display
9. Deep sleep

---

## Mechanical

- PCB: 80mm × 50mm, 1.6mm FR4, 4-layer
- Enclosure: IP67 polycarbonate (114mm × 76mm × 40mm)
- Top face: OLED window, RGB LED diffuser
- Side 1: Microphone acoustic vents (2× 3mm holes with acoustic mesh)
- Side 2: microSD slot (rubber gasket cover), USB-C port
- Bottom: Solar panel connector (IP67 M8), tree strap mounts
- Antenna: LoRa 868/915MHz whip antenna on SMA connector (top edge)
- GPS: Ceramic patch antenna on top face (under polycarbonate)
- Weight: 85g (device) + 2000mAh LiPo (45g) + solar panel (60g)

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── main.c              # Entry point, core assignment, scheduler
│   ├── audio_capture.c     # PIO-driven I2S capture, DMA to circular buffer
│   ├── audio_capture.h
│   ├── wildlife_classify.c # CNN inference on audio spectrograms
│   ├── wildlife_classify.h
│   ├── lora_radio.c        # SX1262 driver, LoRa TX/RX
│   ├── lora_radio.h
│   ├── gps_module.c        # L86-Q GNSS control, NMEA parsing
│   ├── gps_module.h
│   ├── sd_logger.c         # SD card WAV + CSV logging
│   ├── sd_logger.h
│   ├── env_sensor.c        # BME280 T/H/P reading
│   ├── env_sensor.h
│   ├── oled_display.c      # SSD1306 128×64 display driver
│   ├── oled_display.h
│   ├── power_manager.c     # Deep sleep, solar/USB charge monitoring
│   ├── power_manager.h
│   └── tflite_model.h      # Quantized model weights (embedded)
├── pico_sdk_import.cmake
├── CMakeLists.txt
└── sdkconfig
```

### Key Firmware Flow

```c
int main(void) {
    stdio_usb_init();
    board_init();       // clocks, GPIO, power
    
    // Core 0: Audio + ML + Logging
    multicore_launch_core1(core1_entry);  // LoRa + Display + GPS
    
    audio_capture_init(48000);  // 48kHz stereo
    wildlife_classify_init();    // load CNN model
    env_sensor_init();
    sd_logger_init();
    
    while (true) {
        // Read environmental context
        env_data_t env;
        env_sensor_read(&env);
        
        // Capture audio buffer (5s at 48kHz)
        int16_t audio_buf[2 * 48000 * 5];  // stereo, 5 seconds
        audio_capture_start(audio_buf, sizeof(audio_buf));
        audio_capture_wait();
        
        // Classify each 512-sample chunk
        for (int i = 0; i < NUM_CHUNKS; i++) {
            wildlife_class_t cls = wildlife_classify(&audio_buf[i * 512]);
            float confidence = wildlife_classify_get_confidence();
            
            if (cls != WIND_CLASS && confidence > 0.7f) {
                // Log detection
                detection_t det = {
                    .timestamp = gps_get_utc(),
                    .latitude = gps_get_lat(),
                    .longitude = gps_get_lon(),
                    .species = cls,
                    .confidence = confidence,
                    .temp = env.temperature,
                    .humidity = env.humidity
                };
                sd_logger_log_detection(&det);
                
                // Send to Core 1 for LoRa TX
                multicore_fifo_push_blocking((uint32_t)&det);
            }
        }
        
        // Deep sleep until next cycle
        power_manager_deep_sleep_ms(60000);  // 60 seconds
    }
}

void core1_entry(void) {
    lora_radio_init();
    oled_display_init();
    gps_module_init();
    
    while (true) {
        // Check for detection events from Core 0
        if (multicore_fifo_rvalid()) {
            detection_t *det = (detection_t *)multicore_fifo_pop_blocking();
            lora_radio_send_detection(det);
        }
        
        // Update display every 5s
        oled_display_update();
        
        // Manage GPS power (30s every 5 min)
        gps_module_manage_power();
        
        sleep_ms(100);
    }
}
```

---

## LoRa Protocol

Detection packets sent over LoRa (SX1262, 868MHz EU / 915MHz US):

```
Frame format (variable length, LoRa SF7, 125kHz):
┌──────┬──────┬──────────┬───────────┬──────┬──────┬──────────┬──────┐
│ 0xAA │ LEN  │ UTC_TIME │ LAT (4B)  │ LON  │ CLASS│ CONF(1B) │ CRC  │
│ sync │ 1B   │ 4B       │ int32×1e7 │ 4B   │ 1B   │ uint8%   │ 2B   │
└──────┴──────┴──────────┴───────────┴──────┴──────┴──────────┴──────┘
Total: 18 bytes per detection
```

Gateway receives packets and posts to a cloud dashboard (separate project).

---

## CNN Model Details

- Architecture: 5-layer 1D convolutional INT8 quantized network
- Input: 512-sample mono audio chunk (10.67ms at 48kHz)
- Preprocessing: Compute 64-bin log-mel spectrogram from 512-sample FFT
- Output: 8-class softmax
- Size: 32KB flash, ~5ms inference on RP2040 @ 133MHz (Core 0)
- Training data: Xeno-Canto (birds), BatDetect (bats), FrogCallDB (frogs), synthetic insects/rain/wind

```
Input (512) → FFT(512) → LogMel(64) → Conv1D(16, k=3) → Conv1D(32, k=3) → 
Conv1D(64, k=3) → Dense(64, ReLU) → Dense(8, Softmax)
```

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | RP2040 | QFN-56 7×7 | 1 | $1.50 | Dual Cortex-M0+, 133MHz |
| 2 | W25Q128JVSIQ | SOIC-8 | 1 | $0.80 | 16MB QSPI flash |
| 3 | ICS-43434 | LGA-6 3.5×2.65 | 2 | $1.30 | MEMS mic, I2S, 48kHz |
| 4 | SX1262 | QFN-24 4×4 | 1 | $3.80 | LoRa 868/915MHz |
| 5 | L86-Q | LCC 9.7×9.7 | 1 | $6.50 | GNSS (GPS/GLONASS/BeiDou) |
| 6 | BME280 | LGA-8 2.5×2.5 | 1 | $2.20 | T/H/P sensor |
| 7 | SSD1306 | Module 128×64 | 1 | $1.50 | OLED display |
| 8 | MCP73871 | DFN-10 3×3 | 1 | $1.20 | Solar + USB LiPo charger |
| 9 | RT9013-3.3 | SOT-23-5 | 1 | $0.25 | 3.3V LDO |
| 10 | LiPo 2000mAh | Custom pouch | 1 | $4.50 | 3.7V |
| 11 | microSD slot | Molex 504077 | 1 | $0.60 | Push-push, spring eject |
| 12 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Power + data |
| 13 | SMA connector | Edge-mount | 1 | $0.80 | LoRa antenna |
| 14 | LoRa antenna | 868/915MHz whip | 1 | $2.00 | 1/4-wave whip |
| 15 | WS2812B-2020 | 2020 | 1 | $0.15 | Status LED |
| 16 | Crystal 12MHz | HC49/SMD | 1 | $0.20 | RP2040 clock |
| 17 | Passives (R/C/L) | 0402 | ~50 | $0.80 | Pullups, decoupling, filters |
| 18 | Voltage dividers | 0402 | 6 | $0.06 | Battery/solar sensing |
| 19 | PCB 4-layer 80×50mm | Rect | 1 | $2.00 | JLCPCB |
| 20 | IP67 enclosure | Polycarbonate | 1 | $3.50 | Custom or off-the-shelf |

**Total estimated BOM: ~$32.80** (qty 1)

---

## Directory Structure

```
canopy-listener/
├── README.md                  # This file
├── schematic/
│   ├── canopy_listener.kicad_sch
│   ├── canopy_listener.kicad_pcb
│   └── canopy_listener.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── main.c
│   │   ├── audio_capture.c
│   │   ├── audio_capture.h
│   │   ├── wildlife_classify.c
│   │   ├── wildlife_classify.h
│   │   ├── lora_radio.c
│   │   ├── lora_radio.h
│   │   ├── gps_module.c
│   │   ├── gps_module.h
│   │   ├── sd_logger.c
│   │   ├── sd_logger.h
│   │   ├── env_sensor.c
│   │   ├── env_sensor.h
│   │   ├── oled_display.c
│   │   ├── oled_display.h
│   │   ├── power_manager.c
│   │   └── power_manager.h
│   ├── pico_sdk_import.cmake
│   ├── CMakeLists.txt
│   └── sdkconfig
├── hardware/
│   └── BOM.csv
├── scripts/
│   ├── classify_recording.py
│   └── gateway_receiver.py
└── docs/
    ├── assembly_guide.md
    ├── api_reference.md
    └── field_deployment_guide.md
```

---

## Getting Started

### Flash Firmware

```bash
# Install Pico SDK
git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk && git submodule update --init

# Build firmware
cd SoC-Device-Inventions/canopy-listener/firmware
mkdir build && cd build
cmake ..
make -j4

# Flash via UF2 (hold BOOT button, plug USB)
# Device appears as USB mass storage — copy canopy_listener.uf2
# Or use OpenOCD/SWD:
openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "program canopy_listener.elf verify reset exit"
```

### Read Detections via LoRa

```bash
# Using a second Canopy Listener or SX1262 dev board as gateway
pip install pyserial
python3 scripts/gateway_receiver.py --port /dev/ttyUSB0
```

### Classify Audio File

```python
# Offline classification of a WAV file
python3 scripts/classify_recording.py --input recording.wav --model model/wildlife_classify.tflite
```

### Monitor via Serial

```bash
# Connect USB-C, open serial at 115200 baud
minicom -b 115200 -D /dev/ttyACM0
# Output: detections, sensor readings, system status
```

---

## LoRa Detection Packet API

Each detection is transmitted as an 18-byte LoRa packet:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | Sync | 0xAA (fixed) |
| 1 | 1 | Length | Total packet length |
| 2 | 4 | UTC Time | Unix timestamp (uint32) |
| 6 | 4 | Latitude | int32, ×10^7 (e.g., 51747840 = 51.747840°) |
| 10 | 4 | Longitude | int32, ×10^7 |
| 14 | 1 | Class | 0-7 detection class |
| 15 | 1 | Confidence | 0-100 (percent) |
| 16 | 2 | CRC16 | Packet integrity |

---

## I2C Device Addresses

| Device | I²C Address | Bus |
|--------|-------------|-----|
| BME280 | 0x76 | I2C0 (GP18/GP19) |
| SSD1306 | 0x3C | I2C0 (GP18/GP19) |

---

## SD Card File Structure

```
/mount/
├── detections.csv        # Rolling detection log
├── config.txt            # Device configuration
├── audio/
│   ├── 20260613T143022_BIRD_SONG_87.wav
│   ├── 20260613T143027_FROG_CALL_92.wav
│   └── ...
└── diagnostics/
    └── boot_log.txt
```

`detections.csv` format:
```
timestamp,latitude,longitude,class,confidence,temp_c,humidity_pct,battery_v
2026-06-13T14:30:22Z,51.747840,-1.263520,BIRD_SONG,0.87,18.2,65.3,3.91
```

---

*Invented 2026-06-13 by jayis1*