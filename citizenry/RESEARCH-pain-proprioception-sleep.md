# Robot Pain, Proprioception, and Sleep — Research & Design Document

Deep research into three biological analogs for autonomous robot agents in the armOS Citizenry protocol: nociception (pain), proprioception (body awareness), and sleep (maintenance consolidation).

---

## 1. Robot Pain — Motivational Damage Signal

### How biological pain works

Pain is NOT the same as fault detection. Fault detection says "something is wrong." Pain says "this HURTS, remember it, and never do that again." The critical distinction:

| System | Purpose | Temporal scope | Behavioral effect |
|--------|---------|----------------|-------------------|
| Fault detection (immune memory) | Detect and mitigate known failure modes | Present | Apply known mitigation |
| Warning (mycelium) | Propagate safety signals to neighbors | Present | Reduce duty cycle |
| **Pain** | Create aversive memory that changes future behavior | **Past + Future** | **Avoid the situation that caused it** |

Biological nociception has four components that map to robot implementation:

1. **Transduction** — sensory receptors convert harmful stimuli into electrical signals. Three receptor types:
   - Mechanical nociceptors (pressure/force) -> servo load/current spikes
   - Thermal nociceptors (heat/cold) -> temperature readings
   - Polymodal nociceptors (multiple stimuli) -> compound conditions (current + temp + position error)

2. **Transmission** — signals travel via two pathways:
   - A-delta fibers (fast, sharp, localized) -> reflex engine direct action (<10ms)
   - C-fibers (slow, dull, diffuse) -> pain memory formation (100ms-seconds)

3. **Modulation** — pain signal is amplified or dampened based on context:
   - Gate control theory: non-painful input can close the "gate" to painful input
   - Descending modulation: the brain can suppress pain (e.g., during fight-or-flight)
   - For robots: governor can override pain response for critical tasks

4. **Perception** — the subjective experience. For robots, this is the **pain state** that drives behavior change.

### What the research says

**Haddadin et al. (2017-2019) — "An Artificial Robot Nervous System"**
Sami Haddadin's group at TU Munich built the most complete artificial nociception system for robots. Published in IEEE Robotics and Automation Letters. Key architecture:

- **Artificial nociceptors** that convert physical stimuli (force, temperature, electrical) into pain signals
- **Pain classification**: sharp (fast, reflexive), burning (thermal, slow onset), dull aching (sustained overload)
- **Pain-motor coupling**: pain signals directly modulate motor behavior — the robot withdraws from the painful stimulus
- **Pain habituation and sensitization**: repeated mild stimuli reduce pain response (habituation), but repeated harmful stimuli increase it (sensitization)

The critical insight from Haddadin: **pain is not a binary signal — it is a continuous, multi-dimensional state that decays over time and modulates behavior proportionally.**

**Cully et al. (2015) — "Robots that can adapt like animals" (arXiv:1407.3501)**
The Intelligent Trial-and-Error (IT&E) algorithm demonstrates pain's deeper purpose — avoidance learning:

- Before deployment, the robot builds a "behavioral repertoire" — a map of high-performing behaviors
- When damaged, the robot uses this repertoire as "intuitions" to guide rapid trial-and-error learning
- Key result: a legged robot adapted to 5 different injury types in under 2 minutes
- A robotic arm recovered from 14 different joint failures

The IT&E algorithm is the computational equivalent of pain memory: "that movement pattern caused damage, so weight it down in the repertoire and try alternative approaches."

**Bayesian Optimization for Damage Recovery (Limbo library)**
The `resibots/limbo` C++ library implements Gaussian Process-based optimization for robot damage recovery:
- **Reset-free trial-and-error** (Chatzilygeroudis, Vassiliades, Mouret, 2017): robots adapt without manual intervention between attempts
- **Safety-constrained adaptation** (Papaspyros et al., 2016): damaged robots recover while maintaining safety constraints
- Data-efficient: finds solutions with minimal physical trials (critical because trials can cause further damage)

### Pain vs. existing armOS systems

armOS already has the building blocks but lacks the motivational/memory layer:

| Existing system | What it does | What pain adds |
|----------------|-------------|----------------|
| `telemetry.py` / `check_safety()` | Detects violations NOW | Nothing — pure detection |
| `mycelium.py` | Propagates warnings | Nothing — pure notification |
| `immune.py` | Stores fault patterns, applies mitigations | Pattern is reactive, not avoidant |
| `reflex.py` (proposed) | Fires immediate protective actions | Nothing — pure reaction |
| `emotional.py` / fatigue | Tracks temperature + uptime | Fatigue != pain |
| **Pain (new)** | **Records HOW and WHERE damage occurred, creates aversive memories that bias future movement planning** | **This is the missing piece** |

### Pain intensity model

Biological pain scales nonlinearly. The pain model needs:

```python
@dataclass
class PainEvent:
    """A single pain event — records what hurt, how much, and where."""

    id: str
    timestamp: float
    joint: str                    # Which motor/joint
    pain_type: str                # "sharp", "burning", "aching"
    intensity: float              # 0.0-1.0, nonlinear scale
    cause: str                    # "overcurrent", "overtemp", "collision", "position_error"
    context: dict                 # What was the robot doing? (task, target position, speed)
    position_at_onset: dict       # Joint positions when pain started
    recovery_action: str          # What the reflex/system did
    resolved: bool = False
    resolved_at: float = 0.0
    duration: float = 0.0        # How long the pain lasted

    @property
    def is_chronic(self) -> bool:
        """Pain lasting > 30 seconds is chronic."""
        return self.duration > 30.0


class PainIntensityModel:
    """Maps sensor readings to pain intensity.

    The key insight: pain is NOT proportional to the sensor reading.
    It is proportional to how close the reading is to causing DAMAGE.
    """

    # Thresholds: (warning, pain_onset, severe, critical)
    CURRENT_THRESHOLDS = (400, 600, 800, 1000)  # mA per servo
    TEMP_THRESHOLDS = (45, 55, 62, 70)           # Celsius
    LOAD_THRESHOLDS = (50, 70, 85, 95)           # Percent

    @staticmethod
    def compute(sensor: str, value: float, thresholds: tuple) -> float:
        """Compute pain intensity from sensor value and thresholds.

        Returns 0.0 below warning, scales nonlinearly to 1.0 at critical.
        Uses a sigmoid-like curve centered at pain_onset.
        """
        warning, onset, severe, critical = thresholds
        if value < warning:
            return 0.0
        if value >= critical:
            return 1.0
        # Normalize to [0, 1] range between onset and critical
        normalized = (value - onset) / (critical - onset)
        # Apply sigmoid for nonlinear scaling
        # Sharp increase around onset, plateaus near critical
        import math
        return 1 / (1 + math.exp(-6 * (normalized - 0.5)))
```

### Pain intensity classification

| Intensity | Biological analog | Robot behavior |
|-----------|-------------------|----------------|
| 0.0-0.2 | Mild discomfort | Log, no behavior change |
| 0.2-0.4 | Moderate pain | Slow down the affected joint, add context to pain memory |
| 0.4-0.6 | Significant pain | Alter trajectory to avoid pain-causing configuration, warn neighbors |
| 0.6-0.8 | Severe pain | Abort current task, retreat to safe position, create immune entry |
| 0.8-1.0 | Emergency pain | Disable torque (reflex), broadcast emergency, create permanent avoidance zone |

### Referred pain

In biology, referred pain is when damage in one area causes pain signals in another (heart attack causes arm pain). In robots, the analog is **compensatory stress**:

- Shoulder motor overloaded -> elbow and wrist take extra load to compensate -> they overheat
- One servo jammed -> adjacent servos strain to maintain position -> cascading overload

Implementation: when a pain event occurs on one joint, check adjacent joints for elevated readings. If found, create a **referred pain** entry linking the two:

```python
@dataclass
class ReferredPain:
    """Pain in one joint caused by compensatory stress from another."""
    primary_joint: str         # Where the original problem is
    affected_joint: str        # Where the referred pain manifests
    correlation: float         # How strongly correlated (0-1)
    discovery_timestamp: float

# Adjacency map for the SO-101
JOINT_ADJACENCY = {
    "shoulder_pan": ["shoulder_lift"],
    "shoulder_lift": ["shoulder_pan", "elbow_flex"],
    "elbow_flex": ["shoulder_lift", "wrist_flex"],
    "wrist_flex": ["elbow_flex", "wrist_roll"],
    "wrist_roll": ["wrist_flex", "gripper"],
    "gripper": ["wrist_roll"],
}
```

### Pain memory and avoidance learning

This is what makes pain different from fault detection. Pain memory creates **avoidance zones** in joint space:

```python
@dataclass
class PainMemory:
    """A remembered painful configuration that the robot should avoid."""

    joint_positions: dict[str, int]   # The configuration that hurt
    pain_intensity: float             # How much it hurt (determines avoidance radius)
    cause: str                        # What type of pain
    avoidance_radius: int             # How far (in servo ticks) to stay away
    occurrence_count: int             # How many times this has hurt
    last_occurrence: float
    confidence: float                 # Decays over time if not reinforced

    def contains(self, positions: dict[str, int]) -> bool:
        """Check if a target position falls within this avoidance zone."""
        for joint, pain_pos in self.joint_positions.items():
            target = positions.get(joint)
            if target is not None:
                if abs(target - pain_pos) < self.avoidance_radius:
                    return True
        return False

    def avoidance_cost(self, positions: dict[str, int]) -> float:
        """Compute a cost for being near this pain zone.

        Used to bias trajectory planning away from painful configurations.
        Closer = higher cost. Cost decays with confidence.
        """
        min_distance = float('inf')
        for joint, pain_pos in self.joint_positions.items():
            target = positions.get(joint)
            if target is not None:
                dist = abs(target - pain_pos)
                if dist < min_distance:
                    min_distance = dist
        if min_distance >= self.avoidance_radius:
            return 0.0
        proximity = 1.0 - (min_distance / self.avoidance_radius)
        return proximity * self.pain_intensity * self.confidence


class PainSystem:
    """Central pain system for a citizen.

    Tracks active pain, pain history, and avoidance zones.
    Integrates with the reflex engine (fast response) and
    trajectory planner (avoidance learning).
    """

    def __init__(self):
        self.active_pain: list[PainEvent] = []
        self.pain_history: list[PainEvent] = []
        self.avoidance_zones: list[PainMemory] = []
        self.pain_sensitivity: float = 1.0   # Modulated by context
        self._chronic_threshold = 30.0       # seconds

    def report_pain(self, event: PainEvent) -> None:
        """Record a new pain event."""
        event.intensity *= self.pain_sensitivity
        self.active_pain.append(event)
        self.pain_history.append(event)

        # If high enough intensity, create/reinforce avoidance zone
        if event.intensity > 0.3:
            self._update_avoidance_zone(event)

    def check_trajectory(self, waypoints: list[dict]) -> list[dict]:
        """Check a planned trajectory against avoidance zones.

        Returns a list of warnings with the painful waypoints
        and suggested alternatives.
        """
        warnings = []
        for i, wp in enumerate(waypoints):
            total_cost = sum(z.avoidance_cost(wp) for z in self.avoidance_zones)
            if total_cost > 0.2:
                warnings.append({
                    "waypoint_index": i,
                    "positions": wp,
                    "avoidance_cost": total_cost,
                    "nearby_zones": [
                        z for z in self.avoidance_zones if z.contains(wp)
                    ],
                })
        return warnings

    def current_pain_level(self) -> float:
        """Aggregate current pain level across all active events."""
        if not self.active_pain:
            return 0.0
        return max(e.intensity for e in self.active_pain)

    def decay_and_resolve(self) -> None:
        """Called periodically to resolve expired pain and decay avoidance confidence."""
        now = time.time()
        # Resolve pain events older than their expected duration
        for event in self.active_pain:
            if not event.resolved and now - event.timestamp > self._chronic_threshold:
                event.duration = now - event.timestamp

        # Decay avoidance zone confidence (forgotten pain)
        for zone in self.avoidance_zones:
            age_hours = (now - zone.last_occurrence) / 3600
            zone.confidence *= 0.999 ** age_hours  # Slow exponential decay

        # Prune zones with very low confidence
        self.avoidance_zones = [z for z in self.avoidance_zones if z.confidence > 0.05]

    def sensitize(self, factor: float = 1.2) -> None:
        """Increase pain sensitivity (after repeated injury). Hyperalgesia analog."""
        self.pain_sensitivity = min(2.0, self.pain_sensitivity * factor)

    def habituate(self, factor: float = 0.95) -> None:
        """Decrease pain sensitivity (after repeated benign stimuli). Habituation analog."""
        self.pain_sensitivity = max(0.5, self.pain_sensitivity * factor)
```

### Chronic vs. acute pain

| Type | Duration | Cause | Robot behavior |
|------|----------|-------|----------------|
| Acute | <5 seconds | Collision, sudden overcurrent | Reflex fires, pain memory created, resume task |
| Subacute | 5-30 seconds | Sustained overload, thermal spike | Degraded operation, try alternative approach |
| Chronic | >30 seconds | Persistent mechanical issue, worn gear, bad calibration | Permanent avoidance zone, request maintenance, reduce capability claims |

Chronic pain in a robot means something is mechanically wrong — a stripped gear, worn bearing, or calibration drift. The pain system should escalate chronic pain to the governor with a maintenance request:

```python
def check_chronic_pain(self) -> list[PainEvent]:
    """Identify pain events that have become chronic.

    Chronic pain indicates mechanical issues requiring maintenance.
    """
    chronic = []
    now = time.time()
    for event in self.active_pain:
        if not event.resolved and (now - event.timestamp) > self._chronic_threshold:
            event.duration = now - event.timestamp
            chronic.append(event)
    return chronic
```

### Integration with existing systems

```
Telemetry (sensor readings)
    │
    ├──> Reflex Engine (immediate response, <10ms)
    │       │
    │       └──> Pain System (records event, creates memory, 100ms-1s)
    │               │
    │               ├──> Avoidance Zones (biases future trajectories)
    │               ├──> Pain Memory (episodic: "this hurt at 14:32")
    │               ├──> Immune Memory (if pattern is generalizable)
    │               ├──> Emotional State (pain increases fatigue, reduces confidence)
    │               └──> Mycelium (broadcast if severe enough)
    │
    └──> Normal telemetry pipeline (dashboard, logging)
```

---

## 2. Robot Proprioception — Internal Body Awareness

### How biological proprioception works

Proprioception is the sense of body position and movement without looking. You can touch your nose with your eyes closed because proprioceptors in your muscles, tendons, and joints tell your brain where your arm is in space.

Key biological components:

1. **Muscle spindles** — detect muscle length and rate of change -> servo position registers
2. **Golgi tendon organs** — detect muscle tension/force -> servo load/current registers
3. **Joint receptors** — detect joint angle at extremes -> joint limit awareness
4. **Vestibular system** — balance and spatial orientation -> IMU (if available)
5. **Body schema** — the brain's internal model of body geometry -> forward kinematics model

The critical distinction: **telemetry is raw sensor data. Proprioception is an integrated body model that fuses sensor data with a geometric understanding of the body.**

A robot reading `position=2048` from servo #1 is telemetry.
A robot knowing "my gripper tip is currently 15cm above the table surface, 20cm forward of my base, and my elbow is near its extension limit" is proprioception.

### What the research says

**Chen, Kwiatkowski, Vondrick, Lipson (2021) — "Full-Body Visual Self-Modeling of Robot Morphologies" (arXiv:2111.06389)**

The most complete robot self-model implementation. Key findings:

- The robot learns to predict its **complete 3D mesh** from joint state alone — it knows where every part of its body is in space
- Uses a **query-driven** approach: given a point in space, the model predicts whether the robot occupies that point
- Achieves ~1% workspace accuracy
- **Enables damage detection**: when the predicted self-model diverges from the actual visual observation, the robot knows something has changed about its body
- Fully differentiable: can do gradient-based planning through the self-model

Implementation: PyTorch with SIREN/SDF networks. Repository: `github.com/BoyuanChen/visual-selfmodeling`. Trains in simulation (PyBullet), transfers to real hardware.

**Hoffmann & Bednarova (2016) — "The encoding of proprioceptive inputs in the brain"**
Used Self-Organizing Maps (SOMs) trained on iCub robot "body babbling" data. The SOM learns a topographic map of joint space — nearby joints are represented nearby in the map. This is the computational proprioceptive homunculus.

**Gama & Hoffmann (2019) — "The homunculus for proprioception"**
Extended the SOM approach to learn spatial body representations from self-touch configurations. The robot learns its own body shape by touching itself and mapping proprioceptive inputs.

### armOS proprioception today vs. what's needed

| What exists | What's missing |
|-------------|----------------|
| `telemetry.py` reads servo position, velocity, load, current, temperature, voltage | No geometric model — raw numbers, not spatial awareness |
| `calibration.py` maps pixel space to servo space | Only for camera-arm coordination, not body self-model |
| Servo position registers (STS3215 reg 56) | No forward kinematics to compute end-effector position |
| Load registers (STS3215 reg 60) | No force estimation from current draw |
| No self-collision awareness | No body model to check against |
| No workspace boundary awareness | No joint limit proximity tracking |
| No calibration drift detection | No periodic self-verification |

### Forward kinematics for the SO-101

The SO-101 is a 6-DOF arm. We need a forward kinematics model to convert joint angles to Cartesian positions. The SO-101's DH parameters (approximate, from the Waveshare/HuggingFace SO-100 specs):

```python
import math
import numpy as np

# SO-101 link lengths (approximate, in mm)
SO101_LINKS = {
    "base_height": 55,        # Base to shoulder_pan axis
    "shoulder_offset": 0,     # Lateral offset
    "upper_arm": 104,         # shoulder_lift to elbow_flex
    "forearm": 88,            # elbow_flex to wrist_flex
    "wrist": 35,              # wrist_flex to wrist_roll
    "gripper": 60,            # wrist_roll to gripper tip
}

# Servo position to angle conversion
# STS3215: 0-4095 range maps to 0-360 degrees
# Center (2048) = 180 degrees = 0 in robot frame
TICKS_PER_DEGREE = 4096 / 360
CENTER_TICK = 2048


def ticks_to_radians(ticks: int) -> float:
    """Convert servo ticks to radians from center position."""
    degrees = (ticks - CENTER_TICK) / TICKS_PER_DEGREE
    return math.radians(degrees)


@dataclass
class CartesianPose:
    """Position and orientation of a point on the robot."""
    x: float   # mm, forward from base
    y: float   # mm, left from base
    z: float   # mm, up from base
    # Could add orientation quaternion later


@dataclass
class BodyState:
    """The robot's proprioceptive state — where every joint and the
    end-effector are in Cartesian space."""

    joint_positions: dict[str, int]      # Raw servo ticks
    joint_angles_rad: dict[str, float]   # Converted to radians
    joint_velocities: dict[str, int]     # Raw velocity
    joint_loads: dict[str, float]        # Percent
    joint_currents: dict[str, float]     # mA
    joint_temperatures: dict[str, float] # Celsius

    # Computed from forward kinematics
    elbow_position: CartesianPose | None = None
    wrist_position: CartesianPose | None = None
    gripper_position: CartesianPose | None = None

    # Derived awareness
    joint_limit_proximity: dict[str, float] = None  # 0.0=center, 1.0=at limit
    estimated_payload_grams: float = 0.0
    workspace_utilization: float = 0.0  # How much of reachable space is being used

    def near_joint_limit(self, joint: str, threshold: float = 0.8) -> bool:
        """Is this joint close to its limit?"""
        if self.joint_limit_proximity is None:
            return False
        return self.joint_limit_proximity.get(joint, 0.0) > threshold

    def estimated_force_n(self, joint: str) -> float:
        """Estimate force at a joint from current draw.

        STS3215: current (mA) * 6.5 gives approximate raw value.
        Force estimation requires torque constant and lever arm.
        Approximate: torque_Nm = current_A * Kt, force = torque / lever_arm
        """
        current_ma = self.joint_currents.get(joint, 0.0)
        current_a = abs(current_ma) / 1000.0
        # STS3215 approximate torque constant: ~0.015 Nm/A (at 7.4V)
        KT = 0.015
        torque_nm = current_a * KT
        # Very rough force estimate assuming average lever arm
        lever_m = 0.1  # 100mm average
        return torque_nm / lever_m if lever_m > 0 else 0.0


# Joint limits for SO-101 (in servo ticks)
JOINT_LIMITS = {
    "shoulder_pan":  (1024, 3072),   # ~90 to ~270 degrees
    "shoulder_lift": (1200, 2200),   # Restricted range
    "elbow_flex":    (2000, 3200),   # Restricted range
    "wrist_flex":    (1024, 3072),
    "wrist_roll":    (1024, 3072),
    "gripper":       (1400, 2600),
}


def compute_joint_limit_proximity(positions: dict[str, int]) -> dict[str, float]:
    """Compute how close each joint is to its limits.

    Returns 0.0 when at center of range, 1.0 when at limit.
    """
    proximity = {}
    for joint, (lo, hi) in JOINT_LIMITS.items():
        pos = positions.get(joint, (lo + hi) // 2)
        center = (lo + hi) / 2
        half_range = (hi - lo) / 2
        if half_range == 0:
            proximity[joint] = 0.0
        else:
            proximity[joint] = abs(pos - center) / half_range
    return proximity
```

### Force/torque estimation from current draw

No force sensor needed. The STS3215's current register (reg 69) gives current draw in ~6.5mA steps. Current correlates with torque output:

```
Torque = Kt * Current
Force_at_tip = Torque / Lever_arm_to_tip
```

This is imprecise but useful for:
- **Detecting unexpected loads** (someone placed a heavy object in the gripper)
- **Detecting collisions** (sudden current spike without commanded motion)
- **Estimating payload weight** (steady-state current in a holding pose)

```python
def estimate_payload_grams(
    gripper_current_ma: float,
    gripper_angle_ticks: int,
    gravity_torque_factor: float = 0.0001,
) -> float:
    """Estimate payload weight from gripper holding current.

    Very rough: subtracts estimated no-load current, converts to force.
    Should be calibrated per-arm using known weights.
    """
    # No-load current for STS3215 is approximately 50-100mA
    NO_LOAD_CURRENT = 80.0
    excess_current = max(0, abs(gripper_current_ma) - NO_LOAD_CURRENT)
    # Very rough conversion, should be calibrated
    estimated_grams = excess_current * gravity_torque_factor * 1000
    return estimated_grams
```

### Proprioceptive drift detection

Calibration degrades over time. Gears wear, screws loosen, temperature changes dimensions. Proprioceptive drift is when the robot's internal model no longer matches reality:

```python
@dataclass
class DriftDetector:
    """Detects calibration drift by comparing expected vs actual positions.

    Periodically moves to known calibration positions and measures
    the error. If error exceeds threshold, flags for recalibration.
    """

    calibration_positions: list[dict[str, int]]  # Known reference positions
    expected_positions: list[dict[str, int]]      # What camera sees (pixel->servo)
    max_error_ticks: int = 30                     # Acceptable error threshold

    def check_drift(self, actual: dict[str, int], expected: dict[str, int]) -> float:
        """Compute drift as RMS error across all joints."""
        errors = []
        for joint in actual:
            if joint in expected:
                errors.append((actual[joint] - expected[joint]) ** 2)
        if not errors:
            return 0.0
        return math.sqrt(sum(errors) / len(errors))

    def needs_recalibration(self, drift: float) -> bool:
        return drift > self.max_error_ticks
```

### Self-collision awareness

The SO-101 can collide with itself (gripper hitting the base, elbow folding into the shoulder). A body model enables self-collision prediction:

```python
def check_self_collision(body_state: BodyState) -> list[str]:
    """Check if any parts of the arm are at risk of self-collision.

    Uses simplified bounding sphere checks between non-adjacent links.
    Returns list of collision risk descriptions.
    """
    risks = []

    # Simplified: check if gripper is too close to base
    if body_state.gripper_position is not None:
        gp = body_state.gripper_position
        dist_to_base = math.sqrt(gp.x**2 + gp.y**2 + gp.z**2)
        if dist_to_base < 80:  # mm, minimum safe distance
            risks.append(f"gripper near base: {dist_to_base:.0f}mm")

    # Check if elbow is below table surface
    if body_state.elbow_position is not None:
        if body_state.elbow_position.z < 0:
            risks.append(f"elbow below table: z={body_state.elbow_position.z:.0f}mm")

    return risks
```

### The integrated proprioceptive system

```python
class ProprioceptiveSystem:
    """Integrated body awareness for a citizen.

    Fuses raw telemetry into a spatial body model with:
    - Forward kinematics (where am I in space?)
    - Force estimation (what forces am I experiencing?)
    - Joint limit awareness (am I near my limits?)
    - Self-collision checking (am I about to hit myself?)
    - Drift detection (is my calibration still accurate?)
    """

    def __init__(self, link_params: dict = None):
        self.links = link_params or SO101_LINKS
        self.body_state: BodyState | None = None
        self.drift_detector = DriftDetector(
            calibration_positions=[],
            expected_positions=[],
        )
        self._position_history: deque = deque(maxlen=100)  # For velocity smoothing

    def update(self, telemetry: ArmTelemetry) -> BodyState:
        """Update body state from new telemetry reading.

        This is called every telemetry cycle (~10ms).
        """
        positions = {}
        angles = {}
        velocities = {}
        loads = {}
        currents = {}
        temperatures = {}

        for name, snap in telemetry.snapshots.items():
            positions[name] = snap.position
            angles[name] = ticks_to_radians(snap.position)
            velocities[name] = snap.velocity
            loads[name] = snap.load_pct
            currents[name] = snap.current_ma
            temperatures[name] = snap.temperature_c

        # Compute forward kinematics
        gripper_pos = self._forward_kinematics(angles)

        # Compute joint limit proximity
        limit_proximity = compute_joint_limit_proximity(positions)

        # Estimate payload
        gripper_current = currents.get("gripper", 0.0)
        payload = estimate_payload_grams(gripper_current, positions.get("gripper", 2048))

        self.body_state = BodyState(
            joint_positions=positions,
            joint_angles_rad=angles,
            joint_velocities=velocities,
            joint_loads=loads,
            joint_currents=currents,
            joint_temperatures=temperatures,
            gripper_position=gripper_pos,
            joint_limit_proximity=limit_proximity,
            estimated_payload_grams=payload,
        )

        self._position_history.append(positions)
        return self.body_state

    def _forward_kinematics(self, angles: dict[str, float]) -> CartesianPose | None:
        """Compute gripper tip position from joint angles.

        Uses simplified DH parameter approach for the SO-101.
        Returns None if insufficient joint data.
        """
        # Simplified 3-DOF FK using shoulder_pan, shoulder_lift, elbow_flex
        try:
            pan = angles.get("shoulder_pan", 0.0)
            lift = angles.get("shoulder_lift", 0.0)
            elbow = angles.get("elbow_flex", 0.0)

            L1 = self.links["upper_arm"]
            L2 = self.links["forearm"]
            L3 = self.links["wrist"] + self.links["gripper"]

            # 2D arm in the sagittal plane, then rotate by pan
            r = L1 * math.cos(lift) + L2 * math.cos(lift + elbow) + L3
            z = (self.links["base_height"]
                 + L1 * math.sin(lift)
                 + L2 * math.sin(lift + elbow))

            x = r * math.cos(pan)
            y = r * math.sin(pan)

            return CartesianPose(x=x, y=y, z=z)
        except (KeyError, TypeError):
            return None

    def get_warnings(self) -> list[str]:
        """Get proprioceptive warnings."""
        warnings = []
        if self.body_state is None:
            return warnings

        # Joint limit warnings
        for joint, prox in (self.body_state.joint_limit_proximity or {}).items():
            if prox > 0.9:
                warnings.append(f"{joint}: at {prox:.0%} of joint limit")

        # Self-collision warnings
        warnings.extend(check_self_collision(self.body_state))

        return warnings
```

### How proprioception differs from telemetry

| Telemetry | Proprioception |
|-----------|---------------|
| "shoulder_lift position = 1600" | "My arm is extended 15cm forward, elbow at 120 degrees" |
| "gripper current = 350mA" | "I'm holding something weighing approximately 50 grams" |
| "elbow_flex position = 3100" | "My elbow is near its extension limit, be careful" |
| Six independent sensor readings | One integrated body state with spatial meaning |
| Updated every 10ms | Updated every 10ms, but also predicts forward |
| No memory | Tracks drift from calibration baseline |

---

## 3. Robot Sleep — Periodic Maintenance and Consolidation

### How biological sleep works

Sleep is not idle time. It is an active maintenance cycle with distinct phases:

1. **NREM Stage 1 (Light sleep)** — transition, easily awakened, muscle relaxation
2. **NREM Stage 2** — spindles and K-complexes, memory consolidation begins
3. **NREM Stage 3 (Slow-wave/Deep sleep)** — heavy maintenance: growth hormone release, immune system activation, cellular repair
4. **REM sleep** — dreaming, procedural memory consolidation, emotional processing, synaptic pruning

The critical functions that map to robots:

| Biological function | Robot analog |
|--------------------|----|
| Memory consolidation (hippocampus -> cortex) | Episodic -> semantic/procedural memory transfer |
| Synaptic pruning (remove weak connections) | Prune low-value immune patterns, stale knowledge |
| Immune system activation | Immune memory reorganization, pattern matching optimization |
| Growth hormone / tissue repair | Calibration check, servo EEPROM verification |
| Dream replay (REM) | Replay recent episodes to extract patterns |
| Circadian rhythm | Scheduled maintenance windows |
| Adenosine buildup (sleep pressure) | Fatigue metric from `emotional.py` |

### What the research says

**Elastic Weight Consolidation (Kirkpatrick et al., 2016, arXiv:1612.00796)**
The EWC paper addresses catastrophic forgetting — when a neural network learns a new task and forgets old ones. The solution: identify which weights are important for previously learned tasks and protect them during new learning. This is the computational analog of sleep-based memory consolidation.

Key insight for armOS: during "sleep," the robot should identify which procedural memories are important (high success rate, frequently used) and protect them from being overwritten by new experiences.

**Prioritized Experience Replay (Schaul et al., 2015, arXiv:1511.05952)**
Instead of replaying all experiences uniformly, prioritize experiences by their "surprise" value (TD-error). During robot sleep, replay the most informative episodes — not random ones.

Key finding: 41 of 49 Atari games improved with prioritized replay. The principle: **not all memories are equally worth replaying.**

**Sleep-inspired memory consolidation in robotics** (emerging field):
No single landmark paper, but the convergence of:
- Experience replay from RL (DQN, 2015)
- Continual learning without forgetting (EWC, PackNet, Progressive Neural Networks)
- The hippocampal consolidation theory from neuroscience

The computational model: during active operation, experiences are written to a fast, high-capacity buffer (hippocampus / episodic memory). During sleep, important experiences are "replayed" and slowly integrated into long-term storage (neocortex / semantic + procedural memory), while unimportant ones are pruned.

### Robot sleep architecture

```python
class SleepState(Enum):
    """Sleep depth levels."""
    AWAKE = 0          # Normal operation
    DROWSY = 1         # Reduced activity, light maintenance
    LIGHT_SLEEP = 2    # Background consolidation, still responsive
    DEEP_SLEEP = 3     # Full maintenance, slow to wake
    REM = 4            # Dream replay, not externally observable


@dataclass
class SleepSchedule:
    """When and how deeply to sleep."""

    # Time-based schedule (24h format)
    preferred_sleep_time: float = 2.0    # 2 AM
    preferred_wake_time: float = 6.0     # 6 AM
    min_awake_hours: float = 4.0         # Don't sleep if awake < 4h

    # Fatigue-based triggers
    fatigue_threshold: float = 0.7       # Start sleeping when fatigue > 0.7
    emergency_wake_threshold: float = 0.0  # Any severity >= this wakes up

    # Adaptive: learn optimal sleep schedule from experience
    # (e.g., sleep after high-activity periods, stay awake during
    #  anticipated task periods)


class SleepCycle:
    """Manages sleep phases and maintenance activities.

    Each sleep phase does different work:
    - DROWSY: reduce servo update rate, lower power consumption
    - LIGHT_SLEEP: run consolidation, still process heartbeats
    - DEEP_SLEEP: heavy maintenance, only wake for emergencies
    - REM: dream replay of recent episodes
    """

    CYCLE_DURATION_MINUTES = 90  # Like human sleep cycles

    def __init__(self, citizen):
        self.citizen = citizen
        self.state = SleepState.AWAKE
        self.sleep_started_at: float = 0.0
        self.cycles_completed: int = 0
        self.maintenance_log: list[dict] = []

    async def enter_sleep(self) -> None:
        """Begin a sleep cycle."""
        self.state = SleepState.DROWSY
        self.sleep_started_at = time.time()
        self._log("entering sleep — drowsy phase")

        # Phase 1: DROWSY (2 minutes)
        await self._drowsy_phase()

        # Phase 2: LIGHT SLEEP (20 minutes)
        await self._light_sleep_phase()

        # Phase 3: DEEP SLEEP (40 minutes)
        await self._deep_sleep_phase()

        # Phase 4: REM (20 minutes)
        await self._rem_phase()

        self.cycles_completed += 1
        self.state = SleepState.AWAKE
        self._log(f"sleep cycle {self.cycles_completed} complete")

    async def _drowsy_phase(self) -> None:
        """Light transition into sleep. Still fully responsive."""
        self.state = SleepState.DROWSY
        # Reduce heartbeat frequency
        # Finish any in-progress tasks
        # Announce "going to sleep" to neighbors
        await asyncio.sleep(120)  # 2 minutes

    async def _light_sleep_phase(self) -> None:
        """Memory consolidation. Responsive to direct messages."""
        self.state = SleepState.LIGHT_SLEEP

        # Task 1: Consolidate episodic memory
        consolidated = await self._consolidate_episodes()
        self.maintenance_log.append({
            "phase": "light_sleep",
            "task": "episode_consolidation",
            "episodes_processed": consolidated,
            "timestamp": time.time(),
        })

        # Task 2: Update semantic memory from recent episodes
        knowledge_added = await self._extract_knowledge()
        self.maintenance_log.append({
            "phase": "light_sleep",
            "task": "knowledge_extraction",
            "facts_added": knowledge_added,
            "timestamp": time.time(),
        })

    async def _deep_sleep_phase(self) -> None:
        """Heavy maintenance. Only wake for emergencies."""
        self.state = SleepState.DEEP_SLEEP

        # Task 1: Immune memory optimization
        pruned = self._optimize_immune_memory()
        self.maintenance_log.append({
            "phase": "deep_sleep",
            "task": "immune_optimization",
            "patterns_pruned": pruned,
            "timestamp": time.time(),
        })

        # Task 2: Calibration drift check
        drift = await self._check_calibration_drift()
        self.maintenance_log.append({
            "phase": "deep_sleep",
            "task": "calibration_check",
            "drift_detected": drift,
            "timestamp": time.time(),
        })

        # Task 3: Log rotation and cleanup
        cleaned = self._cleanup_logs()
        self.maintenance_log.append({
            "phase": "deep_sleep",
            "task": "log_cleanup",
            "bytes_freed": cleaned,
            "timestamp": time.time(),
        })

        # Task 4: Genome optimization
        self._compress_genome()

        # Task 5: Pain memory decay
        self._decay_pain_memories()

    async def _rem_phase(self) -> None:
        """Dream replay — replay recent episodes to strengthen procedural memory."""
        self.state = SleepState.REM

        # Select important recent episodes for replay
        episodes = self._select_episodes_for_replay()

        for episode in episodes:
            # "Replay" the episode — re-evaluate outcomes, update procedure params
            self._replay_episode(episode)

        self.maintenance_log.append({
            "phase": "rem",
            "task": "dream_replay",
            "episodes_replayed": len(episodes),
            "timestamp": time.time(),
        })

    def should_sleep(self) -> bool:
        """Determine if the citizen should enter sleep.

        Based on fatigue level, time of day, and recent activity.
        """
        # Never sleep during active tasks
        if self.citizen.state not in ("idle", "steady"):
            return False

        # Fatigue-based
        if self.citizen.emotional_state.fatigue > 0.7:
            return True

        # Time-based (if configured)
        hour = time.localtime().tm_hour
        if self.citizen.sleep_schedule:
            sched = self.citizen.sleep_schedule
            if sched.preferred_sleep_time <= hour or hour < sched.preferred_wake_time:
                return True

        return False

    def should_wake(self, event_severity: int = 0) -> bool:
        """Determine if an event should wake the citizen.

        EMERGENCY always wakes. CRITICAL wakes from light sleep.
        Only EMERGENCY wakes from deep sleep.
        """
        if self.state == SleepState.AWAKE:
            return False

        if event_severity >= 3:  # EMERGENCY
            return True
        if event_severity >= 2 and self.state <= SleepState.LIGHT_SLEEP:  # CRITICAL
            return True
        return False
```

### Consolidation details

The consolidation engine runs during light sleep and performs the episodic-to-semantic and episodic-to-procedural transfers described in the memory research doc:

```python
async def _consolidate_episodes(self) -> int:
    """Consolidate recent episodic memory.

    1. Score episodes by importance
    2. Extract patterns from high-importance episodes
    3. Compress low-importance episodes into summaries
    4. Prune expired episodes
    """
    memory = self.citizen.memory
    if not hasattr(memory, 'episodic'):
        return 0

    recent = memory.episodic.get_since(self._last_consolidation_time)
    processed = 0

    for episode in recent:
        # High importance: extract knowledge
        if episode.importance > 0.6:
            self._extract_semantic_knowledge(episode)
            self._refine_procedural_memory(episode)

        # Medium importance: keep but compress context
        elif episode.importance > 0.3:
            episode.context = self._compress_context(episode.context)

        # Low importance: mark for pruning
        else:
            episode.tags.append("prune_candidate")

        processed += 1

    # Prune old low-importance episodes
    memory.episodic.prune(max_age_days=7, min_importance=0.2)

    self._last_consolidation_time = time.time()
    return processed


def _select_episodes_for_replay(self) -> list:
    """Select episodes for dream replay using prioritized sampling.

    Priority based on:
    - Surprise (outcomes that differed from expectation)
    - Importance (failures, first-time events)
    - Recency (recent episodes replayed more)
    """
    memory = self.citizen.memory
    if not hasattr(memory, 'episodic'):
        return []

    recent = memory.episodic.get_since(time.time() - 86400)  # Last 24 hours

    # Score each episode for replay priority
    scored = []
    for ep in recent:
        surprise = 1.0 if ep.outcome == "failure" else 0.3
        priority = ep.importance * 0.4 + surprise * 0.4 + 0.2  # Recency bonus
        scored.append((priority, ep))

    # Top 10 by priority
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ep for _, ep in scored[:10]]


def _replay_episode(self, episode) -> None:
    """Replay an episode to strengthen procedural memory.

    This is the computational analog of dream replay.
    Re-evaluate the episode's outcome and update:
    - Procedure parameters (if the episode was a task execution)
    - Avoidance zones (if the episode involved pain)
    - Success rate estimates (running averages)
    """
    if episode.outcome == "success":
        # Reinforce the procedure that was used
        if hasattr(self.citizen, 'memory') and hasattr(self.citizen.memory, 'procedural'):
            skill = episode.context.get("skill_name")
            if skill:
                self.citizen.memory.procedural.reinforce(skill, episode.context)
    elif episode.outcome == "failure":
        # Strengthen avoidance of the failure conditions
        if hasattr(self.citizen, 'pain_system'):
            positions = episode.context.get("joint_positions")
            if positions:
                self.citizen.pain_system.reinforce_avoidance(positions)
```

### Immune memory optimization during deep sleep

The existing LRU pruning in `immune.py` is a blunt instrument. Sleep-based optimization is smarter:

```python
def _optimize_immune_memory(self) -> int:
    """Smarter immune memory pruning during deep sleep.

    Instead of pure LRU, consider:
    1. Merge similar patterns (reduce redundancy)
    2. Prune patterns that have never matched in 30 days
    3. Boost patterns that have matched recently (increase occurrences)
    4. Cross-reference with pain memory (pain-validated patterns are more valuable)
    """
    immune = self.citizen.immune_memory
    patterns = immune.get_all()
    pruned = 0
    now = time.time()

    # Pass 1: Prune never-triggered patterns older than 30 days
    for p in patterns:
        age_days = (now - p.learned_at) / 86400
        if p.occurrences <= 1 and age_days > 30:
            if p.id in immune.patterns:
                del immune.patterns[p.id]
                pruned += 1

    # Pass 2: Merge similar patterns
    # (patterns with same type but different thresholds -> keep tighter threshold)
    by_type = {}
    for p in immune.get_all():
        by_type.setdefault(p.pattern_type, []).append(p)

    for ptype, group in by_type.items():
        if len(group) > 1:
            # Keep the one with highest occurrences, merge others into it
            group.sort(key=lambda p: p.occurrences, reverse=True)
            primary = group[0]
            for secondary in group[1:]:
                primary.occurrences += secondary.occurrences
                if secondary.id in immune.patterns:
                    del immune.patterns[secondary.id]
                    pruned += 1

    return pruned
```

### Calibration drift check during deep sleep

```python
async def _check_calibration_drift(self) -> bool:
    """Check if calibration has drifted by moving to known positions.

    Only runs if the arm has a saved calibration and is not in use.
    Moves to 3 reference positions and checks if servo positions
    match the expected values from last calibration.
    """
    if not hasattr(self.citizen, 'proprioceptive_system'):
        return False

    proprio = self.citizen.proprioceptive_system
    detector = proprio.drift_detector

    if not detector.calibration_positions:
        return False

    drifts = []
    for ref_pos in detector.calibration_positions[:3]:
        # Move to reference position
        # (In practice, this would command the servos)
        # Read actual position after settling
        # Compare to expected
        # drift = detector.check_drift(actual, expected)
        # drifts.append(drift)
        pass

    if drifts:
        avg_drift = sum(drifts) / len(drifts)
        if detector.needs_recalibration(avg_drift):
            self._log(f"CALIBRATION DRIFT DETECTED: avg {avg_drift:.1f} ticks")
            # Notify governor
            return True

    return False
```

### When to sleep

Sleep pressure builds from multiple sources:

```python
def compute_sleep_pressure(citizen) -> float:
    """Compute how much the citizen needs to sleep.

    Combines multiple factors into a 0.0-1.0 pressure score.
    """
    pressure = 0.0

    # Factor 1: Uptime (adenosine analog)
    uptime_hours = (time.time() - citizen.start_time) / 3600
    pressure += min(0.3, uptime_hours / 24 * 0.3)  # Max 0.3 from uptime

    # Factor 2: Fatigue from emotional state
    pressure += citizen.emotional_state.fatigue * 0.3  # Max 0.3 from fatigue

    # Factor 3: Unconsolidated episodes
    if hasattr(citizen, 'memory') and hasattr(citizen.memory, 'episodic'):
        unconsolidated = citizen.memory.episodic.count_since(
            citizen._last_consolidation_time if hasattr(citizen, '_last_consolidation_time') else 0
        )
        pressure += min(0.2, unconsolidated / 100 * 0.2)  # Max 0.2

    # Factor 4: Time since last sleep
    if hasattr(citizen, 'sleep_cycle'):
        hours_since_sleep = (time.time() - citizen.sleep_cycle.sleep_started_at) / 3600
        if citizen.sleep_cycle.cycles_completed > 0:
            pressure += min(0.2, hours_since_sleep / 8 * 0.2)  # Max 0.2

    return min(1.0, pressure)
```

### Light sleep vs. deep sleep responsiveness

| Sleep state | Heartbeat rate | Responds to | Wakes for | Maintenance work |
|-------------|---------------|-------------|-----------|-----------------|
| AWAKE | 2s (normal) | Everything | N/A | None |
| DROWSY | 5s | All messages | Any task assignment | Finish current work |
| LIGHT_SLEEP | 10s | Direct messages, heartbeats | CRITICAL or higher | Episode consolidation, knowledge extraction |
| DEEP_SLEEP | 30s | Emergency only | EMERGENCY only | Immune optimization, calibration check, log cleanup |
| REM | 10s | Direct messages | CRITICAL or higher | Dream replay, procedural reinforcement |

### Integration with existing emotional system

Sleep feeds back into `emotional.py`:

- After a full sleep cycle: `fatigue` drops by 0.5 (minimum 0.0)
- `confidence` gets a small boost (0.05) from consolidation
- `curiosity` resets toward personality baseline
- Incomplete sleep (woken by emergency): fatigue drops by 0.1 only

```python
def post_sleep_emotional_update(citizen, cycles_completed: int) -> None:
    """Update emotional state after sleeping."""
    if cycles_completed > 0:
        fatigue_reduction = min(0.5, cycles_completed * 0.2)
        citizen.emotional_state.fatigue = max(0.0,
            citizen.emotional_state.fatigue - fatigue_reduction)
        citizen.emotional_state.confidence = min(1.0,
            citizen.emotional_state.confidence + 0.05)
```

---

## 4. Synthesis: How Pain, Proprioception, and Sleep Interact

These three systems are deeply interconnected:

```
                    ┌─────────────────────────────────┐
                    │         PROPRIOCEPTION           │
                    │  "Where am I? What am I doing?"  │
                    │  Body schema, FK, force estimate  │
                    └────────┬──────────┬──────────────┘
                             │          │
                    detects  │          │  provides context
                    anomaly  │          │  for pain localization
                             │          │
                    ┌────────▼──────────▼──────────────┐
                    │            PAIN                   │
                    │  "That hurt. Remember and avoid." │
                    │  Avoidance zones, pain memory     │
                    └────────┬──────────┬──────────────┘
                             │          │
                   creates   │          │  pain events need
                   memories  │          │  consolidation
                             │          │
                    ┌────────▼──────────▼──────────────┐
                    │           SLEEP                   │
                    │  "Process, consolidate, repair."  │
                    │  Dream replay, pruning, calibrate │
                    └──────────────────────────────────┘
                             │
                             │  sleep recalibrates
                             │  proprioception and
                             │  decays stale pain
                             │
                    ┌────────▼─────────────────────────┐
                    │       Back to PROPRIOCEPTION      │
                    │  Refreshed body model, decayed    │
                    │  avoidance zones, new knowledge   │
                    └──────────────────────────────────┘
```

### Data flow example

**Scenario:** The arm reaches for an object and the elbow overloads.

1. **Proprioception** detects: "elbow is at 95% of joint limit, current draw spiking to 800mA"
2. **Reflex** fires: reduce elbow velocity 50% (existing system)
3. **Pain** records: PainEvent at elbow, intensity 0.6, cause "overcurrent near joint limit", position {elbow_flex: 3150}
4. **Pain** creates avoidance zone: avoid elbow_flex > 3100 with radius 100 ticks
5. **Emotional state** updates: fatigue +0.1, confidence -0.05
6. **Mycelium** broadcasts: WARNING "elbow overload at extended position"
7. **Immune memory** checks: is this a known pattern? If yes, increment. If new, create entry.

**Hours later, during sleep:**

8. **Light sleep consolidation**: the pain episode is reviewed, extracted as knowledge: "reaching to zone X requires elbow extension beyond safe range"
9. **REM replay**: the failed reach episode is replayed. Procedural memory updates: "for objects in zone X, try a different approach angle that keeps elbow below 3050"
10. **Deep sleep calibration check**: move to 3 reference positions, verify calibration is still accurate
11. **Pain memory decay**: the avoidance zone confidence drops slightly (but persists because it has high intensity)

**Next day, same task:**

12. **Trajectory planner** queries pain system: "I want to reach zone X"
13. **Pain system** returns: avoidance cost for the direct path
14. **Planner** chooses: alternative approach angle (from procedural memory, refined during REM)
15. **Proprioception** monitors: elbow stays below 3050, current nominal
16. **No pain event** — success. Procedural memory reinforced.

### New modules needed

| Module | Size estimate | Dependencies |
|--------|--------------|--------------|
| `pain.py` | 300-400 lines | `telemetry.py`, `immune.py`, `emotional.py` |
| `proprioception.py` | 300-400 lines | `telemetry.py`, `calibration.py` |
| `sleep.py` | 400-500 lines | `pain.py`, `proprioception.py`, `immune.py`, `memory.py` (from memory research), `emotional.py` |

### Implementation priority

1. **Proprioception first** — it provides the spatial context that pain and sleep need. Start with FK, joint limit proximity, and force estimation. Pure computation, no hardware changes.

2. **Pain second** — builds on proprioception for localization and the reflex engine for triggering. The pain memory and avoidance zones are the highest-value new capability.

3. **Sleep third** — requires the memory system (from the memory research doc) to be in place. Sleep is the consolidation mechanism that makes both pain and episodic memory durable.

All three modules are implementable in pure Python, require no GPU, and integrate through the existing citizen architecture.

---

## Sources

### Robot Pain / Artificial Nociception
- Haddadin et al., "An Artificial Robot Nervous System to Teach Robots How to Feel Pain and Reflexively React to Potentially Damaging Contacts" — IEEE Robotics and Automation Letters, 2017-2019
- Cully, Clune, Tarapore, Mouret, "Robots that can adapt like animals" — arXiv:1407.3501, Nature 2015
- Chatzilygeroudis, Vassiliades, Mouret, "Reset-free Trial-and-Error Learning for Robot Damage Recovery" — 2017 (Limbo library)
- Papaspyros et al., "Safety-Constrained Bayesian Optimization for Robot Damage Recovery" — 2016
- resibots/limbo — C++ library for Gaussian Process optimization, robot damage recovery

### Robot Proprioception / Self-Modeling
- Chen, Kwiatkowski, Vondrick, Lipson, "Full-Body Visual Self-Modeling of Robot Morphologies" — arXiv:2111.06389, Science Robotics 2022
- Hoffmann, Bednarova, "The encoding of proprioceptive inputs in the brain: knowns and unknowns from a robotic perspective" — 2016
- Gama, Hoffmann, "The homunculus for proprioception: Toward learning the representation of a humanoid robot's joint space using self-organizing maps" — 2019
- Bechtle, Das, Meier, "Multi-Modal Learning of Keypoint Predictive Models for Visual Object Manipulation" — 2020
- BoyuanChen/visual-selfmodeling — PyTorch implementation of robot self-modeling (GitHub)

### Sleep / Memory Consolidation
- Kirkpatrick et al., "Overcoming catastrophic forgetting in neural networks" (EWC) — arXiv:1612.00796, PNAS 2017
- Schaul et al., "Prioritized Experience Replay" — arXiv:1511.05952, ICLR 2016
- Mnih et al., "Human-level control through deep reinforcement learning" (DQN experience replay) — Nature 2015
- See also: RESEARCH-robot-memory.md for comprehensive memory architecture references

### Cross-cutting
- RESEARCH-reflexes.md — reflex engine architecture (pain triggers reflexes, proprioception feeds reflexes)
- SOUL.md — personality and values (pain affects personality drift, sleep restores emotional baseline)
- GROWTH.md — developmental stages (pain sensitivity and sleep patterns change with maturation)
