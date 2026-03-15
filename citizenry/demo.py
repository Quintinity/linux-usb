#!/usr/bin/env python3
"""armOS Citizenry — Live Demo.

Runs the full protocol stack: discovery, constitution, teleop, telemetry.
"""

import asyncio
import time
from .surface_citizen import SurfaceCitizen

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def bar(pct, width=20):
    filled = int(pct / 100 * width)
    return f"{GREEN}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


async def run_demo(leader_port="/dev/ttyACM0", fps=30.0):
    surface = SurfaceCitizen(leader_port=leader_port, teleop_fps=fps)
    await surface.start()

    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  armOS CITIZENRY — LIVE DEMO                                ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()

    # ── Phase 1: Discovery ──
    print(f"{BOLD}▸ Phase 1: Discovery{RESET}")
    t0 = time.time()
    while not surface.neighbors and time.time() - t0 < 8:
        await asyncio.sleep(0.1)

    if not surface.neighbors:
        print(f"  {RED}✗ No citizens found after 8s{RESET}")
        await surface.stop()
        return

    n = list(surface.neighbors.values())[0]
    elapsed = time.time() - t0
    caps = ", ".join(n.capabilities)
    print(f"  {GREEN}✓{RESET} Pi found in {elapsed:.2f}s — {n.name} @ {n.addr[0]}")
    print(f"    Capabilities: {CYAN}{caps}{RESET}")
    print(f"    Identity: [{n.pubkey[:16]}...]")
    print()

    # ── Phase 2: Constitution ──
    print(f"{BOLD}▸ Phase 2: Constitutional Governance{RESET}")
    await asyncio.sleep(1)
    if surface.constitution:
        c = surface.constitution
        print(f"  {GREEN}✓{RESET} Constitution v{c['version']} signed by governor [{surface.short_id}]")
        for art in c.get("articles", []):
            print(f"    Article {art['number']}: {DIM}{art['title']}{RESET}")
        limits = c.get("servo_limits", {})
        mt = limits.get("max_torque", "?")
        pc = limits.get("protection_current", "?")
        print(f"    Servo limits: max_torque={mt}, protection_current={pc}mA")

        n = list(surface.neighbors.values())[0]
        if n.has_constitution:
            print(f"    Follower status: {GREEN}APPLIED{RESET}")
        else:
            print(f"    Follower status: {YELLOW}PENDING{RESET}")
    print()

    # ── Phase 3: Teleop ──
    print(f"{BOLD}▸ Phase 3: Cross-Network Teleop{RESET}")
    print(f"  Streaming leader arm → follower arm over citizenry protocol...")
    print()

    for i in range(12):
        await asyncio.sleep(1)
        n = list(surface.neighbors.values())[0]
        telem = surface.follower_telemetry.get(n.pubkey, {})
        frames = surface._frames_sent
        elapsed_t = time.time() - surface._teleop_start if surface._teleop_start else 1
        fps_actual = frames / elapsed_t if elapsed_t > 0 else 0

        motors = telem.get("motors", {})

        line = f"  {DIM}[{i+1:2d}s]{RESET} {BOLD}{frames:>5d}{RESET} frames  {GREEN}{fps_actual:4.1f}{RESET} FPS  "

        if telem:
            v = telem.get("min_voltage")
            t = telem.get("max_temperature")
            tc = telem.get("total_current_ma") or 0

            v_str = f"{v:.1f}V" if v else "?"
            t_color = YELLOW if (t and t > 45) else GREEN
            t_str = f"{t_color}{t:.0f}°C{RESET}" if t else "?"

            sl = motors.get("shoulder_lift", {})
            load = sl.get("load_pct") or 0
            load_abs = abs(load)

            line += f"V={v_str}  T={t_str}  I={tc:.0f}mA  "
            line += f"shoulder_lift: {bar(load_abs, 10)} {load_abs:.0f}%"
        else:
            line += f"{DIM}awaiting telemetry...{RESET}"

        print(line)

    print()

    # ── Phase 4: Safety ──
    print(f"{BOLD}▸ Phase 4: Safety & Telemetry Report{RESET}")
    n = list(surface.neighbors.values())[0]
    telem = surface.follower_telemetry.get(n.pubkey, {})

    if telem:
        motors = telem.get("motors", {})
        print(f"  {BOLD}{'Motor':<18} {'Voltage':>8} {'Current':>9} {'Load':>7} {'Temp':>7} {'Status':<8}{RESET}")
        print(f"  {DIM}{'─'*18} {'─'*8} {'─'*9} {'─'*7} {'─'*7} {'─'*8}{RESET}")

        for mname in ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]:
            m = motors.get(mname, {})
            v = m.get("voltage")
            c = m.get("current_ma") or 0
            l = m.get("load_pct") or 0
            t = m.get("temperature_c") or 0
            s = m.get("status", -1)

            v_str = f"{v:.1f}V" if v else "   ?"
            c_str = f"{abs(c):.0f}mA"
            l_str = f"{abs(l):.1f}%"
            t_color = YELLOW if t > 45 else GREEN
            t_str = f"{t_color}{t:.0f}°C{RESET}"

            if s == 0:
                s_str = f"{GREEN}OK{RESET}"
            elif s > 0:
                s_str = f"{RED}ERR:{s}{RESET}"
            else:
                s_str = f"{DIM}?{RESET}"

            print(f"  {mname:<18} {v_str:>8} {c_str:>9} {l_str:>7} {t_str:>7}   {s_str}")

    violations = surface.safety_violations
    print()
    if violations:
        for v in violations:
            print(f"  {RED}⚠ {v['violation']}{RESET}")
    else:
        print(f"  {GREEN}✓ No safety violations{RESET}")
    print()

    # ── Phase 5: Stats ──
    print(f"{BOLD}▸ Phase 5: Protocol Statistics{RESET}")
    total_frames = surface._frames_sent
    elapsed_total = time.time() - surface._teleop_start if surface._teleop_start else 1
    avg_fps = total_frames / elapsed_total if elapsed_total > 0 else 0

    print(f"  Messages sent:     {surface.messages_sent}")
    print(f"  Messages received: {surface.messages_received}")
    print(f"  Teleop frames:     {total_frames}")
    print(f"  Average FPS:       {avg_fps:.1f}")
    print(f"  Presence:          {n.presence.value}")
    print(f"  Uptime:            {elapsed_total:.1f}s")
    print()

    print(f"{BOLD}▸ Message Log{RESET}")
    for entry in surface.message_log:
        print(f"  {DIM}{entry.timestamp}{RESET} {BOLD}{entry.msg_type:<12}{RESET} {entry.sender} — {entry.detail}")

    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  Two citizens. One protocol. The citizenry lives.           ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")

    await surface.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--leader-port", default="/dev/ttyACM0")
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args()
    asyncio.run(run_demo(args.leader_port, args.fps))
