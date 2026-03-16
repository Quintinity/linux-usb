"""Dynamixel XL330/XL430 Driver — uses dynamixel_sdk.

Supports Koch v1.1 and other Dynamixel-based arms.
Falls back gracefully if dynamixel_sdk is not installed.
"""

from __future__ import annotations

from .servo_driver import ServoDriver, MotorInfo

# Dynamixel XL330/XL430 control table addresses
_ADDR_TORQUE_ENABLE = 64
_ADDR_GOAL_POSITION = 116
_ADDR_PRESENT_POSITION = 132
_ADDR_PRESENT_VOLTAGE = 144
_ADDR_PRESENT_TEMPERATURE = 146
_ADDR_PRESENT_LOAD = 126
_ADDR_PRESENT_CURRENT = 126  # Same as load on XL series
_ADDR_MODEL_NUMBER = 0

_PROTOCOL_VERSION = 2.0
_DEFAULT_BAUDRATE = 57600


class DynamixelDriver(ServoDriver):
    """ServoDriver for Dynamixel XL330/XL430 servos."""

    def __init__(self):
        self._port_handler = None
        self._packet_handler = None
        self._port: str = ""
        self._motor_ids: list[int] = []
        self._connected = False

    @property
    def protocol_name(self) -> str:
        return "dynamixel"

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, port: str, baudrate: int = _DEFAULT_BAUDRATE) -> None:
        try:
            from dynamixel_sdk import PortHandler, PacketHandler
        except ImportError:
            raise ImportError("dynamixel_sdk not installed. Run: pip install dynamixel-sdk")

        self._port = port
        self._port_handler = PortHandler(port)
        self._packet_handler = PacketHandler(_PROTOCOL_VERSION)

        if not self._port_handler.openPort():
            raise ConnectionError(f"Failed to open port {port}")
        if not self._port_handler.setBaudRate(baudrate):
            raise ConnectionError(f"Failed to set baudrate {baudrate}")

        self._connected = True

    def disconnect(self) -> None:
        if self._port_handler:
            self._port_handler.closePort()
        self._connected = False
        self._port_handler = None
        self._packet_handler = None

    def scan_motors(self, id_range: range = range(1, 20)) -> list[MotorInfo]:
        if not self._connected:
            return []
        found = []
        for mid in id_range:
            try:
                model, result, error = self._packet_handler.read2ByteTxRx(
                    self._port_handler, mid, _ADDR_MODEL_NUMBER
                )
                if result == 0 and error == 0:
                    model_name = "xl330" if model == 1190 else "xl430" if model == 1060 else f"dxl_{model}"
                    found.append(MotorInfo(id=mid, model=model_name))
            except Exception:
                continue
        return found

    def read_position(self, motor_id: int) -> int:
        if not self._connected:
            return 0
        try:
            val, result, _ = self._packet_handler.read4ByteTxRx(
                self._port_handler, motor_id, _ADDR_PRESENT_POSITION
            )
            return val if result == 0 else 0
        except Exception:
            return 0

    def write_position(self, motor_id: int, position: int) -> None:
        if not self._connected:
            return
        try:
            self._packet_handler.write4ByteTxRx(
                self._port_handler, motor_id, _ADDR_GOAL_POSITION, position
            )
        except Exception:
            pass

    def sync_read_positions(self, motor_ids: list[int]) -> dict[int, int]:
        if not self._connected:
            return {}
        return {mid: self.read_position(mid) for mid in motor_ids}

    def sync_write_positions(self, positions: dict[int, int]) -> None:
        if not self._connected:
            return
        for mid, pos in positions.items():
            self.write_position(mid, pos)

    def enable_torque(self, motor_ids: list[int] | None = None) -> None:
        if not self._connected:
            return
        for mid in (motor_ids or self._motor_ids):
            try:
                self._packet_handler.write1ByteTxRx(
                    self._port_handler, mid, _ADDR_TORQUE_ENABLE, 1
                )
            except Exception:
                pass

    def disable_torque(self, motor_ids: list[int] | None = None) -> None:
        if not self._connected:
            return
        for mid in (motor_ids or self._motor_ids):
            try:
                self._packet_handler.write1ByteTxRx(
                    self._port_handler, mid, _ADDR_TORQUE_ENABLE, 0
                )
            except Exception:
                pass

    def read_voltage(self, motor_id: int) -> float:
        if not self._connected:
            return 0.0
        try:
            val, result, _ = self._packet_handler.read2ByteTxRx(
                self._port_handler, motor_id, _ADDR_PRESENT_VOLTAGE
            )
            return val / 10.0 if result == 0 else 0.0
        except Exception:
            return 0.0

    def read_temperature(self, motor_id: int) -> float:
        if not self._connected:
            return 0.0
        try:
            val, result, _ = self._packet_handler.read1ByteTxRx(
                self._port_handler, motor_id, _ADDR_PRESENT_TEMPERATURE
            )
            return float(val) if result == 0 else 0.0
        except Exception:
            return 0.0

    def read_load(self, motor_id: int) -> float:
        if not self._connected:
            return 0.0
        try:
            val, result, _ = self._packet_handler.read2ByteTxRx(
                self._port_handler, motor_id, _ADDR_PRESENT_LOAD
            )
            if result != 0:
                return 0.0
            # Dynamixel load is signed 16-bit
            if val > 32767:
                val -= 65536
            return val / 10.0
        except Exception:
            return 0.0

    def read_current(self, motor_id: int) -> float:
        if not self._connected:
            return 0.0
        try:
            val, result, _ = self._packet_handler.read2ByteTxRx(
                self._port_handler, motor_id, _ADDR_PRESENT_CURRENT
            )
            if result != 0:
                return 0.0
            if val > 32767:
                val -= 65536
            return val * 2.69  # XL330 current scale: 1 unit = 2.69mA
        except Exception:
            return 0.0
