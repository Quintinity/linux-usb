---
title: Sub-1 follow-up backlog
date: 2026-05-01
status: open — defer to Sub-2 / later
---

# Sub-1 (Constitution v2 + Identity Model) — open follow-ups

Items the final code review surfaced that did NOT block Sub-1 shipping but
should be addressed during Sub-2 mesh hardening or earlier.

## I-3 — `policy_pinning` semantic collision (medium priority)

`Constitution.policy_pinning` is typed `dict[str, str]` (just the
hf_revision_sha) per spec §7.4. `Citizen.policy_pinning` (runtime, populated
by `GOVERN(pin_policy, ...)`) is `dict[str, dict]` (hf_revision_sha +
aibom_url + rekor_log_index). Same name, different shapes.

Additionally, when a Constitution is received via `_on_constitution_received`,
the `policy_pinning` field is NOT synced into runtime state. So Constitution-
borne pins are silently ignored.

**Recommendation for Sub-2:** Either (a) widen the Constitution field's value
type to `dict[str, dict]` to match runtime, or (b) rename one side. Then add
a sync path in `_on_constitution_received` that merges Constitution pins into
the runtime dict. Sub-7 (safety-mcp) and Sub-9 (provenance pipeline) will
both need this resolved.

## M-2 — `_handle_govern` is approaching dispatch-table threshold

After Tasks 4-6 the if/elif chain is ~140 lines. Sub-2 + Sub-7 will likely
each add a body type. Recommend refactoring to a `_GOVERN_HANDLERS` dispatch
dict before the chain reaches 200 lines.

## M-3 — `governor_pubkey_short` UI label

`citizenry/cli/governor_emex_tablet.py:state_snapshot` exposes
`governor_pubkey_short` which after Sub-1 reflects the Authority key (via the
mirror), not the per-node governor key. Rename to `authority_pubkey_short`
in the snapshot and update `governor_emex_web.html` correspondingly.

## M-4 — `migrate_v1_dict` silently accepts mixed-shape inputs

If a v1 dict already has `authority_pubkey` (corrupt/half-migrated state),
`migrate_v1_dict` re-signs without warning. Add a guard that raises on
conflict, or logs.

## I-3.b — Constitution-borne pins do not flow into runtime state

Same root issue as I-3. When `_on_constitution_received` runs on a citizen,
the new v2 fields (`tool_manifest_pinning`, `policy_pinning`,
`embassy_topics`, `compliance_artefacts`) on the Constitution document do
NOT get merged into the citizen's runtime equivalent state. The citizen
only updates its runtime pins via subsequent GOVERN messages. This is a
design gap — a constitutional pin should be honored from the moment the
Constitution is applied. Fix: in `_on_constitution_received`, for each of
the 4 new dict fields, merge into the corresponding runtime dict.
