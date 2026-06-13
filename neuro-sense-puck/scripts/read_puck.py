#!/usr/bin/env python3
"""
read_puck.py — Read Neuro Sense Puck data over BLE

Usage:
    python3 read_puck.py --mac AA:BB:CC:DD:EE:FF
"""

import asyncio
import argparse
from bleak import BleakClient

SERVICE_UUID = "0000ffa0-0000-1000-8000-00805f9b34fb"
CHAR_UUIDS = {
    "env_class":  "0000ffa1-0000-1000-8000-00805f9b34fb",
    "voc_index":  "0000ffa2-0000-1000-8000-00805f9b34fb",
    "pm25":       "0000ffa3-0000-1000-8000-00805f9b34fb",
    "temp":       "0000ffa4-0000-1000-8000-00805f9b34fb",
    "humidity":   "0000ffa5-0000-1000-8000-00805f9b34fb",
    "lux":        "0000ffa6-0000-1000-8000-00805f9b34fb",
    "dba":        "0000ffa7-0000-1000-8000-00805f9b34fb",
    "activity":   "0000ffa8-0000-1000-8000-00805f9b34fb",
    "device_info":"0000ffa9-0000-1000-8000-00805f9b34fb",
}

CLASS_NAMES = [
    "FRESH_OUTDOORS", "STUFFY_OFFICE", "ACTIVE_COMMUTE", "QUIET_HOME",
    "GYM_WORKOUT", "SLEEP_READY", "LOUD_STREET", "RAIN_OUTDOORS",
    "SUNNY_PARK", "CROWDED_INDOOR", "COOL_BASEMENT", "HUMID_KITCHEN",
    "WINDY_ROOFTOP", "SMOKY_AREA", "SILENT_NIGHT", "UNKNOWN"
]

ACTIVITY_NAMES = ["still", "walking", "running"]

import struct

async def read_puck(mac_address):
    async with BleakClient(mac_address) as client:
        print(f"Connected to {mac_address}")
        
        # Read all characteristics
        env_class = await client.read_gatt_char(CHAR_UUIDS["env_class"])
        voc = await client.read_gatt_char(CHAR_UUIDS["voc_index"])
        pm25 = await client.read_gatt_char(CHAR_UUIDS["pm25"])
        temp = await client.read_gatt_char(CHAR_UUIDS["temp"])
        hum = await client.read_gatt_char(CHAR_UUIDS["humidity"])
        lux = await client.read_gatt_char(CHAR_UUIDS["lux"])
        dba = await client.read_gatt_char(CHAR_UUIDS["dba"])
        act = await client.read_gatt_char(CHAR_UUIDS["activity"])
        info = await client.read_gatt_char(CHAR_UUIDS["device_info"])
        
        cls_idx = env_class[0] if env_class else 15
        voc_val = struct.unpack(">H", voc)[0] if voc else 0
        pm25_val = struct.unpack("<f", pm25)[0] if pm25 else 0
        temp_val = struct.unpack("<f", temp)[0] if temp else 0
        hum_val = struct.unpack("<f", hum)[0] if hum else 0
        lux_val = struct.unpack("<f", lux)[0] if lux else 0
        dba_val = struct.unpack("<f", dba)[0] if dba else 0
        act_idx = act[0] if act else 0
        
        print(f"\n--- Neuro Sense Puck ---")
        print(f"Device:    {info.decode() if info else 'N/A'}")
        print(f"Class:     {CLASS_NAMES[cls_idx]}")
        print(f"VOC:       {voc_val}")
        print(f"PM2.5:     {pm25_val:.1f} µg/m³")
        print(f"Temp:      {temp_val:.1f} °C")
        print(f"Humidity:  {hum_val:.1f} %RH")
        print(f"Light:     {lux_val:.0f} lux")
        print(f"Sound:     {dba_val:.0f} dBA")
        print(f"Activity:  {ACTIVITY_NAMES[act_idx]}")

def main():
    parser = argparse.ArgumentParser(description="Read Neuro Sense Puck over BLE")
    parser.add_argument("--mac", required=True, help="Puck MAC address (AA:BB:CC:DD:EE:FF)")
    args = parser.parse_args()
    
    asyncio.run(read_puck(args.mac))

if __name__ == "__main__":
    main()