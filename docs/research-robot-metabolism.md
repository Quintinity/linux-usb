# Robot Metabolism: Energy Budget Management for armOS Citizens

**Research Date:** 2026-03-16
**Context:** armOS citizenry protocol — distributed autonomous robot agents on SO-101 arms with Feetech STS3215 servos, 12V 5A PSU, governed by Surface Pro 7 + Raspberry Pi 5.

---

## Executive Summary

armOS citizens currently have telemetry (voltage, current, temperature, load) but no energy **management**. They can see what is happening but cannot plan around it. This research covers six dimensions of "robot metabolism" — the bridge from passive observation to active power-aware behavior.

The core design principle: **Power is a first-class resource in the marketplace, just like capabilities and skills.** A citizen that cannot power a task should not bid on it.

---

## 1. Energy-Aware Robotics: How Robots Manage Power

### 1.1 The Power Decomposition Model

Research from ETH Zurich and MIT (2024-2025) converges on a three-component power model for robot arms:

```
P_total = P_mechanical + P_electrical_loss + P_overhead
```

- **P_mechanical** = torque x velocity (joint motion). Dominates during movement.
- **P_electrical_loss** = R/Kt^2 x torque^2 (resistive heating in windings). Dominates during static holds under load (your elbow_flex holding position against gravity).
- **P_overhead** = constant baseline for controllers, sensors, bus communication. For the SO-101, this is the CH340 USB-serial adapter + servo electronics idle draw.

A key finding: for collaborative robots, **overhead accounts for approximately 95% of active power consumption** when idle, meaning movement duration matters more than peak instantaneous power for total energy budgeting.

### 1.2 What This Means for SO-101

The SO-101 is **tethered** (12V 5A PSU), not battery-powered. The scarce resource is not stored energy but **instantaneous current capacity**. The PSU is a pipe, not a tank.

**Your specific constraint:**
- PSU delivers 5A max at 12V = 60W power envelope
- 6 servos idle at ~180mA each = 1.08A idle (13W)
- Single servo stall current: ~2.7A
- Elbow at 100% load + shoulder at 33% load already exceeds a 2A PSU (your old one)
- Even with the 5A PSU: two servos at stall simultaneously = 5.4A = brownout

This makes the SO-101 closer to a **brownout-prone FRC robot** than a battery-powered mobile robot. The FIRST Robotics roboRIO brownout protection scheme is directly applicable:

| Stage | Voltage Threshold | Action |
|-------|------------------|--------|
| Normal | >10V | Full operation |
| Warning | <10V, >8V | Log warning, reduce non-essential loads |
| Brownout | <8V, >6V | Disable non-critical servos, reduce speed |
| Critical | <6V | Emergency stop all servos (STS3215 min spec is 6V) |

### 1.3 Energy-Optimal Trajectory Planning

Research shows trajectory optimization reduces energy consumption by 15-30%:

- **Slower is cheaper**: P_electrical_loss scales with torque^2. Moving at 70% max speed can halve electrical losses.
- **Gravity-aware paths**: Planning paths that work *with* gravity rather than against it. For the SO-101, moving the elbow downward before extending outward.
- **Regenerative deceleration**: STS3215 servo drives support generator mode during deceleration. Energy from one axis can flow to another via the shared DC bus. This is free — already in the hardware.

---

## 2. Resource Allocation: CPU, Memory, Bandwidth Budgets

### 2.1 The Citizen Resource Model

A citizen running inference + teleop + telemetry simultaneously needs a resource budget beyond just power. Three scarce resources:

| Resource | Budget | Why It Matters |
|----------|--------|---------------|
| **CPU** | Per-task time slices | Pi 5 has 4 cores. Inference at 30fps can saturate 1 core. Teleop servo writes need <2ms latency. |
| **Bus bandwidth** | Serial port throughput | STS3215 bus at 1Mbaud. 6 servos x 7 register reads = 42 transactions per telemetry cycle. At 10Hz telemetry + 60Hz teleop write = bus contention. |
| **Memory** | Working set limits | Pi 5 has 8GB. ACT inference model + camera frames + telemetry history. |

### 2.2 Priority Hierarchy

Research on ROS 2 real-time scheduling (ROSGuard, 2025) and budget-based executors for Micro-ROS establishes a clean priority model:

**Critical (must never miss deadline):**
1. Safety checks (voltage, temperature, overcurrent) — 100Hz, <1ms
2. Emergency stop processing — interrupt-level
3. Servo position writes during teleop — 60Hz, <2ms

**High (degrades experience if missed):**
4. Telemetry collection — 10Hz, <10ms
5. Heartbeat broadcast — 0.5Hz, <5ms
6. Marketplace bid evaluation — event-driven, <50ms

**Best-effort (nice to have):**
7. Inference (ACT model) — 10-30Hz, 30-100ms
8. Dashboard updates — 2Hz
9. Genome persistence — every 60s

### 2.3 CPU Budget Implementation

The ROS 2 approach uses **callback groups with SCHED_FIFO priorities**. For armOS (which uses asyncio, not ROS 2), the equivalent is:

```python
# Priority-based task scheduling within a citizen
class ResourceBudget:
    """CPU time budget for a citizen's concurrent tasks."""

    def __init__(self, total_cpu_pct: float = 80.0):
        self.budgets = {
            "safety":     {"pct": 15.0, "period_ms": 10,   "priority": 0},
            "servo_io":   {"pct": 25.0, "period_ms": 16,   "priority": 1},
            "telemetry":  {"pct": 10.0, "period_ms": 100,  "priority": 2},
            "protocol":   {"pct": 10.0, "period_ms": 2000, "priority": 3},
            "inference":  {"pct": 20.0, "period_ms": 100,  "priority": 4},
            "dashboard":  {"pct": 5.0,  "period_ms": 500,  "priority": 5},
        }
```

### 2.4 Bus Bandwidth Budget

The STS3215 serial bus is half-duplex at 1Mbaud. Each register read takes approximately:
- 8 bytes instruction + 8 bytes response = 16 bytes x 10 bits = 160 bits
- At 1Mbaud = 0.16ms per transaction
- 42 transactions for full telemetry = 6.7ms
- At 10Hz telemetry = 67ms/sec of bus time consumed
- At 60Hz teleop writes (6 servos) = 360 transactions/sec = 57.6ms/sec

**Total bus utilization: ~125ms out of 1000ms = 12.5%**. This leaves headroom, but concurrent reads and writes will collide on the half-duplex bus. A bus arbiter is needed.

---

## 3. Metabolic Rate: Tracking Steady-State vs Burst Power

### 3.1 The Metabolism Metaphor

| Biological | Robot Equivalent | SO-101 Value |
|-----------|-----------------|--------------|
| Basal metabolic rate (BMR) | Idle power: all servos energized, holding position | ~1.1A @ 12V = 13W |
| Resting metabolic rate | Light activity: occasional small movements, telemetry active | ~1.5A @ 12V = 18W |
| Active metabolic rate | Task execution: pick-and-place, teleop following | ~2.5-3.5A @ 12V = 30-42W |
| Peak metabolic rate | Maximum burst: multi-servo fast movement against load | ~4.5A+ @ 12V = 54W+ |
| VO2 max | PSU current limit: 5A @ 12V = 60W | Hard ceiling |

### 3.2 Measuring Metabolic Rate from Telemetry

The STS3215 register at address 0x45 (Current Current, 2 bytes) gives per-servo current in units of 6.5mA. The register at 0x3E (Current Voltage, 1 byte) gives voltage in units of 0.1V.

**Instantaneous power per servo:**
```
P_servo = (register_0x3E / 10.0) * (register_0x45 * 6.5 / 1000.0)  # Watts
```

**Total arm power:**
```
P_arm = sum(P_servo[i] for i in range(6))
```

**Metabolic rate tracking** requires a sliding window:

```python
@dataclass
class MetabolicState:
    """Tracks power consumption over time windows."""

    # Instantaneous
    current_power_w: float = 0.0
    current_draw_a: float = 0.0

    # Sliding windows
    power_1s: float = 0.0     # 1-second average (burst detection)
    power_10s: float = 0.0    # 10-second average (task-level)
    power_60s: float = 0.0    # 1-minute average (metabolic rate)
    power_300s: float = 0.0   # 5-minute average (sustained load)

    # Peaks
    peak_power_w: float = 0.0
    peak_current_a: float = 0.0

    # Cumulative
    energy_consumed_wh: float = 0.0  # Watt-hours since boot
    uptime_s: float = 0.0

    # Classification
    metabolic_state: str = "idle"  # idle, resting, active, peak, critical
```

### 3.3 Metabolic State Classification

```python
def classify_metabolic_state(power_10s: float, psu_max_w: float = 60.0) -> str:
    ratio = power_10s / psu_max_w
    if ratio < 0.25:
        return "idle"       # <15W — servos energized, minimal movement
    elif ratio < 0.45:
        return "resting"    # 15-27W — light activity
    elif ratio < 0.70:
        return "active"     # 27-42W — normal task execution
    elif ratio < 0.85:
        return "peak"       # 42-51W — heavy load, approaching limit
    else:
        return "critical"   # >51W — at PSU limit, brownout risk
```

### 3.4 Predictive Power Estimation

Before starting a task, a citizen should estimate whether it can afford it:

```python
def estimate_task_power(task_type: str, params: dict) -> PowerEstimate:
    """Predict power requirements for a task before execution."""

    TASK_POWER_PROFILES = {
        "pick_and_place": {
            "peak_a": 3.5,      # Lifting with gripper
            "sustained_a": 2.0,  # Moving with object
            "duration_s": 8.0,
            "energy_wh": 0.06,
        },
        "teleop_follow": {
            "peak_a": 4.0,      # Fast tracking movements
            "sustained_a": 2.5,  # Average during teleop
            "duration_s": None,  # Continuous
            "energy_wh": None,
        },
        "wave_gesture": {
            "peak_a": 1.5,
            "sustained_a": 1.0,
            "duration_s": 3.0,
            "energy_wh": 0.01,
        },
        "hold_position": {
            "peak_a": 2.0,      # Depends on pose
            "sustained_a": 1.5,
            "duration_s": None,
            "energy_wh": None,
        },
    }
```

These profiles should be **learned from actual telemetry**, not just hardcoded. Each time a task completes, record actual power draw and update the profile via exponential moving average.

---

## 4. Fatigue from Energy: Beyond Temperature

### 4.1 The Three Fatigue Dimensions

Current `emotional.py` tracks temperature-based fatigue. But power-cycle fatigue has three distinct sources:

| Fatigue Type | Mechanism | STS3215 Impact | Timeframe |
|-------------|-----------|----------------|-----------|
| **Thermal** | Winding insulation degradation | Temp >65C triggers protection | Minutes to hours |
| **Mechanical** | Gear tooth wear, bearing degradation | Metal gears in STS3215 — 20,000+ hours at rated load | Thousands of hours |
| **Electrical** | Capacitor aging, solder joint fatigue from thermal cycling | Connector wear, bus adapter degradation | Months to years |

### 4.2 Servo Lifetime Model

Industrial servo MTBF is 20,000-30,000 working hours. The STS3215 is a hobby-grade servo with metal gears — expect the lower end. Critically, **lifetime scales inversely with load**:

```python
@dataclass
class ServoFatigueTracker:
    """Track cumulative wear on a single servo."""

    # Lifetime counters (persist in genome)
    total_operating_hours: float = 0.0
    total_high_load_hours: float = 0.0   # >70% load
    total_overload_events: int = 0        # Protection triggered
    total_thermal_cycles: int = 0         # >50C then <35C transitions
    total_stall_events: int = 0           # Current > 2A sustained >1s

    # Duty cycle tracking
    duty_cycle_1h: float = 0.0    # Fraction of last hour under load
    duty_cycle_24h: float = 0.0   # Fraction of last 24h under load

    # Estimated remaining life
    estimated_remaining_hours: float = 20000.0

    def update(self, load_pct: float, temp_c: float, current_ma: float, dt_s: float):
        self.total_operating_hours += dt_s / 3600

        # High load accelerates wear — each hour at >70% load = 3 hours of normal wear
        if abs(load_pct) > 70:
            self.total_high_load_hours += dt_s / 3600
            wear_multiplier = 3.0
        elif abs(load_pct) > 50:
            wear_multiplier = 1.5
        else:
            wear_multiplier = 1.0

        # Thermal cycling stress — temperature transitions degrade solder joints
        # and cause differential expansion in gear teeth
        # (tracked separately via threshold crossings)

        # Stall detection
        if abs(current_ma) > 2000 and abs(load_pct) > 90:
            self.total_stall_events += 1

        # Update remaining life estimate
        effective_hours = self.total_operating_hours + self.total_high_load_hours * 2.0
        self.estimated_remaining_hours = max(0, 20000 - effective_hours)
```

### 4.3 Duty Cycle Limits

The STS3215 datasheet specifies three IEC duty cycle types:
- **S1 (continuous)**: Constant load reaching thermal equilibrium. STS3215 tested stable at 48C under 15 kg-cm for >1 hour.
- **S2 (short-time)**: Load followed by full cooling. This is pick-and-place.
- **S3 (intermittent)**: Frequent start-stop without full cooling. This is teleop.

**S3 is the most destructive** because the servo never fully cools. Each incomplete cooling cycle adds stress. Recommendation: after 30 minutes of continuous teleop, enforce a 5-minute "rest" period where the citizen reports itself as fatigued and refuses high-load tasks.

### 4.4 Integration with Emotional State

Extend `compute_emotional_state()` to include power-based fatigue:

```python
def compute_fatigue(
    max_temperature: float,
    uptime_hours: float,
    warning_count: int,
    # NEW: power-based inputs
    duty_cycle_1h: float = 0.0,
    overload_events: int = 0,
    metabolic_state: str = "idle",
    voltage_sag_count: int = 0,
) -> float:
    temp_factor = max(0.0, (max_temperature - 30) / 35)
    uptime_factor = min(1.0, uptime_hours / 8.0)
    warning_factor = min(1.0, warning_count / 5.0)

    # Power-based fatigue components
    duty_factor = duty_cycle_1h  # 0-1, how much of last hour was under load
    overload_factor = min(1.0, overload_events / 3.0)  # 3 overloads = max fatigue
    sag_factor = min(1.0, voltage_sag_count / 5.0)  # Voltage sags indicate PSU stress

    fatigue = min(1.0, (
        temp_factor * 0.25 +
        uptime_factor * 0.20 +
        warning_factor * 0.10 +
        duty_factor * 0.25 +
        overload_factor * 0.10 +
        sag_factor * 0.10
    ))
    return fatigue
```

---

## 5. Power-Aware Task Scheduling

### 5.1 Power as a Marketplace Constraint

The current `TaskMarketplace` evaluates bids on capability, availability, and health. Power must become a fourth dimension:

```python
# Extended bid scoring with power budget
METABOLISM_WEIGHTS = {
    "capability": 0.30,
    "availability": 0.25,
    "health": 0.20,
    "power_headroom": 0.25,  # NEW
}

def compute_power_aware_bid_score(
    skill_level: int,
    current_load: float,
    health: float,
    fatigue: float,
    # NEW: power parameters
    available_current_a: float,    # PSU_max - current_draw
    task_required_current_a: float,
    metabolic_state: str,
) -> float:
    """Bid score that accounts for power headroom."""

    # Base capability/availability/health score (existing)
    w = METABOLISM_WEIGHTS
    skill_norm = min(skill_level, 10) / 10.0
    avail = max(0.0, 1.0 - current_load)
    h = max(0.0, min(1.0, health))

    # Power headroom: can I actually power this task?
    if available_current_a < task_required_current_a:
        return 0.0  # Cannot bid — insufficient power

    power_ratio = available_current_a / max(task_required_current_a, 0.1)
    power_score = min(1.0, power_ratio - 1.0)  # 0 at exact fit, 1 at 2x headroom

    # Metabolic penalty: citizens already at peak should not take more work
    metabolic_penalty = {
        "idle": 0.0,
        "resting": 0.0,
        "active": 0.1,
        "peak": 0.4,
        "critical": 1.0,
    }.get(metabolic_state, 0.0)

    base = (w["capability"] * skill_norm +
            w["availability"] * avail +
            w["health"] * h +
            w["power_headroom"] * power_score)

    fatigue_modifier = 1.0 - 0.3 * max(0.0, min(1.0, fatigue))
    metabolic_modifier = 1.0 - metabolic_penalty

    return base * fatigue_modifier * metabolic_modifier
```

### 5.2 Multi-Arm Power Planning

With two arms (leader + follower) on the same PSU, or future multi-arm setups:

```
PSU capacity: 5A
Arm 1 (follower) current task: teleop_follow @ 2.5A sustained
Arm 2 (proposed task): pick_and_place @ 3.5A peak

Total peak: 6.0A > 5.0A limit
Decision: REJECT bid or DEFER until Arm 1 finishes
```

This is a **power-aware admission control** problem. The governor must maintain a global power ledger:

```python
class PowerLedger:
    """Tracks power allocation across all citizens sharing a PSU."""

    def __init__(self, psu_max_a: float = 5.0, psu_voltage: float = 12.0):
        self.psu_max_a = psu_max_a
        self.psu_voltage = psu_voltage
        self.allocations: dict[str, float] = {}  # citizen_id -> reserved amps

    def can_allocate(self, citizen_id: str, required_a: float) -> bool:
        total_committed = sum(self.allocations.values())
        available = self.psu_max_a - total_committed
        # Keep 0.5A safety margin
        return required_a <= (available - 0.5)

    def allocate(self, citizen_id: str, amps: float) -> bool:
        if self.can_allocate(citizen_id, amps):
            self.allocations[citizen_id] = amps
            return True
        return False

    def release(self, citizen_id: str):
        self.allocations.pop(citizen_id, None)

    def utilization(self) -> float:
        return sum(self.allocations.values()) / self.psu_max_a
```

### 5.3 Task Power Requirements in Task Definition

Extend the `Task` dataclass:

```python
@dataclass
class Task:
    # ... existing fields ...

    # Power requirements (NEW)
    estimated_peak_current_a: float = 0.0
    estimated_sustained_current_a: float = 0.0
    estimated_duration_s: float = 0.0
    power_priority: str = "normal"  # "critical", "normal", "low"
```

### 5.4 Brownout Response Protocol

When voltage sag is detected, the citizen must respond in stages:

```python
class BrownoutProtocol:
    """Staged response to PSU current limiting / voltage collapse."""

    STAGE_NORMAL = "normal"       # >10V: full operation
    STAGE_WARNING = "warning"     # 8-10V: log, reduce speed
    STAGE_BROWNOUT = "brownout"   # 6-8V: disable non-critical, slow everything
    STAGE_CRITICAL = "critical"   # <6V: emergency stop, torque off

    def evaluate(self, min_voltage: float) -> str:
        if min_voltage >= 10.0:
            return self.STAGE_NORMAL
        elif min_voltage >= 8.0:
            return self.STAGE_WARNING
        elif min_voltage >= 6.0:
            return self.STAGE_BROWNOUT
        else:
            return self.STAGE_CRITICAL

    def respond(self, stage: str, citizen):
        if stage == self.STAGE_WARNING:
            # Reduce servo speed limits by 50%
            # Broadcast mycelium warning to neighbors
            # Log event for fatigue tracking
            pass
        elif stage == self.STAGE_BROWNOUT:
            # Disable gripper servo (lowest priority)
            # Reduce all torque limits to 50%
            # Reject all new task bids
            # Broadcast ALERT to governor
            pass
        elif stage == self.STAGE_CRITICAL:
            # Disable ALL servo torque immediately
            # Broadcast EMERGENCY_STOP
            # This is Article 3: Self-Preservation
            pass
```

---

## 6. Practical Implementation: Building on Existing Telemetry

### 6.1 STS3215 Register Map for Metabolism

Everything needed for metabolism tracking is already readable from the STS3215 registers. Here is the complete set of relevant registers:

**EEPROM (configurable, persist across power cycles):**

| Address | Name | Default | Unit | Purpose |
|---------|------|---------|------|---------|
| 0x0D | Max Temperature | 70 | Celsius | Protection threshold |
| 0x0E | Max Input Voltage | 80 | 0.1V (=8.0V) | Overvoltage protection |
| 0x0F | Min Input Voltage | 40 | 0.1V (=4.0V) | Undervoltage protection |
| 0x10 | Max Torque | 1000 | 0.1% (=100%) | Torque ceiling |
| 0x13 | Unloading Conditions | varies | Bitmask | Bit0=Voltage, Bit1=Sensor, Bit2=Temp, Bit3=Current, Bit4=Angle, Bit5=Overload |
| 0x1C | Protection Current | varies | 6.5mA units | Max current before protection (max 500 = 3250mA) |
| 0x22 | Protective Torque | varies | Percent | Output torque after overload trips (e.g., 20 = 20%) |
| 0x23 | Protection Time | varies | 10ms units | Duration above overload threshold before trip (max 254 = 2540ms) |
| 0x24 | Overload Torque | varies | Percent | Load threshold that starts the overload timer (e.g., 80 = 80%) |
| 0x26 | Overcurrent Prot. Time | varies | 10ms units | Duration above protection current before trip |

**RAM (read-only feedback, real-time):**

| Address | Name | Length | Unit | Your Code |
|---------|------|--------|------|-----------|
| 0x38 | Current Position | 2 bytes | Steps | REG_PRESENT_POSITION = 56 |
| 0x3A | Current Speed | 2 bytes | Steps/s (sign-magnitude bit 15) | REG_PRESENT_SPEED = 58 |
| 0x3C | Current Load | 2 bytes | 0.1% (sign-magnitude bit 10) | REG_PRESENT_LOAD = 60 |
| 0x3E | Current Voltage | 1 byte | 0.1V | REG_PRESENT_VOLTAGE = 62 |
| 0x3F | Current Temperature | 1 byte | Celsius | REG_PRESENT_TEMPERATURE = 63 |
| 0x41 | Servo Status | 1 byte | Bitmask (errors) | REG_STATUS = 65 |
| 0x45 | Current Current | 2 bytes | 6.5mA (sign-magnitude bit 15) | REG_PRESENT_CURRENT = 69 |

### 6.2 What to Add to telemetry.py

The current `telemetry.py` reads all the right registers. The metabolism layer wraps it:

```python
# metabolism.py — new file

@dataclass
class PowerSnapshot:
    """Instantaneous power state derived from telemetry."""
    total_current_a: float
    min_voltage_v: float
    total_power_w: float
    per_servo_power_w: dict[str, float]
    brownout_stage: str
    metabolic_state: str
    timestamp: float

def compute_power_snapshot(telemetry: ArmTelemetry) -> PowerSnapshot:
    """Derive power state from raw telemetry."""
    per_servo = {}
    for name, snap in telemetry.snapshots.items():
        if not math.isnan(snap.voltage) and not math.isnan(snap.current_ma):
            per_servo[name] = snap.voltage * abs(snap.current_ma) / 1000.0
        else:
            per_servo[name] = 0.0

    total_power = sum(per_servo.values())
    total_current = telemetry.total_current_ma / 1000.0 if not math.isnan(telemetry.total_current_ma) else 0.0
    min_v = telemetry.min_voltage if not math.isnan(telemetry.min_voltage) else 12.0

    brownout = BrownoutProtocol().evaluate(min_v)
    metabolic = classify_metabolic_state(total_power)

    return PowerSnapshot(
        total_current_a=total_current,
        min_voltage_v=min_v,
        total_power_w=total_power,
        per_servo_power_w=per_servo,
        brownout_stage=brownout,
        metabolic_state=metabolic,
        timestamp=telemetry.timestamp,
    )
```

### 6.3 Voltage Sag Detection

Voltage sag is the canary in the coal mine — it signals that the PSU has hit its current limit before the servos report errors. Detection is simple:

```python
class VoltageSagDetector:
    """Detect PSU current limiting from voltage telemetry."""

    def __init__(self, baseline_v: float = 12.0, sag_threshold_v: float = 1.0):
        self.baseline_v = baseline_v
        self.sag_threshold_v = sag_threshold_v
        self.history: list[float] = []  # last N voltage readings
        self.sag_events: int = 0
        self.in_sag: bool = False

    def update(self, min_voltage: float) -> bool:
        """Returns True if a new sag event started."""
        self.history.append(min_voltage)
        if len(self.history) > 100:
            self.history.pop(0)

        # Baseline is rolling max of recent readings (tracks actual PSU output)
        if len(self.history) > 10:
            self.baseline_v = max(self.history[-10:])

        sag = self.baseline_v - min_voltage
        new_sag = False

        if sag >= self.sag_threshold_v and not self.in_sag:
            self.in_sag = True
            self.sag_events += 1
            new_sag = True
        elif sag < self.sag_threshold_v * 0.5:  # Hysteresis
            self.in_sag = False

        return new_sag
```

The key insight from your own data: **all servo voltages collapse simultaneously from ~12V to ~5V** during overload. This is not per-servo — it is the PSU hitting its wall. A single voltage reading from any servo is sufficient to detect this.

### 6.4 Duty Cycle Tracking

```python
class DutyCycleTracker:
    """Track what fraction of time a servo has been under load."""

    def __init__(self, load_threshold_pct: float = 30.0):
        self.load_threshold = load_threshold_pct
        self.window_1h: collections.deque = collections.deque(maxlen=36000)  # 10Hz for 1h
        self.window_24h_summary: list[float] = []  # hourly duty cycle averages

    def update(self, load_pct: float):
        under_load = 1.0 if abs(load_pct) > self.load_threshold else 0.0
        self.window_1h.append(under_load)

    @property
    def duty_cycle_1h(self) -> float:
        if not self.window_1h:
            return 0.0
        return sum(self.window_1h) / len(self.window_1h)

    def should_rest(self) -> bool:
        """Recommend rest if duty cycle too high for too long."""
        return self.duty_cycle_1h > 0.7  # >70% of last hour under load
```

### 6.5 Genome Extensions for Metabolism

Add to `CitizenGenome`:

```python
# In genome.py, extend CitizenGenome dataclass:
metabolism: dict[str, Any] = field(default_factory=lambda: {
    "total_operating_hours": 0.0,
    "total_high_load_hours": 0.0,
    "total_overload_events": 0,
    "total_voltage_sag_events": 0,
    "total_thermal_cycles": 0,
    "total_energy_consumed_wh": 0.0,
    "task_power_profiles": {},          # Learned power profiles per task type
    "per_servo_fatigue": {},            # Per-servo wear tracking
    "estimated_remaining_life_hours": 20000.0,
})
```

### 6.6 Constitution Extensions

Add new laws for power governance:

```python
# New constitutional laws
Law(
    id="power_budget",
    description="Maximum sustained current draw per citizen.",
    params={"max_sustained_a": 4.0, "max_peak_a": 4.5, "safety_margin_a": 0.5},
),
Law(
    id="brownout_thresholds",
    description="Voltage thresholds for staged brownout response.",
    params={"warning_v": 10.0, "brownout_v": 8.0, "critical_v": 6.0},
),
Law(
    id="duty_cycle_limit",
    description="Maximum duty cycle before mandatory rest.",
    params={"max_duty_1h": 0.7, "rest_duration_s": 300},
),
Law(
    id="metabolic_reporting",
    description="Citizens include metabolic state in heartbeat.",
    params={"enabled": True, "report_interval_s": 10},
),
```

---

## 7. Implementation Roadmap

### Phase 1: Passive Metabolism (observe and report)
- Add `PowerSnapshot` computation to telemetry cycle
- Add `MetabolicState` to heartbeat body
- Add `VoltageSagDetector` — count and log sag events
- Add `DutyCycleTracker` — per-servo duty cycle tracking
- Extend genome with metabolism counters
- Dashboard shows metabolic state, power headroom, voltage graph

### Phase 2: Reactive Metabolism (respond to power events)
- Implement `BrownoutProtocol` — staged response to voltage sag
- Add duty cycle fatigue to `compute_emotional_state()`
- Citizens in "peak" or "critical" metabolic state refuse new task bids
- Governor receives metabolic REPORT messages and factors into scheduling

### Phase 3: Predictive Metabolism (plan around power)
- Learn task power profiles from telemetry history
- `PowerLedger` for multi-citizen PSU-aware admission control
- Power headroom in marketplace bid scoring
- Task estimated power in `Task` dataclass
- Trajectory optimization: slower movements when power headroom is low

### Phase 4: Adaptive Metabolism (self-optimize)
- Automatic servo speed/torque reduction when metabolic state is "peak"
- Energy-optimal path planning for pick-and-place
- Predictive rest scheduling: "I have been at 60% duty cycle for 45 minutes, I should rest in 15 minutes"
- Fleet-level power balancing: shift tasks from power-stressed citizens to idle ones

---

## 8. Key Design Decisions

1. **Power is a marketplace resource, not just a safety check.** The current `check_safety()` function in `telemetry.py` is reactive (alarm after violation). Metabolism is proactive (plan to stay within budget).

2. **Voltage sag is the primary signal**, not current. The STS3215 current registers update slowly and per-servo. Voltage collapses system-wide and is visible instantly from any servo.

3. **The PSU is a shared resource.** Multiple citizens on the same PSU must coordinate. The governor must maintain a global power ledger.

4. **Fatigue compounds.** Temperature fatigue + duty cycle fatigue + overload event fatigue are additive. A citizen that is hot AND has been working hard AND had voltage sags is much more fatigued than any single factor suggests.

5. **Metabolic state goes in the heartbeat.** Every citizen broadcasts its metabolic state. The governor and neighbors can see who is stressed before tasks are assigned.

6. **Task power profiles are learned, not hardcoded.** Initial estimates are provided, but actual telemetry during task execution updates the profile. Over time, the citizen learns exactly how much power each task type costs.

---

## Sources

- [Power solutions for autonomous mobile robots: A survey](https://www.sciencedirect.com/science/article/abs/pii/S0921889022001749)
- [Optimization of energy consumption in industrial robots, a review](https://www.sciencedirect.com/science/article/pii/S2667241323000174)
- [Energy Consumption in Robotics: A Simplified Modeling Approach](https://arxiv.org/html/2411.03194v1)
- [Trajectory Optimization of Energy Consumption and Expected Service Life of a Robotic System](https://ieeexplore.ieee.org/document/9517539/)
- [On-Device CPU Scheduling for Robot Systems (UIUC)](https://radhikam.web.illinois.edu/catan.pdf)
- [ROSGuard: Bandwidth Regulation for ROS2-based Applications](https://arxiv.org/html/2506.04640)
- [Budget-based Real-time Executor for Micro-ROS](https://arxiv.org/pdf/2105.05590)
- [Priority-Driven Real-Time Scheduling in ROS 2](https://noaa99.github.io/pdf/rage2022_ros2.pdf)
- [roboRIO Brownout Protection Scheme (FIRST Robotics)](https://docs.wpilib.org/en/stable/docs/software/roborio-info/roborio-brownouts.html)
- [Servo Motor Lifespan (Advanced Motion Controls)](https://www.a-m-c.com/servomotor-lifespan/)
- [Testing of Feetech STS3215 Servomotor (Robo9)](https://robonine.com/testing-of-feetech-sts3215-servomotor-backlash-repeatability-and-torque/)
- [ST3215 Servo Register Map (Waveshare)](https://www.waveshare.com/wiki/ST3215_Servo)
- [ST3215 Memory Register Map (Excel)](https://files.waveshare.com/upload/2/27/ST3215%20memory%20register%20map-EN.xls)
- [Dynamic Power Management on a Mobile Robot](https://www.researchgate.net/publication/358099060_Dynamic_Power_Management_on_a_Mobile_Robot)
- [Energy-aware multi-robot task scheduling (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0921889024002823)
- [Energy Budgets (Adafruit)](https://learn.adafruit.com/energy-budgets/overview)
- [The Battery Bottleneck Holding Robotics Back](https://www.roboticstomorrow.com/story/2025/09/the-battery-bottleneck-holding-robotics-back/25483/)
- [Improving Performance with Current Limits (CTR Electronics)](https://v6.docs.ctr-electronics.com/en/stable/docs/hardware-reference/talonfx/improving-performance-with-current-limits.html)
- [STS3215 Datasheet (Feetech/Core Electronics)](https://core-electronics.com.au/attachments/uploads/sts3215-smart-servo-datasheet-translated.pdf)
