/*
 * wildlife_classify.h — CNN-based wildlife sound classification
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>

/* Wildlife detection classes */
typedef enum {
    BIRD_CHIP = 0,     /* Small bird calls (chickadee, wren) */
    BIRD_SONG,          /* Complex bird song (thrush, robin) */
    FROG_CALL,          /* Frog/toad vocalization */
    BAT_ECHO,           /* Bat echolocation (ultrasonic, 96kHz mode) */
    INSECT_BUZZ,        /* Cicada, cricket, mosquito */
    RAIN,               /* Rainfall on vegetation */
    WIND,               /* Wind noise (to exclude) */
    ANTHROPOGENIC,      /* Vehicle, machinery, speech */
    WILDLIFE_CLASS_MAX
} wildlife_class_t;

#define WILDLIFE_CHUNK_SIZE  512   /* Samples per classification chunk */

/* Initialize wildlife classifier (load model from flash) */
int wildlife_classify_init(void);

/* Classify a chunk of mono 16-bit PCM audio
 * @param samples: pointer to 16-bit PCM samples
 * @param num_samples: number of samples (should be WILDLIFE_CHUNK_SIZE)
 * @return detected wildlife class
 */
wildlife_class_t wildlife_classify(const int16_t *samples, int num_samples);

/* Get confidence (0.0-1.0) for last classification */
float wildlife_classify_get_confidence(void);

/* Get human-readable name for a class */
const char *wildlife_class_name(wildlife_class_t cls);