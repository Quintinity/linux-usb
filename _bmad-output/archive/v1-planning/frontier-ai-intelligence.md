# armOS Frontier AI Intelligence Layer -- Horizon 3 Roadmap

**Date:** 2026-03-15
**Authors:** Winston (Architect) + Amelia (Developer)
**Status:** Draft -- Frontier Research Roadmap
**Scope:** 18-36 months out. Builds on Horizon 1 (USB stick) and Horizon 2 (platform). This document specifies what's realistic on CPU-only hardware (Intel i5-1035G4, 8GB RAM, no GPU) and what requires cloud offloading.

---

## Table of Contents

1. [Embodied AI Agent -- Natural Language Robot Control](#1-embodied-ai-agent)
2. [Self-Diagnosing Robot -- AI-Powered Telemetry Analysis](#2-self-diagnosing-robot)
3. [Cross-Robot Learning -- Federated Intelligence](#3-cross-robot-learning)
4. [Sim-to-Real Pipeline](#4-sim-to-real-pipeline)
5. [Vision-Language-Action Models](#5-vision-language-action-models)
6. [Autonomous Data Collection](#6-autonomous-data-collection)
7. [Hardware Constraints Reference](#7-hardware-constraints-reference)
8. [Implementation Phasing](#8-implementation-phasing)
9. [ADRs](#9-adrs)

---

## 1. Embodied AI Agent

### 1.1 The Vision

A user says "pick up the red block and put it on the blue plate." The system:

1. Parses the command (language model)
2. Grounds objects in the camera feed (vision model)
3. Plans a trajectory (motion planner)
4. Executes servo commands (HAL)
5. Monitors execution and retries on failure (closed-loop control)

This is the "Siri for robots" moment -- the thing that makes robotics accessible to people who can't write Python.

### 1.2 Latency Budget

The entire pipeline from speech to servo motion must complete in under 2 seconds for the interaction to feel responsive. Here's the budget:

```
Speech-to-text:        200ms  (local Whisper tiny/base)
Language understanding: 500ms  (cloud API or local SLM)
Visual grounding:       300ms  (local YOLO or OWL-ViT)
Motion planning:        200ms  (analytical IK + RRT)
Servo execution:        500ms  (first motion visible)
Safety check:            50ms  (collision/torque limits)
─────────────────────────────
Total:                ~1750ms
```

For repetitive tasks after the first command, the pipeline drops to ~500ms (skip STT, cache visual grounding, replay adapted trajectory).

### 1.3 Architecture

```
+------------------------------------------------------------------+
|                    EMBODIED AI AGENT                              |
|                                                                    |
|  +------------------+    +------------------+    +--------------+ |
|  | Speech Input     |    | Text Input       |    | API Input    | |
|  | (Whisper tiny)   |    | (CLI/TUI)        |    | (REST/WS)   | |
|  +--------+---------+    +--------+---------+    +------+-------+ |
|           |                       |                      |        |
|           +-----------+-----------+----------------------+        |
|                       |                                           |
|           +-----------v-----------+                               |
|           | Intent Parser         |                               |
|           | (SLM or cloud LLM)    |                               |
|           | Outputs: action,      |                               |
|           |   objects, modifiers  |                               |
|           +-----------+-----------+                               |
|                       |                                           |
|           +-----------v-----------+                               |
|           | Visual Grounder       |                               |
|           | (YOLO-World / OWLv2)  |                               |
|           | Input: camera frame + |                               |
|           |   object names        |                               |
|           | Output: bounding box, |                               |
|           |   6D pose estimate    |                               |
|           +-----------+-----------+                               |
|                       |                                           |
|           +-----------v-----------+                               |
|           | Motion Planner        |                               |
|           | Analytical IK for     |                               |
|           |   SO-101 kinematics   |                               |
|           | RRT/PRM for obstacle  |                               |
|           |   avoidance           |                               |
|           +-----------+-----------+                               |
|                       |                                           |
|           +-----------v-----------+                               |
|           | Execution Monitor     |                               |
|           | Closed-loop: compare  |                               |
|           |   expected vs actual  |                               |
|           |   servo positions     |                               |
|           | Retry / replan on     |                               |
|           |   failure             |                               |
|           +----------+------------+                               |
|                      |                                            |
+----------------------|--------------------------------------------+
                       v
              armOS HAL (servo commands)
```

### 1.4 Model Selection for CPU Inference

Every model in the pipeline must run on an Intel i5-1035G4 (4 cores, 8 threads, AVX2, no GPU). Here are the realistic options:

#### Speech-to-Text

| Model | Size | RAM | Latency (i5) | Quality | Recommendation |
|-------|------|-----|-------------|---------|----------------|
| Whisper tiny | 39 MB | ~200 MB | 150-300ms/5s audio | Decent for commands | **Use this** |
| Whisper base | 74 MB | ~400 MB | 300-600ms/5s audio | Good for commands | Fallback |
| Whisper small | 244 MB | ~1 GB | 2-4s/5s audio | Very good | Too slow |
| Whisper large-v3 | 1.5 GB | ~4 GB | 15-30s/5s audio | Excellent | Cloud only |

**Runtime:** whisper.cpp (C++ with AVX2 optimizations). Do NOT use the Python whisper package -- it pulls in PyTorch and is 10x slower on CPU.

**Decision:** Whisper tiny via whisper.cpp for local. Robot commands are short, structured sentences -- tiny is sufficient. For noisy environments, fall back to cloud API.

#### Language Understanding (Intent Parsing)

The intent parser converts "pick up the red block" into structured output:

```json
{"action": "pick", "object": "block", "color": "red", "destination": null}
```

| Model | Size | RAM | Latency (i5) | Recommendation |
|-------|------|-----|-------------|----------------|
| Rule-based parser | 0 MB | 0 MB | <1ms | **Phase 1: start here** |
| TinyLlama 1.1B (Q4) | 700 MB | ~1.5 GB | 2-5s | Phase 2: structured commands |
| Phi-3 mini 3.8B (Q4) | 2.3 GB | ~4 GB | 8-15s | Too slow for real-time |
| Gemma 2 2B (Q4) | 1.5 GB | ~3 GB | 5-10s | Borderline |
| Claude API | 0 MB | 0 MB | 300-800ms | **Phase 1: complex commands** |

**Runtime for local SLMs:** llama.cpp with GGUF quantized models. Supports AVX2, no GPU needed.

**Decision:** Hybrid approach.
- Phase 1: Rule-based parser for a fixed vocabulary of robot actions (pick, place, move, pour, stack, sweep). Handles 80% of commands with <1ms latency.
- Phase 1 fallback: Cloud LLM API for commands the rule parser can't handle. 500ms latency is acceptable for novel commands.
- Phase 2: TinyLlama 1.1B Q4_K_M via llama.cpp for offline-capable intent parsing. 2-5 second latency is acceptable when the user has already initiated a "thinking" mode.
- Phase 3: Fine-tuned small model on robot command dataset (see Section 6).

#### Visual Grounding (Object Detection + Localization)

| Model | Size | RAM | Latency (i5) | Open-vocab | Recommendation |
|-------|------|-----|-------------|------------|----------------|
| YOLOv8n | 6 MB | ~200 MB | 30-50ms | No (fixed classes) | Fast, limited |
| YOLOv8s | 22 MB | ~400 MB | 80-120ms | No | Good balance |
| YOLO-World-S | 50 MB | ~600 MB | 150-250ms | **Yes** | **Use this** |
| OWL-ViT base | 600 MB | ~2 GB | 500-1000ms | Yes | Too slow |
| Grounding DINO-T | 350 MB | ~1.5 GB | 800-1500ms | Yes | Too slow |

**Runtime:** ONNX Runtime with OpenVINO execution provider. This is critical -- running PyTorch models on CPU is 3-5x slower than the optimized ONNX path.

**Decision:** YOLO-World-S via ONNX Runtime. It handles open-vocabulary detection ("find the red block" works without pretraining on blocks). At 150-250ms on CPU, it fits the latency budget. Export the model to ONNX once, ship it with armOS.

For 6D pose estimation (needed for grasping), add a lightweight pose head or use depth estimation from stereo cameras if available. On a single USB camera, use PnP with known object dimensions.

#### Motion Planning

No ML model needed. Analytical inverse kinematics for the SO-101's 6-DOF chain:

- **IKFast** (OpenRAVE): Generates a closed-form IK solver for the specific arm geometry. Compiles to C, runs in microseconds.
- **ikpy**: Pure Python IK library. Slower (~10ms) but simpler to integrate. Good enough for Phase 1.
- **RRT/PRM** for obstacle avoidance: Only needed if the workspace has obstacles. Use `roboticstoolbox-python` (Peter Corke's library) -- pure NumPy, no GPU dependency.

**Decision:** ikpy for Phase 1 (simplicity), migrate to IKFast for production (speed). Trajectory interpolation in joint space with velocity/acceleration limits from the robot profile.

### 1.5 Cloud vs Local Decision Framework

```
User command
    |
    v
[Rule-based parser succeeds?]
    |                    |
   YES                  NO
    |                    |
    v                    v
[Use local pipeline]  [Internet available?]
 - YOLO-World            |           |
 - IK solver            YES          NO
 - Direct execution      |           |
                         v           v
                 [Cloud LLM API]  [Local SLM]
                  ~500ms           ~3-5s
                         |           |
                         v           v
                 [Parse response, continue with local pipeline]
```

The principle: compute-heavy perception (vision) and control (IK) always run locally. Language understanding is the only component that benefits from cloud offloading, and only for complex/novel commands.

### 1.6 Safety Architecture

Natural language control introduces a new class of safety risks. A misheard "stop" could be "stomp."

```python
class SafetyGovernor:
    """Wraps all agent-initiated servo commands with safety checks."""

    def validate_trajectory(self, trajectory: JointTrajectory) -> SafetyVerdict:
        """Check trajectory against safety constraints:
        1. Joint limits (from robot profile)
        2. Velocity limits (max 60 deg/s for safety)
        3. Self-collision (arm geometry check)
        4. Workspace bounds (configurable keep-out zones)
        5. Torque limits (from servo protection settings)
        """

    def validate_force(self, expected_load: dict[str, float]) -> SafetyVerdict:
        """Predict servo loads for planned motion.
        Reject if any servo would exceed 80% of Overload_Torque setting."""

    def emergency_stop(self) -> None:
        """Immediate torque disable on all servos.
        Triggered by: voice command 'stop', safety violation,
        or watchdog timeout (no heartbeat from agent for 500ms)."""
```

**Hard rule:** The safety governor cannot be bypassed by the AI agent. It operates at the HAL level, below the agent. This is the same pattern as ADAS in cars -- the AI suggests, the safety system has veto power.

### 1.7 Implementation Phases

| Phase | Scope | Timeline | Dependencies |
|-------|-------|----------|--------------|
| 1a | Rule-based commands ("move left", "open gripper") | Month 18-20 | HAL, robot profiles |
| 1b | Cloud LLM for complex commands + YOLO-World grounding | Month 20-22 | Cloud API, camera pipeline |
| 1c | Whisper STT for voice commands | Month 22-24 | Audio input pipeline |
| 2 | Local SLM (TinyLlama) for offline intent parsing | Month 24-28 | llama.cpp integration |
| 3 | Closed-loop execution monitoring + retry | Month 28-32 | Telemetry stream |
| 4 | Fine-tuned intent model on robot command dataset | Month 32-36 | Data collection (Section 6) |

---

## 2. Self-Diagnosing Robot

### 2.1 The Vision

The diagnostic suite (`diagnose_arms.py`) already checks servo health, voltage, temperature, firmware, and communication reliability. Today it produces a report. Tomorrow it becomes an AI agent that:

- Watches telemetry continuously (not just on-demand)
- Correlates patterns across time ("temperature rising 2C/hour for the last 3 hours")
- Predicts failures before they happen ("this load pattern usually precedes bearing failure")
- Recommends actions in natural language ("reduce max torque to 70%, order replacement")
- Learns from the fleet (Section 3) what "normal" looks like for this hardware configuration

### 2.2 Architecture

```
+-------------------------------------------------------------------+
|                 SELF-DIAGNOSING ROBOT                              |
|                                                                     |
|  +---------------------+     +---------------------------+         |
|  | Telemetry Collector  |     | Historical Database       |        |
|  | (HAL -> SQLite)      |---->| (SQLite, 90-day window)   |        |
|  | 10 Hz per servo      |     | ~500 MB for 90 days       |        |
|  +---------------------+     +-------------+-------------+         |
|                                             |                       |
|  +------------------------------------------v-------------------+  |
|  | Anomaly Detection Engine                                      | |
|  |                                                                | |
|  | Layer 1: Rule-based (thresholds from robot profile)           | |
|  |   - Temperature > 55C -> WARN                                 | |
|  |   - Voltage < 6V -> CRITICAL                                  | |
|  |   - Load > 90% for > 5s -> WARN                               | |
|  |                                                                | |
|  | Layer 2: Statistical (rolling window anomaly detection)       | |
|  |   - Z-score on 1h rolling window per servo per metric         | |
|  |   - Detects: gradual drift, sudden spikes, periodic patterns  | |
|  |   - Implementation: NumPy only, no ML framework               | |
|  |                                                                | |
|  | Layer 3: ML anomaly detection (isolation forest / autoencoder)| |
|  |   - Trained on "normal" telemetry from this specific arm      | |
|  |   - Detects: multi-variate anomalies (temp+load correlation)  | |
|  |   - Implementation: scikit-learn (isolation forest, 5ms/pred) | |
|  |     or ONNX autoencoder (10ms/pred)                           | |
|  |                                                                | |
|  | Layer 4: LLM interpretation (optional, cloud or local)        | |
|  |   - Takes anomaly alerts + telemetry context                  | |
|  |   - Produces natural language diagnosis + recommendation      | |
|  |   - "Your elbow servo temperature has increased from 31C to   | |
|  |     45C over the last 2 hours while load remained constant.   | |
|  |     This suggests bearing degradation. Recommended: reduce    | |
|  |     Overload_Torque from 90 to 70 and inspect the joint."    | |
|  +--------------------------------------------------------------+ |
|                              |                                      |
|  +---------------------------v----------------------------------+  |
|  | Alert System                                                  | |
|  | - TUI notification bar                                        | |
|  | - Web dashboard alert panel                                   | |
|  | - CLI: armos health (summary) / armos health --detail         | |
|  | - Optional: webhook for fleet hub                             | |
|  +--------------------------------------------------------------+ |
+-------------------------------------------------------------------+
```

### 2.3 Anomaly Detection Models -- What Runs on CPU

#### Isolation Forest (scikit-learn)

The best starting point for servo anomaly detection. No neural network, trains in seconds, predicts in microseconds.

- **Training data:** 1 hour of "normal" telemetry per servo (6 servos x 6 metrics x 36,000 samples = ~1.3M data points)
- **Training time:** <5 seconds on i5
- **Prediction time:** <1ms per sample
- **Memory:** <50 MB per model
- **Features per sample:** [position, velocity, load, voltage, temperature, position_error]
- **What it catches:** Anything that deviates from the learned "normal" distribution -- gradual bearing wear (load increases for same position), loose connection (intermittent voltage drops), calibration drift (position error grows)

```python
from sklearn.ensemble import IsolationForest

class ServoAnomalyDetector:
    """Per-servo anomaly detection using Isolation Forest."""

    def __init__(self, servo_id: int, contamination: float = 0.01):
        self._model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        )
        self._servo_id = servo_id
        self._scaler = StandardScaler()

    def train(self, telemetry: pd.DataFrame) -> None:
        """Train on 'normal' telemetry. Call during initial calibration
        or after a 'retrain' command.
        Columns: position, velocity, load, voltage, temperature, position_error
        """
        X = self._scaler.fit_transform(telemetry.values)
        self._model.fit(X)

    def predict(self, sample: np.ndarray) -> AnomalyResult:
        """Returns NORMAL or ANOMALY with anomaly score.
        score < -0.5 is suspicious, < -0.7 is likely anomalous."""
        X = self._scaler.transform(sample.reshape(1, -1))
        score = self._model.decision_function(X)[0]
        return AnomalyResult(
            is_anomaly=score < -0.5,
            score=score,
            servo_id=self._servo_id,
        )
```

#### Autoencoder (for multi-servo correlation)

An autoencoder captures relationships *between* servos that isolation forest misses. For example: when the shoulder lifts, elbow load increases proportionally. If that proportionality changes, something is wrong.

- **Architecture:** 36-input (6 servos x 6 features) -> 18 -> 8 -> 18 -> 36-output
- **Size:** ~10 KB weights
- **Training:** 30 seconds on CPU (PyTorch), then export to ONNX
- **Inference:** 5-10ms via ONNX Runtime
- **Memory:** <100 MB including ONNX Runtime

```python
class MultiServoAutoencoder(nn.Module):
    """Detects anomalies in cross-servo correlations."""
    def __init__(self, n_servos: int = 6, n_features: int = 6):
        super().__init__()
        input_dim = n_servos * n_features  # 36
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 18), nn.ReLU(),
            nn.Linear(18, 8), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 18), nn.ReLU(),
            nn.Linear(18, input_dim),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

    # Anomaly = high reconstruction error
    # Train on normal data, threshold at 95th percentile of training error
```

**Decision:** Start with isolation forest per servo (Layer 3a). Add autoencoder for cross-servo correlation (Layer 3b) when we have enough fleet data to validate it adds value.

### 2.4 Failure Prediction -- What We Can Actually Predict

Based on STS3215 failure modes documented in our servo tuning notes:

| Failure Mode | Predictive Signal | Detection Method | Lead Time |
|-------------|-------------------|------------------|-----------|
| Bearing wear | Load increases for same motion over days | Linear regression on load-vs-position slope | Days to weeks |
| Overheating shutdown | Temperature ramp rate exceeds historical baseline | Rate-of-change threshold | 10-30 minutes |
| Voltage collapse (PSU overload) | Voltage drops correlate with aggregate load spikes | Multi-servo load sum vs voltage regression | Seconds (real-time) |
| Cable fatigue | Intermittent communication errors increase over weeks | Error rate trend (exponential smoothing) | Days |
| Calibration drift | Position error grows monotonically between calibrations | Drift rate on position_error | Hours to days |
| Gear tooth damage | Periodic load spikes at specific joint angles | FFT on load signal vs position | Immediate (post-event) |

These are all detectable with classical statistics or simple ML. No LLM needed for detection -- the LLM adds value in **explanation and recommendation**, not detection.

### 2.5 LLM Integration for Diagnosis Reports

When an anomaly is detected, the system builds a context packet and sends it to an LLM for interpretation:

```python
class DiagnosisContextBuilder:
    """Builds LLM-readable context from anomaly events."""

    def build_context(self, anomaly: AnomalyEvent) -> str:
        """Produces a structured context string like:

        ANOMALY DETECTED: servo elbow_flex (ID 3)
        ANOMALY TYPE: temperature_rising
        CURRENT: 45.2C (baseline: 31-33C)
        TREND: +2.1C/hour over last 3 hours
        LOAD PATTERN: 45-55% (unchanged from baseline)
        VOLTAGE: 11.8V (stable)
        RECENT EVENTS: recalibrated 2 days ago, no firmware changes
        FLEET CONTEXT: 92% of SO-101 arms with STS3215 v3.10 report
            elbow_flex baseline temps of 28-35C at similar load levels.
        MAINTENANCE HISTORY: servo replaced 6 months ago.

        QUESTION: What is the likely cause and recommended action?
        """
```

**Where the LLM runs:**
- **Cloud API (preferred):** Claude or GPT-4o. Diagnosis reports are infrequent (maybe once per session) and not latency-critical. A 2-second API call is fine.
- **Local fallback:** TinyLlama 1.1B can generate basic recommendations from a template-augmented prompt. Quality is lower but works offline.
- **Hybrid:** Detect locally, explain via cloud. If no internet, use templated explanations ("Temperature anomaly detected on {servo}. Possible causes: bearing wear, insufficient cooling, overloading. Recommended: reduce Overload_Torque to {current * 0.7}").

### 2.6 Implementation Phases

| Phase | Scope | Timeline | RAM Impact |
|-------|-------|----------|------------|
| 1 | Rule-based thresholds (already partially in diagnose_arms.py) | Month 18-19 | ~0 MB |
| 2 | Statistical anomaly detection (z-score rolling windows) | Month 19-20 | ~50 MB |
| 3 | Isolation forest per servo | Month 20-22 | ~100 MB |
| 4 | LLM diagnosis reports (cloud API) | Month 22-24 | ~0 MB (cloud) |
| 5 | Multi-servo autoencoder | Month 24-26 | ~100 MB |
| 6 | Failure prediction (trend extrapolation) | Month 26-28 | ~50 MB |
| 7 | Local SLM for offline diagnosis reports | Month 28-30 | ~1.5 GB |

---

## 3. Cross-Robot Learning

### 3.1 The Vision

Every armOS instance is a data point. A fleet of 10,000 SO-101 arms collectively knows more about optimal settings than any single user or engineer. Cross-robot learning turns that collective knowledge into better defaults.

Example insights that emerge from fleet data:

- "SO-101 arms with STS3215 firmware v3.10 and 12V 5A supply: optimal P_Coefficient is 18, not the factory default of 16. Arms using 18 show 23% less position oscillation."
- "Elbow servo bearing failure probability increases 4x after 500 hours of operation at >60% average load."
- "Temperature differential between room temp and servo temp >20C correlates with 3x higher calibration drift rate."

### 3.2 What Data Is Shared (Privacy Boundaries)

```
SHARED (anonymized aggregates):
  - Hardware configuration (servo firmware version, PSU voltage, servo count)
  - Calibration parameters (P/I/D values, protection settings)
  - Aggregate telemetry statistics (mean/std of temperature, load, voltage per servo per session)
  - Failure events (which failure mode, what settings were active)
  - Anomaly detection model performance (false positive rates)

NEVER SHARED:
  - Camera images (contain user's environment)
  - Precise motion trajectories (may reveal proprietary tasks)
  - User identity, location, IP address
  - Raw telemetry streams (too granular, privacy risk)
  - Dataset contents
```

### 3.3 Federated Learning Architecture

True federated learning (training on-device, sharing only gradients) is overkill for our use case. The data we're aggregating is small, structured, and non-sensitive. A simpler approach:

#### Phase 1: Centralized Aggregation (Simple, Effective)

```
armOS Instance                           armOS Cloud
+-------------------+                    +---------------------------+
| Compute local     |    HTTPS POST      | Aggregate across fleet    |
| statistics:       | -----------------> | Compute recommended       |
| - mean temps      |    opt-in only     |   settings per hardware   |
| - mean loads      |                    |   configuration           |
| - calibration     |                    |                           |
|   values used     |    HTTPS GET       | Serve recommendations:    |
| - failure events  | <----------------- | "For your hardware,       |
+-------------------+    on profile      |  P_Coefficient=18 is      |
                         install          |  better than default 16"  |
                                         +---------------------------+
```

Implementation: the telemetry system (architecture-enhancements.md Section 2) already collects this data locally. The cross-robot learning system adds a new opt-in transmission category: "calibration_insights."

#### Phase 2: Differential Privacy (When Fleet Grows)

When the fleet exceeds ~1,000 active instances, add differential privacy guarantees:

- **Mechanism:** Add calibrated Laplace noise to aggregate statistics before transmission
- **Privacy budget:** epsilon = 1.0 per metric per 24-hour window (standard for utility/privacy balance)
- **Implementation:** Use Google's `dp-accounting` library or OpenDP
- **Why wait:** Differential privacy reduces data utility. With <1,000 instances, the noise would overwhelm the signal. Start with simple aggregation + strict data minimization.

#### Phase 3: Federated Model Training (Future)

When we have enough fleet data, train a fleet-wide anomaly detection model without centralizing raw telemetry:

- Each instance trains a local isolation forest on its telemetry
- Instances share model parameters (tree structures), not data
- Central server aggregates parameters using federated averaging
- Updated global model is distributed to all instances

**Framework:** Flower (flwr.ai) -- the standard federated learning framework for Python. Supports scikit-learn models. Runs on CPU.

### 3.4 Recommendation Engine

```python
class FleetRecommendationEngine:
    """Generates hardware-specific recommendations from fleet data."""

    def get_recommendations(self, hardware_config: HardwareConfig) -> list[Recommendation]:
        """Given a hardware configuration, return recommendations:

        Example output:
        [
            Recommendation(
                setting="P_Coefficient",
                current_value=16,
                recommended_value=18,
                confidence=0.87,
                evidence="Based on 342 SO-101 arms with STS3215 v3.10 and 12V 5A supply. "
                         "Arms using P_Coefficient=18 show 23% less position oscillation "
                         "(p < 0.001, n=342).",
                source="fleet_aggregate_v2026.09",
            ),
            Recommendation(
                setting="Overload_Torque",
                current_value=80,
                recommended_value=90,
                confidence=0.92,
                evidence="Factory default of 80 causes protection trips during normal teleop "
                         "for 67% of users. Setting to 90 with adequate PSU (>= 5A) "
                         "eliminates trips with no increase in failure rate (n=518).",
                source="fleet_aggregate_v2026.09",
            ),
        ]
        """
```

Recommendations are displayed during `armos calibrate` and `armos diagnose`:

```
armos calibrate
...
FLEET INSIGHT: 342 similar arms use P_Coefficient=18 instead of the default 16.
This reduces position oscillation by 23%. Apply? [Y/n]
```

### 3.5 Implementation Phases

| Phase | Scope | Timeline | Dependency |
|-------|-------|----------|------------|
| 1 | Local calibration statistics computation | Month 20-22 | Telemetry DB |
| 2 | Opt-in aggregate upload to cloud | Month 22-24 | Telemetry transmission |
| 3 | Server-side aggregation + recommendation API | Month 24-26 | Cloud infrastructure |
| 4 | `armos calibrate` fleet recommendations | Month 26-28 | Recommendation API |
| 5 | Differential privacy layer | Month 30-32 | Fleet > 1,000 |
| 6 | Federated anomaly model training | Month 32-36 | Flower integration |

---

## 4. Sim-to-Real Pipeline

### 4.1 The Vision

Train manipulation policies in simulation (fast, safe, unlimited data), then transfer to the real SO-101. This collapses the data collection bottleneck: instead of 200 human demonstrations, generate 100,000 simulated demonstrations overnight on a cloud GPU.

### 4.2 Simulator Selection

| Simulator | License | CPU Performance | SO-101 Support | Rendering | Recommendation |
|-----------|---------|-----------------|---------------|-----------|----------------|
| PyBullet | MIT | 100-500 Hz (headless) | Manual URDF | OpenGL (basic) | **Local dev/test** |
| MuJoCo | Apache 2.0 | 1000-5000 Hz (headless) | Manual MJCF | OpenGL/EGL | **Primary (cloud training)** |
| Isaac Sim | Proprietary | GPU only | Built-in assets | RTX | Cloud only, best visual fidelity |
| Genesis | MIT | GPU preferred, CPU possible | Community URDF | Warp | Promising, immature |

**Decision:**
- **MuJoCo** as the primary simulator. It's free (Apache 2.0 since 2022), the fastest on CPU, and has the best contact physics for manipulation tasks. LeRobot already has MuJoCo integration (gym environments).
- **PyBullet** as the lightweight local option. Runs at 100-500 Hz on the i5, enough for visualization and basic policy testing (not training). Ships with armOS for the digital twin feature.
- **Isaac Sim** for users with NVIDIA hardware who want photorealistic domain randomization. Cloud training pipeline only.

### 4.3 SO-101 Simulation Model

Creating an accurate sim model requires:

1. **URDF/MJCF kinematics:** Joint limits, link lengths, masses from the SO-101 CAD files (available from HuggingFace). Already exists in the LeRobot community.
2. **Actuator model:** Map STS3215 servo behavior (PID response, torque limits, velocity limits) to simulator actuator parameters. This is the hard part -- requires system identification.
3. **Contact properties:** Friction, restitution for gripper-object interaction. Tune on real hardware.

```python
class SimModelBuilder:
    """Generates a simulator model from an armOS robot profile."""

    def build_mujoco_xml(self, profile: RobotProfile) -> str:
        """Convert armOS robot profile to MuJoCo XML.

        Maps:
        - Joint limits -> joint/range
        - Servo PID -> actuator/position gains
        - Max torque -> actuator/forcerange
        - Link masses -> body/inertial (from CAD or estimation)
        """

    def build_pybullet_urdf(self, profile: RobotProfile) -> str:
        """Convert armOS robot profile to URDF for PyBullet."""
```

### 4.4 Domain Randomization for Sim-to-Real Transfer

The gap between simulation and reality is the core challenge. Domain randomization bridges it by training on varied sim conditions:

| Parameter | Range | Why |
|-----------|-------|-----|
| Link masses | +/- 20% | 3D-printed parts vary |
| Joint friction | +/- 50% | Bearing quality varies |
| Actuator delay | 10-50ms | USB serial latency varies |
| Camera position | +/- 5cm, +/- 10 degrees | Camera mount is imprecise |
| Lighting | 50-500 lux, random direction | Environments vary |
| Object textures | Random from texture dataset | Generalization |
| Table height | +/- 5cm | Real tables vary |

### 4.5 Digital Twin (Real-Time 3D Visualization)

A digital twin renders the real arm's state in 3D, using live telemetry from the HAL.

**Technology:** rerun.io (already in architecture-enhancements.md Section 6). rerun supports 3D mesh rendering, joint transforms, and real-time streaming. The digital twin is a natural extension of the rerun export bridge.

```python
class DigitalTwin:
    """Real-time 3D visualization of arm state using rerun.io."""

    def __init__(self, profile: RobotProfile, urdf_path: Path):
        self._urdf = load_urdf(urdf_path)
        rr.init("armos_digital_twin")
        rr.serve()  # Start web viewer

    def update(self, joint_positions: dict[str, float]) -> None:
        """Called at 10Hz from telemetry stream.
        Updates joint transforms in the 3D scene."""
        for joint_name, position in joint_positions.items():
            transform = self._compute_fk(joint_name, position)
            rr.log(f"robot/{joint_name}", rr.Transform3D(transform))

    def overlay_target(self, target_positions: dict[str, float]) -> None:
        """Show ghost arm at target position (for motion planning viz)."""
```

**CPU feasibility:** rerun's 3D rendering requires a GPU for the viewer, but the *server* (running on armOS) only sends data -- the viewer runs on the user's browser or desktop app. The armOS i5 handles the data serialization at 10Hz with negligible CPU load.

### 4.6 Local vs Cloud Simulation

- **Local (PyBullet on i5):** 100-500 Hz headless. Enough for: policy testing (run 10 episodes in 30 seconds), digital twin visualization, basic debugging. NOT enough for training (need millions of steps).
- **Cloud (MuJoCo on GPU):** 5,000-50,000 Hz with parallelization. Required for: policy training, domain randomization sweeps, large-scale data generation.

The cloud training pipeline (architecture-enhancements.md Section 1) naturally extends to sim training:

```
armos sim train --task pick_place --episodes 100000 --upload
```

This packages the sim environment + task definition, uploads to cloud, trains, and downloads the policy. Same pipeline as real-data training, different data source.

### 4.7 Implementation Phases

| Phase | Scope | Timeline | Dependencies |
|-------|-------|----------|-------------|
| 1 | SO-101 URDF/MJCF model creation | Month 20-22 | Robot profile system |
| 2 | PyBullet local visualization + basic sim | Month 22-24 | URDF model |
| 3 | Digital twin via rerun.io | Month 24-26 | Rerun bridge, telemetry stream |
| 4 | MuJoCo cloud training integration | Month 26-30 | Cloud training pipeline |
| 5 | Domain randomization framework | Month 28-32 | MuJoCo integration |
| 6 | System identification (real servo -> sim actuator) | Month 30-34 | Telemetry data |

---

## 5. Vision-Language-Action Models

### 5.1 The Landscape (as of 2026)

VLA models unify perception and action: they take camera images + language instructions and directly output robot actions. This is the end game -- skip the separate perception/planning pipeline entirely.

| Model | Parameters | Size (Q4) | RAM (Q4) | CPU Latency | Open-Weight | Recommendation |
|-------|-----------|-----------|----------|-------------|-------------|----------------|
| RT-2 (Google) | 55B | N/A | N/A | Minutes | No | Cloud API only |
| Octo-Base | 93M | ~60 MB | ~200 MB | 200-500ms | **Yes** | **Best CPU candidate** |
| Octo-Small | 27M | ~20 MB | ~100 MB | 50-150ms | **Yes** | **Fastest, less capable** |
| OpenVLA | 7B | ~4 GB | ~6 GB | 30-60s | Yes | Too large for real-time on CPU |
| pi0 (Physical Intelligence) | 3B | ~2 GB | ~4 GB | 15-30s | Partial | Too large for real-time on CPU |
| RT-1 (Google) | 35M | ~25 MB | ~150 MB | 100-300ms | Yes | Good but task-specific |
| HPT (Kaiming He) | Various | Various | Various | Various | Yes | Research-stage |

### 5.2 The CPU-Realistic Path: Octo

Octo is the only production-quality VLA model that can run in real-time on CPU. Built by the Berkeley Robot Learning lab (same team that built the precursors to RT-2).

**Octo-Base on i5:**
- **Inference time:** 200-500ms per step (via ONNX Runtime with OpenVINO)
- **Control frequency:** 2-5 Hz (sufficient for manipulation tasks -- human teleop is typically 10-30 Hz, but policy inference can be slower with interpolation)
- **Memory:** ~200 MB
- **Input:** 256x256 image + language instruction + proprioceptive state (joint positions)
- **Output:** Delta joint positions (6-DOF)

**Integration with armOS:**

```python
class VLAInferenceEngine:
    """Runs Vision-Language-Action model inference."""

    def __init__(self, model_path: Path, backend: str = "onnx"):
        if backend == "onnx":
            self._session = ort.InferenceSession(
                str(model_path),
                providers=["OpenVINOExecutionProvider", "CPUExecutionProvider"],
            )
        elif backend == "pytorch":
            self._model = torch.load(model_path, weights_only=True)

    def predict(
        self,
        image: np.ndarray,          # 256x256x3 uint8
        instruction: str,            # "pick up the red block"
        joint_positions: np.ndarray, # current joint positions
    ) -> np.ndarray:
        """Returns delta joint positions for next timestep."""
```

### 5.3 LeRobot Integration Path

LeRobot v0.5.0 already supports ACT (Action Chunking Transformer) and Diffusion Policy. The path to VLA integration:

1. **LeRobot v0.6+ (expected 2026 H2):** Octo and OpenVLA support is on the LeRobot roadmap. When it lands, armOS gets it for free through the LeRobot bridge layer.

2. **Before LeRobot native support:** armOS can integrate Octo directly using the `octo` Python package (Apache 2.0 license). The bridge layer isolates this from the rest of the stack.

3. **Custom fine-tuning path:**
   ```
   [armOS data collection] -> [LeRobot dataset format] -> [Cloud training]
        |                                                        |
        | 50-200 human demonstrations                           | Fine-tune Octo-Base
        | of "pick up the red block"                             | on user's data
        |                                                        |
        +<---------- Download fine-tuned model ------------------+
        |
        v
   [armOS inference] -> [Octo-Base fine-tuned, 2-5 Hz on CPU]
   ```

### 5.4 The Training Data Question

VLA models need demonstration data paired with language instructions. armOS already collects demonstrations via teleop + `armos record`. The missing piece is language annotation:

```python
class AnnotatedRecording:
    """A teleop recording with language annotations."""

    episodes: list[Episode]           # From LeRobot recording
    task_description: str             # "Pick up the red block from the table"
    step_annotations: list[str]       # Optional per-step descriptions
    # "reaching toward the block", "closing gripper", "lifting"

    @classmethod
    def from_recording(cls, recording_dir: Path, task: str) -> "AnnotatedRecording":
        """User provides task description at recording time:
        armos record --task 'pick up the red block'
        """
```

This is a minimal change to the recording pipeline. Adding `--task` to `armos record` gives us language-annotated demonstration data that VLA models can train on.

### 5.5 What's Realistic on CPU

| Capability | CPU Feasible? | How |
|-----------|--------------|-----|
| Run pre-trained Octo-Small | Yes, 5-10 Hz | ONNX + OpenVINO |
| Run pre-trained Octo-Base | Yes, 2-5 Hz | ONNX + OpenVINO |
| Run fine-tuned Octo on user data | Yes, 2-5 Hz | Same as above |
| Run OpenVLA (7B) | No | Cloud inference or Jetson |
| Fine-tune Octo | No | Cloud GPU (A100, ~2 hours for 200 demos) |
| Fine-tune OpenVLA | No | Cloud GPU cluster |
| Real-time VLA + visual grounding | Borderline | 1-2 Hz total, may need to alternate |

### 5.6 Implementation Phases

| Phase | Scope | Timeline | Dependencies |
|-------|-------|----------|-------------|
| 1 | `--task` annotation for recordings | Month 22-24 | Recording pipeline |
| 2 | Octo-Small ONNX inference integration | Month 26-28 | ONNX Runtime, OpenVINO |
| 3 | Cloud fine-tuning pipeline for Octo | Month 28-30 | Cloud training pipeline |
| 4 | Octo-Base with action chunking | Month 30-32 | Octo Phase 2 |
| 5 | LeRobot native VLA support (when available) | Month 30+ | LeRobot upstream |
| 6 | Multi-task VLA with task embedding | Month 34-36 | Sufficient training data |

---

## 6. Autonomous Data Collection

### 6.1 The Vision

A robot that teaches itself through exploration. Instead of relying on 200 human demonstrations, the robot generates its own training data by interacting with objects and learning from outcomes. Like a baby reaching for objects and gradually learning to grasp.

### 6.2 Reality Check: What's Feasible on CPU

This is the hardest section to be honest about. Autonomous exploration requires:

1. A policy that generates exploratory actions (needs inference at 5+ Hz)
2. A reward signal (did I succeed?) -- typically from vision
3. Many thousands of episodes (hours to days of robot time)

On CPU-only hardware:

| Approach | CPU Feasible? | Episodes/hour | Time to Useful Policy |
|---------|--------------|---------------|----------------------|
| Random exploration + hindsight relabeling | Yes | 60-120 | 50-100 hours |
| Curiosity-driven (RND/ICM) | Borderline | 30-60 | 100+ hours |
| Goal-conditioned exploration | Borderline | 30-60 | 50-100 hours |
| Model-based exploration (world model) | No | N/A | Cloud training only |
| RL from scratch | No | N/A | Cloud sim only |

**The honest answer:** Autonomous data collection at training scale requires simulation. On real hardware with CPU-only inference, the episode rate is too slow for RL-style exploration. However, there are useful intermediate approaches.

### 6.3 Realistic Approaches

#### Approach 1: Scripted Exploration with Random Perturbation

No ML required. Generate diverse demonstrations by adding controlled randomness to scripted motions:

```python
class ScriptedExplorer:
    """Generates diverse demonstrations from scripted primitives."""

    def explore_pick_place(
        self,
        workspace_bounds: BoundingBox,
        n_episodes: int = 100,
        perturbation_std: float = 0.05,  # 5% noise in joint space
    ) -> list[Episode]:
        """For each episode:
        1. Move to random position in workspace
        2. Lower gripper with random approach angle (+/- 15 degrees)
        3. Close gripper at random height (exploring grasp points)
        4. Lift to random height
        5. Move to random place position
        6. Open gripper
        7. Record success/failure from visual change detection

        Adds Gaussian noise to all joint commands for diversity.
        """
```

This is not "learning" in the RL sense, but it generates diverse data that a supervised learning model (ACT, Diffusion Policy, Octo) can train on. A human doesn't need to demonstrate every variation -- the scripted explorer generates them.

**CPU requirements:** Minimal. Scripted motions + random noise + visual change detection (simple frame differencing). Runs at full servo control rate.

**Episodes per hour:** 60-120 (each episode is 30-60 seconds including reset).

**Practical use:** Generate 1,000 diverse grasping episodes overnight (16 hours) while the robot runs unattended. Upload to cloud, fine-tune Octo, download policy that generalizes to novel object positions.

#### Approach 2: Visual Outcome Detection (Reward Signal)

For autonomous learning, the robot needs to know if it succeeded. A lightweight visual reward:

```python
class VisualOutcomeDetector:
    """Determines task success from camera images."""

    def detect_pick_success(
        self,
        before_image: np.ndarray,
        after_image: np.ndarray,
        gripper_region: BoundingBox,
    ) -> bool:
        """Did the gripper pick up an object?

        Method: Compare before/after images in the gripper region.
        If significant pixel change in gripper area AND object missing
        from table region -> success.

        Implementation: OpenCV frame differencing + contour analysis.
        No ML model needed. ~5ms on CPU.
        """

    def detect_place_success(
        self,
        before_image: np.ndarray,
        after_image: np.ndarray,
        target_region: BoundingBox,
    ) -> bool:
        """Did the object land in the target region?
        Same frame-differencing approach.
        """
```

#### Approach 3: Curiosity-Driven Exploration (Borderline CPU)

Random Network Distillation (RND) provides an intrinsic reward for visiting novel states:

- **How:** A fixed random network and a trainable predictor network. States where the predictor disagrees with the random network are "novel."
- **Size:** Two small MLPs (~100KB each)
- **Inference:** <1ms on CPU
- **Training:** Update predictor every episode (~10ms)
- **Memory:** <50 MB

The bottleneck is not the curiosity model but the *policy* that acts on the curiosity reward. If using a small policy (MLP or small transformer), this can run at 5-10 Hz on CPU.

**Realistic assessment:** Curiosity-driven exploration on real hardware is slow (30-60 episodes/hour). It would take 50-100 hours to collect enough data for a meaningful policy. This is a "start Friday evening, check Monday morning" workflow. Possible, not practical for interactive use.

#### Approach 4: Human-in-the-Loop Exploration

The most practical path: combine human demonstrations with autonomous exploration.

```
Phase 1: Human provides 10-20 demonstrations of the task
Phase 2: Train initial policy (cloud, 30 minutes)
Phase 3: Robot executes policy autonomously, human corrects failures
Phase 4: Add corrected episodes to dataset, retrain
Phase 5: Repeat until policy success rate > 90%
```

This is DAgger (Dataset Aggregation) -- a well-studied approach that converges much faster than pure exploration. The human provides the hard parts (initial grasps, tricky orientations), the robot fills in the easy variations.

**CPU requirements:** Policy inference at 2-5 Hz (Octo-Small) + visual success detection. Fully feasible on i5.

### 6.4 The Overnight Autonomous Collection Workflow

The killer feature for armOS: set up a task, start autonomous collection, go to sleep.

```bash
# User sets up the workspace and defines the task
armos collect --task "pick up object from zone A, place in zone B" \
              --workspace-image setup.jpg \
              --episodes 500 \
              --reset-mode manual-first-then-script \
              --overnight

# armOS:
# 1. Records user performing 5 reset demonstrations
# 2. Learns a reset policy (move arm to home, wait for human to reposition object)
# 3. For each episode:
#    a. Execute exploration (scripted + perturbation, or policy-based)
#    b. Detect success/failure via visual outcome
#    c. Execute reset motion
#    d. If reset fails (object stuck), pause and alert (optional)
# 4. In the morning: "347/500 episodes collected. 231 successful. Ready to upload."
```

### 6.5 Implementation Phases

| Phase | Scope | Timeline | Dependencies |
|-------|-------|----------|-------------|
| 1 | Scripted exploration primitives (move, grasp, place) | Month 24-26 | Motion planner, HAL |
| 2 | Visual outcome detection (frame differencing) | Month 26-28 | Camera pipeline |
| 3 | Overnight collection workflow (`armos collect`) | Month 28-30 | Phases 1+2, safety governor |
| 4 | DAgger human-in-the-loop correction | Month 30-32 | Policy inference, Phase 3 |
| 5 | RND curiosity reward (experimental) | Month 32-34 | Phase 3 |
| 6 | Learned reset policies | Month 34-36 | Sufficient reset demonstrations |

---

## 7. Hardware Constraints Reference

Everything in this document is designed for the following baseline hardware. This section is the reality check.

### 7.1 Target Hardware: Intel i5-1035G4 (Surface Pro 7 class)

| Resource | Available | Notes |
|----------|-----------|-------|
| CPU | 4 cores / 8 threads, 1.1-3.7 GHz | AVX2, no AVX-512 |
| RAM | 8 GB (some models 16 GB) | ~5 GB available after OS + armOS core |
| GPU | Intel Iris Plus G4 (integrated) | OpenCL 2.0, ~1 TFLOPS FP32. Usable for OpenVINO but NOT for PyTorch CUDA |
| Storage | USB 3.1 Gen 1 (5 Gbps) | Model loading speed limited by USB |
| USB ports | 1x USB-A, 1x USB-C | Shared with servo controller + cameras |
| Network | WiFi 6 (AX201) | For cloud API calls |
| Power | 15W TDP sustained | Throttles under sustained load |

### 7.2 Memory Budget for AI Workloads

With 8 GB total RAM and ~5 GB available:

```
Base armOS + Python + HAL:           ~500 MB
LeRobot + PyTorch (CPU):             ~800 MB
Camera pipeline (2 cameras):          ~200 MB
Telemetry + SQLite:                   ~100 MB
────────────────────────────────────────────
Subtotal (always running):          ~1,600 MB
Available for AI models:            ~3,400 MB

Model allocations (pick ONE active at a time):
  Whisper tiny (whisper.cpp):          200 MB
  YOLO-World-S (ONNX):                600 MB
  Isolation forest (scikit-learn):     100 MB
  TinyLlama 1.1B Q4 (llama.cpp):    1,500 MB
  Octo-Small (ONNX):                  100 MB
  Octo-Base (ONNX):                   200 MB

Maximum simultaneous:
  YOLO-World + Octo-Base + Whisper = ~1,000 MB  (fits)
  YOLO-World + TinyLlama + Whisper = ~2,300 MB  (fits, tight)
  All models loaded simultaneously   = ~2,700 MB  (fits in 3,400 MB)
```

**Key insight:** On 8 GB RAM, we can run the full agent pipeline (speech + vision + VLA + anomaly detection) simultaneously, but not with a large language model. TinyLlama 1.1B can run, but it must be loaded on-demand and unloaded after use.

On 16 GB RAM (Surface Pro 7 i7 models), there's headroom for everything including a 3B parameter model.

### 7.3 Inference Acceleration on Intel

The Intel Iris Plus G4 integrated GPU is underutilized by default. OpenVINO can leverage it:

| Runtime | Device | YOLO-World-S Latency | Octo-Base Latency |
|---------|--------|---------------------|-------------------|
| PyTorch (CPU) | CPU only | 400-800ms | 800-1500ms |
| ONNX Runtime (CPU) | CPU only | 200-400ms | 300-600ms |
| ONNX + OpenVINO | CPU + iGPU | **100-200ms** | **150-350ms** |
| whisper.cpp | CPU (AVX2) | 150-300ms/5s audio | N/A |

**OpenVINO is the single most important optimization for CPU-only hardware.** It's the difference between 1 Hz and 5 Hz inference, which is the difference between "useless" and "usable."

Installation: `pip install openvino-runtime` (~50 MB). Already in the architecture as an optional inference backend (architecture-enhancements.md Section 5.4).

### 7.4 Thermal Considerations

The Surface Pro 7 throttles under sustained CPU load. Fan-less design means:

- Sustained all-core load: CPU drops from 3.7 GHz to ~2.0-2.5 GHz after 30-60 seconds
- Impact on inference: latencies increase ~50% under sustained load
- Mitigation: interleave inference with I/O (servo communication, camera capture). The CPU idle time during USB transfers provides thermal recovery.

The agent pipeline naturally interleaves: servo command (5ms USB) -> camera capture (33ms) -> inference (200ms) -> servo command. The CPU never sustains 100% utilization.

---

## 8. Implementation Phasing

### 8.1 Master Timeline

```
Month 18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35  36
       |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
       |                                                                     |
AGENT  |==1a: Rule cmds==|                                                  |
       |        |==1b: Cloud LLM + YOLO==|                                  |
       |                  |===1c: Whisper STT===|                            |
       |                            |===2: Local SLM===|                     |
       |                                      |===3: Closed-loop===|        |
       |                                                     |==4: Fine-tune=|
       |                                                                     |
DIAG   |=1: Rules=|                                                          |
       |    |=2: Stats=|                                                     |
       |         |==3: IsoForest==|                                          |
       |                  |==4: LLM reports==|                               |
       |                           |==5: Autoencoder=|                       |
       |                                    |==6: Prediction==|              |
       |                                              |=7: Local SLM=|      |
       |                                                                     |
FLEET  |         |==1: Local stats==|                                        |
       |                  |==2: Aggregate upload==|                          |
       |                           |==3: Server aggregation==|              |
       |                                    |==4: Recommendations==|        |
       |                                                   |=5: DP layer=|  |
       |                                                          |=6: Fed=||
       |                                                                     |
SIM    |         |==1: URDF/MJCF==|                                          |
       |                  |==2: PyBullet local==|                            |
       |                           |==3: Digital twin==|                     |
       |                                    |====4: MuJoCo cloud====|       |
       |                                         |===5: Domain rand===|     |
       |                                                   |=6: SysID=|     |
       |                                                                     |
VLA    |                  |=1: Task annotation=|                             |
       |                                    |=2: Octo-Small ONNX=|          |
       |                                         |=3: Cloud fine-tune=|     |
       |                                                   |=4: Octo-Base=| |
       |                                                                     |
DATA   |                           |=1: Scripted explore=|                  |
       |                                    |=2: Visual outcome=|            |
       |                                         |=3: Overnight collect=|   |
       |                                                   |=4: DAgger=|    |
       |                                                          |=5: RND=||
```

### 8.2 Critical Path

The critical path runs through:

1. **OpenVINO + ONNX Runtime integration** (Month 18-20) -- Everything depends on this for acceptable CPU inference speed.
2. **YOLO-World ONNX export** (Month 20-22) -- Visual grounding unlocks the embodied agent, VLA evaluation, and visual outcome detection.
3. **Cloud LLM integration** (Month 20-22) -- Intent parsing and diagnosis reports.
4. **Octo ONNX integration** (Month 26-28) -- The first end-to-end VLA on CPU.

### 8.3 Resource Requirements per Phase

| Phase | Engineering Effort | Cloud Cost | New Dependencies |
|-------|-------------------|-----------|-----------------|
| Agent Phase 1a | 2 person-weeks | $0 | ikpy |
| Agent Phase 1b | 4 person-weeks | ~$50/mo (API) | onnxruntime, openvino |
| Agent Phase 1c | 2 person-weeks | $0 | whisper.cpp (C binding) |
| Diagnostic Phase 1-3 | 3 person-weeks | $0 | scikit-learn |
| Diagnostic Phase 4 | 2 person-weeks | ~$20/mo (API) | None new |
| Fleet Phase 1-2 | 3 person-weeks | $0 | None new |
| Fleet Phase 3-4 | 4 person-weeks | ~$100/mo (server) | DuckDB (server) |
| Sim Phase 1-2 | 4 person-weeks | $0 | mujoco, pybullet |
| Sim Phase 3 | 2 person-weeks | $0 | rerun-sdk |
| VLA Phase 2 | 3 person-weeks | $0 | octo (Python pkg) |
| Data Phase 1-3 | 4 person-weeks | $0 | None new |

---

## 9. ADRs

### ADR-13: Inference Runtime Strategy

**Status:** Proposed
**Context:** All AI models in the intelligence layer must run on Intel i5 CPUs without discrete GPUs.
**Decision:** ONNX Runtime with OpenVINO Execution Provider as the primary inference runtime. whisper.cpp for speech-to-text. llama.cpp for local language models. PyTorch as fallback only.
**Rationale:** ONNX Runtime + OpenVINO delivers 2-5x speedup over raw PyTorch on Intel CPUs by leveraging AVX2 and the integrated GPU. whisper.cpp and llama.cpp are purpose-built for CPU inference and consistently outperform their Python/PyTorch equivalents. The three runtimes cover all model types (vision, language, VLA) without pulling in CUDA dependencies.
**Consequences:** Every model must be exportable to ONNX. Models that resist ONNX export (rare but possible with dynamic architectures) fall back to PyTorch CPU. The build pipeline must include ONNX export and validation steps.

### ADR-14: Embodied Agent Safety Architecture

**Status:** Proposed
**Context:** Natural language robot control means the AI agent generates servo commands. Misinterpretation or hallucination could cause dangerous motions.
**Decision:** A SafetyGovernor operates at the HAL level, below the AI agent. It validates every trajectory against joint limits, velocity limits, torque limits, and workspace bounds. The agent cannot bypass it. Emergency stop is triggered by voice command, safety violation, or watchdog timeout.
**Rationale:** Defense in depth. The AI agent is treated as untrusted input to the servo system, just like a network packet is untrusted input to a firewall. The safety governor is small, auditable, and deterministic -- no ML in the safety path.
**Consequences:** Adds ~50ms latency to every servo command (safety validation). Acceptable. May reject valid-but-aggressive motions; users can adjust workspace bounds and velocity limits in the robot profile.

### ADR-15: Anomaly Detection Model Selection

**Status:** Proposed
**Context:** Servo telemetry anomaly detection must run continuously on CPU without impacting teleop performance.
**Decision:** Isolation Forest (scikit-learn) per-servo for univariate anomalies. Tiny autoencoder (ONNX) for cross-servo correlations. Both run on a background thread at 1 Hz (subsampled from 10 Hz telemetry).
**Rationale:** Isolation Forest is the best-studied unsupervised anomaly detection algorithm for tabular data. It requires no hyperparameter tuning (contamination=0.01 is robust), trains in seconds, and predicts in microseconds. The autoencoder adds multi-variate correlation detection at minimal cost. Running at 1 Hz instead of 10 Hz reduces CPU load by 90% with negligible detection delay.
**Consequences:** Anomaly detection has ~1 second latency (1 Hz sampling). This is acceptable for trend-based anomalies (temperature, bearing wear) but would miss instantaneous spikes. The rule-based threshold layer (Layer 1) runs at 10 Hz to catch spikes.

### ADR-16: Cross-Robot Learning Privacy Strategy

**Status:** Proposed
**Context:** Fleet data aggregation provides significant value but raises privacy concerns.
**Decision:** Three-phase approach: (1) strict opt-in with data minimization (aggregates only, no raw telemetry), (2) differential privacy when fleet exceeds 1,000 instances, (3) federated learning for model training when fleet exceeds 5,000 instances.
**Rationale:** Privacy protection should scale with the privacy risk. With <1,000 instances, the data is too sparse for de-anonymization attacks, and differential privacy noise would destroy utility. Data minimization (sharing only means/stds, never raw streams) provides adequate protection at small scale. As the fleet grows, add formal privacy guarantees.
**Consequences:** Fleet recommendations are less accurate at small fleet sizes. Acceptable -- the alternative (no fleet learning) provides zero value. The progression from aggregation to DP to federated learning is a natural maturation path.

### ADR-17: Simulation Strategy

**Status:** Proposed
**Context:** Sim-to-real is essential for data-efficient learning but simulators are heavy.
**Decision:** PyBullet for local visualization and basic testing. MuJoCo for cloud training. No simulator bundled in the USB ISO by default -- installed on demand via `armos sim install`.
**Rationale:** PyBullet is MIT-licensed, pip-installable, and runs headless on CPU at 100-500 Hz. MuJoCo is faster and more accurate but heavier. Bundling either in the ISO adds 50-200 MB and is only needed by users doing sim-to-real (a minority in Horizon 3's early phases). On-demand installation keeps the ISO lean.
**Consequences:** Users must run `armos sim install` before using simulation features. This adds a one-time setup step but saves 200 MB for users who never use simulation.

---

## Closing Notes

### What's Realistic vs What's Aspirational

**Realistic on CPU in 18-36 months (high confidence):**
- Rule-based + cloud LLM intent parsing for natural language commands
- YOLO-World open-vocabulary object detection at 5-10 Hz
- Whisper tiny voice commands at <300ms latency
- Isolation forest anomaly detection running continuously
- Fleet-wide calibration recommendations from aggregated data
- PyBullet digital twin visualization
- Scripted autonomous data collection overnight
- Octo-Small VLA inference at 5-10 Hz

**Feasible but pushing limits (medium confidence):**
- TinyLlama 1.1B for offline intent parsing (works, but quality is marginal)
- Octo-Base VLA at 2-5 Hz with OpenVINO (depends on model architecture supporting ONNX export cleanly)
- DAgger human-in-the-loop policy improvement (workflow complexity, not compute, is the bottleneck)
- Federated anomaly model training (requires large fleet)

**Aspirational / requires cloud or better hardware (low confidence on CPU):**
- OpenVLA or pi0 real-time inference on CPU (too large)
- Model-based exploration / world models (too compute-intensive)
- Photorealistic sim-to-real with Isaac Sim (GPU-only)
- Fine-tuning any model locally (GPU required)
- Curiosity-driven exploration converging to useful policies on real hardware in reasonable time

### The Core Bet

armOS's intelligence layer bets on three things:

1. **Small models get better fast.** Octo-Small in 2026 is roughly where GPT-3 was in 2020. In 2-3 years, a 100M parameter VLA will match today's 7B models. CPU inference becomes increasingly viable.

2. **The cloud/edge split is the right architecture.** Heavy training in the cloud, fast inference on the edge. This is how phones work (Siri processes locally, trains in the cloud). It will be how robots work.

3. **Fleet data is the moat.** Any single user can set up Octo. But only armOS has calibration data from 10,000 arms, failure patterns from 50,000 hours of operation, and optimal settings validated across the fleet. That data compounds and cannot be replicated by a competitor launching today.

---

*Frontier AI Intelligence Roadmap for armOS -- Winston (Architect) + Amelia (Developer)*
