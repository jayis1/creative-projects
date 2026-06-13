/*
 * sensor_manager.c — Unified sensor reading implementation
 *
 * I2C bus: GPIO0=SDA, GPIO1=SCL, 400kHz
 * Sensors: BME680(0x77), SGP40(0x59), SPS30(0x69), ICM-42688(0x68), TSL2591(0x29)
 * Audio: MAX9814 on ADC1_CH2 (GPIO2)
 */

#include "sensor_manager.h"
#include "esp_log.h"
#include "driver/i2c.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"
#include "esp_timer.h"

static const char *TAG = "SENSOR_MGR";

#define I2C_MASTER_NUM    I2C_NUM_0
#define I2C_MASTER_SDA    0   /* GPIO0 */
#define I2C_MASTER_SCL    1   /* GPIO1 */
#define I2C_MASTER_FREQ   400000
#define I2C_TIMEOUT_MS    100

/* I2C addresses */
#define BME680_ADDR       0x77
#define SGP40_ADDR        0x59
#define SPS30_ADDR        0x69
#define ICM42688_ADDR     0x68
#define TSL2591_ADDR      0x29

/* ADC for MAX9814 audio */
#define AUDIO_ADC_UNIT    ADC_UNIT_1
#define AUDIO_ADC_CHANNEL ADC_CHANNEL_2  /* GPIO2 */
#define AUDIO_SAMPLES     256
#define AUDIO_SAMPLE_RATE 16000

static bool initialized = false;

/* ---- I2C helpers ---- */

static esp_err_t i2c_read_reg(uint8_t dev_addr, uint8_t reg, uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_READ, true);
    if (len > 1) {
        i2c_master_read(cmd, data, len - 1, I2C_MASTER_ACK);
    }
    i2c_master_read_byte(cmd, data + len - 1, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(I2C_TIMEOUT_MS));
    i2c_cmd_link_delete(cmd);
    return ret;
}

static esp_err_t i2c_write_reg(uint8_t dev_addr, uint8_t reg, const uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (dev_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_write(cmd, data, len, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(I2C_TIMEOUT_MS));
    i2c_cmd_link_delete(cmd);
    return ret;
}

/* ---- Individual sensor drivers (stub implementations) ---- */

static esp_err_t bme680_read(float *temp, float *hum, float *press, uint16_t *voc)
{
    /* In production: use Bosch BME680 driver with BSEC library */
    /* Here: register-level read stub */
    uint8_t buf[8] = {0};
    esp_err_t ret = i2c_read_reg(BME680_ADDR, 0x1D, buf, 8);
    if (ret != ESP_OK) return ret;
    /* Parse raw data and apply compensation (BSEC does this in production) */
    *temp = 22.5f;   /* placeholder compensated */
    *hum = 45.0f;
    *press = 1013.25f;
    *voc = 120;
    return ESP_OK;
}

static esp_err_t sgp40_read(uint16_t *voc_index)
{
    /* SGP40: send measure_raw command 0x260F, wait 50ms, read 3 bytes */
    uint8_t cmd[2] = {0x26, 0x0F};
    esp_err_t ret = i2c_write_reg(SGP40_ADDR, 0x00, cmd, 2);
    if (ret != ESP_OK) return ret;
    vTaskDelay(pdMS_TO_TICKS(50));
    uint8_t buf[3] = {0};
    ret = i2c_read_reg(SGP40_ADDR, 0x00, buf, 3);
    if (ret != ESP_OK) return ret;
    *voc_index = (buf[0] << 8) | buf[1];
    return ESP_OK;
}

static esp_err_t sps30_read(float *pm1, float *pm25, float *pm4, float *pm10)
{
    /* SPS30: start measurement 0x0020, read data 0x0300 */
    *pm1 = 5.2f; *pm25 = 8.1f; *pm4 = 10.3f; *pm10 = 15.0f;
    return ESP_OK;
}

static esp_err_t icm42688_read(activity_t *activity, float *accel_mag)
{
    /* Read accelerometer data registers 0x1D-0x22 */
    *activity = ACTIVITY_STILL;
    *accel_mag = 9.81f;
    return ESP_OK;
}

static esp_err_t tsl2591_read(float *lux, float *color_temp, bool *flicker)
{
    /* TSL2591: read CH0 (0x14-0x17) and CH1 (0x18-0x1B) */
    *lux = 350.0f;
    *color_temp = 4500.0f;
    *flicker = false;
    return ESP_OK;
}

static esp_err_t max9814_read(float *dba, uint8_t *spectral_class)
{
    /* Sample ADC at 16kHz for 256 samples, compute RMS and spectral features */
    uint32_t sum_sq = 0;
    for (int i = 0; i < AUDIO_SAMPLES; i++) {
        int raw = adc1_get_raw(AUDIO_ADC_CHANNEL);
        float sample = (raw - 2048) / 2048.0f;
        sum_sq += (uint32_t)(sample * sample * 65536);
    }
    float rms = sqrtf((float)sum_sq / (AUDIO_SAMPLES * 65536.0f));
    *dba = 20.0f * log10f(rms / 0.00002f);  /* approximate dBA */
    *dba = *dba < 20 ? 20 : (*dba > 120 ? 120 : *dba);
    *spectral_class = 0; /* silence — real impl uses FFT */
    return ESP_OK;
}

/* ---- Public API ---- */

esp_err_t sensor_manager_init(void)
{
    if (initialized) return ESP_OK;

    /* Configure I2C master */
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA,
        .scl_io_num = I2C_MASTER_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ,
    };
    ESP_ERROR_CHECK(i2c_param_config(I2C_MASTER_NUM, &conf));
    ESP_ERROR_CHECK(i2c_driver_install(I2C_MASTER_NUM, I2C_MODE_MASTER, 0, 0, 0));

    /* Configure ADC for MAX9814 */
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(AUDIO_ADC_CHANNEL, ADC_ATTEN_DB_11);

    ESP_LOGI(TAG, "I2C bus @ 400kHz, ADC @ 12-bit initialized");

    /* Self-test all sensors */
    esp_err_t ret = sensor_manager_self_test();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Self-test incomplete — some sensors may not respond");
    }

    initialized = true;
    return ESP_OK;
}

esp_err_t sensor_manager_read_all(sensor_data_t *data)
{
    if (!initialized) return ESP_ERR_INVALID_STATE;

    data->timestamp_ms = esp_timer_get_time() / 1000;

    /* Read each sensor — failures are logged but don't abort others */
    if (bme680_read(&data->temperature, &data->humidity, &data->pressure, &data->voc_index) != ESP_OK)
        ESP_LOGW(TAG, "BME680 read failed");

    if (sgp40_read(&data->voc_index_sgp) != ESP_OK)
        ESP_LOGW(TAG, "SGP40 read failed");

    if (sps30_read(&data->pm1_0, &data->pm2_5, &data->pm4_0, &data->pm10) != ESP_OK)
        ESP_LOGW(TAG, "SPS30 read failed");

    if (icm42688_read(&data->activity, &data->accel_mag) != ESP_OK)
        ESP_LOGW(TAG, "ICM-42688 read failed");

    if (tsl2591_read(&data->lux, &data->color_temp, &data->flicker_detected) != ESP_OK)
        ESP_LOGW(TAG, "TSL2591 read failed");

    if (max9814_read(&data->sound_dba, &data->spectral_class) != ESP_OK)
        ESP_LOGW(TAG, "MAX9814 read failed");

    return ESP_OK;
}

esp_err_t sensor_manager_self_test(void)
{
    uint8_t buf[1] = {0};
    esp_err_t ret;
    int pass = 0, total = 5;

    /* Probe each I2C device */
    ret = i2c_read_reg(BME680_ADDR, 0xD0, buf, 1);  /* Chip ID */
    if (ret == ESP_OK) { ESP_LOGI(TAG, "BME680: OK (ID=0x%02X)", buf[0]); pass++; }

    ret = i2c_read_reg(SGP40_ADDR, 0x36, buf, 1);
    if (ret == ESP_OK) { ESP_LOGI(TAG, "SGP40: OK"); pass++; }

    ret = i2c_read_reg(SPS30_ADDR, 0xD0, buf, 1);
    if (ret == ESP_OK) { ESP_LOGI(TAG, "SPS30: OK"); pass++; }

    ret = i2c_read_reg(ICM42688_ADDR, 0x00, buf, 1);
    if (ret == ESP_OK) { ESP_LOGI(TAG, "ICM-42688: OK"); pass++; }

    ret = i2c_read_reg(TSL2591_ADDR, 0x12, buf, 1);
    if (ret == ESP_OK) { ESP_LOGI(TAG, "TSL2591: OK"); pass++; }

    ESP_LOGI(TAG, "Self-test: %d/%d sensors responding", pass, total);
    return (pass >= 3) ? ESP_OK : ESP_ERR_NOT_FOUND;
}