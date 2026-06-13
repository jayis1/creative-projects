#!/usr/bin/env python3
"""
train_model.py — Train environment classification model for Neuro Sense Puck

Usage:
    python3 train_model.py --data training_data.csv --output model/env_classify.tflite
"""

import argparse
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

# Model architecture: 4-layer FC
# Input(12) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(16, ReLU) → Dense(16, Softmax)

CLASS_NAMES = [
    "FRESH_OUTDOORS", "STUFFY_OFFICE", "ACTIVE_COMMUTE", "QUIET_HOME",
    "GYM_WORKOUT", "SLEEP_READY", "LOUD_STREET", "RAIN_OUTDOORS",
    "SUNNY_PARK", "CROWDED_INDOOR", "COOL_BASEMENT", "HUMID_KITCHEN",
    "WINDY_ROOFTOP", "SMOKY_AREA", "SILENT_NIGHT", "UNKNOWN"
]

def build_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(12,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(16, activation='softmax')
    ])
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

def load_data(csv_path):
    """Load CSV with columns: class,temp,hum,voc_bme,voc_sgp,pm25,pm10,lux,color_temp,flicker,dba,accel,activity"""
    data = np.genfromtxt(csv_path, delimiter=',', skip_header=1)
    X = data[:, 1:]   # features
    y = data[:, 0]    # class labels
    return X, y.astype(int)

def train(args):
    print(f"Loading data from {args.data}...")
    X, y = load_data(args.data)
    print(f"Dataset: {X.shape[0]} samples, {X.shape[1]} features, {len(CLASS_NAMES)} classes")

    # Normalize features
    scaler = MinMaxScaler()
    X_normalized = scaler.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized, y, test_size=0.2, random_state=42, stratify=y
    )

    # Build and train
    model = build_model()
    model.summary()

    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=50,
        batch_size=64,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3)
        ]
    )

    # Evaluate
    test_loss, test_acc = model.evaluate(X_test, y_test)
    print(f"\nTest accuracy: {test_acc:.4f}")

    # Convert to TFLite with INT8 quantization
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
    
    output_path = args.output
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"\nTFLite INT8 model saved to {output_path}")
    print(f"Model size: {len(tflite_model) / 1024:.1f} KB")

def main():
    parser = argparse.ArgumentParser(description="Train Neuro Sense Puck environment classifier")
    parser.add_argument("--data", required=True, help="Path to training CSV")
    parser.add_argument("--output", default="env_classify.tflite", help="Output TFLite model path")
    args = parser.parse_args()
    
    train(args)

if __name__ == "__main__":
    main()