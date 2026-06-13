/*
 * inference_engine.h — TFLite Micro environment classification
 */

#pragma once

#include "sensor_manager.h"

/* Initialize TFLite Micro interpreter and load model from flash */
esp_err_t inference_engine_init(void);

/* Run 16-class environment classification on sensor data */
env_class_t inference_engine_classify(const sensor_data_t *data);

/* Get confidence score for last classification (0.0-1.0) */
float inference_engine_get_confidence(void);