/*
 * sd_logger.h — SD card logging interface
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "lora_radio.h"
#include <stdint.h>

/* Initialize SD card and mount FAT filesystem */
int sd_logger_init(void);

/* Log a detection event to detections.csv */
int sd_logger_log_detection(const detection_t *det);

/* Save a WAV file containing audio samples
 * @param filename: path relative to SD root (e.g., "audio/recording.wav")
 * @param samples: mono 16-bit PCM audio data
 * @param num_samples: number of samples
 * @param sample_rate: sample rate in Hz
 */
int sd_logger_save_wav(const char *filename, const int16_t *samples,
                        int num_samples, uint32_t sample_rate);

/* Unmount SD card (call before power off) */
void sd_logger_unmount(void);