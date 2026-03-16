"""Motor Scanner — scan a servo bus for connected motors.

Works with any ServoDriver implementation. Used during hardware detection
and first-run wizard to identify what's connected.
"""

from __future__ import annotations

from dataclasses import dataclass
from .servo_driver import ServoDriver, MotorInfo


@dataclass
class ScanResult:
    """Result of a motor scan."""
    port: str
    protocol: str
    motors: list[MotorInfo]
    motor_count: int = 0

    def __post_init__(self):
        self.motor_count = len(self.motors)


def scan_bus(driver: ServoDriver, port: str, id_range: range = range(1, 20)) -> ScanResult:
    """Scan a servo bus for connected motors.

    Args:
        driver: The servo driver to use (determines protocol)
        port: Serial port path
        id_range: Range of motor IDs to scan

    Returns:
        ScanResult with list of found motors
    """
    try:
        driver.connect(port)
        motors = driver.scan_motors(id_range)
        driver.disconnect()
        return ScanResult(
            port=port,
            protocol=driver.protocol_name,
            motors=motors,
        )
    except Exception as e:
        return ScanResult(port=port, protocol=driver.protocol_name, motors=[])
