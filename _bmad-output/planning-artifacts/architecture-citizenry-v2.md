---
project: armOS Citizenry v2.0
date: 2026-03-15
status: approved
---

# Architecture — armOS Citizenry v2.0: "Citizens Collaborate"

## Overview

v2.0 adds 8 new modules to the existing citizenry package. All new behavior is expressed through the existing 7-message protocol — no transport or protocol changes. The architecture follows the same patterns established in v1.5: asyncio event loop, UDP multicast + unicast, Ed25519 signing, JSON persistence.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SURFACE PRO 7 (Governor)                         │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   SurfaceCitizen     │  │  CameraCitizen   │  │  Dashboard   │  │
│  │   (governor)         │  │  (sensor)        │  │  (TUI)       │  │
│  │                      │  │                  │  │              │  │
│  │  ┌────────────────┐  │  │  OpenCV capture  │  │  Neighbors   │  │
│  │  │ TaskMarketplace│  │  │  Color detection │  │  Tasks       │  │
│  │  │ CompositionEng │  │  │  Frame capture   │  │  Skills      │  │
│  │  │ ContractMgr    │  │  └────────┬─────────┘  │  Contracts   │  │
│  │  │ ImmuneMemory   │  │           │             │  Warnings    │  │
│  │  │ MyceliumNet    │  │           │             │  Telemetry   │  │
│  │  │ GenomeManager  │  │           │             └──────────────┘  │
│  │  └────────────────┘  │           │                               │
│  │          │           │           │                               │
│  └──────────┼───────────┘           │                               │
│             │                       │                               │
│  ┌──────────▼───────────────────────▼────────────────────────────┐  │
│  │              Citizen Base Layer (citizen.py)                    │  │
│  │  Identity │ Heartbeat │ Discovery │ Presence │ Persistence     │  │
│  │  SkillTree │ Genome │ ImmuneMemory │ MyceliumNetwork           │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐  │
│  │              Transport Layer (transport.py)                    │  │
│  │  MulticastTransport (UDP 239.67.84.90:7770)                   │  │
│  │  UnicastTransport (UDP dynamic port)                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │ LAN │
┌─────────────────────────────┼─────┼─────────────────────────────────┐
│                     RASPBERRY PI 5 (Follower)                        │
│                                                                      │
│  ┌──────────────────────┐                                           │
│  │     PiCitizen        │                                           │
│  │   (manipulator)      │                                           │
│  │                      │                                           │
│  │  ┌────────────────┐  │                                           │
│  │  │ SkillTree      │  │                                           │
│  │  │ ContractMgr    │  │                                           │
│  │  │ ImmuneMemory   │  │                                           │
│  │  │ MyceliumNet    │  │                                           │
│  │  │ Genome         │  │                                           │
│  │  │ TaskExecutor   │  │                                           │
│  │  └────────────────┘  │                                           │
│  │          │           │                                           │
│  │  Feetech STS3215    │                                           │
│  │  Servo Bus          │                                           │
│  └──────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Dependency Graph

```
protocol.py ──────────────────────────────────────────── (unchanged, foundation)
identity.py ──────────────────────────────────────────── (unchanged)
transport.py ─────────────────────────────────────────── (unchanged)
constitution.py ──────────────────────────────────────── (unchanged)
persistence.py ───────────────────────────────────────── (extended: genome, immune, contracts)
mdns.py ──────────────────────────────────────────────── (unchanged)
telemetry.py ─────────────────────────────────────────── (unchanged)

skills.py ────────────────────────────────────────────── (NEW, standalone)
marketplace.py ───────────────────────────────────────── (NEW, standalone)
immune.py ────────────────────────────────────────────── (NEW, standalone)
mycelium.py ──────────────────────────────────────────── (NEW, standalone)
symbiosis.py ─────────────────────────────────────────── (NEW, standalone)
genome.py ──────────── depends on: persistence.py ────── (NEW)
composition.py ───────────────────────────────────────── (NEW, standalone)

citizen.py ─────────── depends on: all above ──────────── (EXTENDED)
  └── integrates: SkillTree, ImmuneMemory, MyceliumNetwork, Genome, ContractManager

surface_citizen.py ── depends on: citizen.py ──────────── (EXTENDED)
  └── integrates: TaskMarketplace, CompositionEngine

pi_citizen.py ─────── depends on: citizen.py ──────────── (EXTENDED)
  └── integrates: task bidding, skill-gated execution

camera_citizen.py ─── depends on: citizen.py ──────────── (NEW)
  └── OpenCV frame capture + color detection

dashboard.py ────────────────────────────────────────── (EXTENDED)
  └── new sections: tasks, skills, contracts, warnings
```

## Data Flow

### Task Auction Flow

```
Governor                          Arm-1                     Arm-2
   │                                │                         │
   │──── PROPOSE (task) ──────────►│◄────────────────────────│
   │     (multicast)               │                         │
   │                               │── evaluate ──►          │── evaluate ──►
   │                               │  capabilities?          │  capabilities?
   │                               │  skills?                │  skills?
   │                               │  health?                │  health?
   │                               │  load?                  │  load?
   │                               │                         │
   │◄── ACCEPT (bid) ─────────────│                         │
   │◄── ACCEPT (bid) ────────────────────────────────────────│
   │                                                          │
   │── select_winner() ──►                                   │
   │                                                          │
   │──── GOVERN (assign) ─────────►│                         │
   │                               │── execute task ──►      │
   │                               │                         │
   │◄── REPORT (complete) ────────│                         │
   │                               │                         │
   │── award_xp() ──►             │                         │
```

### Warning Propagation Flow (Mycelium)

```
Arm-1 (detects fault)         All Citizens              Governor
   │                              │                        │
   │── check telemetry ──►       │                        │
   │   voltage < 6.0V            │                        │
   │                              │                        │
   │── REPORT (warning) ────────►│ (multicast, fast ch)   │
   │   severity: critical         │                        │
   │   TTL: 2s                    │                        │
   │                              │── apply mitigation     │
   │                              │   reduce duty 50%      │
   │                              │                        │
   │                              │                     ◄──│ dashboard update
   │                              │                        │
   │── create FaultPattern ──►   │                        │
   │── REPORT (immune_share) ───►│ (multicast)            │
   │                              │── merge patterns       │
   │                              │                        │
```

### Symbiosis Contract Flow

```
Camera                           Arm-1                   Governor
   │                               │                       │
   │── PROPOSE (symbiosis) ──────►│                       │
   │   provider: video_stream      │                       │
   │   consumer: 6dof_arm          │                       │
   │   composite: visual_pick      │                       │
   │                               │                       │
   │◄── ACCEPT (contract_id) ─────│                       │
   │                               │                       │
   │── register contract           │── register contract   │
   │                               │                       │
   │── health checks via heartbeat │                       │
   │◄── health checks via heartbeat│                       │
   │                               │                       │
   │   (3 missed checks)          │                       │
   │                               │── contract BROKEN     │
   │                               │── enter safe mode     │
   │                               │── REPORT to governor ►│
```

## Persistence Schema

All v2.0 state persists to `~/.citizenry/` using the established atomic-write pattern (write-to-tmp, rename).

```
~/.citizenry/
├── <name>.key                    # Ed25519 private key (v1.5)
├── <name>.neighbors.json         # Neighbor table (v1.5)
├── <name>.constitution.json      # Constitution (v1.5)
├── <name>.genome.json            # Citizen genome (v2.0)
├── <name>.immune.json            # Immune memory patterns (v2.0)
├── <name>.contracts.json         # Active symbiosis contracts (v2.0)
└── <name>.skills.json            # Skill tree + XP (v2.0)
```

## Integration Points

### citizen.py Extensions

The base `Citizen` class gains these new attributes:
- `self.skill_tree: SkillTree` — initialized with type-appropriate defaults
- `self.immune_memory: ImmuneMemory` — bootstrapped with known patterns
- `self.mycelium: MyceliumNetwork` — warning management
- `self.contracts: ContractManager` — symbiosis contracts
- `self.genome: CitizenGenome` — portable state

New lifecycle hooks:
- `_on_warning_received(warning)` — subclass override for warning response
- `_on_immune_share_received(patterns)` — merge incoming patterns
- `_on_genome_received(genome)` — apply genome from governor
- `_on_task_proposed(task)` — evaluate and bid
- `_on_contract_proposed(contract)` — evaluate symbiosis

### surface_citizen.py Extensions

Governor gains:
- `TaskMarketplace` instance for managing auctions
- `CompositionEngine` for auto-discovering composite capabilities
- Genome distribution to new citizens on join
- Immune memory aggregation and distribution
- Skill tree definition distribution

### pi_citizen.py Extensions

Follower gains:
- Task bidding logic (evaluate PROPOSE, generate bid, send ACCEPT/REJECT)
- XP tracking on task completion
- Warning generation from telemetry
- Immune memory pattern matching against telemetry
- Contract health monitoring

### dashboard.py Extensions

New TUI sections:
- **TASKS**: Active task list with status, assigned citizen, bids
- **SKILLS**: Per-citizen skill levels and XP
- **CONTRACTS**: Active symbiosis contracts with health status
- **WARNINGS**: Active mycelium warnings with severity and decay

## Security Model

No changes to the security model. All new message bodies are carried inside signed Envelopes. Genome imports require governor signature verification. Immune memory entries are traceable to source citizen pubkey.

## Performance Budget

| Operation | Budget | Mechanism |
|-----------|--------|-----------|
| Task auction round-trip | < 500ms | 2s timeout, LAN UDP |
| Warning fast channel | < 100ms | UDP multicast, no ack |
| Genome export/import | < 1s | JSON serialization |
| Immune pattern match | < 1ms per pattern | In-memory dict scan |
| Skill tree check | < 0.1ms | DAG traversal, cached |
| Dashboard refresh | 500ms | Same 2Hz as v1.5 |
| Memory per citizen | < 50MB RSS | Same as v1.5 + ~5MB for v2.0 state |

## Error Handling

All v2.0 modules follow the v1.5 pattern: catch exceptions at the handler level, log them, and continue. No new exception types. No crashes from unexpected message bodies (unknown fields are ignored).

## Testing Strategy

| Level | What | How |
|-------|------|-----|
| Unit | Each new module in isolation | pytest, no hardware |
| Protocol compat | v2.0 messages valid v1.5 envelopes | Envelope roundtrip tests |
| Integration | Multi-citizen scenarios on localhost | pytest-asyncio, mock buses |
| Manual | Real hardware end-to-end | Surface + Pi + camera |
