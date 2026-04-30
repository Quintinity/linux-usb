"""Governor citizen — Constitution ratification + marketplace coordination.

Hosts no arms and no recorder. Spawned only on a node that the
fleet treats as Governor (today: the Surface).

v2.0: Task marketplace, capability composition, genome distribution,
immune memory aggregation, skill tree distribution.
"""

from __future__ import annotations

import asyncio
import time

from .citizen import Citizen, Neighbor, Presence
from .protocol import MessageType
from .authority import load_or_create_authority_key
from .marketplace import TaskMarketplace, Task, Bid, compute_bid_score
from .composition import CompositionEngine
from .genome import CitizenGenome, compute_fleet_average
from .skills import default_manipulator_skills, default_camera_skills
from .immune import FaultPattern
from .coordinator import TaskCoordinator
from .survey import HardwareMap, merge_capabilities


def _sid(env) -> str:
    """Get short ID from an envelope sender."""
    return env.sender[:8]


class GovernorCitizen(Citizen):
    """Governor citizen — Constitution ratification + marketplace coordination.

    Responsibilities:
    - Send constitution to new citizens (GOVERN)
    - Receive and log telemetry REPORTs
    - Monitor neighborhood health and presence
    - Manage the task marketplace and auctions
    - Coordinate multi-citizen composite tasks

    No follower bus. No leader bus. No recorder.
    """

    def __init__(
        self,
        hardware: HardwareMap | None = None,
        **kwargs,
    ):
        base_caps = ["compute", "govern"]
        super().__init__(
            name=kwargs.pop("name", "governor"),
            citizen_type="governor",
            capabilities=merge_capabilities(base_caps, hardware),
            **kwargs,
        )
        self.hardware = hardware

        # Telemetry received from followers
        self.follower_telemetry: dict[str, dict] = {}  # pubkey → latest telemetry
        self.safety_violations: list[dict] = []  # recent violations

        # Active laws (mutable at runtime)
        self.laws: dict[str, dict] = {
            "idle_timeout": {"seconds": 300},
            "teleop_max_fps": {"fps": 60},
            "heartbeat_interval": {"seconds": 2.0},
        }

        # v2.0: Task marketplace
        self.marketplace = TaskMarketplace()
        self._auction_tasks: dict[str, asyncio.Task] = {}

        # v2.0: Capability composition engine
        self.composition_engine = CompositionEngine()
        self.composite_capabilities: list[str] = []

        # v2.0: Fleet genomes for averaging
        self._fleet_genomes: dict[str, CitizenGenome] = {}

        # v2.0: Initialize governor's skill tree with all defaults
        self.skill_tree.merge_definitions(default_manipulator_skills())
        self.skill_tree.merge_definitions(default_camera_skills())

        # v3.0: Task coordinator for composite tasks
        self._coordinator = TaskCoordinator(self)

        # v3.0: Rolling updater
        from .rolling_update import RollingUpdater
        self._rolling_updater = RollingUpdater(self)

        # v3.0: Federated learning weight registry
        from .federated import WeightRegistry
        self.weight_registry = WeightRegistry()

        # v3.0: Multi-location registry
        from .multi_location import LocationRegistry, Location
        self.location_registry = LocationRegistry()
        self.location_registry.register(Location(
            id="local", name="Local Network", subnet="192.168.1.0/24",
        ))
        self.location_registry.set_local("local")

    def _maybe_start_recorder(self) -> None:
        """The governor never records. This method exists only as an
        explicit refusal so a misconfigured Constitution doesn't silently
        spawn a recorder on the GovernorNode.
        """
        if self._law("governor.recorder_enabled", default=False):
            raise RuntimeError(
                "GovernorCitizen does not record — set "
                "governor.recorder_enabled=False in Constitution Laws."
            )
        # Otherwise: do nothing.

    async def start(self):
        # Create and sign the constitution
        self._init_constitution()
        await super().start()
        self._maybe_start_recorder()  # explicit no-op when law is correct
        self._log("governor ready — no arms, no recorder")
        self._log("waiting for citizens to join...")

    def ratify_constitution(self, constitution) -> None:
        """Sign and persist a Constitution with the Authority key (not the
        per-citizen governor key). This is the canonical path for any
        Constitution amendment going forward; smell #1 fix."""
        auth_key = load_or_create_authority_key()
        constitution.sign(auth_key)

    def _init_constitution(self):
        """Create the default constitution, signed by the Authority key."""
        try:
            from .constitution import default_constitution
            const = default_constitution()
            self.ratify_constitution(const)
            self.constitution = const.to_dict()
            self.constitution_received = True
            self._log(f"constitution created — v{const.version}, {len(const.articles)} articles")
        except Exception as e:
            self._log(f"constitution creation failed: {e} — proceeding without")
            self.constitution = None

    # ── Neighbor lifecycle ──

    def _on_neighbor_joined(self, neighbor: Neighbor):
        """When a new citizen joins: send constitution, skills, genome."""
        # Send constitution to every new citizen
        if self.constitution:
            self._log(f"sending constitution to {neighbor.name}")
            self.send_govern(
                neighbor.pubkey,
                {"type": "constitution", "constitution": self.constitution},
                neighbor.addr,
            )

        # v2.0: Send skill tree definitions
        skill_defs = {}
        if "6dof_arm" in neighbor.capabilities:
            skill_defs = {k: v.to_dict() for k, v in default_manipulator_skills().items()}
        elif neighbor.citizen_type == "sensor":
            skill_defs = {k: v.to_dict() for k, v in default_camera_skills().items()}
        if skill_defs:
            self.send_govern(
                neighbor.pubkey,
                {"type": "skill_tree", "definitions": skill_defs},
                neighbor.addr,
            )

        # v2.0: Send fleet average genome if available
        self._send_fleet_genome(neighbor)

        # v2.0: Send immune memory
        patterns = self.immune_memory.to_list()
        if patterns:
            self.send_report(
                neighbor.pubkey,
                {"type": "immune_share", "patterns": patterns},
                neighbor.addr,
            )

        # v2.0: Check capability compositions and symbiosis
        self._update_compositions()
        self._try_symbiosis()

    def _on_neighbor_presence_changed(self, neighbor: Neighbor, old_presence: Presence):
        """React to citizens going degraded or dead."""
        if neighbor.presence == Presence.PRESUMED_DEAD:
            self._log(f"citizen DEAD: {neighbor.name}")
            self._add_log("SAFETY", neighbor.name, "presumed dead")
        elif neighbor.presence == Presence.DEGRADED:
            self._log(f"citizen DEGRADED: {neighbor.name}")
            self._add_log("WARNING", neighbor.name, "degraded — missed heartbeats")

    # ── Inbound message handlers ──

    def _handle_accept_reject(self, env, addr):
        body = env.body

        # v2.0: Task marketplace bid
        if body.get("accepted") and body.get("task_id"):
            bid = Bid.from_accept_body(body, env.sender)

            # Apply can_citizen_bid filter at intake (Task 2 follower-targeting gate).
            # We look up the bidder's Neighbor entry so we use the governor's own
            # record of the bidder's capabilities/health rather than trusting
            # self-declared fields in the bid message.
            # If the task isn't in the marketplace yet (race condition between bid
            # arrival and task creation) we skip the filter and let add_bid handle it.
            task = self.marketplace.tasks.get(bid.task_id)
            if task is not None:
                nbr = self.neighbors.get(env.sender)
                eligible, reason = self.marketplace.can_citizen_bid(
                    task=task,
                    citizen_capabilities=nbr.capabilities if nbr else [],
                    citizen_skills=[],        # Neighbor doesn't track skills today
                    citizen_load=0.0,         # No live load tracking on Neighbor
                    citizen_health=nbr.health if nbr else 1.0,
                    target_follower_pubkey=bid.target_follower_pubkey,
                )
                if not eligible:
                    self._log(f"bid rejected from {_sid(env)}: {reason}")
                    return

            if self.marketplace.add_bid(bid):
                self._log(f"bid received: [{bid.task_id}] from {_sid(env)} score={bid.score:.2f}")
            return

        # v2.0: Symbiosis contract acceptance
        if body.get("accepted") and body.get("task") == "symbiosis_propose":
            contract_id = body.get("contract_id", "")
            accepted = self.contracts.accept(contract_id)
            if accepted:
                self._log(f"symbiosis active: {accepted.composite_capability} [{contract_id}]")
                self._add_log("CONTRACT", _sid(env), f"active: {accepted.composite_capability}")
                self._update_compositions()
            return

    def _handle_report(self, env, addr):
        # Let base class handle warnings and immune shares first
        super()._handle_report(env, addr)

        body = env.body
        report_type = body.get("type", "unknown")

        # v2.0: Task completion
        if report_type == "task_complete":
            task_id = body.get("task_id", "")
            result = body.get("result", "unknown")
            if result == "success":
                self.marketplace.complete_task(task_id, body)
                xp_earned = body.get("xp_earned", 0)
                self._log(f"task complete: [{task_id}] success, +{xp_earned} XP")
                self._add_log("TASK", _sid(env), f"[{task_id}] complete +{xp_earned}XP")
            else:
                reauction = self.marketplace.fail_task(task_id, result)
                if reauction:
                    self._log(f"task failed: [{task_id}] — re-auctioning")
                    for pubkey, n in self.neighbors.items():
                        self.send_propose(pubkey, reauction.to_propose_body(), n.addr)
            return

        # v3.0: Will absorption — re-auction tasks, preserve XP, break contracts
        if report_type == "will":
            citizen_name = body.get("citizen", "?")
            citizen_pubkey = body.get("citizen_pubkey", env.sender)
            self._log(f"WILL received from {citizen_name} — reason: {body.get('reason', '?')}")
            self._add_log("WILL", citizen_name, f"final will — {body.get('reason', 'shutdown')}")

            # Re-auction active task with partial results
            task_id = body.get("current_task_id")
            if task_id:
                reauction = self.marketplace.fail_task(task_id, "citizen_died")
                if reauction:
                    reauction.params["partial_results"] = body.get("partial_results", {})
                    for pubkey, n in self.neighbors.items():
                        self.send_propose(pubkey, reauction.to_propose_body(), n.addr)
                    self._log(f"will: task [{task_id}] re-auctioned with partial results")

            # Preserve XP in fleet genome
            will_xp = body.get("xp", {})
            if will_xp:
                citizen_type = body.get("citizen_type", "")
                if citizen_type not in self._fleet_genomes:
                    self._fleet_genomes[citizen_type] = CitizenGenome(citizen_type=citizen_type)
                for skill, xp in will_xp.items():
                    existing = self._fleet_genomes[citizen_type].xp.get(skill, 0)
                    self._fleet_genomes[citizen_type].xp[skill] = existing + xp
                self._log(f"will: {len(will_xp)} XP entries preserved in fleet genome")

            # Break contracts involving this citizen
            broken = self.contracts.remove_citizen(citizen_pubkey)
            if broken:
                self._log(f"will: {len(broken)} contracts broken")
                for contract in broken:
                    self._add_log("CONTRACT", citizen_name, f"broken: {contract.composite_capability}")
                self._update_compositions()

            # Archive the will
            self._archive_will(body)
            return

        # v3.0: Model weight announcement (federated learning)
        if report_type == "model_weights_available":
            envelope_data = body.get("envelope", {})
            try:
                from .federated import ModelWeightEnvelope
                envelope = ModelWeightEnvelope.from_dict(envelope_data)
                self.weight_registry.register(envelope)
                self._log(f"weights registered: {envelope.model_type} v{envelope.version} from [{_sid(env)}]")
                self._add_log("FEDERATED", _sid(env), f"weights: {envelope.model_type} v{envelope.version}")
            except Exception as e:
                self._log(f"weight registration failed: {e}")
            return

        # v3.0: Consciousness stream
        if report_type == "consciousness":
            narration = body.get("narration", "")
            citizen_name = body.get("citizen", _sid(env))
            self._add_log("CONSCIOUSNESS", citizen_name, narration)
            return

        # v4.0: Self-calibration result
        if report_type == "self_calibration_complete":
            error = body.get("error")
            if error:
                self._log(f"self-calibration FAILED: {error}")
                self._add_log("CALIBRATE", _sid(env), f"self-cal failed: {error}")
            else:
                motors = body.get("motors", {})
                duration = body.get("duration_s", 0)
                self._log(f"self-calibration complete: {len(motors)} motors in {duration:.1f}s")
                self._add_log("CALIBRATE", _sid(env), f"self-cal: {len(motors)} motors")
                for name, limits in motors.items():
                    self._log(f"  {name}: {limits['min']} → {limits['max']} (range={limits['range']})")
            return

        # v3.0: Calibration result from Pi
        if report_type == "calibration_complete":
            error = body.get("error")
            if error:
                self._log(f"calibration FAILED: {error}")
                self._add_log("CALIBRATE", _sid(env), f"failed: {error}")
            else:
                pts = body.get("points", 0)
                reproj = body.get("reprojection_error", 0)
                val = body.get("validation_error", 0)
                placement = body.get("placement", "?")
                self._log(f"calibration complete: {pts} points, reproj={reproj:.1f}, val={val:.1f}, placement={placement}")
                self._add_log("CALIBRATE", _sid(env), f"done: {pts}pts err={reproj:.1f}")
                # Save calibration locally too (for visual_tasks to use)
                cal_data = body.get("calibration")
                if cal_data:
                    try:
                        from .calibration import CalibrationResult, save_calibration
                        result = CalibrationResult.from_dict(cal_data)
                        save_calibration("calibration", result)
                        # Load into visual tasks
                        from .visual_tasks import load_calibration_transform
                        load_calibration_transform("calibration")
                        self._log("calibration loaded into visual task pipeline")
                    except Exception as e:
                        self._log(f"calibration save failed: {e}")
                for s in body.get("suggestions", []):
                    self._log(f"  placement suggestion: {s}")
            return

        if report_type == "telemetry":
            self.follower_telemetry[env.sender] = body
            violations = body.get("violations", [])
            if violations:
                for v in violations:
                    self._log(f"SAFETY VIOLATION from {body.get('citizen', '?')}: {v}")
                    self._add_log("SAFETY", body.get("citizen", "?"), v)
                self.safety_violations.extend(
                    {"citizen": env.sender, "violation": v, "time": time.time()}
                    for v in violations
                )

        elif report_type == "fault":
            detail = body.get("detail", "unknown")
            self._log(f"FAULT from [{_sid(env)}]: {detail}")
            self._add_log("FAULT", _sid(env), detail)

        elif report_type == "constitution_applied":
            self._log(f"constitution applied by [{_sid(env)}]")
            self._add_log("GOVERN", _sid(env), "constitution applied")
            if env.sender in self.neighbors:
                self.neighbors[env.sender].has_constitution = True

        elif report_type == "constitution_rejected":
            reason = body.get("reason", "unknown")
            self._log(f"constitution REJECTED by [{_sid(env)}]: {reason}")
            self._add_log("SECURITY", _sid(env), f"constitution rejected: {reason}")

        elif report_type == "law_applied":
            self._log(f"law applied by [{_sid(env)}]: {body.get('law_id', '?')}")
            self._add_log("GOVERN", _sid(env), f"law applied: {body.get('law_id', '?')}")

    # ── Law updates ──

    def update_law(self, law_id: str, params: dict):
        """Update a law and broadcast to all citizens."""
        self.laws[law_id] = params
        self._log(f"law updated: {law_id} = {params}")

        # Broadcast to all citizens
        for pubkey, neighbor in self.neighbors.items():
            self.send_govern(
                pubkey,
                {
                    "type": "law_update",
                    "law_id": law_id,
                    "params": params,
                },
                neighbor.addr,
            )
        self._add_log("GOVERN", self.name, f"law update: {law_id}")

    # ── v2.0: Task marketplace ──

    def create_task(
        self,
        task_type: str,
        params: dict | None = None,
        priority: float = 0.5,
        required_capabilities: list[str] | None = None,
        required_skills: list[str] | None = None,
    ) -> Task:
        """Create a task and broadcast it to the marketplace."""
        task = self.marketplace.create_task(
            task_type, params, priority, required_capabilities, required_skills,
        )
        # Broadcast PROPOSE to all citizens
        body = task.to_propose_body()
        for pubkey, neighbor in self.neighbors.items():
            self.send_propose(pubkey, body, neighbor.addr)

        # Start auction timer
        auction_task = asyncio.get_event_loop().create_task(
            self._run_auction(task.id)
        )
        self._auction_tasks[task.id] = auction_task
        self._log(f"task created: {task.type} [{task.id}] prio={task.priority}")
        return task

    async def _run_auction(self, task_id: str):
        """Wait for bids, then select winner."""
        await asyncio.sleep(self.marketplace.bid_timeout)
        winner = self.marketplace.close_auction(task_id)
        task = self.marketplace.tasks.get(task_id)
        if not task:
            return

        if winner:
            self._log(f"auction won: [{task_id}] → {winner.citizen_pubkey[:8]} (score={winner.score:.2f})")
            self._add_log("TASK", "marketplace", f"{task.type} → {winner.citizen_pubkey[:8]}")
            self.marketplace.start_execution(task_id)
            # Notify winner via GOVERN task_assign
            if winner.citizen_pubkey in self.neighbors:
                n = self.neighbors[winner.citizen_pubkey]
                self.send_govern(
                    winner.citizen_pubkey,
                    {"type": "task_assign", "task_id": task_id, "task": task.type, "params": task.params},
                    n.addr,
                )
        else:
            self._log(f"auction: no bids for [{task_id}] (attempt {task.broadcast_count})")
            if task.broadcast_count < task.max_broadcasts:
                # Re-broadcast with backoff
                delay = 2 ** task.broadcast_count
                await asyncio.sleep(delay)
                task.status = task.status  # Keep bidding
                body = task.to_propose_body()
                for pubkey, neighbor in self.neighbors.items():
                    self.send_propose(pubkey, body, neighbor.addr)
                asyncio.get_event_loop().create_task(self._run_auction(task_id))

    # ── v2.0: Composition ──

    def _update_compositions(self):
        """Re-check capability compositions after neighbor changes."""
        citizen_caps = {}
        # Include our own capabilities
        citizen_caps[self.pubkey] = list(self.capabilities)
        for pubkey, n in self.neighbors.items():
            citizen_caps[pubkey] = list(n.capabilities)
        # Add composite capabilities from contracts
        for cap in self.contracts.get_composite_capabilities():
            if cap not in self.composite_capabilities:
                self.composite_capabilities.append(cap)

        discovered = self.composition_engine.discover_capabilities(citizen_caps)
        new_caps = [c for c in discovered if c not in self.composite_capabilities]
        if new_caps:
            self.composite_capabilities.extend(new_caps)
            self._log(f"compositions discovered: {', '.join(new_caps)}")
            self._add_log("COMPOSE", "engine", f"+{', '.join(new_caps)}")

    # ── v2.0: Symbiosis auto-proposal ──

    def _try_symbiosis(self):
        """Check if any camera + arm pair can form a symbiosis contract."""
        cameras = [n for n in self.neighbors.values() if "video_stream" in n.capabilities or "color_detection" in n.capabilities]
        arms = [n for n in self.neighbors.values() if "6dof_arm" in n.capabilities]

        for cam in cameras:
            for arm in arms:
                # Check if visual_pick_and_place contract already exists between these two
                already = any(
                    c.provider == cam.pubkey and c.consumer == arm.pubkey
                    for c in self.contracts.get_active()
                )
                if already:
                    continue

                # Propose camera → arm symbiosis
                contract = self.contracts.propose(
                    provider=cam.pubkey,
                    consumer=arm.pubkey,
                    provider_cap="video_stream",
                    consumer_cap="6dof_arm",
                    composite="visual_pick_and_place",
                )
                # Send proposal to the arm (consumer)
                self.send_propose(
                    arm.pubkey,
                    contract.to_propose_body(),
                    arm.addr,
                )
                self._log(f"symbiosis proposed: {cam.name} + {arm.name} → visual_pick_and_place")
                self._add_log("CONTRACT", "governor", f"proposed: {cam.name} + {arm.name}")

    # ── v3.0: Will archive ──

    def _archive_will(self, will_body: dict):
        """Persist received will to disk."""
        try:
            import json
            from .persistence import CITIZENRY_DIR
            CITIZENRY_DIR.mkdir(parents=True, exist_ok=True)
            archive_path = CITIZENRY_DIR / "will_archive.json"
            archive = []
            if archive_path.exists():
                try:
                    archive = json.loads(archive_path.read_text())
                except Exception:
                    archive = []
            archive.append(will_body)
            # Keep last 100 wills
            archive = archive[-100:]
            tmp = archive_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(archive, indent=2) + "\n")
            tmp.replace(archive_path)
        except Exception as e:
            self._log(f"will archive failed: {e}")

    def get_will_archive(self) -> list[dict]:
        """Load the will archive."""
        try:
            import json
            from .persistence import CITIZENRY_DIR
            path = CITIZENRY_DIR / "will_archive.json"
            if path.exists():
                return json.loads(path.read_text())
        except Exception:
            pass
        return []

    # ── v2.0: Genome distribution ──

    def _send_fleet_genome(self, neighbor: Neighbor):
        """Send a fleet-average genome to a new citizen."""
        same_type = [g for g in self._fleet_genomes.values()
                     if g.citizen_type == neighbor.citizen_type]
        if same_type:
            avg = compute_fleet_average(same_type)
            self.send_govern(
                neighbor.pubkey,
                {"type": "genome", "genome": avg.to_dict()},
                neighbor.addr,
            )
            self._log(f"fleet genome sent to {neighbor.name} (avg of {len(same_type)})")
