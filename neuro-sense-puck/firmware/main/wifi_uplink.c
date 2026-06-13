/*
 * wifi_uplink.c — WiFi 6 MQTT push implementation
 *
 * Connects to configured WiFi AP, publishes JSON to MQTT broker.
 * Falls back gracefully if no credentials stored.
 */

#include "wifi_uplink.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "mqtt_client.h"
#include "cJSON.h"

static const char *TAG = "WIFI_UPLINK";
static bool connected = false;
static esp_mqtt_client_handle_t mqtt_client = NULL;

#define MQTT_BROKER_URL  "mqtt://broker.hivemq.com:1883"
#define MQTT_TOPIC       "neuropuck/sensor_data"

esp_err_t wifi_uplink_init(void)
{
    /* Check if WiFi credentials are stored in NVS */
    nvs_handle_t nvs;
    esp_err_t ret = nvs_open("wifi_creds", NVS_READONLY, &nvs);
    if (ret != ESP_OK) {
        ESP_LOGI(TAG, "No WiFi credentials stored — uplink disabled");
        return ESP_OK;
    }

    char ssid[33] = {0}, password[65] = {0};
    size_t ssid_len = sizeof(ssid), pass_len = sizeof(password);

    if (nvs_get_str(nvs, "ssid", ssid, &ssid_len) != ESP_OK ||
        nvs_get_str(nvs, "password", password, &pass_len) != ESP_OK) {
        ESP_LOGI(TAG, "Incomplete WiFi credentials — uplink disabled");
        nvs_close(nvs);
        return ESP_OK;
    }
    nvs_close(nvs);

    /* Configure WiFi station */
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);

    wifi_config_t wifi_config = {0};
    strlcpy((char *)wifi_config.sta.ssid, ssid, sizeof(wifi_config.sta.ssid));
    strlcpy((char *)wifi_config.sta.password, password, sizeof(wifi_config.sta.password));
    wifi_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
    esp_wifi_connect();

    /* Configure MQTT client */
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.uri = MQTT_BROKER_URL,
    };
    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_start(mqtt_client);

    connected = true;
    ESP_LOGI(TAG, "WiFi uplink initialized (SSID: %s)", ssid);
    return ESP_OK;
}

bool wifi_uplink_is_connected(void)
{
    return connected;
}

esp_err_t wifi_uplink_push(const sensor_data_t *data, env_class_t cls)
{
    if (!connected || !mqtt_client) return ESP_ERR_INVALID_STATE;

    /* Build JSON payload */
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "class", cls);
    cJSON_AddNumberToObject(root, "temp", data->temperature);
    cJSON_AddNumberToObject(root, "hum", data->humidity);
    cJSON_AddNumberToObject(root, "voc", data->voc_index);
    cJSON_AddNumberToObject(root, "pm25", data->pm2_5);
    cJSON_AddNumberToObject(root, "lux", data->lux);
    cJSON_AddNumberToObject(root, "dba", data->sound_dba);
    cJSON_AddNumberToObject(root, "act", data->activity);
    cJSON_AddNumberToObject(root, "ts", data->timestamp_ms);

    char *json = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);

    /* Publish to MQTT */
    int msg_id = esp_mqtt_client_publish(mqtt_client, MQTT_TOPIC, json, 0, 1, 0);
    free(json);

    if (msg_id == -1) {
        ESP_LOGW(TAG, "MQTT publish failed");
        return ESP_FAIL;
    }

    ESP_LOGD(TAG, "Pushed to MQTT (msg_id=%d)", msg_id);
    return ESP_OK;
}