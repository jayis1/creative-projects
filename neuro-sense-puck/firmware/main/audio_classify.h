/*
 * audio_classify.h — Sound classification from ADC samples
 */

#pragma once

#include <stdint.h>

/* Sound spectral classes */
typedef enum {
    SOUND_SILENCE = 0,
    SOUND_SPEECH,
    SOUND_MUSIC,
    SOUND_NOISE
} sound_class_t;

/* Compute approximate dBA from ADC samples */
float audio_compute_dba(const int16_t *samples, int count);

/* Classify sound into spectral class (requires FFT in production) */
sound_class_t audio_classify(const int16_t *samples, int count, int sample_rate);