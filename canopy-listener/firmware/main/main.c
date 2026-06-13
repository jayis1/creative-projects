/*
 * main.c — Canopy Listener main entry point
 * RP2040 dual-core acoustic biodiversity monitor
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "pico/sleep.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"

#include "audio_capture.h"
#include "wildlife_classify.h"
#include "lora_radio.h"
#include "gps_module.h"
#include "sd_logger.h"
#include "env_sensor.h"
#include "oled_display.h"
#include "power_manager.h"

/* Detection queue between cores */
#define DETECTION_QUEUE_SIZE 32
static detection_t detection_queue[DETECTION_QUEUE_SIZE];
static volatile uint32_t dq_head = 0;
static volatile uint32_t dq_tail = 0;

/* Audio buffer: 5s stereo at 48kHz = 480,000 bytes (too large for stack) */
#define AUDIO_BUF_SAMPLES (48000 * 5)  /* 5 seconds, mono */
static int16_t audio_buffer[AUDIO_BUF_SAMPLES];

/* Configuration */
#define SAMPLE_RATE      48000
#define CAPTURE_SECONDS  5
#define DETECT_CONFIDENCE_THRESHOLD 0.7f
#define DEEP_SLEEP_MS   60000  /* 60 seconds between captures */

static const char *class_names[WILDLIFE_CLASS_MAX] = {
    "BIRD_CHIP", "BIRD_SONG", "FROG_CALL", "BAT_ECHO",
    "INSECT_BUZZ", "RAIN", "WIND", "ANTHROPOGENIC"
};

/*
 * Core 1 entry: LoRa radio, OLED display, GPS management
 */
void core1_entry(void)
{
    printf("[CORE1] Starting LoRa + Display + GPS\r\n");

    lora_radio_init();
    oled_display_init();
    gps_module_init();

    uint32_t last_gps_fix_ms = 0;
    uint32_t last_display_update_ms = 0;
    bool gps_powered = false;

    while (true) {
        uint32_t now = to_ms_since_boot(get_absolute_time());

        /* Check for detection events from Core 0 */
        while (dq_tail != dq_head) {
            detection_t det = detection_queue[dq_tail % DETECTION_QUEUE_SIZE];
            dq_tail++;

            /* Send detection via LoRa */
            lora_radio_send_detection(&det);

            /* Update display with latest detection */
            oled_display_set_detection(&det);
        }

        /* Manage GPS power: enable for 30s every 5 minutes */
        if (!gps_powered && (now - last_gps_fix_ms > 300000)) {
            gps_module_power_on();
            gps_powered = true;
            last_gps_fix_ms = now;
        }
        if (gps_powered && (now - last_gps_fix_ms > 30000)) {
            if (gps_module_has_fix()) {
                last_gps_fix_ms = now;  /* Reset timer after successful fix */
            }
            gps_module_power_off();
            gps_powered = false;
        }

        /* Update OLED every 5 seconds */
        if (now - last_display_update_ms > 5000) {
            oled_display_update();
            last_display_update_ms = now;
        }

        sleep_ms(100);
    }
}

/*
 * Main entry point — Core 0: Audio capture + ML inference + logging
 */
int main(void)
{
    stdio_usb_init();
    board_init();

    printf("=== Canopy Listener v1.0 ===\r\n");
    printf("RP2040 dual-core acoustic biodiversity monitor\r\n");

    /* Initialize subsystems on Core 0 */
    audio_capture_init(SAMPLE_RATE);
    wildlife_classify_init();
    env_sensor_init();
    sd_logger_init();
    power_manager_init();

    printf("[CORE0] All subsystems initialized\r\n");

    /* Launch Core 1 */
    multicore_launch_core1(core1_entry);

    uint32_t capture_count = 0;

    while (true) {
        capture_count++;
        printf("[CORE0] Capture cycle #%lu\r\n", capture_count);

        /* Read environmental context */
        env_data_t env;
        env_sensor_read(&env);

        /* Check battery voltage */
        float battery_v = power_manager_read_battery_voltage();
        if (battery_v < 3.3f) {
            printf("[CORE0] Low battery (%.2fV), entering deep sleep\r\n", battery_v);
            power_manager_deep_sleep_ms(300000);  /* 5 minutes */
            continue;
        }

        /* Capture audio */
        uint32_t samples_captured = audio_capture_record(
            audio_buffer, AUDIO_BUF_SAMPLES, SAMPLE_RATE);

        if (samples_captured == 0) {
            printf("[CORE0] Audio capture failed\r\n");
            sleep_ms(1000);
            continue;
        }

        /* Classify each 512-sample chunk */
        int num_chunks = samples_captured / WILDLIFE_CHUNK_SIZE;
        wildlife_class_t best_class = WIND_CLASS;  /* default: wind/nothing */
        float best_confidence = 0.0f;
        int best_chunk = -1;

        for (int i = 0; i < num_chunks; i++) {
            wildlife_class_t cls = wildlife_classify(
                &audio_buffer[i * WILDLIFE_CHUNK_SIZE], WILDLIFE_CHUNK_SIZE);
            float conf = wildlife_classify_get_confidence();

            /* Track the highest-confidence non-wind detection */
            if (cls != WIND_CLASS && conf > best_confidence) {
                best_class = cls;
                best_confidence = conf;
                best_chunk = i;
            }
        }

        /* If we have a confident detection, log and transmit */
        if (best_class != WIND_CLASS && best_confidence > DETECT_CONFIDENCE_THRESHOLD) {
            detection_t det = {
                .timestamp = gps_module_get_utc(),
                .latitude = gps_module_get_latitude(),
                .longitude = gps_module_get_longitude(),
                .species = best_class,
                .confidence = best_confidence,
                .temp = env.temperature,
                .humidity = env.humidity,
                .battery_v = battery_v
            };

            /* Log to SD card */
            sd_logger_log_detection(&det);

            /* Save WAV of the best detection chunk */
            char filename[64];
            snprintf(filename, sizeof(filename),
                     "audio/%010lu_%s_%d.wav",
                     (uint32_t)det.timestamp,
                     class_names[best_class],
                     (int)(best_confidence * 100));
            sd_logger_save_wav(filename,
                &audio_buffer[best_chunk * WILDLIFE_CHUNK_SIZE],
                WILDLIFE_CHUNK_SIZE, SAMPLE_RATE);

            printf("[CORE0] Detection: %s (%.0f%%) at chunk %d\r\n",
                   class_names[best_class], best_confidence * 100, best_chunk);

            /* Push to Core 1 for LoRa transmission */
            uint32_t next_head = (dq_head + 1) % DETECTION_QUEUE_SIZE;
            if (next_head != dq_tail) {
                detection_queue[dq_head % DETECTION_QUEUE_SIZE] = det;
                dq_head = next_head;
            }
        } else {
            printf("[CORE0] No significant detection (best: %s %.0f%%)\r\n",
                   class_names[best_class], best_confidence * 100);
        }

        /* Log environmental snapshot */
        printf("[CORE0] Env: %.1f°C, %.1f%%RH, %.0fhPa, Bat: %.2fV\r\n",
               env.temperature, env.humidity, env.pressure, battery_v);

        /* Deep sleep until next cycle */
        power_manager_deep_sleep_ms(DEEP_SLEEP_MS);
    }

    return 0;
}

/*
 * Board-level initialization
 */
void board_init(void)
{
    /* Configure GPIO pins */

    /* I2C0: GP18=SDA, GP19=SCL (for BME280 + SSD1306) */
    gpio_set_function(18, GPIO_FUNC_I2C);
    gpio_set_function(19, GPIO_FUNC_I2C);
    gpio_pull_up(18);
    gpio_pull_up(19);

    /* SPI0: GP2-5 (for SX1262 LoRa) */
    gpio_set_function(2, GPIO_FUNC_SPI);
    gpio_set_function(3, GPIO_FUNC_SPI);
    gpio_set_function(4, GPIO_FUNC_SPI);
    gpio_init(5);  /* CS manual */
    gpio_set_dir(5, GPIO_OUT);
    gpio_put(5, 1);  /* CS inactive */

    /* SPI1: GP14-17 (for microSD) */
    gpio_set_function(14, GPIO_FUNC_SPI);
    gpio_set_function(15, GPIO_FUNC_SPI);
    gpio_set_function(16, GPIO_FUNC_SPI);
    gpio_init(17);  /* CS manual */
    gpio_set_dir(17, GPIO_OUT);
    gpio_put(17, 1);  /* CS inactive */

    /* UART0: GP0=TX, GP1=RX (for GPS) */
    gpio_set_function(0, GPIO_FUNC_UART);
    gpio_set_function(1, GPIO_FUNC_UART);

    /* SX1262 control pins */
    gpio_init(6);   /* DIO1 interrupt */
    gpio_set_dir(6, GPIO_IN);
    gpio_pull_down(6);

    gpio_init(7);   /* RESET */
    gpio_set_dir(7, GPIO_OUT);
    gpio_put(7, 1);  /* Not in reset */

    gpio_init(11);  /* BUSY */
    gpio_set_dir(11, GPIO_IN);
    gpio_pull_down(11);

    /* GPS control */
    gpio_init(12);  /* PPS input */
    gpio_set_dir(12, GPIO_IN);
    gpio_pull_down(12);

    gpio_init(20);  /* FORCE_ON */
    gpio_set_dir(20, GPIO_OUT);
    gpio_put(20, 0);  /* GPS off initially */

    /* WS2812B LED */
    gpio_init(13);
    gpio_set_dir(13, GPIO_OUT);

    /* User button */
    gpio_init(21);
    gpio_set_dir(21, GPIO_IN);
    gpio_pull_up(21);

    /* Power enable */
    gpio_init(22);
    gpio_set_dir(22, GPIO_OUT);
    gpio_put(22, 1);  /* Enable power rail */

    /* Charge status inputs */
    gpio_init(23);  /* PG */
    gpio_set_dir(23, GPIO_IN);
    gpio_pull_up(23);

    gpio_init(24);  /* STAT2 */
    gpio_set_dir(24, GPIO_IN);
    gpio_pull_up(24);

    /* ADC for battery/solar voltage sensing */
    adc_init();
    adc_gpio_init(25);  /* Battery sense */
    adc_gpio_init(26);  /* Solar sense */

    /* Mic L/R select */
    gpio_init(27);
    gpio_set_dir(27, GPIO_OUT);
    gpio_put(27, 0);  /* Left channel selected */

    /* Boot button */
    gpio_init(28);
    gpio_set_dir(28, GPIO_IN);
    gpio_pull_up(28);

    printf("[BOARD] GPIO initialized\r\n");
}