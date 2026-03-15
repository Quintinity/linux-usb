#!/usr/bin/env python3
"""armOS Citizenry v2.0 — Collaboration Demo.

Demonstrates: task marketplace, skill trees, capability composition,
symbiosis contracts, mycelium warnings, immune memory, and citizen genome.

Runs the governor on the Surface, waits for the Pi follower,
then exercises every v2.0 feature with live output.
"""

import asyncio
import time
from .surface_citizen import SurfaceCitizen
from .marketplace import TaskStatus

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def section(title: str) -> None:
    print()
    print(f"{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    print()


async def run_demo(leader_port="/dev/ttyACM0", fps=30.0):
    surface = SurfaceCitizen(leader_port=leader_port, teleop_fps=fps)
    await surface.start()

    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  armOS CITIZENRY v2.0 — CITIZENS COLLABORATE                ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")

    # ── Phase 1: Discovery ──
    section("Phase 1: Discovery & Constitution")
    t0 = time.time()
    while not surface.neighbors and time.time() - t0 < 10:
        await asyncio.sleep(0.1)

    if not surface.neighbors:
        print(f"  {YELLOW}No citizens found — running solo demo (marketplace + skills only){RESET}")
        solo = True
    else:
        n = list(surface.neighbors.values())[0]
        elapsed = time.time() - t0
        caps = ", ".join(n.capabilities)
        print(f"  {GREEN}✓{RESET} Citizen found in {elapsed:.2f}s — {n.name} @ {n.addr[0]}")
        print(f"    Capabilities: {CYAN}{caps}{RESET}")
        print(f"    Identity: [{n.pubkey[:16]}...]")
        solo = False

    if surface.constitution:
        c = surface.constitution
        print(f"  {GREEN}✓{RESET} Constitution v{c['version']} signed and distributed")
        print(f"    {len(c.get('articles', []))} articles, {len(c.get('laws', []))} laws")

    # ── Phase 2: Skill Trees ──
    section("Phase 2: Skill Trees & XP")

    print(f"  {BOLD}Governor skills:{RESET}")
    unlocked = surface.skill_tree.unlocked_skills()
    for skill in sorted(unlocked):
        level = surface.skill_tree.skill_level(skill)
        xp = surface.skill_tree.get_xp(skill)
        print(f"    {GREEN}✓{RESET} {skill} (level {level}, {xp} XP)")

    locked_count = len(surface.skill_tree.definitions) - len(unlocked)
    if locked_count:
        print(f"    {DIM}{locked_count} skills locked (need more XP){RESET}")

    if not solo:
        print(f"\n  {BOLD}Skill tree sent to {n.name}{RESET}")
        print(f"    Manipulator defaults: {len(surface.skill_tree.definitions)} skill definitions")

    # ── Phase 3: Immune Memory ──
    section("Phase 3: Immune Memory")

    patterns = surface.immune_memory.get_all()
    print(f"  {BOLD}{len(patterns)} fault patterns loaded:{RESET}")
    for p in patterns:
        severity_color = RED if p.severity in ("critical", "emergency") else YELLOW
        print(f"    {severity_color}●{RESET} {p.pattern_type} — {p.mitigation} ({p.severity})")

    if not solo:
        print(f"\n  {GREEN}✓{RESET} Immune memory shared with {n.name}")

    # ── Phase 4: Genome ──
    section("Phase 4: Citizen Genome")

    genome = surface.genome
    print(f"  Citizen: {genome.citizen_name}")
    print(f"  Type: {genome.citizen_type}")
    print(f"  Version: {genome.version}")
    print(f"  XP entries: {len(genome.xp)}")
    print(f"  Immune patterns: {len(genome.immune_memory)}")
    print(f"  Skill definitions: {len(genome.skill_definitions)}")

    # ── Phase 5: Capability Composition ──
    section("Phase 5: Capability Composition")

    if surface.composite_capabilities:
        print(f"  {BOLD}Discovered composite capabilities:{RESET}")
        for cap in surface.composite_capabilities:
            print(f"    {GREEN}✓{RESET} {CYAN}{cap}{RESET}")
    else:
        print(f"  {DIM}No composite capabilities yet (need camera citizen){RESET}")
        print(f"  {DIM}Run: python -m citizenry.run_camera  to add camera{RESET}")

    # ── Phase 6: Task Marketplace ──
    section("Phase 6: Task Marketplace")

    if not solo:
        # Create a test task
        print(f"  Creating task: {BOLD}basic_gesture{RESET} (wave hello)")
        task = surface.create_task(
            "basic_gesture",
            params={"gesture": "wave"},
            priority=0.7,
            required_capabilities=["6dof_arm"],
            required_skills=["basic_gesture"],
        )
        print(f"    Task ID: {task.id}")
        print(f"    Status: {YELLOW}{task.status.value}{RESET}")
        print(f"    Required: 6dof_arm + basic_gesture skill")

        # Wait for auction
        print(f"\n  Waiting for bids ({surface.marketplace.bid_timeout}s timeout)...")
        await asyncio.sleep(surface.marketplace.bid_timeout + 0.5)

        # Check result
        bids = surface.marketplace.bids.get(task.id, [])
        print(f"  Bids received: {len(bids)}")
        for bid in bids:
            print(f"    [{bid.citizen_pubkey[:8]}] score={bid.score:.2f} skill={bid.skill_level} load={bid.current_load:.1f}")

        task = surface.marketplace.tasks.get(task.id)
        if task:
            if task.status in (TaskStatus.ASSIGNED, TaskStatus.EXECUTING, TaskStatus.COMPLETED):
                print(f"  {GREEN}✓{RESET} Task {task.status.value} → {task.assigned_to[:8] if task.assigned_to else '?'}")
            else:
                print(f"  {YELLOW}Task status: {task.status.value}{RESET}")

        # Wait for execution
        await asyncio.sleep(2)
        task = surface.marketplace.tasks.get(task.id)
        if task and task.status == TaskStatus.COMPLETED:
            print(f"  {GREEN}✓{RESET} Task completed!")
        elif task:
            print(f"  Task status: {task.status.value}")
    else:
        # Solo demo — just show marketplace API
        print(f"  {DIM}(No followers connected — showing marketplace API){RESET}")
        task = surface.marketplace.create_task("pick_and_place", priority=0.8)
        print(f"  Created: [{task.id}] pick_and_place prio=0.8")
        print(f"  Status: {YELLOW}{task.status.value}{RESET} (no citizens to bid)")

    # ── Phase 7: Contracts ──
    section("Phase 7: Symbiosis Contracts")

    active = surface.contracts.get_active()
    if active:
        for contract in active:
            print(f"  {GREEN}●{RESET} {contract.provider[:8]} <-> {contract.consumer[:8]}")
            print(f"    Composite: {CYAN}{contract.composite_capability}{RESET}")
            print(f"    Health: {'ok' if contract.is_healthy() else 'broken'}")
    else:
        print(f"  {DIM}No active contracts (need camera + arm symbiosis){RESET}")

    # ── Phase 8: Mycelium Network ──
    section("Phase 8: Mycelium Warning Network")

    active_warnings = surface.mycelium.active_count()
    print(f"  Active warnings: {active_warnings}")
    print(f"  Mitigation factor: {surface.mycelium.current_mitigation_factor():.0%}")
    print(f"  Emergency stop: {'YES' if surface.mycelium.should_stop() else 'no'}")

    if not solo:
        # Let teleop run briefly to collect telemetry
        print(f"\n  Monitoring telemetry for warnings (5s)...")
        await asyncio.sleep(5)
        new_warnings = surface.mycelium.active_count()
        if new_warnings > active_warnings:
            print(f"  {YELLOW}New warnings detected: {new_warnings - active_warnings}{RESET}")
        else:
            print(f"  {GREEN}✓{RESET} No new warnings — all systems nominal")

    # ── Phase 9: Protocol Stats ──
    section("Phase 9: Protocol Statistics")

    print(f"  Messages sent:     {surface.messages_sent}")
    print(f"  Messages received: {surface.messages_received}")
    print(f"  Neighbors:         {len(surface.neighbors)}")
    print(f"  Skills unlocked:   {len(surface.skill_tree.unlocked_skills())}")
    print(f"  Immune patterns:   {len(surface.immune_memory.get_all())}")
    print(f"  Active contracts:  {len(surface.contracts.get_active())}")
    print(f"  Composite caps:    {len(surface.composite_capabilities)}")
    if surface._teleop_active:
        elapsed = time.time() - surface._teleop_start
        fps = surface._frames_sent / elapsed if elapsed > 0 else 0
        print(f"  Teleop frames:     {surface._frames_sent} ({fps:.1f} FPS)")

    # ── Summary ──
    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  v2.0 Demo Complete — The citizenry collaborates.           ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()

    # Show message log
    if surface.message_log:
        print(f"{BOLD}Message Log (last 15):{RESET}")
        for entry in list(surface.message_log)[-15:]:
            print(f"  {DIM}{entry.timestamp}{RESET} {BOLD}{entry.msg_type:<12}{RESET} {entry.sender} — {entry.detail}")

    await surface.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="armOS Citizenry v2.0 Demo")
    parser.add_argument("--leader-port", default="/dev/ttyACM0")
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args()
    asyncio.run(run_demo(args.leader_port, args.fps))
