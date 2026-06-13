/*
 * wifi_uplink.h — WiFi 6 MQTT push to cloud dashboard
 */

#pragma once

#include "sensor_manager.h"

/* Initialize WiFi and MQTT client (no-op if credentials not stored) */
esp_err_t wifi_uplink_init(void);

/* Check if WiFi is connected */
bool wifi_uplink_is_connected(void);

/* Push sensor data + classification to MQTT broker */
esp_err_t wifi_uplink_push(const sensor_data_t *data, env_class_t cls);