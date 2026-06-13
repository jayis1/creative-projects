/*
 * env_sensor.h — BME280 environmental sensor interface
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Environmental data */
typedef struct {
    float temperature;   /* °C */
    float humidity;       /* %RH */
    float pressure;       /* hPa */
} env_data_t;

/* Initialize I2C and BME280 sensor */
int env_sensor_init(void);

/* Read current temperature, humidity, and pressure */
int env_sensor_read(env_data_t *data);