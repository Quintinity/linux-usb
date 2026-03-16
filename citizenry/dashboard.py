"""armOS Citizenry Dashboard — Terminal UI.

Real-time TUI for monitoring all citizens in the neighborhood.
Uses only Python stdlib with raw ANSI escape codes (no curses).
Designed for the Surface Pro 7 governor station.

v2.0: Tasks, skills, contracts, warnings, immune memory sections.
"""

import asyncio
import os
import time
from collections import deque
from typing import Any

from .citizen import Citizen, Neighbor
from .protocol import MessageType, Envelope
from .identity import short_id
from .marketplace import TaskStatus


# -- ANSI escape codes --------------------------------------------------------

ESC = "\033"
CLEAR = f"{ESC}[2J"
HOME = f"{ESC}[H"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"

RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
DIM = f"{ESC}[2m"

GREEN = f"{ESC}[32m"
RED = f"{ESC}[31m"
YELLOW = f"{ESC}[33m"
CYAN = f"{ESC}[36m"
WHITE = f"{ESC}[37m"
BRIGHT_WHITE = f"{ESC}[97m"

BG_BLUE = f"{ESC}[44m"


# -- Motor names (SO-101) ----------------------------------------------------

MOTOR_NAMES = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


# -- Dashboard ----------------------------------------------------------------

class Dashboard:
    """Terminal dashboard for an armOS citizen.

    Hooks into the citizen's message dispatch to capture events,
    telemetry, and teleop statistics in real time.
    """

    def __init__(self, citizen: Citizen):
        self.citizen = citizen

        # Message log (newest at the end)
        self.messages: deque[str] = deque(maxlen=10)

        # Telemetry from REPORT messages with type="telemetry"
        self.telemetry: dict[str, dict[str, Any]] = {}

        # Teleop statistics
        self.teleop_stats: dict[str, Any] = {
            "active": False,
            "fps": 0.0,
            "frames": 0,
            "drops": 0.0,
            "leader": "",
            "follower": "",
        }

        # Constitution status
        self.constitution_received = False

        # Register handlers on the citizen
        citizen.on(MessageType.HEARTBEAT, self._on_heartbeat)
        citizen.on(MessageType.DISCOVER, self._on_discover)
        citizen.on(MessageType.ADVERTISE, self._on_advertise)
        citizen.on(MessageType.PROPOSE, self._on_propose)
        citizen.on(MessageType.ACCEPT_REJECT, self._on_accept_reject)
        citizen.on(MessageType.REPORT, self._on_report)
        citizen.on(MessageType.GOVERN, self._on_govern)

    # -- Message handlers (capture events for display) ------------------------

    def _ts(self) -> str:
        return time.strftime("%H:%M:%S")

    def _log(self, text: str) -> None:
        self.messages.append(f"{self._ts()} {text}")

    def _neighbor_name(self, pubkey: str) -> str:
        n = self.citizen.neighbors.get(pubkey)
        return n.name if n else short_id(pubkey)

    def _on_heartbeat(self, env: Envelope, addr: tuple) -> None:
        name = env.body.get("name", short_id(env.sender))
        health = env.body.get("health", 1.0)
        state = env.body.get("state", "?")
        self._log(f"HEARTBEAT {name} health={health} state={state}")

    def _on_discover(self, env: Envelope, addr: tuple) -> None:
        name = env.body.get("name", short_id(env.sender))
        sid = short_id(env.sender)
        self._log(f"DISCOVER {name} [{sid}]")

    def _on_advertise(self, env: Envelope, addr: tuple) -> None:
        name = env.body.get("name", short_id(env.sender))
        self._log(f"ADVERTISE {name} -> {self.citizen.name}")

    def _on_propose(self, env: Envelope, addr: tuple) -> None:
        task = env.body.get("task", "?")
        sender = self._neighbor_name(env.sender)
        if task == "teleop_frame":
            # Don't flood the log with every frame
            return
        self._log(f"PROPOSE {task} -> {sender}")

    def _on_accept_reject(self, env: Envelope, addr: tuple) -> None:
        accepted = env.body.get("accepted", False)
        task = env.body.get("task", "?")
        sender = self._neighbor_name(env.sender)
        verb = "ACCEPT" if accepted else "REJECT"
        self._log(f"{verb} {sender} -> {task}")

    def _on_report(self, env: Envelope, addr: tuple) -> None:
        body = env.body
        report_type = body.get("type", "")
        sender = self._neighbor_name(env.sender)

        if report_type == "telemetry":
            # Update motor telemetry
            motors = body.get("motors", {})
            for motor_name, data in motors.items():
                self.telemetry[motor_name] = data
        elif report_type == "teleop_stats":
            self.teleop_stats.update({
                "active": True,
                "fps": body.get("fps", 0.0),
                "frames": body.get("frames", 0),
                "drops": body.get("drops", 0.0),
            })
        elif report_type == "fault":
            detail = body.get("detail", "unknown")
            self._log(f"FAULT {sender}: {detail}")
        else:
            self._log(f"REPORT {sender} type={report_type}")

    def _on_govern(self, env: Envelope, addr: tuple) -> None:
        self.constitution_received = True
        self._log("GOVERN constitution received")

    # -- Render ---------------------------------------------------------------

    def _get_width(self) -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    def _box_top(self, w: int) -> str:
        return f"{CYAN}{BOLD}" + "\u2554" + "\u2550" * (w - 2) + "\u2557" + RESET

    def _box_bot(self, w: int) -> str:
        return f"{CYAN}{BOLD}" + "\u255a" + "\u2550" * (w - 2) + "\u255d" + RESET

    def _box_sep(self, w: int) -> str:
        return f"{CYAN}{BOLD}" + "\u2560" + "\u2550" * (w - 2) + "\u2563" + RESET

    def _box_line(self, text: str, w: int) -> str:
        """Render a line inside the box. Text is left-aligned, padded to width."""
        # Strip ANSI codes to compute visible length
        visible = self._visible_len(text)
        padding = max(0, w - 4 - visible)
        return f"{CYAN}{BOLD}\u2551{RESET} {text}{' ' * padding} {CYAN}{BOLD}\u2551{RESET}"

    def _visible_len(self, text: str) -> int:
        """Length of text with ANSI codes stripped."""
        import re
        return len(re.sub(r"\033\[[0-9;]*m", "", text))

    def _blank_line(self, w: int) -> str:
        return self._box_line("", w)

    def update(self) -> None:
        """Redraw the entire dashboard."""
        w = self._get_width()
        # Clamp to reasonable range
        w = max(68, min(w, 200))
        lines: list[str] = []

        c = self.citizen
        now = time.time()
        neighbor_count = len(c.neighbors)

        # Derive teleop state from the citizen itself
        self._update_teleop_from_citizen()

        # -- Header
        lines.append(self._box_top(w))

        title = f"{BOLD}{BRIGHT_WHITE}armOS CITIZENRY DASHBOARD"
        count = f"{neighbor_count} citizen{'s' if neighbor_count != 1 else ''}"
        lines.append(self._box_line(f"{title}{RESET}  {DIM}{count}{RESET}", w))

        governor_line = (
            f"{DIM}Governor:{RESET} {BOLD}{c.name}{RESET} "
            f"{DIM}[{c.short_id}]{RESET}"
        )
        # Try to get our IP from unicast transport
        try:
            ip = c._unicast._sock.getsockname()[0] if hasattr(c, '_unicast') else ""
        except Exception:
            ip = ""
        if ip:
            governor_line += f"  {DIM}{ip}{RESET}"
        const_status = f"  {GREEN}const:ok{RESET}" if self.constitution_received else f"  {YELLOW}const:pending{RESET}"
        governor_line += const_status
        lines.append(self._box_line(governor_line, w))

        # -- Neighbor table
        lines.append(self._box_sep(w))
        lines.append(self._blank_line(w))

        header_cols = (
            f"{BOLD}{'CITIZEN':<18} {'TYPE':<13} {'STATE':<9} "
            f"{'HEALTH':<8} {'LAST SEEN':<11} {'ADDR':<6}{RESET}"
        )
        lines.append(self._box_line(header_cols, w))
        lines.append(self._box_line(
            f"{DIM}" + "\u2500" * 18 + " " + "\u2500" * 13 + " " +
            "\u2500" * 9 + " " + "\u2500" * 8 + " " + "\u2500" * 11 + " " +
            "\u2500" * 6 + RESET, w
        ))

        if neighbor_count == 0:
            lines.append(self._box_line(f"{DIM}(no citizens discovered yet){RESET}", w))
        else:
            for pubkey, n in c.neighbors.items():
                ago = now - n.last_seen if n.last_seen > 0 else 999
                health_pct = int(n.health * 100)

                # Color coding
                if ago > 10:
                    state_color = RED
                    health_color = RED
                elif health_pct < 50 or ago > 5:
                    state_color = YELLOW
                    health_color = YELLOW
                else:
                    state_color = GREEN
                    health_color = GREEN

                # Short addr: just last octet
                addr_str = ""
                if n.addr and n.addr[0]:
                    parts = n.addr[0].split(".")
                    addr_str = f".{parts[-1]}" if len(parts) == 4 else n.addr[0][:6]

                ago_str = f"{ago:.1f}s ago" if ago < 100 else "offline"

                row = (
                    f"{BOLD}{n.name:<18}{RESET} "
                    f"{n.citizen_type:<13} "
                    f"{state_color}{n.state:<9}{RESET} "
                    f"{health_color}{health_pct}%{RESET}{'':>{4 - len(str(health_pct))}} "
                    f"{ago_str:<11} "
                    f"{addr_str:<6}"
                )
                lines.append(self._box_line(row, w))

                # Second line: short ID
                sid = short_id(pubkey)
                lines.append(self._box_line(
                    f"{'':>18} {DIM}[{sid}]{RESET}", w
                ))

                # Third line: capabilities
                if n.capabilities:
                    caps = ", ".join(n.capabilities)
                    lines.append(self._box_line(
                        f"  {DIM}caps: {caps}{RESET}", w
                    ))

                # v3.0: Mood label from emotional state
                if hasattr(n, 'emotional_state') and n.emotional_state is not None:
                    mood = n.emotional_state.mood
                    mood_colors = {"focused": GREEN, "tired": YELLOW, "exhausted": RED,
                                   "uncertain": YELLOW, "curious": CYAN, "energized": GREEN}
                    mc = mood_colors.get(mood, DIM)
                    lines.append(self._box_line(
                        f"  {mc}mood: {mood}{RESET}", w
                    ))

        lines.append(self._blank_line(w))

        # -- v2.0: Tasks section
        active_tasks = []
        if hasattr(c, 'marketplace'):
            active_tasks = c.marketplace.get_active_tasks()

        if active_tasks:
            lines.append(self._box_sep(w))
            lines.append(self._box_line(
                f"{BOLD}TASKS{RESET} ({len(active_tasks)} active)", w
            ))
            for task in active_tasks[:5]:  # Show at most 5
                status_str = task.status.value.upper()
                if task.status == TaskStatus.BIDDING:
                    sc = YELLOW
                elif task.status == TaskStatus.EXECUTING:
                    sc = GREEN
                else:
                    sc = WHITE
                bids = len(c.marketplace.bids.get(task.id, []))
                assigned = task.assigned_to[:8] if task.assigned_to else "(auction)"
                lines.append(self._box_line(
                    f"[{task.id}] {task.type:<14} {sc}{status_str:<10}{RESET} "
                    f"{assigned:<14} prio:{task.priority:.1f}  {bids} bids", w
                ))
            lines.append(self._blank_line(w))

        # -- v2.0: Contracts section
        active_contracts = c.contracts.get_active()
        composite_caps = getattr(c, 'composite_capabilities', [])
        if active_contracts or composite_caps:
            lines.append(self._box_sep(w))
            if active_contracts:
                lines.append(self._box_line(
                    f"{BOLD}CONTRACTS{RESET} ({len(active_contracts)} active)", w
                ))
                for contract in active_contracts:
                    provider_name = self._citizen_name_by_key(contract.provider)
                    consumer_name = self._citizen_name_by_key(contract.consumer)
                    health_str = f"{GREEN}ok{RESET}" if contract.is_healthy() else f"{RED}broken{RESET}"
                    lines.append(self._box_line(
                        f"{provider_name} <-> {consumer_name}: "
                        f"{BOLD}{contract.composite_capability}{RESET}  health:{health_str}", w
                    ))
            if composite_caps:
                lines.append(self._box_line(
                    f"{BOLD}COMPOSITE CAPABILITIES{RESET}", w
                ))
                lines.append(self._box_line(
                    f"  {CYAN}{', '.join(composite_caps)}{RESET}", w
                ))
            lines.append(self._blank_line(w))

        # -- Teleop section
        lines.append(self._box_sep(w))
        lines.append(self._box_line(f"{BOLD}TELEOP{RESET}", w))

        ts = self.teleop_stats
        if ts["active"]:
            status_color = GREEN
            status_text = "STREAMING"
        else:
            status_color = DIM
            status_text = "INACTIVE"

        fps_str = f"{ts['fps']:.1f}" if ts["fps"] else "0.0"
        drops_str = f"{ts['drops']:.0f}%" if isinstance(ts["drops"], (int, float)) else str(ts["drops"])

        lines.append(self._box_line(
            f"Status: {status_color}{status_text}{RESET}  "
            f"FPS: {BOLD}{fps_str}{RESET}  "
            f"Frames: {ts['frames']}  "
            f"Drops: {drops_str}", w
        ))

        if ts.get("leader") or ts.get("follower"):
            lines.append(self._box_line(
                f"Leader: {BOLD}{ts.get('leader', '?')}{RESET} -> "
                f"Follower: {BOLD}{ts.get('follower', '?')}{RESET}", w
            ))

        lines.append(self._blank_line(w))

        # -- Telemetry section
        lines.append(self._box_sep(w))

        # Figure out which citizen the telemetry is for
        telemetry_source = ""
        for n in c.neighbors.values():
            if n.citizen_type == "manipulator":
                telemetry_source = n.name
                break

        lines.append(self._box_line(
            f"{BOLD}TELEMETRY{RESET}"
            + (f" ({telemetry_source})" if telemetry_source else ""), w
        ))

        if self.telemetry:
            motor_header = (
                f"{BOLD}{'Motor':<18} {'Voltage':>8} {'Current':>9} "
                f"{'Load':>6} {'Temp':>7} {'Status':<8}{RESET}"
            )
            lines.append(self._box_line(motor_header, w))

            for motor_name in MOTOR_NAMES:
                data = self.telemetry.get(motor_name)
                if data is None:
                    lines.append(self._box_line(
                        f"{motor_name:<18} {DIM}---{RESET}", w
                    ))
                    continue

                voltage = data.get("voltage", 0)
                current = data.get("current", 0)
                load = data.get("load", 0)
                temp = data.get("temperature", 0)
                status = data.get("status", "OK")

                # Color code status
                if status != "OK":
                    sc = RED
                elif temp > 55 or load > 80:
                    sc = YELLOW
                else:
                    sc = GREEN

                lines.append(self._box_line(
                    f"{motor_name:<18} "
                    f"{voltage:>6.1f}V "
                    f"{current:>6.0f}mA "
                    f"{load:>4.0f}% "
                    f"{temp:>4.0f}\u00b0C "
                    f"  {sc}{status:<8}{RESET}", w
                ))
        else:
            lines.append(self._box_line(f"{DIM}(awaiting telemetry){RESET}", w))

        # Warnings (v2.0: includes mycelium warnings)
        warnings = self._collect_warnings()
        lines.append(self._blank_line(w))
        if warnings:
            for warn in warnings:
                lines.append(self._box_line(f"{YELLOW}WARNING: {warn}{RESET}", w))
        else:
            lines.append(self._box_line(f"{DIM}WARNINGS: (none){RESET}", w))

        # v2.0: Mycelium active warnings
        mycelium_count = c.mycelium.active_count()
        if mycelium_count > 0:
            for mw in c.mycelium.active_warnings[:3]:
                age = time.time() - mw.timestamp
                lines.append(self._box_line(
                    f"{RED}MYCELIUM: {mw.detail} ({mw.severity.name}) {age:.0f}s ago{RESET}", w
                ))

        # v2.0: Immune memory summary
        immune_count = len(c.immune_memory.get_all())
        lines.append(self._box_line(
            f"{DIM}IMMUNE: {immune_count} patterns{RESET}", w
        ))

        # -- Messages section
        lines.append(self._box_sep(w))
        lines.append(self._box_line(f"{BOLD}MESSAGES{RESET} (last 10)", w))

        if self.messages:
            for msg in self.messages:
                lines.append(self._box_line(f"{DIM}{msg}{RESET}", w))
        else:
            lines.append(self._box_line(f"{DIM}(no messages yet){RESET}", w))

        # -- Footer
        lines.append(self._box_bot(w))

        # Write to terminal in one shot
        output = HOME + "\n".join(lines) + "\n"
        print(output, end="", flush=True)

    # -- Helpers --------------------------------------------------------------

    def _update_teleop_from_citizen(self) -> None:
        """Pull teleop stats directly from the citizen if it has them."""
        c = self.citizen

        # SurfaceCitizen (governor) has _teleop_active, _frames_sent
        if hasattr(c, '_teleop_active') and c._teleop_active:
            self.teleop_stats["active"] = True
            self.teleop_stats["frames"] = getattr(c, '_frames_sent', 0)
            self.teleop_stats["leader"] = c.name

            elapsed = time.time() - getattr(c, '_teleop_start', time.time())
            if elapsed > 0:
                self.teleop_stats["fps"] = self.teleop_stats["frames"] / elapsed

            # Find follower name
            fk = getattr(c, '_follower_key', None)
            if fk and fk in c.neighbors:
                self.teleop_stats["follower"] = c.neighbors[fk].name

        # PiCitizen (follower) has _teleop_active, _frames_received, _frames_written
        if hasattr(c, '_frames_received') and hasattr(c, '_frames_written'):
            fr = c._frames_received
            fw = c._frames_written
            if fr > 0:
                self.teleop_stats["frames"] = fr
                drop_rate = (1.0 - fw / fr) * 100
                self.teleop_stats["drops"] = drop_rate

                elapsed = time.time() - getattr(c, '_teleop_start', time.time())
                if elapsed > 0:
                    self.teleop_stats["fps"] = fr / elapsed

            gk = getattr(c, '_governor_key', None)
            if gk and gk in c.neighbors:
                self.teleop_stats["leader"] = c.neighbors[gk].name
            self.teleop_stats["follower"] = c.name

        if hasattr(c, '_teleop_active') and not c._teleop_active:
            self.teleop_stats["active"] = False

    def _citizen_name_by_key(self, pubkey: str) -> str:
        """Look up citizen name by pubkey."""
        if pubkey == self.citizen.pubkey:
            return self.citizen.name
        n = self.citizen.neighbors.get(pubkey)
        return n.name if n else short_id(pubkey)

    def _collect_warnings(self) -> list[str]:
        """Scan telemetry and neighbor state for warnings."""
        warnings: list[str] = []
        now = time.time()

        # Neighbor timeouts
        for n in self.citizen.neighbors.values():
            ago = now - n.last_seen if n.last_seen > 0 else 999
            if ago > 10:
                warnings.append(f"{n.name} not seen for {ago:.0f}s")
            elif n.health < 0.5:
                warnings.append(f"{n.name} health={n.health:.0%}")

        # Motor warnings
        for motor_name, data in self.telemetry.items():
            temp = data.get("temperature", 0)
            load = data.get("load", 0)
            voltage = data.get("voltage", 99)
            status = data.get("status", "OK")

            if status != "OK":
                warnings.append(f"{motor_name}: {status}")
            if temp > 55:
                warnings.append(f"{motor_name}: temp {temp}\u00b0C")
            if load > 80:
                warnings.append(f"{motor_name}: load {load:.0f}%")
            if voltage < 6.5:
                warnings.append(f"{motor_name}: low voltage {voltage:.1f}V")

        return warnings


# -- Async entry point --------------------------------------------------------

async def run_dashboard(citizen: Citizen) -> None:
    """Run the dashboard at 2Hz until cancelled.

    Usage:
        dashboard_task = asyncio.create_task(run_dashboard(citizen))
        # ... later ...
        dashboard_task.cancel()
    """
    dash = Dashboard(citizen)

    # Clear screen and hide cursor
    print(CLEAR + HIDE_CURSOR, end="", flush=True)

    try:
        while True:
            dash.update()
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    finally:
        # Restore cursor
        print(SHOW_CURSOR + RESET, end="", flush=True)
