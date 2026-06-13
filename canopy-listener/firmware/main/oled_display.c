/*
 * oled_display.c — SSD1306 128x64 OLED display driver
 *
 * I2C0 interface (GP18=SDA, GP19=SCL) at 400kHz.
 * Shows species count, battery, storage, and GNSS status.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "oled_display.h"
#include "hardware/i2c.h"
#include "pico/stdlib.h"
#include <string.h>
#include <stdio.h>

static const char TAG[] = "OLED";

#define I2C_PORT        i2c0
#define SSD1306_ADDR     0x3C

/* SSD1306 commands */
#define SSD1306_CMD_DISPLAY_OFF          0xAE
#define SSD1306_CMD_DISPLAY_ON           0xAF
#define SSD1306_CMD_SET_DISPLAY_CLK_DIV  0xD5
#define SSD1306_CMD_SET_MUX_RATIO        0xA8
#define SSD1306_CMD_SET_DISPLAY_OFFSET   0xD3
#define SSD1306_CMD_SET_START_LINE       0x40
#define SSD1306_CMD_SET_CHARGE_PUMP      0x8D
#define SSD1306_CMD_SET_MEMORY_MODE      0x20
#define SSD1306_CMD_SEG_REMAP            0xA1
#define SSD1306_CMD_COM_SCAN_DEC          0xC8
#define SSD1306_CMD_SET_COM_PINS         0xDA
#define SSD1306_CMD_SET_CONTRAST         0x81
#define SSD1306_CMD_SET_PRECHARGE        0xD9
#define SSD1306_CMD_SET_VCOMH            0xDB
#define SSD1306_CMD_SET_ENTIRE_ON        0xA5
#define SSD1306_CMD_SET_NORMAL_DISPLAY   0xA6
#define SSD1306_CMD_SET_COL_ADDR         0x21
#define SSD1306_CMD_SET_PAGE_ADDR        0x22

/* Display buffer: 128x64 pixels = 1024 bytes (1 bit per pixel, 8 pages) */
static uint8_t display_buffer[128 * 8];  /* 128 columns × 8 pages */
static bool initialized = false;

/* Latest detection for display */
static detection_t latest_detection;
static bool has_detection = false;

/* 5x7 ASCII font (printable chars 0x20-0x7E) */
static const uint8_t font5x7[][5] = {
    /* Space (0x20) */ {0x00, 0x00, 0x00, 0x00, 0x00},
    /* ! */ {0x00, 0x00, 0x5F, 0x00, 0x00},
    /* " */ {0x00, 0x07, 0x00, 0x07, 0x00},
    /* # */ {0x14, 0x7F, 0x14, 0x7F, 0x14},
    /* $ */ {0x24, 0x2A, 0x7F, 0x2A, 0x12},
    /* % */ {0x23, 0x13, 0x08, 0x64, 0x62},
    /* & */ {0x36, 0x49, 0x55, 0x22, 0x50},
    /* ' */ {0x00, 0x05, 0x03, 0x00, 0x00},
    /* ( */ {0x00, 0x1C, 0x22, 0x41, 0x00},
    /* ) */ {0x00, 0x41, 0x22, 0x1C, 0x00},
    /* * */ {0x14, 0x08, 0x3E, 0x08, 0x14},
    /* + */ {0x08, 0x08, 0x3E, 0x08, 0x08},
    /* , */ {0x00, 0x50, 0x30, 0x00, 0x00},
    /* - */ {0x08, 0x08, 0x08, 0x08, 0x08},
    /* . */ {0x00, 0x60, 0x60, 0x00, 0x00},
    /* / */ {0x20, 0x10, 0x08, 0x04, 0x02},
    /* 0-9 */ {0x3E, 0x51, 0x49, 0x45, 0x3E},
              {0x00, 0x42, 0x7F, 0x40, 0x00},
              {0x42, 0x61, 0x51, 0x49, 0x46},
              {0x21, 0x41, 0x45, 0x4B, 0x31},
              {0x18, 0x14, 0x12, 0x7F, 0x10},
              {0x27, 0x45, 0x45, 0x45, 0x39},
              {0x3C, 0x4A, 0x49, 0x49, 0x30},
              {0x01, 0x71, 0x09, 0x05, 0x03},
              {0x36, 0x49, 0x49, 0x49, 0x36},
              {0x06, 0x49, 0x49, 0x29, 0x1E},
    /* : */ {0x00, 0x36, 0x36, 0x00, 0x00},
    /* ; */ {0x00, 0x56, 0x36, 0x00, 0x00},
    /* A-Z */ {0x7F, 0x49, 0x49, 0x49, 0x36},
              {0x3E, 0x41, 0x41, 0x41, 0x22},
              {0x41, 0x7F, 0x41, 0x41, 0x00},
              {0x7F, 0x49, 0x49, 0x49, 0x41},
              {0x7F, 0x09, 0x09, 0x09, 0x01},
              {0x7F, 0x49, 0x49, 0x49, 0x36},
              {0x7F, 0x09, 0x09, 0x09, 0x01},  /* Simplified */
              {0x7F, 0x49, 0x49, 0x49, 0x36},
              {0x7F, 0x01, 0x01, 0x01, 0x7F},
              {0x00, 0x41, 0x7F, 0x41, 0x00},
              {0x20, 0x40, 0x41, 0x3F, 0x01},
              {0x7F, 0x08, 0x14, 0x22, 0x41},
              {0x7F, 0x40, 0x40, 0x40, 0x40},
              {0x7F, 0x02, 0x0C, 0x02, 0x7F},
              {0x7F, 0x04, 0x08, 0x10, 0x7F},
              {0x3E, 0x41, 0x41, 0x41, 0x3E},
              {0x7F, 0x09, 0x09, 0x09, 0x06},
              {0x3E, 0x41, 0x51, 0x21, 0x5E},
              {0x7F, 0x09, 0x19, 0x29, 0x46},
              {0x46, 0x49, 0x49, 0x49, 0x31},
              {0x01, 0x01, 0x7F, 0x01, 0x01},
              {0x3F, 0x40, 0x40, 0x40, 0x3F},
              {0x1F, 0x20, 0x40, 0x20, 0x1F},
              {0x3F, 0x40, 0x38, 0x40, 0x3F},
              {0x63, 0x14, 0x08, 0x14, 0x63},
              {0x07, 0x08, 0x70, 0x08, 0x07},
              {0x61, 0x51, 0x49, 0x45, 0x43},
    /* a-z (simplified, just showing placeholder for lowercase) */
    /* Using uppercase glyphs for simplicity */
    /* For brevity, we only handle A-Z, 0-9, space, and common punctuation */
};

/* Write a command byte to SSD1306 */
static void ssd1306_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};  /* Control byte: 0x00 = command */
    i2c_write_blocking(I2C_PORT, SSD1306_ADDR, buf, 2, false);
}

/* Write display buffer to SSD1306 */
static void ssd1306_write_buffer(void)
{
    /* Set column address range */
    ssd1306_write_cmd(SSD1306_CMD_SET_COL_ADDR);
    ssd1306_write_cmd(0);    /* Start column */
    ssd1306_write_cmd(127);  /* End column */

    /* Set page address range */
    ssd1306_write_cmd(SSD1306_CMD_SET_PAGE_ADDR);
    ssd1306_write_cmd(0);    /* Start page */
    ssd1306_write_cmd(7);    /* End page */

    /* Send display data in 16-byte chunks */
    for (int i = 0; i < 128 * 8; i += 16) {
        uint8_t buf[17];
        buf[0] = 0x40;  /* Control byte: 0x40 = data */
        memcpy(&buf[1], &display_buffer[i], 16);
        i2c_write_blocking(I2C_PORT, SSD1306_ADDR, buf, 17, false);
    }
}

/* Clear display buffer */
static void display_clear(void)
{
    memset(display_buffer, 0, sizeof(display_buffer));
}

/* Draw a single character at (x, page) position */
static void display_draw_char(char c, int x, int page)
{
    if (c < 0x20 || c > 0x5A) c = ' ';  /* Only handle printable ASCII */

    int idx = c - 0x20;
    if (idx < 0 || idx >= (int)(sizeof(font5x7) / sizeof(font5x7[0]))) {
        idx = 0;  /* Default to space */
    }

    for (int col = 0; col < 5; col++) {
        if (x + col < 128) {
            display_buffer[(page * 128) + x + col] = font5x7[idx][col];
        }
    }
}

/* Draw a string starting at (x, page) position */
static void display_draw_string(const char *str, int x, int page)
{
    while (*str && x < 128) {
        display_draw_char(*str, x, page);
        x += 6;  /* 5 pixels + 1 pixel spacing */
        str++;
    }
}

/*
 * Initialize SSD1306 OLED display
 */
int oled_display_init(void)
{
    if (initialized) return 0;

    /* SSD1306 initialization sequence */
    ssd1306_write_cmd(SSD1306_CMD_DISPLAY_OFF);
    ssd1306_write_cmd(SSD1306_CMD_SET_DISPLAY_CLK_DIV);
    ssd1306_write_cmd(0x80);  /* Clock divide ratio */
    ssd1306_write_cmd(SSD1306_CMD_SET_MUX_RATIO);
    ssd1306_write_cmd(0x3F);  /* 64 rows */
    ssd1306_write_cmd(SSD1306_CMD_SET_DISPLAY_OFFSET);
    ssd1306_write_cmd(0x00);
    ssd1306_write_cmd(SSD1306_CMD_SET_START_LINE | 0x00);
    ssd1306_write_cmd(SSD1306_CMD_SET_CHARGE_PUMP);
    ssd1306_write_cmd(0x14);  /* Enable charge pump */
    ssd1306_write_cmd(SSD1306_CMD_SET_MEMORY_MODE);
    ssd1306_write_cmd(0x00);  /* Horizontal addressing */
    ssd1306_write_cmd(SSD1306_CMD_SEG_REMAP);     /* Column address 127 mapped to SEG0 */
    ssd1306_write_cmd(SSD1306_CMD_COM_SCAN_DEC);   /* Remapped mode */
    ssd1306_write_cmd(SSD1306_CMD_SET_COM_PINS);
    ssd1306_write_cmd(0x12);
    ssd1306_write_cmd(SSD1306_CMD_SET_CONTRAST);
    ssd1306_write_cmd(0xCF);  /* Contrast */
    ssd1306_write_cmd(SSD1306_CMD_SET_PRECHARGE);
    ssd1306_write_cmd(0xF1);
    ssd1306_write_cmd(SSD1306_CMD_SET_VCOMH);
    ssd1306_write_cmd(0x40);
    ssd1306_write_cmd(SSD1306_CMD_SET_ENTIRE_ON);   /* Output follows RAM content */
    ssd1306_write_cmd(SSD1306_CMD_SET_NORMAL_DISPLAY);
    ssd1306_write_cmd(SSD1306_CMD_DISPLAY_ON);

    display_clear();
    ssd1306_write_buffer();

    printf("[OLED] SSD1306 initialized (128x64)\r\n");
    initialized = true;
    return 0;
}

/*
 * Set the latest detection for display
 */
void oled_display_set_detection(const detection_t *det)
{
    if (det) {
        latest_detection = *det;
        has_detection = true;
    }
}

/*
 * Update display with current status information
 * Shows: species, confidence, battery, GPS fix, time
 */
void oled_display_update(void)
{
    if (!initialized) return;

    display_clear();

    /* Line 0: Title */
    display_draw_string("CANOPY LISTENER", 0, 0);

    /* Line 1: Latest detection */
    if (has_detection) {
        char line[22];
        snprintf(line, sizeof(line), "%s %d%%",
                 wildlife_class_name(latest_detection.species),
                 (int)(latest_detection.confidence * 100));
        display_draw_string(line, 0, 1);
    } else {
        display_draw_string("No detection", 0, 1);
    }

    /* Line 2: GPS coordinates */
    if (latest_detection.latitude != 0 || latest_detection.longitude != 0) {
        char line[22];
        snprintf(line, sizeof(line), "%.4f %.4f",
                 latest_detection.latitude, latest_detection.longitude);
        display_draw_string(line, 0, 2);
    }

    /* Line 3: Battery and temperature */
    char status[22];
    snprintf(status, sizeof(status), "Bat %.1fV T %.0fC",
             latest_detection.battery_v, latest_detection.temp);
    display_draw_string(status, 0, 3);

    /* Line 4-5: Humidity and pressure info */
    char env_line[22];
    snprintf(env_line, sizeof(env_line), "RH %.0f%%",
             latest_detection.humidity);
    display_draw_string(env_line, 0, 4);

    /* Line 7: Status bar */
    display_draw_string("CANOPY v1.0", 0, 7);

    ssd1306_write_buffer();
}

/*
 * Turn off OLED display to save power
 */
void oled_display_off(void)
{
    if (!initialized) return;
    ssd1306_write_cmd(SSD1306_CMD_DISPLAY_OFF);
}

/*
 * Turn on OLED display
 */
void oled_display_on(void)
{
    if (!initialized) return;
    ssd1306_write_cmd(SSD1306_CMD_DISPLAY_ON);
}