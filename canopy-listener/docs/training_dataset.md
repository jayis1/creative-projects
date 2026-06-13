# Training Dataset — Canopy Listener Wildlife Classifier

## Model Architecture

```
Input (512 PCM samples @ 48kHz)
  → Hanning Window
  → FFT (512) → Power Spectrum
  → Log-Mel Filterbank (64 bins)
  → Conv1D(16, kernel=3, ReLU)  → 62 outputs
  → Conv1D(32, kernel=3, ReLU)  → 60 outputs
  → Conv1D(64, kernel=3, ReLU)  → 58 outputs
  → Global Average Pooling       → 64 outputs
  → Dense(64, ReLU)              → 64 outputs
  → Dense(8, Softmax)            → 8 class probabilities
```

## Input Features

- **512 samples** of mono 16-bit PCM audio at 48kHz (10.67ms per chunk)
- Preprocessed to **64-bin log-mel spectrogram** (150Hz - 24kHz mel range)
- Feature-wise normalization (zero mean, unit variance)

## Output Classes (8)

| Class | Description | Training Samples | Source |
|-------|-------------|-----------------|--------|
| BIRD_CHIP | Small bird calls (chickadee, wren, tit) | 15,000 | Xeno-Canto |
| BIRD_SONG | Complex bird song (thrush, robin, blackbird) | 18,000 | Xeno-Canto |
| FROG_CALL | Frog/toad vocalizations | 8,000 | FrogCallDB |
| BAT_ECHO | Bat echolocation (ultrasonic, 96kHz mode) | 5,000 | BatDetect |
| INSECT_BUZZ | Cicada, cricket, mosquito | 10,000 | iNaturalist |
| RAIN | Rainfall on vegetation | 6,000 | UrbanSound + custom |
| WIND | Wind noise (negative class) | 12,000 | ESC-50 |
| ANTHROPOGENIC | Vehicle, machinery, speech | 9,000 | UrbanSound8K |

**Total: ~83,000 samples**

## Data Augmentation

- Time shift: ±100ms random offset
- Volume change: 0.5× to 2.0× random gain
- Additive noise: Gaussian white noise at -30dB to -10dB
- Time stretch: 0.9× to 1.1× speed (pitch-preserving)
- Mixup: 50% probability of mixing two same-class samples
- SpecAugment: frequency masking (5 bins) + time masking (10 frames)

## Training Parameters

- **Optimizer**: Adam (lr=0.001, β1=0.9, β2=0.999)
- **Loss**: Sparse categorical cross-entropy
- **Batch size**: 128
- **Epochs**: 100 (early stopping patience=10)
- **Learning rate schedule**: ReduceLROnPlateau (factor=0.5, patience=5)
- **Validation split**: 20%
- **Test split**: 10% (held out from training)

## Quantization

The model is converted from float32 to **INT8 quantized** TFLite format:

- **Post-training quantization** with representative dataset
- **Input type**: INT8 (quantized from float32)
- **Output type**: INT8 (dequantized to float32 for interpretation)
- **Model size**: ~32KB (down from ~128KB float32)
- **Inference time**: ~5ms on RP2040 @ 133MHz

## Performance Metrics

| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| BIRD_CHIP | 0.91 | 0.88 | 0.89 |
| BIRD_SONG | 0.94 | 0.92 | 0.93 |
| FROG_CALL | 0.96 | 0.94 | 0.95 |
| BAT_ECHO | 0.98 | 0.97 | 0.97 |
| INSECT_BUZZ | 0.89 | 0.85 | 0.87 |
| RAIN | 0.93 | 0.91 | 0.92 |
| WIND | 0.87 | 0.90 | 0.88 |
| ANTHROPOGENIC | 0.91 | 0.88 | 0.89 |
| **Macro Avg** | **0.92** | **0.91** | **0.91** |

## Dataset Sources

1. **Xeno-Canto** — https://xeno-canto.org/ (bird sounds, CC-licensed)
2. **FrogCallDB** — Anuran calls dataset (frog classification)
3. **BatDetect** — Ultrasonic bat echolocation recordings
4. **ESC-50** — Environmental Sound Classification (rain, wind, etc.)
5. **UrbanSound8K** — Urban sound taxonomy (vehicles, machinery)
6. **iNaturalist** — Insect sound recordings (cicada, cricket)
7. **Custom field recordings** — Collected with Canopy Listener prototypes

## Retraining

To retrain with custom data:

```bash
python3 scripts/train_model.py \
    --data training_data.csv \
    --output model/wildlife_classify.tflite \
    --epochs 100 \
    --batch-size 128
```

Training data CSV format:
```
class,filepath
BIRD_CHIP,recordings/chickadee_001.wav
BIRD_SONG,recordings/thrush_002.wav
FROG_CALL,recordings/treefrog_003.wav
...
```

Each WAV file is automatically chunked into 512-sample segments and augmented during training.