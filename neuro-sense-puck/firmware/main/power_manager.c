/*
 * power_manager.c — Deep sleep, duty cycling, battery monitoring
 */

#include "power_manager.h"
#include "esp_sleep.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/adc.h"

static const char *TAG = "POWER";
static bool charging = false;

esp_err_t power_manager_init(void)
{
    /* Configure GPIO14 as input for MCP73831 STAT pin */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << 14),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&io_conf);

    /* Enable GPIO wake source for charge status changes */
    esp_sleep_enable_gpio_wakeup();

    ESP_LOGI(TAG, "Power manager initialized");
    return ESP_OK;
}

void power_manager_sleep_ms(uint32_t ms)
{
    /* Configure RTC timer wakeup */
    esp_sleep_enable_timer_wakeup((uint64_t)ms * 1000);

    /* Check charge status before sleeping */
    charging = (gpio_get_level(14) == 0);  /* STAT low = charging */

    /* Enter deep sleep */
    esp_deep_sleep_start();

    /* Never reaches here — wakes at app_main() */
}

float power_manager_get_battery_voltage(void)
{
    /* In production: use ADC on battery divider through AP2112 bypass */
    /* Placeholder: return 3.7V nominal */
    return 3.7f;
}

bool power_manager_is_charging(void)
{
    return charging;
}