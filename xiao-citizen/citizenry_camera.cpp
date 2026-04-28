// linux-usb/xiao-citizen/citizenry_camera.cpp
//
// Phase 3.0 implementation: esp_camera_init + a FreeRTOS mutex shared by
// the legacy http /capture path and the citizenry PROPOSE→REPORT path.
#ifndef ARDUINO_HOST_TEST
#include "citizenry_camera.h"
#include "board_config.h"
#include "camera_pins.h"
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <Arduino.h>

static SemaphoreHandle_t s_camera_mtx = nullptr;
static bool              s_inited     = false;
static uint16_t          s_width      = 320;
static uint16_t          s_height     = 240;

bool citizenry_camera_begin() {
    if (s_inited) return true;
    if (!s_camera_mtx) s_camera_mtx = xSemaphoreCreateMutex();

    camera_config_t cfg = {};
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.ledc_timer   = LEDC_TIMER_0;
    cfg.pin_d0       = Y2_GPIO_NUM;
    cfg.pin_d1       = Y3_GPIO_NUM;
    cfg.pin_d2       = Y4_GPIO_NUM;
    cfg.pin_d3       = Y5_GPIO_NUM;
    cfg.pin_d4       = Y6_GPIO_NUM;
    cfg.pin_d5       = Y7_GPIO_NUM;
    cfg.pin_d6       = Y8_GPIO_NUM;
    cfg.pin_d7       = Y9_GPIO_NUM;
    cfg.pin_xclk     = XCLK_GPIO_NUM;
    cfg.pin_pclk     = PCLK_GPIO_NUM;
    cfg.pin_vsync    = VSYNC_GPIO_NUM;
    cfg.pin_href     = HREF_GPIO_NUM;
    cfg.pin_sccb_sda = SIOD_GPIO_NUM;
    cfg.pin_sccb_scl = SIOC_GPIO_NUM;
    cfg.pin_pwdn     = PWDN_GPIO_NUM;
    cfg.pin_reset    = RESET_GPIO_NUM;
    cfg.xclk_freq_hz = 20000000;
    cfg.frame_size   = FRAMESIZE_QVGA;
    cfg.pixel_format = PIXFORMAT_JPEG;
    cfg.grab_mode    = CAMERA_GRAB_LATEST;
    cfg.fb_location  = CAMERA_FB_IN_PSRAM;
    cfg.jpeg_quality = 12;
    cfg.fb_count     = 2;

    if (esp_camera_init(&cfg) != ESP_OK) return false;
    s_width  = 320;
    s_height = 240;
    s_inited = true;
    return true;
}

camera_fb_t* citizenry_camera_grab(uint32_t timeout_ms) {
    if (!s_inited) return nullptr;
    if (xSemaphoreTake(s_camera_mtx, pdMS_TO_TICKS(timeout_ms)) != pdTRUE) return nullptr;
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        xSemaphoreGive(s_camera_mtx);
        return nullptr;
    }
    return fb;  // mutex held until release
}

void citizenry_camera_release(camera_fb_t* fb) {
    if (fb) esp_camera_fb_return(fb);
    if (s_camera_mtx) xSemaphoreGive(s_camera_mtx);
}

uint16_t citizenry_camera_width()  { return s_width; }
uint16_t citizenry_camera_height() { return s_height; }
bool     citizenry_camera_ready()  { return s_inited; }
#endif
