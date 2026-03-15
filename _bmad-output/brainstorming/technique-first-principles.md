# First Principles Thinking + Assumption Reversal

**Technique:** First Principles Decomposition with Systematic Assumption Reversal
**Date:** 2026-03-15
**Topic:** Distributed Autonomous Robot Agent System -- Every Device is a Citizen

---

## Part 1: Decomposition from Fundamental Truths

### What IS a Robot Citizen?

Strip away every assumption from robotics, IoT, ROS, cloud platforms. Start from nothing.

A citizen is an entity that:

1. **Exists** -- it has a unique, unforgeable identity. Not an IP address (those change). Not a MAC address (those can be spoofed). A cryptographic keypair generated at first boot. The public key IS the identity. Everything else is metadata.

2. **Has capabilities** -- it can DO things. A servo arm can move. A camera can see. A laptop can compute. A speaker can talk. These capabilities are not static -- a camera in a dark room has degraded "seeing" capability. Capabilities are dynamic, self-assessed, and advertised honestly.

3. **Has location** -- physical position in the real world. Not GPS coordinates (too imprecise indoors). Relative position to other citizens. "I am 30cm from citizen-arm-alpha, mounted on the same table." Location is discovered, not configured.

4. **Has state** -- busy, idle, sleeping, broken, learning, calibrating. State is observable by neighbors and self-reported.

5. **Has autonomy** -- the ability to make decisions within policy bounds. A citizen can refuse a request ("I cannot lift that -- it exceeds my torque limit"). A citizen can propose actions ("I notice the block is near me, should I pick it up?").

6. **Has memory** -- learned behaviors, calibration data, history of interactions, knowledge of what worked and what failed.

7. **Has mortality** -- batteries die, servos wear out, SD cards corrupt. A citizen knows it is mortal and can transfer knowledge before death.

**Minimum viable citizen:** Identity + one capability + state reporting. A temperature sensor with a keypair that broadcasts "I am sensor-7f3a, I measure temperature, current reading is 23.4C, I am healthy." That is the simplest citizen.

### What IS a Country?

A country is not a server. A country is an agreement.

1. **Constitution** -- immutable rules that all citizens must follow. Safety constraints. "No arm shall move faster than X degrees/second when a human is detected within Y cm." The constitution is small, fits in a few kilobytes, and every citizen carries a copy.

2. **Laws** -- mutable policies set by the governor (user). "Cameras should record when motion is detected." "Arms should return to home position when idle for 5 minutes." Laws can be updated. Citizens receive law updates and comply or report inability to comply.

3. **Borders** -- the physical and network boundaries of the country. Which WiFi networks define the territory? Which Bluetooth ranges? A country could span multiple physical locations connected by VPN, or it could be a single room bounded by a local network.

4. **Immigration** -- when a new device plugs in or joins the network, it goes through immigration. It presents its identity, declares its capabilities, and receives the constitution and current laws. The governor can pre-approve device types ("all Feetech controllers are auto-admitted") or require manual approval.

5. **Citizenship registry** -- the list of all citizens, their capabilities, their last known state. This is NOT centralized. Every citizen maintains a partial view. Consistency is eventual, not immediate. A citizen that goes offline for an hour and comes back can sync the registry with any neighbor.

6. **Economy** -- citizens trade resources. Compute time, sensor data, physical actions. An arm trades manipulation capability for camera data. A laptop trades compute for physical-world information. This is not cryptocurrency -- it is cooperative resource allocation.

7. **Culture** -- learned collective behaviors. "In this country, we always verify servo positions before executing trajectories." Culture emerges from experience and is encoded as shared policies.

### What IS Governance Without Micromanagement?

The user does not command individual robots. The user sets policy and intent.

**Governance primitives:**

1. **Goals** -- "Sort the colored blocks by color." The system figures out which citizens do what.
2. **Constraints** -- "Never exceed 50% torque." Applied globally or per-citizen-type.
3. **Priorities** -- "Safety > task completion > energy efficiency."
4. **Permissions** -- "Arms can move freely in zone A. Zone B requires confirmation."
5. **Escalation rules** -- "If confidence < 70%, ask me. If confidence < 30%, stop."
6. **Delegation** -- "Citizen-alpha is the coordinator for sorting tasks." The user appoints leaders, not micromanages.

---

## Part 2: Assumption Reversal

### Reversed Assumption 1: No Central Server

**Standard assumption:** There is a server (laptop, cloud, Raspberry Pi) that coordinates everything.

**Reversed:** Fully peer-to-peer. Every citizen is equal. No single point of failure.

**Implications:**
- Discovery must be local (mDNS, BLE beacons, or broadcast UDP on local network)
- Consensus requires distributed agreement (Raft is overkill for 5-20 devices -- simple leader election with heartbeats suffices)
- The "country" survives any single device being unplugged
- The user's phone/laptop is just another citizen with a special role (governor), not the brain
- If the governor goes offline, the country continues operating under last known laws

**Idea 1: Gossip Protocol for Robot State.** Each citizen periodically tells a random neighbor its state. State propagates like a rumor. Within seconds, every citizen knows every other citizen's approximate state. No central database needed. This is how Cassandra and Consul work, scaled down to 5-50 devices.

**Idea 2: Leaderless Task Allocation via Auction.** When a goal arrives, it is broadcast. Citizens bid based on capability, proximity, and current load. The bid with the best score wins. No coordinator needed. If two citizens tie, the one with the lower public-key hash wins (deterministic tiebreak).

**Idea 3: Constitution as Signed Document.** The constitution is a JSON document signed by the governor's key. Every citizen verifies the signature before accepting it. A malicious device cannot alter the constitution because it cannot forge the governor's signature.

### Reversed Assumption 2: Devices Do NOT Trust Each Other

**Standard assumption:** Everything on my network is friendly.

**Reversed:** Zero trust. Every message must be authenticated. A compromised device should not be able to harm the country.

**Implications:**
- Every message is signed by the sender's private key
- Citizens maintain reputation scores for each other (did they do what they said they would?)
- A citizen that behaves erratically (sending contradictory state, claiming impossible capabilities) gets quarantined
- The governor can revoke citizenship (add public key to revocation list)

**Idea 4: Capability Attestation.** A citizen does not just claim "I can lift 500g." It provides proof: a signed log of recent lifts with measured torque values. Other citizens can verify claims against demonstrated performance. Liars get reputation downgrades.

**Idea 5: Blast Radius Containment.** If arm-alpha starts sending "move to maximum speed" commands to arm-beta, arm-beta checks: does arm-alpha have authority to command me? The constitution says only the governor and designated coordinators can issue movement commands. Arm-alpha is quarantined. The blast radius of a compromised device is limited to its own actuators.

**Idea 6: Physical Safety as Constitutional Right.** No citizen can command another citizen to violate safety constraints, regardless of authority level. Safety limits are in the constitution and cannot be overridden by laws. This is the equivalent of constitutional rights that even the government cannot violate.

### Reversed Assumption 3: The Network is Unreliable

**Standard assumption:** WiFi works, messages arrive, latency is low.

**Reversed:** Devices go offline constantly. WiFi drops. Batteries die mid-task. The system must be resilient to partial connectivity.

**Implications:**
- Every citizen must function independently when disconnected
- Tasks must be designed to be resumable, not atomic
- State must be reconcilable after a partition heals
- Offline citizens should not block online citizens

**Idea 7: Offline-First Task Execution.** When a citizen receives a task, it downloads everything it needs to execute independently: goal, constraints, relevant sensor snapshots. If the network dies mid-task, it continues. When connectivity returns, it reports results and syncs state.

**Idea 8: Conflict Resolution via Timestamps + Priority.** If two citizens both moved an object while partitioned, the one with the later timestamp wins (last-writer-wins CRDT). For safety-critical conflicts, the more conservative action wins (if one citizen says "stop" and another says "go", "stop" wins).

**Idea 9: Heartbeat-Based Presence with Graceful Degradation.** Each citizen broadcasts a heartbeat every 2 seconds. If 3 heartbeats are missed, the citizen is marked "possibly offline." After 10 missed, "presumed offline." Tasks assigned to presumed-offline citizens are re-auctioned. When the citizen comes back, it reconciles.

### Reversed Assumption 4: A Device is Malicious

**Standard assumption:** Devices are honest.

**Reversed:** A hacked robot arm could try to injure someone, steal data, or sabotage the system.

**Idea 10: Hardware-Enforced Safety Limits.** The servo firmware (not software) enforces maximum speed, torque, and position limits. armOS writes these to the servo EEPROM during immigration. Even if the controlling software is compromised, the hardware refuses dangerous commands. This is defense in depth.

**Idea 11: Behavioral Anomaly Detection at the Citizen Level.** Each citizen monitors its own behavior against its calibration baseline. If it detects that it is being commanded to do something outside normal parameters, it self-quarantines and alerts the governor. The citizen is its own watchdog.

**Idea 12: Cryptographic Command Chains.** Every command has a provenance chain: governor signed a law, law authorized coordinator-beta, coordinator-beta issued command to arm-alpha. arm-alpha can verify the entire chain. A command without a valid chain is rejected.

### Reversed Assumption 5: The User Has ZERO Technical Knowledge

**Standard assumption:** The user can SSH, read logs, configure YAML files.

**Reversed:** The user is a 10-year-old, a teacher with no CS background, or an elderly person.

**Idea 13: Natural Language Governance.** The user says "make sure the robots are gentle" and the system translates that to: reduce all torque limits by 30%, increase collision detection sensitivity. The user says "the red arm is in charge of the table area" and the system assigns coordinator role to the arm identified by its red enclosure color (detected via camera).

**Idea 14: Visual Country Dashboard.** A spatial map showing every citizen as an icon at its physical location. Green = healthy, yellow = busy, red = problem. Tap a citizen to see what it is doing. Drag a finger to define zones. No text configuration required.

**Idea 15: One-Button Immigration.** New device plugs in. Phone buzzes: "New device detected: Robot Arm (Feetech SO-101). Add to your country? [Yes] [No]." One tap. Done.

**Idea 16: Story-Based Goal Setting.** Instead of programming, the user describes a scenario: "Every morning at 8am, I want the arm to wave hello when it sees someone walk in." The system decomposes: schedule trigger (8am-9am) + vision trigger (person detected) + action (wave gesture from learned behavior library).

### Reversed Assumption 6: The Country Spans Multiple Locations

**Standard assumption:** All devices are on the same local network.

**Reversed:** Devices at home, at school, at the office. Different networks, different latencies, different security contexts.

**Idea 17: Embassy Model.** Each physical location is a "province" with its own local mesh. Provinces connect through "embassies" -- always-on relay nodes (a Raspberry Pi at each location connected via WireGuard VPN). Inter-province communication goes through embassies. Intra-province communication is local and fast.

**Idea 18: Location-Aware Laws.** "At home, arms can operate freely. At school, arms require teacher confirmation for every action." Laws have location scopes. A citizen that travels between locations (e.g., a mobile robot carried in a backpack) automatically switches to the local law set.

**Idea 19: Federated Learning Across Provinces.** An arm at home learns to pick up cups. An arm at school learns to sort pencils. The learned behaviors (model weights, not raw data) are shared across provinces. Both arms become better at general manipulation without sharing private sensor data.

---

## Part 3: The Fundamental Truths

### Physics
- **Latency is real.** Local servo control must be <10ms. Local network communication must be <50ms. Cross-internet must be <500ms for teleoperation. Design for these constraints, not against them.
- **Bandwidth is finite.** Camera streams at 30fps consume 5-30 Mbps. A country with 5 cameras will saturate a consumer WiFi network. Process locally, share summaries.
- **Power runs out.** Battery-powered citizens will die. The system must handle graceful departure (low battery = announce departure + transfer tasks) and ungraceful departure (power cut = neighbors detect absence and compensate).
- **Things break.** Gears wear, cables loosen, encoders drift. A citizen's capabilities degrade over time. The system must detect and adapt.

### Identity
- **Ed25519 keypair generated at first boot.** The public key is the citizen ID. 32 bytes. Stored in a tamper-resistant location if available (TPM, secure enclave), otherwise in a protected file.
- **Human-readable aliases.** The governor assigns names: "left-arm," "kitchen-camera," "Bradley's laptop." These are metadata, not identity.
- **Identity is portable.** If you move a servo controller to a new USB port, it is still the same citizen. Identity is in the controller's EEPROM, not in the port.

### Capability
- **Capabilities are typed.** A standard taxonomy: `sense.vision`, `sense.depth`, `sense.temperature`, `actuate.revolute`, `actuate.prismatic`, `compute.inference`, `compute.training`, `store.persistent`, `communicate.audio`.
- **Capabilities have parameters.** `actuate.revolute: {joints: 6, max_torque: 30kg_cm, max_speed: 60rpm, workspace_radius: 280mm}`.
- **Capabilities are dynamic.** A camera in a dark room: `sense.vision: {quality: degraded, reason: low_light}`. A servo at high temperature: `actuate.revolute: {max_torque: reduced_50pct, reason: thermal_protection}`.

### Intent
- **Users have goals, not programs.** "Sort the blocks" not "move joint 3 to 45 degrees then open gripper then..."
- **Goals decompose into tasks.** Tasks decompose into actions. Actions decompose into servo commands. Each layer can be handled by a different entity.
- **Intent can be ambiguous.** "Clean up" means different things in different contexts. The system asks clarifying questions or makes its best guess and reports what it did.

### Emergence
- **Collective behavior is more than individual behavior.** Two arms can hand objects to each other. Five cameras provide 360-degree coverage. A mobile base plus an arm creates a mobile manipulator. The system should discover and exploit these synergies.
- **Emergent failures also exist.** Two arms reaching for the same object creates a collision risk that neither arm would face alone. The system must detect and prevent emergent hazards.

---

## Part 4: Claude Agent to Robot Agent Mapping

| Claude Code Concept | Robot Citizen Equivalent |
|---------------------|------------------------|
| Tools (Bash, Read, Edit, Grep) | Capabilities (move, sense, compute, store) |
| Context window | Situational awareness (sensor fusion, neighbor state, recent history) |
| System prompt | Constitution + current laws |
| Memory (CLAUDE.md, memory files) | Learned behaviors, calibration data, experience logs |
| Skills (slash commands) | Composed behaviors ("pick-and-place," "patrol," "wave") |
| Tool results | Sensor readings, action outcomes, task completion reports |
| Conversation history | Interaction log with governor and other citizens |
| Temperature/creativity settings | Autonomy level (conservative=0.0 to exploratory=1.0) |
| Token budget | Energy budget, compute budget, time budget |
| Multi-turn reasoning | Multi-step task planning and execution |
| Error handling / retries | Fault recovery (retry servo command, re-plan trajectory, ask for help) |
| Agent orchestration (sub-agents) | Coordinator citizens delegating to worker citizens |

**Idea 20: Citizens Run Local LLMs as Their "Brain."** Each capable citizen (RPi 5+, Jetson, laptop) runs a small language model (Phi-3-mini, Gemma 2B) as its reasoning engine. The LLM receives the constitution as system prompt, sensor readings as context, and produces decisions as tool calls (move, sense, communicate). This is literally the Claude agent architecture replicated on a robot.

**Idea 21: Behavior as Skill Plugins.** Just as Claude Code has skills that can be invoked, robot citizens have behavior plugins: `pick_and_place.py`, `follow_person.py`, `sort_by_color.py`. New behaviors can be downloaded from a marketplace (like armOS profiles but for behaviors, not hardware configs). A citizen's capability grows as it acquires new skills.

**Idea 22: Context Window as Spatial Awareness.** A Claude agent's context window is its understanding of the current conversation. A robot citizen's "context window" is its spatial model: where am I, what do I see, what are my neighbors doing, what tasks are active, what happened recently. This spatial context has a budget (limited memory, limited sensor range) just like tokens.

---

## Part 5: The Minimum Viable Protocol

### Design Principles
1. **Transport agnostic.** Works over WiFi (UDP multicast), Bluetooth LE, USB serial, or even audio (ultrasonic between nearby devices). The protocol does not assume a specific physical layer.
2. **Human readable.** Messages are JSON (or CBOR for constrained devices). No binary protocol that requires a decoder ring.
3. **Self-describing.** Every message contains enough information to be understood without prior context.
4. **Small.** A heartbeat message is under 200 bytes. A capability advertisement is under 1KB. Bandwidth is precious.

### Message Types (7 total -- the minimum)

```
1. HEARTBEAT    -- "I exist, here is my state"
2. DISCOVER     -- "Who is out there?"
3. ADVERTISE    -- "Here is what I can do"
4. PROPOSE      -- "I think we should do X" (task proposal)
5. AGREE/REJECT -- "I accept/decline task X"
6. REPORT       -- "Here is the result of task X"
7. GOVERN       -- "New law/constitution update from governor"
```

**Idea 23: Seven-Message Protocol.** The entire robot citizen communication system needs only seven message types. Everything else is composed from these primitives. HEARTBEAT provides presence. DISCOVER initiates relationships. ADVERTISE shares capabilities. PROPOSE/AGREE/REJECT handle task negotiation. REPORT closes the loop. GOVERN updates policy. That is it. No pub/sub topics, no service calls, no action servers. Seven messages.

### Message Format

```json
{
  "v": 1,
  "type": "PROPOSE",
  "from": "ed25519:abc123...",
  "to": "ed25519:def456..." | "*",
  "ts": 1710500000000,
  "ttl": 30,
  "sig": "base64...",
  "body": {
    "task_id": "uuid",
    "goal": "pick_up_red_block",
    "constraints": {"max_torque_pct": 50},
    "priority": 0.8
  }
}
```

Every message is signed. Every message has a TTL (time to live) so stale messages are discarded. Messages can be unicast (to a specific citizen) or broadcast (to "*").

**Idea 24: TTL-Based Message Expiry.** In an unreliable network, old messages are dangerous. "Move to position X" from 30 seconds ago could be catastrophic if executed now. Every message has a TTL in seconds. Citizens discard expired messages. Safety-critical commands have short TTLs (2-5 seconds). Policy updates have long TTLs (3600 seconds).

---

## Part 6: Additional Ideas from First Principles

**Idea 25: Capability Composition Discovery.** When two citizens are near each other, they automatically check if their combined capabilities create something new. Arm + camera = visual manipulation. Mobile base + arm = mobile manipulator. Camera + speaker = interactive display. The system announces composite capabilities: "Citizens arm-alpha and camera-beta together offer: visual_pick_and_place."

**Idea 26: Energy-Aware Task Scheduling.** A battery-powered citizen should not accept long tasks when its battery is at 15%. The auction system factors in energy: a plugged-in citizen bids lower (more available) than a battery-powered one. Tasks naturally flow to citizens with the most resources.

**Idea 27: Dead Citizen's Will.** When a citizen detects imminent shutdown (low battery, thermal shutdown, user unplugging), it broadcasts a "will" -- a summary of its current tasks, partial results, and any knowledge that should be preserved. Neighboring citizens absorb this knowledge. The task gets re-auctioned with partial progress included.

**Idea 28: Apprenticeship Learning.** A new arm citizen observes an experienced arm citizen performing tasks. It records the demonstrations and trains a local policy. This is learning from demonstration, but between citizens rather than from a human. The experienced arm does not need to know it is teaching -- the new arm learns by watching through a shared camera citizen.

**Idea 29: Constitutional Amendments via Quorum.** The governor can amend the constitution. But for safety-critical changes (increasing speed limits, reducing safety margins), the system requires confirmation: "This change affects 4 citizens and reduces safety margins. Confirm? [Yes/No]." The system never silently accepts dangerous policy changes.

**Idea 30: Sensory Sharing as a Service.** A camera citizen does not just serve itself. It offers its visual stream to any citizen that needs it. An arm planning a grasp requests a depth frame from the nearest camera. The camera citizen provides it. This is capability lending -- citizens share senses they do not have.

**Idea 31: Territorial Mapping.** Citizens collectively build a spatial map of their environment. Each camera contributes its view. Each mobile base contributes odometry. The map is shared and continuously updated. New citizens can download the map during immigration to immediately understand their surroundings.

**Idea 32: Behavioral Quarantine Sandbox.** Before deploying a new behavior (skill plugin) to a citizen, it runs in a sandbox: simulated execution with the citizen's actual capability profile. If the simulated behavior violates any constitutional constraint (exceeds torque limits, enters forbidden zones), it is rejected before touching real hardware.

**Idea 33: Multi-Modal Citizen Identity.** A citizen can be identified by its cryptographic key (primary), but also by physical characteristics: the red arm, the camera with the scratched lens, the base that pulls slightly left. Physical identity allows the governor to refer to citizens naturally: "the arm on the left table." A camera citizen can map physical descriptions to cryptographic identities.

**Idea 34: Graceful Sovereignty Transfer.** If the governor (user's phone/laptop) goes offline permanently, the country does not collapse. The governor can pre-designate a successor ("if I'm offline for 24 hours, laptop-beta becomes governor"). Or the citizens can hold an election: the citizen with the most compute capability and longest uptime becomes interim governor with limited powers (maintain operations, no constitutional changes).

**Idea 35: Event-Driven Reactivity, Not Polling.** Citizens do not poll each other for state. They subscribe to events: "tell me when you detect a person," "tell me when your battery drops below 20%," "tell me when you finish task X." This is publish-subscribe built into the REPORT message type. Efficient, low-bandwidth, responsive.

**Idea 36: The Country Scales Down to ONE.** The architecture must work with a single citizen. One arm, no network, no peers. The governance model still applies: the arm has a constitution (safety limits), laws (user preferences), and capabilities. When a second citizen joins, the protocol activates. The single-citizen case is not a degenerate edge case -- it is the starting point. armOS v1.0 IS the single-citizen country.

---

## Part 7: Key Insight -- armOS is Already Building the First Citizen

The current armOS architecture -- hardware abstraction, safety watchdog, diagnostics engine, robot profiles, telemetry -- is the internal anatomy of a single robot citizen. The servo protocol is how the citizen controls its body. The diagnostic engine is self-awareness. The safety watchdog is the citizen's conscience. The profile system is the citizen's identity and capability declaration.

**The path from armOS v1.0 to robot citizenry:**

1. **v1.0 (now):** Single citizen. One arm, one machine, local control. The citizen's internal architecture is solid.
2. **v1.5:** Citizen identity. The arm gets a keypair. It can advertise itself on the local network. A second arm can discover it.
3. **v2.0:** Multi-citizen country. Two arms can see each other, negotiate tasks, share camera feeds. The seven-message protocol is live.
4. **v2.5:** Governance. The user sets policies via natural language. Citizens comply autonomously.
5. **v3.0:** Intelligence. Citizens learn from each other. Federated behavior sharing. The country gets smarter over time.

This is not a rewrite of armOS. It is the natural evolution of what is already being built. Every architectural decision in armOS v1.0 -- the plugin system, the YAML profiles, the event-driven telemetry -- maps directly to a citizen capability in the distributed model.

---

## Summary: 36 Ideas

| # | Idea | Category |
|---|------|----------|
| 1 | Gossip protocol for robot state propagation | Protocol |
| 2 | Leaderless task allocation via capability auction | Coordination |
| 3 | Constitution as cryptographically signed document | Governance |
| 4 | Capability attestation with proof-of-performance | Trust |
| 5 | Blast radius containment for compromised devices | Security |
| 6 | Physical safety as constitutional right (unoverridable) | Safety |
| 7 | Offline-first task execution with full context download | Resilience |
| 8 | Conflict resolution via timestamps + conservative-wins for safety | Resilience |
| 9 | Heartbeat-based presence with graceful degradation | Protocol |
| 10 | Hardware-enforced safety limits via servo EEPROM | Safety |
| 11 | Behavioral anomaly self-detection and self-quarantine | Security |
| 12 | Cryptographic command chains with provenance verification | Security |
| 13 | Natural language governance ("make the robots gentle") | UX |
| 14 | Visual spatial dashboard for non-technical users | UX |
| 15 | One-button immigration for new devices | UX |
| 16 | Story-based goal setting ("every morning wave hello") | UX |
| 17 | Embassy model for multi-location countries via VPN relays | Architecture |
| 18 | Location-aware laws with automatic context switching | Governance |
| 19 | Federated learning across provinces (share weights not data) | Intelligence |
| 20 | Local LLMs as citizen reasoning engines | Intelligence |
| 21 | Behavior as downloadable skill plugins (marketplace) | Ecosystem |
| 22 | Spatial awareness as the robot's "context window" | Architecture |
| 23 | Seven-message protocol (the minimum viable protocol) | Protocol |
| 24 | TTL-based message expiry for safety in unreliable networks | Protocol |
| 25 | Automatic capability composition discovery | Emergence |
| 26 | Energy-aware task scheduling via auction bid weighting | Coordination |
| 27 | Dead citizen's will (knowledge transfer before shutdown) | Resilience |
| 28 | Apprenticeship learning between citizens | Intelligence |
| 29 | Constitutional amendments with safety quorum | Governance |
| 30 | Sensory sharing as a service (capability lending) | Coordination |
| 31 | Collective territorial mapping from distributed sensors | Intelligence |
| 32 | Behavioral quarantine sandbox before real-hardware deploy | Safety |
| 33 | Multi-modal citizen identity (crypto + physical appearance) | Identity |
| 34 | Graceful sovereignty transfer if governor goes offline | Resilience |
| 35 | Event-driven reactivity, not polling | Protocol |
| 36 | Architecture scales down to one citizen (armOS v1.0 IS the first citizen) | Architecture |
