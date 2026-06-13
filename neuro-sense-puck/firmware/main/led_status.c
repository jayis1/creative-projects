/*
 * led_status.c — WS2812B NeoPixel status indicator
 *
 * Maps 16 environment classes to distinct colors.
 * Uses RMT peripheral for WS2812B timing-accurate data transmission.
 */

#include "led_status.h"
#include "esp_log.h"
#include "driver/rmt.h"

static const char *TAG = "LED_STAT";
#define WS2812B_GPIO  15
#define WS2812B_RMT   RMT_CHANNEL_0
#define NUM_LEDS      1

/* Color map for each environment class (RGB) */
typedef struct { uint8_t r, g, b; } rgb_t;

static const rgb_t class_colors[ENV_CLASS_MAX] = {
    {0,   255, 128},   /* FRESH_OUTDOORS  — spring green */
    {255, 200, 0},     /* STUFFY_OFFICE   — amber */
    {0,   128, 255},   /* ACTIVE_COMMUTE  — sky blue */
    {128, 64,  255},   /* QUIET_HOME      — lavender */
    {255, 64,  0},     /* GYM_WORKOUT     — orange-red */
    {32,  0,   128},   /* SLEEP_READY     — deep purple */
    {255, 0,   0},     /* LOUD_STREET     — red */
    {0,   128, 255},   /* RAIN_OUTDOORS   — blue */
    {255, 255, 0},     /* SUNNY_PARK      — yellow */
    {200, 100, 0},     /* CROWDED_INDOOR  — brown-orange */
    {0,   128, 128},   /* COOL_BASEMENT   — teal */
    {255, 128, 0},     /* HUMID_KITCHEN   — warm orange */
    {200, 200, 255},   /* WINDY_ROOFTOP   — ice blue */
    {128, 0,   0},     /* SMOKY_AREA      — dark red */
    {0,   0,   64},    /* SILENT_NIGHT    — navy */
    {64,  64,  64},    /* UNKNOWN         — gray */
};

static bool initialized = false;

static void ws2812b_send(const rgb_t *color)
{
    /* WS2812B protocol: each bit is a pulse pair
       0-bit: 0.4µs high + 0.85µs low
       1-bit: 0.8µs high + 0.45µs low
       Using RMT channel for precise timing */
    rmt_item32_t items[24];
    for (int bit = 0; bit < 24; bit++) {
        uint8_t byte_val;
        if (bit < 8) byte_val = color->g;
        else if (bit < 16) byte_val = color->r;
        else byte_val = color->b;

        /* WS2812B is MSB-first for each color byte */
        int idx = bit % 8;
        bool high = (byte_val & (1 << (7 - idx))) != 0;

        items[bit].duration0 = high ? 80 : 40;   /* 0.8µs or 0.4µs (100MHz clock) */
        items[bit].level0 = 1;
        items[bit].duration1 = high ? 45 : 85;   /* 0.45µs or 0.85µs */
        items[bit].level1 = 0;
    }

    rmt_write_items(WS2812B_RMT, items, 24, true);
    /* Reset latch: >50µs low */
    vTaskDelay(pdMS_TO_TICKS(1));
}

esp_err_t led_status_init(void)
{
    rmt_config_t config = {
        .rmt_mode = RMT_MODE_TX,
        .channel = WS2812B_RMT,
        .gpio_num = WS2812B_GPIO,
        .mem_block_num = 1,
        .tx_config.loop_en = false,
        .tx_config.carrier_en = false,
        .clk_div = 1,  /* 80MHz APB clock */
    };
    esp_err_t ret = rmt_config(&config);
    if (ret != ESP_OK) return ret;
    ret = rmt_driver_install(WS2812B_RMT, 0, 0);
    if (ret != ESP_OK) return ret;

    initialized = true;
    /* Startup animation: white flash */
    rgb_t white = {255, 255, 255};
    ws2812b_send(&white);
    vTaskDelay(pdMS_TO_TICKS(100));
    rgb_t off = {0, 0, 0};
    ws2812b_send(&off);

    ESP_LOGI(TAG, "WS2812B on GPIO%d initialized", WS2812B_GPIO);
    return ESP_OK;
}

void led_status_show(env_class_t cls)
{
    if (!initialized) return;
    if (cls >= ENV_CLASS_MAX) cls = ENV_CLASS_UNKNOWN;
    ws2812b_send(&class_colors[cls]);
}

void led_status_error(void)
{
    if (!initialized) return;
    rgb_t red = {255, 0, 0};
    ws2812b_send(&red);
}