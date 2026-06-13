/*
 * gps_module.c — L86-Q GNSS module driver
 *
 * UART0 interface (GP0=TX, GP1=RX) for NMEA parsing.
 * Manages GPS power cycling for battery conservation.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "gps_module.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static const char TAG[] = "GPS";

#define UART_PORT       uart0
#define UART_BAUD       9600
#define GPS_TX_PIN      0
#define GPS_RX_PIN      1
#define GPS_FORCE_ON    20
#define GPS_PPS_PIN     12

#define NMEA_BUF_SIZE   256

static bool initialized = false;
static bool has_fix = false;
static bool gps_powered = false;

/* Parsed GPS data */
static double gps_latitude = 0.0;
static double gps_longitude = 0.0;
static int64_t gps_utc_time = 0;
static int gps_satellites = 0;
static float gps_hdop = 99.9f;

/* NMEA sentence buffer */
static char nmea_buf[NMEA_BUF_SIZE];
static int nmea_idx = 0;

/* Parse a float from NMEA field */
static float parse_float(const char *field)
{
    if (field == NULL || field[0] == '\0') return 0.0f;
    return strtof(field, NULL);
}

/* Parse an integer from NMEA field */
static int parse_int(const char *field)
{
    if (field == NULL || field[0] == '\0') return 0;
    return atoi(field);
}

/* Parse latitude from NMEA format (DDMM.MMMM) */
static double parse_lat(const char *lat_str, const char *dir)
{
    if (lat_str == NULL || lat_str[0] == '\0') return 0.0;
    double raw = strtod(lat_str, NULL);
    int degrees = (int)(raw / 100.0);
    double minutes = raw - (degrees * 100.0);
    double result = degrees + minutes / 60.0;
    if (dir && dir[0] == 'S') result = -result;
    return result;
}

/* Parse longitude from NMEA format (DDDMM.MMMM) */
static double parse_lon(const char *lon_str, const char *dir)
{
    if (lon_str == NULL || lon_str[0] == '\0') return 0.0;
    double raw = strtod(lon_str, NULL);
    int degrees = (int)(raw / 100.0);
    double minutes = raw - (degrees * 100.0);
    double result = degrees + minutes / 60.0;
    if (dir && dir[0] == 'W') result = -result;
    return result;
}

/* Parse NMEA GGA sentence */
static void parse_gga(const char *sentence)
{
    /* $GPGGA,time,lat,N/S,lon,E/W,quality,numSV,HDOP,alt,altUnit,... */
    char buf[NMEA_BUF_SIZE];
    strncpy(buf, sentence, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    char *fields[15] = {0};
    char *token = strtok(buf, ",");
    int i = 0;
    while (token != NULL && i < 15) {
        fields[i++] = token;
        token = strtok(NULL, ",");
    }

    if (i < 7) return;

    /* Field 1: UTC time (HHMMSS) */
    if (fields[1] && strlen(fields[1]) >= 6) {
        int hour = (fields[1][0] - '0') * 10 + (fields[1][1] - '0');
        int min  = (fields[1][2] - '0') * 10 + (fields[1][3] - '0');
        int sec  = (fields[1][4] - '0') * 10 + (fields[1][5] - '0');
        /* Store as seconds since midnight (simplified) */
        gps_utc_time = (int64_t)hour * 3600 + (int64_t)min * 60 + sec;
    }

    /* Fields 2-3: Latitude */
    gps_latitude = parse_lat(fields[2], fields[3]);

    /* Fields 4-5: Longitude */
    gps_longitude = parse_lon(fields[4], fields[5]);

    /* Field 6: Fix quality (0=invalid, 1=GPS, 2=DGPS) */
    int quality = parse_int(fields[6]);
    has_fix = (quality >= 1);

    /* Field 7: Number of satellites */
    gps_satellites = parse_int(fields[7]);

    /* Field 8: HDOP */
    gps_hdop = parse_float(fields[8]);
}

/* Process incoming NMEA data from UART */
static void gps_process_data(void)
{
    while (uart_is_readable(UART_PORT)) {
        char c = uart_getc(UART_PORT);

        if (c == '$') {
            /* Start of new NMEA sentence */
            nmea_idx = 0;
            nmea_buf[nmea_idx++] = c;
        } else if (c == '\n' || c == '\r') {
            /* End of sentence */
            if (nmea_idx > 0) {
                nmea_buf[nmea_idx] = '\0';

                /* Check for GGA sentence */
                if (strncmp(nmea_buf, "$GPGGA", 6) == 0 ||
                    strncmp(nmea_buf, "$GNGGA", 6) == 0) {
                    parse_gga(nmea_buf);
                }
            }
            nmea_idx = 0;
        } else if (nmea_idx < NMEA_BUF_SIZE - 1) {
            nmea_buf[nmea_idx++] = c;
        }
    }
}

/*
 * Initialize GPS module
 */
int gps_module_init(void)
{
    if (initialized) return 0;

    /* Initialize UART0 at 9600 baud */
    uart_init(UART_PORT, UART_BAUD);

    gpio_set_function(GPS_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(GPS_RX_PIN, GPIO_FUNC_UART);

    /* Configure FORCE_ON pin */
    gpio_init(GPS_FORCE_ON);
    gpio_set_dir(GPS_FORCE_ON, GPIO_OUT);
    gpio_put(GPS_FORCE_ON, 0);  /* GPS in backup mode initially */

    /* Configure PPS input */
    gpio_init(GPS_PPS_PIN);
    gpio_set_dir(GPS_PPS_PIN, GPIO_IN);
    gpio_pull_down(GPS_PPS_PIN);

    gps_powered = false;
    has_fix = false;

    printf("[GPS] L86-Q initialized (UART0 @ %d baud)\r\n", UART_BAUD);
    initialized = true;
    return 0;
}

/*
 * Power on GPS and start acquiring fix
 */
void gps_module_power_on(void)
{
    if (!initialized) return;

    gpio_put(GPS_FORCE_ON, 1);
    gps_powered = true;
    has_fix = false;

    printf("[GPS] Powered on, acquiring fix...\r\n");
}

/*
 * Power off GPS to conserve battery
 */
void gps_module_power_off(void)
{
    if (!initialized) return;

    gpio_put(GPS_FORCE_ON, 0);
    gps_powered = false;

    printf("[GPS] Powered off\r\n");
}

/*
 * Check if GPS has a valid position fix
 */
bool gps_module_has_fix(void)
{
    if (!initialized || !gps_powered) return false;

    /* Process any pending NMEA data */
    gps_process_data();

    return has_fix;
}

/*
 * Get UTC time as Unix timestamp (simplified — seconds since midnight)
 * In production, use full date parsing from $GPRMC
 */
int64_t gps_module_get_utc(void)
{
    if (!initialized) return 0;

    /* Process pending data */
    gps_process_data();

    return gps_utc_time;
}

/*
 * Get latitude in decimal degrees
 */
double gps_module_get_latitude(void)
{
    if (!initialized) return 0.0;
    return gps_latitude;
}

/*
 * Get longitude in decimal degrees
 */
double gps_module_get_longitude(void)
{
    if (!initialized) return 0.0;
    return gps_longitude;
}

/*
 * Get number of satellites in view
 */
int gps_module_get_satellites(void)
{
    return gps_satellites;
}

/*
 * Get HDOP (horizontal dilution of precision)
 */
float gps_module_get_hdop(void)
{
    return gps_hdop;
}

/*
 * Manage GPS power: cycle on/off for battery conservation
 * Enable for 30s every 5 minutes to update position
 */
void gps_module_manage_power(void)
{
    static uint32_t last_on_ms = 0;
    static bool cycling = false;
    uint32_t now = to_ms_since_boot(get_absolute_time());

    if (!gps_powered && !cycling) {
        /* Time to turn on? */
        if (now - last_on_ms > 300000) {  /* Every 5 minutes */
            gps_module_power_on();
            cycling = true;
            last_on_ms = now;
        }
    } else if (gps_powered && cycling) {
        /* Process data while on */
        gps_process_data();

        /* Turn off after 30s or if we have a fix */
        if ((now - last_on_ms > 30000) || has_fix) {
            gps_module_power_off();
            cycling = false;
            last_on_ms = now;
        }
    }
}