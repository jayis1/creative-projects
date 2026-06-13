/*
 * power_manager.h — Deep sleep and duty cycling control
 */

#pragma once

#include "esp_err.h"

/* Initialize power management (configure wake sources) */
esp_err_t power_manager_init(void);

/* Enter deep sleep for specified milliseconds */
void power_manager_sleep_ms(uint32_t ms);

/* Get battery voltage (0.0 if on USB) */
float power_manager_get_battery_voltage(void);

/* Check if charging */
bool power_manager_is_charging(void);