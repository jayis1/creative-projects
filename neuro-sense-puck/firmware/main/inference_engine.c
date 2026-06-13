/*
 * inference_engine.c — TFLite Micro environment classification
 *
 * Model: 4-layer FC INT8 quantized, 48KB
 * Input: 12 normalized features from sensor_data_t
 * Output: 16-class softmax
 */

#include "inference_engine.h"
#include "esp_log.h"
#include "esp_system.h"

/* TFLite Micro headers — linked via components/ */
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

static const char *TAG = "INFERENCE";

/* Model binary — embedded in flash via component CMakeLists */
extern const unsigned char env_classify_model_tflite[];
extern const unsigned int env_classify_model_tflite_len;

/* TFLite arena — 64KB should be enough for this tiny model */
static constexpr int kTensorArenaSize = 64 * 1024;
static uint8_t tensor_arena[kTensorArenaSize] __attribute__((aligned(16)));

static tflite::MicroInterpreter *interpreter = nullptr;
static float last_confidence = 0.0f;

/* Feature normalization ranges (determined from training data) */
typedef struct {
    float temp_min, temp_max;     /* -20 to 60 °C */
    float hum_min, hum_max;       /* 0 to 100 % */
    float voc_min, voc_max;       /* 0 to 500 */
    float pm25_min, pm25_max;     /* 0 to 250 µg/m³ */
    float lux_min, lux_max;       /* 0 to 88000 */
    float dba_min, dba_max;       /* 20 to 120 */
    float accel_min, accel_max;   /* 0 to 30 m/s² */
} norm_range_t;

static const norm_range_t norm = {
    .temp_min = -20.0f, .temp_max = 60.0f,
    .hum_min  = 0.0f,   .hum_max  = 100.0f,
    .voc_min  = 0.0f,   .voc_max  = 500.0f,
    .pm25_min = 0.0f,   .pm25_max = 250.0f,
    .lux_min  = 0.0f,   .lux_max  = 88000.0f,
    .dba_min  = 20.0f,  .dba_max  = 120.0f,
    .accel_min= 0.0f,   .accel_max= 30.0f,
};

static inline float normalize(float val, float vmin, float vmax)
{
    if (vmax == vmin) return 0.0f;
    float n = (val - vmin) / (vmax - vmin);
    return n < 0.0f ? 0.0f : (n > 1.0f ? 1.0f : n);
}

esp_err_t inference_engine_init(void)
{
    const tflite::Model *model = tflite::GetModel(env_classify_model_tflite);
    if (!model) {
        ESP_LOGE(TAG, "Failed to load TFLite model");
        return ESP_FAIL;
    }

    static tflite::MicroMutableOpResolver<6> resolver;
    resolver.AddReshape();
    resolver.AddFullyConnected();
    resolver.AddRelu();
    resolver.AddSoftmax();
    resolver.AddQuantize();
    resolver.AddDequantize();

    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);

    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors failed");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "TFLite Micro initialized. Arena: %d bytes", kTensorArenaSize);
    ESP_LOGI(TAG, "Model input: %d features, output: %d classes",
             interpreter->input(0)->dims->data[1],
             interpreter->output(0)->dims->data[1]);

    return ESP_OK;
}

env_class_t inference_engine_classify(const sensor_data_t *data)
{
    if (!interpreter) return ENV_CLASS_UNKNOWN;

    /* Build 12-element normalized input vector */
    float input[12];
    input[0]  = normalize(data->temperature,    norm.temp_min,  norm.temp_max);
    input[1]  = normalize(data->humidity,        norm.hum_min,   norm.hum_max);
    input[2]  = normalize((float)data->voc_index, norm.voc_min,  norm.voc_max);
    input[3]  = normalize((float)data->voc_index_sgp, norm.voc_min, norm.voc_max);
    input[4]  = normalize(data->pm2_5,           norm.pm25_min,  norm.pm25_max);
    input[5]  = normalize(data->pm10,            norm.pm25_min,  norm.pm25_max);
    input[6]  = normalize(data->lux,             norm.lux_min,   norm.lux_max);
    input[7]  = normalize(data->color_temp / 100.0f, 0.0f, 65.0f); /* norm to 0-6500K → 0-65 */
    input[8]  = data->flicker_detected ? 1.0f : 0.0f;
    input[9]  = normalize(data->sound_dba,       norm.dba_min,   norm.dba_max);
    input[10] = normalize(data->accel_mag,       norm.accel_min, norm.accel_max);
    input[11] = (float)data->activity / 2.0f;   /* 0=still, 0.5=walk, 1=run */

    /* Copy to model input tensor */
    float *input_ptr = interpreter->typed_input_tensor<float>(0);
    for (int i = 0; i < 12; i++) {
        input_ptr[i] = input[i];
    }

    /* Run inference */
    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGW(TAG, "Inference invoke failed");
        return ENV_CLASS_UNKNOWN;
    }

    /* Find argmax from output */
    float *output = interpreter->typed_output_tensor<float>(0);
    int best = 0;
    float best_score = output[0];
    for (int i = 1; i < ENV_CLASS_MAX; i++) {
        if (output[i] > best_score) {
            best_score = output[i];
            best = i;
        }
    }

    last_confidence = best_score;
    return (env_class_t)best;
}

float inference_engine_get_confidence(void)
{
    return last_confidence;
}