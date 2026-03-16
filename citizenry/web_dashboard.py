"""Web Dashboard — real-time fleet monitoring via HTTP.

Serves a single-page dashboard at http://localhost:8080 with live data
from the governor citizen. Uses aiohttp (already installed).

Usage:
    # Start alongside governor:
    dashboard = WebDashboard(governor_citizen, port=8080)
    await dashboard.start()
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from aiohttp import web

from .marketplace import TaskStatus


STATIC_DIR = Path(__file__).parent / "static"


class WebDashboard:
    """HTTP dashboard for the armOS citizenry."""

    def __init__(self, citizen, port: int = 8080):
        self.citizen = citizen
        self.port = port
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._events: list[dict] = []  # Recent events for SSE

    async def start(self):
        self._app = web.Application()
        self._app.router.add_get("/", self._index)
        self._app.router.add_get("/api/status", self._api_status)
        self._app.router.add_get("/api/events", self._api_events)
        self._app.router.add_post("/api/calibrate", self._api_calibrate)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()

    async def stop(self):
        if self._runner:
            await self._runner.cleanup()

    def add_event(self, event_type: str, data: dict):
        """Add an event for SSE clients."""
        self._events.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        })
        # Keep last 100 events
        if len(self._events) > 100:
            self._events = self._events[-100:]

    # ── Handlers ──

    async def _index(self, request: web.Request) -> web.Response:
        html_path = STATIC_DIR / "dashboard.html"
        if html_path.exists():
            return web.Response(text=html_path.read_text(), content_type="text/html")
        return web.Response(text="<h1>armOS Citizenry Dashboard</h1><p>static/dashboard.html not found</p>",
                            content_type="text/html")

    async def _api_status(self, request: web.Request) -> web.Response:
        c = self.citizen
        now = time.time()

        neighbors = {}
        for pk, n in c.neighbors.items():
            neighbors[pk[:8]] = {
                "name": n.name,
                "type": n.citizen_type,
                "capabilities": n.capabilities,
                "health": n.health,
                "state": n.state,
                "addr": f"{n.addr[0]}:{n.addr[1]}",
                "last_seen_ago": round(now - n.last_seen, 1) if n.last_seen > 0 else None,
                "presence": n.presence.value,
                "has_constitution": n.has_constitution,
                "mood": n.emotional_state.mood if hasattr(n, 'emotional_state') and n.emotional_state else None,
                "emotional": n.emotional_state.to_dict() if hasattr(n, 'emotional_state') and n.emotional_state else None,
            }

        tasks = []
        if hasattr(c, 'marketplace'):
            for t in c.marketplace.get_active_tasks():
                assigned_name = None
                if t.assigned_to:
                    assigned_name = next(
                        (n.name for n in c.neighbors.values() if n.pubkey == t.assigned_to),
                        t.assigned_to[:8]
                    )
                tasks.append({
                    "id": t.id,
                    "type": t.type,
                    "status": t.status.value,
                    "priority": t.priority,
                    "assigned_to": assigned_name,
                    "bids": len(c.marketplace.bids.get(t.id, [])),
                })

        completed = []
        if hasattr(c, 'marketplace'):
            for t in c.marketplace.completed_tasks[-10:]:
                assigned_name = next(
                    (n.name for n in c.neighbors.values() if n.pubkey == t.assigned_to),
                    t.assigned_to[:8]
                ) if t.assigned_to else None
                completed.append({
                    "id": t.id,
                    "type": t.type,
                    "assigned_to": assigned_name,
                    "duration_ms": t.result.get("duration_ms", 0) if t.result else 0,
                    "xp_earned": t.result.get("xp_earned", 0) if t.result else 0,
                })

        contracts = []
        for ct in c.contracts.get_active():
            prov = next((n.name for n in c.neighbors.values() if n.pubkey == ct.provider), ct.provider[:8])
            cons = next((n.name for n in c.neighbors.values() if n.pubkey == ct.consumer), ct.consumer[:8])
            contracts.append({
                "id": ct.id,
                "provider": prov,
                "consumer": cons,
                "composite": ct.composite_capability,
                "healthy": ct.is_healthy(),
            })

        composites = getattr(c, 'composite_capabilities', [])

        telemetry = {}
        if hasattr(c, 'follower_telemetry'):
            for pk, t in c.follower_telemetry.items():
                name = next((n.name for n in c.neighbors.values() if n.pubkey == pk), pk[:8])
                telemetry[name] = t

        warnings = [
            {"severity": w.severity.name, "detail": w.detail, "age": round(now - w.timestamp)}
            for w in c.mycelium.active_warnings
        ]

        emotional = c.emotional_state.to_dict() if hasattr(c, 'emotional_state') else {}
        mood = c.emotional_state.mood if hasattr(c, 'emotional_state') else "unknown"

        messages = [
            {"time": m.timestamp, "type": m.msg_type, "sender": m.sender, "detail": m.detail}
            for m in list(c.message_log)[-15:]
        ]

        # v4.0: biological subsystem stats
        v4_stats = {}
        try:
            v4_stats = {
                "soul": c.soul.to_dict() if hasattr(c, 'soul') else {},
                "memory": c.memory.stats() if hasattr(c, 'memory') else {},
                "growth": c.growth_tracker.stats() if hasattr(c, 'growth_tracker') else {},
                "sleep": c.sleep_engine.stats() if hasattr(c, 'sleep_engine') else {},
                "metabolism": c.metabolism_tracker.state.to_dict() if hasattr(c, 'metabolism_tracker') else {},
                "pain": {"zones": c.pain_memory.active_zones(), "events": c.pain_memory.total_pain_events()} if hasattr(c, 'pain_memory') else {},
                "reflexes": c.reflex_engine.get_stats() if hasattr(c, 'reflex_engine') else {},
                "performance": {
                    skill: round(c.performance.success_rate(skill), 2)
                    for skill in list(c.performance.records.keys())[:10]
                } if hasattr(c, 'performance') else {},
            }
        except Exception:
            pass

        return web.json_response({
            "governor": {
                "name": c.name,
                "id": c.short_id,
                "state": c.state,
                "uptime": round(now - c.start_time) if c.start_time else 0,
                "messages_sent": c.messages_sent,
                "messages_received": c.messages_received,
            },
            "neighbors": neighbors,
            "tasks_active": tasks,
            "tasks_completed": completed,
            "contracts": contracts,
            "composites": composites,
            "telemetry": telemetry,
            "warnings": warnings,
            "immune_count": len(c.immune_memory.get_all()),
            "emotional": emotional,
            "mood": mood,
            "messages": messages,
            "biological": v4_stats,
        })

    async def _api_calibrate(self, request: web.Request) -> web.Response:
        """Trigger calibration on an arm citizen via POST."""
        try:
            data = await request.json()
        except Exception:
            data = {}
        mode = data.get("mode", "staged")
        c = self.citizen

        # Find an arm citizen
        arm = next((n for n in c.neighbors.values() if "6dof_arm" in n.capabilities), None)
        if not arm:
            return web.json_response({"error": "no arm citizen found"}, status=404)

        c.send_propose(arm.pubkey, {"task": "self_calibrate", "mode": mode}, arm.addr)
        self.add_event("calibration_started", {"arm": arm.name, "mode": mode})
        return web.json_response({"status": "started", "arm": arm.name, "mode": mode})

    async def _api_events(self, request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        await response.prepare(request)

        last_idx = len(self._events)
        try:
            while True:
                if len(self._events) > last_idx:
                    for evt in self._events[last_idx:]:
                        data = json.dumps(evt)
                        await response.write(f"data: {data}\n\n".encode())
                    last_idx = len(self._events)
                await asyncio.sleep(0.5)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        return response
