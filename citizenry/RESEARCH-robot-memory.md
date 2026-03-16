# Robot Memory for armOS Citizenry

**Research Date:** 2026-03-16
**Purpose:** Design a structured memory system for autonomous robot citizens

---

## Table of Contents

1. [The Gap in armOS Today](#the-gap)
2. [Episodic Memory](#episodic-memory)
3. [Semantic Memory / Knowledge Graphs](#semantic-memory)
4. [Procedural Memory](#procedural-memory)
5. [Memory Consolidation](#memory-consolidation)
6. [Shared Fleet Memory](#shared-fleet-memory)
7. [Practical Implementations Survey](#practical-implementations)
8. [Proposed armOS Memory Architecture](#proposed-architecture)
9. [Implementation Plan](#implementation-plan)
10. [References](#references)

---

## The Gap in armOS Today <a id="the-gap"></a>

Citizens currently have three persistence layers:

| System | What it stores | File |
|--------|---------------|------|
| **Genome** | Calibration, protection settings, hardware descriptor, XP, skill defs, immune memory | `genome.py` |
| **Skill Tree** | Skill DAG with XP thresholds and prerequisites | `skills.py` |
| **Immune Memory** | Fault patterns with conditions, mitigations, severity, occurrence counts | `immune.py` |

**What's missing:**

- **No episodic memory** -- A citizen cannot recall "I tried to pick up the red block at 14:32 and failed because my gripper force was insufficient." It has immune memory (fault patterns) but not event memory.
- **No semantic memory** -- A citizen has no knowledge graph. It cannot represent "the charging station is near the south wall" or "red blocks are heavier than blue blocks."
- **No procedural memory beyond skill trees** -- XP tracks *whether* a citizen can do something, not *how* to do it best. No stored trajectories, approach angles, or learned motion parameters.
- **No consolidation** -- Short-term observations vanish. There is no mechanism to promote repeated observations into durable knowledge.
- **No shared memory protocol** -- Immune patterns are broadcast via mycelium, but there is no structured way for citizens to share experiences, spatial knowledge, or learned procedures.

---

## Episodic Memory <a id="episodic-memory"></a>

### What the research says

Episodic memory stores specific events: what happened, where, when, and the outcome. In cognitive science, it is the system that lets you remember "last Tuesday I dropped the coffee because the mug was wet."

**Key papers and systems:**

- **RoboMemory** (Lei et al., 2025, arXiv:2508.01415) -- Unifies Spatial, Temporal, Episodic, and Semantic memory in a parallelized architecture. Uses a dynamic spatial knowledge graph for consistent memory updates and a closed-loop planner with critic module. Achieved 26.5% improvement over baselines on EmbodiedBench.

- **HIMM** (Li et al., 2026, arXiv:2602.15513) -- "Explicitly disentangles episodic and semantic memory." Episodic memory stores specific experiences with a "retrieval-first, reasoning-assisted" approach: retrieve by semantic similarity, then validate via visual reasoning. Semantic memory converts experiences into structured, reusable rules via "program-style rule extraction." +11.4% on embodied QA.

- **MrSteve** (Park et al., 2024, arXiv:2411.06736, ICLR 2025) -- Place Event Memory (PEM) captures **what-where-when** tuples. Each episode records what event occurred, the spatial location, and the timestamp. This structure enables efficient recall and navigation for long-horizon tasks.

- **Mind Palace** (Ginting et al., 2025, arXiv:2507.12846) -- Encodes "episodic experiences as scene-graph-based world instances." Uses value-of-information-based stopping criteria to decide when to explore vs. recall.

- **Ella** (Zhang et al., 2025, arXiv:2506.24019) -- Embodied social agent with "spatiotemporal episodic memory for capturing multimodal experiences" + "name-centric semantic memory for organizing acquired knowledge." Enables lifelong learning in open worlds.

- **3DLLM-Mem** (Hu et al., 2025, arXiv:2505.22657) -- Working memory tokens serve as queries into episodic memory (past observations). Current perception actively retrieves relevant history. +16.5% over baselines.

- **TriVLA** (Liu et al., 2025, arXiv:2507.01424) -- "Episodic world model" enabling robots to "accumulate, recall, and predict sequential experiences." Three systems: multimodal grounding (System 2), dynamics perception via video diffusion (System 3), and action policy (System 1). Runs at 36 Hz.

### Design patterns for episodic memory

**The What-Where-When-Outcome tuple** (from MrSteve and cognitive science):

```python
@dataclass
class Episode:
    id: str                    # UUID
    timestamp: float           # When
    citizen_id: str            # Who experienced it
    location: str              # Where (zone/station ID)
    event_type: str            # What category (pick, place, navigate, fail, ...)
    description: str           # Natural language summary
    context: dict              # Structured data (objects involved, forces, sensor readings)
    outcome: str               # success / failure / partial
    importance: float          # 0.0-1.0, computed at write time
    embedding: list[float]     # For similarity retrieval (optional)
    tags: list[str]            # Searchable labels
```

**Episode boundaries:** An episode starts when a task begins and ends when it succeeds, fails, or is interrupted. Sub-episodes can nest (a pick-and-place contains a reach, grasp, lift, move, release).

**Importance scoring** (from Lilian Weng's survey of agent memory):
- Recency: exponential decay from timestamp
- Significance: failures score higher than routine successes
- Novelty: first-time events score higher than repeats
- Emotional valence: high-stress states (from `emotional.py`) boost importance

**Retention policy:** Keep all episodes for N days (configurable, default 7). After that, consolidate important episodes into semantic memory and prune low-importance ones. This mirrors the hippocampal consolidation model.

---

## Semantic Memory / Knowledge Graphs <a id="semantic-memory"></a>

### What the research says

Semantic memory stores general knowledge: facts, relationships, categories. "Red blocks are usually on the left table." "The charging station is near the south wall." It is built by consolidating episodic memories into durable knowledge.

**Key papers:**

- **G-Memory** (Zhang et al., 2025, arXiv:2506.07398) -- Three-tier graph hierarchy: **insight graphs** (generalizable knowledge), **query graphs** (task-specific info), **interaction graphs** (detailed collaboration trajectories). Bidirectional traversal retrieves both high-level insights and fine-grained interaction traces. +20.89% on embodied action success.

- **MEMENTO** (Kwon et al., 2025, arXiv:2505.16348) -- "Hierarchical knowledge graph-based user-profile memory module." Identifies two critical memory bottlenecks: information overload and coordination failures when handling multiple memories.

- **HIMM's semantic layer** -- Converts episodic experiences into "program-style rules" for reuse. This is the consolidation pathway: episodes become rules.

- **Mind Palace** -- Scene-graph-based world instances. Objects have properties, spatial relationships, and temporal annotations.

### Design patterns for semantic knowledge

**Simple property graph** (implementable in JSON):

```python
@dataclass
class KnowledgeNode:
    id: str                     # e.g., "object:red_block_1"
    node_type: str              # object, location, agent, concept
    properties: dict            # color, weight, size, etc.
    confidence: float           # 0.0-1.0
    last_updated: float
    source_episodes: list[str]  # Episode IDs that contributed to this knowledge

@dataclass
class KnowledgeEdge:
    source: str                 # Node ID
    target: str                 # Node ID
    relation: str               # "located_at", "heavier_than", "used_for", "near"
    confidence: float
    last_updated: float
    source_episodes: list[str]
```

**Why not RDF/OWL?** Too heavy for edge robotics. A JSON-backed property graph with simple relation types is sufficient for armOS citizens and can be persisted to `~/.citizenry/<name>.knowledge.json`.

**Key relation types for robot knowledge:**
- Spatial: `located_at`, `near`, `left_of`, `above`, `inside`
- Causal: `causes`, `prevents`, `requires`
- Property: `has_property`, `weighs`, `colored`
- Temporal: `usually_at` (with time-of-day), `moved_from`
- Social: `owned_by`, `used_by`, `preferred_by`

**Object permanence:** When a citizen last sees an object at location X, it creates/updates a `located_at` edge with a timestamp. Confidence decays over time. If another citizen reports the object elsewhere, the edge updates. This gives the fleet approximate object tracking without a central database.

---

## Procedural Memory <a id="procedural-memory"></a>

### What the research says

Procedural memory stores *how* to do things -- not just that you can, but the specific motor patterns and strategies that work best.

**Key papers and systems:**

- **Voyager** (Wang et al., 2023, arXiv:2305.16291) -- Stores learned behaviors as **executable code** in a skill library. Skills are composable and retrievable. When facing a new task, the agent retrieves relevant code from the library and composes it. 3.3x more unique items collected, 15.3x faster tech tree progression vs. baselines.

- **LRLL - Lifelong Robot Library Learning** (Tziafas & Kasaei, 2024, arXiv:2406.18746) -- LLM-based agent that "continuously grows the robot skill library." Four mechanisms: soft memory module for storing/retrieving experiences, self-guided exploration policy, skill abstractor that distills experiences into new library skills, and a lifelong learning algorithm.

- **LOTUS** (Wan et al., 2023, arXiv:2311.02058) -- Builds "an ever-growing skill library from a sequence of new tasks." Uses open-vocabulary vision models for unsupervised skill discovery from demonstrations. A meta-controller composes skills for complex tasks.

- **AtomicVLA** (Zhang et al., 2026, arXiv:2603.07648) -- "Jointly generates task-level plans, atomic skill abstractions, and fine-grained actions" through Skill-Guided Mixture-of-Experts.

- **Code as Policies** (Liang et al., 2022, arXiv:2209.07753) -- LLMs generate robot policy code from natural language. Stateless (no memory), but the pattern of "skills as code" is directly relevant.

- **SayCan** (Ahn et al., 2022, arXiv:2204.01691) -- Grounds language in robotic affordances by combining LLM semantic knowledge with pretrained skill value functions. The skill value function is a form of procedural knowledge: "I know how well I can do this action in this state."

### Design patterns for procedural memory

The existing armOS `SkillTree` tracks XP and prerequisites -- *whether* a citizen can do something. Procedural memory adds *how* to do it best.

**Skill procedures as stored parameters:**

```python
@dataclass
class Procedure:
    id: str
    skill_name: str             # Links to SkillTree
    description: str            # "Pick up cup from right side"
    parameters: dict            # Learned parameters: approach_angle, grip_force, speed, etc.
    success_rate: float         # Empirical success rate
    avg_duration: float         # How long it typically takes
    context_conditions: dict    # When to use this procedure (object_type, surface, etc.)
    source: str                 # "learned", "demonstrated", "shared"
    learned_from_episodes: list[str]  # Episode IDs where this was refined
    created_at: float
    last_used: float
    use_count: int
```

**Multiple procedures per skill:** A citizen might have three ways to pick up a cup -- from the right, from the left, from above. Each has different success rates in different contexts. The procedural memory selects the best one based on the current context.

**Trajectory snippets** (for manipulation citizens):

```python
@dataclass
class TrajectorySnippet:
    id: str
    procedure_id: str           # Parent procedure
    waypoints: list[dict]       # [{joint_positions, gripper_state, timestamp}, ...]
    duration: float
    reference_frame: str        # "base", "object", "world"
    recorded_at: float
```

**The Voyager pattern applied to armOS:** Instead of storing executable code (appropriate for Minecraft), armOS citizens store parameter sets and trajectory snippets. When attempting a skill, the citizen:
1. Queries procedural memory for matching procedures (skill + context)
2. Ranks by success_rate in similar conditions
3. Executes the best procedure
4. Records the outcome as an episode
5. Updates the procedure's success_rate and parameters

---

## Memory Consolidation <a id="memory-consolidation"></a>

### What the research says

Memory consolidation is the process of converting short-term observations into long-term knowledge. In neuroscience, this happens during sleep via hippocampal replay -- the brain replays recent experiences, strengthening important connections and pruning unimportant ones.

**Key papers:**

- **The AI Hippocampus** (Jia et al., 2026, arXiv:2601.09113) -- Comprehensive survey organizing AI memory into implicit (in parameters), explicit (external stores), and agentic (persistent, temporally-extended). Highlights open challenges: memory capacity constraints, alignment issues, factual consistency.

- **AutoAgent** (Wang et al., 2026, arXiv:2603.09716) -- "Elastic Memory Orchestrator" that: (1) preserves raw records, (2) compresses redundant trajectories, (3) constructs reusable episodic abstractions. This is consolidation in action -- raw events become compressed, reusable knowledge.

- **HIMM's consolidation** -- Episodic memory uses "retrieval-first, reasoning-assisted" recall. Semantic memory extracts "program-style rules" from experience. This is the episodic-to-semantic consolidation pathway.

- **Experience replay in RL** -- The classic technique from DQN (Mnih et al., 2015). Agents store transitions (s, a, r, s') in a replay buffer and sample from it during learning. Prioritized experience replay weights sampling by TD-error (surprise). This is the computational analog of hippocampal replay.

### Design patterns for consolidation

**The consolidation cycle for armOS:**

```
[Short-term: Episode Buffer]
         |
         | (periodic consolidation, e.g., every hour or on idle)
         v
[Medium-term: Episodic Memory]
         |
         | (pattern extraction, e.g., daily or on threshold)
         v
[Long-term: Semantic Memory + Procedural Memory]
```

**Consolidation rules:**

1. **Episode buffer -> Episodic memory:** All episodes are immediately written to episodic memory. The buffer is just the write-ahead log.

2. **Episodic -> Semantic (knowledge extraction):**
   - If the same object is seen at the same location 3+ times, create/strengthen a `located_at` edge
   - If a causal pattern repeats (action X causes outcome Y), create a causal edge
   - If an object property is observed consistently, add it to the knowledge node

3. **Episodic -> Procedural (skill refinement):**
   - After N successful completions of a skill, extract average parameters as a Procedure
   - If a procedure fails in a new context, fork it: create a context-specific variant
   - Update success_rate as a running average

4. **Forgetting:**
   - Episodes older than retention_days with importance < threshold are pruned
   - Knowledge edges with confidence < 0.1 are pruned
   - Procedures with use_count == 0 and age > 30 days are pruned
   - Immune patterns already have LRU pruning (existing code)

**Implementation: the "sleep" cycle.**
A citizen runs consolidation during idle periods (no active tasks). This is a background coroutine:

```python
async def consolidate_memory(self):
    """Run during idle periods. The robot's 'sleep' cycle."""
    # 1. Extract knowledge from recent episodes
    recent = self.episodic_memory.get_since(self._last_consolidation)
    for episode in recent:
        self._extract_knowledge(episode)
        self._refine_procedures(episode)

    # 2. Prune old, low-importance episodes
    self.episodic_memory.prune(max_age_days=7, min_importance=0.2)

    # 3. Decay confidence on stale knowledge
    self.semantic_memory.decay_stale(half_life_days=30)

    self._last_consolidation = time.time()
```

---

## Shared Fleet Memory <a id="shared-fleet-memory"></a>

### What the research says

How do multiple robots share what they have learned?

**Key papers:**

- **G-Memory** (Zhang et al., 2025) -- Multi-agent hierarchical memory. Insight graphs store generalizable knowledge that transfers across agents. Interaction graphs encode collaboration trajectories. This is the closest to what armOS needs.

- **Federated Multi-Agent Mapping** (Szatmari & Cauligi, 2024, arXiv:2404.02289) -- Agents jointly train a global map model *without transmitting raw data*. Model parameters are shared instead. 93.8% reduction in data transmission. This is the federated learning pattern.

- **Federated Learning for Social Robot Behaviors** (Checker et al., 2024, arXiv:2403.07586) -- Individual robots learn about unique environments while sharing patterns via FedAvg. "Rehearsal-based continual learning helps robots adapt to new situations without forgetting previously learned social norms."

- **Flow-FL** (Majcherczyk et al., 2020, arXiv:2010.08595) -- Federated learning framework for spatio-temporal predictions in connected robot teams.

- **Decentralized Federated RL** (Nair et al., 2022, arXiv:2207.09372) -- Mobile agents carry and aggregate Q-tables between robots. No central server needed.

### Design patterns for shared memory in armOS

armOS already has the transport layer (multicast + unicast) and the immune memory broadcast pattern. Shared memory extends this with three new message types:

**1. Knowledge gossip (lightweight, frequent):**
When a citizen learns something new (high-confidence knowledge edge), it broadcasts a compact summary:
```json
{
  "msg_type": "KNOWLEDGE_GOSSIP",
  "knowledge": {
    "subject": "object:red_block_1",
    "relation": "located_at",
    "object": "location:table_south",
    "confidence": 0.85,
    "timestamp": 1742140800
  }
}
```
Receiving citizens merge this into their own semantic memory, weighted by trust in the sender.

**2. Episode sharing (on request):**
A citizen can request relevant episodes from neighbors:
```json
{
  "msg_type": "EPISODE_REQUEST",
  "query": {
    "event_type": "pick",
    "context": {"object_type": "cup"},
    "max_results": 5
  }
}
```
The neighbor responds with matching episodes. This is the "I learned from robot-2 that..." pattern.

**3. Procedure sharing (rare, high-value):**
When a citizen achieves high success_rate on a procedure, it can offer it to neighbors:
```json
{
  "msg_type": "PROCEDURE_OFFER",
  "procedure": {
    "skill_name": "pick_cup",
    "success_rate": 0.92,
    "use_count": 47,
    "parameters": {"approach_angle": 30, "grip_force": 0.6}
  }
}
```

**Trust and provenance:** Every shared memory carries the source citizen's pubkey. Citizens weight shared knowledge by:
- Trust score of the sender (from the existing neighbor/contract system)
- How many independent citizens report the same knowledge
- Recency of the observation

**Conflict resolution:** When two citizens disagree (citizen A says red_block is at table_south, citizen B says table_north), the most recent observation with the highest sender trust wins. Both observations are kept with their timestamps, so the knowledge can be queried historically.

---

## Practical Implementations Survey <a id="practical-implementations"></a>

### MemGPT / Letta (arXiv:2310.08560)

The most directly relevant architecture for LLM-backed agents.

**Core idea:** Treat LLM context like virtual memory in an OS. The agent manages its own memory through explicit read/write operations across tiers:

- **Core memory:** Always in context. Small, critical information (who the user is, current goals). The agent can edit this directly.
- **Recall memory:** Conversation history. Searchable via timestamps and text queries. Analogous to episodic memory.
- **Archival memory:** Long-term storage with unlimited capacity. Searchable via embedding similarity. Analogous to semantic + procedural memory.

**Key insight:** The agent *itself* decides what to remember and what to forget. It has explicit `memory_insert`, `memory_search`, and `memory_replace` tools. This self-directed memory management is more flexible than hard-coded retention rules.

**Relevance to armOS:** Citizens could have a similar tier system. Core memory = genome + active state. Recall memory = episodic buffer. Archival memory = semantic knowledge graph + procedural library. The consolidation cycle is the mechanism that moves data between tiers.

### Voyager (arXiv:2305.16291)

**Pattern:** Skills as executable code in a growing library. The agent:
1. Gets a curriculum of increasingly complex tasks
2. Writes code to solve each task
3. Stores successful code in a skill library
4. Retrieves and composes skills for new tasks

**Key numbers:** 3.3x more unique items, 15.3x faster milestone completion.

**Relevance to armOS:** The "skill library as code" pattern maps to armOS procedures. Instead of Python code (appropriate for Minecraft), armOS stores parameter sets and trajectories. The curriculum / self-guided exploration pattern from LRLL is also relevant -- citizens could propose their own practice tasks.

### LangChain Memory

LangChain's memory module (now part of LangGraph) provides:
- **Conversation buffer memory:** Raw history in context
- **Summary memory:** LLM-generated summaries of conversation history
- **Entity memory:** Extracts and tracks entities mentioned in conversation
- **Knowledge graph memory:** Builds a simple triple store from conversation

**Relevance to armOS:** The entity memory and knowledge graph memory patterns map directly to semantic memory. The summary memory pattern maps to episode consolidation (compress raw events into summaries).

### SayCan (Ahn et al., 2022)

**Pattern:** Ground language in affordances. The LLM proposes actions; value functions filter for what's actually possible. The value functions are trained per-skill and encode procedural knowledge ("how well can I do this action in this state?").

**Relevance to armOS:** The skill value function pattern could augment the SkillTree. Instead of just XP thresholds, each skill gets a context-dependent confidence score: "I can do pick_cup with 0.92 confidence when approaching from the right, but only 0.45 from the left."

### RACAS (Ashley et al., 2026, arXiv:2603.05621)

**Pattern:** Three LLM/VLM modules (Monitors, Controller, Memory Curator) communicating through natural language. The Memory Curator manages what the system remembers across diverse robot platforms.

**Relevance to armOS:** The Memory Curator role could be a citizen responsibility -- a dedicated memory management agent, or a responsibility of the governor.

### Lilian Weng's Agent Memory Framework

**Three retrieval dimensions** (from the Generative Agents paper, Park et al. 2023):
1. **Recency:** Exponential decay -- recent memories surface first
2. **Importance:** LLM-scored significance (1-10 scale)
3. **Relevance:** Embedding similarity to current query

The final retrieval score is a weighted combination of all three. This is the standard approach for agent memory retrieval and should be the default for armOS.

---

## Proposed armOS Memory Architecture <a id="proposed-architecture"></a>

### Overview

```
                    +-------------------+
                    |   Citizen Agent   |
                    +-------------------+
                    |                   |
            +-------+-------+   +------+------+
            | Working State |   | Genome      |
            | (in-memory)   |   | (persisted) |
            +-------+-------+   +------+------+
                    |                   |
        +-----------+-----------+-------+
        |           |           |
   +----+----+ +----+----+ +---+----+
   |Episodic | |Semantic | |Proced- |
   |Memory   | |Memory   | |ural    |
   |         | |         | |Memory  |
   +----+----+ +----+----+ +---+----+
        |           |           |
        +-----------+-----------+
                    |
            +-------+-------+
            | Consolidation |
            | Engine        |
            +-------+-------+
                    |
            +-------+-------+
            | Fleet Sharing |
            | (Mycelium)    |
            +---------------+
```

### New module: `memory.py`

A single module that encapsulates all three memory types and the consolidation engine.

```python
class CitizenMemory:
    """Unified memory system for a citizen agent."""

    def __init__(self, citizen_name: str):
        self.citizen_name = citizen_name
        self.episodic = EpisodicMemory(citizen_name)
        self.semantic = SemanticMemory(citizen_name)
        self.procedural = ProceduralMemory(citizen_name)
        self._last_consolidation = 0.0

    # --- Episodic interface ---
    def record_episode(self, event_type, description, context, outcome, importance=None): ...
    def recall_episodes(self, query, limit=10): ...
    def recall_recent(self, hours=1): ...
    def recall_failures(self, skill_name=None, limit=5): ...

    # --- Semantic interface ---
    def learn_fact(self, subject, relation, obj, confidence=0.8): ...
    def query_knowledge(self, subject=None, relation=None, obj=None): ...
    def object_location(self, object_id): ...

    # --- Procedural interface ---
    def get_best_procedure(self, skill_name, context): ...
    def record_procedure_outcome(self, procedure_id, success, duration): ...
    def add_procedure(self, skill_name, parameters, context_conditions): ...

    # --- Consolidation ---
    async def consolidate(self): ...

    # --- Fleet sharing ---
    def get_shareable_knowledge(self, since=None): ...
    def merge_remote_knowledge(self, knowledge, source_trust): ...
    def get_shareable_episodes(self, query): ...
    def merge_remote_episode(self, episode, source_citizen): ...

    # --- Persistence ---
    def save(self): ...
    def load(self): ...
```

### Integration with existing systems

| Existing System | Integration Point |
|----------------|-------------------|
| `Citizen.__init__` | Add `self.memory = CitizenMemory(name)` |
| `Genome` | Add `memory_stats` field (episode count, knowledge node count, procedure count) |
| `SkillTree.award_xp` | After XP award, call `memory.record_episode(...)` |
| `ImmuneMemory.add` | Immune patterns become episodes + semantic knowledge |
| `EmotionalState` | Emotional valence modulates episode importance |
| `MyceliumNetwork` | Add `KNOWLEDGE_GOSSIP`, `EPISODE_REQUEST`, `PROCEDURE_OFFER` message types |
| `persistence.py` | Add `save_memory` / `load_memory` functions |
| Heartbeat loop | Run `consolidate()` during idle periods |

### Persistence format

All memory persists as JSON in `~/.citizenry/`:

```
~/.citizenry/
  surface-arm.genome.json          # Existing
  surface-arm.neighbors.json       # Existing
  surface-arm.episodes.json        # NEW: episodic memory
  surface-arm.knowledge.json       # NEW: semantic knowledge graph
  surface-arm.procedures.json      # NEW: procedural memory
```

### Retrieval scoring

Following the Generative Agents pattern (Park et al. 2023), every memory retrieval uses a composite score:

```python
def retrieval_score(memory, query, now):
    recency = exp(-DECAY_RATE * (now - memory.timestamp))
    importance = memory.importance
    relevance = cosine_similarity(query_embedding, memory.embedding)
    return ALPHA * recency + BETA * importance + GAMMA * relevance
```

For armOS citizens without GPU (like the Surface Pro 7), skip the embedding-based relevance and use tag/keyword matching instead. Embeddings can be added later when citizens have access to a model server.

**Simplified retrieval for edge devices:**

```python
def retrieval_score_simple(memory, query_tags, now):
    recency = exp(-0.01 * (now - memory.timestamp) / 3600)  # hourly decay
    importance = memory.importance
    tag_overlap = len(set(memory.tags) & set(query_tags)) / max(len(query_tags), 1)
    return 0.3 * recency + 0.3 * importance + 0.4 * tag_overlap
```

---

## Implementation Plan <a id="implementation-plan"></a>

### Phase 1: Episodic Memory (simplest, highest value)

**Files:** `citizenry/memory.py` (new), modify `citizen.py`, `persistence.py`

1. Implement `Episode` dataclass and `EpisodicMemory` class
2. Write `record_episode()` -- append to in-memory list + persist
3. Write `recall_episodes()` -- tag-based search with recency/importance scoring
4. Wire into `Citizen` base class: record episodes on task start/complete/fail
5. Add persistence: `save_episodes()` / `load_episodes()` in JSON

**Estimated effort:** 200-300 lines. One session.

### Phase 2: Semantic Memory

1. Implement `KnowledgeNode`, `KnowledgeEdge`, `SemanticMemory`
2. Wire location tracking: when a citizen observes an object, update knowledge graph
3. Add confidence decay on stale edges
4. Persistence as JSON

**Estimated effort:** 200-300 lines. One session.

### Phase 3: Procedural Memory

1. Implement `Procedure`, `ProceduralMemory`
2. Wire into `SkillTree`: after task completion, update procedure parameters
3. Add context-based procedure selection
4. Persistence as JSON

**Estimated effort:** 150-250 lines. One session.

### Phase 4: Consolidation Engine

1. Implement the episodic-to-semantic extraction rules
2. Implement the episodic-to-procedural refinement rules
3. Add forgetting/pruning
4. Wire as a background coroutine on the citizen event loop

**Estimated effort:** 150-200 lines. One session.

### Phase 5: Fleet Memory Sharing

1. Add `KNOWLEDGE_GOSSIP`, `EPISODE_REQUEST`, `PROCEDURE_OFFER` to `protocol.py`
2. Implement trust-weighted merge in `CitizenMemory`
3. Wire into the existing multicast/unicast transport

**Estimated effort:** 200-300 lines. One session.

---

## References <a id="references"></a>

### Core Papers

| Paper | Year | Key Contribution |
|-------|------|-----------------|
| RoboMemory (arXiv:2508.01415) | 2025 | Unified 4-memory architecture (Spatial, Temporal, Episodic, Semantic) |
| HIMM (arXiv:2602.15513) | 2026 | Disentangled episodic/semantic with program-style rule extraction |
| G-Memory (arXiv:2506.07398) | 2025 | 3-tier graph hierarchy for multi-agent memory |
| AutoAgent (arXiv:2603.09716) | 2026 | Elastic memory orchestration with trajectory compression |
| The AI Hippocampus (arXiv:2601.09113) | 2026 | Survey: implicit, explicit, agentic memory taxonomy |
| MemGPT (arXiv:2310.08560) | 2023 | OS-inspired virtual context management with self-directed memory |
| Voyager (arXiv:2305.16291) | 2023 | Skill library as executable code, lifelong learning |
| MrSteve (arXiv:2411.06736) | 2024 | What-Where-When episodic memory (ICLR 2025) |
| Ella (arXiv:2506.24019) | 2025 | Lifelong multimodal episodic + semantic memory |
| 3DLLM-Mem (arXiv:2505.22657) | 2025 | Working memory queries episodic memory for 3D reasoning |
| TriVLA (arXiv:2507.01424) | 2025 | Episodic world model at 36 Hz |
| Mind Palace (arXiv:2507.12846) | 2025 | Scene-graph episodic encoding with value-of-information retrieval |
| MEMENTO (arXiv:2505.16348) | 2025 | Hierarchical KG for personalized embodied agents |

### Skill Learning Papers

| Paper | Year | Key Contribution |
|-------|------|-----------------|
| LRLL (arXiv:2406.18746) | 2024 | Lifelong robot library learning with soft memory + skill abstraction |
| LOTUS (arXiv:2311.02058) | 2023 | Continual imitation learning with unsupervised skill discovery |
| AtomicVLA (arXiv:2603.07648) | 2026 | Atomic skill abstractions via Mixture-of-Experts |
| SayCan (arXiv:2204.01691) | 2022 | Grounding language in affordance value functions |
| Code as Policies (arXiv:2209.07753) | 2022 | LLM-generated robot policy code |

### Fleet Learning Papers

| Paper | Year | Key Contribution |
|-------|------|-----------------|
| Federated Multi-Agent Mapping (arXiv:2404.02289) | 2024 | 93.8% data reduction via federated implicit neural maps |
| FL for Social Robot Behaviors (arXiv:2403.07586) | 2024 | FedAvg + rehearsal-based continual learning |
| Decentralized Federated RL (arXiv:2207.09372) | 2022 | Mobile agents carry and aggregate Q-tables, no central server |
| Flow-FL (arXiv:2010.08595) | 2020 | Spatio-temporal predictions in connected robot teams |
| RACAS (arXiv:2603.05621) | 2026 | Memory Curator module for cross-platform robot control |

### Architecture References

| System | Key Pattern |
|--------|------------|
| Letta/MemGPT | Self-directed memory management across core/recall/archival tiers |
| LangChain/LangGraph Memory | Entity memory, knowledge graph memory, summary memory |
| Generative Agents (Park et al. 2023) | Recency + Importance + Relevance retrieval scoring |
| Lilian Weng's survey | MIPS algorithms (LSH, ANNOY, HNSW, FAISS, ScaNN) for memory retrieval |
