---
project: armOS Citizenry v3.0
date: 2026-03-16
status: draft
---

# Architecture — armOS Citizenry v3.0: "The Nation Governs Itself"

## Overview

v3.0 adds 4 new modules (plus 2 stretch) to the existing citizenry package. All new behavior is expressed through the existing 7-message protocol -- no transport or protocol changes. The architecture follows the same patterns established in v1.5 and extended in v2.0: asyncio event loop, UDP multicast + unicast, Ed25519 signing, JSON persistence.

The new modules form a "governance intelligence layer" sitting between the user and the existing protocol machinery:

- **nl_governance.py** -- Translates natural language intent to formal policy changes
- **rollout.py** -- Manages canary deployment of policy changes
- **self_test.py** -- Citizen self-test suite for canary validation
- **will.py** -- Dead citizen's will broadcast and absorption

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        SURFACE PRO 7 (Governor)                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Governance Intelligence Layer (v3.0)                  │ │
│  │                                                                         │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ NLPolicyInterp   │  │  RolloutEngine   │  │   WillArchive        │  │ │
│  │  │                  │  │                  │  │                      │  │ │
│  │  │ Claude API  ─────┤  │ canary_order()   │  │ absorb(will)         │  │ │
│  │  │ keyword fallback │  │ test_one()       │  │ relist_task()        │  │ │
│  │  │ confidence score │  │ commit_or_roll() │  │ merge_immune()       │  │ │
│  │  │ policy_history   │  │ abort()          │  │ will_archive[]       │  │ │
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘  │ │
│  │           │                     │                        │              │ │
│  └───────────┼─────────────────────┼────────────────────────┼──────────────┘ │
│              │                     │                        │                │
│  ┌───────────▼─────────────────────▼────────────────────────▼──────────────┐ │
│  │                     SurfaceCitizen (governor)                            │ │
│  │                                                                         │ │
│  │  v1.5: identity, heartbeat, discovery, constitution, teleop             │ │
│  │  v2.0: marketplace, composition, genome, immune, skills, symbiosis      │ │
│  │  v3.0: nl_governance, rollout_engine, will_archive                      │ │
│  │                                                                         │ │
│  └───────────┬─────────────────────────────────────────────────────────────┘ │
│              │                                                               │
│  ┌───────────▼─────────────────────────────────────────────────────────────┐ │
│  │                 Citizen Base Layer (citizen.py)                          │ │
│  │  Identity │ Heartbeat │ Discovery │ Presence │ Persistence              │ │
│  │  SkillTree │ Genome │ ImmuneMemory │ MyceliumNetwork │ Contracts        │ │
│  │  v3.0: policy_version │ rollback_snapshot │ will_handler                │ │
│  └───────────┬─────────────────────────────────────────────────────────────┘ │
│              │                                                               │
│  ┌───────────▼─────────────────────────────────────────────────────────────┐ │
│  │                 Transport Layer (transport.py)                           │ │
│  │  MulticastTransport (UDP 239.67.84.90:7770)                             │ │
│  │  UnicastTransport (UDP dynamic port)                                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                              │ LAN │
┌─────────────────────────────┼─────┼──────────────────────────────────────────┐
│                      RASPBERRY PI 5 (Follower)                                │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                      PiCitizen (manipulator)                           │   │
│  │                                                                        │   │
│  │  v1.5: identity, heartbeat, servo control, teleop execution            │   │
│  │  v2.0: skills, immune, mycelium, genome, contracts, bidding            │   │
│  │  v3.0: self_test_suite │ will_handler │ canary_mode │ policy_version    │   │
│  │                                                                        │   │
│  │  ┌────────────────────────────┐  ┌─────────────────────────────────┐   │   │
│  │  │     SelfTestSuite          │  │      WillHandler                │   │   │
│  │  │                            │  │                                 │   │   │
│  │  │  joint_range_check()       │  │  register_signals()            │   │   │
│  │  │  load_test()               │  │  compose_will()                │   │   │
│  │  │  fault_check()             │  │  broadcast_will()              │   │   │
│  │  │  camera_check() (camera)   │  │  handle_received_will()        │   │   │
│  │  └────────────────────────────┘  └─────────────────────────────────┘   │   │
│  │                                                                        │   │
│  │  Feetech STS3215 Servo Bus                                             │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Module Dependency Graph

```
protocol.py ──────────────────────────────────────────── (unchanged, foundation)
identity.py ──────────────────────────────────────────── (unchanged)
transport.py ─────────────────────────────────────────── (unchanged)
constitution.py ──────────────────────────────────────── (unchanged)
persistence.py ───────────────────────────────────────── (extended: rollout state, will archive)
mdns.py ──────────────────────────────────────────────── (unchanged)
telemetry.py ─────────────────────────────────────────── (unchanged)

skills.py ────────────────────────────────────────────── (unchanged from v2.0)
marketplace.py ───────────────────────────────────────── (extended: partial progress on re-list)
immune.py ────────────────────────────────────────────── (unchanged from v2.0)
mycelium.py ──────────────────────────────────────────── (unchanged from v2.0)
symbiosis.py ─────────────────────────────────────────── (unchanged from v2.0)
genome.py ────────────────────────────────────────────── (unchanged from v2.0)
composition.py ───────────────────────────────────────── (unchanged from v2.0)

nl_governance.py ── depends on: constitution.py ──────── (NEW)
  └── Anthropic SDK (optional), keyword fallback

self_test.py ──────────────────────────────────────────── (NEW, standalone)
  └── defines SelfTestSuite with pluggable test functions

rollout.py ────────── depends on: self_test.py, persistence.py ── (NEW)
  └── RolloutEngine: ordering, canary dispatch, commit/rollback

will.py ───────────── depends on: immune.py, genome.py ── (NEW)
  └── WillComposer, WillHandler (signal registration + broadcast)

emotional.py ──────────────────────────────────────────── (NEW, stretch, standalone)
consciousness.py ──── depends on: nl_governance.py ────── (NEW, stretch)
  └── shares Anthropic client with nl_governance

citizen.py ─────────── depends on: all above ──────────── (EXTENDED)
  └── adds: policy_version, rollback_snapshot, will_handler

surface_citizen.py ── depends on: citizen.py ──────────── (EXTENDED)
  └── adds: NLPolicyInterpreter, RolloutEngine, WillArchive

pi_citizen.py ─────── depends on: citizen.py ──────────── (EXTENDED)
  └── adds: SelfTestSuite (manipulator tests), will handler

camera_citizen.py ─── depends on: citizen.py ──────────── (EXTENDED)
  └── adds: SelfTestSuite (camera tests), will handler

dashboard.py ──────────────────────────────────────────── (EXTENDED)
  └── new sections: rollout progress, will events, policy history, emotions (stretch)
```

## Data Flow

### Natural Language Governance Flow

```
User                  NLPolicyInterpreter    RolloutEngine         Citizens
 │                         │                      │                    │
 │── "make robots gentle"──►                      │                    │
 │                         │                      │                    │
 │                         │── build_context() ──►│                    │
 │                         │   (constitution +    │                    │
 │                         │    laws + states)    │                    │
 │                         │                      │                    │
 │                         │── call Claude API ──►│                    │
 │                         │   (or keyword match) │                    │
 │                         │                      │                    │
 │                         │◄── LawChange[] ──────│                    │
 │                         │   confidence: 0.85   │                    │
 │                         │                      │                    │
 │◄── "Reduce torque 30%, │                      │                    │
 │    slow by 30%. Apply?" │                      │                    │
 │                         │                      │                    │
 │── "y" ─────────────────►│                      │                    │
 │                         │                      │                    │
 │                         │── start_rollout() ──►│                    │
 │                         │                      │── (canary flow) ──►│
 │                         │                      │                    │
 │◄── "Policy applied to  │                      │                    │
 │    all 3 citizens"      │                      │                    │
```

### Canary Rollout Flow

```
Governor (RolloutEngine)          Citizen-1 (canary)       Citizen-2           Citizen-3
     │                                 │                      │                   │
     │── order_citizens() ──►         │                      │                   │
     │   [c1=lowest risk, c2, c3]     │                      │                   │
     │                                 │                      │                   │
     │── GOVERN (policy_canary) ──────►│                      │                   │
     │   {changes, rollout_id}         │                      │                   │
     │                                 │── save_snapshot()    │                   │
     │                                 │── apply_changes()    │                   │
     │                                 │── run_self_test()    │                   │
     │                                 │   joint_range ✓      │                   │
     │                                 │   load_test ✓        │                   │
     │                                 │   fault_check ✓      │                   │
     │                                 │                      │                   │
     │◄── REPORT (canary_result) ─────│                      │                   │
     │    {passed: true, tests: [...]} │                      │                   │
     │                                 │                      │                   │
     │── GOVERN (policy_canary) ──────────────────────────────►                   │
     │                                 │                      │── self_test()     │
     │◄── REPORT (canary_result) ─────────────────────────────│                   │
     │    {passed: true}               │                      │                   │
     │                                 │                      │                   │
     │── GOVERN (policy_canary) ──────────────────────────────────────────────────►
     │                                 │                      │                   │── self_test()
     │◄── REPORT (canary_result) ─────────────────────────────────────────────────│
     │    {passed: true}               │                      │                   │
     │                                 │                      │                   │
     │── GOVERN (policy_commit) ──────►│◄─────────────────────│◄──────────────────│
     │   {rollout_id}                  │                      │                   │
     │                                 │── discard_snapshot() │── discard()       │── discard()
```

### Canary Failure and Rollback Flow

```
Governor (RolloutEngine)          Citizen-1 (canary)       Citizen-2 (already updated)
     │                                 │                      │
     │── GOVERN (policy_canary) ──────►│                      │
     │                                 │── save_snapshot()    │
     │                                 │── apply_changes()    │
     │                                 │── run_self_test()    │
     │                                 │   joint_range ✗      │
     │                                 │   (elbow can't reach │
     │                                 │    50% at new torque) │
     │                                 │                      │
     │                                 │── revert_snapshot()  │
     │                                 │                      │
     │◄── REPORT (canary_result) ─────│                      │
     │    {passed: false,              │                      │
     │     tests: [{name: "joint_range",                      │
     │              passed: false,     │                      │
     │              detail: "elbow_flex                        │
     │               range reduced 40%"}]}                    │
     │                                 │                      │
     │── failure_rate = 1/3 = 33%     │                      │
     │   > 20% threshold → ABORT      │                      │
     │                                 │                      │
     │── GOVERN (policy_rollback) ────────────────────────────►
     │   {rollout_id, reason}          │                      │── revert_snapshot()
     │                                 │                      │
     │── log: "Rollout aborted"       │                      │
```

### Dead Citizen's Will Flow

```
Pi (dying)                      All Citizens (multicast)      Governor
  │                                    │                         │
  │── SIGTERM received                 │                         │
  │                                    │                         │
  │── enter "dying" state              │                         │
  │── compose_will()                   │                         │
  │   task_state: pick_place 60%       │                         │
  │   joint_positions: {...}           │                         │
  │   telemetry: last 10              │                         │
  │   immune_patterns: [...]           │                         │
  │   contracts: [contract-1]          │                         │
  │   policy_version: 12              │                         │
  │                                    │                         │
  │── REPORT (will) ─────────────────►│ (UDP multicast)         │
  │   (best-effort, single packet)    │                         │
  │                                    │                         │
  │── process exits                    │── merge_immune()        │
  │                                    │── break_contracts()     │
  │                                    │                         │
  │                                    │                      ◄──│
  │                                    │                         │── absorb_will()
  │                                    │                         │── archive_will()
  │                                    │                         │── relist_task()
  │                                    │                         │   (with partial_progress)
  │                                    │                         │── dashboard: "will received"
```

## Module Specifications

### nl_governance.py

```python
class NLPolicyInterpreter:
    """Translates natural language policy intents to formal law changes."""

    def __init__(self, constitution: dict, laws: dict, api_key_path: str):
        """
        Args:
            constitution: Current constitution dict
            laws: Current laws dict {law_id: params}
            api_key_path: Path to Anthropic API key file (~/.citizenry/api_key)
        """

    async def interpret(self, text: str, citizen_states: dict) -> PolicyIntent:
        """
        Translate natural language to policy changes.

        Args:
            text: User's natural language intent
            citizen_states: Current state of all citizens {pubkey: {name, health, state, ...}}

        Returns:
            PolicyIntent with interpreted_changes, confidence, and requires_confirmation
        """

    def _build_prompt(self, text: str, citizen_states: dict) -> str:
        """Build the Claude API prompt with full context."""

    def _parse_response(self, response: str) -> list[LawChange]:
        """Parse Claude's structured response into LawChange objects."""

    def _keyword_fallback(self, text: str) -> PolicyIntent:
        """
        Offline fallback: match keywords to predefined policy changes.
        Handles: gentle/careful, fast/slow, stop/resume, home, aggressive.
        """

    def update_context(self, constitution: dict, laws: dict):
        """Update the interpreter's context after a policy change."""
```

**Claude API prompt structure:**

```
System: You are the governance interpreter for an armOS robot citizenry.
You translate natural language intents into formal law changes.

Current constitution version: {version}
Current laws:
{json_dump of laws}

Current citizen states:
{json_dump of citizen_states}

Available law parameters you can change:
- servo_limits.max_torque (int, 0-1000, current: {value})
- servo_limits.max_velocity (float, 0.0-1.0, current: {value})
- servo_limits.collision_sensitivity (float, 0.0-1.0, current: {value})
- teleop_max_fps.fps (int, 1-120, current: {value})
- idle_timeout.seconds (int, 30-3600, current: {value})
- heartbeat_interval.seconds (float, 0.5-10.0, current: {value})

User intent: "{text}"

Respond with JSON:
{
  "changes": [
    {"law_id": "...", "param": "...", "new_value": ..., "reasoning": "..."}
  ],
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation for the user"
}
```

**Keyword fallback mapping (top 10):**

| Keywords | Law Changes |
|----------|------------|
| "gentle", "careful", "soft" | max_torque * 0.7, max_velocity * 0.7 |
| "aggressive", "strong", "powerful" | max_torque * 1.3, max_velocity * 1.3 |
| "fast", "faster", "speed up" | max_velocity * 1.3, teleop_max_fps + 20 |
| "slow", "slower" | max_velocity * 0.7, teleop_max_fps * 0.7 |
| "half speed" | max_velocity * 0.5, teleop_max_fps * 0.5 |
| "full speed" | max_velocity = 1.0, teleop_max_fps = 60 |
| "stop" | emergency_stop = true |
| "resume", "go", "start" | emergency_stop = false |
| "home", "rest" | idle_timeout = 0 (immediate) |
| "cautious", "safe" | collision_sensitivity * 1.5 |

### rollout.py

```python
@dataclass
class Rollout:
    id: str
    changes: list[LawChange]
    status: str  # pending, rolling, committed, rolled_back, aborted
    citizen_order: list[str]  # pubkeys in rollout order
    results: dict[str, CanaryResult]
    started_at: float
    completed_at: float | None
    failure_threshold: float  # default 0.2
    rollback_snapshot: dict  # pre-change law state
    policy_version: int


class RolloutEngine:
    """Manages canary deployment of policy changes."""

    def __init__(self, persistence_dir: str = "~/.citizenry"):
        self.current_rollout: Rollout | None = None
        self.rollout_history: list[Rollout] = []
        self._persistence_dir = persistence_dir

    def start_rollout(
        self,
        changes: list[LawChange],
        citizens: dict[str, dict],  # pubkey -> {name, xp_total, health_stability, uptime}
        current_laws: dict,
        failure_threshold: float = 0.2,
    ) -> Rollout:
        """
        Begin a new canary rollout.

        Args:
            changes: Law changes to roll out
            citizens: Eligible citizens with their risk metrics
            current_laws: Snapshot of current laws for rollback
            failure_threshold: Max failure rate before abort (default 20%)

        Returns:
            Rollout object with citizen order computed

        Raises:
            RolloutInProgressError: If another rollout is active
        """

    def order_citizens(self, citizens: dict[str, dict]) -> list[str]:
        """
        Order citizens by risk (lowest first).
        Risk = 1.0 / (xp_total * health_stability * uptime_hours + 1)
        """

    def record_result(self, result: CanaryResult) -> str:
        """
        Record a canary result. Returns next action:
        'next' - proceed to next citizen
        'commit' - all passed, send commit
        'abort' - failure threshold exceeded, send rollback
        """

    def get_next_citizen(self) -> str | None:
        """Return the next citizen pubkey to canary test, or None if done."""

    def commit(self) -> None:
        """Mark rollout as committed. Persist to disk."""

    def abort(self, reason: str) -> list[str]:
        """
        Abort rollout. Returns list of citizen pubkeys that need rollback.
        Persists abort state to disk.
        """

    def recover_on_startup(self) -> str | None:
        """
        Check for interrupted rollout on startup.
        Returns 'rollback' if an incomplete rollout is found (triggers auto-rollback).
        Returns None if clean.
        """

    def _persist_state(self) -> None:
        """Atomic write of current rollout state to disk."""

    def _load_state(self) -> None:
        """Load persisted rollout state (for crash recovery)."""
```

### self_test.py

```python
@dataclass
class SelfTestResult:
    test_name: str
    passed: bool
    detail: str
    duration_ms: float


class SelfTestSuite:
    """Pluggable self-test suite for canary validation."""

    def __init__(self):
        self.tests: list[Callable] = []

    def add_test(self, test_fn: Callable) -> None:
        """Register a test function. Signature: async (citizen) -> SelfTestResult"""

    async def run_all(self, citizen) -> tuple[bool, list[SelfTestResult]]:
        """
        Run all registered tests sequentially.
        Returns (all_passed, results).
        Stops on first failure.
        """


# Built-in test functions for manipulator citizens

async def joint_range_check(citizen) -> SelfTestResult:
    """
    Move each joint to 50% of its range at current torque/velocity limits.
    Pass if all joints reach target within 5 seconds each.
    Uses mock bus in test mode, real servos in production.
    """

async def load_test(citizen) -> SelfTestResult:
    """
    Apply a predefined safe motion sequence (home -> 30% reach -> home).
    Pass if no overload, thermal, or voltage faults trigger.
    """

async def fault_check(citizen) -> SelfTestResult:
    """
    Check that zero new fault patterns were created during the test window.
    Reads immune memory before and after the other tests.
    """


# Built-in test functions for camera citizens

async def camera_capture_check(citizen) -> SelfTestResult:
    """
    Capture a frame and verify resolution and format are acceptable.
    """

async def camera_latency_check(citizen) -> SelfTestResult:
    """
    Time 10 consecutive frame captures. Pass if avg < 200ms.
    """
```

### will.py

```python
@dataclass
class CitizenWill:
    citizen_pubkey: str
    citizen_name: str
    timestamp: float
    cause: str
    current_task: dict | None
    joint_positions: dict
    recent_telemetry: list[dict]
    unsent_immune_patterns: list[dict]
    active_contracts: list[str]
    policy_version: int

    def to_report_body(self) -> dict:
        """Serialize to a REPORT body dict."""

    @classmethod
    def from_report_body(cls, body: dict) -> "CitizenWill":
        """Deserialize from a REPORT body dict."""

    def truncate_to_fit(self, max_bytes: int = 60000) -> None:
        """
        Truncate to fit UDP payload limit.
        Priority (highest first): task state, joint positions, contracts,
        policy version, immune patterns, telemetry.
        """


class WillComposer:
    """Composes a will from current citizen state."""

    @staticmethod
    def compose(citizen, cause: str) -> CitizenWill:
        """
        Gather all will data from the citizen's current state.
        Called in the signal handler -- must be fast and non-blocking.
        """


class WillHandler:
    """Manages signal registration and will broadcast."""

    def __init__(self, citizen):
        self.citizen = citizen
        self._registered = False

    def register_signals(self) -> None:
        """
        Register SIGTERM, SIGINT, SIGHUP handlers.
        Each handler: compose will, broadcast, then re-raise for clean exit.
        """

    def _signal_handler(self, signum, frame) -> None:
        """
        Signal handler implementation.
        1. Set citizen state to "dying"
        2. Compose will
        3. Broadcast via multicast (best-effort)
        4. Call original signal handler (or sys.exit)
        """

    def handle_received_will(self, will: CitizenWill) -> None:
        """
        Process a received will from another citizen.
        - Merge immune patterns
        - Mark contracts as broken
        - Log to dashboard
        """
```

### emotional.py (Stretch)

```python
@dataclass
class EmotionalState:
    fatigue: float      # 0.0-1.0
    confidence: float   # 0.0-1.0
    curiosity: float    # 0.0-1.0
    computed_at: float
    inputs: dict

    def label(self) -> str:
        """
        Human-readable label:
        - fatigue > 0.7: "tired"
        - confidence > 0.8 and fatigue < 0.3: "focused"
        - confidence < 0.3: "uncertain"
        - curiosity > 0.7: "curious"
        - else: "steady"
        """

    def to_heartbeat_payload(self) -> dict:
        """Serialize for piggybacking on heartbeat."""


class EmotionalEngine:
    """Computes emotional state from telemetry."""

    def __init__(self):
        self._error_history: deque = deque(maxlen=300)  # last 5 min at 1Hz
        self._command_history: deque = deque(maxlen=300)
        self._task_results: deque = deque(maxlen=20)    # last 20 task outcomes
        self._sensor_history: deque = deque(maxlen=100)  # for novelty detection

    def compute(
        self,
        avg_motor_temp: float,
        max_motor_temp: float,
        uptime_seconds: float,
        current_voltage: float,
        nominal_voltage: float,
        current_task_type: str | None,
    ) -> EmotionalState:
        """Compute emotional state from current telemetry."""

    def record_error(self) -> None:
        """Record an error event for fatigue/confidence calculation."""

    def record_command(self) -> None:
        """Record a command for error rate calculation."""

    def record_task_result(self, task_type: str, success: bool) -> None:
        """Record task outcome for confidence calculation."""

    def record_sensor_state(self, state_vector: list[float]) -> None:
        """Record sensor state for curiosity/novelty calculation."""
```

### consciousness.py (Stretch)

```python
class ConsciousnessStream:
    """Generates natural language narrations of citizen state."""

    def __init__(self, use_api: bool = False, api_client=None):
        """
        Args:
            use_api: If True, use Anthropic API. If False, use templates.
            api_client: Shared Anthropic client (from nl_governance).
        """

    async def narrate(self, citizen_state: dict) -> str:
        """
        Generate a narration from structured state.

        citizen_state includes: task, phase, joint_loads, health,
        emotional_state, recent_events.
        """

    def _template_narrate(self, state: dict) -> str:
        """
        Template-based narration (for Pi / offline).

        Templates:
        - "Executing {task}. {highest_load_joint} load at {load}%."
        - "Idle. Health: {health}. Uptime: {uptime}."
        - "Waiting for task assignment. {n_neighbors} neighbors online."
        """

    async def _api_narrate(self, state: dict) -> str:
        """
        Claude API narration (for Surface with internet).
        Uses a small, cheap prompt to generate 1-2 sentences.
        """
```

## Integration Points

### citizen.py Extensions

The base `Citizen` class gains:

```python
# New attributes
self.policy_version: int = 0
self.rollback_snapshot: dict | None = None
self.will_handler: WillHandler = WillHandler(self)
self.self_test_suite: SelfTestSuite = SelfTestSuite()
# stretch:
self.emotional_engine: EmotionalEngine | None = None
self.emotional_state: EmotionalState | None = None
```

New lifecycle integration:

- `start()`: Call `self.will_handler.register_signals()` after transport start
- `stop()`: Normal shutdown -- save state but do NOT broadcast will
- `_send_heartbeat()`: Include `policy_version` in body; include `emotional_state` if computed (stretch)
- `_handle_govern()`: New cases for `policy_canary`, `policy_commit`, `policy_rollback`
- `_handle_report()`: New case for `type: "will"`

New handler methods:

```python
def _handle_canary(self, env, addr):
    """Receive canary policy, save snapshot, apply, self-test, report."""

def _handle_commit(self, env, addr):
    """Discard rollback snapshot, finalize policy."""

def _handle_rollback(self, env, addr):
    """Revert to rollback snapshot."""

def _handle_will(self, env, addr):
    """Process received will: merge immune, break contracts, log."""
```

### surface_citizen.py Extensions

Governor gains:

```python
# New attributes
self.nl_interpreter: NLPolicyInterpreter
self.rollout_engine: RolloutEngine
self.policy_history: list[PolicyIntent] = []
self.will_archive: list[CitizenWill] = []

# New methods
async def interpret_policy(self, text: str) -> PolicyIntent:
    """NL -> policy changes. Prompts for confirmation if needed."""

async def apply_policy(self, intent: PolicyIntent) -> None:
    """Feed changes to rollout engine, begin canary deployment."""

def _handle_canary_result(self, env, addr):
    """Process canary result, advance or abort rollout."""

def _absorb_will(self, will: CitizenWill):
    """Archive will, relist task with partial progress, merge data."""
```

The existing `update_law()` method is modified to route through the rollout engine instead of broadcasting directly:

```python
def update_law(self, law_id: str, params: dict, force: bool = False):
    """Update a law via rollout engine (or force for emergencies)."""
    changes = [LawChange(law_id=law_id, param=k, old_value=self.laws.get(law_id, {}).get(k), new_value=v)
               for k, v in params.items()]
    if force:
        # Emergency: skip canary, broadcast directly (existing behavior)
        ...
    else:
        # Normal: start rollout
        self.rollout_engine.start_rollout(changes, ...)
```

### pi_citizen.py Extensions

Follower gains:

- Self-test suite with manipulator-specific tests (joint_range_check, load_test, fault_check)
- Will handler with signal registration
- Canary mode: save/apply/test/report cycle
- Policy version tracking

### camera_citizen.py Extensions

Camera citizen gains:

- Self-test suite with camera-specific tests (capture_check, latency_check)
- Will handler with signal registration
- Canary mode (simplified: camera tests only)

### marketplace.py Extensions

Task re-listing with partial progress:

```python
def relist_with_progress(self, task_id: str, partial_progress: dict) -> Task:
    """
    Re-list a task in the marketplace with partial progress from a dead citizen's will.
    The partial_progress dict is attached to the task so bidders can resume.
    """
```

### dashboard.py Extensions

New TUI sections:

- **POLICY**: Current policy version, last NL intent, rollout status
- **ROLLOUT**: Progress bar (X/Y citizens passed), pass/fail per citizen
- **WILLS**: Recent will events with cause, task state, and absorption status
- **EMOTIONS** (stretch): Per-citizen emotional state labels and bars
- **CONSCIOUSNESS** (stretch): Latest narration per citizen

## Persistence Schema

v3.0 additions to `~/.citizenry/`:

```
~/.citizenry/
├── <name>.key                    # Ed25519 private key (v1.5)
├── <name>.neighbors.json         # Neighbor table (v1.5)
├── <name>.constitution.json      # Constitution (v1.5)
├── <name>.genome.json            # Citizen genome (v2.0)
├── <name>.immune.json            # Immune memory patterns (v2.0)
├── <name>.contracts.json         # Active symbiosis contracts (v2.0)
├── <name>.skills.json            # Skill tree + XP (v2.0)
├── <name>.rollout.json           # Active rollout state (v3.0) -- for crash recovery
├── <name>.policy_history.json    # NL policy change history (v3.0)
├── <name>.will_archive.json      # Received wills (v3.0, governor only)
├── <name>.rollback_snapshot.json # Law snapshot during canary (v3.0) -- deleted on commit
└── api_key                       # Anthropic API key (v3.0, 0600 perms, governor only)
```

## Security Model

Extends v2.0 security model with:

- **Policy changes signed by governor**: All GOVERN messages (canary, commit, rollback) are signed with the governor's Ed25519 key. Citizens verify before applying.
- **Wills signed by dying citizen**: Receivers verify the will's signature against the known neighbor pubkey before absorbing data. Prevents spoofed wills from injecting bad immune patterns.
- **API key isolation**: The Anthropic API key is stored outside the citizenry package, not deployed to Pi via rsync. `deploy.sh` excludes `api_key`.
- **NL interpreter sandboxing**: The interpreter's output (LawChange objects) is validated against allowed parameter ranges before application. Claude cannot produce changes outside the defined law schema.

## Performance Budget

| Operation | Budget | Mechanism |
|-----------|--------|-----------|
| NL interpretation (API) | < 5s | Single Claude Haiku call, ~2KB context |
| NL interpretation (fallback) | < 50ms | Keyword regex match |
| Canary self-test (manipulator) | < 10s | 3 tests: range (5s), load (3s), fault (1s) |
| Canary self-test (camera) | < 5s | 2 tests: capture (2s), latency (3s) |
| Full rollout (5 citizens) | < 60s | Sequential canary, 10s per citizen + overhead |
| Will composition | < 50ms | In-memory data gathering, no I/O |
| Will broadcast | < 100ms | Single UDP multicast packet |
| Will absorption | < 10ms | JSON parse + merge |
| Emotional state computation | < 1ms | Arithmetic on cached telemetry (stretch) |
| Consciousness narration (API) | < 3s | Single short prompt (stretch) |
| Consciousness narration (template) | < 1ms | String formatting (stretch) |
| Memory per citizen | < 55MB RSS | v2.0 baseline + ~5MB for v3.0 state |

## Error Handling

All v3.0 modules follow the established pattern: catch exceptions at the handler level, log them, and continue.

Specific error handling:

| Scenario | Behavior |
|----------|----------|
| Anthropic API timeout | Fall back to keyword engine, log warning |
| Anthropic API auth failure | Fall back to keyword engine, log error, prompt user to check api_key |
| API budget exhausted | Fall back to keyword engine, log warning with budget status |
| Invalid NL response from Claude | Reject interpretation, ask user to rephrase |
| Canary self-test timeout (>10s) | Treat as failure, trigger rollback |
| Rollout state file corrupted | Treat as interrupted rollout, trigger rollback |
| Will broadcast fails (socket error) | Log error, proceed with process exit (will is best-effort) |
| Will too large for UDP | Truncate per priority order, send truncated will |
| Signal handler re-entrant call | Guard with `_dying` flag, ignore re-entrant signals |
| Unknown GOVERN type in v3.0 message received by v2.0 citizen | Ignored (existing v2.0 behavior) |

## Testing Strategy

| Level | What | How |
|-------|------|-----|
| Unit | NL interpreter with mocked API | pytest, mock anthropic client |
| Unit | Keyword fallback completeness | pytest, all 10 keyword categories |
| Unit | Rollout engine state machine | pytest, mock citizens |
| Unit | Self-test suite individual tests | pytest, mock servo bus |
| Unit | Will composition and parsing | pytest, no hardware |
| Unit | Emotional state computation | pytest, synthetic telemetry (stretch) |
| Integration | Full rollout: canary -> commit | pytest-asyncio, 3 mock citizens on localhost |
| Integration | Full rollout: canary -> abort -> rollback | pytest-asyncio, inject failure |
| Integration | Will broadcast and absorption | pytest-asyncio, send SIGTERM to test process |
| Integration | NL -> rollout -> citizens updated | pytest-asyncio, mocked API + mock citizens |
| Protocol compat | v3.0 messages are valid v2.0 envelopes | Envelope roundtrip tests |
| Protocol compat | v2.0 citizen ignores v3.0 body types | Send v3.0 GOVERN to v2.0 mock citizen |
| Manual | Real hardware NL governance demo | Surface + Pi + camera, spoken intents |
| Manual | Power-pull will test | Unplug Pi during task, verify will received |

## API Cost Model

| Feature | Model | Est. Tokens/Call | Est. Cost/Call | Frequency |
|---------|-------|-----------------|----------------|-----------|
| NL governance | Claude Haiku | ~500 in, ~200 out | ~$0.001 | Per policy change (~5/session) |
| Consciousness (stretch) | Claude Haiku | ~300 in, ~100 out | ~$0.0005 | 12/min when enabled |

Estimated monthly cost at typical usage (3 sessions/week, consciousness disabled): < $0.10
Estimated monthly cost with consciousness enabled (2 hours/day): ~$5.00

The `monthly_api_budget` law defaults to $5.00 and enforces a hard cap.

## Migration from v2.0

v3.0 is fully backward compatible with v2.0:

1. **No protocol changes**: Same 7 message types, same envelope format
2. **New GOVERN body types**: v2.0 citizens ignore unknown `type` values in GOVERN bodies (existing behavior in `_handle_govern` which only processes known types)
3. **New REPORT body types**: v2.0 citizens ignore unknown `type` values in REPORT bodies (same pattern)
4. **New persistence files**: v3.0 creates new files (rollout.json, policy_history.json, etc.) alongside existing v2.0 files. No schema changes to existing files.
5. **Governor upgrade**: Update Surface citizenry code, install `anthropic` SDK, add API key. No changes to Pi needed for governor-side features.
6. **Citizen upgrade**: Update Pi citizenry code. New features (self-test, will) activate automatically. No configuration needed.
7. **Mixed fleet**: A v3.0 governor can manage v2.0 citizens. Canary policies sent to v2.0 citizens are ignored (unknown GOVERN type), so the rollout engine treats them as "not participating" and skips them. Wills are only broadcast by v3.0 citizens.
