"""ServoDriver ABC — abstract interface for servo motor communication.

Every servo protocol (Feetech, Dynamixel, CAN-bus, etc.) implements this
interface. The ArmCitizen uses it without knowing what's underneath.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MotorInfo:
    """Information about a discovered motor."""
    id: int
    model: str = "unknown"
    firmware_version: int = 0
    position: int = 0


class ServoDriver(ABC):
    """Abstract interface for servo motor communication.

    Implementors: FeetechDriver, DynamixelDriver, etc.
    """

    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return the protocol name (e.g., 'feetech', 'dynamixel')."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the driver is connected to the bus."""
        ...

    @abstractmethod
    def connect(self, port: str, baudrate: int = 1000000) -> None:
        """Connect to the servo bus on the given serial port."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the servo bus."""
        ...

    @abstractmethod
    def scan_motors(self, id_range: range = range(1, 20)) -> list[MotorInfo]:
        """Scan for connected motors in the given ID range."""
        ...

    @abstractmethod
    def read_position(self, motor_id: int) -> int:
        """Read current position of a motor (raw value)."""
        ...

    @abstractmethod
    def write_position(self, motor_id: int, position: int) -> None:
        """Write goal position to a motor (raw value)."""
        ...

    @abstractmethod
    def sync_read_positions(self, motor_ids: list[int]) -> dict[int, int]:
        """Read positions from multiple motors in one transaction."""
        ...

    @abstractmethod
    def sync_write_positions(self, positions: dict[int, int]) -> None:
        """Write positions to multiple motors in one transaction."""
        ...

    @abstractmethod
    def enable_torque(self, motor_ids: list[int] | None = None) -> None:
        """Enable torque on specified motors (None = all)."""
        ...

    @abstractmethod
    def disable_torque(self, motor_ids: list[int] | None = None) -> None:
        """Disable torque on specified motors (None = all)."""
        ...

    @abstractmethod
    def read_voltage(self, motor_id: int) -> float:
        """Read supply voltage for a motor (volts)."""
        ...

    @abstractmethod
    def read_temperature(self, motor_id: int) -> float:
        """Read motor temperature (celsius)."""
        ...

    @abstractmethod
    def read_load(self, motor_id: int) -> float:
        """Read motor load (percent, signed)."""
        ...

    @abstractmethod
    def read_current(self, motor_id: int) -> float:
        """Read motor current draw (milliamps)."""
        ...

    def read_telemetry(self, motor_id: int) -> dict[str, float]:
        """Read all telemetry for a motor. Default calls individual reads."""
        return {
            "position": self.read_position(motor_id),
            "voltage": self.read_voltage(motor_id),
            "temperature": self.read_temperature(motor_id),
            "load": self.read_load(motor_id),
            "current": self.read_current(motor_id),
        }
