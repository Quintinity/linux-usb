"""Metabolism — power/energy budget management.

Tracks power consumption, manages PSU current limits, implements brownout
protection, and provides power-aware task scheduling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class MetabolicLevel(Enum):
    IDLE = "idle"           # ~13W, no movement
    RESTING = "resting"     # ~18W, heartbeat + telemetry only
    ACTIVE = "active"       # ~30-42W, executing tasks
    PEAK = "peak"           # ~54W+, heavy manipulation


class BrownoutStage(Enum):
    NORMAL = "normal"       # > 10V
    CAUTION = "caution"     # 8-10V
    CRITICAL = "critical"   # 6-8V
    EMERGENCY = "emergency" # < 6V


BROWNOUT_THRESHOLDS = {
    BrownoutStage.NORMAL: 10.0,
    BrownoutStage.CAUTION: 8.0,
    BrownoutStage.CRITICAL: 6.0,
    BrownoutStage.EMERGENCY: 0.0,
}


@dataclass
class PowerReading:
    """A single power measurement."""
    voltage: float = 0.0
    current_ma: float = 0.0
    power_w: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetabolicState:
    """Current metabolic state of a citizen."""
    level: MetabolicLevel = MetabolicLevel.IDLE
    brownout_stage: BrownoutStage = BrownoutStage.NORMAL
    instant_power_w: float = 0.0
    avg_power_1s: float = 0.0
    avg_power_10s: float = 0.0
    avg_power_60s: float = 0.0
    energy_wh: float = 0.0          # Cumulative energy since boot
    peak_current_ma: float = 0.0
    min_voltage: float = 12.0
    psu_headroom_pct: float = 100.0  # % of PSU capacity remaining

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "brownout": self.brownout_stage.value,
            "power_w": round(self.instant_power_w, 1),
            "avg_1s": round(self.avg_power_1s, 1),
            "energy_wh": round(self.energy_wh, 3),
            "headroom_pct": round(self.psu_headroom_pct, 0),
        }


@dataclass
class ServoFatigue:
    """Lifetime fatigue tracking for a servo."""
    motor_name: str
    total_cycles: int = 0
    total_energy_j: float = 0.0
    max_temperature_ever: float = 0.0
    overload_events: int = 0
    estimated_life_pct: float = 100.0  # 100% = new, 0% = end of life

    def record_cycle(self, load_pct: float, temperature: float, duration_s: float):
        self.total_cycles += 1
        self.total_energy_j += abs(load_pct) * duration_s * 0.01  # Rough estimate
        self.max_temperature_ever = max(self.max_temperature_ever, temperature)
        if load_pct > 80:
            self.overload_events += 1
        # Rough life estimate: 20,000hr MTBF at rated load
        base_hours = 20000
        load_factor = max(0.1, abs(load_pct) / 50.0)  # Higher load = faster wear
        self.estimated_life_pct = max(0.0,
            100.0 - (self.total_cycles / (base_hours * 3600 / load_factor)) * 100
        )


class MetabolismTracker:
    """Tracks power consumption and manages energy budget."""

    def __init__(self, psu_voltage: float = 12.0, psu_max_current_a: float = 5.0):
        self.psu_voltage = psu_voltage
        self.psu_max_current_a = psu_max_current_a
        self.psu_max_power_w = psu_voltage * psu_max_current_a

        self.state = MetabolicState()
        self.servo_fatigue: dict[str, ServoFatigue] = {}

        self._readings_1s: deque[PowerReading] = deque(maxlen=10)   # ~10Hz
        self._readings_10s: deque[PowerReading] = deque(maxlen=100)
        self._readings_60s: deque[PowerReading] = deque(maxlen=600)
        self._boot_time = time.time()

    def update(self, voltage: float, total_current_ma: float):
        """Update metabolic state with new telemetry."""
        now = time.time()
        power = voltage * (total_current_ma / 1000.0)
        reading = PowerReading(voltage=voltage, current_ma=total_current_ma, power_w=power, timestamp=now)

        self._readings_1s.append(reading)
        self._readings_10s.append(reading)
        self._readings_60s.append(reading)

        # Update state
        self.state.instant_power_w = power
        self.state.avg_power_1s = self._avg_power(self._readings_1s)
        self.state.avg_power_10s = self._avg_power(self._readings_10s)
        self.state.avg_power_60s = self._avg_power(self._readings_60s)
        self.state.peak_current_ma = max(self.state.peak_current_ma, total_current_ma)
        self.state.min_voltage = min(self.state.min_voltage, voltage)

        # Energy accumulation
        elapsed = now - self._boot_time
        if elapsed > 0:
            self.state.energy_wh = self.state.avg_power_60s * (elapsed / 3600)

        # PSU headroom
        current_a = total_current_ma / 1000.0
        self.state.psu_headroom_pct = max(0, (1.0 - current_a / self.psu_max_current_a) * 100)

        # Metabolic level
        if power < 15:
            self.state.level = MetabolicLevel.IDLE
        elif power < 25:
            self.state.level = MetabolicLevel.RESTING
        elif power < 45:
            self.state.level = MetabolicLevel.ACTIVE
        else:
            self.state.level = MetabolicLevel.PEAK

        # Brownout stage
        if voltage >= 10.0:
            self.state.brownout_stage = BrownoutStage.NORMAL
        elif voltage >= 8.0:
            self.state.brownout_stage = BrownoutStage.CAUTION
        elif voltage >= 6.0:
            self.state.brownout_stage = BrownoutStage.CRITICAL
        else:
            self.state.brownout_stage = BrownoutStage.EMERGENCY

    def can_power_task(self, estimated_power_w: float) -> bool:
        """Check if there's enough PSU headroom for a task."""
        available = self.psu_max_power_w - self.state.avg_power_1s
        return estimated_power_w < available * 0.8  # 20% safety margin

    def record_servo_cycle(self, motor_name: str, load_pct: float, temperature: float, duration_s: float):
        if motor_name not in self.servo_fatigue:
            self.servo_fatigue[motor_name] = ServoFatigue(motor_name=motor_name)
        self.servo_fatigue[motor_name].record_cycle(load_pct, temperature, duration_s)

    def _avg_power(self, readings: deque) -> float:
        if not readings:
            return 0.0
        return sum(r.power_w for r in readings) / len(readings)
