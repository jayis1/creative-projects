/*
 * ble_service.h — BLE 5.0 GATT server for Neuro Sense Puck
 */

#pragma once

#include "sensor_manager.h"

/* Service and characteristic UUIDs */
#define NEURO_SENSE_SERVICE_UUID      0xFFA0
#define CHAR_ENV_CLASS_UUID          0xFFA1
#define CHAR_VOC_INDEX_UUID          0xFFA2
#define CHAR_PM25_UUID               0xFFA3
#define CHAR_TEMPERATURE_UUID        0xFFA4
#define CHAR_HUMIDITY_UUID           0xFFA5
#define CHAR_LIGHT_LUX_UUID          0xFFA6
#define CHAR_SOUND_DBA_UUID          0xFFA7
#define CHAR_ACTIVITY_UUID           0xFFA8
#define CHAR_DEVICE_INFO_UUID        0xFFA9

/* Initialize BLE stack and register GATT service */
esp_err_t ble_service_init(void);

/* Update all GATT characteristic values + advertising payload */
esp_err_t ble_service_update(env_class_t cls, const sensor_data_t *data);