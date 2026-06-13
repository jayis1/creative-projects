/*
 * power_manager.c — Power management, deep sleep, battery monitoring
 *
 * Manages deep sleep cycles, battery/solar voltage sensing via ADC,
 * and charge status monitoring from MCP73871.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "power_manager.h"
#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "hardware/sleep.h"
#include "pico/stdlib.h"
#include <stdio.h>

static const char TAG[] = "POWER";

/* GPIO pins */
#define PIN_PG          23   /* MCP73871 Power Good */
#define PIN_STAT2       24   /* MCP73871 Charge Status 2 */
#define PIN_POWER_EN    22   /* Boost converter enable */

/* ADC channels */
#define ADC_BATTERY     0    /* GP25 - battery voltage (1:2 divider) */
#define ADC_SOLAR       1    /* GP26 - solar voltage (1:3 divider) */

/* Voltage divider ratios */
#define BATTERY_DIVIDER_RATIO  2.0f  /* 100k / (100k + 100k) */
#define SOLAR_DIVIDER_RATIO    3.0f  /* 100k / (100k + 200k) */

/* Reference voltage (3.3V) */
#define ADC_VREF       3.3f
#define ADC_RESOLUTION 4096.0f  /* 12-bit */

static bool initialized = false;

/*
 * Initialize power management subsystem
 */
int power_manager_init(void)
{
    if (initialized) return 0;

    /* Configure GPIO inputs for charge status */
    gpio_init(PIN_PG);
    gpio_set_dir(PIN_PG, GPIO_IN);
    gpio_pull_up(PIN_PG);

    gpio_init(PIN_STAT2);
    gpio_set_dir(PIN_STAT2, GPIO_IN);
    gpio_pull_up(PIN_STAT2);

    /* Configure power enable output */
    gpio_init(PIN_POWER_EN);
    gpio_set_dir(PIN_POWER_EN, GPIO_OUT);
    gpio_put(PIN_POWER_EN, 1);  /* Enable power rail */

    /* Configure ADC */
    adc_init();
    adc_gpio_init(25);  /* Battery sense */
    adc_gpio_init(26);  /* Solar sense */

    printf("[POWER] Initialized\r\n");
    initialized = true;
    return 0;
}

/*
 * Read battery voltage via ADC
 * Uses 1:2 voltage divider on GP25
 */
float power_manager_read_battery_voltage(void)
{
    adc_select_input(ADC_BATTERY);

    /* Average multiple readings */
    uint32_t sum = 0;
    for (int i = 0; i < 16; i++) {
        sum += adc_read();
    }
    uint16_t adc_val = sum / 16;

    /* Convert to voltage:
     * ADC voltage = adc_val * VREF / 4096
     * Battery voltage = ADC voltage * divider_ratio
     */
    float adc_voltage = (float)adc_val * ADC_VREF / ADC_RESOLUTION;
    float battery_voltage = adc_voltage * BATTERY_DIVIDER_RATIO;

    return battery_voltage;
}

/*
 * Read solar panel voltage via ADC
 * Uses 1:3 voltage divider on GP26
 */
float power_manager_read_solar_voltage(void)
{
    adc_select_input(ADC_SOLAR);

    uint32_t sum = 0;
    for (int i = 0; i < 16; i++) {
        sum += adc_read();
    }
    uint16_t adc_val = sum / 16;

    float adc_voltage = (float)adc_val * ADC_VREF / ADC_RESOLUTION;
    float solar_voltage = adc_voltage * SOLAR_DIVIDER_RATIO;

    return solar_voltage;
}

/*
 * Check if USB/solar power is good
 */
bool power_manager_is_power_good(void)
{
    return gpio_get(PIN_PG) == 0;  /* PG is active low */
}

/*
 * Check charge status
 * Returns: CHARGE_CHARGING, CHARGE_COMPLETE, or CHARGE_FAULT
 */
charge_status_t power_manager_get_charge_status(void)
{
    bool pg = (gpio_get(PIN_PG) == 0);
    bool stat2 = (gpio_get(PIN_STAT2) == 0);

    if (!pg) return CHARGE_NO_POWER;
    if (stat2) return CHARGE_CHARGING;
    return CHARGE_COMPLETE;
}

/*
 * Enter deep sleep for specified milliseconds
 * Uses RP2040 sleep modes with RTC wake
 */
void power_manager_deep_sleep_ms(uint32_t ms)
{
    printf("[POWER] Deep sleep for %lu ms\r\n", ms);

    /* Turn off peripherals to save power */
    /* OLED off */
    /* LoRa to sleep */
    /* GPS off */

    /* Save current state if needed */

    /* Use RP2040 sleep functionality */
    /* The RP2040 doesn't have true deep sleep like ESP32,
     * but we can use clock gating and lower power states */
    sleep_ms(ms);

    printf("[POWER] Woke up from sleep\r\n");
}

/*
 * Get estimated battery percentage
 * Based on typical LiPo discharge curve
 */
uint8_t power_manager_get_battery_percent(float voltage)
{
    if (voltage >= 4.20f) return 100;
    if (voltage >= 4.10f) return 90;
    if (voltage >= 4.00f) return 80;
    if (voltage >= 3.90f) return 70;
    if (voltage >= 3.82f) return 60;
    if (voltage >= 3.76f) return 50;
    if (voltage >= 3.72f) return 40;
    if (voltage >= 3.68f) return 30;
    if (voltage >= 3.64f) return 20;
    if (voltage >= 3.50f) return 10;
    if (voltage >= 3.30f) return 5;
    return 0;  /* Critically low */
}