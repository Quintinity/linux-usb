---
name: Surface Pro 7 Hardware
type: reference
---

# Surface Pro 7 Hardware

## Specs
- **CPU:** Intel Core i5-1035G4 (Ice Lake, 4C/8T)
- **RAM:** 8 GB LPDDR4x
- **GPU:** Intel Iris Plus Graphics (no CUDA, no discrete GPU)
- **Storage:** 128 GB / 256 GB SSD (NVMe)

## Linux Notes

### Networking
- **WiFi:** Intel AX201 — works with stock Ubuntu kernel, no extra drivers needed

### Input
- **Type Cover keyboard/trackpad:** Requires linux-surface kernel for full support
- **Touchscreen:** Works after linux-surface kernel + iptsd (touch daemon)

### Cameras
- **Front and rear cameras do NOT work** under Linux on this device
- Use USB webcams for any camera-dependent tasks (e.g., LeRobot data collection)

### USB Ports
- 1x USB-A 3.1
- 1x USB-C 3.1
- Multi-port USB adapter available for connecting multiple peripherals simultaneously

### Peripherals
- USB wireless keyboard (backup/alternative to Type Cover)
- Feetech SO-101 servo controller connects via USB serial (CH340 chip, vendor ID 1a86)
