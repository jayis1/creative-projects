/*
 * env_sensor.c — BME280 temperature/humidity/pressure sensor driver
 *
 * I2C0 interface (GP18=SDA, GP19=SCL) at 400kHz.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "env_sensor.h"
#include "hardware/i2c.h"
#include "pico/stdlib.h"
#include <stdio.h>
#include <math.h>

static const char TAG[] = "ENV_SENSOR";

#define I2C_PORT        i2c0
#define I2C_SDA_PIN     18
#define I2C_SCL_PIN     19
#define I2C_FREQ        400000

#define BME280_ADDR     0x76

/* BME280 register addresses */
#define BME280_REG_ID       0xD0
#define BME280_REG_RESET    0xE0
#define BME280_REG_CTRL_HUM 0xF2
#define BME280_REG_CTRL_MEAS 0xF4
#define BME280_REG_CONFIG   0xF5
#define BME280_REG_STATUS   0xF3
#define BME280_REG_DATA     0xF7  /* Pressure, temp, humidity start */

/* BME280 compensation parameters (read from chip) */
typedef struct {
    uint16_t dig_T1;
    int16_t dig_T2, dig_T3;
    uint16_t dig_P1;
    int16_t dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
    uint16_t dig_H1, dig_H3;
    int16_t dig_H2, dig_H4, dig_H5, dig_H6;
    int32_t t_fine;
} bme280_calib_t;

static bme280_calib_t calib;
static bool initialized = false;

/* I2C helpers */
static esp_err_t i2c_write_reg(uint8_t dev_addr, uint8_t reg, uint8_t value)
{
    uint8_t buf[2] = {reg, value};
    int ret = i2c_write_blocking(I2C_PORT, dev_addr, buf, 2, false);
    return (ret == 2) ? 0 : -1;
}

static esp_err_t i2c_read_regs(uint8_t dev_addr, uint8_t reg, uint8_t *data, size_t len)
{
    int ret = i2c_write_blocking(I2C_PORT, dev_addr, &reg, 1, true);
    if (ret != 1) return -1;
    ret = i2c_read_blocking(I2C_PORT, dev_addr, data, len, false);
    return (ret == (int)len) ? 0 : -1;
}

/* Read calibration data from BME280 */
static void read_calib_data(void)
{
    uint8_t buf[24];

    /* Temperature and pressure calibration */
    i2c_read_regs(BME280_ADDR, 0x88, buf, 24);
    calib.dig_T1 = (buf[1] << 8) | buf[0];
    calib.dig_T2 = (buf[3] << 8) | buf[2];
    calib.dig_T3 = (buf[5] << 8) | buf[4];
    calib.dig_P1 = (buf[7] << 8) | buf[6];
    calib.dig_P2 = (buf[9] << 8) | buf[8];
    calib.dig_P3 = (buf[11] << 8) | buf[10];
    calib.dig_P4 = (buf[13] << 8) | buf[12];
    calib.dig_P5 = (buf[15] << 8) | buf[14];
    calib.dig_P6 = (buf[17] << 8) | buf[16];
    calib.dig_P7 = (buf[19] << 8) | buf[18];
    calib.dig_P8 = (buf[21] << 8) | buf[20];
    calib.dig_P9 = (buf[23] << 8) | buf[22];

    /* Humidity calibration */
    uint8_t h1;
    i2c_read_regs(BME280_ADDR, 0xA1, &h1, 1);
    calib.dig_H1 = h1;

    uint8_t h_buf[7];
    i2c_read_regs(BME280_ADDR, 0xE1, h_buf, 7);
    calib.dig_H2 = (h_buf[1] << 8) | h_buf[0];
    calib.dig_H3 = h_buf[2];
    calib.dig_H4 = (h_buf[3] << 4) | (h_buf[4] & 0x0F);
    calib.dig_H5 = (h_buf[5] << 4) | (h_buf[4] >> 4);
    calib.dig_H6 = h_buf[6];
}

/* BME280 temperature compensation */
static float compensate_temp(int32_t adc_t)
{
    float var1 = ((float)adc_t / 16384.0f - (float)calib.dig_T1 / 1024.0f) * (float)calib.dig_T2;
    float var2 = (((float)adc_t / 131072.0f - (float)calib.dig_T1 / 8192.0f) *
                  ((float)adc_t / 131072.0f - (float)calib.dig_T1 / 8192.0f)) *
                  (float)calib.dig_T3;
    calib.t_fine = (int32_t)(var1 + var2);
    return (var1 + var2) / 5120.0f;
}

/* BME280 pressure compensation */
static float compensate_press(int32_t adc_p)
{
    float var1 = ((float)calib.t_fine / 2.0f) - 64000.0f;
    float var2 = var1 * var1 * ((float)calib.dig_P6) / 32768.0f;
    var2 = var2 + var1 * ((float)calib.dig_P5) * 2.0f;
    var2 = (var2 / 4.0f) + ((float)calib.dig_P4) * 65536.0f;
    var1 = (((float)calib.dig_P3) * var1 * var1 / 524288.0f + ((float)calib.dig_P2) * var1) / 524288.0f;
    var1 = (1.0f + var1 / 32768.0f) * (float)calib.dig_P1;
    if (var1 == 0.0f) return 0.0f;  /* Avoid divide by zero */

    float p = 1048576.0f - (float)adc_p;
    p = (p - (var2 / 4096.0f)) * 6250.0f / var1;
    var1 = ((float)calib.dig_P9) * p * p / 2147483648.0f;
    var2 = p * ((float)calib.dig_P8) / 32768.0f;
    p = p + (var1 + var2 + ((float)calib.dig_P7)) / 16.0f;
    return p / 100.0f;  /* Convert to hPa */
}

/* BME280 humidity compensation */
static float compensate_hum(int32_t adc_h)
{
    float v_x1 = (float)calib.t_fine - 76800.0f;
    v_x1 = ((float)adc_h - ((float)calib.dig_H4 * 64.0f + (float)calib.dig_H5 / 16384.0f * v_x1)) *
           ((float)calib.dig_H2 / 65536.0f * (1.0f + (float)calib.dig_H6 / 67108864.0f * v_x1 *
            (1.0f + (float)calib.dig_H3 / 67108864.0f * v_x1)));
    v_x1 = v_x1 * (1.0f - (float)calib.dig_H1 * v_x1 / 524288.0f);
    if (v_x1 > 100.0f) v_x1 = 100.0f;
    if (v_x1 < 0.0f) v_x1 = 0.0f;
    return v_x1;
}

/*
 * Initialize BME280 environmental sensor
 */
int env_sensor_init(void)
{
    if (initialized) return 0;

    /* Initialize I2C0 at 400kHz */
    i2c_init(I2C_PORT, I2C_FREQ);
    gpio_set_function(I2C_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA_PIN);
    gpio_pull_up(I2C_SCL_PIN);

    /* Check BME280 chip ID */
    uint8_t chip_id;
    i2c_read_regs(BME280_ADDR, BME280_REG_ID, &chip_id, 1);
    if (chip_id != 0x60) {
        printf("[ENV_SENSOR] BME280 not found (ID=0x%02X, expected 0x60)\r\n", chip_id);
        return -1;
    }
    printf("[ENV_SENSOR] BME280 found (ID=0x%02X)\r\n", chip_id);

    /* Soft reset */
    i2c_write_reg(BME280_ADDR, BME280_REG_RESET, 0xB6);
    sleep_ms(2);

    /* Read calibration data */
    read_calib_data();

    /* Configure: oversampling x1 for all, normal mode */
    i2c_write_reg(BME280_ADDR, BME280_REG_CTRL_HUM, 0x01);    /* Humidity oversampling x1 */
    i2c_write_reg(BME280_REG_CTRL_MEAS, 0x27);                  /* Temp+Press oversampling x1, normal mode */
    i2c_write_reg(BME280_REG_CONFIG, 0xA0);                     /* Standby 1000ms, filter off */

    sleep_ms(100);  /* Wait for first measurement */

    initialized = true;
    printf("[ENV_SENSOR] BME280 initialized\r\n");
    return 0;
}

/*
 * Read temperature, humidity, and pressure from BME280
 */
int env_sensor_read(env_data_t *data)
{
    if (!initialized || data == NULL) return -1;

    uint8_t raw[8];
    esp_err_t ret = i2c_read_regs(BME280_ADDR, BME280_REG_DATA, raw, 8);
    if (ret != 0) {
        printf("[ENV_SENSOR] Read failed\r\n");
        return -1;
    }

    /* Parse raw data: pressure(3) + temp(3) + humidity(2) */
    int32_t adc_p = (raw[0] << 16) | (raw[1] << 8) | raw[2];
    adc_p >>= 4;
    int32_t adc_t = (raw[3] << 16) | (raw[4] << 8) | raw[5];
    adc_t >>= 4;
    int32_t adc_h = (raw[6] << 8) | raw[7];

    /* Compensate */
    data->temperature = compensate_temp(adc_t);
    data->pressure = compensate_press(adc_p);
    data->humidity = compensate_hum(adc_h);

    return 0;
}