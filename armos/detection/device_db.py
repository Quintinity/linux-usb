"""USB Device Database — maps vendor:product IDs to driver types.

When a USB device is plugged in, we look up its IDs here to determine
what kind of servo controller or camera it is.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeviceInfo:
    """Information about a detected USB device."""
    vendor_id: str
    product_id: str
    driver_type: str  # "feetech", "dynamixel", "camera", "unknown"
    device_name: str
    port: str = ""
    serial: str = ""


# USB Vendor:Product → Driver Type mapping
KNOWN_DEVICES: dict[tuple[str, str], tuple[str, str]] = {
    # Feetech CH340/CH341 USB-serial adapters
    ("1a86", "55d3"): ("feetech", "QinHeng CH340 (Feetech)"),
    ("1a86", "7523"): ("feetech", "QinHeng CH341 (Feetech)"),
    ("1a86", "55d4"): ("feetech", "QinHeng CH9340 (Feetech)"),

    # Dynamixel USB adapters (FTDI-based)
    ("0403", "6014"): ("dynamixel", "FTDI USB2Dynamixel"),
    ("0403", "6001"): ("dynamixel", "FTDI FT232R (Dynamixel)"),
    ("0403", "6015"): ("dynamixel", "FTDI FT-X (U2D2)"),

    # Robotis U2D2 direct
    ("fff1", "ff48"): ("dynamixel", "Robotis U2D2"),
}


def identify_device(vendor_id: str, product_id: str) -> DeviceInfo:
    """Identify a USB device by its vendor and product IDs.

    Args:
        vendor_id: USB vendor ID (hex string, e.g., "1a86")
        product_id: USB product ID (hex string, e.g., "55d3")

    Returns:
        DeviceInfo with driver_type set ("feetech", "dynamixel", or "unknown")
    """
    key = (vendor_id.lower(), product_id.lower())
    if key in KNOWN_DEVICES:
        driver_type, name = KNOWN_DEVICES[key]
        return DeviceInfo(
            vendor_id=vendor_id,
            product_id=product_id,
            driver_type=driver_type,
            device_name=name,
        )
    return DeviceInfo(
        vendor_id=vendor_id,
        product_id=product_id,
        driver_type="unknown",
        device_name=f"Unknown ({vendor_id}:{product_id})",
    )


def list_known_devices() -> list[tuple[str, str, str]]:
    """List all known device IDs and their types."""
    return [
        (f"{vid}:{pid}", driver, name)
        for (vid, pid), (driver, name) in sorted(KNOWN_DEVICES.items())
    ]
