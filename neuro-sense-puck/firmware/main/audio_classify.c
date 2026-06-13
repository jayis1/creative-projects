/*
 * audio_classify.c — Sound level and spectral classification
 *
 * ADC samples from MAX9814 → dBA + rough spectral class
 * Production version would use ESP-DSP FFT for spectral features.
 */

#include "audio_classify.h"
#include <math.h>
#include <string.h>

float audio_compute_dba(const int16_t *samples, int count)
{
    if (count == 0) return 20.0f;

    double sum_sq = 0.0;
    for (int i = 0; i < count; i++) {
        double s = (samples[i] - 2048) / 2048.0;
        sum_sq += s * s;
    }
    float rms = (float)sqrt(sum_sq / count);
    if (rms < 1e-6f) rms = 1e-6f;

    /* Approximate dBA (MAX9814 has A-weighting filter built in) */
    float dba = 20.0f * log10f(rms / 0.00002f);
    if (dba < 20.0f) dba = 20.0f;
    if (dba > 120.0f) dba = 120.0f;
    return dba;
}

sound_class_t audio_classify(const int16_t *samples, int count, int sample_rate)
{
    float dba = audio_compute_dba(samples, count);

    /* Simple threshold-based classification:
     * - Very quiet (<35 dBA) → silence
     * - Moderate (35-65 dBA) → likely speech or music
     * - Loud (>65 dBA) → noise
     * 
     * Production version uses FFT spectral features:
     * - Speech: strong 300-3000Hz, harmonics
     * - Music: broader spectrum, rhythmic patterns
     * - Noise: flat spectrum, no structure
     */
    if (dba < 35.0f) return SOUND_SILENCE;
    if (dba < 65.0f) return SOUND_SPEECH;   /* placeholder */
    return SOUND_NOISE;
}