"""Servo telemetry for Feetech STS3215 motors on the SO-101 arm.

Reads voltage, current, load, temperature, position, velocity, and status
from all 6 servos and packages results into REPORT messages for the
citizenry protocol.
"""

import math
import time
from dataclasses import dataclass, field, asdict


# ── Motor Map ────────────────────────────────────────────────────────────────

MOTOR_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]
MOTOR_IDS = {name: i + 1 for i, name in enumerate(MOTOR_NAMES)}

# ── STS3215 Register Addresses ──────────────────────────────────────────────

REG_PRESENT_POSITION = 56      # 2 bytes
REG_PRESENT_SPEED = 58         # 2 bytes, sign-magnitude bit 15
REG_PRESENT_LOAD = 60          # 2 bytes, sign-magnitude bit 10
REG_PRESENT_VOLTAGE = 62       # 1 byte, value / 10 = volts
REG_PRESENT_TEMPERATURE = 63   # 1 byte, celsius
REG_STATUS = 65                # 1 byte, 5 error flag bits
REG_PRESENT_CURRENT = 69       # 2 bytes, sign-magnitude bit 15, value * 6.5 = mA

# ── Default Safety Limits ───────────────────────────────────────────────────

DEFAULT_LIMITS = {
    "voltage_min": 6.0,          # Volts
    "temperature_max": 65.0,     # Celsius
    "total_current_max": 4000.0, # mA
    "load_max_pct": 90.0,        # Percent
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _decode_sign_magnitude(val: int, sign_bit: int) -> int:
    """Decode a sign-magnitude value where sign_bit is the bit index of the sign."""
    mask = (1 << sign_bit) - 1
    magnitude = val & mask
    sign = (val >> sign_bit) & 1
    return -magnitude if sign else magnitude


# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class ServoSnapshot:
    """Telemetry snapshot from a single STS3215 servo."""
    motor_name: str
    voltage: float          # Volts
    current_ma: float       # Milliamps
    load_pct: float         # Percent (signed)
    temperature_c: float    # Celsius
    position: int           # Raw position value
    velocity: int           # Raw velocity (signed)
    status: int             # Error flag byte
    timestamp: float = field(default_factory=time.time)


@dataclass
class ArmTelemetry:
    """Aggregated telemetry for all 6 motors on an SO-101 arm."""
    snapshots: dict[str, ServoSnapshot]
    total_current_ma: float
    min_voltage: float
    max_temperature: float
    max_load_pct: float
    has_errors: bool
    timestamp: float = field(default_factory=time.time)


# ── Core Functions ──────────────────────────────────────────────────────────

def read_telemetry(bus) -> ArmTelemetry:
    """Read telemetry from all 6 SO-101 motors via raw register reads.

    Args:
        bus: A FeetechMotorsBus instance with port already opened.
             Uses bus.packet_handler and bus.port_handler for raw reads.

    Returns:
        ArmTelemetry with snapshots for all motors and summary fields.
    """
    ph = bus.packet_handler
    port = bus.port_handler
    now = time.time()
    snapshots: dict[str, ServoSnapshot] = {}

    for name in MOTOR_NAMES:
        mid = MOTOR_IDS[name]

        voltage = math.nan
        current_ma = math.nan
        load_pct = math.nan
        temperature_c = math.nan
        position = -1
        velocity = -1
        status = -1

        try:
            voltage_raw, c1, _ = ph.read1ByteTxRx(port, mid, REG_PRESENT_VOLTAGE)
            if c1 == 0:
                voltage = voltage_raw / 10.0
        except Exception:
            pass

        try:
            current_raw, c2, _ = ph.read2ByteTxRx(port, mid, REG_PRESENT_CURRENT)
            if c2 == 0:
                magnitude = current_raw & 0x7FFF
                sign = (current_raw >> 15) & 1
                current_ma = magnitude * 6.5
                if sign:
                    current_ma = -current_ma
        except Exception:
            pass

        try:
            load_raw, c3, _ = ph.read2ByteTxRx(port, mid, REG_PRESENT_LOAD)
            if c3 == 0:
                load_pct = _decode_sign_magnitude(load_raw, 10) / 10.0
        except Exception:
            pass

        try:
            temp_raw, c4, _ = ph.read1ByteTxRx(port, mid, REG_PRESENT_TEMPERATURE)
            if c4 == 0:
                temperature_c = float(temp_raw)
        except Exception:
            pass

        try:
            pos_raw, c5, _ = ph.read2ByteTxRx(port, mid, REG_PRESENT_POSITION)
            if c5 == 0:
                position = pos_raw
        except Exception:
            pass

        try:
            vel_raw, c6, _ = ph.read2ByteTxRx(port, mid, REG_PRESENT_SPEED)
            if c6 == 0:
                velocity = _decode_sign_magnitude(vel_raw, 15)
        except Exception:
            pass

        try:
            status_raw, c7, _ = ph.read1ByteTxRx(port, mid, REG_STATUS)
            if c7 == 0:
                status = status_raw
        except Exception:
            pass

        snapshots[name] = ServoSnapshot(
            motor_name=name,
            voltage=voltage,
            current_ma=current_ma,
            load_pct=load_pct,
            temperature_c=temperature_c,
            position=position,
            velocity=velocity,
            status=status,
            timestamp=now,
        )

    # Compute summary fields, ignoring NaN / error values
    currents = [
        abs(s.current_ma) for s in snapshots.values()
        if not math.isnan(s.current_ma)
    ]
    voltages = [
        s.voltage for s in snapshots.values()
        if not math.isnan(s.voltage)
    ]
    temperatures = [
        s.temperature_c for s in snapshots.values()
        if not math.isnan(s.temperature_c)
    ]
    loads = [
        abs(s.load_pct) for s in snapshots.values()
        if not math.isnan(s.load_pct)
    ]

    return ArmTelemetry(
        snapshots=snapshots,
        total_current_ma=sum(currents) if currents else math.nan,
        min_voltage=min(voltages) if voltages else math.nan,
        max_temperature=max(temperatures) if temperatures else math.nan,
        max_load_pct=max(loads) if loads else math.nan,
        has_errors=any(s.status > 0 for s in snapshots.values()),
        timestamp=now,
    )


def telemetry_to_report(telemetry: ArmTelemetry) -> dict:
    """Convert ArmTelemetry into a JSON-safe dict for a REPORT message body.

    Returns:
        Dict with type="telemetry", summary fields, and per-motor snapshots.
    """
    motors = {}
    for name, snap in telemetry.snapshots.items():
        motors[name] = {
            "voltage": _nan_safe(snap.voltage),
            "current_ma": _nan_safe(snap.current_ma),
            "load_pct": _nan_safe(snap.load_pct),
            "temperature_c": _nan_safe(snap.temperature_c),
            "position": snap.position,
            "velocity": snap.velocity,
            "status": snap.status,
            "timestamp": snap.timestamp,
        }

    return {
        "type": "telemetry",
        "timestamp": telemetry.timestamp,
        "total_current_ma": _nan_safe(telemetry.total_current_ma),
        "min_voltage": _nan_safe(telemetry.min_voltage),
        "max_temperature": _nan_safe(telemetry.max_temperature),
        "max_load_pct": _nan_safe(telemetry.max_load_pct),
        "has_errors": telemetry.has_errors,
        "motors": motors,
    }


def check_safety(
    telemetry: ArmTelemetry,
    limits: dict | None = None,
) -> list[str]:
    """Check telemetry against safety limits.

    Args:
        telemetry: Current arm telemetry reading.
        limits: Dict with keys voltage_min, temperature_max,
                total_current_max, load_max_pct. Uses DEFAULT_LIMITS
                for any missing keys.

    Returns:
        List of violation description strings. Empty means all clear.
    """
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    violations: list[str] = []

    # Voltage check — per motor
    for name, snap in telemetry.snapshots.items():
        if not math.isnan(snap.voltage) and snap.voltage < lim["voltage_min"]:
            violations.append(
                f"{name}: voltage {snap.voltage:.1f}V < {lim['voltage_min']:.1f}V minimum"
            )

    # Temperature check — per motor
    for name, snap in telemetry.snapshots.items():
        if not math.isnan(snap.temperature_c) and snap.temperature_c > lim["temperature_max"]:
            violations.append(
                f"{name}: temperature {snap.temperature_c:.0f}C > {lim['temperature_max']:.0f}C maximum"
            )

    # Total current check
    if not math.isnan(telemetry.total_current_ma) and telemetry.total_current_ma > lim["total_current_max"]:
        violations.append(
            f"total current {telemetry.total_current_ma:.0f}mA > {lim['total_current_max']:.0f}mA maximum"
        )

    # Load check — per motor
    for name, snap in telemetry.snapshots.items():
        if not math.isnan(snap.load_pct) and abs(snap.load_pct) > lim["load_max_pct"]:
            violations.append(
                f"{name}: load {abs(snap.load_pct):.1f}% > {lim['load_max_pct']:.1f}% maximum"
            )

    return violations


# ── Internal Helpers ────────────────────────────────────────────────────────

def _nan_safe(value: float) -> float | None:
    """Convert NaN to None for JSON serialization."""
    if math.isnan(value):
        return None
    return value
