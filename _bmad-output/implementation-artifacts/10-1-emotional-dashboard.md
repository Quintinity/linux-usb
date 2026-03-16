---
story_id: "10.1"
story_key: "10-1-emotional-dashboard"
epic: "Epic 10: Emotional State in Dashboard"
status: ready-for-dev
created: 2026-03-16
---

# Story: Emotional State Display in Web + TUI Dashboards

## User Story
As a fleet operator, I want to see each citizen's mood (focused, tired, curious) on the dashboard, so I can understand fleet health at a glance.

## Acceptance Criteria
- Web dashboard shows mood label per citizen with color coding
- Web dashboard shows fatigue/confidence/curiosity bars for governor
- TUI dashboard shows mood label next to each neighbor's state
- Neighbor emotional state received via heartbeat `emotional_state` field
- Governor's own emotional state computed locally

## Technical Requirements

### Files to modify
- `citizenry/dashboard.py` — add mood label to neighbor rows in TUI
- `citizenry/static/dashboard.html` — already shows governor mood; add per-citizen mood
- `citizenry/web_dashboard.py` — include neighbor emotional state in API response
- `citizenry/citizen.py` — parse `emotional_state` from neighbor heartbeats into Neighbor dataclass

### Existing code to reuse
- `emotional.EmotionalState.mood` property — returns mood label string
- `emotional.EmotionalState.from_dict()` — parse from heartbeat body
- `citizen._handle_heartbeat()` — already processes heartbeat body fields
- `Neighbor` dataclass — add `emotional_state` field

## Testing
- Unit test: emotional state parsed from heartbeat body
- Manual: verify mood labels appear in web and TUI dashboards
