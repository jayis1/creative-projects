/*
 * power_manager.h — Power management interface
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Charge status enum */
typedef enum {
    CHARGE_NO_POWER = 0,  /* No USB or solar power */
    CHARGE_CHARGING,       /* Battery is charging */
    CHARGE_COMPLETE,       /* Charge complete */
    CHARGE_FAULT           /* Charge fault */
} charge_status_t;

/* Initialize power management */
int power_manager_init(void);

/* Read battery voltage (V) via ADC */
float power_manager_read_battery_voltage(void);

/* Read solar panel voltage (V) via ADC */
float power_manager_read_solar_voltage(void);

/* Check if USB/solar power is good */
bool power_manager_is_power_good(void);

/* Get charge status */
charge_status_t power_manager_get_charge_status(void);

/* Enter deep sleep for specified milliseconds */
void power_manager_deep_sleep_ms(uint32_t ms);

/* Get estimated battery percentage from voltage */
uint8_t power_manager_get_battery_percent(float voltage);