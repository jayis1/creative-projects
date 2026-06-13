/*
 * led_status.h — WS2812B NeoPixel status feedback
 */

#pragma once

#include "sensor_manager.h"

/* Initialize GPIO15 for WS2812B data */
esp_err_t led_status_init(void);

/* Show environment class as LED color pattern */
void led_status_show(env_class_t cls);

/* Show error pattern (fast red blink) */
void led_status_error(void);