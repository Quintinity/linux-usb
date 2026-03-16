---
project: armOS v4.0 "The Living Machine"
date: 2026-03-16
status: draft
inputDocuments:
  - product-brief-v4.md
  - citizenry/SOUL.md
  - citizenry/RESEARCH-robot-memory.md
  - citizenry/RESEARCH-reflexes.md
  - citizenry/RESEARCH-pain-proprioception-sleep.md
  - citizenry/RESEARCH-spatial-awareness.md
  - citizenry/GROWTH.md
  - docs/research-robot-metabolism.md
---

# Architecture --- armOS v4.0: "The Living Machine"

## Overview

v4.0 adds 10 new modules to the citizenry package, implementing biological subsystems that make each citizen a living entity. All new behavior is expressed through the existing 7-message protocol --- no transport or protocol changes. New data rides in the body fields of HEARTBEAT, REPORT, PROPOSE, ACCEPT_REJECT, and GOVERN messages. The architecture follows the same patterns established in v1.5--v3.0: asyncio event loop, UDP multicast + unicast, Ed25519 signing, JSON persistence.

The 10 new modules form a "biological layer" beneath and beside the existing governance and marketplace systems:

| Module | Biological Analog | Engineering Problem Solved |
|--------|------------------|---------------------------|
| `soul.py` | Identity + personality | Persistent individuality, behavioral divergence |
| `memory.py` | Hippocampus + cortex | Event recall, knowledge graphs, learned procedures |
| `improvement.py` | Meta-cognition | Self-optimization, strategy selection, practice |
| `reflex.py` | Spinal cord | Sub-10ms safety responses without governor |
| `metabolism.py` | Metabolism | Power budgeting, brownout protection, duty cycling |
| `pain.py` | Nociception | Avoidance learning from damage events |
| `proprioception.py` | Body awareness | Forward kinematics, body schema, force estimation |
| `sleep_cycle.py` | Sleep | Memory consolidation, calibration, maintenance |
| `spatial.py` | Spatial cognition | Collision avoidance, zone management, flight plans |
| `growth.py` | Maturation | Developmental stages, earned autonomy |

**Constraint:** No new protocol message types. No new dependencies beyond numpy (and optionally `cma` for CMA-ES). Pure Python. Must not break v3.0 backward compatibility.

---

## System Architecture

```
+==============================================================================+
|                         SURFACE PRO 7 (Governor)                             |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                   Governance Intelligence (v3.0)                        |  |
|  |  NLPolicyInterp | RolloutEngine | WillArchive | ConsciousnessStream    |  |
|  +------------------------------------------------------------------------+  |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                   Biological Layer (v4.0)                               |  |
|  |                                                                         |  |
|  |  +----------+  +-----------+  +----------+  +----------+  +----------+ |  |
|  |  |  Soul    |  |  Memory   |  | Growth   |  | Spatial  |  |Improvmnt | |  |
|  |  | (governor|  | (governor |  | (fleet   |  | (zone    |  | (fleet   | |  |
|  |  |  soul)   |  |  memory)  |  |  tracker)|  |  manager)|  |  stats)  | |  |
|  |  +----------+  +-----------+  +----------+  +----------+  +----------+ |  |
|  +------------------------------------------------------------------------+  |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                   SurfaceCitizen (governor)                             |  |
|  |  v1.5: identity, heartbeat, discovery, constitution, teleop            |  |
|  |  v2.0: marketplace, composition, genome, immune, skills, symbiosis     |  |
|  |  v3.0: nl_governance, rollout_engine, will, emotional, consciousness   |  |
|  |  v4.0: soul, memory, growth (fleet view), spatial (zone manager)       |  |
|  +------------------------------------------------------------------------+  |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                   Transport Layer (unchanged)                           |  |
|  |  MulticastTransport (UDP 239.67.84.90:7770) | UnicastTransport         |  |
|  +------------------------------------------------------------------------+  |
+==============================================================================+
                              | LAN |
+==============================================================================+
|                      RASPBERRY PI 5 (Follower)                               |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                   Biological Layer (v4.0)                               |  |
|  |                                                                         |  |
|  |  +----------+  +-----------+  +---------+  +----------+  +----------+  |  |
|  |  |  Soul    |  |  Memory   |  | Reflex  |  | Metabol- |  |  Pain    |  |  |
|  |  | (citizen |  | (episodic |  | Engine  |  | ism      |  | (noci-   |  |  |
|  |  |  soul)   |  |  + proc.) |  | (100Hz) |  | (power)  |  |  ception)|  |  |
|  |  +----------+  +-----------+  +---------+  +----------+  +----------+  |  |
|  |                                                                         |  |
|  |  +----------+  +-----------+  +---------+  +----------+  +----------+  |  |
|  |  | Proprio- |  | Sleep     |  | Spatial |  | Growth   |  |Improvmnt |  |  |
|  |  | ception  |  | Cycle     |  | (self-  |  | (local   |  | (self-   |  |  |
|  |  | (FK/body)|  | (4-phase) |  |  coll.) |  |  stage)  |  |  optim.) |  |  |
|  |  +----------+  +-----------+  +---------+  +----------+  +----------+  |  |
|  +------------------------------------------------------------------------+  |
|                                                                              |
|  +------------------------------------------------------------------------+  |
|  |                      PiCitizen (manipulator)                            |  |
|  |  v1.5: identity, heartbeat, servo control, teleop execution            |  |
|  |  v2.0: skills, immune, mycelium, genome, contracts, bidding            |  |
|  |  v3.0: self_test, will, canary_mode, emotional                         |  |
|  |  v4.0: soul, memory, reflex, metabolism, pain, proprioception,         |  |
|  |        sleep_cycle, spatial, growth, improvement                        |  |
|  |                                                                         |  |
|  |  Feetech STS3215 Servo Bus                                             |  |
|  +------------------------------------------------------------------------+  |
+==============================================================================+
```

### Layer Interaction Model

The biological modules form three layers with distinct timing requirements:

```
+----------------------------------------------------------------------+
|  DELIBERATIVE LAYER (100ms - seconds)                                |
|  Governor directives | Task planning | Marketplace bidding           |
|  soul.py (goal selection) | memory.py (recall) | growth.py           |
|  improvement.py (strategy selection) | sleep_cycle.py (scheduling)   |
+----------------------------------------------------------------------+
        |  inform / constrain
+----------------------------------------------------------------------+
|  SEQUENCING LAYER (10-100ms)                                         |
|  Task execution | Trajectory following | Spatial coordination        |
|  spatial.py (flight plans, zone checks) | pain.py (avoidance zones)  |
|  metabolism.py (power budgeting) | proprioception.py (body state)    |
+----------------------------------------------------------------------+
        |  override / degrade
+----------------------------------------------------------------------+
|  REACTIVE LAYER (<10ms)                                              |
|  reflex.py (100Hz telemetry loop, declarative rules)                 |
|  Cannot be suppressed by higher layers                               |
|  Acts first, notifies governor async                                 |
+----------------------------------------------------------------------+
        |
+----------------------------------------------------------------------+
|  HARDWARE                                                            |
|  STS3215 servo bus | Telemetry registers | Hardware protection       |
+----------------------------------------------------------------------+
```

---

## Module Architecture

### New file map and dependencies

```
citizenry/
  soul.py             NEW  depends on: identity.py, genome.py, constitution.py
  memory.py           NEW  depends on: genome.py, persistence.py
  improvement.py      NEW  depends on: memory.py, skills.py, genome.py
  reflex.py           NEW  depends on: telemetry.py, constitution.py, mycelium.py
  metabolism.py        NEW  depends on: telemetry.py, genome.py
  pain.py             NEW  depends on: reflex.py, memory.py, proprioception.py
  proprioception.py   NEW  depends on: genome.py (link lengths), numpy
  sleep_cycle.py      NEW  depends on: memory.py, immune.py, genome.py, calibration.py
  spatial.py          NEW  depends on: proprioception.py, protocol.py, numpy
  growth.py           NEW  depends on: skills.py, genome.py, memory.py
```

### Dependency graph

```
                   constitution.py     identity.py
                        |                  |
                        v                  v
protocol.py         soul.py <----------genome.py
    |                  |                   ^
    v                  v                   |
transport.py     memory.py ----------> persistence.py
    |               ^  ^  ^
    v               |  |  |
telemetry.py        |  |  +--- improvement.py <--- skills.py
    |               |  |
    v               |  +------- sleep_cycle.py <--- immune.py, calibration.py
reflex.py           |
    |               +---------- pain.py <---------- proprioception.py
    v                                                     |
mycelium.py                                               v
                                                      spatial.py
                   growth.py <--- skills.py, memory.py, genome.py
```

---

## Module Specifications

### 1. soul.py --- Identity, Personality, Purpose, Values

```python
@dataclass
class PersonalityProfile:
    """OCEAN-based personality with armOS behavioral dimensions."""
    # Big Five (0.0 to 1.0)
    openness: float = 0.5
    conscientiousness: float = 0.7
    extraversion: float = 0.5
    agreeableness: float = 0.7
    neuroticism: float = 0.3
    # armOS dimensions
    movement_style: float = 0.5      # 0=cautious, 1=fast
    exploration_drive: float = 0.5
    social_drive: float = 0.5
    teaching_drive: float = 0.5
    independence: float = 0.5
    drift_rate: float = 0.01         # Per 1000 interactions

    def mutate(self, trait: str, delta: float): ...

class GoalPriority(Enum):
    SURVIVAL = 0
    OBLIGATION = 1
    COMMITMENT = 2
    ASPIRATION = 3
    CURIOSITY = 4

@dataclass
class Goal:
    id: str
    description: str
    priority: GoalPriority
    parent_id: str | None = None
    progress: float = 0.0
    skill_required: str | None = None
    intrinsic_reward: float = 0.0

class GoalHierarchy:
    """BDI-inspired goal management with intrinsic motivation."""
    def __init__(self, personality: PersonalityProfile): ...
    def select_next_goal(self) -> Goal | None: ...
    def _generate_intrinsic_goal(self) -> Goal: ...

@dataclass
class BehavioralPreferences:
    """Learned preferences that define HOW a citizen performs tasks."""
    speed_preference: float = 0.5
    smoothness: float = 0.7
    precision_priority: float = 0.5
    grip_force_bias: float = 0.5
    preferred_approach_angle: float = 0.0
    retry_patience: int = 3
    task_success_by_style: dict = field(default_factory=dict)

    def update_from_outcome(self, task_type, style_params, success, quality): ...

@dataclass
class ValueSystem:
    """Three-tier value system: constitutional (immutable), normative
    (governor-mutable), learned (self-mutable)."""
    risk_tolerance: float = 0.3
    autonomy_level: float = 0.5
    resource_sharing: float = 0.7
    trust_scores: dict[str, float] = field(default_factory=dict)
    cooperation_value: float = 0.5
    caution_value: float = 0.5

    def check_action(self, action: str, context: dict) -> tuple[bool, str]: ...
    def update_trust(self, citizen_pubkey: str, outcome: float): ...

@dataclass
class LifeEvent:
    timestamp: float
    event_type: str     # "born", "first_task", "hardware_swap", "achievement", ...
    description: str
    emotional_impact: float  # -1.0 to 1.0
    participants: list[str]

@dataclass
class Soul:
    """The persistent core identity of a citizen."""
    private_key_path: str
    pubkey: str
    birth_timestamp: float
    birth_hardware: dict
    name: str
    personality: PersonalityProfile
    preferences: BehavioralPreferences
    goals: GoalHierarchy
    values: ValueSystem
    autobiography: list[LifeEvent]
    relationships: dict[str, float]
    hardware_changes: list[dict]
    incarnation: int = 1

    def continuity_score(self) -> float: ...
```

**Personality seeding:** On first boot, personality is derived from genome (hardware type, role) plus small random perturbation. Manipulators start with high conscientiousness. Cameras start with high openness.

**Personality affects behavior:** Personality biases marketplace bidding (high-conscientiousness bids with quality guarantee), idle behavior (high-openness explores new movements), and collaboration (high-extraversion volunteers for multi-arm tasks).

**Identity rule:** Private key = soul. Genome = knowledge (shareable). Cloning genome = child, not resurrection. If the key is destroyed, the citizen is dead.

---

### 2. memory.py --- Episodic, Semantic, Procedural Memory

```python
@dataclass
class Episode:
    id: str                  # UUID
    timestamp: float
    citizen_id: str
    location: str            # Zone/station ID
    event_type: str          # pick, place, navigate, fail, ...
    description: str
    context: dict            # Objects, forces, sensor readings
    outcome: str             # success / failure / partial
    importance: float        # 0.0-1.0
    tags: list[str]

class EpisodicMemory:
    """What-Where-When-Outcome event store."""
    def __init__(self, citizen_name: str, max_episodes: int = 10000): ...
    def record(self, episode: Episode): ...
    def recall(self, query_tags: list[str], limit: int = 10) -> list[Episode]: ...
    def recall_failures(self, skill_name: str = None, limit: int = 5) -> list[Episode]: ...
    def prune(self, max_age_days: int = 7, min_importance: float = 0.2): ...

@dataclass
class KnowledgeNode:
    id: str                  # e.g., "object:red_block_1"
    node_type: str           # object, location, agent, concept
    properties: dict
    confidence: float
    last_updated: float
    source_episodes: list[str]

@dataclass
class KnowledgeEdge:
    source: str
    target: str
    relation: str            # located_at, heavier_than, near, causes, ...
    confidence: float
    last_updated: float

class SemanticMemory:
    """JSON property graph knowledge store."""
    def __init__(self, citizen_name: str): ...
    def learn_fact(self, subject, relation, obj, confidence=0.8): ...
    def query(self, subject=None, relation=None, obj=None) -> list[KnowledgeEdge]: ...
    def decay_stale(self, half_life_days: float = 30.0): ...

@dataclass
class Procedure:
    id: str
    skill_name: str
    parameters: dict         # approach_angle, grip_force, speed, ...
    success_rate: float
    avg_duration: float
    context_conditions: dict # When to use this procedure
    use_count: int

class ProceduralMemory:
    """How-to-do-it parameter recipes per skill per context."""
    def __init__(self, citizen_name: str): ...
    def get_best_procedure(self, skill_name: str, context: dict) -> Procedure | None: ...
    def record_outcome(self, procedure_id: str, success: bool, duration: float): ...
    def add_procedure(self, skill_name: str, parameters: dict, context: dict) -> str: ...

class CitizenMemory:
    """Unified memory facade."""
    def __init__(self, citizen_name: str):
        self.episodic = EpisodicMemory(citizen_name)
        self.semantic = SemanticMemory(citizen_name)
        self.procedural = ProceduralMemory(citizen_name)

    def record_episode(self, ...): ...
    def recall_episodes(self, ...): ...
    def get_best_procedure(self, ...): ...
    def learn_fact(self, ...): ...
    async def consolidate(self): ...     # Called by sleep_cycle
    def get_shareable_knowledge(self, since=None) -> list[KnowledgeEdge]: ...
    def merge_remote_knowledge(self, edges, source_trust: float): ...
    def save(self): ...
    def load(self): ...
```

**Retrieval scoring** (simplified for edge, no embeddings):

```python
def retrieval_score(episode, query_tags, now):
    recency = exp(-0.01 * (now - episode.timestamp) / 3600)
    importance = episode.importance
    tag_overlap = len(set(episode.tags) & set(query_tags)) / max(len(query_tags), 1)
    return 0.3 * recency + 0.3 * importance + 0.4 * tag_overlap
```

**Fleet sharing:** High-confidence semantic knowledge is gossipped via REPORT bodies with `type: "knowledge_gossip"`. Receiving citizens merge weighted by sender trust. No new message types.

---

### 3. improvement.py --- Self-Optimization

```python
class PerformanceTracker:
    """Sliding window success rate per skill. Trend detection."""
    def __init__(self): ...
    def record(self, skill_name: str, success: bool, quality: float): ...
    def success_rate(self, skill_name: str, window: int = 50) -> float: ...
    def trend(self, skill_name: str) -> str: ...  # "improving", "stable", "degrading"

class StrategySelector:
    """UCB1 multi-armed bandit per task type."""
    def __init__(self): ...
    def select(self, task_type: str) -> dict: ...    # Returns strategy params
    def update(self, task_type: str, strategy: dict, reward: float): ...

class ParameterEvolution:
    """CMA-ES for continuous skill parameters (optional cma dep)."""
    def __init__(self, param_names: list[str], sigma: float = 0.3): ...
    def ask(self) -> dict: ...           # Propose parameter set
    def tell(self, params: dict, fitness: float): ...

class FailureAnalyzer:
    """Telemetry diff at failure time -> hypothesis -> corrective action."""
    def analyze(self, episode: Episode, telemetry_window: list) -> dict: ...

class PracticeMode:
    """Idle citizens generate practice goals from learning-progress heuristic."""
    def __init__(self, memory: CitizenMemory, performance: PerformanceTracker): ...
    def suggest_practice_goal(self) -> Goal: ...
```

**Integration with soul:** PracticeMode generates CURIOSITY-priority goals fed into `GoalHierarchy.goals`. The personality's `exploration_drive` biases whether practice focuses on known skills (exploitation) or new variations (exploration).

---

### 4. reflex.py --- 100Hz Reactive Safety Layer

```python
@dataclass
class ReflexCondition:
    sensor: str              # "current_ma", "voltage", "temperature_c", "load_pct"
    scope: str               # "per_servo" or "aggregate"
    operator: str            # ">", "<", ">=", "<=", "derivative>"
    threshold: float
    sustain_ms: float = 0    # Debounce

@dataclass
class CompoundCondition:
    operator: str            # "AND", "OR"
    conditions: list[ReflexCondition | "CompoundCondition"]

@dataclass
class ReflexAction:
    action_type: str         # "reduce_velocity", "disable_torque", "reverse", "hold"
    scope: str               # "triggering_servo", "all_servos", "arm"
    parameter: float = 0.0
    duration_ms: float = 0

@dataclass
class ReflexRule:
    id: str
    priority: int            # 0 = highest
    condition: ReflexCondition | CompoundCondition
    action: ReflexAction
    cooldown_ms: float
    notify_governor: bool
    description: str

class TelemetryWindow:
    """Rolling buffer of last N telemetry readings for derivative triggers."""
    def __init__(self, size: int = 10): ...
    def push(self, telemetry): ...
    def derivative(self, field: str, servo: str) -> float: ...

class ReflexEngine:
    """100Hz telemetry loop with declarative reflex rules."""
    def __init__(self, rules: list[ReflexRule], bus, mycelium): ...
    async def run(self): ...             # Tight async loop targeting 10ms cycle
    def evaluate(self, telemetry) -> ReflexRule | None: ...
    def fire(self, rule: ReflexRule, telemetry): ...
    def add_rule(self, rule: ReflexRule): ...
    def remove_rule(self, rule_id: str): ...

# Default reflex table
REFLEX_TABLE: list[ReflexRule] = [
    # Priority 0: Voltage collapse -> kill all torque
    # Priority 1: Emergency stop (governor override)
    # Priority 2: Overcurrent critical (>1200mA sustained 20ms)
    # Priority 3: Temperature critical (>70C)
    # Priority 4: Collision detection (load derivative >80% in <20ms)
    # Priority 5: Overcurrent warning (>800mA sustained 50ms)
    # Priority 6: Temperature warning (>60C)
    # Priority 7: Position error / jam (>200 ticks for >100ms)
]
```

**Timing budget (10ms cycle):**
- Telemetry read (6 servos via serial at 1Mbaud): ~5ms
- Rule evaluation: <0.1ms
- Action dispatch: ~0.5ms
- Headroom: ~4.4ms

**GC strategy:** `gc.set_threshold()` tuned to avoid pauses in the reflex loop. Manual `gc.collect()` between cycles if headroom permits.

**Distributed reflexes:** When a reflex fires at CRITICAL or EMERGENCY severity, a REPORT is multicast with `type: "reflex_fired"`. Neighboring citizens in the same workspace zone trigger sympathetic reflexes (weaker: 25% speed reduction vs 50%). Hop count capped at 1 to prevent cascade.

---

### 5. metabolism.py --- Power Budgeting

```python
@dataclass
class MetabolicState:
    current_power_w: float = 0.0
    current_draw_a: float = 0.0
    power_1s: float = 0.0
    power_10s: float = 0.0
    power_60s: float = 0.0
    metabolic_state: str = "idle"       # idle, resting, active, peak, critical
    energy_consumed_wh: float = 0.0

    def classify(self, psu_max_w: float = 60.0) -> str: ...

class BrownoutProtocol:
    """4-stage voltage threshold protection."""
    STAGE_NORMAL = "normal"             # >10V
    STAGE_WARNING = "warning"           # 8-10V: reduce speed 50%
    STAGE_BROWNOUT = "brownout"         # 6-8V: disable non-critical, 50% torque
    STAGE_CRITICAL = "critical"         # <6V: emergency torque off

    def evaluate(self, min_voltage: float) -> str: ...
    def respond(self, stage: str, citizen): ...

class PowerLedger:
    """Multi-citizen PSU-aware admission control."""
    def __init__(self, psu_max_a: float = 5.0): ...
    def can_allocate(self, citizen_id: str, required_a: float) -> bool: ...
    def allocate(self, citizen_id: str, amps: float) -> bool: ...
    def release(self, citizen_id: str): ...

class DutyCycleTracker:
    """Per-servo load fraction over time. Recommends rest."""
    def __init__(self, load_threshold_pct: float = 30.0): ...
    def update(self, load_pct: float): ...
    @property
    def duty_cycle_1h(self) -> float: ...
    def should_rest(self) -> bool: ...   # >70% of last hour under load
```

**Integration with marketplace:** `MetabolicState` is included in heartbeat body. Power headroom becomes a bidding dimension. Citizens in "peak" or "critical" metabolic state refuse new bids. `PowerLedger` lives on the governor for multi-arm PSU-aware admission control.

**Integration with reflex.py:** BrownoutProtocol stages WARNING and above trigger reflex rules. CRITICAL triggers voltage_collapse reflex (priority 0).

---

### 6. pain.py --- Avoidance Learning

```python
@dataclass
class PainEvent:
    timestamp: float
    servo_id: str
    pain_type: str           # "overcurrent", "thermal", "collision", "jam", "voltage_sag"
    intensity: float         # 0.0-1.0
    joint_positions: dict    # Snapshot at time of pain
    cartesian_position: list[float] | None  # From proprioception FK
    context: dict            # Task, approach angle, object, etc.

class PainLevel(Enum):
    DISCOMFORT = 1           # Log, continue with caution
    MILD = 2                 # Slow down, record avoidance
    MODERATE = 3             # Stop current motion, replan
    SEVERE = 4               # Abort task, safe position
    EMERGENCY = 5            # Disable torque, broadcast EMERGENCY

@dataclass
class AvoidanceZone:
    center_joint_positions: dict
    radius_ticks: float      # Proportional to pain intensity
    created_at: float
    pain_count: int          # Strengthened by repeated pain
    decay_rate: float = 0.01 # Radius shrinks over time if no re-injury

class ReferredPain:
    """Detect compensatory stress in adjacent joints."""
    def check(self, telemetry, triggering_servo: str) -> list[str]: ...

class PainMemory:
    """Persistent avoidance zone map in joint space."""
    def __init__(self): ...
    def record_pain(self, event: PainEvent): ...
    def check_avoidance(self, target_positions: dict) -> AvoidanceZone | None: ...
    def decay(self): ...     # Called during sleep consolidation
    def save(self) / def load(self): ...
```

**Pain pipeline:**
1. Reflex engine detects harmful condition (fast path, <10ms)
2. Reflex fires protective action
3. PainEvent created with full context (slow path, ~100ms)
4. PainMemory records AvoidanceZone at the joint configuration
5. Future motion commands check against avoidance zones
6. AvoidanceZone radius decays during sleep (forgetting), but re-injury strengthens it

**Behavioral levels map to actions:**

| Level | Trigger Example | Action |
|-------|----------------|--------|
| DISCOMFORT | Servo at 50% load for 5s | Log, nudge preferences toward caution |
| MILD | Overcurrent 800mA, 50ms | Slow down, create small avoidance zone |
| MODERATE | Collision detected (load derivative) | Stop, replan approach, medium avoidance zone |
| SEVERE | Repeated jam at same position | Abort task, large avoidance zone, report to governor |
| EMERGENCY | Voltage collapse | Torque off, broadcast EMERGENCY |

---

### 7. proprioception.py --- Body Awareness

```python
@dataclass
class DHParams:
    """Denavit-Hartenberg parameters for one joint."""
    a: float       # Link length (mm)
    d: float       # Link offset (mm)
    alpha: float   # Link twist (radians)
    # theta computed from servo position

# SO-101 DH parameters (from research)
SO101_DH = [
    DHParams(a=0,   d=55,  alpha=-pi/2),   # shoulder_pan
    DHParams(a=104, d=0,   alpha=0),        # shoulder_lift
    DHParams(a=88,  d=0,   alpha=0),        # elbow_flex
    DHParams(a=0,   d=0,   alpha=-pi/2),    # wrist_flex
    DHParams(a=0,   d=0,   alpha=pi/2),     # wrist_roll
    DHParams(a=0,   d=60,  alpha=0),        # gripper
]

class ForwardKinematics:
    """DH parameter chain -> Cartesian coordinates."""
    def __init__(self, dh_params: list[DHParams]): ...
    def compute(self, joint_angles: list[float]) -> list[np.ndarray]:
        """Returns list of 4x4 transform matrices, one per joint."""
    def end_effector_position(self, joint_angles: list[float]) -> np.ndarray:
        """Returns (x, y, z) of end-effector in base frame."""

@dataclass
class Capsule:
    p0: np.ndarray       # Start point (3D)
    p1: np.ndarray       # End point (3D)
    radius: float        # mm

class BodyState:
    """Current physical state of the arm."""
    joint_positions: dict[str, int]       # Servo ticks
    joint_angles: list[float]             # Radians
    joint_velocities: list[float]         # Radians/s
    end_effector_xyz: np.ndarray          # mm in base frame
    capsules: list[Capsule]               # Current capsule positions
    joint_limit_proximity: dict[str, float]  # 0.0=at limit, 1.0=centered
    estimated_forces: dict[str, float]    # From current readings

class BodySchema:
    """Integrated body model with FK, capsules, and limit awareness."""
    def __init__(self, dh_params: list[DHParams], capsule_radii: dict): ...
    def update(self, joint_positions: dict, telemetry) -> BodyState: ...
    def check_self_collision(self, target_positions: dict) -> float: ...
    def safe_move(self, target: dict, current: dict) -> dict:
        """Returns clamped positions that avoid self-collision and joint limits."""
```

**Capsule model for SO-101:**

| Link | Length (mm) | Radius (mm) |
|------|------------|-------------|
| base | 55 (height) | 30 |
| upper_arm | 104 | 20 |
| forearm | 88 | 18 |
| wrist | 35 | 15 |
| gripper | 60 | 25 |

**Self-collision pairs to check** (skip adjacent links):
- base <-> forearm
- base <-> wrist
- base <-> gripper
- upper_arm <-> wrist
- upper_arm <-> gripper

5 pairs at <5 microseconds total. Runs every servo command cycle.

---

### 8. sleep_cycle.py --- Maintenance and Consolidation

```python
class SleepPhase(Enum):
    AWAKE = 0
    DROWSY = 1               # Reducing activity, finishing tasks
    LIGHT_SLEEP = 2          # Memory consolidation
    DEEP_SLEEP = 3           # Calibration, maintenance, immune pruning
    REM = 4                  # Dream replay of surprising episodes

class SleepEngine:
    """4-phase sleep cycle with pressure-based scheduling."""
    def __init__(self, memory: CitizenMemory, immune, genome, calibration): ...

    def compute_sleep_pressure(self) -> float:
        """0.0-1.0 based on uptime, fatigue, unconsolidated episodes,
        time since last sleep."""

    async def enter_sleep(self):
        """Transition through phases: DROWSY -> LIGHT -> DEEP -> REM -> AWAKE."""

    def should_sleep(self) -> bool:
        """True if sleep pressure > threshold and no active OBLIGATION goals."""

    def can_wake(self, event_severity: str) -> bool:
        """EMERGENCY always wakes. CRITICAL wakes from LIGHT only.
        WARNING and below wait until natural wake."""

class ConsolidationWorker:
    """LIGHT_SLEEP phase: consolidate episodic -> semantic + procedural."""
    def __init__(self, memory: CitizenMemory): ...
    async def consolidate(self):
        """
        1. Extract knowledge from recent episodes (repeated patterns -> semantic edges)
        2. Refine procedures (successful params -> averaged into procedures)
        3. Prune low-importance episodes older than retention period
        4. Decay confidence on stale knowledge edges
        """

class DreamReplay:
    """REM phase: replay surprising episodes for reinforcement."""
    def __init__(self, memory: CitizenMemory, improvement: PerformanceTracker): ...
    async def replay(self):
        """
        1. Select episodes with highest surprise (outcome != expected)
        2. Re-analyze with FailureAnalyzer
        3. Update procedural memory with corrective parameters
        4. Update avoidance zones (strengthen or decay)
        """
```

**Sleep pressure formula:**

```
pressure = 0.3 * min(1.0, uptime_hours / 4.0)
         + 0.3 * min(1.0, unconsolidated_episodes / 100)
         + 0.2 * fatigue
         + 0.2 * min(1.0, hours_since_last_sleep / 2.0)
```

**Deep sleep maintenance tasks:**
1. Run `calibration.quick_check()` on each servo
2. Prune immune memory LRU entries
3. Compact genome (remove stale metabolic counters)
4. Verify genome persistence (write + re-read)

**Wake thresholds:**

| Phase | EMERGENCY | CRITICAL | WARNING | INFO |
|-------|-----------|----------|---------|------|
| DROWSY | Wake | Wake | Wake | Ignore |
| LIGHT | Wake | Wake | Ignore | Ignore |
| DEEP | Wake | Ignore | Ignore | Ignore |
| REM | Wake | Ignore | Ignore | Ignore |

---

### 9. spatial.py --- Collision Avoidance and Zone Management

```python
@dataclass
class CapsuleGeometry:
    """Static capsule definition for a robot link."""
    link_name: str
    radius: float    # mm

def segment_distance(a0, a1, b0, b1) -> float:
    """Minimum distance between two 3D line segments. ~20 FLOPs."""

def capsule_distance(cap_a: Capsule, cap_b: Capsule) -> float:
    """Distance between capsules. Negative = penetrating."""

class CollisionChecker:
    """Capsule-based collision detection for self and inter-arm."""
    SELF_COLLISION_PAIRS = [
        ("base", "forearm"), ("base", "wrist"), ("base", "gripper"),
        ("upper_arm", "wrist"), ("upper_arm", "gripper"),
    ]

    def check_self(self, capsules: list[Capsule]) -> float:
        """Minimum distance among self-collision pairs. 5 checks, <5us."""

    def check_inter_arm(self, my_capsules, other_capsules) -> float:
        """Minimum distance between two arms. 25 checks, <10us."""

@dataclass
class Zone:
    name: str
    bounds_min: list[float]  # [x, y, z] mm
    bounds_max: list[float]
    zone_type: str           # "exclusive", "shared", "forbidden"
    max_occupants: int = 1
    current_occupants: list[str] = field(default_factory=list)

class ZoneManager:
    """Manages workspace zones distributed via constitution."""
    def __init__(self): ...
    def load_from_constitution(self, workspace_config: dict): ...
    def check_position(self, position: np.ndarray, citizen_id: str) -> str:
        """Returns: 'allowed', 'shared_request_needed', 'forbidden'."""
    def request_access(self, zone_name: str, citizen_id: str) -> bool: ...
    def release_access(self, zone_name: str, citizen_id: str): ...

@dataclass
class FlightPlan:
    id: str
    citizen_id: str
    start_cartesian: list[float]
    end_cartesian: list[float]
    envelope_min: list[float]    # Bounding box of swept volume
    envelope_max: list[float]
    duration_ms: float
    priority: int                # 10=emergency, 1=idle
    created_at: float

    def conflicts_with(self, other: "FlightPlan") -> bool:
        """AABB overlap test on envelopes."""

class FlightPlanManager:
    """Coordinate motion intents via PROPOSE/ACCEPT."""
    def __init__(self): ...
    def create_plan(self, start, end, duration, priority) -> FlightPlan: ...
    def check_conflicts(self, plan: FlightPlan) -> list[FlightPlan]: ...
    def register_active(self, plan: FlightPlan): ...
    def complete(self, plan_id: str): ...
```

**Separation thresholds:**
- Green (>50mm): Normal operation
- Yellow (20-50mm): Approaching arm slows down, mycelium warning
- Red (<20mm): Approaching arm stops, EMERGENCY broadcast
- Contact (<0mm): Both arms emergency stop

**Flight plan flow (using existing protocol):**
1. Arm sends PROPOSE with `task: "flight_plan"` and trajectory envelope
2. Other arms check for conflicts and respond with ACCEPT_REJECT
3. Priority arbitration: higher priority wins; equal priority: lower pubkey yields
4. On completion: REPORT with `type: "flight_plan_complete"`

**Zone definitions distributed via GOVERN** in the constitution's `workspace` field. No new message types.

---

### 10. growth.py --- Developmental Stages and Earned Autonomy

```python
class DevelopmentalStage(Enum):
    NEWBORN = 0      # Just booted, no experience
    INFANT = 1       # Basic motor control, teleop only
    JUVENILE = 2     # Supervised autonomy, simple tasks
    ADULT = 3        # Full autonomy for known tasks
    EXPERT = 4       # Can teach, optimize, lead multi-arm tasks
    ELDER = 5        # Mentor role, may have degraded hardware

class AutonomyLevel(Enum):
    TELEOP_ONLY = 0       # Human controls every motion
    SUPERVISED = 1        # Autonomous but human monitors and can override
    ASSISTED = 2          # Autonomous with safety constraints, reports frequently
    AUTONOMOUS = 3        # Full autonomous execution
    SELF_GOVERNING = 4    # Can modify own parameters within constitution bounds

class MaturationTracker:
    """Tracks developmental progression with multi-factor gates."""
    def __init__(self, genome, skills, memory): ...

    def current_stage(self) -> DevelopmentalStage:
        """Compute stage from XP, success rate, peer endorsements, uptime."""

    def autonomy_for_skill(self, skill_name: str) -> AutonomyLevel:
        """Per-skill autonomy based on success rate and task count."""

    def check_promotion(self) -> DevelopmentalStage | None:
        """Returns new stage if all gate conditions met, else None."""

    def check_regression(self) -> DevelopmentalStage | None:
        """EWMA monitoring. Returns lower stage if performance degraded."""

class SpecializationProfile:
    """Track performance per task type, detect natural specialization."""
    def __init__(self): ...
    def update(self, task_type: str, success: bool, quality: float): ...
    def specializations(self) -> list[str]:
        """Task types where this citizen performs significantly above fleet average."""
    def weaknesses(self) -> list[str]:
        """Task types where performance is below fleet average."""
```

**Stage gate conditions:**

| Stage | XP Required | Success Rate | Peer Endorsements | Other |
|-------|------------|-------------|-------------------|-------|
| NEWBORN -> INFANT | 10 | any | 0 | Completed calibration |
| INFANT -> JUVENILE | 100 | >60% | 0 | 5+ unique task types |
| JUVENILE -> ADULT | 500 | >80% | 1 | No severe pain in last 100 tasks |
| ADULT -> EXPERT | 2000 | >90% | 3 | Has taught another citizen |
| EXPERT -> ELDER | 5000 | any | 5 | >1000 hours uptime |

**Regression:** EWMA of success rate. If the 50-task EWMA drops below the stage's minimum, citizen is demoted one stage. This triggers a REPORT to the governor and a LifeEvent in the autobiography.

**Autonomy unlocking:** Per-skill, not global. A citizen can be AUTONOMOUS for `pick_and_place` but only SUPERVISED for `precision_assembly`. This tracks independently in the genome.

---

## Integration Points

### citizen.py Extensions

```python
# New attributes on Citizen base class
self.soul: Soul                          # Identity + personality + goals + values
self.memory: CitizenMemory               # Episodic + semantic + procedural
self.growth: MaturationTracker           # Developmental stage
self.improvement: PerformanceTracker     # Success tracking + strategy selection
```

New lifecycle hooks:
- `start()`: Load soul from genome. Load memory from disk. Register soul birth event if first boot.
- `stop()`: Save soul to genome. Save memory to disk.
- `_send_heartbeat()`: Include `metabolic_state`, `developmental_stage`, `sleep_phase`, `personality_summary` in body.
- `_handle_report()`: New cases for `knowledge_gossip`, `reflex_fired`, `flight_plan_complete`, `spatial_report`.
- `_handle_propose()`: New case for `flight_plan` proposals.
- `_handle_accept_reject()`: New case for flight plan clearance.

### surface_citizen.py Extensions

Governor gains:
- `soul`: Governor's own soul with administrative personality
- `memory`: Fleet-level semantic memory (merged from all citizen gossip)
- `spatial.ZoneManager`: Manages zone definitions, distributes via constitution
- `growth`: Fleet-wide maturation view, endorsement authority
- `PowerLedger`: Multi-citizen PSU-aware admission control
- `improvement`: Fleet-level performance statistics

Governor-specific behaviors:
- Distributes workspace zones via GOVERN constitution
- Resolves flight plan deadlocks (timeout -> lower pubkey yields)
- Endorses citizens for stage promotion based on observed performance
- Manages `PowerLedger` and rejects marketplace bids that would exceed PSU budget

### pi_citizen.py Extensions

Follower gains all 10 biological modules:
- `reflex.ReflexEngine`: Runs as dedicated asyncio task at 100Hz
- `proprioception.BodySchema`: Updated every servo command cycle
- `metabolism.MetabolicState`: Updated every telemetry cycle
- `pain.PainMemory`: Checked before every servo command
- `spatial.CollisionChecker`: Self-collision on every command, inter-arm on heartbeat
- `sleep_cycle.SleepEngine`: Runs when idle and sleep pressure exceeds threshold

Servo command pipeline becomes:

```
Target positions (from teleop or policy)
    |
    v
[1] Joint limit enforcement (existing)
    |
    v
[2] Pain avoidance zone check (pain.py) --- reject/deflect if in zone
    |
    v
[3] Self-collision check (proprioception.py) --- scale back if collision
    |
    v
[4] Zone/fence check (spatial.py) --- clamp to zone boundaries
    |
    v
[5] Power budget check (metabolism.py) --- reduce speed if at peak
    |
    v
Write to servo bus
    |
    v
[6] Reflex engine reads result (reflex.py) --- override if dangerous
```

### marketplace.py Extensions

Bid scoring adds three new dimensions:

```python
def compute_bid_score(self, ...):
    base = (capability * 0.20 + availability * 0.15 + health * 0.15 +
            power_headroom * 0.15 + personality_fit * 0.10 +
            developmental_autonomy * 0.15 + specialization * 0.10)
    return base * fatigue_modifier * metabolic_modifier
```

- `power_headroom`: From metabolism. Citizens that can't power the task don't bid.
- `personality_fit`: From soul. High-conscientiousness bids higher for precision tasks.
- `developmental_autonomy`: From growth. Citizens without sufficient autonomy for the skill don't bid.
- `specialization`: From growth. Citizens specialized in the task type bid higher.

### dashboard.py Extensions

New TUI sections:
- **SOUL**: Personality radar (OCEAN), current goal, autobiography snippet
- **MEMORY**: Episode count, knowledge node count, procedure count, last consolidation
- **REFLEXES**: Active reflex table, recent firings, reflex rate
- **METABOLISM**: Power draw graph, metabolic state, PSU utilization, duty cycle
- **PAIN**: Avoidance zone count, recent pain events, pain intensity history
- **BODY**: End-effector position, joint limit proximity bars, capsule visualization
- **SLEEP**: Current phase, sleep pressure bar, consolidation stats
- **SPATIAL**: Zone map, active flight plans, minimum separation distance
- **GROWTH**: Developmental stage, per-skill autonomy levels, specialization profile
- **IMPROVEMENT**: Success rate trends, active strategy, CMA-ES generation

---

## Data Flow Diagrams

### Reflex Firing

```
Servo telemetry (100Hz)
    |
    v
TelemetryWindow.push()
    |
    v
ReflexEngine.evaluate()
    |
    +-- No rule triggered --> sleep remaining budget, next cycle
    |
    +-- Rule triggered:
        |
        v
    ReflexEngine.fire(rule)
        |
        +---> Direct servo command (reduce_velocity / disable_torque / reverse)
        |     (bypasses governor, <10ms from trigger)
        |
        +---> PainEvent created (async, ~100ms)
        |     |
        |     v
        |     PainMemory.record_pain() --> AvoidanceZone created
        |     |
        |     v
        |     Episode recorded in EpisodicMemory
        |
        +---> REPORT multicast: {type: "reflex_fired", rule_id, servo, values}
        |     |
        |     v
        |     Neighbors in same zone: sympathetic reflex (25% speed reduction)
        |
        +---> If repeated 3+ times in 60s:
              ImmuneMemory.add_pattern()
```

### Sleep Cycle

```
SleepEngine.compute_sleep_pressure()
    |
    v
Pressure > 0.7 AND no OBLIGATION goals?
    |
    +-- No --> continue normal operation
    |
    +-- Yes:
        |
        v
    PHASE 1: DROWSY (30s)
        - Finish current task or safe-position
        - Broadcast REPORT: {type: "entering_sleep"}
        - Reject marketplace bids
        |
        v
    PHASE 2: LIGHT_SLEEP (60-120s)
        - ConsolidationWorker.consolidate()
          - Episodes -> semantic knowledge (repeated patterns)
          - Episodes -> procedural refinements (successful params)
          - Prune old low-importance episodes
          - Decay stale knowledge confidence
        - Can wake for CRITICAL or EMERGENCY
        |
        v
    PHASE 3: DEEP_SLEEP (30-60s)
        - Calibration quick-check on each servo
        - ImmuneMemory.prune() (LRU)
        - Genome compact and verify write
        - AvoidanceZone decay (pain forgetting)
        - Only EMERGENCY can wake
        |
        v
    PHASE 4: REM (30-60s)
        - DreamReplay: replay surprising episodes
        - Update procedural memory with corrective params
        - Strengthen/weaken avoidance zones
        - Only EMERGENCY can wake
        |
        v
    AWAKE
        - Broadcast REPORT: {type: "sleep_complete", consolidated_episodes: N}
        - Resume normal operation
        - Reset sleep pressure to 0
```

### Pain -> Avoidance Learning

```
Harmful condition detected (reflex or sequencing layer)
    |
    v
PainEvent created:
    {servo: "elbow_flex", type: "overcurrent", intensity: 0.7,
     joint_positions: {shoulder:2048, elbow:2800, ...},
     cartesian: [120, -30, 80]}
    |
    v
PainMemory.record_pain():
    |
    +-- Existing AvoidanceZone nearby?
    |   |
    |   +-- Yes: Strengthen (increase radius, increment pain_count)
    |   |
    |   +-- No: Create new AvoidanceZone
    |       center = joint_positions, radius = 100 * intensity
    |
    +-- Record Episode in EpisodicMemory
    |   tags: ["pain", servo_id, pain_type]
    |   importance: 0.5 + 0.5 * intensity
    |
    +-- Update soul.preferences (nudge toward caution for this task type)
    |
    +-- ReferredPain.check() -- adjacent joints compensating?
        |
        +-- If yes: create secondary AvoidanceZone at adjacent joint config

FUTURE MOTION:
    Target positions proposed
        |
        v
    PainMemory.check_avoidance(target)
        |
        +-- No zone hit --> proceed normally
        |
        +-- Zone hit:
            - If DISCOMFORT zone: proceed with reduced speed
            - If MILD/MODERATE zone: deflect trajectory around zone
            - If SEVERE zone: refuse motion, report to governor

DURING SLEEP:
    AvoidanceZone.decay()
        - Radius *= (1 - decay_rate) per sleep cycle
        - Zones with radius < 5 ticks are pruned
        - Zones with pain_count > 5 decay 3x slower (deeply learned)
```

### Spatial Conflict Resolution

```
Arm-A needs to move into shared zone
    |
    v
FlightPlanManager.create_plan(start, end, duration, priority=6)
    |
    v
PROPOSE broadcast: {task: "flight_plan", envelope: {min, max}, priority: 6}
    |
    v
Arm-B receives PROPOSE:
    |
    v
    FlightPlanManager.check_conflicts(incoming_plan)
        |
        +-- No conflict: ACCEPT_REJECT {accepted: true}
        |
        +-- Conflict detected:
            |
            +-- Arm-B priority > Arm-A priority:
            |   ACCEPT_REJECT {accepted: false, my_priority: 8, reason: "higher_priority"}
            |   Arm-A waits for Arm-B to complete
            |
            +-- Arm-B priority < Arm-A priority:
            |   ACCEPT_REJECT {accepted: true}
            |   Arm-B yields: slows down, adjusts own plan
            |
            +-- Equal priority:
                Deterministic tiebreak: lower pubkey yields
                ACCEPT_REJECT {accepted: true/false based on pubkey comparison}

After all responses received (or 200ms timeout):
    |
    +-- All accepted: Execute plan, broadcast REPORT on completion
    |
    +-- Rejected by higher priority: Wait, retry after higher-priority plan completes
    |
    +-- Timeout (no response): Assume accepted (optimistic for exclusive zones)
    |
    +-- Deadlock (mutual rejection): Governor resolves via GOVERN override
```

---

## Persistence Schema

v4.0 additions to `~/.citizenry/`:

```
~/.citizenry/
  <name>.key                      # Ed25519 private key (v1.5)
  <name>.neighbors.json           # Neighbor table (v1.5)
  <name>.constitution.json        # Constitution (v1.5)
  <name>.genome.json              # Citizen genome (v2.0, extended with soul data)
  <name>.immune.json              # Immune memory patterns (v2.0)
  <name>.contracts.json           # Active symbiosis contracts (v2.0)
  <name>.skills.json              # Skill tree + XP (v2.0)
  <name>.rollout.json             # Active rollout state (v3.0)
  <name>.policy_history.json      # NL policy change history (v3.0)
  <name>.will_archive.json        # Received wills (v3.0, governor only)
  <name>.episodes.json            # Episodic memory (v4.0)
  <name>.knowledge.json           # Semantic knowledge graph (v4.0)
  <name>.procedures.json          # Procedural memory (v4.0)
  <name>.pain_zones.json          # Avoidance zones in joint space (v4.0)
  <name>.sleep_state.json         # Last sleep time, pressure, stats (v4.0)
  <name>.growth_log.json          # Stage transitions, autonomy history (v4.0)
  <name>.improvement_state.json   # Strategy bandit state, CMA-ES state (v4.0)
```

**Genome extensions** (fields added to `CitizenGenome`):

```python
# soul data (persisted in genome for portability)
soul: dict = {
    "personality": {...},           # PersonalityProfile fields
    "preferences": {...},           # BehavioralPreferences fields
    "values": {...},                # ValueSystem fields
    "autobiography": [...],         # List of LifeEvent dicts
    "relationships": {...},         # {pubkey: trust_score}
    "birth_timestamp": float,
    "incarnation": int,
}

# metabolism counters (persisted in genome)
metabolism: dict = {
    "total_operating_hours": float,
    "total_high_load_hours": float,
    "total_overload_events": int,
    "total_voltage_sag_events": int,
    "total_thermal_cycles": int,
    "total_energy_consumed_wh": float,
    "task_power_profiles": {...},
    "per_servo_fatigue": {...},
}

# growth state (persisted in genome)
growth: dict = {
    "stage": str,
    "per_skill_autonomy": {...},
    "stage_transitions": [...],
    "specialization_scores": {...},
}
```

**Size budget:**
- Episodes: Max 10,000 entries. At ~500 bytes each = ~5MB. Pruned during sleep.
- Knowledge graph: Max 5,000 nodes + 10,000 edges. At ~200 bytes each = ~3MB.
- Procedures: Max 500. At ~300 bytes each = ~150KB.
- Pain zones: Max 200. At ~100 bytes each = ~20KB.
- Total v4.0 persistence overhead: <10MB per citizen.

---

## Performance Budget

| Operation | Target | Mechanism |
|-----------|--------|-----------|
| Reflex loop cycle | 10ms (100Hz) | Dedicated asyncio task, GC tuned |
| Telemetry read (6 servos) | <5ms | Serial at 1Mbaud, sync_read |
| Reflex rule evaluation | <0.1ms | Linear scan of ~8 rules, simple comparisons |
| Self-collision check | <5us | 5 capsule-capsule pairs, numpy |
| Inter-arm collision check | <10us | 25 capsule-capsule pairs, numpy |
| FK computation (6 joints) | <50us | 6 matrix multiplications, numpy |
| Pain avoidance check | <0.5ms | Linear scan of avoidance zones |
| Flight plan conflict check | <1ms | AABB overlap test per active plan |
| Memory retrieval (10 results) | <5ms | Tag-based search, sorted by score |
| Sleep consolidation (full cycle) | 2-5 min | Background, no servo commands during sleep |
| Episode recording | <0.5ms | Append to in-memory list + async persist |
| Personality mutation | <0.1ms | Single float update |
| CMA-ES ask/tell | <10ms | numpy only, population size 10 |
| Total memory per citizen (RSS) | <70MB | v3.0 baseline (~55MB) + ~15MB for v4.0 state |
| CPU overhead (Pi 5, 4 cores) | <25% of 1 core | Reflex loop is main consumer |

### CPU Budget Breakdown (Pi 5)

| Task | Frequency | CPU Time/Call | CPU % |
|------|-----------|--------------|-------|
| Reflex loop | 100Hz | ~6ms | ~60% of budget (dedicated) |
| Teleop servo writes | 60Hz | ~2ms | Shared with reflex loop bus |
| Telemetry processing | 10Hz | ~1ms | <1% |
| FK + collision | 60Hz | ~0.1ms | <1% |
| Pain check | 60Hz | ~0.5ms | ~3% |
| Heartbeat + protocol | 0.5Hz | ~5ms | <1% |
| Memory operations | ~1Hz | ~5ms | <1% |
| Sleep consolidation | ~0.001Hz | ~300s total | 0% normally, 100% during sleep |

The reflex loop and servo I/O share the serial bus. Bus arbitration uses a simple asyncio lock: reflex loop holds the lock during its read-evaluate-act cycle, teleop writes acquire it between reflex cycles.

---

## Testing Strategy

### Unit Tests (no hardware)

| Module | Test Cases | Mock Strategy |
|--------|-----------|---------------|
| `soul.py` | Personality drift, goal selection, value checking, identity continuity | No mocks needed (pure data) |
| `memory.py` | Episode CRUD, retrieval scoring, knowledge graph merge, consolidation, pruning | No mocks (in-memory) |
| `improvement.py` | UCB1 selection, CMA-ES convergence, performance trend detection | No mocks (pure math) |
| `reflex.py` | Each reflex rule with synthetic telemetry, compound conditions, cooldown, priority arbitration | Mock servo bus |
| `metabolism.py` | Brownout stages, metabolic classification, power ledger allocation, duty cycle | Mock telemetry |
| `pain.py` | Pain event -> avoidance zone, zone decay, zone strengthening, deflection | No mocks (pure data) |
| `proprioception.py` | FK against known positions, capsule distances, self-collision detection | No mocks (pure math, numpy) |
| `sleep_cycle.py` | Sleep pressure computation, phase transitions, wake thresholds, consolidation invocation | Mock memory + immune |
| `spatial.py` | Zone boundary checks, flight plan conflicts, AABB overlap, capsule-capsule distance | No mocks (pure math) |
| `growth.py` | Stage gate conditions, promotion, regression detection, specialization scoring | Mock skills + memory |

### Integration Tests (pytest-asyncio, no hardware)

| Scenario | What It Tests |
|----------|--------------|
| Reflex -> Pain -> Avoidance | Synthetic overcurrent fires reflex, creates pain event, avoidance zone blocks future motion |
| Sleep cycle end-to-end | Citizen accumulates episodes, sleep pressure rises, enters sleep, consolidation runs, episodes pruned |
| Spatial flight plan conflict | Two mock citizens propose conflicting flight plans, priority arbitration resolves |
| Growth promotion | Citizen accumulates XP and success rate, gate conditions met, stage promoted, REPORT sent |
| Metabolism -> Marketplace | Citizen at peak metabolic state refuses bid, governor re-routes task |
| Soul personality drift | Citizen completes 100 tasks, personality traits drift measurably toward successful patterns |
| Memory consolidation | 50 episodes with repeated patterns -> semantic edges created, procedures refined |
| Distributed reflex sympathy | Citizen-A fires EMERGENCY reflex, Citizen-B receives report, triggers sympathetic slowdown |

### Protocol Compatibility Tests

| Test | Assertion |
|------|-----------|
| v4.0 heartbeat body parses as valid v3.0 | Extra fields are ignored by v3.0 citizens |
| v4.0 REPORT types ignored by v3.0 | Unknown `type` values in REPORT body are silently ignored |
| v4.0 PROPOSE (flight_plan) ignored by v3.0 | v3.0 citizen rejects unknown task types |
| v4.0 GOVERN (workspace) ignored by v3.0 | Unknown GOVERN body types are ignored |
| v3.0 citizen operates normally alongside v4.0 | Mixed fleet, v3.0 citizen has no v4.0 features but participates in protocol |

### Hardware Validation (manual)

| Test | Hardware | Pass Criteria |
|------|----------|--------------|
| Reflex response time | Pi 5 + SO-101 | Overcurrent trigger -> velocity reduction in <10ms |
| Self-collision prevention | Pi 5 + SO-101 | Teleop cannot drive arm into self-collision |
| Brownout protection | Pi 5 + SO-101 + load | Voltage sag -> staged degradation -> recovery |
| Sleep cycle on real hardware | Pi 5 + SO-101 | Enter sleep, consolidate, calibration check, wake on command |
| Multi-arm flight plan | 2x Pi + 2x SO-101 | Arms avoid collision in shared zone via flight plan protocol |
| Pain avoidance | Pi 5 + SO-101 | Repeated jam at position -> citizen avoids that position |
| Growth progression | Pi 5 + SO-101 | Citizen progresses from NEWBORN to JUVENILE through normal operation |

---

## Migration from v3.0

v4.0 is fully backward compatible with v3.0:

1. **No protocol changes**: Same 7 message types, same envelope format. New data rides in body fields.
2. **New body fields**: v3.0 citizens ignore unknown fields in heartbeat, REPORT, PROPOSE, and GOVERN bodies (existing behavior: JSON `dict.get()` with defaults).
3. **New persistence files**: v4.0 creates new `.json` files alongside existing v3.0 files. No schema changes to existing files.
4. **Genome extensions**: New top-level keys (`soul`, `metabolism`, `growth`) are added to the genome dict. v3.0 citizens ignore unknown keys.
5. **Mixed fleet**: A v4.0 governor can manage v3.0 citizens. Biological features (reflexes, sleep, pain, spatial) only activate on v4.0 citizens. v3.0 citizens continue to operate normally.
6. **Upgrade path**: Update citizenry code on each device. New modules initialize with defaults on first boot. No migration scripts needed.

---

## Dependencies

| Package | Purpose | New? |
|---------|---------|------|
| `numpy` | FK, capsule math, CMA-ES, sliding windows | No (already used) |
| `cma` | CMA-ES for parameter evolution (optional) | Yes (optional, pure-Python fallback provided) |
| All existing citizenry deps | Protocol, crypto, transport, etc. | No |

If `cma` is not installed, `ParameterEvolution` falls back to a simple random-perturbation hill climber. All other modules use only numpy and the standard library.
