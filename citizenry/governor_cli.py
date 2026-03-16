#!/usr/bin/env python3
"""Interactive Governor CLI — natural language control of the citizenry.

Run on the Surface Pro 7 to control the entire mesh via natural language.

Usage:
    python -m citizenry.governor_cli
    python -m citizenry.governor_cli --leader-port /dev/ttyACM0

Commands:
    wave hello          → arm waves
    sort the blocks     → camera detects, arm sorts
    be gentle           → reduce torque 30%
    slow down           → reduce speed 50%
    what do you see     → camera detects colors
    take a photo        → camera captures frame
    stop                → emergency stop all citizens
    status              → show neighborhood status
    tasks               → show active/completed tasks
    skills              → show citizen skills
    contracts           → show symbiosis contracts
    quit/exit           → shutdown
"""

import asyncio
import sys
import time

from .surface_citizen import SurfaceCitizen
from .nl_governance import GovernorAide, parse_command
from .marketplace import TaskStatus
from .data_collection import DataCollector
from .web_dashboard import WebDashboard

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_status(surface: SurfaceCitizen):
    """Print current neighborhood status."""
    print(f"\n{BOLD}Neighborhood ({1 + len(surface.neighbors)} citizens):{RESET}")
    print(f"  {GREEN}●{RESET} {surface.name} [{surface.short_id}] (governor)")
    for n in surface.neighbors.values():
        health_color = GREEN if n.health > 0.5 else YELLOW
        print(f"  {health_color}●{RESET} {BOLD}{n.name}{RESET} ({n.citizen_type}) @ {n.addr[0]}")
        print(f"    caps: {CYAN}{', '.join(n.capabilities)}{RESET}")
    if surface.composite_capabilities:
        print(f"  Composites: {CYAN}{', '.join(surface.composite_capabilities)}{RESET}")
    contracts = surface.contracts.get_active()
    if contracts:
        print(f"  Contracts: {len(contracts)} active")
    print(f"  Warnings: {surface.mycelium.active_count()} | Immune: {len(surface.immune_memory.get_all())} patterns")
    print(f"  Messages: {surface.messages_sent} sent / {surface.messages_received} rx")


def print_tasks(surface: SurfaceCitizen):
    """Print task status."""
    active = surface.marketplace.get_active_tasks()
    completed = surface.marketplace.completed_tasks

    if active:
        print(f"\n{BOLD}Active Tasks:{RESET}")
        for t in active:
            name = "?"
            if t.assigned_to:
                name = next((n.name for n in surface.neighbors.values() if n.pubkey == t.assigned_to), t.assigned_to[:8])
            print(f"  [{t.id}] {t.type} — {YELLOW}{t.status.value}{RESET} → {name}")

    if completed:
        print(f"\n{BOLD}Completed Tasks (last 10):{RESET}")
        for t in completed[-10:]:
            name = "?"
            if t.assigned_to:
                name = next((n.name for n in surface.neighbors.values() if n.pubkey == t.assigned_to), t.assigned_to[:8])
            dur = t.result.get("duration_ms", 0) if t.result else 0
            xp = t.result.get("xp_earned", 0) if t.result else 0
            print(f"  {GREEN}✓{RESET} [{t.id}] {t.type} → {name} ({dur}ms, +{xp} XP)")

    if not active and not completed:
        print(f"  {DIM}No tasks yet{RESET}")


def print_skills(surface: SurfaceCitizen):
    """Print skill tree status."""
    print(f"\n{BOLD}Skills:{RESET}")
    unlocked = surface.skill_tree.unlocked_skills()
    for skill in sorted(unlocked):
        level = surface.skill_tree.skill_level(skill)
        xp = surface.skill_tree.get_xp(skill)
        print(f"  {GREEN}✓{RESET} {skill} (level {level}, {xp} XP)")
    locked = len(surface.skill_tree.definitions) - len(unlocked)
    if locked:
        print(f"  {DIM}{locked} locked{RESET}")


async def run_cli(leader_port: str = "/dev/ttyACM0", fps: float = 25.0):
    surface = SurfaceCitizen(leader_port=leader_port, teleop_fps=fps)
    await surface.start()

    # Wait for neighbors
    print(f"\n{BOLD}{CYAN}armOS Citizenry v2.0 — Governor CLI{RESET}")
    print(f"{DIM}Discovering citizens...{RESET}")
    t0 = time.time()
    while not surface.neighbors and time.time() - t0 < 8:
        await asyncio.sleep(0.2)
    await asyncio.sleep(1)

    # Pause teleop — CLI mode uses marketplace for tasks
    if surface._teleop_active:
        await surface.stop_teleop()
        await asyncio.sleep(0.5)

    surface._update_compositions()

    # Start web dashboard
    web = WebDashboard(surface, port=8080)
    try:
        await web.start()
        print(f"{GREEN}Web dashboard:{RESET} http://0.0.0.0:8080")
    except Exception as e:
        print(f"{DIM}Web dashboard failed: {e}{RESET}")
        web = None

    # Init data collector
    collector = DataCollector(surface)
    surface._data_collector = collector

    print_status(surface)

    aide = GovernorAide(surface)

    print(f"\n{BOLD}Ready.{RESET} Type commands in natural language, or 'help' for options.\n")

    try:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(f"{BOLD}governor>{RESET} ")
                )
            except EOFError:
                break

            line = line.strip()
            if not line:
                continue

            if line in ("quit", "exit", "q"):
                break
            elif line == "help":
                print(f"""
{BOLD}Commands:{RESET}
  {BOLD}Tasks:{RESET}
    wave / nod / grip       Gesture tasks (arm)
    sort the blocks         Color sorting (camera + arm)
    what do you see         Color detection (camera)
    take a photo            Frame capture (camera)
    pick and place          Pick and place (arm)
  {BOLD}Governance:{RESET}
    be gentle / careful     Reduce torque
    slow down / speed up    Adjust speed
    set fps to N            Set teleop FPS
    stop                    Emergency stop
  {BOLD}Recording:{RESET}
    start recording [task]  Begin data collection
    stop recording          Save episode
  {BOLD}Calibration:{RESET}
    calibrate camera        Run guided calibration
    check calibration       Validate current calibration
  {BOLD}Info:{RESET}
    status                  Neighborhood status
    tasks                   Task history
    skills                  Skill levels
    contracts               Symbiosis contracts
    dashboard               Web dashboard URL
    quit                    Exit
""")
            elif line == "status":
                print_status(surface)
            elif line == "tasks":
                print_tasks(surface)
            elif line == "skills":
                print_skills(surface)
            elif line == "contracts":
                contracts = surface.contracts.get_active()
                if contracts:
                    for c in contracts:
                        prov = next((n.name for n in surface.neighbors.values() if n.pubkey == c.provider), c.provider[:8])
                        cons = next((n.name for n in surface.neighbors.values() if n.pubkey == c.consumer), c.consumer[:8])
                        print(f"  {GREEN}●{RESET} {prov} ←→ {cons} = {CYAN}{c.composite_capability}{RESET}")
                else:
                    print(f"  {DIM}No active contracts{RESET}")
            elif line == "dashboard":
                print(f"  {GREEN}http://0.0.0.0:8080{RESET}")
            elif line == "wills":
                archive = surface.get_will_archive()
                if archive:
                    print(f"\n{BOLD}Will Archive ({len(archive)} entries):{RESET}")
                    for w in archive[-10:]:
                        name = w.get("citizen", "?")
                        reason = w.get("reason", "?")
                        task = w.get("current_task_type", "none")
                        xp_count = len(w.get("xp", {}))
                        print(f"  {DIM}{name}{RESET} — {reason} | task: {task} | {xp_count} XP entries")
                else:
                    print(f"  {DIM}No wills received yet{RESET}")
            elif line.startswith("start recording"):
                task_label = line.replace("start recording", "").strip() or "teleoperation"
                if collector.start_recording(task_label):
                    print(f"  {GREEN}Recording started:{RESET} {task_label}")
                else:
                    print(f"  {YELLOW}Already recording{RESET}")
            elif line in ("stop recording", "save episode"):
                result = collector.stop_recording()
                if "error" in result:
                    print(f"  {YELLOW}{result['error']}{RESET}")
                else:
                    print(f"  {GREEN}Episode saved:{RESET} {result['frames']} frames, {result['duration_s']}s")
            elif line in ("calibrate camera", "calibrate", "run calibration"):
                # Find a Pi citizen that has both arm and camera capabilities nearby
                arm_citizen = None
                for n in surface.neighbors.values():
                    if "6dof_arm" in n.capabilities:
                        arm_citizen = n
                        break
                if arm_citizen:
                    print(f"  {BOLD}Sending calibration to {arm_citizen.name}...{RESET}")
                    print(f"  {DIM}Arm will move to 10+ positions while camera detects gripper.{RESET}")
                    print(f"  {DIM}This takes ~30 seconds. Do not touch the arm.{RESET}")
                    surface.send_propose(
                        arm_citizen.pubkey,
                        {"task": "calibrate"},
                        arm_citizen.addr,
                    )
                    # Wait for result
                    print(f"  {DIM}Waiting for calibration result...{RESET}")
                    await asyncio.sleep(35)
                    # Check for calibration_complete in message log
                    for entry in list(surface.message_log)[-10:]:
                        if "calibration" in entry.detail.lower():
                            print(f"  {GREEN}→{RESET} {entry.detail}")
                else:
                    print(f"  {YELLOW}No arm citizen found. Connect a Pi with arm first.{RESET}")
            elif line in ("check calibration",):
                from .calibration import load_calibration
                cal = load_calibration("calibration")
                if cal and cal.homography:
                    age_hrs = (time.time() - cal.timestamp) / 3600
                    print(f"  {GREEN}Calibration loaded:{RESET} {len(cal.points)} points, error={cal.reprojection_error:.1f}")
                    print(f"  {DIM}Age: {age_hrs:.1f} hours{RESET}")
                    if cal.validation_error > 50:
                        print(f"  {YELLOW}Validation error high ({cal.validation_error:.0f}) — recalibrate recommended{RESET}")
                else:
                    print(f"  {YELLOW}No calibration found. Run 'calibrate camera' first.{RESET}")
            else:
                action = aide.execute(line)
                if action:
                    print(f"  {GREEN}→{RESET} {action.explanation}")
                    if action.action_type == "task_create":
                        # Wait for task execution
                        await asyncio.sleep(0.5)
                        print(f"  {DIM}Task dispatched to marketplace...{RESET}")
                else:
                    print(f"  {YELLOW}?{RESET} Not understood. Try 'help' for commands.")

            # Brief pause for protocol messages to flow
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        pass

    print(f"\n{DIM}Shutting down...{RESET}")
    if web:
        await web.stop()
    if collector.session.is_recording:
        collector.stop_recording()
    await surface.stop()
    print(f"{GREEN}Governor offline.{RESET}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Governor CLI")
    parser.add_argument("--leader-port", default="/dev/ttyACM0")
    parser.add_argument("--fps", type=float, default=25.0)
    args = parser.parse_args()
    asyncio.run(run_cli(args.leader_port, args.fps))
