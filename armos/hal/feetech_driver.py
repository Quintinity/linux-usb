"""Feetech STS3215 Driver — wraps lerobot's FeetechMotorsBus.

This is the reference implementation of ServoDriver for the SO-101 arm.
"""

from __future__ import annotations

from .servo_driver import ServoDriver, MotorInfo


class FeetechDriver(ServoDriver):
    """ServoDriver for Feetech STS3215 servos via CH340 USB adapter."""

    def __init__(self):
        self._bus = None
        self._port: str = ""
        self._motor_ids: list[int] = []

    @property
    def protocol_name(self) -> str:
        return "feetech"

    @property
    def is_connected(self) -> bool:
        return self._bus is not None

    def connect(self, port: str, baudrate: int = 1000000) -> None:
        from lerobot.motors.feetech.feetech import FeetechMotorsBus
        from lerobot.motors.motors_bus import Motor, MotorNormMode

        self._port = port
        # Default SO-101 motor config — will be overridden by profile
        motor_names = ["motor_1", "motor_2", "motor_3", "motor_4", "motor_5", "motor_6"]
        motors = {
            name: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100)
            for i, name in enumerate(motor_names)
        }
        self._bus = FeetechMotorsBus(port=port, motors=motors)
        self._bus.connect()
        self._motor_ids = list(range(1, 7))

    def disconnect(self) -> None:
        if self._bus:
            try:
                self._bus.disconnect()
            except Exception:
                pass
            self._bus = None

    def scan_motors(self, id_range: range = range(1, 20)) -> list[MotorInfo]:
        if not self._bus:
            return []
        found = []
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        for mid in id_range:
            try:
                model_raw, result, _ = ph.read2ByteTxRx(port, mid, 3)  # Model number register
                if result == 0:
                    found.append(MotorInfo(id=mid, model="sts3215", firmware_version=0))
            except Exception:
                continue
        return found

    def read_position(self, motor_id: int) -> int:
        if not self._bus:
            return 0
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        try:
            val, result, _ = ph.read2ByteTxRx(port, motor_id, 56)
            return val if result == 0 else 0
        except Exception:
            return 0

    def write_position(self, motor_id: int, position: int) -> None:
        if not self._bus:
            return
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        try:
            ph.write2ByteTxRx(port, motor_id, 42, position)
        except Exception:
            pass

    def sync_read_positions(self, motor_ids: list[int]) -> dict[int, int]:
        if not self._bus:
            return {}
        result = {}
        for mid in motor_ids:
            result[mid] = self.read_position(mid)
        return result

    def sync_write_positions(self, positions: dict[int, int]) -> None:
        if not self._bus:
            return
        for mid, pos in positions.items():
            self.write_position(mid, pos)

    def enable_torque(self, motor_ids: list[int] | None = None) -> None:
        if not self._bus:
            return
        ids = motor_ids or self._motor_ids
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        for mid in ids:
            try:
                ph.write1ByteTxRx(port, mid, 40, 1)
            except Exception:
                pass

    def disable_torque(self, motor_ids: list[int] | None = None) -> None:
        if not self._bus:
            return
        ids = motor_ids or self._motor_ids
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        for mid in ids:
            try:
                ph.write1ByteTxRx(port, mid, 40, 0)
            except Exception:
                pass

    def read_voltage(self, motor_id: int) -> float:
        if not self._bus:
            return 0.0
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        try:
            val, result, _ = ph.read1ByteTxRx(port, motor_id, 62)
            return val / 10.0 if result == 0 else 0.0
        except Exception:
            return 0.0

    def read_temperature(self, motor_id: int) -> float:
        if not self._bus:
            return 0.0
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        try:
            val, result, _ = ph.read1ByteTxRx(port, motor_id, 63)
            return float(val) if result == 0 else 0.0
        except Exception:
            return 0.0

    def read_load(self, motor_id: int) -> float:
        if not self._bus:
            return 0.0
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        try:
            val, result, _ = ph.read2ByteTxRx(port, motor_id, 60)
            if result != 0:
                return 0.0
            magnitude = val & 0x3FF
            sign = (val >> 10) & 1
            load = magnitude / 10.0
            return -load if sign else load
        except Exception:
            return 0.0

    def read_current(self, motor_id: int) -> float:
        if not self._bus:
            return 0.0
        ph = self._bus.packet_handler
        port = self._bus.port_handler
        try:
            val, result, _ = ph.read2ByteTxRx(port, motor_id, 69)
            if result != 0:
                return 0.0
            magnitude = val & 0x7FFF
            sign = (val >> 15) & 1
            current_ma = magnitude * 6.5
            return -current_ma if sign else current_ma
        except Exception:
            return 0.0
