/*
 * Neuro Sense Puck — Main Entry Point
 * ESP32-C6 wearable multi-modal environment sensor
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "esp_sleep.h"
#include "esp_log.h"

#include "sensor_manager.h"
#include "inference_engine.h"
#include "ble_service.h"
#include "wifi_uplink.h"
#include "power_manager.h"
#include "led_status.h"

static const char *TAG = "NEURO_PUCK";

/* Environment class names for logging */
static const char *env_class_names[ENV_CLASS_MAX] = {
    "FRESH_OUTDOORS",    "STUFFY_OFFICE",    "ACTIVE_COMMUTE",  "QUIET_HOME",
    "GYM_WORKOUT",       "SLEEP_READY",      "LOUD_STREET",     "RAIN_OUTDOORS",
    "SUNNY_PARK",        "CROWDED_INDOOR",   "COOL_BASEMENT",   "HUMID_KITCHEN",
    "WINDY_ROOFTOP",     "SMOKY_AREA",       "SILENT_NIGHT",    "UNKNOWN"
};

void app_main(void)
{
    ESP_LOGI(TAG, "=== Neuro Sense Puck v1.0 ===");
    ESP_LOGI(TAG, "Initializing...");

    /* Initialize NVS for BLE bonding and WiFi credentials */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize subsystems */
    sensor_manager_init();
    inference_engine_init();
    ble_service_init();
    power_manager_init();
    led_status_init();

    /* WiFi uplink is optional — only connects if credentials stored */
    wifi_uplink_init();

    ESP_LOGI(TAG, "All subsystems initialized. Entering main loop.");

    sensor_data_t sensor_data;
    env_class_t env_class;
    uint32_t loop_count = 0;

    while (true) {
        /* Step 1: Read all sensors */
        esp_err_t err = sensor_manager_read_all(&sensor_data);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Sensor read failed: %s", esp_err_to_name(err));
            led_status_error();
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        /* Step 2: Run ML inference */
        env_class = inference_engine_classify(&sensor_data);

        /* Step 3: Update BLE advertisements and GATT values */
        ble_service_update(env_class, &sensor_data);

        /* Step 4: LED status feedback */
        led_status_show(env_class);

        /* Step 5: Periodic WiFi uplink (every 30 loops = ~30s) */
        if (loop_count % 30 == 0 && wifi_uplink_is_connected()) {
            wifi_uplink_push(&sensor_data, env_class);
        }

        /* Step 6: Log current state */
        ESP_LOGI(TAG, "[%lu] Class: %-16s | VOC:%u PM2.5:%.1f T:%.1f H:%.1f Lux:%.0lf dB:%.0lf Act:%d",
                 loop_count,
                 env_class_names[env_class],
                 sensor_data.voc_index,
                 sensor_data.pm2_5,
                 sensor_data.temperature,
                 sensor_data.humidity,
                 sensor_data.lux,
                 sensor_data.sound_dba,
                 sensor_data.activity);

        loop_count++;

        /* Step 7: Deep sleep until next cycle (1 second) */
        power_manager_sleep_ms(1000);
    }
}