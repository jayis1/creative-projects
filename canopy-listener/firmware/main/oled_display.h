/*
 * oled_display.h — SSD1306 128x64 OLED display interface
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "lora_radio.h"
#include <stdint.h>

/* Initialize SSD1306 OLED via I2C */
int oled_display_init(void);

/* Set the latest detection for display */
void oled_display_set_detection(const detection_t *det);

/* Update display with current status info */
void oled_display_update(void);

/* Turn off display (power saving) */
void oled_display_off(void);

/* Turn on display */
void oled_display_on(void);