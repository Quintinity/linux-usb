# Robot Growth and Maturation — Research & Design Document

Deep research into capability development over time, developmental stages, and earned autonomy for the armOS Citizenry protocol.

---

## 1. Developmental Robotics — Staged Growth

### What the research says

**Developmental robotics** models robot learning after human cognitive development, specifically Piaget's four stages:

1. **Sensorimotor** (0-2 years) — awareness limited to what is immediately present. The robot can only react to current sensor input. No planning, no memory of absent objects.
2. **Preoperational** (2-7 years) — symbolic thinking but egocentric. The robot can represent objects internally (position memory, task models) but cannot take another agent's perspective.
3. **Concrete operational** (7-11 years) — logical reasoning about concrete situations. The robot can reason about cause-and-effect, compare its approach to peers, and understand reversibility ("if I moved it here, I can move it back").
4. **Formal operational** (11+ years) — abstract reasoning. The robot can plan for hypothetical situations, generalize from specific experiences, and teach other agents.

**The iCub project** (Italian Institute of Technology) is the landmark implementation. The iCub humanoid demonstrates that staged behavior emerges naturally when you constrain early capabilities and gradually unlock them. The key architectural insight from the iCub: **constraints drive development**. Limiting what the robot can do in early stages forces it to master fundamentals before attempting complex behaviors.

The **Epigenetic Robotics Architecture** on iCub shows that multi-stage development works on real hardware: the robot first discovers body control, then object affordances, then proto-linguistic interaction — each stage bootstrapping from the previous one.

**Intrinsic motivation** research (INRIA Flowers lab) demonstrates that **learning progress** as an intrinsic reward signal can spontaneously create developmental stages. When a robot is driven to seek situations where it learns fastest, it naturally progresses from:
- Exploring its own body (easiest to learn)
- Manipulating simple objects (next most learnable)
- Complex multi-object interactions (learnable only after basics)
- Social/communicative behavior (highest complexity)

This is not programmed — it **emerges** from the learning progress signal. The robot abandons domains where it has stopped improving and seeks domains where improvement is still rapid.

### Design for armOS: DevelopmentalStage

```python
class DevelopmentalStage(Enum):
    """Piaget-inspired developmental stages for armOS citizens."""

    NEWBORN = 0       # Sensorimotor: can only react to direct commands
    INFANT = 1        # Late sensorimotor: basic body awareness, calibration
    CHILD = 2         # Preoperational: can represent tasks, follow teleop
    JUVENILE = 3      # Concrete operational: can execute tasks, reason about outcomes
    ADULT = 4         # Formal operational: can bid on marketplace, plan sequences
    ELDER = 5         # Mastery: can coordinate others, train new citizens


@dataclass
class MaturationState:
    """Tracks a citizen's developmental progress."""

    stage: DevelopmentalStage = DevelopmentalStage.NEWBORN
    stage_entered_at: float = 0.0
    total_uptime_hours: float = 0.0
    total_tasks_attempted: int = 0
    total_tasks_succeeded: int = 0
    calibration_complete: bool = False
    self_test_passed: bool = False
    teleop_sessions_completed: int = 0
    autonomous_tasks_completed: int = 0
    citizens_trained: int = 0
    regression_flags: list[str] = field(default_factory=list)

    def success_rate(self, window: int = 100) -> float:
        """Rolling success rate."""
        if self.total_tasks_attempted == 0:
            return 0.0
        return self.total_tasks_succeeded / self.total_tasks_attempted

    def ready_for_promotion(self) -> tuple[bool, str]:
        """Check if citizen meets criteria for next stage."""
        checks = PROMOTION_CRITERIA.get(self.stage)
        if checks is None:
            return False, "already at max stage"
        for criterion, (check_fn, description) in checks.items():
            if not check_fn(self):
                return False, f"not met: {description}"
        return True, "all criteria met"
```

**The key constraint:** A NEWBORN citizen literally cannot do certain things. The stage gates capabilities at the protocol level, not just the UI level. A NEWBORN cannot bid on marketplace tasks — the marketplace rejects bids from citizens below JUVENILE. A CHILD cannot coordinate other citizens — the coordinator ignores proposals from non-ADULT citizens.

---

## 2. Earned Autonomy — From Supervised to Independent

### What the research says

**NIST ALFUS (Autonomy Levels for Unmanned Systems)** defines autonomy along three axes:
1. **Mission complexity** — how complex a task can the system handle?
2. **Environmental difficulty** — how challenging are the conditions?
3. **Human interaction** — how much human oversight is required?

The critical insight: autonomy is not a single number. A robot might be highly autonomous for simple tasks in controlled environments but require full supervision for complex tasks in novel environments.

**Competence-Aware Autonomy** (UMass) — robots that know their own limitations. The robot learns to reason about: (1) what it can do autonomously, (2) what environmental factors affect its competence, and (3) what kind of help to request when it exceeds its competence. This is directly applicable to armOS: a citizen should know when to ask the governor for approval and when to proceed independently.

**Machine Self-Confidence** (ACM THRI, 2025) — factorized into multiple competency indicators: solver quality, model accuracy, outcome assessment, execution confidence. Not a single "confidence" number but a structured assessment of "how confident am I in each part of my reasoning?"

**Adjustable Autonomy via Reinforcement Learning** (NSF) — the autonomy level is automatically adjusted based on performance. When the robot reaches higher performance levels, it operates more autonomously. When performance degrades, autonomy is reduced and human oversight increases.

### Design for armOS: AutonomyLevel

```python
class AutonomyLevel(Enum):
    """Progressive autonomy levels — earned, not configured."""

    TELEOP_ONLY = 0       # Every movement comes from human input
    SUPERVISED = 1        # Can execute commands, governor monitors
    GUIDED = 2            # Can make choices, governor approves plans
    AUTONOMOUS = 3        # Can bid and execute tasks independently
    DELEGATING = 4        # Can assign tasks to other citizens
    SELF_GOVERNING = 5    # Can operate without governor (emergency only)


@dataclass
class AutonomyProfile:
    """Per-task-type autonomy levels.

    A citizen might be AUTONOMOUS for basic_grasp but only
    SUPERVISED for delicate_grasp. Autonomy is earned per skill.
    """

    default_level: AutonomyLevel = AutonomyLevel.TELEOP_ONLY
    per_skill_levels: dict[str, AutonomyLevel] = field(default_factory=dict)
    governor_overrides: dict[str, AutonomyLevel] = field(default_factory=dict)

    # Evidence tracking
    consecutive_successes: dict[str, int] = field(default_factory=dict)
    consecutive_failures: dict[str, int] = field(default_factory=dict)
    last_demotion: dict[str, float] = field(default_factory=dict)

    def effective_level(self, skill: str) -> AutonomyLevel:
        """Get the effective autonomy level for a skill.

        Governor overrides take precedence, then per-skill, then default.
        """
        if skill in self.governor_overrides:
            return self.governor_overrides[skill]
        return self.per_skill_levels.get(skill, self.default_level)

    def record_outcome(self, skill: str, success: bool):
        """Record a task outcome and potentially adjust autonomy."""
        if success:
            self.consecutive_successes[skill] = \
                self.consecutive_successes.get(skill, 0) + 1
            self.consecutive_failures[skill] = 0
        else:
            self.consecutive_failures[skill] = \
                self.consecutive_failures.get(skill, 0) + 1
            self.consecutive_successes[skill] = 0

    def check_promotion(self, skill: str) -> bool:
        """Should this skill be promoted to a higher autonomy level?

        Requires N consecutive successes at current level.
        N scales with level — higher levels need more evidence.
        """
        current = self.effective_level(skill)
        required = PROMOTION_THRESHOLDS.get(current.value, float('inf'))
        return self.consecutive_successes.get(skill, 0) >= required

    def check_demotion(self, skill: str) -> bool:
        """Should this skill be demoted? 3 consecutive failures triggers."""
        return self.consecutive_failures.get(skill, 0) >= 3


# Consecutive successes needed for promotion at each level
PROMOTION_THRESHOLDS = {
    0: 5,      # TELEOP_ONLY → SUPERVISED: 5 successful teleop sessions
    1: 10,     # SUPERVISED → GUIDED: 10 successful supervised tasks
    2: 25,     # GUIDED → AUTONOMOUS: 25 successful guided tasks
    3: 50,     # AUTONOMOUS → DELEGATING: 50 successful autonomous tasks
    4: 100,    # DELEGATING → SELF_GOVERNING: 100 successful delegations
}
```

**How earned autonomy works in practice:**

1. **Newborn arm** — TELEOP_ONLY. Human moves every joint. The arm learns body awareness.
2. After 5 successful teleop sessions for `basic_movement`, promoted to SUPERVISED. The arm can execute `basic_movement` commands, but the governor monitors and can override.
3. After 10 successful supervised `basic_grasp` tasks, promoted to GUIDED. The arm proposes its own grasp plan, but the governor approves before execution.
4. After 25 successful guided grasps, promoted to AUTONOMOUS. The arm bids on grasp tasks in the marketplace and executes them without asking.
5. After 50 successful autonomous tasks, promoted to DELEGATING. The arm can coordinate with camera citizens to plan pick-and-place sequences.
6. SELF_GOVERNING is an emergency mode — only activated if the governor goes offline and the citizen has proven extreme competence.

**Demotion is fast, promotion is slow.** Three consecutive failures at any level triggers immediate demotion to the previous level. This asymmetry is intentional: trust is hard to build and easy to lose, just like in human relationships.

---

## 3. Capability Unlocking — Beyond XP Counters

### What the research says

Pure XP thresholds are a necessary but insufficient unlocking mechanism. The research points to three additional mechanisms:

**Demonstrated competence** — success rate over a rolling window of N trials. This is the standard in FDA-cleared surgical robots (Nature Digital Medicine): a system must demonstrate a statistically significant success rate before being approved for autonomous operation at a given complexity level.

**Peer endorsement** — in multi-agent RL systems (ROMA architecture), agents that observe another agent's competence can vouch for it. This reduces the sample size needed for trust-building, because a camera citizen that watches an arm succeed 10 times carries more weight than the arm's own self-report.

**Environmental context** — competence-aware systems (UMass) recognize that competence is not absolute. An arm might be fully capable in a well-lit, clean workspace but incompetent in a cluttered, dimly-lit one. Capability unlocking should be contextualized.

### Design for armOS: CapabilityGates

```python
@dataclass
class CapabilityGate:
    """Multi-factor gate for unlocking a capability.

    All conditions must be met. Any single condition failing
    blocks the unlock — even if XP is sufficient.
    """

    skill_name: str
    xp_required: int = 0
    success_rate_required: float = 0.0     # Over last N trials
    success_window: int = 20               # N for rolling window
    min_trials: int = 0                    # Must have attempted at least this many
    peer_endorsements_required: int = 0    # Other citizens who've observed success
    governor_certification: bool = False   # Governor must explicitly approve
    prerequisite_autonomy: AutonomyLevel = AutonomyLevel.TELEOP_ONLY
    environmental_conditions: dict = field(default_factory=dict)
    # e.g., {"lighting": "adequate", "workspace": "clear"}


# Default gates for manipulator skills
MANIPULATOR_GATES = {
    "basic_movement": CapabilityGate(
        skill_name="basic_movement",
        xp_required=0,
        # Available immediately — every citizen can try basic movement
    ),
    "precise_movement": CapabilityGate(
        skill_name="precise_movement",
        xp_required=100,
        success_rate_required=0.8,
        success_window=20,
        min_trials=20,
        # Must succeed 80% of the time over 20 attempts
    ),
    "basic_grasp": CapabilityGate(
        skill_name="basic_grasp",
        xp_required=0,
        success_rate_required=0.5,
        success_window=10,
        min_trials=10,
        # Low bar — just prove you can grasp sometimes
    ),
    "precise_grasp": CapabilityGate(
        skill_name="precise_grasp",
        xp_required=200,
        success_rate_required=0.85,
        success_window=30,
        min_trials=30,
        peer_endorsements_required=1,
        # Camera citizen must have observed successful grasps
    ),
    "delicate_grasp": CapabilityGate(
        skill_name="delicate_grasp",
        xp_required=1000,
        success_rate_required=0.95,
        success_window=50,
        min_trials=50,
        peer_endorsements_required=2,
        governor_certification=True,
        prerequisite_autonomy=AutonomyLevel.AUTONOMOUS,
        # High bar: 95% success, multiple witnesses, governor sign-off
    ),
    "pick_and_place": CapabilityGate(
        skill_name="pick_and_place",
        xp_required=50,
        success_rate_required=0.7,
        success_window=20,
        min_trials=15,
    ),
    "coordinate_task": CapabilityGate(
        skill_name="coordinate_task",
        xp_required=500,
        success_rate_required=0.9,
        success_window=50,
        min_trials=50,
        governor_certification=True,
        prerequisite_autonomy=AutonomyLevel.AUTONOMOUS,
        # Can only coordinate if proven highly competent
    ),
    "train_citizen": CapabilityGate(
        skill_name="train_citizen",
        xp_required=2000,
        success_rate_required=0.9,
        success_window=100,
        min_trials=100,
        peer_endorsements_required=3,
        governor_certification=True,
        prerequisite_autonomy=AutonomyLevel.DELEGATING,
        # Highest bar in the system
    ),
}
```

**Peer endorsement protocol:**

```python
@dataclass
class Endorsement:
    """A citizen's endorsement of another citizen's competence."""

    endorser_pubkey: str       # Who is endorsing
    subject_pubkey: str        # Who is being endorsed
    skill: str                 # What skill is being endorsed
    observations: int          # How many successful executions observed
    success_rate: float        # Observed success rate
    timestamp: float = 0.0
    signature: str = ""        # Ed25519 signature for authenticity

    def is_strong(self) -> bool:
        """A strong endorsement: 10+ observations, 85%+ success."""
        return self.observations >= 10 and self.success_rate >= 0.85
```

A camera citizen watching an arm work naturally generates endorsement data. After observing 10 successful grasps out of 12 attempts, it can broadcast an endorsement. This endorsement is signed with the camera's Ed25519 key, so it cannot be forged. The governor (or the skill gate system) collects endorsements and uses them as evidence for capability unlocking.

---

## 4. Specialization — Emergent Expertise

### What the research says

**Emergent specialization** in multi-agent systems is well-studied. Key findings:

- **ROMA (Role-Oriented Multi-Agent)** learning (ICML 2020) shows that agents in multi-agent RL naturally develop specialized roles when the reward structure permits it. Roles are "comprehensive patterns of behavior specialized in some tasks."
- **Predicting Multi-Agent Specialization via Task Parallelizability** (arXiv, 2025) demonstrates that specialization emerges when tasks are parallelizable — each agent becomes expert at a subset of tasks rather than being mediocre at all of them.
- **Emergent Specialization in Swarm Systems** (Springer) shows stigmergic self-organization: robots develop asymmetric workload distributions that reduce congestion, analogous to division of labor in insect colonies.

The critical insight: **specialization should emerge, not be assigned.** Forced specialization creates fragility (single point of failure). Emergent specialization through experience creates robustness — every citizen can do basic tasks, but some become particularly good at specific ones.

### Design for armOS: SpecializationProfile

```python
@dataclass
class SpecializationProfile:
    """Tracks emergent specialization from experience.

    No citizen is ASSIGNED a specialization. Specialization emerges
    from accumulated success patterns and is quantified here.
    """

    # Task-type performance history (EMA of success quality)
    task_performance: dict[str, float] = field(default_factory=dict)
    # e.g., {"basic_grasp": 0.92, "precise_grasp": 0.88, "pick_and_place": 0.95}

    # Task-type attempt counts
    task_counts: dict[str, int] = field(default_factory=dict)

    # Computed specialization scores (updated periodically)
    specialization_scores: dict[str, float] = field(default_factory=dict)

    # Anti-specialization: minimum breadth requirement
    breadth_threshold: float = 0.3  # Must maintain at least this performance
                                     # across all attempted task types

    def update(self, task_type: str, quality: float):
        """Update performance tracking after a task completion."""
        alpha = 0.1  # EMA smoothing factor
        old = self.task_performance.get(task_type, 0.5)
        self.task_performance[task_type] = old * (1 - alpha) + quality * alpha
        self.task_counts[task_type] = self.task_counts.get(task_type, 0) + 1
        self._recompute_specialization()

    def _recompute_specialization(self):
        """Compute specialization as deviation from mean performance.

        A citizen specialized in grasping will have high grasp performance
        relative to their average performance.
        """
        if not self.task_performance:
            return
        mean_perf = sum(self.task_performance.values()) / len(self.task_performance)
        if mean_perf == 0:
            return
        for task, perf in self.task_performance.items():
            # Specialization = how far above average, weighted by volume
            count = self.task_counts.get(task, 0)
            volume_weight = min(1.0, count / 50)  # Full weight at 50+ tasks
            self.specialization_scores[task] = (perf / mean_perf - 1.0) * volume_weight

    @property
    def primary_specialty(self) -> str | None:
        """The citizen's strongest specialization, if any."""
        if not self.specialization_scores:
            return None
        best = max(self.specialization_scores, key=self.specialization_scores.get)
        if self.specialization_scores[best] > 0.1:  # 10% above average
            return best
        return None  # No clear specialization yet

    def breadth_check(self) -> list[str]:
        """Return skills that have dropped below breadth threshold.

        These skills need maintenance practice to prevent over-specialization.
        """
        degraded = []
        for task, perf in self.task_performance.items():
            if perf < self.breadth_threshold and self.task_counts.get(task, 0) > 10:
                degraded.append(task)
        return degraded
```

**Anti-specialization mechanism:** The `breadth_check()` prevents dangerous over-specialization. If a citizen's performance on non-primary tasks drops below 30%, the goal hierarchy (from SOUL.md) generates intrinsic practice goals for those degraded skills. A "precision grasp expert" must still be able to do basic movement — otherwise, a single hardware issue could make it useless.

**Marketplace integration:** Specialization scores feed into bid scoring. When the marketplace evaluates bids, a citizen with a high specialization score for the relevant task type gets a bonus. This creates a positive feedback loop: specialists win more tasks of their type, get more practice, and become even more specialized. The `breadth_threshold` prevents this loop from running away.

---

## 5. Maturation Milestones — Concrete Stages

### The milestone ladder

Each milestone maps to a DevelopmentalStage and represents a concrete, testable achievement:

```
NEWBORN (Stage 0)
├── M0.1: Identity created (Ed25519 key generated)
├── M0.2: First heartbeat sent
├── M0.3: First neighbor discovered
└── M0.4: Constitution received and accepted

INFANT (Stage 1)
├── M1.1: Calibration completed (all 6 servos homed)
├── M1.2: Self-test passed (all joints move freely)
├── M1.3: Basic movement verified (reach 3 target positions)
├── M1.4: Telemetry reporting online (voltage, temp, current)
└── M1.5: Safety limits written to EEPROM

CHILD (Stage 2)
├── M2.1: First teleop session completed (5 minutes continuous)
├── M2.2: Teleop success rate > 80% (smooth tracking, no stalls)
├── M2.3: 10 teleop sessions completed
├── M2.4: First autonomous movement (move to commanded position)
└── M2.5: Gripper control demonstrated (open/close on command)

JUVENILE (Stage 3)
├── M3.1: First task executed (any task type)
├── M3.2: basic_grasp success rate > 70% over 20 trials
├── M3.3: pick_and_place success rate > 60% over 15 trials
├── M3.4: 50 total tasks completed
├── M3.5: First peer endorsement received
└── M3.6: Can recover from common errors without human intervention

ADULT (Stage 4)
├── M4.1: Marketplace bidding enabled (first bid submitted)
├── M4.2: 100 marketplace tasks completed
├── M4.3: Success rate > 85% across all attempted task types
├── M4.4: Governor certification received
├── M4.5: First multi-citizen coordination participated in
├── M4.6: Specialization score > 0.1 in at least one task type
└── M4.7: Can detect and report own degradation

ELDER (Stage 5)
├── M5.1: 500+ tasks completed with > 90% success rate
├── M5.2: Successfully coordinated 10+ multi-citizen tasks
├── M5.3: Received 3+ peer endorsements from different citizens
├── M5.4: First citizen trained (genome shared + mentored to JUVENILE)
├── M5.5: Contributed to fleet immune memory (patterns shared)
└── M5.6: Survived a hardware change with continuity maintained
```

### Implementation

```python
PROMOTION_CRITERIA = {
    DevelopmentalStage.NEWBORN: {
        "calibration": (
            lambda s: s.calibration_complete,
            "calibration must be complete"
        ),
        "self_test": (
            lambda s: s.self_test_passed,
            "self-test must pass"
        ),
    },
    DevelopmentalStage.INFANT: {
        "teleop_sessions": (
            lambda s: s.teleop_sessions_completed >= 5,
            "need 5+ teleop sessions"
        ),
        "basic_movement": (
            lambda s: s.success_rate() >= 0.8 and s.total_tasks_attempted >= 10,
            "need 80%+ success rate over 10+ tasks"
        ),
    },
    DevelopmentalStage.CHILD: {
        "task_count": (
            lambda s: s.total_tasks_succeeded >= 50,
            "need 50+ successful tasks"
        ),
        "success_rate": (
            lambda s: s.success_rate() >= 0.7,
            "need 70%+ overall success rate"
        ),
    },
    DevelopmentalStage.JUVENILE: {
        "marketplace_tasks": (
            lambda s: s.autonomous_tasks_completed >= 100,
            "need 100+ autonomous tasks"
        ),
        "high_success": (
            lambda s: s.success_rate() >= 0.85,
            "need 85%+ success rate"
        ),
    },
    DevelopmentalStage.ADULT: {
        "volume": (
            lambda s: s.autonomous_tasks_completed >= 500,
            "need 500+ autonomous tasks"
        ),
        "elite_rate": (
            lambda s: s.success_rate() >= 0.9,
            "need 90%+ success rate"
        ),
        "trained_others": (
            lambda s: s.citizens_trained >= 1,
            "must have trained at least 1 citizen"
        ),
    },
}
```

---

## 6. Growth Rate and Plateaus

### What the research says

Learning curves in robotics follow a **sigmoid (S-curve)** pattern:

1. **Slow start** — the robot is learning fundamentals. Success rate climbs slowly from 0% to ~30%.
2. **Rapid improvement** — once basics click, performance jumps quickly from 30% to 75%.
3. **Plateau** — performance levels off. Further improvement requires qualitative change, not just more practice.
4. **Breakthrough** — a new capability (camera guidance, better algorithm, environmental change) breaks through the plateau.

Google's research on robotic grasping showed this concretely: after ~800,000 grasp attempts, success rate plateaued. The breakthrough came from adding visual prediction — a qualitatively different input, not just more of the same practice.

In one study, PPO (Proximal Policy Optimization) for grasping moving objects plateaued at ~50% success rate. Adding curriculum learning (starting with slow objects, gradually increasing speed) broke through to ~80%.

### Design for armOS: GrowthTracker

```python
@dataclass
class GrowthTracker:
    """Tracks learning curves and detects plateaus/breakthroughs."""

    # Rolling performance windows at different scales
    recent_window: deque  # Last 20 tasks (short-term trend)
    medium_window: deque  # Last 100 tasks (medium-term trend)
    long_window: deque    # Last 500 tasks (long-term baseline)

    # Plateau detection
    plateau_threshold: float = 0.02   # Less than 2% improvement = plateau
    plateau_duration: int = 50        # Must be flat for 50+ tasks

    # Growth rate tracking
    growth_snapshots: list[GrowthSnapshot] = field(default_factory=list)

    def record(self, task_type: str, quality: float, timestamp: float):
        """Record a task outcome."""
        entry = (task_type, quality, timestamp)
        self.recent_window.append(entry)
        self.medium_window.append(entry)
        self.long_window.append(entry)

        # Snapshot every 50 tasks
        if len(self.long_window) % 50 == 0:
            self.growth_snapshots.append(GrowthSnapshot(
                timestamp=timestamp,
                success_rate=self._rate(self.medium_window),
                task_count=len(self.long_window),
            ))

    def detect_plateau(self, task_type: str | None = None) -> bool:
        """Is the citizen on a learning plateau?

        True if improvement rate over the last `plateau_duration` tasks
        is less than `plateau_threshold`.
        """
        if len(self.medium_window) < self.plateau_duration:
            return False

        recent_rate = self._rate(self.recent_window, task_type)
        older_entries = list(self.medium_window)[:len(self.medium_window)//2]
        older_rate = self._rate(older_entries, task_type)

        improvement = recent_rate - older_rate
        return abs(improvement) < self.plateau_threshold

    def detect_breakthrough(self, task_type: str | None = None) -> bool:
        """Has the citizen just broken through a plateau?

        True if recent performance is 10%+ above the medium-term average.
        """
        if len(self.recent_window) < 10 or len(self.medium_window) < 50:
            return False

        recent_rate = self._rate(self.recent_window, task_type)
        medium_rate = self._rate(self.medium_window, task_type)

        return recent_rate - medium_rate > 0.10

    def growth_rate(self) -> float:
        """Current learning rate: improvement per 50 tasks.

        Positive = improving, zero = plateau, negative = regressing.
        """
        if len(self.growth_snapshots) < 2:
            return 0.0
        recent = self.growth_snapshots[-1].success_rate
        previous = self.growth_snapshots[-2].success_rate
        return recent - previous

    def suggest_intervention(self) -> str | None:
        """Suggest what might break a plateau.

        Based on research: plateaus are broken by qualitative changes,
        not more practice of the same kind.
        """
        if not self.detect_plateau():
            return None

        rate = self._rate(self.medium_window)
        if rate < 0.5:
            return "plateau_low: consider adding sensor input (camera guidance)"
        elif rate < 0.8:
            return "plateau_mid: consider curriculum learning (easier tasks first)"
        else:
            return "plateau_high: consider new task variants for generalization"

    @staticmethod
    def _rate(window, task_type=None) -> float:
        entries = list(window)
        if task_type:
            entries = [e for e in entries if e[0] == task_type]
        if not entries:
            return 0.0
        return sum(e[1] for e in entries) / len(entries)


@dataclass
class GrowthSnapshot:
    """A point-in-time snapshot of growth metrics."""
    timestamp: float
    success_rate: float
    task_count: int
```

**Example growth trajectory for an SO-101 arm:**

```
Tasks    Success Rate    Stage          Event
─────    ────────────    ─────          ─────
0        0%              NEWBORN        Born. Calibrating.
10       30%             INFANT         Basic movement learned.
25       55%             INFANT         Rapid improvement phase.
50       72%             CHILD          First teleop mastered.
100      78%             CHILD          ← PLATEAU (no new input)
150      80%             JUVENILE       ← STILL PLATEAU
200      81%             JUVENILE       Camera citizen joins network.
210      88%             JUVENILE       ← BREAKTHROUGH (visual feedback)
300      91%             ADULT          Marketplace bidding begins.
500      93%             ADULT          ← PLATEAU (high-performance)
600      93%             ADULT          New task type: color sorting.
650      95%             ADULT          ← BREAKTHROUGH (generalization)
1000     94%             ELDER          Training first new citizen.
```

---

## 7. Regression Detection — Getting Worse

### What the research says

Predictive maintenance for robotic arms uses vibration signals, current draw, temperature trends, and position accuracy as degradation indicators. The key insight from automotive predictive maintenance: **degradation is usually gradual, but failure is sudden.** By the time a human notices a problem, the robot has been declining for hundreds of cycles.

Machine learning models for Remaining Useful Life (RUL) prediction use:
- **Linear Regression / Random Forest** on time-series sensor data
- **Anomaly detection** for unusual temperature or current patterns
- **Statistical Process Control** — CUSUM and EWMA charts for drift detection

For armOS, the problem is both hardware degradation (servo wear, calibration drift) and software/behavioral regression (a model that starts performing worse, environmental changes that invalidate learned behaviors).

### Design for armOS: RegressionDetector

```python
@dataclass
class RegressionDetector:
    """Detects when a citizen is getting worse.

    Three types of regression:
    1. Performance regression — success rate declining
    2. Hardware degradation — telemetry trending bad
    3. Calibration drift — position accuracy declining
    """

    # Performance tracking
    performance_history: deque     # (timestamp, success_rate) pairs
    performance_ewma: float = 0.0  # Exponentially weighted moving average
    performance_baseline: float = 0.0  # Established performance level

    # Hardware tracking
    temperature_trend: deque       # Recent temperature readings
    current_trend: deque           # Recent current draw readings
    position_error_trend: deque    # Recent position accuracy readings

    # Alert state
    active_alerts: list[RegressionAlert] = field(default_factory=list)

    def check_performance(self, current_rate: float) -> RegressionAlert | None:
        """Check for performance regression.

        Uses EWMA with sensitivity factor. Alert if EWMA drops
        more than 10% below established baseline.
        """
        alpha = 0.1
        self.performance_ewma = (
            alpha * current_rate + (1 - alpha) * self.performance_ewma
        )

        # Update baseline (slow-moving, only goes up)
        if current_rate > self.performance_baseline:
            self.performance_baseline = (
                0.99 * self.performance_baseline + 0.01 * current_rate
            )

        # Check for regression
        if self.performance_baseline > 0:
            drop = (self.performance_baseline - self.performance_ewma) / self.performance_baseline
            if drop > 0.10:  # 10% below baseline
                return RegressionAlert(
                    alert_type="performance",
                    severity="warning" if drop < 0.20 else "critical",
                    detail=f"Performance dropped {drop:.0%} below baseline "
                           f"({self.performance_ewma:.0%} vs {self.performance_baseline:.0%})",
                    recommended_action=self._recommend_performance_action(drop),
                )
        return None

    def check_hardware(self, telemetry) -> list[RegressionAlert]:
        """Check telemetry trends for hardware degradation.

        Looks for:
        - Rising temperature trend (bearing wear, increased friction)
        - Rising current draw (motor degradation)
        - Increasing position error (encoder/gear wear)
        """
        alerts = []

        # Temperature trend
        if len(self.temperature_trend) >= 20:
            recent = list(self.temperature_trend)[-10:]
            older = list(self.temperature_trend)[:10]
            temp_rise = _mean(recent) - _mean(older)
            if temp_rise > 5.0:  # 5C rise over monitoring window
                alerts.append(RegressionAlert(
                    alert_type="hardware_temperature",
                    severity="warning",
                    detail=f"Temperature rising: +{temp_rise:.1f}C trend",
                    recommended_action="inspect_bearings",
                ))

        # Current draw trend
        if len(self.current_trend) >= 20:
            recent = list(self.current_trend)[-10:]
            older = list(self.current_trend)[:10]
            current_rise = _mean(recent) - _mean(older)
            if current_rise > 200:  # 200mA increase
                alerts.append(RegressionAlert(
                    alert_type="hardware_current",
                    severity="warning",
                    detail=f"Current draw rising: +{current_rise:.0f}mA trend",
                    recommended_action="check_motor_resistance",
                ))

        # Position error trend
        if len(self.position_error_trend) >= 20:
            recent = list(self.position_error_trend)[-10:]
            older = list(self.position_error_trend)[:10]
            error_rise = _mean(recent) - _mean(older)
            if error_rise > 2.0:  # 2 position units
                alerts.append(RegressionAlert(
                    alert_type="calibration_drift",
                    severity="warning",
                    detail=f"Position error increasing: +{error_rise:.1f} units",
                    recommended_action="recalibrate",
                ))

        return alerts

    def _recommend_performance_action(self, drop: float) -> str:
        if drop > 0.30:
            return "emergency_maintenance"
        elif drop > 0.20:
            return "demote_autonomy_and_retrain"
        elif drop > 0.10:
            return "increase_supervision"
        return "monitor"


@dataclass
class RegressionAlert:
    """An alert about detected regression."""
    alert_type: str         # "performance", "hardware_*", "calibration_drift"
    severity: str           # "info", "warning", "critical"
    detail: str
    recommended_action: str
    timestamp: float = field(default_factory=time.time)

    def to_warning(self) -> Warning:
        """Convert to a mycelium Warning for network broadcast."""
        from .mycelium import Warning, Severity
        sev_map = {"info": Severity.LOW, "warning": Severity.MEDIUM, "critical": Severity.HIGH}
        return Warning(
            severity=sev_map.get(self.severity, Severity.MEDIUM),
            detail=self.detail,
            source_citizen="self",
        )
```

**Automated response to regression:**

```python
async def handle_regression(citizen, alert: RegressionAlert):
    """Automated response to detected regression."""

    if alert.recommended_action == "recalibrate":
        # Generate intrinsic goal to recalibrate
        citizen.goals.add(Goal(
            id="recal_" + str(int(time.time())),
            description="Recalibrate — position error drift detected",
            priority=GoalPriority.SURVIVAL,
            skill_required="basic_movement",
        ))

    elif alert.recommended_action == "increase_supervision":
        # Demote autonomy level for affected skill
        for skill in citizen.autonomy.per_skill_levels:
            level = citizen.autonomy.effective_level(skill)
            if level.value > AutonomyLevel.SUPERVISED.value:
                citizen.autonomy.per_skill_levels[skill] = AutonomyLevel(level.value - 1)
                citizen._log(f"autonomy demoted for {skill}: {level.name} -> regression detected")

    elif alert.recommended_action == "demote_autonomy_and_retrain":
        # Severe: demote to SUPERVISED and request governor intervention
        for skill in citizen.autonomy.per_skill_levels:
            citizen.autonomy.per_skill_levels[skill] = AutonomyLevel.SUPERVISED
        # Broadcast warning
        citizen.mycelium.add_warning(alert.to_warning())

    elif alert.recommended_action == "emergency_maintenance":
        # Critical: stop accepting tasks, broadcast SOS
        citizen.state = "maintenance_required"
        citizen.mycelium.add_warning(alert.to_warning())
        citizen._log("REGRESSION CRITICAL — entering maintenance mode")
```

---

## 8. Integration with Existing armOS

### How growth connects to existing modules

| Existing Module | Growth Integration |
|---|---|
| `skills.py` (SkillTree) | CapabilityGates replace simple XP thresholds. SkillTree still tracks XP, but unlocking requires gates to pass. |
| `citizen.py` (Citizen base) | MaturationState added to Citizen. DevelopmentalStage gates what protocol messages a citizen can send. |
| `marketplace.py` (TaskMarketplace) | `can_citizen_bid()` checks both CapabilityGates and AutonomyLevel. SpecializationProfile feeds into bid scoring. |
| `emotional.py` (EmotionalState) | GrowthTracker data feeds into confidence and curiosity. Plateaus reduce confidence. Breakthroughs boost it. |
| `genome.py` (CitizenGenome) | Genome gains `maturation_state`, `autonomy_profile`, `specialization_profile`, `growth_history` fields. |
| `telemetry.py` (ArmTelemetry) | RegressionDetector consumes telemetry data for hardware degradation detection. |
| `constitution.py` (Constitution) | Add a Law for `minimum_developmental_stage` — governor can set minimum stage for each task type. |
| `coordinator.py` (TaskCoordinator) | Only ADULT+ citizens can participate as coordinators in multi-citizen tasks. |
| `consciousness.py` (narrate) | Narration becomes stage-aware: "I am a JUVENILE citizen, working toward ADULT status. 72 of 100 autonomous tasks completed." |
| `SOUL.md` (PersonalityProfile) | Openness drives how eagerly a citizen seeks new task types (anti-specialization). Conscientiousness drives how carefully it tracks its own regression. |

### Implementation plan

**Phase 1: Foundation (maturation.py)**
- `DevelopmentalStage` enum
- `MaturationState` dataclass
- `AutonomyLevel` enum and `AutonomyProfile`
- `CapabilityGate` with multi-factor unlock
- Promotion/demotion logic
- Persistence via genome

**Phase 2: Growth tracking (growth.py)**
- `GrowthTracker` with rolling windows
- Plateau detection
- Breakthrough detection
- `GrowthSnapshot` for historical curves
- Intervention suggestions

**Phase 3: Regression detection (regression.py)**
- `RegressionDetector` consuming telemetry
- Performance EWMA tracking
- Hardware degradation trends
- `RegressionAlert` generation
- Automated response (autonomy demotion, recalibration goals)

**Phase 4: Specialization (specialization.py)**
- `SpecializationProfile` with EMA tracking
- Breadth threshold enforcement
- Marketplace bid score integration
- Anti-over-specialization maintenance goals

**Phase 5: Protocol integration**
- Gate marketplace bids by DevelopmentalStage
- Gate coordinator participation by stage
- Endorsement messages (new MessageType or REPORT subtype)
- Dashboard visualization of growth curves

All modules are pure Python, no GPU, no external services. Dataclasses serialize to JSON and persist through the genome mechanism.

---

## Sources

### Developmental Robotics
- [Developmental Robotics: From Babies to Robots](https://madbrain.ai/developmental-robotics-from-babies-to-robots-f8c1551b000f) — Book review, MadBrain
- [The iCub humanoid robot: An open-systems platform for research in cognitive development](https://www.sciencedirect.com/science/article/abs/pii/S0893608010001619) — ScienceDirect
- [A psychology based approach for longitudinal development in cognitive robotics](https://www.frontiersin.org/journals/neurorobotics/articles/10.3389/fnbot.2014.00001/full) — Frontiers in Neurorobotics
- [From Babies to Robots: The Contribution of Developmental Robotics](https://onlinelibrary.wiley.com/doi/10.1111/cdep.12282) — Child Development Perspectives
- [Piagetian experiments to DevRobotics](https://www.sciencedirect.com/science/article/abs/pii/S1389041723001043) — ScienceDirect

### Intrinsic Motivation and Curiosity-Driven Learning
- [Curiosity, intrinsic motivation and information seeking — Flowers Lab](https://flowers.inria.fr/curiosity/) — INRIA
- [Infant-inspired intrinsically motivated curious robots](https://www.sciencedirect.com/science/article/abs/pii/S2352154620300838) — ScienceDirect
- [Intrinsically Motivated Open-Ended Learning in Autonomous Robots](https://pmc.ncbi.nlm.nih.gov/articles/PMC6978885/) — Frontiers in Robotics and AI
- [Computational Theories of Curiosity-Driven Learning](https://arxiv.org/pdf/1802.10546) — arXiv
- [Autotelic Agents: IMGEP Architecture](https://www.jmlr.org/papers/volume23/21-0808/21-0808.pdf) — JMLR 2022

### Earned Autonomy and Levels of Autonomy
- [Toward a framework for levels of robot autonomy in HRI](https://pmc.ncbi.nlm.nih.gov/articles/PMC5656240/) — PMC
- [NIST ALFUS Framework](https://www.nist.gov/document/alfus-bgpdf) — NIST
- [Levels of Autonomy for Field Robots](https://www.earthsense.co/news/2020/7/24/levels-of-autonomy-for-field-robots) — EarthSense
- [A Learning-based Autonomy Framework for HRI](https://par.nsf.gov/servlets/purl/10326308) — NSF

### Competence-Aware Autonomy
- [Competence-Aware Autonomy: An Essential Skill for Robots](http://rbr.cs.umass.edu/shlomo/papers/BBZaaai23bridge.pdf) — UMass
- [Machine Self-Confidence: Factorized Competency Indicators](https://dl.acm.org/doi/10.1145/3732794) — ACM THRI
- [Event-triggered robot self-assessment for autonomy adjustment](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2023.1294533/full) — Frontiers in Robotics and AI
- [Know your limits! Optimize the robot's behavior through self-awareness](https://arxiv.org/abs/2409.10308) — arXiv

### Multi-Agent Specialization
- [ROMA: Multi-Agent RL with Emergent Roles](http://proceedings.mlr.press/v119/wang20f/wang20f.pdf) — ICML 2020
- [Predicting Multi-Agent Specialization via Task Parallelizability](https://arxiv.org/html/2503.15703) — arXiv 2025
- [Emergent Specialization in Swarm Systems](https://link.springer.com/chapter/10.1007/3-540-45675-9_43) — Springer
- [Multi-Agent Deep RL for Multi-Robot Applications: A Survey](https://pmc.ncbi.nlm.nih.gov/articles/PMC10098527/) — Sensors/MDPI

### Robot Learning Curves and Skill Acquisition
- [Robot skill acquisition in assembly using deep RL](https://www.sciencedirect.com/science/article/abs/pii/S0925231219301316) — ScienceDirect
- [Skill Learning by Autonomous Robotic Playing](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2020.00042/full) — Frontiers in Robotics and AI
- [Google robot grasping at scale](https://spectrum.ieee.org/google-wants-robots-to-acquire-new-skills-by-learning-from-each-other) — IEEE Spectrum
- [Plateaus and the curve of learning in motor skill](https://psycnet.apa.org/record/2011-15839-001) — APA PsycNet

### Predictive Maintenance and Regression Detection
- [AI and robotics in predictive maintenance](https://www.frontiersin.org/journals/mechanical-engineering/articles/10.3389/fmech.2025.1722114/full) — Frontiers in Mechanical Engineering
- [Robot fault detection and remaining life estimation](https://www.sciencedirect.com/science/article/pii/S1877050919305563) — ScienceDirect
- [AI-Enabled Predictive Maintenance for Autonomous Robots](https://pmc.ncbi.nlm.nih.gov/articles/PMC8747287/) — PMC
- [Data analytics for predictive maintenance of industrial robots](https://www.researchgate.net/publication/318688258_Data_analytics_for_predictive_maintenance_of_industrial_robots) — ResearchGate
