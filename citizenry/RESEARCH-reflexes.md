# Robot Reflexes and Reactive Systems
## Deep Research for armOS Citizenry

**Date:** 2026-03-16
**Context:** armOS currently routes all behavior through the governor (brain). Biological systems use reflex arcs — spinal cord handles "hand on hot stove" before the brain knows. We need the same.

---

## 1. Reactive Architectures in Robotics

### Brooks' Subsumption Architecture

Rodney Brooks (1986) introduced subsumption architecture as a direct rejection of classical AI's "sense-model-plan-act" pipeline. The core insight: **you don't need a world model to behave intelligently.**

**How it works:**
- Behaviors are organized in layers, lowest = most primitive (avoid obstacles), highest = most goal-directed (explore room)
- Each layer is an independent Augmented Finite State Machine (AFSM) — it runs continuously
- Higher layers **subsume** lower layers via two mechanisms:
  - **Inhibition:** block a lower layer's output from reaching actuators
  - **Suppression:** replace a lower layer's input with the higher layer's signal
- There is **no central arbitrator** — priority is structural, wired into the connections

**Build order:** Layer 0 (survive) is built and tested alone. Layer 1 (wander) is added on top — if it fails, Layer 0 still works. This is crucial: **safety degrades gracefully.**

**Relevance to armOS:**
- Layer 0 = Reflex layer (overcurrent protection, thermal shutdown, voltage collapse response)
- Layer 1 = Teleop compliance (follow leader arm positions)
- Layer 2 = Autonomous task execution (policy inference)
- Layer 3 = Governor directives (high-level goals)

Each layer can only suppress or inhibit the one below it. Layer 0 **cannot be suppressed by anything** — it is always active. This is the reflex guarantee.

### Behavior-Based Robotics Beyond Brooks

Brooks' architecture was Layer 0 of a broader movement. Key developments:

- **Arkin's Motor Schemas (1989):** Instead of strict priority, behaviors are vector fields that get summed. A "move to goal" vector + "avoid obstacle" vector = actual movement. This allows **blending** rather than winner-take-all.
- **Mataric's Basis Behaviors (1997):** Built on Brooks but added reinforcement learning to tune the relative strengths of behaviors over time.
- **Behavior Trees (Colledanchise & Ogren, 2018):** Modern successor — tree structure where Fallback nodes provide priority (left child = highest priority, tried first) and Sequence nodes provide chaining. Used in ROS2 Nav2 stack. Safety checks sit as the leftmost children of root Fallback nodes — they get ticked every cycle and can abort any plan.

### Priority-Based Behavior Arbitration Patterns

| Pattern | Mechanism | Tradeoff |
|---------|-----------|----------|
| Fixed priority (subsumption) | Hardwired layer order | Simple, predictable, no blending |
| Voting/auction | Each behavior votes for actions | Flexible, but latency |
| Motor schema (vector sum) | Weighted vector addition | Smooth, but can deadlock |
| Behavior trees | Tree-structured tick traversal | Modular, testable, industry standard |
| Activation networks | Spreading activation selects behavior | Biologically plausible, hard to debug |

**Recommendation for armOS:** Fixed priority for reflexes (Layer 0), behavior trees for everything above. Reflexes must never participate in arbitration — they just fire.

---

## 2. Reflex Arcs

### Biological Model

In vertebrates, a reflex arc is: **sensory neuron -> interneuron (spinal cord) -> motor neuron**. The brain is notified *after* the reflex fires. Key properties:

- **Latency:** 1-2ms for monosynaptic reflexes (knee-jerk), 10-50ms for polysynaptic (withdrawal)
- **Involuntary:** Cannot be suppressed by conscious effort (though can be modulated)
- **Hardwired:** The circuit is anatomical, not learned
- **Local:** Processing happens at the spinal cord, not the brain

### Robot Reflex Arc Mapping

```
Biological:    Sensor → Spinal Cord → Motor Neuron → Muscle
armOS:         Servo Telemetry → Reflex Engine (local) → Servo Command → Motor
                                      ↓
                              Notify Governor (async)
```

The reflex engine runs **on the citizen itself** (Pi 5 for the follower arm). It does NOT send a message to the governor and wait for a response. It acts first, reports second.

### What Triggers Deserve Reflexes

Based on STS3215 capabilities and SO-101 failure modes:

| Trigger | Threshold | Reflex Action | Latency Budget |
|---------|-----------|---------------|----------------|
| **Overcurrent (single servo)** | >800mA sustained 50ms | Reduce that servo's velocity 50% | <10ms |
| **Overcurrent (total arm)** | >4000mA | Reduce all servo velocities 50% | <10ms |
| **Voltage collapse** | <6.0V on any servo | Disable torque on all servos | <5ms (critical) |
| **Temperature spike** | >60C on any servo | Reduce velocity 25%, warn | <100ms |
| **Temperature critical** | >70C | Disable torque on that servo | <10ms |
| **Position error** | Actual vs commanded >200 ticks for >100ms | Stop servo, report jam | <50ms |
| **Status error bits** | Any error bit set in register 65 | Log + appropriate response | <10ms |
| **Communication loss** | No telemetry read for 500ms | Disable all torque (existing watchdog) | 500ms |
| **Collision detection** | Load spike >80% in <20ms (derivative) | Reverse 10 ticks, hold | <20ms |

### Reflex Hierarchy (Non-negotiable ordering)

1. **Voltage collapse** — if power is dying, nothing else matters, kill torque
2. **Emergency stop** (governor command) — human override
3. **Overcurrent critical** — prevent hardware damage
4. **Temperature critical** — prevent hardware damage
5. **Collision detection** — prevent mechanical damage
6. **Overcurrent warning** — degrade gracefully
7. **Temperature warning** — degrade gracefully
8. **Position error / jam** — stop wasting energy

---

## 3. Stimulus-Response Mapping

### Declarative Reflex Rules

The key insight from rule-based systems: separate the **what** (condition-action pairs) from the **how** (evaluation engine). Reflexes should be *data*, not scattered if-statements.

**Proposed format:**

```python
@dataclass
class ReflexRule:
    id: str                          # "overcurrent_single"
    priority: int                    # Lower = higher priority (0 = highest)
    condition: ReflexCondition       # Evaluates telemetry -> bool
    action: ReflexAction             # What to do when triggered
    cooldown_ms: float               # Don't re-trigger within this window
    notify_governor: bool            # Send REPORT after firing
    description: str                 # Human-readable explanation

@dataclass
class ReflexCondition:
    sensor: str                      # "current_ma", "voltage", "temperature_c", "load_pct"
    scope: str                       # "per_servo" or "aggregate"
    operator: str                    # ">", "<", ">=", "<=", "derivative>"
    threshold: float                 # The trigger value
    sustain_ms: float = 0            # Must be true for this long (debounce)

@dataclass
class ReflexAction:
    action_type: str                 # "reduce_velocity", "disable_torque", "reverse", "hold"
    scope: str                       # "triggering_servo", "all_servos", "arm"
    parameter: float = 0.0           # e.g., 0.5 for 50% velocity reduction
    duration_ms: float = 0           # 0 = until cleared
```

**Example declarations:**

```python
REFLEX_TABLE = [
    ReflexRule(
        id="voltage_collapse",
        priority=0,
        condition=ReflexCondition("voltage", "per_servo", "<", 6.0),
        action=ReflexAction("disable_torque", "all_servos"),
        cooldown_ms=5000,
        notify_governor=True,
        description="Kill all torque if any servo voltage drops below 6V",
    ),
    ReflexRule(
        id="overcurrent_single",
        priority=2,
        condition=ReflexCondition("current_ma", "per_servo", ">", 800, sustain_ms=50),
        action=ReflexAction("reduce_velocity", "triggering_servo", parameter=0.5),
        cooldown_ms=1000,
        notify_governor=True,
        description="Halve servo speed if sustained overcurrent",
    ),
    ReflexRule(
        id="collision_detect",
        priority=4,
        condition=ReflexCondition("load_pct", "per_servo", "derivative>", 80, sustain_ms=0),
        action=ReflexAction("reverse", "triggering_servo", parameter=10),
        cooldown_ms=500,
        notify_governor=True,
        description="Reverse 10 ticks on sudden load spike (collision)",
    ),
]
```

### Why Declarative Matters

1. **Inspectable:** The governor can query "what reflexes are active?" and display them on the dashboard
2. **Configurable:** The constitution can ship reflex thresholds — different arms can have different limits
3. **Testable:** Unit tests can feed synthetic telemetry and verify the correct reflex fires
4. **Auditable:** Every reflex firing is logged with the rule ID, condition values, and action taken

### Rule Engine Evaluation

The reflex engine runs a tight loop:

```
while running:
    telemetry = read_telemetry(bus)           # ~3-5ms for 6 servos
    for rule in sorted(REFLEX_TABLE, key=priority):
        if rule.evaluate(telemetry):
            rule.execute(bus)
            rule.notify(governor)              # async, non-blocking
            break                              # highest-priority rule wins
    sleep_remaining_budget()                   # target 100Hz = 10ms cycle
```

**Critical:** The `break` after first match means only one reflex fires per cycle. This prevents conflicting actions (e.g., "reduce velocity" and "disable torque" simultaneously). The highest-priority rule always wins.

---

## 4. Reflex vs. Deliberation

### The Three-Layer Hybrid Architecture

The robotics community converged on a standard pattern called the **three-layer architecture** (Gat, 1998):

```
┌─────────────────────────────────┐
│     Deliberative Layer          │  Plans, reasons, optimizes
│     (Governor / Policy)         │  Latency: 100ms - seconds
├─────────────────────────────────┤
│     Sequencing Layer            │  Coordinates behaviors, monitors
│     (Citizen task executor)     │  Latency: 10-100ms
├─────────────────────────────────┤
│     Reactive Layer              │  Reflexes, hardcoded responses
│     (Reflex Engine)             │  Latency: <10ms
└─────────────────────────────────┘
```

### How Reflexes Interact With Plans

**Scenario:** The arm is executing a pick-and-place policy. Shoulder_lift servo hits overcurrent.

1. **Reflex fires** (< 10ms): Shoulder_lift velocity reduced 50%
2. **Reflex notifies sequencing layer** (~10ms): "Reflex OVERCURRENT_SINGLE fired on shoulder_lift"
3. **Sequencing layer decides** (~50ms):
   - Is the task still feasible at reduced speed? → Continue with adapted trajectory
   - Has the object been dropped? → Abort and report
   - Is this a recurring fault? → Check immune memory, escalate
4. **Deliberative layer informed** (~100ms): Governor gets REPORT, can issue new directive

**Key principle:** The reflex does NOT ask permission. It acts, then the plan adapts. This is the "beg forgiveness, not permission" pattern — but for safety, not social etiquette.

### Reflex Recovery States

After a reflex fires, the system enters a **recovery state**:

```
NORMAL → [reflex triggers] → REFLEX_ACTIVE → [condition clears] → RECOVERY → NORMAL
                                    ↓                                   ↑
                              [condition persists]              [recovery timeout]
                                    ↓                                   ↑
                              REFLEX_ESCALATED → [governor intervenes] ─┘
```

- **REFLEX_ACTIVE:** The mitigation is in effect. The plan is paused or degraded.
- **RECOVERY:** The trigger condition cleared. Gradually restore normal operation (don't snap back to full speed — ramp up over 500ms).
- **REFLEX_ESCALATED:** The condition persisted beyond the reflex's capability (e.g., temperature keeps rising despite reduced speed). Governor must intervene.

### Plan Adaptation Patterns

| Reflex Outcome | Plan Response |
|----------------|---------------|
| Transient (fired and cleared in <1s) | Resume plan, log event |
| Sustained (>1s, then cleared) | Rewind plan 1 step, retry with caution |
| Escalated (governor notified) | Abort current task, safe position |
| Repeated (3+ times in 60s) | Create immune memory entry, notify governor |

---

## 5. Sensor Fusion for Reflex Triggers

### The False Positive Problem

Single-sensor reflexes produce false positives:
- **High current alone** could be normal heavy load (picking up an object)
- **High temperature alone** could be ambient heat
- **Position error alone** could be backlash in the gears

### Multi-Sensor Reflex Conditions

The solution is **compound conditions** — multiple sensor inputs that together indicate a real problem:

| Condition | Meaning | Reflex |
|-----------|---------|--------|
| High current + high temperature | Overload (thermal confirmation) | Reduce speed, definite |
| High current + normal temperature | Heavy load, probably fine | Monitor, don't trigger |
| High current + position error | Jam/collision (servo straining but not moving) | Stop servo immediately |
| Voltage drop + high total current | Power supply overloaded | Reduce all servos |
| Voltage drop + low current | Bad connection or dying battery | Warn, prepare for shutdown |
| Load spike (derivative) + no command change | External collision | Reverse and hold |
| Load spike (derivative) + command change | Expected load from movement | Ignore |

### Implementation: Compound Conditions

Extend the ReflexCondition to support AND/OR composition:

```python
@dataclass
class CompoundCondition:
    operator: str  # "AND", "OR"
    conditions: list[ReflexCondition | CompoundCondition]

# Example: Jam detection
jam_detection = CompoundCondition(
    operator="AND",
    conditions=[
        ReflexCondition("current_ma", "per_servo", ">", 600, sustain_ms=100),
        ReflexCondition("position_error", "per_servo", ">", 50, sustain_ms=100),
    ]
)
```

### Derivative-Based Triggers

Some reflexes need rate-of-change, not absolute values. The reflex engine must maintain a **rolling window** of recent telemetry (last 10 readings at 100Hz = 100ms history):

```python
class TelemetryWindow:
    def __init__(self, size=10):
        self.buffer = deque(maxlen=size)

    def derivative(self, field: str, servo: str) -> float:
        """Compute rate of change per second for a sensor field."""
        if len(self.buffer) < 2:
            return 0.0
        newest = getattr(self.buffer[-1].snapshots[servo], field)
        oldest = getattr(self.buffer[0].snapshots[servo], field)
        dt = self.buffer[-1].timestamp - self.buffer[0].timestamp
        if dt == 0:
            return 0.0
        return (newest - oldest) / dt
```

This enables collision detection: "load went from 10% to 85% in 20ms" is a collision. "Load is steady at 60%" is just a heavy object.

### Bayesian Confidence

For non-critical reflexes, a confidence score can prevent false positives:

```python
confidence = 0.0
if current > 600:
    confidence += 0.4
if temperature > 55:
    confidence += 0.3
if position_error > 30:
    confidence += 0.3

if confidence > 0.7:
    trigger_reflex()
```

**But:** For critical safety reflexes (voltage collapse, extreme overcurrent), there is NO confidence weighting. Single-condition trigger. Better a false positive that cuts torque than a false negative that fries a servo.

---

## 6. Distributed Reflexes

### Sympathetic Reflexes in Multi-Robot Systems

Biological analogy: when one person in a group stumbles, nearby people instinctively brace or step back. This is a **sympathetic reflex** — triggered not by your own sensors, but by observing another agent's distress.

### armOS Implementation: Mycelium + Reflexes

The existing mycelium warning network already provides the propagation channel. The missing piece is **receiver-side reflexes** — when a citizen receives a warning, it should trigger a local reflex, not just log it.

**Proposed distributed reflex types:**

| Source Event | Propagation | Receiver Reflex |
|-------------|-------------|-----------------|
| Robot A: voltage collapse | EMERGENCY multicast | Robot B in same workspace: reduce speed 50% |
| Robot A: collision detected | CRITICAL multicast | Robot B nearby: pause for 200ms, then resume cautiously |
| Robot A: servo overtemp | WARNING in heartbeat | Robot B: no action (not contagious) |
| Robot A: communication lost | EMERGENCY (from governor) | All robots: hold position |
| Robot A: task failed with jam | REPORT | Robot B doing same task: adjust approach angle |

### Spatial Awareness for Distributed Reflexes

Not all robots should react to all warnings. A robot across the room doesn't need to slow down because a robot at the workbench detected a collision. This requires **workspace zones**:

```python
@dataclass
class WorkspaceZone:
    id: str
    citizens: list[str]  # pubkeys of citizens in this zone

# Reflexes propagate within a zone, not globally
# Exception: EMERGENCY always propagates globally
```

### Cascade Prevention

Distributed reflexes can cascade: A slows down, B detects A is slow and also slows down, C sees both slow and stops entirely. This is the "phantom traffic jam" problem.

**Mitigation:**
- Tag every warning with `origin_citizen` and `hop_count`
- Sympathetic reflexes set `hop_count += 1`
- Reflexes with `hop_count > 1` are **not re-propagated** (damping)
- Sympathetic reflexes are always **weaker** than direct reflexes (e.g., 25% reduction vs 50%)

---

## 7. Practical Implementation

### What Exists in armOS Today

The codebase already has several reflex-adjacent systems:

1. **`telemetry.py` / `check_safety()`** — reads servo telemetry and checks against limits. But it only returns violation strings — it doesn't act on them.

2. **`mycelium.py`** — warning propagation with severity levels and mitigation factors. Already has the right severity model (INFO/WARNING/CRITICAL/EMERGENCY) and mitigation factors (1.0/0.75/0.50/0.0).

3. **`pi_citizen.py` / `_teleop_watchdog()`** — a basic reflex: "no teleop frames for 500ms → disable torque." This IS a reflex. It just needs to be generalized.

4. **`constitution.py` / `ServoLimits`** — defines hardware safety limits. These should feed into reflex thresholds.

5. **`immune.py`** — learns from faults. Reflexes that fire repeatedly should create immune memory entries.

### What's Missing

- **A dedicated reflex engine** that runs in a tight loop independent of the citizen's main async event loop
- **Declarative reflex rules** instead of scattered if-statements
- **Derivative/rate-of-change tracking** for collision detection
- **Reflex-to-plan interaction** — the plan layer doesn't know a reflex fired
- **Distributed reflex receivers** — mycelium warnings are logged but don't trigger local actions

### Existing Frameworks and Approaches

**ROS2 safety_node (Nav2):** A dedicated node that monitors sensor data and can override velocity commands. Runs independently from the planner. Publishes zero-velocity when safety conditions are violated. This is exactly the pattern we need, but we don't need ROS2 — we can implement the same idea in our asyncio citizen.

**ros-safety/software_watchdogs:** DDS QoS-based watchdogs that monitor heartbeats and declare nodes failed if heartbeats stop. Similar to our existing teleop watchdog but generalized.

**Hardware watchdog timers:** Many microcontrollers have hardware watchdog timers that reset the system if not "fed" regularly. The STS3215's built-in protection (overcurrent, overtemp, overvoltage in register 65) is essentially a hardware reflex. We should ensure these are enabled via EEPROM config AND have software reflexes as a second layer.

### Python at 100Hz: Is It Fast Enough?

**Yes, with caveats.**

- Reading 6 servos via serial at 1Mbaud takes ~3-5ms (each read is ~0.5ms round-trip)
- Python asyncio overhead for the reflex check is negligible (<0.1ms for rule evaluation)
- Total cycle: ~5ms read + ~0.1ms evaluate + ~0.5ms act = **~6ms, well within 10ms budget**
- **Risk:** Garbage collection pauses can add 1-5ms spikes. Mitigation: use `gc.disable()` in the reflex loop and manually collect between cycles, or use `gc.set_threshold()` to reduce frequency.
- **Risk:** The serial bus is shared between teleop commands and telemetry reads. Need a bus lock or dedicated time slots.

### Proposed Architecture

```
┌─────────────────────────────────────────────┐
│           pi_citizen.py (async main loop)    │
│                                              │
│  ┌──────────────────────┐  ┌──────────────┐ │
│  │  Task Executor       │  │  Governor     │ │
│  │  (policy inference)  │  │  Comms        │ │
│  └──────────┬───────────┘  └──────┬───────┘ │
│             │                      │         │
│  ┌──────────▼──────────────────────▼───────┐ │
│  │        Sequencing Layer                  │ │
│  │  (coordinates tasks, handles recovery)   │ │
│  └──────────┬──────────────────────────────┘ │
│             │                                │
│  ┌──────────▼──────────────────────────────┐ │
│  │        REFLEX ENGINE (reflex.py)         │ │
│  │                                          │ │
│  │  ┌─────────────┐  ┌──────────────────┐  │ │
│  │  │ Telemetry   │  │ Reflex Table     │  │ │
│  │  │ Window      │  │ (declarative     │  │ │
│  │  │ (last 10    │  │  rules from      │  │ │
│  │  │  readings)  │  │  constitution)   │  │ │
│  │  └──────┬──────┘  └────────┬─────────┘  │ │
│  │         │    evaluate()    │             │ │
│  │         └────────┬─────────┘             │ │
│  │                  ▼                       │ │
│  │         ┌────────────────┐               │ │
│  │         │ Fire reflex    │───→ Mycelium  │ │
│  │         │ (direct servo  │    (notify    │ │
│  │         │  command)      │    governor)  │ │
│  │         └────────────────┘               │ │
│  └──────────────────────────────────────────┘ │
│                      │                        │
│              ┌───────▼───────┐                │
│              │  Serial Bus   │                │
│              │  (STS3215)    │                │
│              └───────────────┘                │
└───────────────────────────────────────────────┘
```

### Implementation Priority

1. **`reflex.py`** — The reflex engine module with declarative rules, telemetry window, and evaluation loop
2. **Wire reflex engine into `pi_citizen.py`** — Replace the ad-hoc watchdog with the general reflex engine
3. **Feed constitution's `ServoLimits` into reflex thresholds** — Single source of truth
4. **Add derivative tracking** — Enable collision detection
5. **Add distributed reflex receivers** — When mycelium warnings arrive, evaluate local reflex response
6. **Connect to immune memory** — Repeated reflexes become learned fault patterns

### STS3215-Specific Notes

The STS3215 has built-in hardware protections (register-level):
- Overcurrent protection (configurable threshold)
- Overtemperature shutdown
- Overvoltage/undervoltage lockout
- Overload protection (torque-based)

These are the **first line of defense** (hardware reflexes). Our software reflexes are the **second line** — they should trigger at LOWER thresholds than the hardware, so the software can degrade gracefully before the hardware does an abrupt shutdown.

```
Software reflex threshold < Hardware protection threshold

Example:
  Software: reduce speed at 800mA    (graceful degradation)
  Hardware: shutdown at 1000mA        (hard cutoff, last resort)
```

---

## Key Takeaways for armOS

1. **Reflexes are not optional.** Every robot that interacts with the physical world needs them. They are Article 3 of the constitution ("Self-Preservation") made executable.

2. **Reflexes bypass the governor.** This is the fundamental architectural decision. The reflex engine runs locally on each citizen and acts on the bus directly. The governor is notified after the fact.

3. **Declarative rules, not scattered if-statements.** The reflex table should be data — loadable from the constitution, inspectable from the dashboard, testable with synthetic telemetry.

4. **Compound conditions reduce false positives.** High current alone is not always a problem. High current + position error = jam. High current + high temperature = overload. The reflex engine must support AND/OR composition.

5. **The existing codebase is 70% there.** `telemetry.py` reads the sensors. `check_safety()` has the right logic but wrong integration — it returns strings instead of triggering actions. `mycelium.py` has the propagation channel. The teleop watchdog is a reflex that needs to be generalized.

6. **Python at 100Hz is feasible.** The serial bus read is the bottleneck (~5ms for 6 servos), not Python. The reflex evaluation adds negligible overhead.

7. **Distributed reflexes need damping.** Sympathetic reflexes propagate within workspace zones, decay with hop count, and are weaker than direct reflexes. This prevents cascade failures.

---

## Sources

- [Subsumption Architecture — Wikipedia](https://en.wikipedia.org/wiki/Subsumption_architecture)
- [Robot Architectures — Brown CS148](https://cs.brown.edu/people/tdean/courses/cs148/02/architectures.html)
- [A Brief Introduction to Behavior-Based Robotics — EPFL](https://baibook.epfl.ch/exercises/behaviorBasedRobotics/BBSummary.pdf)
- [Servo Collision Detection Control System Based on Robot Dynamics — PMC/MDPI Sensors](https://pmc.ncbi.nlm.nih.gov/articles/PMC11859132/)
- [A Tactile Reflex Arc for Physical Human-Robot Interaction — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0957415825000169)
- [Reflex Control for Robot System Preservation, Reliability and Autonomy — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/0045790694900337)
- [Reflex Control for Safe Autonomous Robot Operation — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0951832096000440)
- [Declarative Rule-Based Safety for Robotic Perception Systems — ResearchGate](https://www.researchgate.net/publication/323446593_Declarative_Rule-based_Safety_for_Robotic_Perception_Systems)
- [Towards Online Safety Corrections for Robotic Manipulation Policies — arXiv](https://arxiv.org/html/2409.08233)
- [Reactive vs. Deliberative Agents — CMU](https://www.cs.cmu.edu/afs/cs/usr/pstone/public/papers/97MAS-survey/node14.html)
- [Hybrid Deliberative/Reactive Systems — UTK](https://web.eecs.utk.edu/~leparker/Courses/CS594-spring07/Lectures/Mar-27-Hybrid.pdf)
- [The Cognitive Controller: A Hybrid Deliberative/Reactive Architecture — SpringerLink](https://link.springer.com/chapter/10.1007/978-3-540-24677-0_113)
- [Collaborative Safe Formation Control for Coupled Multi-Agent Systems — arXiv](https://arxiv.org/abs/2311.11156)
- [Multi-Sensor Fusion Techniques for Improved Perception in Robotics — TechNexion](https://www.technexion.com/resources/multi-sensor-fusion-techniques-for-improved-perception-in-robotics/)
- [Behavior Trees in Robotics and AI: An Introduction — arXiv](https://arxiv.org/abs/1709.00084)
- [Behavior Trees for Smart Robots — Wiley](https://onlinelibrary.wiley.com/doi/10.1155/2022/3314084)
- [Nav2 Safety Node — ROS2 Navigation](https://navigation.ros.org/2021summerOfCode/projects/safety_node.html)
- [ROS2 Software Watchdogs — GitHub](https://github.com/ros-safety/software_watchdogs)
- [ST3215 Servo — Waveshare Wiki](https://www.waveshare.com/wiki/ST3215_Servo)
- [python-st3215 — GitHub](https://github.com/Mickael-Roger/python-st3215)
- [Feetech STS3215 Servo Hardware Tutorial — Hugging Face Forums](https://discuss.huggingface.co/t/feetech-sts3215-servo-hardware-tutorial/173674)
- [Sensor-Based Control for Collaborative Robots — Frontiers](https://www.frontiersin.org/articles/10.3389/fnbot.2020.576846/full)
- [Overload/Overcurrent Protection for Servos — Arduino Forum](https://forum.arduino.cc/t/overload-overcurrent-protection-for-servos/694082)
- [Swarm Robotic Behaviors and Current Applications — Frontiers](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2020.00036/full)
