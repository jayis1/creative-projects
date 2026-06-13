/*
 * sensor_manager.h — Unified sensor reading interface
 */

#pragma once

#include "esp_err.h"

/* 16 environment classes matching TFLite model output */
typedef enum {
    ENV_CLASS_FRESH_OUTDOORS = 0,
    ENV_CLASS_STUFFY_OFFICE,
    ENV_CLASS_ACTIVE_COMMUTE,
    ENV_CLASS_QUIET_HOME,
    ENV_CLASS_GYM_WORKOUT,
    ENV_CLASS_SLEEP_READY,
    ENV_CLASS_LOUD_STREET,
    ENV_CLASS_RAIN_OUTDOORS,
    ENV_CLASS_SUNNY_PARK,
    ENV_CLASS_CROWDED_INDOOR,
    ENV_CLASS_COOL_BASEMENT,
    ENV_CLASS_HUMID_KITCHEN,
    ENV_CLASS_WINDY_ROOFTOP,
    ENV_CLASS_SMOKY_AREA,
    ENV_CLASS_SILENT_NIGHT,
    ENV_CLASS_UNKNOWN,
    ENV_CLASS_MAX
} env_class_t;

/* Activity classification from IMU */
typedef enum {
    ACTIVITY_STILL = 0,
    ACTIVITY_WALKING,
    ACTIVITY_RUNNING
} activity_t;

/* Aggregated sensor reading */
typedef struct {
    /* BME680 */
    float temperature;       /* °C */
    float humidity;          /* %RH */
    float pressure;          /* hPa */
    uint16_t voc_index;      /* 0-500 (BME680 gas) */

    /* SGP40 */
    uint16_t voc_index_sgp;  /* 0-500 (SGP40 dedicated) */

    /* SPS30 */
    float pm1_0;             /* µg/m³ */
    float pm2_5;             /* µg/m³ */
    float pm4_0;             /* µg/m³ */
    float pm10;              /* µg/m³ */

    /* ICM-42688-P */
    activity_t activity;     /* still/walking/running */
    float accel_mag;         /* m/s² magnitude */

    /* TSL2591 */
    float lux;               /* lux */
    float color_temp;        /* Kelvin (approx) */
    bool flicker_detected;   /* 100/120Hz flicker */

    /* MAX9814 via ADC */
    float sound_dba;         /* approximate dBA */
    uint8_t spectral_class;  /* 0=silence,1=speech,2=music,3=noise */

    /* Timestamp */
    int64_t timestamp_ms;    /* epoch ms */
} sensor_data_t;

/* Initialize I2C bus and all sensors */
esp_err_t sensor_manager_init(void);

/* Read all sensors into unified struct */
esp_err_t sensor_manager_read_all(sensor_data_t *data);

/* Self-test: verify all sensors respond on I2C */
esp_err_t sensor_manager_self_test(void);