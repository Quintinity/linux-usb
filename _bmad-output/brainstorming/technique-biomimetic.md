# Biomimetic: Nature's Solutions for Distributed Robot Citizenry

*Brainstorming technique: Study how nature solves distributed coordination and apply it to autonomous robot agents.*

*Context: Each device (SO-101 arms, Surface Pro, Pi, phones, sensors) is an autonomous "citizen" that discovers neighbors, shares capabilities, and collaborates -- without centralized micromanagement.*

---

## 1. Ant Colony: Stigmergic Coordination

### Idea 1: Digital Pheromone DHT for Capability Scoring

Each robot publishes a capability-weighted score to a shared distributed hash table (DHT) that decays over time, exactly like evaporating pheromones. A robot that just successfully completed a pick-and-place task publishes `{"skill": "pick_place", "confidence": 0.87, "ttl": 3600}`. Other robots querying "who can pick and place?" find this entry and route tasks accordingly. Scores decay -- if the robot goes offline or stops performing, its pheromone evaporates and tasks route elsewhere.

*Research basis: [Automatic design of stigmergy-based behaviours for robot swarms](https://www.nature.com/articles/s44172-024-00175-7) -- Salman et al. 2024 demonstrated automatic design of stigmergy-based collective behaviors through simulation and real-robot experiments.*

### Idea 2: Motion Trail Publishing

When a follower arm executes a trajectory, it publishes the full joint-space path as a "trail" to a shared store (Redis, MQTT retained messages, or a lightweight DHT). Other arms executing similar tasks discover these trails and use them as warm-start priors for their own motion planning -- like ants following pheromone trails to food. Trails that lead to successful task completion get "reinforced" (higher weight); trails that cause collisions or protection faults get "anti-pheromone" markers.

### Idea 3: Task Recruitment via Trail Strength

When the Surface Pro needs an arm to collect training data, it doesn't assign one directly. Instead, it publishes a "food source" (task descriptor) to the mesh. Arms that are idle and have matching capabilities detect the gradient and "walk toward" the task -- the strongest pheromone trail (best-matched, closest, most-idle arm) wins. No central scheduler needed.

### Idea 4: Exploration vs. Exploitation Pheromone Balance

Ants balance exploring new food sources vs. exploiting known ones. Robot agents should similarly balance: 80% of the time follow established "trails" (known-good policies, calibrated routines), 20% of the time explore (try new trajectories, test edge cases). The exploration rate adapts based on swarm success -- if task success rate drops, exploration rate increases (the colony is "hungry").

---

## 2. Bee Hive: Capability Advertisement via Waggle Dance

### Idea 5: Capability Waggle Dance Protocol

When a new device joins the mesh, it performs a "waggle dance" -- a structured mDNS/UDP broadcast announcing:
```json
{
  "citizen_id": "so101-follower-alpha",
  "type": "manipulator",
  "capabilities": ["6dof_arm", "gripper", "feetech_sts3215"],
  "sensors": ["joint_position", "joint_velocity", "load_current", "temperature"],
  "power_state": {"voltage": 12.0, "current_capacity_amps": 5.0},
  "health": 0.95,
  "available": true
}
```
Every citizen on the network listens for waggle dances and maintains a local neighbor table. No central registry.

*Research basis: [Bio-inspired artificial pheromone system for swarm robotics applications](https://journals.sagepub.com/doi/full/10.1177/1059712320918936) -- Na et al. demonstrated the COS-phi system for low-cost pheromonal communication.*

### Idea 6: Scout Bee Exploration Agents

Dedicated lightweight "scout" processes run on each device, periodically probing the network for new citizens, dead citizens, or changed capabilities. When a scout discovers something interesting (a new camera plugged into a USB hub, a servo that came back online after a fault), it returns to its home device and performs a waggle dance to announce the finding. Scouts that discover high-value information (e.g., "the 12V 5A PSU is now connected and voltage is stable at 12.0V") trigger swarm-wide announcements.

### Idea 7: Quorum Sensing for Task Commitment

Bees use quorum sensing to decide when enough scouts have confirmed a new nest site. Robot citizens should do the same for critical operations: before starting a multi-arm teleoperation session, require a quorum -- both arms healthy, camera streaming, PSU voltage above threshold, all calibration files present. No single device decides "go" -- the swarm reaches consensus.

### Idea 8: Division of Labor via Response Thresholds

In bee colonies, individuals have varying response thresholds to stimuli -- some bees respond to low-level signals while others only respond to intense ones. Robot citizens can implement variable response thresholds: a lightly-loaded arm responds to any task request, while a heavily-loaded arm (e.g., elbow at 80% load) only responds to high-priority requests. Thresholds adapt over time based on the agent's history and the swarm's needs.

---

## 3. Mycelium Network: The Underground Warning System

### Idea 9: Telemetry Warning Propagation Network

Directly inspired by the mycorrhizal "wood wide web" where trees share nutrient warnings through fungal networks. When a servo detects overheating (temp > 60C), voltage collapse (12V dropping to 5V -- the exact PSU current-limit scenario documented in the servo tuning notes), or overload protection tripping (the elbow_flex problem at >80% load for >2s), it publishes a warning to the mesh:
```json
{
  "warning_type": "voltage_collapse",
  "source": "so101-follower/elbow_flex",
  "severity": "critical",
  "data": {"voltage_before": 12.0, "voltage_after": 5.0, "load_percent": 100},
  "recommended_action": "reduce_torque_all_joints",
  "ttl": 300
}
```
Other devices on the mesh receive this and adapt: the leader arm slows its teleoperation speed, the Surface Pro logs the event for later analysis, nearby arms avoid the motion pattern that caused the collapse.

*Research basis: [Mycelium AI coordination layer](https://mycelium.fyi/) -- Mycelium.fyi implements exactly this pattern for AI agent networks: tasks, plans, messaging, and approval gates.*

### Idea 10: Nutrient Sharing (Compute/Power Resource Distribution)

Mycelium networks redistribute nutrients from resource-rich trees to resource-poor ones. In the robot mesh: the Surface Pro (Intel i5, 8GB RAM) has compute but no motors. The SO-101 arms have motors but no compute. The Pi has low compute but excellent GPIO. Implement a resource-sharing protocol where devices advertise surplus resources and request deficit ones. The Surface Pro offers inference cycles; the arms offer physical manipulation; the Pi offers sensor I/O.

### Idea 11: Mycelial Memory -- Distributed Experience Store

Mycelium networks can "remember" paths to nutrient sources. Implement a distributed experience replay buffer spread across all devices on the mesh. Each robot stores its recent episodes locally; when any device needs training data, it queries the mycelium and gets episodes from across the swarm. Devices that share high-value episodes (novel situations, edge cases, recovery from faults) get priority when requesting resources back -- a reciprocal exchange like real mycorrhizal networks.

### Idea 12: Slow Warning vs. Fast Warning Channels

Mycelium networks operate on slow timescales (hours/days) compared to chemical signals (seconds). Implement two warning channels: a fast channel (sub-100ms, UDP multicast) for urgent warnings ("servo protection tripped, stop moving NOW") and a slow channel (MQTT retained messages, checked every few seconds) for trends ("elbow load has been trending upward over the last 10 minutes, consider recalibrating").

---

## 4. Slime Mold: Emergent Intelligence from Simple Rules

### Idea 13: Physarum Path Optimization for Multi-Arm Coordination

Slime mold (Physarum polycephalum) solves shortest-path problems without a brain by growing toward food sources and pruning inefficient connections. Apply this to multi-arm task planning: when multiple arms need to collaborate on a task, each arm "grows" toward the task by proposing trajectories. Trajectories that conflict (collision risk) get pruned. Trajectories that complement each other (one arm holds, the other manipulates) get reinforced. The result is an emergent coordination plan with no central planner.

*Research basis: [Slime Mould Metaheuristic for optimization and robot path planning](https://www.sciencedirect.com/science/article/pii/S0925231225012238) -- recent 2025 work on SMA for robot path planning.*

### Idea 14: Three Simple Rules for Collective Intelligence

Inspired by how slime mold operates on minimal rules to produce complex behavior:
1. **Attract**: Move toward tasks that match your capabilities (weighted by confidence score)
2. **Repel**: Move away from configurations that caused faults (anti-pheromone)
3. **Flow**: Share state with immediate neighbors, let information propagate naturally

These three rules, applied locally by each citizen, produce globally intelligent behavior -- task allocation, fault avoidance, and information sharing -- without any central controller.

### Idea 15: Network Topology Pruning via Usage

Slime mold grows extensive networks then prunes unused paths. The robot mesh should do the same: initially, every device connects to every other device. Over time, connections that carry useful data (telemetry, commands, shared episodes) get strengthened (higher bandwidth allocation, lower latency priority). Connections that carry nothing get pruned. The result is an organically optimized network topology.

### Idea 16: Adaptive Exploration via Levy Flights

When slime mold explores, it uses patterns resembling Levy flights -- mostly short moves with occasional long jumps. Robot agents exploring new capabilities should do the same: mostly make small adjustments to known-good policies (fine-tuning joint angles by 1-2 degrees), but occasionally make large jumps (trying a completely different grasp strategy). The ratio of short-to-long moves adapts based on recent success rates.

*Research basis: [Enhanced slime mold algorithm with Levy flight for robot path planning](https://pmc.ncbi.nlm.nih.gov/articles/PMC10616528/) -- LRSMA algorithm demonstrated on autonomous mobile robots.*

---

## 5. Flocking Behavior (Boids): Three Rules for Robot Agents

### Idea 17: The Three Laws of Robot Flocking

Adapted from Reynolds' 1987 boid rules:
1. **Separation**: No two robot arms should attempt the same task simultaneously. If two arms detect the same task, the one with lower capability score yields. Prevents resource contention.
2. **Alignment**: Neighboring agents synchronize their operational state. If one arm enters "data collection mode," nearby arms align to support roles (one leads, one follows). Operational modes propagate through the mesh.
3. **Cohesion**: Agents gravitate toward the swarm's current objective. If the swarm's goal is "collect 100 episodes of pick-and-place," all idle agents steer toward contributing to that goal.

*Research basis: [Boids-Based Integration Algorithm for Formation Control](https://www.mdpi.com/2075-1702/13/4/255) -- 2025 paper applying boid rules to multi-UAV formation control with independent obstacle avoidance.*

### Idea 18: Velocity Matching for Teleoperation Sync

During leader-follower teleoperation, the follower arm should match the "velocity" (operational tempo) of the leader. If the leader moves slowly (human is being careful), the follower moves slowly with high precision. If the leader moves fast (human is doing a quick demo), the follower matches speed but relaxes precision. This is alignment in the boids sense -- matching neighbors' velocity vectors.

### Idea 19: Obstacle Avoidance as Social Force

Boids avoid obstacles through repulsion fields. Robot citizens should treat fault conditions as "obstacles" in capability space. If the elbow servo is running hot (the documented overload problem), that joint becomes an "obstacle" -- all motion planning routes around it (reduces elbow usage, compensates with shoulder and wrist). The avoidance field strength scales with fault severity.

*Research basis: [Decentralized potential field-based self-organizing control framework](https://www.mdpi.com/2218-6581/14/12/192) -- 2025 framework for trajectory, formation, and obstacle avoidance in autonomous swarm robots.*

### Idea 20: Emergent Formation for Multi-Camera Coverage

When multiple cameras are connected to the mesh, they should self-organize into coverage formations using flocking rules. Separation ensures no two cameras point at the same region. Alignment ensures cameras track the same workspace. Cohesion ensures all cameras contribute to the task's field-of-view requirements. The result: plug in 3 cameras and they auto-negotiate optimal viewpoints.

---

## 6. Immune System: Security, Fault Detection, and Memory

### Idea 21: Self/Non-Self Recognition for Mesh Security

Every legitimate citizen has a cryptographic identity (ed25519 keypair generated at first boot). The mesh maintains a "self" set -- known-good citizen fingerprints. Any device that joins without a recognized fingerprint triggers an innate immune response: it can announce capabilities (waggle dance) but cannot issue commands or receive sensitive data until a human "T-cell" (the operator) approves it. Rogue agents are quarantined, not crashed -- they can still be inspected.

*Research basis: [Artificial Immune Systems for self-healing in swarm robotic systems](https://link.springer.com/chapter/10.1007/978-3-319-23108-2_6) -- immune-inspired swarm self-healing using granuloma formation as a model for fault containment.*

### Idea 22: Danger Signal Broadcasting

The biological immune system uses "danger signals" (DAMPs) -- molecules released by damaged cells that activate immune responses even without foreign pathogens. Robot citizens should emit danger signals when they detect anomalies that don't match known fault patterns: unexpected servo register values, USB disconnects during operation, sudden sensor noise spikes. These danger signals activate heightened monitoring across the mesh even before the specific fault is identified.

### Idea 23: Immune Memory Cells -- Learned Fault Patterns

When the mesh encounters and recovers from a fault (like the voltage collapse from insufficient PSU current), it creates an "immune memory" entry:
```json
{
  "pattern": "all_servo_voltages_drop_below_6V_simultaneously",
  "diagnosis": "psu_current_limit",
  "response": "reduce_total_torque_demand_below_2A",
  "confidence": 0.95,
  "first_seen": "2026-03-15",
  "occurrences": 12
}
```
This memory is shared across the mesh. A new arm joining the swarm immediately inherits all learned fault patterns -- it doesn't have to experience the voltage collapse itself to know how to handle it.

### Idea 24: Clonal Selection for Policy Evolution

The immune system amplifies cells that successfully fight infections (clonal selection). When a robot policy variant performs well (higher success rate, fewer faults), it gets "cloned" -- distributed to other agents as their default. Poor-performing variants get suppressed. Over time, the swarm converges on the best policies through distributed evolutionary pressure, not centralized training.

### Idea 25: Inflammatory Response -- Graduated Fault Escalation

Like biological inflammation (redness, swelling, heat, pain), implement graduated fault responses:
1. **Local response**: The affected servo adjusts its own protection parameters
2. **Regional response**: Neighboring joints on the same arm compensate (reduce load on overloaded elbow by adjusting shoulder)
3. **Systemic response**: The entire arm enters protective mode (slower motion, reduced workspace)
4. **Mesh response**: Other devices on the mesh are warned; the operator is notified

Each level triggers only if the previous level fails to resolve the issue.

---

## 7. Neural Networks (Biological): Hebbian Learning in the Mesh

### Idea 26: "Fire Together, Wire Together" Connection Strengthening

Devices that frequently collaborate successfully strengthen their communication links. If the Surface Pro and follower arm consistently work well together for inference tasks, their connection gets priority (lower latency, more bandwidth, faster heartbeats). If two devices rarely interact, their link weakens (longer heartbeat intervals, lower priority). The mesh topology self-organizes based on actual collaboration patterns.

*Research basis: [Cooperative multi-agent reinforcement learning for robotic systems](https://journals.sagepub.com/doi/10.1177/15741702251370050) -- 2025 review of MARL approaches for robotic coordination.*

### Idea 27: Synaptic Plasticity for Role Assignment

In the brain, synaptic connections strengthen or weaken based on activity. Robot roles should be similarly plastic: if the "follower" arm consistently performs better as a "leader" (smoother trajectories, better force control), gradually shift its role. Don't hard-code leader/follower -- let the mesh discover optimal role assignments through use, like neural circuits discovering optimal signal pathways.

### Idea 28: Long-Term Potentiation for Skill Retention

LTP is how the brain converts short-term memories into long-term ones. When a robot successfully performs a new skill multiple times (say, 10 successful pick-and-place episodes), that skill gets "potentiated" -- saved to persistent storage, shared across the mesh, and marked as a core competency. Skills that are performed once and never repeated decay (like short-term memories that aren't consolidated).

### Idea 29: Inhibitory Interneurons -- Active Suppression of Bad Behaviors

The brain isn't just about excitation -- inhibitory neurons are equally important. Implement active suppression agents that monitor for known-bad patterns: motion commands that exceed joint limits, torque demands that will trigger protection faults, trajectories that pass through collision zones. These "inhibitory" processes run alongside every motion command and can veto unsafe actions in real-time, like inhibitory interneurons preventing seizures.

---

## 8. Octopus: Distributed Intelligence with Local Autonomy

### Idea 30: Two-Thirds of Intelligence in the Arms

An octopus has ~500 million neurons, and two-thirds of them are in the arms, not the central brain. Apply this directly: each SO-101 arm should run its own local agent (on an attached Pi or ESP32) handling:
- Servo protection and safety (no cloud round-trip for emergency stops)
- Basic reflexes (if load > 90%, reduce velocity immediately)
- Local calibration and self-test
- Trajectory smoothing and interpolation

The Surface Pro (the "brain") handles high-level planning, task assignment, and coordination -- but the arms can operate semi-autonomously even if the brain goes offline.

*Research basis: [Octopus-inspired Distributed Control for Soft Robotic Arms](https://arxiv.org/abs/2603.10198) -- March 2026 paper using graph neural networks for distributed octopus-arm control with semi-autonomous segments.*

### Idea 31: Arm-Level Reflexes that Override Brain Commands

Octopus arms can perform local withdrawal reflexes without brain involvement. Implement hardware-level reflexes on each arm's microcontroller:
- **Overcurrent reflex**: If total arm current exceeds 4A, immediately reduce all joint velocities by 50% (don't wait for the Surface Pro to decide)
- **Collision reflex**: If any joint hits a hard stop, reverse 5 degrees and hold (local decision, report to brain after)
- **Thermal reflex**: If any servo temp > 65C, enter slow-motion mode (max 25% speed)

These reflexes are hardcoded and cannot be overridden by the brain. Safety is non-negotiable at the local level.

### Idea 32: Hierarchical Suction Intelligence -- Layered Sensing

Octopus suckers have their own sensory processing. Each servo in the SO-101 is like a sucker -- it has local sensors (position, velocity, load, temperature, voltage). Implement per-servo data processing that runs at the servo's native update rate (1kHz for STS3215) and only sends summarized/anomalous data to the arm controller, which only sends summarized/anomalous data to the brain. Three layers of processing, each filtering and compressing, like the octopus's hierarchical sensory system.

*Research basis: [Embodying soft robots with octopus-inspired hierarchical suction intelligence](https://www.science.org/doi/10.1126/scirobotics.adr4264) -- Science Robotics 2024.*

### Idea 33: Semi-Autonomous Exploration with Central Veto

Octopus arms explore crevices independently while the brain monitors. Robot arms should similarly be able to run exploratory behaviors (random safe motions within the known-safe workspace envelope) without explicit brain commands -- useful for self-calibration, workspace mapping, and discovering new capabilities. The brain watches via telemetry and can veto any motion that looks problematic, but doesn't need to command every movement.

---

## Cross-Cutting Synthesis Ideas

### Idea 34: The Citizenship Protocol Stack

Combine multiple biological metaphors into a layered protocol:

| Layer | Biological Model | Function |
|-------|-----------------|----------|
| Physical Safety | Octopus arm reflexes | Local emergency responses, <1ms |
| Fault Detection | Immune system danger signals | Anomaly detection and warning, <100ms |
| Neighbor Discovery | Bee waggle dance | Capability advertisement, mDNS/UDP, <1s |
| Task Coordination | Ant stigmergy | Distributed task allocation via pheromone DHT, <5s |
| Skill Sharing | Mycelium nutrient exchange | Experience replay across mesh, async |
| Swarm Behavior | Boids flocking rules | Emergent formation and role assignment, continuous |
| Learning | Hebbian plasticity | Connection strengthening based on collaboration success, hours/days |
| Evolution | Immune clonal selection | Policy evolution across the swarm, days/weeks |

### Idea 35: Heartbeat as Pulse -- Biological Vital Signs

Every citizen emits a "pulse" (heartbeat) at a frequency proportional to its activity level. Idle devices pulse slowly (every 5s). Active devices pulse fast (every 200ms). A missing pulse means the citizen is "dead" or disconnected -- neighbors detect this within 2x the expected pulse interval and redistribute that citizen's tasks. This is directly analogous to how biological organisms use heart rate as a proxy for metabolic state.

### Idea 36: Seasonal Adaptation -- Day/Night Operational Modes

Many biological systems have circadian rhythms. The robot mesh should have operational modes:
- **Active mode** (human present): Full teleoperation support, real-time safety monitoring, all citizens at high alert
- **Maintenance mode** (overnight): Self-calibration runs, firmware checks, experience replay consolidation, battery monitoring
- **Hibernation mode** (extended idle): Minimal power, only heartbeats and security monitoring

Mode transitions propagate through the mesh like circadian signals -- when the Surface Pro detects the human has left (no keyboard/mouse input for 30 min), it signals the swarm to transition.

### Idea 37: Symbiosis Contracts Between Citizens

Biological symbiosis involves explicit mutual benefit. Citizens should form "symbiosis contracts":
- Surface Pro + Follower Arm: "I provide inference compute, you provide physical execution"
- Camera + Arm: "I provide visual feedback, you provide the workspace I observe"
- Pi + Sensors: "I provide GPIO access, you provide data processing"

Contracts are registered in the mesh DHT. If one party fails to uphold its contract (goes offline, degrades performance), the other party is freed to find a new symbiont. This formalizes the informal dependencies between devices.

### Idea 38: Genetic Memory -- Configuration DNA

Each citizen carries a "genome" -- its configuration, calibration, protection settings, and learned behaviors, stored as a portable JSON/YAML blob. When a citizen is replaced (new arm, new Pi), it can inherit the genome of its predecessor:
```
so101-follower-alpha.genome.json
  - servo_protection: {overload_torque: 90, protective_torque: 50, ...}
  - calibration: {joint_offsets: [...]}
  - learned_faults: [{voltage_collapse_pattern}, ...]
  - skill_library: [{pick_place_v3}, ...]
```
This is how the swarm maintains institutional memory even as individual citizens are replaced -- like DNA passing between generations.

---

## Implementation Priority for Current Setup

Given the current hardware (Surface Pro 7 + 2x SO-101 arms + USB cameras), the highest-impact ideas to implement first:

1. **Idea 31 (Arm reflexes)** -- Immediately prevents the documented voltage collapse and overload protection issues
2. **Idea 9 (Telemetry warning propagation)** -- Builds on existing `monitor_arm.py` and `teleop_monitor.py` infrastructure
3. **Idea 5 (Waggle dance discovery)** -- Foundation for any mesh; simple mDNS broadcast
4. **Idea 23 (Immune memory)** -- Capture the hard-won knowledge about PSU current limits and servo protection
5. **Idea 38 (Genetic memory)** -- Portable calibration and protection settings already partially exist in the calibration JSON files

---

## Sources

- [Automatic design of stigmergy-based behaviours for robot swarms](https://www.nature.com/articles/s44172-024-00175-7) -- Nature Communications Engineering, 2024
- [Bio-inspired artificial pheromone system for swarm robotics applications](https://journals.sagepub.com/doi/full/10.1177/1059712320918936) -- Na et al., 2021
- [Stigmergy: from mathematical modelling to control](https://pmc.ncbi.nlm.nih.gov/articles/PMC11371424/) -- PMC, 2024
- [Towards applied swarm robotics: current limitations and enablers](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1607978/full) -- Frontiers, 2025
- [Digital pheromone mechanisms for coordination of unmanned vehicles](https://www.researchgate.net/publication/314794862_Digital_pheromone_mechanisms_for_coordination_of_unmanned_vehicles) -- ResearchGate
- [Mycelium coordination layer for AI agent networks](https://mycelium.fyi/)
- [Octopus-inspired Distributed Control for Soft Robotic Arms](https://arxiv.org/abs/2603.10198) -- arXiv, March 2026
- [Embodying soft robots with octopus-inspired hierarchical suction intelligence](https://www.science.org/doi/10.1126/scirobotics.adr4264) -- Science Robotics, 2024
- [Learning from Octopuses: Cutting-Edge Developments and Future Directions](https://pmc.ncbi.nlm.nih.gov/articles/PMC12024937/) -- PMC
- [An immune-inspired swarm aggregation algorithm for self-healing swarm robotic systems](https://pubmed.ncbi.nlm.nih.gov/27178784/) -- PubMed
- [Artificial Immune System for self-healing in swarm robotic systems](https://link.springer.com/chapter/10.1007/978-3-319-23108-2_6) -- Springer
- [Slime Mould Metaheuristic for optimization and robot path planning](https://www.sciencedirect.com/science/article/pii/S0925231225012238) -- ScienceDirect, 2025
- [Enhanced slime mold algorithm for autonomous mobile robot path planning](https://pmc.ncbi.nlm.nih.gov/articles/PMC10616528/) -- PMC, 2023
- [Boids-Based Integration Algorithm for Formation Control in UAVs](https://www.mdpi.com/2075-1702/13/4/255) -- MDPI, 2025
- [Distributed control strategy for robot flocking](https://www.nature.com/articles/s41598-024-83703-x) -- Scientific Reports, 2024
- [Decentralized potential field-based self-organizing control framework](https://www.mdpi.com/2218-6581/14/12/192) -- MDPI, 2025
- [Cooperative multi-agent reinforcement learning for robotic systems](https://journals.sagepub.com/doi/10.1177/15741702251370050) -- SAGE, 2025
- [LLM Collaboration with Multi-Agent Reinforcement Learning](https://arxiv.org/pdf/2508.04652) -- arXiv, 2025
