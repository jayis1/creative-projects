#!/usr/bin/env python3
"""
classify_recording.py — Classify a WAV audio file using the wildlife CNN model

Usage:
    python3 classify_recording.py --input recording.wav [--model model/wildlife_classify.tflite]
"""

import argparse
import wave
import numpy as np
import struct
import sys
import os

# Try to import tflite_runtime (lightweight) or fall back to full tensorflow
try:
    import tflite_runtime.interpreter as tflite
    HAS_TFLITE = True
except ImportError:
    try:
        import tensorflow as tf
        HAS_TFLITE = False
    except ImportError:
        print("Error: Install tflite-runtime or tensorflow:")
        print("  pip install tflite-runtime")
        print("  or: pip install tensorflow")
        sys.exit(1)

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

# Mel spectrogram parameters
FFT_SIZE = 512
MEL_BINS = 64
MEL_LOW_FREQ = 150.0
MEL_HIGH_FREQ = 24000.0
CHUNK_SIZE = 512  # Samples per classification chunk


def load_wav(filename):
    """Load a WAV file and return mono 16-bit PCM samples at native sample rate."""
    with wave.open(filename, 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()

        if sample_width != 2:
            print(f"Error: Only 16-bit WAV files supported (got {sample_width*8}-bit)")
            sys.exit(1)

        raw_data = wf.readframes(n_frames)

    # Convert to numpy array
    samples = np.frombuffer(raw_data, dtype=np.int16)

    # Convert to mono if stereo
    if n_channels == 2:
        samples = samples[::2]  # Take every other sample (left channel)

    return samples, sample_rate


def compute_log_mel_spectrogram(samples, sample_rate):
    """Compute log-mel spectrogram from audio samples."""
    # Apply Hanning window
    window = np.hanning(len(samples))
    windowed = samples.astype(np.float32) / 32768.0 * window

    # Zero-pad to FFT size
    if len(windowed) < FFT_SIZE:
        windowed = np.pad(windowed, (0, FFT_SIZE - len(windowed)))

    # Compute FFT
    fft_result = np.fft.rfft(windowed, n=FFT_SIZE)
    power_spectrum = np.abs(fft_result) ** 2

    # Compute mel filterbank
    low_mel = 2595 * np.log10(1 + MEL_LOW_FREQ / 700.0)
    high_mel = 2595 * np.log10(1 + MEL_HIGH_FREQ / 700.0)
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

    # Apply filterbank
    mel_spec = np.dot(filterbank, power_spectrum)

    # Log-mel spectrogram
    log_mel = np.log(mel_spec + 1e-10)

    return log_mel


def classify_file(filename, model_path, threshold=0.5):
    """Classify a WAV file using the wildlife CNN model."""
    # Load audio
    samples, sample_rate = load_wav(filename)
    print(f"Loaded: {filename}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {len(samples)/sample_rate:.1f}s")
    print(f"  Samples: {len(samples)}")

    # Load model
    if HAS_TFLITE:
        interpreter = tflite.Interpreter(model_path=model_path)
    else:
        interpreter = tf.lite.Interpreter(model_path=model_path)

    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Process audio in chunks
    n_chunks = len(samples) // CHUNK_SIZE
    print(f"  Processing {n_chunks} chunks...")

    detections = []

    for i in range(n_chunks):
        chunk = samples[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]

        # Compute features
        log_mel = compute_log_mel_spectrogram(chunk, sample_rate)

        # Normalize
        log_mel = (log_mel - np.mean(log_mel)) / (np.std(log_mel) + 1e-10)

        # Run inference
        input_data = np.expand_dims(log_mel, axis=0).astype(np.float32)
        if input_details[0]['dtype'] == np.int8:
            # Quantize input
            input_scale, input_zero_point = input_details[0]['quantization']
            input_data = (input_data / input_scale + input_zero_point).astype(np.int8)

        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])

        # Get prediction
        if output_details[0]['dtype'] == np.int8:
            output_scale, output_zero_point = output_details[0]['quantization']
            output = (output.astype(np.float32) - output_zero_point) * output_scale

        class_idx = np.argmax(output)
        confidence = output[class_idx]

        # Only report non-WIND detections above threshold
        if class_idx != 6 and confidence > threshold:  # 6 = WIND
            time_s = i * CHUNK_SIZE / sample_rate
            detections.append({
                'time': time_s,
                'class': CLASS_NAMES[class_idx],
                'class_idx': class_idx,
                'confidence': float(confidence),
            })

    # Print results
    print(f"\n=== Classification Results ===")
    print(f"File: {filename}")
    print(f"Detections: {len(detections)}\n")

    if detections:
        # Count by class
        class_counts = {}
        for d in detections:
            cls = d['class']
            class_counts[cls] = class_counts.get(cls, 0) + 1

        print("Species Summary:")
        for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
            print(f"  {cls}: {count} detections")

        print("\nDetailed Detections:")
        for d in detections:
            print(f"  [{d['time']:.2f}s] {d['class']} ({d['confidence']:.0%})")
    else:
        print("No wildlife detections above threshold.")

    return detections


def main():
    parser = argparse.ArgumentParser(
        description="Classify wildlife sounds in a WAV recording"
    )
    parser.add_argument("--input", required=True, help="Path to WAV file")
    parser.add_argument("--model", default="wildlife_classify.tflite",
                       help="Path to TFLite model file")
    parser.add_argument("--threshold", type=float, default=0.5,
                       help="Minimum confidence threshold (0.0-1.0)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    classify_file(args.input, args.model, args.threshold)


if __name__ == "__main__":
    main()