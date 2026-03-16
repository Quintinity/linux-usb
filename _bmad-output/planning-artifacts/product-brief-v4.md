---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - citizenry/SOUL.md
  - citizenry/RESEARCH-robot-memory.md
  - citizenry/RESEARCH-reflexes.md
  - citizenry/RESEARCH-pain-proprioception-sleep.md
  - citizenry/RESEARCH-spatial-awareness.md
  - citizenry/GROWTH.md
  - docs/research-robot-metabolism.md
date: 2026-03-16
author: Bradley
---

# Product Brief: armOS v4.0 — "The Living Machine"

## Vision

armOS v3.0 gave the citizenry a brain (governance), nerves (protocol), DNA (genome), and immune system (fault patterns). **v4.0 makes it alive.** Each citizen becomes a living entity with a soul (identity and purpose), memory (experiences and knowledge), reflexes (instant reactions), pain (avoidance learning), spatial awareness (physical self-knowledge), metabolism (energy management), growth (developmental maturity), and sleep (maintenance cycles). The system doesn't just collaborate — it **lives, learns, adapts, and evolves.**

The biological metaphor is not decorative. It is the architecture. Every subsystem solves a real engineering problem:

| Engineering Problem | Biological Solution | armOS Module |
|---|---|---|
| How does a robot develop preferences? | **Soul** — personality, purpose, values | `soul.py` |
| How does it remember what happened? | **Memory** — episodic, semantic, procedural | `memory.py` |
| How does it get better at tasks? | **Self-Improvement** — meta-learning, strategy evolution | `improvement.py` |
| How does it react instantly to danger? | **Reflexes** — 100Hz stimulus→response | `reflex.py` |
| How does it manage limited power? | **Metabolism** — energy budgeting, brownout protection | `metabolism.py` |
| How does it learn from damage? | **Pain** — avoidance zones, motivational damage signal | `pain.py` |
| How does it know where its body is? | **Proprioception** — FK body model, force estimation | `proprioception.py` |
| How does it maintain itself? | **Sleep** — memory consolidation, calibration, cleanup | `sleep.py` |
| How does it mature over time? | **Growth** — developmental stages, earned autonomy | `growth.py` |
| How do multiple arms avoid collision? | **Spatial Awareness** — flight plans, zone management | `spatial.py` |

## What Already Exists

armOS v3.0 is complete: 30+ citizenry modules, HAL with Feetech + Dynamixel drivers, auto-detection, wizard, web dashboard, NL governance, 297 tests. Running on real hardware (Surface Pro 7 + Pi 5 + SO-101 arms + DJI Osmo Action 4 camera).

## What v4.0 Adds (8 New Biological Subsystems)

### 1. Soul (soul.py)
- **PersonalityProfile**: Big Five (OCEAN) dimensions + armOS traits (movement_style, exploration_drive)
- **GoalHierarchy**: 5 priority tiers (SURVIVAL → CURIOSITY). Idle citizens self-generate practice goals.
- **BehavioralPreferences**: Learned movement style (smooth vs fast), per-task success rates by approach
- **Values**: Constitutional articles (immutable) + governor norms (adjustable) + self-learned values (trust, caution)
- **Identity continuity**: Private key = soul. Hardware swap = life event. Cloning genome = child, not resurrection.

### 2. Memory (memory.py)
- **EpisodicMemory**: What-Where-When-Outcome tuples. Importance-weighted retention. Forgetting curves.
- **SemanticMemory**: JSON property graph. Object properties, spatial relations, causal models. "Red blocks are usually on the left table."
- **ProceduralMemory**: Parameter recipes per skill per context. "Best grasp for cups: approach from right at 30 degrees."
- **Consolidation**: During sleep — episodes → semantic knowledge + procedural refinements.
- **Fleet sharing**: KNOWLEDGE_GOSSIP via existing protocol. Citizens share learned facts.

### 3. Self-Improvement (improvement.py)
- **PerformanceTracker**: Sliding window success rate per skill. Trend detection. Regression alerts.
- **StrategySelector**: UCB1 bandit per task type. Explores approaches, exploits best ones.
- **ParameterEvolution**: CMA-ES for continuous skill parameters (approach speed, grip force).
- **FailureAnalysis**: Telemetry diff at failure time → hypothesis → corrective action.
- **PracticeMode**: Idle citizens generate practice goals from learning-progress heuristic.

### 4. Reflexes (reflex.py)
- **ReflexEngine**: 100Hz telemetry loop, declarative condition→action rules, priority-based arbitration.
- **Hardcoded reflexes**: Overcurrent → reduce velocity. Voltage collapse → disable torque. Thermal → slow down.
- **Derivative triggers**: Rate-of-change detection for collision sensing.
- **Distributed sympathy**: Arm-1 reflex → Arm-2 in same workspace slows down via mycelium.
- **Immune integration**: Repeated reflexes become learned fault patterns.

### 5. Metabolism (metabolism.py)
- **MetabolicState**: Idle/resting/active/peak power tracking from voltage × current.
- **BrownoutProtocol**: 4-stage voltage threshold protection (normal → caution → critical → emergency).
- **PowerLedger**: Multi-citizen PSU-aware admission control. Tasks include power requirements.
- **DutyCycleTracker**: Servo wear estimation, thermal cycling stress, lifetime counters in genome.
- **Power-aware bidding**: Power becomes a marketplace dimension. Can't power it? Don't bid.

### 6. Pain + Proprioception (pain.py, proprioception.py)
- **PainEvents**: Intensity-scaled damage signals. 5 behavioral levels (discomfort → emergency).
- **AvoidanceZones**: Spatial regions in joint space to avoid. Radius proportional to pain intensity. Decay over time.
- **ReferredPain**: Compensatory stress detection across adjacent joints.
- **ForwardKinematics**: DH parameters → Cartesian coordinates. Joint limit proximity. Force estimation from current.
- **BodySchema**: Integrated body model. "My gripper is 15cm forward, elbow near limit."

### 7. Sleep (sleep.py)
- **4-phase cycle**: DROWSY → LIGHT_SLEEP (memory consolidation) → DEEP_SLEEP (maintenance) → REM (dream replay).
- **Sleep pressure**: Computed from uptime, fatigue, unconsolidated episodes, time since last sleep.
- **Wake thresholds**: Emergency always wakes. Critical wakes from light sleep only.
- **Consolidation work**: Episodes → semantic knowledge. Immune pruning. Calibration checks. Genome optimization.
- **Dream replay**: Prioritized replay of surprising episodes. Procedural reinforcement.

### 8. Spatial Awareness (spatial.py)
- **CapsuleCollision**: Each arm link = capsule (line + radius). 25 distance checks for 2 arms. <10μs per check.
- **ZoneArchitecture**: Exclusive zones, shared zones (mutex via PROPOSE/ACCEPT), forbidden zones.
- **FlightPlans**: Before moving into shared space, broadcast trajectory envelope. Conflicts → yield by priority.
- **ObjectHandoff**: 4-phase staged sequence (negotiate → approach → transfer → retreat).
- **Camera verification**: Camera confirms arm positions match FK calculations.

### 9. Growth (growth.py)
- **6 developmental stages**: NEWBORN → INFANT → JUVENILE → ADULT → EXPERT → ELDER.
- **Earned autonomy per-skill**: Teleop-only → supervised → assisted → autonomous → self-governing.
- **Multi-factor gates**: XP + success rate + peer endorsement + governor certification.
- **Emergent specialization**: Track performance per task type, natural divergence over time.
- **Regression detection**: EWMA monitoring, automatic demotion on degradation.

## Target Users
Same as v2.0/v3.0 — hobbyists, researchers, educators, makers. v4.0 makes the system feel **alive** to users: robots that develop personality, learn from mistakes, avoid repeating painful experiences, rest when tired, and grow more capable over time.

## Constraints
- Pure Python, no GPU (all runs on Surface Pro 7 Intel + Pi 5 ARM)
- No new protocol messages (still 7 types — new data in message bodies)
- No new external dependencies beyond numpy and optionally `cma` for CMA-ES
- Must not break v3.0 backward compatibility
- 100Hz reflex loop must not block the asyncio event loop

## Success Metrics
| Metric | Target |
|--------|--------|
| Reflex response time | < 10ms from trigger to action |
| Self-collision prevention | 100% (never self-collide) |
| Multi-arm collision prevention | 100% in shared zones |
| Pain avoidance learning | Avoid repeated fault within 3 occurrences |
| Sleep consolidation | Memory reduced 50%+ while retaining key knowledge |
| Growth progression | Citizen reaches ADULT stage within 500 tasks |
| Strategy improvement | 10%+ success rate gain via CMA-ES after 50 evaluations |
| Personality stability | Big Five drift < 0.1 per 100 tasks |
