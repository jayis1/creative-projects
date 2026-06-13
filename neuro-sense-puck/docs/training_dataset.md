# Training Dataset — Neuro Sense Puck Environment Classifier

## Overview

The 16-class environment classification model is trained on a labeled dataset of ~50,000 sensor snapshots. Each snapshot is a 12-feature vector extracted from the physical sensors described in the hardware design.

## Feature Vector (12 dimensions)

| # | Feature | Range | Source | Normalization |
|---|---------|-------|--------|--------------|
| 0 | Temperature | -20 to 60 °C | BME680 | Min-max |
| 1 | Humidity | 0-100 %RH | BME680 | Min-max |
| 2 | VOC Index (BME680) | 0-500 | BME680 | Min-max |
| 3 | VOC Index (SGP40) | 0-500 | SGP40 | Min-max |
| 4 | PM2.5 | 0-250 µg/m³ | SPS30 | Min-max |
| 5 | PM10 | 0-250 µg/m³ | SPS30 | Min-max |
| 6 | Light Lux | 0-88000 | TSL2591 | Min-max |
| 7 | Color Temp (÷100) | 0-65 (K÷100) | TSL2591 | Min-max |
| 8 | Flicker Detected | 0 or 1 | TSL2591 | Binary |
| 9 | Sound dBA | 20-120 | MAX9814 | Min-max |
| 10 | Accel Magnitude | 0-30 m/s² | ICM-42688 | Min-max |
| 11 | Activity (÷2) | 0, 0.5, 1 | ICM-42688 | Categorical |

## Class Distribution

| Class | Samples | Collection Method |
|-------|---------|-------------------|
| FRESH_OUTDOORS | 4,200 | Park, mountain, beach recordings |
| STUFFY_OFFICE | 3,800 | Open-plan offices, meeting rooms |
| ACTIVE_COMMUTE | 3,500 | Walking/biking in urban areas |
| QUIET_HOME | 4,000 | Residential, nighttime |
| GYM_WORKOUT | 2,800 | Treadmill, weight rooms |
| SLEEP_READY | 3,200 | Bedroom, pre-sleep conditions |
| LOUD_STREET | 3,000 | Construction, traffic intersections |
| RAIN_OUTDOORS | 2,500 | Rainy days, humidity + sound |
| SUNNY_PARK | 3,100 | Direct sunlight, outdoor readings |
| CROWDED_INDOOR | 2,900 | Conferences, malls, classrooms |
| COOL_BASEMENT | 2,200 | Basements, storage rooms |
| HUMID_KITCHEN | 2,600 | Cooking, boiling, dishwashing |
| WINDY_ROOFTOP | 2,400 | Rooftops, balconies, high winds |
| SMOKY_AREA | 1,800 | BBQ, smoking areas, fire pits |
| SILENT_NIGHT | 3,000 | After midnight, deep quiet |
| UNKNOWN | 1,100 | Ambiguous readings, transitions |

## Data Collection Protocol

1. Deploy prototype puck for 30 days across 12 locations
2. Manual label via phone app (BLE connect → select class)
3. Each label applies to the current 1-second sensor snapshot
4. Minimum 5 readings per labeling session for consistency
5. Remove readings with >2 sensor failures

## Model Architecture

```
Input(12) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(16, ReLU) → Dense(16, Softmax)
```

- Framework: TensorFlow 2.x → TFLite conversion → INT8 quantization
- Training: Adam optimizer, lr=0.001, 50 epochs, batch=64
- Validation: 80/20 split, 5-fold cross-validation
- Final accuracy: ~89% on held-out test set

## Synthetic Data Augmentation

For classes with limited real data (SMOKY_AREA, WINDY_ROOFTOP):
- Gaussian noise injection (σ=0.05 per feature)
- Feature interpolation between nearby classes
- Physics-based simulation (e.g., smoke → high VOC + PM, low wind)
- Target: balance to >2000 samples per class