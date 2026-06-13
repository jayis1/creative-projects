#!/usr/bin/env python3
"""
gateway_receiver.py — Receive LoRa detection packets from Canopy Listener devices

Receives 18-byte LoRa packets via serial (connected to SX1262 dev board),
parses detection data, and outputs JSON to stdout or MQTT.

Usage:
    python3 gateway_receiver.py --port /dev/ttyUSB0 --freq 868 [--mqtt]
"""

import argparse
import struct
import serial
import json
import sys
import time
from datetime import datetime

# Detection class names
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

# Packet constants
SYNC_BYTE = 0xAA
PACKET_LENGTH = 18  # Total packet size in bytes

# CRC16-CCITT
def crc16_ccitt(data):
    """Calculate CRC16-CCITT checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def parse_packet(raw_bytes):
    """Parse a LoRa detection packet.

    Format: [0xAA][LEN][UTC(4)][LAT(4)][LON(4)][CLASS(1)][CONF(1)][CRC(2)]
    """
    if len(raw_bytes) < PACKET_LENGTH:
        return None

    # Check sync byte
    if raw_bytes[0] != SYNC_BYTE:
        return None

    # Check length
    if raw_bytes[1] != PACKET_LENGTH:
        return None

    # Verify CRC (over bytes 2-15)
    payload = raw_bytes[2:16]
    received_crc = struct.unpack('>H', raw_bytes[16:18])[0]
    calculated_crc = crc16_ccitt(payload)

    crc_valid = (received_crc == calculated_crc)

    # Parse fields
    timestamp = struct.unpack('>I', raw_bytes[2:6])[0]
    latitude_raw = struct.unpack('>i', raw_bytes[6:10])[0]
    longitude_raw = struct.unpack('>i', raw_bytes[10:14])[0]
    class_idx = raw_bytes[14]
    confidence = raw_bytes[15]

    # Convert fixed-point to float
    latitude = latitude_raw / 1e7
    longitude = longitude_raw / 1e7
    confidence_pct = confidence / 100.0

    # Convert timestamp
    dt = datetime.utcfromtimestamp(timestamp)

    # Validate class index
    if class_idx >= len(CLASS_NAMES):
        class_name = f"UNKNOWN({class_idx})"
    else:
        class_name = CLASS_NAMES[class_idx]

    return {
        'timestamp': timestamp,
        'datetime': dt.isoformat() + 'Z',
        'latitude': latitude,
        'longitude': longitude,
        'class': class_name,
        'class_idx': class_idx,
        'confidence': confidence_pct,
        'confidence_pct': confidence,
        'crc_valid': crc_valid,
    }


def receive_loop(port, baud, freq, mqtt_enabled=False):
    """Main receive loop: read serial data and parse LoRa packets."""
    print(f"Canopy Listener Gateway Receiver")
    print(f"Port: {port}, Baud: {baud}, Frequency: {freq} MHz")
    print(f"Waiting for packets...\n")

    ser = serial.Serial(port, baud, timeout=1.0)
    buffer = bytearray()
    packet_count = 0

    # MQTT setup
    mqtt_client = None
    if mqtt_enabled:
        try:
            import paho.mqtt.client as mqtt
            mqtt_client = mqtt.Client()
            mqtt_client.connect("broker.hivemq.com", 1883)
            mqtt_client.loop_start()
            print("MQTT connected to broker.hivemq.com")
        except ImportError:
            print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")
            mqtt_enabled = False
        except Exception as e:
            print(f"Warning: MQTT connection failed: {e}")
            mqtt_enabled = False

    try:
        while True:
            # Read available bytes
            data = ser.read(64)
            if data:
                buffer.extend(data)

            # Search for sync byte in buffer
            while len(buffer) >= PACKET_LENGTH:
                sync_idx = buffer.find(SYNC_BYTE)
                if sync_idx < 0:
                    buffer.clear()
                    break

                # Remove bytes before sync
                if sync_idx > 0:
                    del buffer[:sync_idx]

                # Check if we have enough bytes for a complete packet
                if len(buffer) < PACKET_LENGTH:
                    break

                # Extract and parse packet
                packet_bytes = bytes(buffer[:PACKET_LENGTH])
                result = parse_packet(packet_bytes)

                if result:
                    packet_count += 1

                    # Print detection
                    print(f"--- Detection #{packet_count} ---")
                    print(f"  Time:       {result['datetime']}")
                    print(f"  Species:    {result['class']}")
                    print(f"  Confidence: {result['confidence_pct']}%")
                    print(f"  Location:   {result['latitude']:.6f}, {result['longitude']:.6f}")
                    print(f"  CRC Valid:  {result['crc_valid']}")
                    print()

                    # Publish to MQTT if enabled
                    if mqtt_enabled and mqtt_client:
                        topic = f"canopy/listener/{result['class'].lower()}"
                        mqtt_client.publish(topic, json.dumps(result))

                    # Remove processed packet
                    del buffer[:PACKET_LENGTH]
                else:
                    # Not a valid packet, skip sync byte and continue
                    del buffer[0]

    except KeyboardInterrupt:
        print(f"\nStopped. Received {packet_count} packets.")
    finally:
        ser.close()
        if mqtt_client and mqtt_enabled:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Receive LoRa detection packets from Canopy Listener devices"
    )
    parser.add_argument("--port", default="/dev/ttyUSB0",
                       help="Serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200,
                       help="Serial baud rate (default: 115200)")
    parser.add_argument("--freq", type=int, default=868,
                       help="LoRa frequency in MHz: 868 (EU) or 915 (US)")
    parser.add_argument("--mqtt", action="store_true",
                       help="Publish detections to MQTT broker")
    args = parser.parse_args()

    receive_loop(args.port, args.baud, args.freq, args.mqtt)


if __name__ == "__main__":
    main()