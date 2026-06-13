/*
 * audio_capture.h — I2S stereo capture for dual ICS-43434 MEMS microphones
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"

/* Initialize I2S audio capture with PIO-driven BCLK/LRCLK
 * @param sample_rate: 48000 (normal) or 96000 (bat mode)
 * @return ESP_OK on success
 */
int audio_capture_init(uint32_t sample_rate);

/* Start recording audio into buffer (non-blocking)
 * @param buffer: destination for mono 16-bit PCM samples
 * @param max_samples: buffer capacity in samples
 * @param sample_rate: sample rate for this recording
 * @return number of samples to be captured, 0 on error
 */
uint32_t audio_capture_record(int16_t *buffer, uint32_t max_samples, uint32_t sample_rate);

/* Wait for audio capture to complete (blocking) */
void audio_capture_wait(void);

/* Check if capture is in progress */
bool audio_capture_is_recording(void);

/* Get current sample rate */
uint32_t audio_capture_get_sample_rate(void);

/* Deinitialize and release resources */
void audio_capture_deinit(void);