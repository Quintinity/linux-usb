// linux-usb/xiao-citizen/citizenry_camera.h
//
// Phase 3.0: shared OV2640 lifecycle + mutex'd capture. Both the legacy
// CameraWebServer (`/capture`, `/stream`) in app_httpd.cpp and the new
// citizenry PROPOSE→REPORT path go through this wrapper so a frame buffer
// is never grabbed twice concurrently.
//
// Hardware-only — host tests are wrapped behind ARDUINO_HOST_TEST so they
// don't pull esp_camera.h into the g++ build.

#pragma once
#ifndef ARDUINO_HOST_TEST

#include "esp_camera.h"
#include <cstdint>

// Initialise the OV2640 with a Phase 3 sensible default (QVGA, JPEG, q=12).
// Returns true on success. Idempotent — second call is a no-op.
bool citizenry_camera_begin();

// Mutex'd grab; release with citizenry_camera_release(fb). Returns NULL on
// timeout or hardware error. Caller MUST balance with release(). The mutex
// is held between grab() and release(), so a second concurrent grab() blocks
// up to timeout_ms before failing.
camera_fb_t* citizenry_camera_grab(uint32_t timeout_ms = 1000);
void         citizenry_camera_release(camera_fb_t* fb);

// Cheap accessors for the configured sensor — used by build_report_frame_capture
// to fill width/height without re-reading the FB metadata.
uint16_t citizenry_camera_width();
uint16_t citizenry_camera_height();

// Was the camera successfully initialised? Used by the PROPOSE handler to
// REJECT cleanly when the sensor failed at boot.
bool citizenry_camera_ready();

#endif // !ARDUINO_HOST_TEST
