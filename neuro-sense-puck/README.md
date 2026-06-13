# Neuro Sense Puck

**A coin-sized, wearable multi-modal environment sensor with on-device ML inference.**

---

## What It Does

The Neuro Sense Puck is a 35mm-diameter PCB that clips to your shirt, bag, or desk and continuously monitors your micro-environment:

- **Air quality** — VOC index, eCO₂, particulate matter (PM1/PM2.5/PM10)
- **Sound landscape** — ambient dB level, spectral class (speech/music/noise/silence)
- **Light character** — lux, color temperature, flicker detection
- **Motion context** — 6-axis IMU for activity classification (sitting/walking/running)
- **Temperature + humidity** — absolute and dew point

All sensor data feeds a lightweight TFLite Micro model on the ESP32-C6 that classifies your current **environment state** into one of 16 categories:

| Class | Meaning |
|-------|---------|
| FRESH_OUTDOORS | Clean air, natural light, low noise |
| STUFFY_OFFICE | High CO₂, artificial light, low motion |
| ACTIVE_COMMUTE | Walking vibration, street noise |
| QUIET_HOME | Low noise, warm light, still |
| GYM_WORKOUT | High motion, elevated temp/humidity |
| SLEEP_READY | Dark, cool, silent, still |
| ... | (10 more fine-grained classes) |

The device exposes results over **BLE 5.0** (low-power advertising + GATT), **Wi-Fi 6** (for OTA updates and dashboard push), and an optional **Zigbee** mesh for multi-puck deployments.

Battery life: **7 days** on a 120 mAh Lipo (low-duty cycling, BLE-only).

---

## Block Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    NEURO SENSE PUCK                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ BME680   │  │ SGP40    │  │ SPS30    │  │ ICM-    │  │
│  │ T/H/VOC  │  │ VOC idx  │  │ PM sensor│  │ 42688-P │  │
│  │ I²C 0x77│  │ I²C 0x59 │  │ I²C 0x69│  │ IMU     │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │ I²C    │  │
│       │              │              │        │ 0x68   │  │
│       └──────────────┴──────────────┴────────┘        │  │
│                        │ I²C bus (400kHz)             │  │
│  ┌─────────────────────▼──────────────────────────┐   │  │
│  │              ESP32-C6-MINI-1                    │   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────────────┐  │   │  │
│  │  │ RISC-V  │ │ WiFi 6  │ │ BLE 5.0 + Zigbee │  │   │  │
│  │  │ 160MHz │ │ 2.4GHz  │ │ 802.15.4         │  │   │  │
│  │  └─────────┘ └─────────┘ └──────────────────┘  │   │  │
│  │  ┌─────────────────────────────────────────┐    │   │  │
│  │  │   TFLite Micro (16-class env infer)     │    │   │  │
│  │  └─────────────────────────────────────────┘    │   │  │
│  └──────────────┬──────────────────────────────────┘   │  │
│                 │                                      │  │
│  ┌──────────────▼───────────────┐  ┌────────────────┐  │  │
│  │     MAX9814 Mic Amp          │  │ TSL2591 Light  │  │  │
│  │     (analog → ADC)          │  │ I²C 0x29       │  │  │
│  └─────────────────────────────┘  └────────────────┘  │  │
│                                                         │  │
│  ┌──────────────────────────────────────────────────┐   │  │
│  │ Power: MCP73831 Lipo charger + AP2112 LDO 3.3V    │   │  │
│  │ Battery: 120mAh Lipo (3.7V)                       │   │  │
│  │ USB-C for charging + UART flash                   │   │  │
│  └──────────────────────────────────────────────────┘   │  │
└─────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (ESP32-C6-MINI-1)

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO0 | I²C SDA | All I²C sensors (pull-up 4.7k) |
| GPIO1 | I²C SCL | All I²C sensors (pull-up 4.7k) |
| GPIO2 | ADC1_CH2 | MAX9814 audio out |
| GPIO3 | SPI CLK | Flash (internal) |
| GPIO4 | SPI MISO | Flash (internal) |
| GPIO5 | SPI MOSI | Flash (internal) |
| GPIO6 | SPS30 RESET | SPS30 pin 5 |
| GPIO7 | SPS30 INT | SPS30 pin 6 |
| GPIO8 | ICM-42688 INT1 | IMU data-ready |
| GPIO12 | USB D+ | USB-C connector |
| GPIO13 | USB D- | USB-C connector |
| GPIO14 | CHARGE_STAT | MCP73831 STAT pin |
| GPIO15 | LED_R | NeoPixel data (WS2812B) |
| GPIO16 | BOOT | Boot button |
| GPIO17 | EN | Power enable (active high) |
| GPIO18 | UART TX | Debug/flash |
| GPIO19 | UART RX | Debug/flash |
| GPIO20 | BME680 INT | Gas sensor alert |

---

## Power Architecture

```
USB-C (5V) ──► MCP73831 ──► Lipo (3.7V 120mAh) ──► AP2112-3.3V ──► VDD

Quiescent: ~12µA (deep sleep, RTC on)
Active (BLE only, 1Hz sample): ~3.2mA avg → 37.5h theoretical, ~7 days with duty cycling
Active (WiFi push): ~68mA burst, 500ms every 5min
```

Duty cycle in normal mode:
1. Wake on RTC alarm (1s interval)
2. Read all I2C sensors (~2ms)
3. Run 16-class inference (~8ms)
4. BLE advertising update (~3ms)
5. Deep sleep (~987ms)

---

## Mechanical

- PCB: 35mm diameter, 1.6mm FR4, 4-layer
- Height: 8mm (components) + 2mm battery = 10mm total
- SPS30 sits in center cutout with airflow channel
- Top: capacitive touch zone (GPIO8 alternate) for tap-to-wake
- Bottom: battery pocket + garment clip slot
- Enclosure: 3D-printed PETG shell (optional, files in `hardware/`)

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── app_main.c          # Entry point, NVS init, task launch
│   ├── sensor_manager.c    # I2C bus init, periodic sensor reads
│   ├── inference_engine.c  # TFLite Micro model load + classify
│   ├── ble_service.c       # GATT server, advertising payload
│   ├── wifi_uplink.c       # MQTT push to dashboard
│   ├── power_manager.c     # Deep sleep, duty cycling, charge monitor
│   ├── audio_classify.c    # ADC sampling + spectral feature extraction
│   └── led_status.c        # NeoPixel feedback patterns
├── components/
│   ├── tflite_micro/       # TFLite Micro library
│   └── model/
│       └── env_classify.tflite  # Quantized INT8 model (48KB)
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow

```c
void app_main(void) {
    nvs_init();
    i2c_bus_init();
    sensor_manager_init();
    ble_service_init();
    inference_engine_init();  // loads TFLite model from flash
    
    while (true) {
        sensor_data_t data = sensor_manager_read_all();
        env_class_t cls = inference_engine_classify(&data);
        ble_service_update(cls, &data);
        led_status_show(cls);
        
        if (wifi_is_connected()) {
            wifi_uplink_push(&data, cls);
        }
        
        power_manager_sleep(1000);  // 1s deep sleep
    }
}
```

---

## BLE GATT Service

```
Service UUID: 0xFFA0 (NeuroSense)
  ├── Char 0xFFA1: Environment Class (read/notify) — uint8
  ├── Char 0xFFA2: VOC Index (read) — uint16
  ├── Char 0xFFA3: PM2.5 (read) — float32
  ├── Char 0xFFA4: Temperature (read) — float32
  ├── Char 0xFFA5: Humidity (read) — float32
  ├── Char 0xFFA6: Light Lux (read) — float32
  ├── Char 0xFFA7: Sound dBA (read) — float32
  ├── Char 0xFFA8: Activity (read) — uint8 (0=still,1=walk,2=run)
  └── Char 0xFFA9: Device Info (read) — string
```

BLE advertising packet (31 bytes):
```
[Flags] [Complete 16-bit UUID: FFA0] [Mfr-specific: env_class(1), voc(2), pm25(2), temp(1), activity(1)]
```

---

## ML Model Details

- Architecture: 4-layer fully connected INT8 quantized
- Input: 12 features (normalized sensor vector)
- Output: 16-class softmax
- Size: 48KB flash, ~8ms inference on ESP32-C6 @ 160MHz
- Training data: synthetic + real-world sensor logs (see `docs/training_dataset.md`)

```
Input (12) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(16, ReLU) → Dense(16, Softmax)
```

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | ESP32-C6-MINI-1 | Module | 1 | $3.20 | WiFi6/BLE5/Zigbee |
| 2 | BME680 | LGA-8 3x3 | 1 | $2.80 | T/H/Pressure/VOC |
| 3 | SGP40 | DFN-6 2.5x2.5 | 1 | $1.90 | VOC index |
| 4 | SPS30 | Custom | 1 | $8.50 | PM sensor |
| 5 | ICM-42688-P | LGA-14 2.5x3 | 1 | $2.40 | 6-axis IMU |
| 6 | TSL2591 | TMB-6 | 1 | $1.20 | Light sensor |
| 7 | MAX9814 | DFN-10 | 1 | $0.80 | Mic amp |
| 8 | MEMS Mic (SPH0645) | LGA-5 | 1 | $1.10 | I2S mic (alt) |
| 9 | MCP73831 | SOT-23-5 | 1 | $0.40 | Lipo charger |
| 10 | AP2112-3.3 | SOT-223 | 1 | $0.30 | LDO |
| 11 | Lipo 120mAh | Custom pouch | 1 | $2.50 | 3.7V |
| 12 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Power+data |
| 13 | WS2812B-2020 | 2020 | 1 | $0.15 | Status LED |
| 14 | Passives (R/C/L) | 0402 | ~30 | $0.50 | Pullups, decoupling |
| 15 | PCB 4-layer 35mm | Round | 1 | $1.50 | JLCPCB |

**Total estimated BOM: ~$26.60** (qty 1)

---

## Directory Structure

```
neuro-sense-puck/
├── README.md                  # This file
├── schematic/
│   ├── neuro_sense_puck.kicad_sch
│   ├── neuro_sense_puck.kicad_pcb
│   └── neuro_sense_puck.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── app_main.c
│   │   ├── sensor_manager.c
│   │   ├── sensor_manager.h
│   │   ├── inference_engine.c
│   │   ├── inference_engine.h
│   │   ├── ble_service.c
│   │   ├── ble_service.h
│   │   ├── wifi_uplink.c
│   │   ├── wifi_uplink.h
│   │   ├── power_manager.c
│   │   ├── power_manager.h
│   │   ├── audio_classify.c
│   │   ├── audio_classify.h
│   │   ├── led_status.c
│   │   └── led_status.h
│   ├── components/
│   │   └── model/
│   │       └── env_classify.tflite
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── hardware/
│   ├── BOM.csv
│   ├── gerbers/
│   ├── placement/
│   └── enclosure/
│       └── puck_shell.step
├── verilog/
│   └── (none — using ESP32-C6 built-in peripherals)
└── docs/
    ├── training_dataset.md
    ├── api_reference.md
    └── assembly_guide.md
```

---

## Getting Started

### Flash Firmware

```bash
# Install ESP-IDF v5.3+
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/neuro-sense-puck/firmware
idf.py set-target esp32c6
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

### Read BLE Data

```bash
# Using bleak (Python)
pip install bleak
python3 scripts/read_puck.py --mac AA:BB:CC:DD:EE:FF
```

### Train Custom Model

```python
# See docs/training_dataset.md for dataset format
python3 scripts/train_model.py --data custom_data.csv --output model/env_classify.tflite
```

---

*Invented 2026-06-12 by jayis1*