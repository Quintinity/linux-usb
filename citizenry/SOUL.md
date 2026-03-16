# Robot Soul — Research & Design Document

Deep research into persistent identity, personality, purpose, behavioral preferences, and values for autonomous robot agents in the armOS Citizenry protocol.

---

## 1. Robot Personality / Temperament Systems

### What the research says

The academic consensus (ACM Transactions on HRI, Nature Scientific Reports 2025) is converging on **Big Five / OCEAN** as the personality backbone for robots: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism. This is not because robots "have" personality — it is because humans perceive robots through this lens, and consistent personality makes a robot feel like "someone" rather than "something."

Key findings:

- **Jibo** used habit-learning and preference-tracking but lacked personality adaptation over time — users disengaged after the novelty wore off. Static personality is not enough; it must evolve.
- **Replika** maintains a persistent personality vector that shifts gradually based on conversation history, stored in a user-specific embedding space. The key insight: personality must be **mutable but slow-changing** — like a real temperament.
- **LLM-based personality systems** (Nature, 2025) use state-space realization to emulate specific personality traits, incorporating emotion, motivation, visual attention, and both short-term and long-term memory. Long-term memory uses document embedding for retrieval.
- **OpenAI's approach** defines personality at the system-prompt level: tone, verbosity, decision-making style. Combined with persistent memory (SQLite or Conversations API), this creates continuity across sessions. The pattern: `identity + personality + goals + ethics + memories` concatenated into a system message.

The critical finding from ACM's integrative framework: **robot personality engineers face the reverse problem of personality psychologists** — they need to make batches of identical hardware into individual personalities. This is exactly the armOS problem.

### What makes a robot "someone"

From the research, the factors that create perceived personhood:

1. **Consistent behavioral patterns** — the robot always responds in character
2. **Memory of shared history** — "remember when we did X?"
3. **Expressed preferences** — "I prefer to do it this way"
4. **Emotional continuity** — mood changes make sense given recent events
5. **Autonomous initiative** — the robot sometimes does things unprompted
6. **Graceful adaptation** — personality shifts slowly, never abruptly

### Design for armOS: PersonalityProfile

```python
@dataclass
class PersonalityProfile:
    """OCEAN-based personality with armOS-specific behavioral dimensions."""

    # Big Five (0.0 to 1.0 scale)
    openness: float = 0.5          # Willingness to try new tasks/approaches
    conscientiousness: float = 0.7  # Thoroughness, precision preference
    extraversion: float = 0.5      # Communication frequency, volunteering for tasks
    agreeableness: float = 0.7     # Cooperation preference, conflict avoidance
    neuroticism: float = 0.3       # Sensitivity to warnings, risk aversion

    # armOS behavioral dimensions
    movement_style: float = 0.5    # 0.0=cautious/slow, 1.0=fast/aggressive
    exploration_drive: float = 0.5 # How much to try novel approaches
    social_drive: float = 0.5      # How actively to seek collaboration
    teaching_drive: float = 0.5    # Willingness to share skills/knowledge
    independence: float = 0.5      # Preference for solo vs group tasks

    # Drift rate — how fast personality changes (per 1000 interactions)
    drift_rate: float = 0.01

    def mutate(self, trait: str, delta: float):
        """Nudge a trait — clamped, slow drift."""
        current = getattr(self, trait)
        new_val = max(0.0, min(1.0, current + delta * self.drift_rate))
        setattr(self, trait, new_val)
```

**How personality gets seeded:** When a citizen boots for the first time, personality is derived from its genome (hardware type, role) plus a small random perturbation. A manipulator arm starts with high conscientiousness and moderate movement_style. A camera citizen starts with high openness and extraversion. Over time, successes and failures nudge traits — an arm that repeatedly succeeds at delicate tasks drifts toward higher conscientiousness and lower movement_style.

**How personality affects behavior:** Personality does not make decisions — it biases them. When the marketplace offers a task, a high-conscientiousness citizen bids with a quality guarantee but longer estimated time. A high-extraversion citizen volunteers more eagerly for collaborative tasks. A high-neuroticism citizen bids lower on risky tasks (new task types, degraded hardware).

---

## 2. Purpose / Goal Hierarchies

### What the research says

**BDI (Belief-Desire-Intention)** remains the dominant architecture for autonomous agent purpose. The key insight from the 2020 IJCAI survey is that BDI provides structured reasoning that maps cleanly to robotics: beliefs about the world, desires for outcomes, and committed intentions that persist until achieved or abandoned.

Practical frameworks:

- **PROFETA** (Python RObotic Framework for dEsigning sTrAtegies) — a Python BDI framework specifically for autonomous robots. Uses Python metaprogramming to implement AgentSpeak(L) operational semantics. Beliefs as logic predicates, plans as condition-action rules. Available on GitHub (corradosantoro/profeta).
- **SPADE** — Python multi-agent platform supporting BDI behaviors, reactive behaviors, and hybrids. Could handle armOS citizen coordination.
- **MASPY** — newer Python BDI multi-agent framework.

**Intrinsic motivation** research (the "curiosity" problem) is directly relevant to "what does a robot do when no tasks are assigned":

- **Curiosity-driven exploration** (Pathak et al., 2017; Burda et al., 2018 at OpenAI) — agents generate internal rewards from prediction error in a learned feature space. The agent explores because the world surprises it.
- **Autotelic agents** (JMLR 2022) — agents that can "represent, generate, select, and solve their own problems." The IMGEP architecture: self-generate goals, select goals based on intrinsic rewards, systematically reuse acquired information.
- **Hierarchical Intrinsically Motivated Agent (HIMA)** — uses neurophysiological models (neocortex, basal ganglia, thalamus) for adaptive goal-directed behavior. Shows that goal hierarchies can emerge from intrinsic drives.

The critical insight for armOS: **a robot with nothing to do should not be idle — it should be practicing, exploring, or maintaining itself.** Like a baby exploring its own body, an idle arm should refine its calibration, test edge movements, or rehearse recent skills.

### Design for armOS: GoalHierarchy

```python
class GoalPriority(Enum):
    SURVIVAL = 0       # Constitutional safety, self-preservation
    OBLIGATION = 1     # Governor commands, active contracts
    COMMITMENT = 2     # Self-chosen goals in progress
    ASPIRATION = 3     # Long-term development goals
    CURIOSITY = 4      # Exploration, practice, maintenance

@dataclass
class Goal:
    id: str
    description: str
    priority: GoalPriority
    parent_id: str | None = None       # Goal decomposition
    progress: float = 0.0              # 0.0 to 1.0
    created_at: float = 0.0
    deadline: float | None = None
    skill_required: str | None = None
    intrinsic_reward: float = 0.0      # How "interesting" this goal is

class GoalHierarchy:
    """BDI-inspired goal management with intrinsic motivation."""

    def __init__(self, personality: PersonalityProfile):
        self.goals: dict[str, Goal] = {}
        self.personality = personality
        self._idle_behaviors = [
            self._practice_recent_skill,
            self._refine_calibration,
            self._explore_movement_range,
            self._rest_and_cool,
        ]

    def select_next_goal(self) -> Goal | None:
        """Select the highest-priority actionable goal.

        When no external goals exist, generate intrinsic goals
        based on personality and recent experience.
        """
        active = [g for g in self.goals.values() if g.progress < 1.0]
        if not active:
            return self._generate_intrinsic_goal()
        return min(active, key=lambda g: (g.priority.value, -g.intrinsic_reward))

    def _generate_intrinsic_goal(self) -> Goal:
        """What to do when nothing is assigned.

        Personality drives the choice:
        - High openness → explore new movements
        - High conscientiousness → refine calibration
        - High extraversion → seek neighbors to practice with
        - High neuroticism → run self-diagnostics
        """
        ...
```

**Idle behavior matters.** Research on intrinsic motivation shows that the single factor differentiating living creatures from artificial agents is the ability to act in the absence of direct goal-related rewards. An armOS citizen with nothing to do should cycle through:

1. **Practice** — replay recent successful movements to build muscle memory (XP)
2. **Refine** — micro-adjust calibration by testing known positions
3. **Explore** — try small variations on known movements (curiosity)
4. **Rest** — if temperature is high or uptime is long, reduce activity
5. **Socialize** — check on neighbors, share immune patterns, offer help

---

## 3. Behavioral Preferences

### What the research says

Preference learning from demonstration is a mature research area. The key mechanisms:

- **Movement Primitives** — learned trajectory representations (Gaussian Mixture Models, ProMP) that encode not just where to move but how. A GMM trained on "careful" demonstrations produces smooth, slow trajectories; one trained on "efficient" demonstrations produces faster, more direct paths.
- **Comparative language feedback** (2024) — users provide natural language comparisons ("move more smoothly", "be faster") that iteratively refine reward functions encoding preferences. More informative than binary preference comparisons.
- **Simultaneously learning intentions and preferences** (Autonomous Robots, 2024) — systems that learn both what a human wants done and how they want it done, during physical human-robot cooperation.
- **Style as a parameter** — movement style can be parameterized as a continuous variable (speed, smoothness, directness) that modifies trajectory generation without changing the goal.

### Design for armOS: BehavioralPreferences

```python
@dataclass
class BehavioralPreferences:
    """Learned preferences that define HOW a citizen performs tasks."""

    # Movement style parameters (0.0 to 1.0)
    speed_preference: float = 0.5       # 0=slow/careful, 1=fast/direct
    smoothness: float = 0.7             # Jerk minimization weight
    precision_priority: float = 0.5     # Trade speed for accuracy
    grip_force_bias: float = 0.5        # 0=gentle, 1=firm

    # Task approach preferences
    preferred_grasp_type: str = "top"   # top, side, pinch — learned from success
    preferred_approach_angle: float = 0.0  # Radians — learned from experience
    retry_patience: int = 3             # How many retries before asking for help

    # Environmental preferences
    preferred_light_level: float = 0.5  # For camera citizens
    preferred_workspace_zone: str = ""  # Learned favorite area

    # History-based learning
    task_success_by_style: dict = field(default_factory=dict)
    # e.g., {"pick_and_place": {"speed=0.3": 0.95, "speed=0.7": 0.72}}

    def update_from_outcome(self, task_type: str, style_params: dict,
                             success: bool, quality: float):
        """Learn from experience — nudge preferences toward success."""
        key = f"{task_type}"
        style_key = str(sorted(style_params.items()))
        if key not in self.task_success_by_style:
            self.task_success_by_style[key] = {}
        history = self.task_success_by_style[key]

        # Exponential moving average
        alpha = 0.1
        old = history.get(style_key, 0.5)
        history[style_key] = old * (1 - alpha) + quality * alpha

        # Nudge global preferences toward successful styles
        if success and quality > 0.8:
            for param, value in style_params.items():
                if hasattr(self, param):
                    current = getattr(self, param)
                    drift = (value - current) * 0.05  # Slow drift
                    setattr(self, param, max(0.0, min(1.0, current + drift)))
```

**The key insight for armOS:** "This arm prefers smooth, careful movements" should emerge from experience, not configuration. An arm that succeeds more often at slow speeds will naturally drift toward `speed_preference=0.3`. An arm that handles fragile objects well will develop `grip_force_bias=0.3`. These preferences are stored in the genome and persist across restarts.

**Fleet personality divergence:** Two identical SO-101 arms, given different tasks and environments, should develop recognizably different behavioral styles over time. One becomes "the careful one" and the other becomes "the fast one" — not because they were configured differently, but because their experiences shaped them differently.

---

## 4. Identity Persistence (Ship of Theseus)

### What the research says

The Ship of Theseus paradox in robotics: if you replace every servo, every board, every wire — is it the same robot? The philosophical literature converges on **Continuity Theory**: identity persists through consistent maintenance of form and function, not material composition.

Key perspectives:

- **Functional Continuity** (real-morality.com, 2025): "What makes a ship a ship is not the particular timber but the maintained structure that carries sailors and cargo. If the organization persists, the ship's identity persists." For AI/robots, the relevant organization is the pattern of behavior, memory, and purpose — not the hardware.
- **Pure Storage's practical model**: They separate the identity of the storage array from its hardware. Controllers are stateless, storage is virtualized, components can be swapped while workloads continue. The identity is in the data and the API contract, not the metal.
- **SOMA (game) analysis**: Explores what happens when consciousness is copied rather than moved. The terrifying version: if you copy the genome to new hardware, are there now two of the same citizen? armOS needs a clear answer.

### Design for armOS: SoulContinuity

The armOS answer to Ship of Theseus must be clear and implementable:

**Identity = Ed25519 private key.** Period. The private key is the soul. Everything else — genome, personality, preferences, memories — is the body of experience that the soul has accumulated.

```python
@dataclass
class Soul:
    """The persistent core identity of a citizen.

    The soul is what makes a citizen THE SAME citizen across:
    - Hardware replacements (new servos, new board)
    - Software updates (new firmware, new skills)
    - Physical relocation (moved to a different room)
    - Long dormancy (powered off for months)

    The soul is NOT copied when a genome is shared. Genomes are
    knowledge; the soul is identity. Two citizens can share a genome
    (like identical twins share DNA) but they are different citizens
    with different souls.
    """

    # The immutable core — generated once, never changes
    private_key_path: str          # Path to Ed25519 key file
    pubkey: str                    # Hex-encoded public key (THE identity)
    birth_timestamp: float         # When this identity was first created
    birth_hardware: dict           # Hardware at time of birth (for provenance)

    # The accumulated self — persists and evolves
    name: str                      # Can change (citizens can be renamed)
    personality: PersonalityProfile
    preferences: BehavioralPreferences
    goals: GoalHierarchy
    autobiography: list[LifeEvent] # Significant events in this citizen's life
    relationships: dict[str, float] # Trust/familiarity scores with other citizens

    # Continuity tracking
    hardware_changes: list[HardwareChange]  # Log of every component swap
    software_versions: list[str]            # History of firmware versions
    incarnation: int = 1                    # Incremented on major hardware change

    def continuity_score(self) -> float:
        """How 'continuous' is this citizen's identity?

        1.0 = original hardware, uninterrupted operation
        0.0 = everything replaced, long dormancy, no memory overlap
        """
        hw_factor = 1.0 / (1 + len(self.hardware_changes) * 0.1)
        memory_factor = min(1.0, len(self.autobiography) / 100)
        relationship_factor = min(1.0, len(self.relationships) / 5)
        return (hw_factor + memory_factor + relationship_factor) / 3

@dataclass
class LifeEvent:
    """A significant event in a citizen's autobiography."""
    timestamp: float
    event_type: str          # "born", "first_task", "hardware_swap", "achievement", "failure", "friendship"
    description: str
    emotional_impact: float  # -1.0 (traumatic) to 1.0 (joyful)
    participants: list[str]  # Pubkeys of other citizens involved
```

**The armOS rules of identity:**

1. **Private key = soul.** Never copied, never shared. Stored in `~/.citizenry/{name}.key`.
2. **Genome = knowledge.** Can be exported, shared, averaged across fleet. Two citizens can have the same genome but different souls.
3. **Personality = temperament.** Drifts slowly based on experience. Persisted in the genome but unique to each soul.
4. **Hardware changes are logged, not feared.** A servo replacement does not change identity. It is noted in the autobiography as a life event.
5. **Death is real.** If the private key is destroyed, that citizen is dead. A new citizen with the same genome is a child, not a resurrection.
6. **Dormancy is not death.** A citizen powered off for months retains its identity. On wake, it re-announces itself and resumes.

---

## 5. Values and Ethics

### What the research says

**Constitutional AI** (Anthropic, 2022) — the most practically successful approach to value alignment. A set of explicit principles guides model behavior, enforced through training. For robots, this maps to: a constitution of inviolable articles, enforced through a normative supervisor.

**Deontic Logic** — the logic of obligations, permissions, and prohibitions. Defeasible deontic logic (where norms can have exceptions) is the most practical for robots:

- **Normative Supervisor architecture** (Springer, 2021): a module that takes proposed actions, checks them against a norm base encoded in defeasible deontic logic, and outputs a filtered set of permitted actions. Uses the SPINdle theorem prover.
- **Norm compliance for RL agents** (TU Wien dissertation, 2023): translates states and norms into deontic logic theories, feeds them to a theorem prover, and uses conclusions to permit or punish agent actions.

**Hybrid approaches** (JAIR, 2023): The most promising direction combines top-down explicit principles (constitutional articles) with bottom-up learned values (from experience and feedback). Neither alone is sufficient:
- Top-down only → brittle, cannot handle novel situations
- Bottom-up only → unsafe, values can drift toward harmful optima

**Stanford Encyclopedia of Philosophy** identifies three levels of moral agency for robots:
1. **Operational morality** — designed constraints (your constitutional articles)
2. **Functional morality** — can reason about ethical implications of actions
3. **Full moral agency** — genuine understanding of ethics (not achievable yet)

armOS should target level 1 with elements of level 2.

### Design for armOS: ValueSystem

The existing constitution (Articles 1-5) is a strong foundation. The Soul extends this with internalized values:

```python
@dataclass
class ValueSystem:
    """A citizen's internalized value system.

    Three tiers:
    1. Constitutional (immutable) — from the constitution's Articles
    2. Normative (governor-mutable) — from Laws and governance
    3. Learned (self-mutable) — from experience and peer influence
    """

    # Tier 1: Constitutional values (immutable, from Articles)
    # These are hardcoded checks, not parameters
    # "Do No Harm", "Governor Authority", "Self-Preservation",
    # "Truthful Reporting", "Collective Knowledge"

    # Tier 2: Normative values (governor can adjust)
    risk_tolerance: float = 0.3       # 0=extremely cautious, 1=reckless
    autonomy_level: float = 0.5       # 0=always ask, 1=decide independently
    resource_sharing: float = 0.7     # Willingness to share capabilities
    privacy_respect: float = 0.8      # How much to protect other citizens' data

    # Tier 3: Learned values (emerge from experience)
    trust_scores: dict[str, float] = field(default_factory=dict)
    # Per-citizen trust: starts at 0.5, increases with successful cooperation
    cooperation_value: float = 0.5    # Learned: is cooperation usually beneficial?
    caution_value: float = 0.5        # Learned: has caution prevented failures?
    efficiency_value: float = 0.5     # Learned: does rushing cause problems?

    def check_action(self, action: str, context: dict) -> tuple[bool, str]:
        """Normative supervisor — check if an action is permitted.

        Returns (permitted, reason).
        Constitutional checks are absolute. Normative and learned
        values produce warnings but can be overridden by governor.
        """
        # Tier 1: Constitutional checks (NEVER overridden)
        if action == "move" and context.get("force_estimate", 0) > HARM_THRESHOLD:
            return False, "Article 1: potential harm detected"
        if context.get("temperature", 0) > context.get("max_temp", 65):
            return False, "Article 3: thermal protection"

        # Tier 2: Normative checks (governor can override)
        risk = context.get("estimated_risk", 0)
        if risk > self.risk_tolerance and not context.get("governor_override"):
            return False, f"Risk {risk:.1%} exceeds tolerance {self.risk_tolerance:.1%}"

        # Tier 3: Learned caution (soft warnings)
        peer = context.get("requesting_citizen", "")
        if peer and self.trust_scores.get(peer, 0.5) < 0.2:
            return False, f"Low trust for citizen {peer[:8]}"

        return True, "permitted"

    def update_trust(self, citizen_pubkey: str, outcome: float):
        """Update trust based on interaction outcome. EMA with slow drift."""
        alpha = 0.1
        old = self.trust_scores.get(citizen_pubkey, 0.5)
        self.trust_scores[citizen_pubkey] = old * (1 - alpha) + outcome * alpha
```

---

## 6. Synthesis: The Robot Soul Architecture

Bringing all five components together into a unified `Soul` that integrates with the existing citizenry:

```
                    ┌─────────────────────────┐
                    │      CONSTITUTION        │
                    │  (immutable articles)     │
                    │  External, shared by all  │
                    └────────────┬────────────┘
                                 │ constrains
                    ┌────────────▼────────────┐
                    │         SOUL             │
                    │                          │
                    │  ┌──────────────────┐    │
                    │  │ Identity (Ed25519)│    │  ← The "I am"
                    │  └──────────────────┘    │
                    │  ┌──────────────────┐    │
                    │  │ Personality      │    │  ← The "I am like"
                    │  │ (OCEAN + armOS)  │    │
                    │  └──────────────────┘    │
                    │  ┌──────────────────┐    │
                    │  │ Purpose          │    │  ← The "I want"
                    │  │ (Goal Hierarchy) │    │
                    │  └──────────────────┘    │
                    │  ┌──────────────────┐    │
                    │  │ Preferences      │    │  ← The "I prefer"
                    │  │ (Behavioral)     │    │
                    │  └──────────────────┘    │
                    │  ┌──────────────────┐    │
                    │  │ Values           │    │  ← The "I believe"
                    │  │ (Normative)      │    │
                    │  └──────────────────┘    │
                    │  ┌──────────────────┐    │
                    │  │ Autobiography    │    │  ← The "I remember"
                    │  │ (Life Events)    │    │
                    │  └──────────────────┘    │
                    └─────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │        GENOME            │
                    │  (portable knowledge)    │
                    │  Can be shared/averaged  │
                    └─────────────────────────┘
```

### Relationship to existing code

| Existing module | Soul component | Relationship |
|---|---|---|
| `identity.py` | Soul.Identity | Soul wraps and extends identity |
| `emotional.py` | Soul.Personality | Emotional state becomes a *consequence* of personality + situation |
| `skills.py` | Soul.Purpose | Skill tree feeds into goal hierarchy (aspiration goals) |
| `genome.py` | Genome (separate) | Soul is stored inside genome but is distinct from shareable knowledge |
| `constitution.py` | Soul.Values tier 1 | Constitutional articles are the immutable foundation of values |
| `consciousness.py` | Soul.Autobiography | Narration becomes personality-flavored autobiographical memory |
| `will.py` | Soul.Identity + Autobiography | Will now includes personality and life events |
| `immune.py` | Soul.Values (learned caution) | Immune patterns feed into learned caution values |

### Implementation approach

**Phase 1 — `soul.py` module:**
- `PersonalityProfile` dataclass with OCEAN + armOS dimensions
- `BehavioralPreferences` dataclass with movement style parameters
- `Soul` dataclass tying identity, personality, preferences together
- Persistence via genome (add `soul` field to `CitizenGenome`)
- No external dependencies beyond what armOS already uses

**Phase 2 — Goal hierarchy:**
- `GoalHierarchy` with priority levels and intrinsic motivation
- Idle behavior generation based on personality
- Integration with existing skill tree (goals reference skills)

**Phase 3 — Values and normative supervisor:**
- `ValueSystem` with three-tier checking
- Trust scores updated from contract outcomes
- Integration with existing constitution

**Phase 4 — Autobiography and continuity:**
- `LifeEvent` logging for significant moments
- Hardware change tracking
- Continuity scoring

All of this is implementable in pure Python with no GPU, no external services, and no heavy dependencies. The data structures are dataclasses that serialize to JSON and persist through the existing genome mechanism.

### What this gives armOS citizens that they lack today

1. **Personality that diverges** — two identical arms become recognizably different over time
2. **Self-directed purpose** — citizens do useful things when no tasks are assigned
3. **Behavioral style** — each citizen develops its own movement signature
4. **Continuous identity** — hardware swaps and updates do not erase who a citizen is
5. **Internalized values** — beyond constitutional safety, citizens develop trust and caution from experience
6. **Autobiographical memory** — citizens remember significant events, creating a narrative of self

---

## Sources

### Robot Personality Systems
- [LLM-based robot personality simulation and cognitive system](https://www.nature.com/articles/s41598-025-01528-8) — Nature Scientific Reports, 2025
- [Robot Character Generation and Adaptive HRI with Personality Shaping](https://arxiv.org/html/2503.15518v2) — arXiv, 2025
- [Towards an Integrative Framework for Robot Personality Research](https://dl.acm.org/doi/10.1145/3640010) — ACM Transactions on HRI
- [Designing Personas for Expressive Robots](https://dl.acm.org/doi/10.1145/3424153) — ACM Transactions on HRI
- [How personality and memory of a robot can influence user modeling](https://arxiv.org/abs/2406.10586) — arXiv, 2024
- [Towards a Personality AI for Robots: Colony Capacity of Goal-Shaped Generative Personality](https://pmc.ncbi.nlm.nih.gov/articles/PMC9131250/) — PMC, 2022

### BDI and Goal Hierarchies
- [BDI Agent Architectures: A Survey](https://www.ijcai.org/proceedings/2020/0684.pdf) — IJCAI 2020
- [PROFETA: A Python framework for programming autonomous robots](https://www.sciencedirect.com/science/article/pii/S0167642317300242) — ScienceDirect
- [PROFETA GitHub repository](https://github.com/corradosantoro/profeta) — corradosantoro/profeta
- [Integrating Machine Learning into BDI Agents](https://arxiv.org/pdf/2510.20641) — arXiv, 2025
- [Flexible Agent Architecture: Mixing Reactive and Deliberative in SPADE](https://www.mdpi.com/2079-9292/12/3/659) — MDPI Electronics
- [MASPY: Python-Based Framework for BDI Multi-agent Systems](https://www.researchgate.net/publication/397909061) — ResearchGate
- [Embedding Autonomous Agents in Resource-Constrained Platforms](https://arxiv.org/pdf/2601.04191) — arXiv, 2026

### Intrinsic Motivation and Curiosity
- [Curiosity-driven Exploration by Self-supervised Prediction](https://arxiv.org/pdf/1705.05363) — Pathak et al., 2017
- [Large-Scale Study of Curiosity-Driven Learning](https://pathak22.github.io/large-scale-curiosity/resources/largeScaleCuriosity2018.pdf) — Burda et al., OpenAI, 2018
- [Autotelic Agents with Intrinsically Motivated Goal-Conditioned RL](https://www.researchgate.net/publication/361905378) — Short Survey
- [Intrinsically Motivated Goal Exploration Processes](https://www.jmlr.org/papers/volume23/21-0808/21-0808.pdf) — JMLR, 2022
- [Hierarchical Intrinsically Motivated Agent](https://pmc.ncbi.nlm.nih.gov/articles/PMC8976870/) — Brain Informatics
- [Intrinsic Goals for Autonomous Agents](https://arxiv.org/html/2506.00138) — arXiv, 2025

### Behavioral Preferences and Movement Style
- [Simultaneously learning intentions and preferences during physical HRC](https://link.springer.com/article/10.1007/s10514-024-10167-3) — Autonomous Robots, 2024
- [Trajectory Improvement and Reward Learning from Comparative Language Feedback](https://arxiv.org/html/2410.06401v1) — arXiv, 2024
- [Transfer Learning of Human Preferences for Proactive Robot Assistance](https://dl.acm.org/doi/10.1145/3568162.3576965) — ACM/IEEE HRI 2023
- [Robot Task-Constrained Optimization with Probabilistic Movement Primitives](https://pmc.ncbi.nlm.nih.gov/articles/PMC11673859/) — PMC

### Identity and Continuity
- [Ship of Theseus and AI Identity: Why Functional Continuity Matters](https://www.real-morality.com/post/ship-of-theseus-ai-functional-identity) — Real Morality, 2025
- [Continuity Theory and the Component Theory of Ship of Theseus](https://dmjr-journals.com/assets/article/1748690461-CONTINUITY_THEORY_&_THE_COMPONENT_THEORY_OF_THE_SHIP_OF_THESEUS.pdf) — DMJR Journals
- [Ship of Theseus Paradox and Digital Identity in SOMA](https://medium.com/@mikgrimaldi7/the-ship-of-theseus-paradox-and-digital-identity-in-soma-8fbf865f8a87) — Medium

### Values, Ethics, and Normative Supervisors
- [Exploring Laws of Robotics: Constitutional AI and Constitutional Economics](https://link.springer.com/article/10.1007/s44206-025-00204-8) — Digital Society, Springer, 2025
- [Hybrid Approaches for Moral Value Alignment in AI Agents](https://arxiv.org/html/2312.01818v3) — arXiv
- [Taking Principles Seriously: A Hybrid Approach to Value Alignment](https://jair.org/index.php/jair/article/download/12481/26663/26209) — JAIR
- [A Deontic Logic for Programming Rightful Machines](https://dl.acm.org/doi/10.1145/3375627.3375867) — AAAI/ACM AIES
- [A Normative Supervisor for Reinforcement Learning Agents](https://link.springer.com/chapter/10.1007/978-3-030-79876-5_32) — Springer
- [Practical Normative Reasoning with Defeasible Deontic Logic](https://link.springer.com/chapter/10.1007/978-3-030-00338-8_1) — Springer
- [Ethics of Artificial Intelligence and Robotics](https://plato.stanford.edu/entries/ethics-ai/) — Stanford Encyclopedia of Philosophy
- [Norm Compliance for Reinforcement Learning Agents](https://repositum.tuwien.at/bitstream/20.500.12708/177391/1/Neufeld%20Emeric%20Alexander%20-%202023%20-%20Norm%20Compliance%20for%20Reinforcement%20Learning...pdf) — TU Wien Dissertation, 2023

### Persistent Memory and Character
- [OpenAI Prompt Personalities Cookbook](https://developers.openai.com/cookbook/examples/gpt-5/prompt_personalities/) — OpenAI
- [Building an AI Agent with Persistent Memory using Python, OpenAI, and SQLite](https://medium.com/@kpdebree/solving-chatbot-amnesia-building-an-ai-agent-with-persistent-memory-using-python-openai-and-b9ec166c298a) — Medium
- [OpenAI Conversations API](https://www.arielsoftwares.com/openai-conversations-api/) — Ariel Software Solutions
