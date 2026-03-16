---
story_id: "9.1"
story_key: "9-1-will-enhancement"
epic: "Epic 9: Will Enhancement — Governor Absorption"
status: ready-for-dev
created: 2026-03-16
---

# Story: Governor Will Absorption — Task Re-listing + XP Preservation

## User Story
As a governor, when a citizen dies and broadcasts its will, I want to automatically re-auction its tasks and preserve its XP in the fleet genome, so that no work or knowledge is lost.

## Acceptance Criteria
- Governor receives will REPORT and extracts task/XP/contract data
- Dead citizen's active task is re-listed in marketplace with partial_results
- Dead citizen's XP is merged into fleet genome
- Active contracts are broken cleanly, partners notified
- Will archived to disk, viewable via `wills` CLI command
- Dashboard shows will receipt event

## Technical Requirements

### Files to modify
- `citizenry/surface_citizen.py` — extend `_handle_report` for `type: "will"`
- `citizenry/governor_cli.py` — add `wills` command
- `citizenry/genome.py` — add `merge_xp_into_fleet()` method
- `citizenry/persistence.py` — add will archive save/load

### Existing code to reuse
- `will.CitizenWill.from_report_body()` — parse will from REPORT
- `marketplace.fail_task()` — re-auction with partial progress
- `contracts.remove_citizen()` — break contracts on citizen death
- `genome.compute_fleet_average()` — fleet genome computation
- `persistence.save_*/load_*` pattern — atomic JSON writes

## Testing
- Unit test: will received → task re-listed, XP merged, contracts broken
- Integration test: citizen stop() → will broadcast → governor absorbs
