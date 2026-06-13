# API Reference — Neuro Sense Puck

## BLE Service

### Service UUID: `0xFFA0`

| Char UUID | Name | Type | Access | Description |
|-----------|------|------|--------|-------------|
| 0xFFA1 | Environment Class | uint8 | Read/Notify | 0-15 class index |
| 0xFFA2 | VOC Index | uint16 | Read | 0-500 VOC index |
| 0xFFA3 | PM2.5 | float32 | Read | µg/m³ |
| 0xFFA4 | Temperature | float32 | Read | °C |
| 0xFFA5 | Humidity | float32 | Read | %RH |
| 0xFFA6 | Light Lux | float32 | Read | lux |
| 0xFFA7 | Sound dBA | float32 | Read | Approximate dBA |
| 0xFFA8 | Activity | uint8 | Read | 0=still, 1=walk, 2=run |
| 0xFFA9 | Device Info | string | Read | "NeuroPuck v1.0 by jayis1" |

## Environment Classes

| Index | Name | Typical Conditions |
|-------|------|--------------------|
| 0 | FRESH_OUTDOORS | Low VOC, natural light, low noise, still/walking |
| 1 | STUFFY_OFFICE | High CO₂/VOC, artificial light, low motion |
| 2 | ACTIVE_COMMUTE | Walking/running, street noise, moderate PM |
| 3 | QUIET_HOME | Low noise, warm light, still, comfortable T/H |
| 4 | GYM_WORKOUT | High motion, elevated T/H, music/noise |
| 5 | SLEEP_READY | Dark, cool, silent, still |
| 6 | LOUD_STREET | High dBA, moderate PM, traffic noise |
| 7 | RAIN_OUTDOORS | High humidity, distinctive sound, moderate PM |
| 8 | SUNNY_PARK | High lux, warm, low PM, natural light |
| 9 | CROWDED_INDOOR | High VOC/CO₂, artificial light, speech noise |
| 10 | COOL_BASEMENT | Cool, moderate humidity, dim, musty VOC |
| 11 | HUMID_KITCHEN | High humidity, cooking VOC, warm |
| 12 | WINDY_ROOFTOP | High accel variance, cool, bright |
| 13 | SMOKY_AREA | Very high VOC + PM, distinctive smell profile |
| 14 | SILENT_NIGHT | Very low dBA, dark, still, cool |
| 15 | UNKNOWN | Ambiguous or transition state |

## MQTT Topic (WiFi uplink)

**Topic:** `neuropuck/sensor_data`

**Payload (JSON):**
```json
{
  "class": 3,
  "temp": 22.5,
  "hum": 45.0,
  "voc": 120,
  "pm25": 8.1,
  "lux": 350.0,
  "dba": 42.0,
  "act": 0,
  "ts": 1718200000000
}
```

## Firmware API

### `sensor_manager_init()`
Initialize I2C bus (400kHz) and all 5 I2C sensors + ADC for audio.

### `sensor_manager_read_all(sensor_data_t *data)`
Populate `sensor_data_t` with current readings from all sensors. Returns `ESP_OK` even if individual sensors fail (logged as warnings).

### `inference_engine_init()`
Load INT8 TFLite model from flash, allocate 64KB tensor arena.

### `inference_engine_classify(const sensor_data_t *data)`
Run 12-feature input through 4-layer FC network, return `env_class_t` (0-15).

### `ble_service_update(env_class_t cls, const sensor_data_t *data)`
Update all GATT characteristic values and restart BLE advertising with new manufacturer-specific payload.

### `power_manager_sleep_ms(uint32_t ms)`
Enter ESP32-C6 deep sleep for specified duration. Wakes at `app_main()`.