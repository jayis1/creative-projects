/*
 * audio_capture.c — PIO-driven I2S stereo capture for ICS-43434 mics
 *
 * Uses RP2040 PIO to generate I2S BCLK/LRCLK and read data from
 * daisy-chained ICS-43434 MEMS microphones.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "audio_capture.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "hardware/clocks.h"
#include "pico/stdlib.h"
#include "pico/multicore.h"

/* PIO program for I2S clock generation (BCLK + LRCLK) */
/* This is a simplified representation; the actual PIO program is
   compiled from i2s_clock.pio and i2s_data.pio at build time */

static const char TAG[] = "AUDIO";

#define I2S_BCLK_PIN   8
#define I2S_LRCLK_PIN  9
#define I2S_DATA_PIN   10
#define MIC_LR_SELECT  27

#define DMA_CHANNEL     0
#define DMA_CHANNEL_MASK (1u << DMA_CHANNEL)

static bool initialized = false;
static volatile bool capture_complete = false;
static int dma_chan;

/* Circular DMA buffer for continuous capture */
static int16_t *active_buffer = NULL;
static uint32_t active_samples = 0;
static uint32_t active_sample_rate = 48000;

/*
 * Initialize I2S audio capture subsystem
 * Configures PIO for I2S BCLK/LRCLK generation and DMA for data capture
 */
esp_err_t audio_capture_init(uint32_t sample_rate)
{
    if (initialized) return ESP_OK;

    active_sample_rate = sample_rate;

    /* Configure mic L/R select pin */
    gpio_init(MIC_LR_SELECT);
    gpio_set_dir(MIC_LR_SELECT, GPIO_OUT);
    gpio_put(MIC_LR_SELECT, 0);  /* Left channel selected for first mic */

    /* Load I2S clock PIO program (BCLK + LRCLK generation) */
    PIO pio = pio0;
    uint offset = pio_add_program(pio, &i2s_clock_program);
    uint sm_clock = pio_claim_unused_sm(pio, true);

    /* Configure I2S clock state machine */
    pio_sm_config c = i2s_clock_program_get_default_config(offset);
    sm_config_set_out_pins(&c, I2S_BCLK_PIN, 1);
    sm_config_set_set_pins(&c, I2S_BCLK_PIN, 2);  /* BCLK + LRCLK */
    sm_config_set_clkdiv(&c, (float)clock_get_hz(clk_sys) / (sample_rate * 64));

    pio_sm_init(pio, sm_clock, offset, &c);
    pio_sm_set_enabled(pio, sm_clock, true);

    /* Load I2S data input PIO program */
    uint offset_data = pio_add_program(pio, &i2s_data_program);
    uint sm_data = pio_claim_unused_sm(pio, true);

    pio_sm_config cd = i2s_data_program_get_default_config(offset_data);
    sm_config_set_in_pins(&cd, I2S_DATA_PIN);
    sm_config_set_in_shift(&cd, false, true, 32);  /* Shift right, auto-push at 32 bits */
    sm_config_set_clkdiv(&cd, (float)clock_get_hz(clk_sys) / (sample_rate * 64));

    pio_sm_init(pio, sm_data, offset_data, &cd);
    pio_sm_set_enabled(pio, sm_data, true);

    /* Claim DMA channel for audio data transfer */
    dma_chan = dma_claim_unused_channel(true);

    printf("[AUDIO] I2S initialized at %lu Hz (BCLK=%d, LRCLK=%d, DATA=%d)\r\n",
           sample_rate, I2S_BCLK_PIN, I2S_LRCLK_PIN, I2S_DATA_PIN);

    initialized = true;
    return ESP_OK;
}

/*
 * Start recording audio into the provided buffer
 * Returns immediately; use audio_capture_wait() to block until complete
 */
uint32_t audio_capture_record(int16_t *buffer, uint32_t max_samples, uint32_t sample_rate)
{
    if (!initialized || buffer == NULL) return 0;

    active_buffer = buffer;
    active_samples = max_samples;
    active_sample_rate = sample_rate;
    capture_complete = false;

    /* Configure DMA: PIO RX FIFO → buffer */
    dma_channel_config cfg = dma_channel_get_default_config(dma_chan);
    channel_config_set_transfer_data_size(&cfg, DMA_SIZE_32);
    channel_config_set_read_increment(&cfg, false);        /* Read from fixed PIO FIFO */
    channel_config_set_write_increment(&cfg, true);          /* Write to sequential buffer */
    channel_config_set_dreq(&cfg, pio_get_dreq(pio0, sm_data, false));
    channel_config_set_chain_to(&cfg, dma_chan);             /* No chaining */

    dma_channel_configure(dma_chan, &cfg,
        buffer,                          /* Write address */
        &pio0->rxf[sm_data],             /* Read from PIO RX FIFO */
        max_samples / 2,                 /* Transfer count (32-bit = 2 samples) */
        true                             /* Start immediately */
    );

    return max_samples;
}

/*
 * Wait for audio capture to complete
 * Blocks until DMA transfer finishes
 */
void audio_capture_wait(void)
{
    if (!initialized) return;

    dma_channel_wait_for_finish_blocking(dma_chan);

    /* Convert from I2S stereo to mono by taking left channel */
    /* I2S data is 32-bit: [R16][L16] per frame */
    for (uint32_t i = 0; i < active_samples; i++) {
        /* Left channel is in lower 16 bits of each 32-bit word */
        uint32_t raw = ((uint32_t *)active_buffer)[i];
        active_buffer[i] = (int16_t)(raw & 0xFFFF);
    }

    capture_complete = true;
}

/*
 * Check if capture is still in progress
 */
bool audio_capture_is_recording(void)
{
    if (!initialized) return false;
    return !dma_channel_is_busy(dma_chan);
}

/*
 * Get the current sample rate
 */
uint32_t audio_capture_get_sample_rate(void)
{
    return active_sample_rate;
}

/*
 * Deinitialize and release resources
 */
void audio_capture_deinit(void)
{
    if (!initialized) return;

    dma_channel_abort(dma_chan);
    dma_channel_unclaim(dma_chan);

    pio_sm_set_enabled(pio0, 0, false);
    pio_sm_set_enabled(pio0, 1, false);

    initialized = false;
    printf("[AUDIO] Deinitialized\r\n");
}