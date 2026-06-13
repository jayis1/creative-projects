/*
 * gps_module.h — L86-Q GNSS module driver
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Initialize GPS module (UART0 @ 9600 baud) */
int gps_module_init(void);

/* Power on GPS and start acquiring fix */
void gps_module_power_on(void);

/* Power off GPS to conserve battery */
void gps_module_power_off(void);

/* Check if GPS has a valid position fix */
bool gps_module_has_fix(void);

/* Get UTC time (simplified — seconds since midnight) */
int64_t gps_module_get_utc(void);

/* Get latitude in decimal degrees */
double gps_module_get_latitude(void);

/* Get longitude in decimal degrees */
double gps_module_get_longitude(void);

/* Get number of satellites in view */
int gps_module_get_satellites(void);

/* Get HDOP (horizontal dilution of precision) */
float gps_module_get_hdop(void);

/* Manage GPS power cycling (call periodically from Core 1) */
void gps_module_manage_power(void);