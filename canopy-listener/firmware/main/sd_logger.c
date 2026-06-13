/*
 * sd_logger.c — SD card logging for detections and WAV files
 *
 * SPI1 interface (GP14-17) for microSD card communication.
 * Writes detections.csv and audio WAV files.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "sd_logger.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"
#include "ff.h"          /* FatFs */
#include "diskio.h"      /* FatFs disk I/O */
#include <string.h>
#include <stdio.h>

static const char TAG[] = "SD_LOGGER";

/* SPI1 pins for SD card */
#define SD_SPI      spi1
#define SD_CLK      14
#define SD_MISO     15
#define SD_MOSI     16
#define SD_CS       17

#define WAV_HEADER_SIZE  44
#define MAX_FILENAME_LEN  64

static bool initialized = false;
static FATFS fs;
static bool mounted = false;

/* WAV file header builder */
static void build_wav_header(uint8_t *header, uint32_t num_samples,
                              uint32_t sample_rate, uint16_t num_channels)
{
    uint32_t data_size = num_samples * num_channels * 2;  /* 16-bit */
    uint32_t file_size = WAV_HEADER_SIZE + data_size - 8;

    /* RIFF header */
    header[0] = 'R'; header[1] = 'I'; header[2] = 'F'; header[3] = 'F';
    header[4] = (file_size) & 0xFF;
    header[5] = (file_size >> 8) & 0xFF;
    header[6] = (file_size >> 16) & 0xFF;
    header[7] = (file_size >> 24) & 0xFF;
    header[8] = 'W'; header[9] = 'A'; header[10] = 'V'; header[11] = 'E';

    /* fmt chunk */
    header[12] = 'f'; header[13] = 'm'; header[14] = 't'; header[15] = ' ';
    header[16] = 16; header[17] = 0; header[18] = 0; header[19] = 0;  /* chunk size */
    header[20] = 1; header[21] = 0;  /* PCM format */
    header[22] = num_channels & 0xFF; header[23] = (num_channels >> 8) & 0xFF;
    header[24] = (sample_rate) & 0xFF;
    header[25] = (sample_rate >> 8) & 0xFF;
    header[26] = (sample_rate >> 16) & 0xFF;
    header[27] = (sample_rate >> 24) & 0xFF;
    uint32_t byte_rate = sample_rate * num_channels * 2;
    header[28] = (byte_rate) & 0xFF;
    header[29] = (byte_rate >> 8) & 0xFF;
    header[30] = (byte_rate >> 16) & 0xFF;
    header[31] = (byte_rate >> 24) & 0xFF;
    header[32] = (num_channels * 2) & 0xFF; header[33] = 0;  /* block align */
    header[34] = 16; header[35] = 0;  /* bits per sample */

    /* data chunk */
    header[36] = 'd'; header[37] = 'a'; header[38] = 't'; header[39] = 'a';
    header[40] = (data_size) & 0xFF;
    header[41] = (data_size >> 8) & 0xFF;
    header[42] = (data_size >> 16) & 0xFF;
    header[43] = (data_size >> 24) & 0xFF;
}

/*
 * Initialize SD card and mount FAT filesystem
 */
int sd_logger_init(void)
{
    if (initialized) return 0;

    /* Initialize SPI1 at 25MHz for SD card */
    spi_init(SD_SPI, 25000000);

    gpio_set_function(SD_CLK, GPIO_FUNC_SPI);
    gpio_set_function(SD_MISO, GPIO_FUNC_SPI);
    gpio_set_function(SD_MOSI, GPIO_FUNC_SPI);

    gpio_init(SD_CS);
    gpio_set_dir(SD_CS, GPIO_OUT);
    gpio_put(SD_CS, 1);  /* CS inactive */

    /* Mount filesystem */
    FRESULT res = f_mount(&fs, "", 1);
    if (res != FR_OK) {
        printf("[SD_LOGGER] Mount failed: %d\r\n", res);
        return -1;
    }

    /* Create directories */
    f_mkdir("audio");
    f_mkdir("diagnostics");

    /* Write boot log */
    FIL boot_log;
    res = f_open(&boot_log, "diagnostics/boot_log.txt", FA_WRITE | FA_CREATE_ALWAYS);
    if (res == FR_OK) {
        const char *msg = "Canopy Listener v1.0 - Boot log\r\nTimestamp: N/A\r\n";
        f_write(&boot_log, msg, strlen(msg), NULL);
        f_close(&boot_log);
    }

    mounted = true;
    initialized = true;
    printf("[SD_LOGGER] Initialized and mounted\r\n");
    return 0;
}

/*
 * Log a detection event to detections.csv
 */
int sd_logger_log_detection(const detection_t *det)
{
    if (!initialized || !mounted || det == NULL) return -1;

    FIL file;
    FRESULT res;

    /* Check if file exists (to write header) */
    bool file_exists = (f_stat("detections.csv", NULL) == FR_OK);

    res = f_open(&file, "detections.csv", FA_WRITE | FA_OPEN_APPEND);
    if (res != FR_OK) {
        printf("[SD_LOGGER] Failed to open detections.csv: %d\r\n", res);
        return -1;
    }

    /* Write header if new file */
    if (!file_exists) {
        const char *header = "timestamp,latitude,longitude,class,confidence,temp_c,humidity_pct,battery_v\r\n";
        f_write(&file, header, strlen(header), NULL);
    }

    /* Write detection row */
    char line[256];
    int len = snprintf(line, sizeof(line),
        "%lld,%.6f,%.6f,%s,%.2f,%.1f,%.1f,%.2f\r\n",
        (long long)det->timestamp,
        det->latitude,
        det->longitude,
        wildlife_class_name(det->species),
        det->confidence,
        det->temp,
        det->humidity,
        det->battery_v
    );

    UINT written;
    f_write(&file, line, len, &written);
    f_close(&file);

    printf("[SD_LOGGER] Logged: %s (%.0f%%)\r\n",
           wildlife_class_name(det->species), det->confidence * 100);

    return 0;
}

/*
 * Save a WAV file containing audio samples
 */
int sd_logger_save_wav(const char *filename, const int16_t *samples,
                        int num_samples, uint32_t sample_rate)
{
    if (!initialized || !mounted || filename == NULL || samples == NULL) return -1;

    char path[MAX_FILENAME_LEN];
    snprintf(path, sizeof(path), "%s", filename);

    FIL file;
    FRESULT res = f_open(&file, path, FA_WRITE | FA_CREATE_ALWAYS);
    if (res != FR_OK) {
        printf("[SD_LOGGER] Failed to create WAV file: %d\r\n", res);
        return -1;
    }

    /* Build and write WAV header */
    uint8_t header[WAV_HEADER_SIZE];
    build_wav_header(header, num_samples, sample_rate, 1);  /* Mono */

    UINT written;
    f_write(&file, header, WAV_HEADER_SIZE, &written);

    /* Write audio samples */
    f_write(&file, samples, num_samples * sizeof(int16_t), &written);

    f_close(&file);

    printf("[SD_LOGGER] Saved %s (%d samples, %d Hz)\r\n",
           filename, num_samples, sample_rate);

    return 0;
}

/*
 * Unmount SD card (call before power off)
 */
void sd_logger_unmount(void)
{
    if (!initialized || !mounted) return;

    f_mount(NULL, "", 0);
    mounted = false;
    printf("[SD_LOGGER] Unmounted\r\n");
}