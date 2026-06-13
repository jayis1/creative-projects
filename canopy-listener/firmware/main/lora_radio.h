/*
 * lora_radio.h — SX1262 LoRa transceiver interface
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "wildlife_classify.h"
#include <stdint.h>
#include <stdbool.h>

/* Detection structure for LoRa transmission */
typedef struct {
    int64_t timestamp;        /* Unix timestamp (UTC) */
    double latitude;          /* Degrees (-90 to 90) */
    double longitude;         /* Degrees (-180 to 180) */
    wildlife_class_t species; /* Detection class */
    float confidence;         /* 0.0 - 1.0 */
    float temp;               /* Temperature °C */
    float humidity;           /* Humidity %RH */
    float battery_v;          /* Battery voltage */
} detection_t;

/* Initialize SX1262 LoRa radio */
int lora_radio_init(void);

/* Send detection packet via LoRa */
int lora_radio_send_detection(const detection_t *det);

/* Put LoRa radio to sleep (lowest power) */
void lora_radio_sleep(void);

/* Wake LoRa radio from sleep */
void lora_radio_wake(void);