#!/usr/bin/env python3
"""
train_model.py — Train wildlife classification CNN for Canopy Listener

Usage:
    python3 train_model.py --data training_data.csv --output model/wildlife_classify.tflite
"""

import argparse
import numpy as np
import os
import sys

# Check for TensorFlow
try:
    import tensorflow as tf
except ImportError:
    print("Error: TensorFlow is required for training.")
    print("Install with: pip install tensorflow")
    sys.exit(1)

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Wildlife class names
CLASS_NAMES = [
    "BIRD_CHIP",      # 0
    "BIRD_SONG",       # 1
    "FROG_CALL",       # 2
    "BAT_ECHO",        # 3
    "INSECT_BUZZ",     # 4
    "RAIN",            # 5
    "WIND",            # 6
    "ANTHROPOGENIC",   # 7
]

NUM_CLASSES = len(CLASS_NAMES)

# Audio parameters
SAMPLE_RATE = 48000
CHUNK_SIZE = 512
FFT_SIZE = 512
MEL_BINS = 64


def build_model():
    """Build the 5-layer 1D CNN wildlife classifier."""
    model = tf.keras.Sequential([
        # Input: 64-bin log-mel spectrogram (1D)
        tf.keras.layers.Input(shape=(MEL_BINS, 1)),

        # Conv1D layers
        tf.keras.layers.Conv1D(16, kernel_size=3, activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Conv1D(32, kernel_size=3, activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Conv1D(64, kernel_size=3, activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),

        # Global average pooling
        tf.keras.layers.GlobalAveragePooling1D(),

        # Dense layers
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(NUM_CLASSES, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    return model


def compute_log_mel_spectrogram(samples, sample_rate=48000):
    """Compute log-mel spectrogram from a chunk of audio samples."""
    # Apply Hanning window
    window = np.hanning(len(samples))
    windowed = samples.astype(np.float32) / 32768.0 * window

    # Compute FFT
    fft_result = np.fft.rfft(windowed, n=FFT_SIZE)
    power_spectrum = np.abs(fft_result) ** 2

    # Compute mel filterbank
    low_mel = 2595 * np.log10(1 + 150.0 / 700.0)
    high_mel = 2595 * np.log10(1 + min(24000.0, sample_rate / 2) / 700.0)
    mel_points = np.linspace(low_mel, high_mel, MEL_BINS + 2)
    hz_points = 700.0 * (10 ** (mel_points / 2595.0) - 1)

    bin_points = np.floor((FFT_SIZE + 1) * hz_points / sample_rate).astype(int)

    # Create triangular filterbank
    filterbank = np.zeros((MEL_BINS, len(power_spectrum)))
    for i in range(MEL_BINS):
        f_left = bin_points[i]
        f_center = bin_points[i + 1]
        f_right = bin_points[i + 2]

        for j in range(f_left, f_center):
            if j < len(power_spectrum):
                filterbank[i, j] = (j - f_left) / max(f_center - f_left, 1)
        for j in range(f_center, f_right):
            if j < len(power_spectrum):
                filterbank[i, j] = (f_right - j) / max(f_right - f_center, 1)

    # Apply filterbank and take log
    mel_spec = np.dot(filterbank, power_spectrum)
    log_mel = np.log(mel_spec + 1e-10)

    return log_mel


def augment_chunk(chunk, sample_rate=48000):
    """Apply data augmentation to an audio chunk."""
    augmented = chunk.copy()

    # Random time shift (±50 samples)
    shift = np.random.randint(-50, 50)
    augmented = np.roll(augmented, shift)

    # Random volume change (0.5x to 2.0x)
    gain = np.random.uniform(0.5, 2.0)
    augmented = (augmented * gain).astype(np.int16)

    # Additive noise (-30dB to -10dB)
    noise_level = np.random.uniform(0.01, 0.1)
    noise = np.random.normal(0, noise_level, len(augmented)).astype(np.int16)
    augmented = augmented + noise

    # Clip to int16 range
    augmented = np.clip(augmented, -32768, 32767).astype(np.int16)

    return augmented


def load_and_preprocess_data(data_dir, augment=True):
    """Load WAV files from class directories and extract log-mel features."""
    X = []
    y = []

    for class_idx, class_name in enumerate(CLASS_NAMES):
        class_dir = os.path.join(data_dir, class_name)
        if not os.path.exists(class_dir):
            print(f"Warning: No data directory for {class_name}")
            continue

        files = [f for f in os.listdir(class_dir) if f.endswith('.wav')]
        print(f"Loading {len(files)} files for {class_name}...")

        for filename in files:
            filepath = os.path.join(class_dir, filename)

            # Load WAV file
            import wave
            with wave.open(filepath, 'rb') as wf:
                n_frames = wf.getnframes()
                raw_data = wf.readframes(n_frames)
                samples = np.frombuffer(raw_data, dtype=np.int16)

            # Chunk into 512-sample segments
            n_chunks = len(samples) // CHUNK_SIZE
            for i in range(n_chunks):
                chunk = samples[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]

                # Compute log-mel features
                features = compute_log_mel_spectrogram(chunk)
                X.append(features)
                y.append(class_idx)

                # Add augmented version
                if augment:
                    aug_chunk = augment_chunk(chunk)
                    aug_features = compute_log_mel_spectrogram(aug_chunk)
                    X.append(aug_features)
                    y.append(class_idx)

    X = np.array(X)
    y = np.array(y)

    # Normalize features
    mean = np.mean(X)
    std = np.std(X) + 1e-10
    X = (X - mean) / std

    # Reshape for Conv1D: (samples, 64, 1)
    X = X.reshape(X.shape[0], MEL_BINS, 1)

    print(f"Total samples: {len(X)}")
    print(f"Feature shape: {X.shape}")

    return X, y


def train(args):
    """Train the wildlife classification model."""
    print(f"Loading data from {args.data}...")
    X, y = load_and_preprocess_data(args.data, augment=True)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.1, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )

    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Test samples: {len(X_test)}")

    # Build model
    model = build_model()
    model.summary()

    # Train
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                patience=10, restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                factor=0.5, patience=5, min_lr=1e-6
            ),
        ]
    )

    # Evaluate
    test_loss, test_acc = model.evaluate(X_test, y_test)
    print(f"\nTest accuracy: {test_acc:.4f}")
    print(f"Test loss: {test_loss:.4f}")

    # Convert to TFLite with INT8 quantization
    print("\nConverting to TFLite INT8...")

    def representative_dataset():
        for i in range(min(500, len(X_train))):
            yield [X_train[i:i+1].astype(np.float32)]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_model = converter.convert()

    # Save model
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, 'wb') as f:
        f.write(tflite_model)

    print(f"\nTFLite INT8 model saved to {args.output}")
    print(f"Model size: {len(tflite_model) / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Train wildlife classification model for Canopy Listener"
    )
    parser.add_argument("--data", required=True,
                       help="Path to training data directory")
    parser.add_argument("--output", default="wildlife_classify.tflite",
                       help="Output TFLite model path")
    parser.add_argument("--epochs", type=int, default=100,
                       help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=128,
                       help="Training batch size")
    args = parser.parse_args()

    train(args)


if __name__ == "__main__":
    main()