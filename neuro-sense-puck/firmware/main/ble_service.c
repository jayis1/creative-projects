/*
 * ble_service.c — BLE 5.0 GATT server implementation
 *
 * Advertising: 31-byte packet with UUID + manufacturer-specific sensor summary
 * GATT: 9 readable/notifiable characteristics
 */

#include "ble_service.h"
#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/ble_gap.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "BLE_SVC";
static const char *device_name = "NeuroPuck";

/* Stored sensor state for GATT reads */
static env_class_t current_class = ENV_CLASS_UNKNOWN;
static sensor_data_t current_data = {0};

/* GATT characteristic value handles */
static uint16_t env_class_handle;
static uint16_t voc_handle;
static uint16_t pm25_handle;
static uint16_t temp_handle;
static uint16_t hum_handle;
static uint16_t lux_handle;
static uint16_t dba_handle;
static uint16_t act_handle;
static uint16_t info_handle;

/* ---- GATT Access Callbacks ---- */

static int sensor_access_cb(uint16_t conn_handle, uint16_t attr_handle,
                            struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    int rc = 0;
    uint8_t buf[16];

    switch (ctxt->op) {
    case BLE_GATT_ACCESS_OP_READ_CHR:
        if (attr_handle == env_class_handle) {
            buf[0] = (uint8_t)current_class;
            rc = os_mbuf_append(ctxt->om, buf, 1);
        } else if (attr_handle == voc_handle) {
            buf[0] = (current_data.voc_index >> 8) & 0xFF;
            buf[1] = current_data.voc_index & 0xFF;
            rc = os_mbuf_append(ctxt->om, buf, 2);
        } else if (attr_handle == pm25_handle) {
            memcpy(buf, &current_data.pm2_5, 4);
            rc = os_mbuf_append(ctxt->om, buf, 4);
        } else if (attr_handle == temp_handle) {
            memcpy(buf, &current_data.temperature, 4);
            rc = os_mbuf_append(ctxt->om, buf, 4);
        } else if (attr_handle == hum_handle) {
            memcpy(buf, &current_data.humidity, 4);
            rc = os_mbuf_append(ctxt->om, buf, 4);
        } else if (attr_handle == lux_handle) {
            memcpy(buf, &current_data.lux, 4);
            rc = os_mbuf_append(ctxt->om, buf, 4);
        } else if (attr_handle == dba_handle) {
            memcpy(buf, &current_data.sound_dba, 4);
            rc = os_mbuf_append(ctxt->om, buf, 4);
        } else if (attr_handle == act_handle) {
            buf[0] = (uint8_t)current_data.activity;
            rc = os_mbuf_append(ctxt->om, buf, 1);
        } else if (attr_handle == info_handle) {
            const char *info = "NeuroPuck v1.0 by jayis1";
            rc = os_mbuf_append(ctxt->om, info, strlen(info));
        }
        return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;

    case BLE_GATT_ACCESS_OP_WRITE_CHR:
        return BLE_ATT_ERR_WRITE_NOT_PERMITTED;

    default:
        return BLE_ATT_ERR_UNLIKELY;
    }
}

/* ---- GATT Service Definition ---- */

static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(NEURO_SENSE_SERVICE_UUID),
        .characteristics = (struct ble_gatt_chr_def[]) {
            { .uuid = BLE_UUID16_DECLARE(CHAR_ENV_CLASS_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
              .val_handle = &env_class_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_VOC_INDEX_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &voc_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_PM25_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &pm25_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_TEMPERATURE_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &temp_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_HUMIDITY_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &hum_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_LIGHT_LUX_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &lux_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_SOUND_DBA_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &dba_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_ACTIVITY_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &act_handle },
            { .uuid = BLE_UUID16_DECLARE(CHAR_DEVICE_INFO_UUID),
              .access_cb = sensor_access_cb,
              .flags = BLE_GATT_CHR_F_READ,
              .val_handle = &info_handle },
            { 0 } /* terminator */
        },
    },
    { 0 } /* terminator */
};

/* ---- GAP Event Handler ---- */

static int gap_event_cb(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        ESP_LOGI(TAG, "BLE %s; status=%d",
                 event->connect.status == 0 ? "connected" : "connect failed",
                 event->connect.status);
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGI(TAG, "BLE disconnected; reason=%d", event->disconnect.reason);
        /* Restart advertising */
        ble_service_update(current_class, &current_data);
        break;
    default:
        break;
    }
    return 0;
}

/* ---- Advertising ---- */

static void start_advertising(void)
{
    struct ble_hs_adv_fields fields = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.uuids16 = (ble_uuid16_t[]) { BLE_UUID16_INIT(NEURO_SENSE_SERVICE_UUID) };
    fields.num_uuids16 = 1;
    fields.uuids16_is_complete = 1;

    /* Manufacturer-specific data: env_class(1) + voc(2) + pm25_lo(2) + temp_lo(1) + activity(1) = 7 bytes */
    uint8_t mfg_data[9];
    mfg_data[0] = 0xFF; mfg_data[1] = 0xFF;  /* mfg ID placeholder */
    mfg_data[2] = (uint8_t)current_class;
    mfg_data[3] = (current_data.voc_index >> 8) & 0xFF;
    mfg_data[4] = current_data.voc_index & 0xFF;
    uint16_t pm25_raw = (uint16_t)(current_data.pm2_5 * 10);
    mfg_data[5] = (pm25_raw >> 8) & 0xFF;
    mfg_data[6] = pm25_raw & 0xFF;
    mfg_data[7] = (uint8_t)current_data.temperature;
    mfg_data[8] = (uint8_t)current_data.activity;

    fields.mfg_data = mfg_data;
    fields.mfg_data_len = sizeof(mfg_data);

    ble_gap_adv_set_fields(&fields);

    struct ble_gap_adv_params adv_params = {0};
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    adv_params.itvl_min = 0x0020;  /* 20ms */
    adv_params.itvl_max = 0x0060;  /* 60ms */

    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                      &adv_params, gap_event_cb, NULL);
}

/* ---- NimBLE sync callback ---- */

static void ble_on_sync(void)
{
    ESP_LOGI(TAG, "BLE synced, starting advertising");
    start_advertising();
}

/* ---- Public API ---- */

esp_err_t ble_service_init(void)
{
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_gatts_count_cfg(gatt_svr_svcs);
    ble_gatts_add_svcs(gatt_svr_svcs);

    ble_hs_cfg.sync_cb = ble_on_sync;

    ESP_LOGI(TAG, "BLE GATT service registered (0x%04X)", NEURO_SENSE_SERVICE_UUID);
    return ESP_OK;
}

esp_err_t ble_service_update(env_class_t cls, const sensor_data_t *data)
{
    current_class = cls;
    current_data = *data;

    /* Restart advertising with updated payload */
    start_advertising();

    /* Send notification on env class characteristic if subscribed */
    if (env_class_handle != 0) {
        uint8_t val = (uint8_t)cls;
        ble_gatts_notify_custom(0, env_class_handle,
                                os_mbuf_get(&val, 1));
    }

    return ESP_OK;
}