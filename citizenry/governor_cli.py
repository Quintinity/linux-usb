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

from .governor_citizen import GovernorCitizen
from .nl_governance import GovernorAide, parse_command
from .marketplace import TaskStatus
from .data_collection import DataCollector
from .web_dashboard import WebDashboard
from .recorder import TimelineRecorder, list_sessions
from .episode_recorder import list_episodes, get_episode_summary  # legacy v1 browsing helpers
from .learning_loop import get_learning_report, analyze_recent_episodes
from .dialogue import parse_question, compose_response, CitizenVoice
from .president import President, GovernorRecord, parse_president_command

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_status(surface: GovernorCitizen):
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


def print_tasks(surface: GovernorCitizen):
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


def print_skills(surface: GovernorCitizen):
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
    # Note: leader arm is now a separate LeaderCitizen process; governor is governor-only.
    surface = GovernorCitizen()
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

    # Initialize president layer
    president = President("president")
    # Register ourselves as a governor
    president.register_governor(GovernorRecord(
        pubkey=surface.pubkey,
        name=surface.name,
        location="local",
        addr=("127.0.0.1", 0),
        citizen_count=len(surface.neighbors),
        capabilities=list(surface.capabilities),
        composite_capabilities=getattr(surface, 'composite_capabilities', []),
        health=surface.health,
        last_seen=time.time(),
    ))

    print_status(surface)

    aide = GovernorAide(surface)

    # Try to load existing calibration
    from .visual_tasks import load_calibration_transform
    if load_calibration_transform("calibration"):
        print(f"{GREEN}Calibration loaded{RESET}")
    else:
        print(f"{DIM}No calibration — run 'calibrate camera' for accurate pick-and-place{RESET}")

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
  {BOLD}Rollout:{RESET}
    rollout <law> <value>   Roll out a law change with canary testing
    rollout status          Show active rollout status
  {BOLD}Info:{RESET}
    status                  Neighborhood status
    tasks                   Task history
    skills                  Skill levels
    contracts               Symbiosis contracts
    wills                   Will archive
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
            elif line.startswith("start teleop"):
                # Find an idle arm to teleop with
                parts = line.split()
                target_name = parts[2] if len(parts) > 2 else None
                arm = None
                for n in surface.neighbors.values():
                    if "6dof_arm" in n.capabilities:
                        if target_name and n.name != target_name:
                            continue
                        arm = n
                        break
                if arm:
                    surface._propose_teleop(arm)
                    print(f"  {GREEN}Teleop proposed to {arm.name}{RESET}")
                else:
                    print(f"  {YELLOW}No idle arm found{RESET}")
            elif line == "stop teleop":
                if surface._teleop_active:
                    await surface.stop_teleop()
                    print(f"  {GREEN}Teleop stopped{RESET}")
                else:
                    print(f"  {DIM}Teleop not active{RESET}")
            elif line == "locations":
                locs = surface.location_registry.to_list()
                print(f"\n{BOLD}Locations ({len(locs)}):{RESET}")
                for l in locs:
                    local = " (local)" if l["id"] == surface.location_registry.local_location_id else ""
                    print(f"  {GREEN}●{RESET} {l['name']}{local} — {l.get('subnet', '?')}")
            elif line == "weights":
                count = surface.weight_registry.count()
                if count:
                    print(f"\n{BOLD}Model Weights ({count}):{RESET}")
                    for e in surface.weight_registry.to_list():
                        print(f"  {e['model_type']} v{e['version']} — {e.get('metrics', {})}")
                else:
                    print(f"  {DIM}No model weights registered{RESET}")
            elif line == "dashboard":
                print(f"  {GREEN}http://0.0.0.0:8080{RESET}")
            elif line.startswith("ask ") or line.startswith("talk to "):
                # Ask a citizen a question: "ask pi-follower how are you"
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    target_name = parts[1]
                    question = parts[2]
                    # Find the target citizen
                    target = next((n for n in surface.neighbors.values() if n.name == target_name), None)
                    if target:
                        q_type = parse_question(question)
                        # For now compose locally from governor's view of citizen
                        # In future: send PROPOSE dialogue to citizen, get REPORT response
                        print(f"\n  {BOLD}[{target.name}]:{RESET}")
                        # Compose basic response from what governor knows
                        health_pct = int(target.health * 100)
                        mood = target.emotional_state.mood if target.emotional_state else "unknown"
                        state = target.state
                        presence = target.presence.value
                        print(f"  Health: {health_pct}% | State: {state} | Mood: {mood} | Presence: {presence}")
                        caps = ", ".join(target.capabilities)
                        print(f"  Capabilities: {caps}")
                        if target.emotional_state:
                            e = target.emotional_state
                            print(f"  Fatigue: {e.fatigue:.0%} | Confidence: {e.confidence:.0%} | Curiosity: {e.curiosity:.0%}")
                    else:
                        print(f"  {YELLOW}Citizen '{target_name}' not found. Known: {', '.join(n.name for n in surface.neighbors.values())}{RESET}")
                else:
                    print(f"  {DIM}Usage: ask <citizen-name> <question>{RESET}")
                    print(f"  {DIM}Example: ask pi-follower how are you{RESET}")
            elif line.startswith("how am i") or line == "self":
                # Governor asks about itself
                voice = CitizenVoice(surface)
                print(f"\n  {BOLD}[{surface.name}]:{RESET}")
                print(f"  {voice.how_are_you()}")
            elif line in ("policy history", "history"):
                entries = aide.get_policy_history(10)
                if entries:
                    print(f"\n{BOLD}Policy History (last {len(entries)}):{RESET}")
                    for e in entries:
                        conf = e.get("confidence", 0)
                        auto = "auto" if e.get("auto_applied") else "manual"
                        print(f"  {DIM}{e.get('command', '?')}{RESET} → {e.get('explanation', '?')} ({conf:.0%}, {auto})")
                else:
                    print(f"  {DIM}No policy changes yet{RESET}")
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
            elif line.startswith("record session"):
                parts = line.split(None, 2)
                session_name = parts[2] if len(parts) > 2 else None
                recorder = TimelineRecorder(session_name)
                recorder.start(camera_index=0)
                surface._recorder = recorder
                print(f"  {GREEN}Recording session: {recorder.session_name}{RESET}")
                print(f"  {DIM}Video + telemetry + commands + events{RESET}")
            elif line == "stop session":
                if hasattr(surface, '_recorder') and surface._recorder and surface._recorder.is_recording:
                    meta = surface._recorder.stop()
                    print(f"  {GREEN}Session saved: {meta.name}{RESET}")
                    print(f"  Video: {meta.video_frames} frames, Telemetry: {meta.telemetry_samples}, Commands: {meta.commands}")
                    surface._recorder = None
                else:
                    print(f"  {DIM}No recording session active{RESET}")
            elif line == "sessions":
                sessions = list_sessions()
                if sessions:
                    print(f"\n{BOLD}Recording Sessions ({len(sessions)}):{RESET}")
                    for s in sessions:
                        name = s.get("name", "?")
                        dur = s.get("duration_s", 0)
                        frames = s.get("video_frames", 0)
                        print(f"  {name} — {dur:.0f}s, {frames} frames")
                else:
                    print(f"  {DIM}No recordings yet{RESET}")
            elif line == "episodes":
                eps = list_episodes(15)
                if eps:
                    print(f"\n{BOLD}Recent Episodes ({len(eps)}):{RESET}")
                    for e in eps:
                        success = f"{GREEN}✓{RESET}" if e.get("success") else f"{RED}✗{RESET}"
                        print(f"  {success} #{e.get('episode_id', '?')} {e.get('task', '?')} — "
                              f"{e.get('duration_s', 0):.1f}s, {e.get('frames', 0)} frames")
                else:
                    print(f"  {DIM}No episodes recorded yet{RESET}")
            elif line.startswith("episode "):
                try:
                    ep_id = int(line.split()[1])
                    summary = get_episode_summary(ep_id)
                    print(f"\n{BOLD}{summary}{RESET}")
                except (ValueError, IndexError):
                    print(f"  {YELLOW}Usage: episode <number>{RESET}")
            elif line in ("learn", "learning report", "what did you learn"):
                report = get_learning_report()
                print(f"\n{report}")
            elif line.startswith("analyze "):
                session_name = line.split(None, 1)[1].strip()
                print(f"  {BOLD}Analyzing {session_name}...{RESET}")
                from .analyzer import analyze_session
                result = analyze_session(session_name, log_fn=lambda m: print(f"  {DIM}{m}{RESET}"))
                print(f"  {GREEN}Done:{RESET} {result.total_frames} frames, {result.total_commands} commands, {len(result.detected_stalls)} stalls")
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
            elif line.startswith("self calibrate") or line.startswith("self-calibrate") or line == "find limits":
                arm = next((n for n in surface.neighbors.values() if "6dof_arm" in n.capabilities), None)
                if arm:
                    # Parse mode from command: "self calibrate staged" / "self calibrate camera" etc
                    parts = line.split()
                    mode = "staged"  # Default
                    if len(parts) >= 3 and parts[-1] in ("staged", "camera", "current", "manual"):
                        mode = parts[-1]
                    else:
                        print(f"  {BOLD}Calibration modes:{RESET}")
                        print(f"    {BOLD}staged{RESET}  — Auto lift + fold + calibrate (recommended)")
                        print(f"    {BOLD}camera{RESET}  — Camera verifies arm position")
                        print(f"    {BOLD}current{RESET} — Current sensing for liftoff")
                        print(f"    {BOLD}manual{RESET}  — You lift arm first, then auto-calibrate")
                        mode_input = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: input(f"  Select mode [{BOLD}staged{RESET}]: ").strip()
                        )
                        if mode_input in ("staged", "camera", "current", "manual"):
                            mode = mode_input

                    print(f"  {BOLD}Self-calibrating {arm.name} (mode: {mode})...{RESET}")
                    if mode == "manual":
                        print(f"  {YELLOW}Lift the arm to an upright L-shape NOW. You have 10 seconds.{RESET}")
                    else:
                        print(f"  {DIM}Do not touch the arm.{RESET}")
                    surface.send_propose(arm.pubkey, {"task": "self_calibrate", "mode": mode}, arm.addr)
                    print(f"  {DIM}Waiting for results...{RESET}")
                    await asyncio.sleep(90 if mode != "manual" else 100)
                    for entry in list(surface.message_log)[-15:]:
                        if "self-cal" in entry.detail.lower() or "calibrat" in entry.detail.lower():
                            print(f"  {GREEN}→{RESET} {entry.detail}")
                else:
                    print(f"  {YELLOW}No arm found{RESET}")
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
            elif line.startswith("rollout ") and line != "rollout status":
                # Parse: rollout teleop_max_fps 30
                parts = line.split()
                if len(parts) >= 3:
                    law_id = parts[1]
                    try:
                        value = int(parts[2])
                    except ValueError:
                        try:
                            value = float(parts[2])
                        except ValueError:
                            value = parts[2]
                    print(f"  {BOLD}Rolling out:{RESET} {law_id} = {value}")
                    plan = surface._rolling_updater.create_rollout(
                        "law_update",
                        {"law_id": law_id, "params": {law_id.split("_")[-1] if "_" in law_id else "value": value}},
                    )
                    print(f"  Plan: {len(plan.citizens)} citizens, threshold: {plan.failure_threshold:.0%}")
                    result = await surface._rolling_updater.execute(plan)
                    status_color = GREEN if result.status.value == "completed" else RED
                    print(f"  {status_color}Result: {result.status.value}{RESET} — {result.success_count}/{len(result.citizens)} succeeded")
                else:
                    print(f"  {YELLOW}Usage: rollout <law_id> <value>{RESET}")
                    print(f"  {DIM}Example: rollout teleop_max_fps 30{RESET}")
            elif line == "rollout status":
                updater = surface._rolling_updater
                if updater.active_rollout:
                    r = updater.active_rollout
                    print(f"  {BOLD}Active rollout:{RESET} {r.policy_type} — {r.progress:.0%} complete")
                elif updater.history:
                    last = updater.history[-1]
                    print(f"  {BOLD}Last rollout:{RESET} {last.policy_type} — {last.status.value}")
                    print(f"  {last.success_count}/{len(last.citizens)} succeeded")
                else:
                    print(f"  {DIM}No rollouts yet{RESET}")
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
            elif line in ("nation", "nation status", "fleet"):
                # Update governor record with current state
                president.governors[surface.pubkey].citizen_count = len(surface.neighbors)
                president.governors[surface.pubkey].composite_capabilities = getattr(surface, 'composite_capabilities', [])
                president.governors[surface.pubkey].last_seen = time.time()
                president.governors[surface.pubkey].mood = surface.emotional_state.mood
                print(f"\n{BOLD}{president.nation_summary()}{RESET}")
            elif line == "governors":
                for g in president.governors.values():
                    status = f"{GREEN}online{RESET}" if g.is_online() else f"{RED}offline{RESET}"
                    print(f"  {BOLD}{g.name}{RESET} ({g.location}) — {g.citizen_count} citizens — {status}")
            elif line.startswith("tell ") or (": " in line and line.startswith("at ")):
                cmd = parse_president_command(line)
                if cmd and cmd["action"] == "delegate":
                    target = cmd["target"]
                    command = cmd["command"]
                    gov = president.get_governor(target)
                    if gov:
                        print(f"  {GREEN}→{RESET} Delegating to {gov.name}: {command}")
                        # Execute locally if it's us
                        action = aide.execute(command)
                        if action:
                            print(f"  {GREEN}→{RESET} {action.explanation}")
                    else:
                        print(f"  {YELLOW}Governor '{target}' not found{RESET}")
            elif line.startswith("all "):
                command = line[4:].strip()
                routes = president.route_command(command)
                print(f"  Broadcasting to {len(routes)} governors: {command}")
                action = aide.execute(command)
                if action:
                    print(f"  {GREEN}→{RESET} {action.explanation}")
            else:
                # Check if the line starts with a citizen name → direct command
                handled = False
                for n in surface.neighbors.values():
                    if line.lower().startswith(n.name.lower() + " "):
                        citizen_cmd = line[len(n.name):].strip()
                        print(f"  {BOLD}→ {n.name}:{RESET} {citizen_cmd}")

                        # Is it a question? (ask-style)
                        q_type = parse_question(citizen_cmd)
                        if any(w in citizen_cmd.lower() for w in ("how are", "status", "hurt", "remember", "goal", "tired", "growth")):
                            # Send dialogue to citizen
                            surface.send_propose(
                                n.pubkey,
                                {"task": "dialogue", "text": citizen_cmd},
                                n.addr,
                            )
                            await asyncio.sleep(2)
                            # Check for response in message log
                            for entry in list(surface.message_log)[-5:]:
                                if "dialogue" in entry.msg_type.lower() or "dialogue" in entry.detail.lower():
                                    print(f"  {GREEN}[{n.name}]:{RESET} {entry.detail}")
                            handled = True
                        else:
                            # It's a task command directed at this citizen
                            from .nl_governance import parse_command
                            action = parse_command(citizen_cmd)
                            if action and action.action_type == "task_create":
                                # Create task with required capabilities matching this citizen
                                task = surface.create_task(
                                    task_type=action.params.get("type", ""),
                                    params=action.params.get("params", {}),
                                    priority=0.9,  # Higher priority for direct commands
                                    required_capabilities=action.params.get("required_capabilities", []),
                                    required_skills=action.params.get("required_skills", []),
                                )
                                print(f"  {GREEN}→{RESET} Task [{task.id}] dispatched: {action.explanation}")
                                await asyncio.sleep(0.5)
                            elif action:
                                aide.execute(citizen_cmd)
                                print(f"  {GREEN}→{RESET} {action.explanation}")
                            else:
                                print(f"  {YELLOW}?{RESET} Didn't understand command for {n.name}")
                            handled = True
                        break

                if not handled:
                    action = aide.execute(line)
                    if action:
                        print(f"  {GREEN}→{RESET} {action.explanation}")
                        if action.action_type == "task_create":
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


async def run_demo(surface, task_type: str = "basic_gesture/wave") -> None:
    """End-to-end demo: print inventory, emit a task, narrate outcome.

    Walks through one full marketplace round so a new operator can see what
    the citizenry actually does:
      1. Print the governor's identity.
      2. Print the inventory of currently-discovered neighbors.
      3. Emit a task to the marketplace.
      4. Wait for the auction + execution to settle.
      5. Narrate the outcome ("completed by <role> in Xs" or failure reason).
    """
    print("=" * 60)
    print("citizenry demo — basic marketplace round")
    print("=" * 60)
    pubkey_str = str(getattr(surface, "pubkey", "") or "")
    print(f"\nGovernor: {surface.name} [{pubkey_str[:8]}]")
    neighbors = getattr(surface, "neighbors", {}) or {}
    print(f"\nNeighbors ({len(neighbors)}):")
    if not neighbors:
        print("  (none discovered yet — is the mesh up?)")
    for pk, n in neighbors.items():
        caps = getattr(n, "capabilities", [])
        pk_str = str(pk)
        print(f"  {n.name} [{pk_str[:8]}] type={getattr(n, 'citizen_type', '?')} caps={caps}")
    print(f"\nProposing task: {task_type!r}")
    result = await create_task_and_wait(
        surface=surface,
        task_type=task_type,
        params={},
        bid_window_s=2.5,
        completion_timeout_s=30.0,
    )
    print("\n--- result ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
    if result["status"] == "completed":
        print(f"\n[OK] task completed by {result['winner_role']} in {result['duration_s']:.2f}s")
    else:
        print(f"\n[FAIL] task did not complete: status={result['status']}")


async def create_task_and_wait(
    surface,                          # GovernorCitizen instance
    task_type: str,
    params: dict,
    required_capabilities: list[str] | None = None,
    required_skills: list[str] | None = None,
    bid_window_s: float = 2.5,
    completion_timeout_s: float = 30.0,
) -> dict:
    """Submit a task, wait for the marketplace to settle, return a result dict.

    Returns a dict with at least:
      task_id, winner_pubkey, winner_role, winner_node, status,
      duration_s, follower_pubkey, follower_node.
    Raises asyncio.TimeoutError on completion_timeout_s expiry.
    """
    import asyncio

    task = surface.create_task(
        task_type=task_type,
        params=params,
        required_capabilities=required_capabilities or [],
        required_skills=required_skills or [],
    )
    # Existing marketplace.close_auction is called after bid_window_s by the
    # governor's auction loop; we just wait for it.
    await asyncio.sleep(bid_window_s)
    deadline = asyncio.get_event_loop().time() + completion_timeout_s
    while True:
        t = surface.marketplace.tasks.get(task.id)
        if t is None:
            raise RuntimeError(f"task {task.id} disappeared")
        if t.status.value in ("completed", "failed"):
            break
        if asyncio.get_event_loop().time() > deadline:
            raise asyncio.TimeoutError(f"task {task.id} did not complete in {completion_timeout_s}s")
        await asyncio.sleep(0.2)
    # Resolve winner role/node from the marketplace's bid log + neighbor table
    winner_pk = t.assigned_to or ""
    nbr = None
    if hasattr(surface, "neighbors"):
        nbr = surface.neighbors.get(winner_pk)
    elif hasattr(surface, "_neighbors"):
        nbr = surface._neighbors.get(winner_pk)
    return {
        "task_id": t.id,
        "winner_pubkey": winner_pk,
        "winner_role": getattr(nbr, "citizen_type", "") if nbr else "",
        "winner_node": getattr(nbr, "node_pubkey", "") if nbr else "",
        "status": t.status.value,
        "duration_s": (t.completed_at or 0.0) - t.created_at,
        "follower_pubkey": params.get("follower_pubkey", ""),
        "follower_node": params.get("follower_node", ""),
    }


async def _run_demo_main(task_type: str) -> None:
    """Construct a fresh GovernorCitizen, let it discover neighbors, run the demo."""
    surface = GovernorCitizen()
    await surface.start()
    try:
        # Give multicast discovery a moment to populate the neighbor table.
        await asyncio.sleep(3.0)
        await run_demo(surface, task_type=task_type)
    finally:
        await surface.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Governor CLI")
    subparsers = parser.add_subparsers(dest="cmd")

    # `demo` subcommand — one-shot end-to-end marketplace round.
    demo_parser = subparsers.add_parser(
        "demo",
        help="Walk through one full marketplace round end-to-end.",
    )
    demo_parser.add_argument(
        "--task-type",
        default="basic_gesture/wave",
        help="Task type to propose (default: basic_gesture/wave).",
    )

    # Default (no subcommand) — the existing interactive REPL.
    parser.add_argument("--leader-port", default="/dev/ttyACM0")
    parser.add_argument("--fps", type=float, default=25.0)
    args = parser.parse_args()

    if args.cmd == "demo":
        asyncio.run(_run_demo_main(args.task_type))
    else:
        asyncio.run(run_cli(args.leader_port, args.fps))
