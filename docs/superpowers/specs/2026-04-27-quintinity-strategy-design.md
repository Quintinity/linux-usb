# Quintinity strategy design — auditable AI for manufacturing

**Date:** 2026-04-27
**Author:** Bradley Festraets, with Claude (Opus 4.7, 1M ctx) as drafting partner
**Status:** Draft for review
**Forcing function:** EMEX 2026 — 26–28 May 2026, Auckland Showgrounds, 3×3m stand
**Companion docs:**
- `~/linux-usb/docs/specs/2026-04-27-smolvla-citizen-design.md` (citizenry SmolVLA spec)
- `~/linux-usb/docs/plans/2026-04-27-smolvla-citizen.md` (citizenry SmolVLA plan)
- (in `Quintinity/pcrottet-tool-data-management`) `docs/superpowers/specs/2026-04-19-emex-shopos-pitch-design.md`

## 1. The bet

Quintinity is building the **auditable execution layer for AI-native manufacturing**. The category does not yet exist, but the four pieces that compose it have all become real in the last 12 months:

1. Live shop-data systems with AI diagnostics — Quintinity's TDM / Hone / ShopOS, deployed in production at Accord Precision (NZ ISO/FDA-certified medical-device + aerospace machine shop).
2. Low-cost dexterous manipulator hardware — SO-101 Feetech servo arms, Pi 5, Jetson Orin Nano, XIAO ESP32S3 cameras.
3. Pretrained vision-language-action policies — Hugging Face SmolVLA 450M and successors.
4. Hosted agent infrastructure — Anthropic's Claude Managed Agents (April 2026), Model Context Protocol (MCP), Skills, Memory Tool, extended thinking, prompt caching.

Quintinity's edge is having all four under one roof at one customer, plus a decentralised signed-protocol fleet OS (citizenry, this repo) that can govern policy execution across heterogeneous hardware. The "profitable, ethical, secure, safe" constraint becomes the **positioning moat**: every decision traced, every action approved, every robot signed. Black-box AI vendors and legacy MES (Manufacturing Execution Systems) can both lose to that story. The wedge is NZ light/contract manufacturing; the moat is the protocol stack underneath; the standards play emerges naturally over 2–3 years if the wedge proves out — and we do not bet the company on it before then.

## 2. The stack

| Layer | Role | What lives here | Status |
|---|---|---|---|
| **L4 — Standards / SDK** | Open spec, optional foundation play | Citizen-MCP spec, published Skills, reference firmware | **Future**. Do not pursue actively before 2027. |
| **L3 — Auditable Agentic Fleet** | Cross-customer, cross-vendor orchestration | Quin-agent (Managed Agents), MCP bridge to citizens, decision ledger, 4-tier action gating, 6-layer memory | **12-month build**, harvested from `Quin-AI-Assistant/quintinity-v2`. |
| **L2 — ShopOS (TDM + Hone)** | The wedge product. Sells today. | Tool/transaction tracking, scrap analytics, NL search via Claude, GibbsCAM integration, kiosk + admin UIs | **Live in production at Accord. EMEX-ready.** |
| **L1 — Citizenry mesh** | Edge execution layer | 7-message signed UDP-multicast protocol (HEARTBEAT, DISCOVER, ADVERTISE, PROPOSE, ACCEPT_REJECT, REPORT, GOVERN), Constitution governance, capability advertise, marketplace bidding, SmolVLA-as-citizen | **Well-progressed. EMEX cell 2.** |
| **L0 — Hardware** | The physical work | SO-101 Feetech servo arms, Pi 5, Jetson Orin Nano (untested live), XIAO ESP32S3 cameras (Phases 0–3 shipped), Hailo-8L (queued) | **Working triplet on Surface + Pi + XIAO.** |

### Keep / harvest / archive

**Keep:**
- TDM/Hone (live), citizenry (becomes L1).
- Tab-runner methodology (Bradley's prompt-engineering rubric across `tab-runner-{antigravity-ide,claude-app,codex-cli,githubcopilot-ide}`) — distil into Quintinity's internal "prompt authoring guide", apply to Quin-agent system prompts.
- `quintinity-ledger` — internal NZ tax/payroll/GST compliance, live, do not touch.

**Harvest from `Quin-AI-Assistant/quintinity-v2` into citizenry + Hone over 90 days post-EMEX:**
- Hash-chained decision ledger (tamper-evident audit log).
- 4-tier action gating: observe → suggest → act-with-approval → act-autonomously.
- 6-layer memory architecture (episodic, semantic, procedural, social, working, curated) — episodic + semantic + procedural ship first; the rest if needed.
- MCP-native interface — refactor citizenry so each citizen runs an MCP server natively (not a side process). Reuse v2's tool-schema patterns.
- Quin-agent companion shape — reused for diagnostic + scheduler agents in Hone.

**Archive:**
- This week: `Quintinity/tabflow-guard`, `Quintinity/full-bloom-build`, `Quintinity/Duran-Playground`, `Quintinity/ubiquitous-fortnight`. Lovable experiments, paused 70+ days, no roadmap link. Set GitHub `archived: true`.
- This week: `BradleyFestraets/az-acs-demo`, `BradleyFestraets/K2-Workflow-API`. 5+ years dormant.
- After IP harvest (~August 2026): `Quin-AI-Assistant/quintinity-v2` main branch. Mark superseded.
- Q4 2026: the four `tab-runner-*` repos once methodology is internal.

**Do not kill but explicitly de-prioritise:**
- `Crowdiant-AI` — separate venture (multi-tenant SaaS for hospitality). Decide by 2026-09-30: spin out, sell, or pause.
- Government consulting (`Takutai-Moana-v2`, `MBIE-Determinations`) — capped at 1 day/week per person across the team. Runway revenue only, never roadmap influence.

**Continuous policy:** any repo with no commits in 90 days gets archived. Quarterly review.

## 3. The 29-day EMEX track

**Sprint window:** 2026-04-27 → 2026-05-25 (rehearsal). Show: 2026-05-26 to 28.
**Stand:** 3×3m, three walls, three cells. Triptych demo: shop data → AI reasoning → robot execution, on one signed protocol.

### The triptych

| Cell | Wall | What visitors see | What it sells |
|---|---|---|---|
| **1 — ShopOS / Hone live** | Left | 24" touchscreen running TDM kiosk + Quin chat panel. Claude diagnosing live (anonymised) Accord data: cost-per-part, scrap clusters, vendor comparisons. Streaming responses with adaptive thinking visible. Decision ledger entry written for every recommendation. | "We already run this in production. Want to be one of 5 founding partners?" |
| **2 — Citizenry mesh** | Centre | Visitor teleops a leader SO-101 to do a shop-floor-ish task (kit-component sort into a foam tray). 60 seconds later the follower replays it autonomously. Governor CLI on a side tablet: visitor changes a Constitution rule (e.g. servo torque cap), citizen enforces instantly. XIAO camera stream visible in-frame. | "Teach it once, it does it forever — and refuses anything outside the Constitution." |
| **3 — The bridge** | Right | One Claude session calls MCP tools that reach into both Cell 1 (TDM data) and Cell 2 (live citizens). Demo flow: "Mazak is scrapping" → query TDM → "stage backup tool" → propose to citizen → 4-tier human-approval gate on tablet → arm physically moves → decision ledger entry written, hashed, signed, exportable. | "Auditable AI for manufacturing. Every decision traced, every action approved, every robot signed." |

### Five workstreams (parallel)

| # | Stream | Lead | Days | Ships |
|---|---|---|---|---|
| W1 | Cell 1 — Quin agent on TDM | Philippe | 5–7 | Managed Agents wrapper around `nl-search-service.ts`, 6 strict-schema tools (search_products, search_transactions, search_purchase_orders, search_stock, get_consumption_stats, get_vendor_spend), streaming + adaptive thinking, anonymised Accord data. |
| W2 | Cell 2 — Robot teach-and-replay | Bradley | 8–12 | Surface→Pi teleop already proven; one rehearsed shop-floor-ish task; episode record + 60s replay; XIAO camera live in-frame; governor CLI on side tablet. |
| W3 | Cell 3 — MCP bridge | Bradley + Philippe | 7–10 | Two thin MCP servers: `tdm-mcp` wrapping the 6 TDM tools, `citizen-mcp` wrapping (get_status, propose_task, govern_update). One Claude session calls both. ≤5s end-to-end loop including human approval tap. |
| W4 | Stand build + materials | Contract | 14 (continuous) | Physical stand, lighting, signage, lead-capture iPads, 60-second video loop visible from the aisle, 1-page leave-behind print, "Quintinity ShopOS" landing page refresh. |
| W5 | Rehearsal + QA + sales script | Bradley | last 5 days | Full triptych dry-run end-to-end. Lead-qualifying script (4 questions). Backup plans for: arm jam, MCP timeout, Claude API down, Constitution rejection of a demo move. Press + LinkedIn schedule for the 2 weeks before. |

### Hard cuts to keep it shippable

- No SmolVLA on policy for Cell 2 — replay-only. Claude narrates "this is what I learned" without committing to a fine-tuned policy.
- No Memory Tool integration. No Files API. No Subagents. No new MCP tools beyond the 9 listed.
- No v2 IP harvest before EMEX. Deferred to post-EMEX track.
- Biological subsystems (genome, will, soul, mycelium, immune memory, emotional state) inside citizenry — leave as-is for EMEX, prune in Section 7 timeline.

### At-show targets

| Metric | Target |
|---|---|
| Qualified conversations on the floor | 50+ |
| Booked free 1-hour diagnostic calls | 30+ |
| Email captures | 100+ |
| Notable contacts (industry, gov, press) | 3+ |

### Risk mitigations

- **Hardware on stand**: a second SO-101 + Pi + XIAO triplet boxed under the table, hot-spareable in <10 minutes.
- **Accord case-study sign-off**: parallel-track conversation starting now. Generic anonymised numbers ready as fallback for Cell 1 by 2026-05-15.
- **Cell 3 latency**: budget loop ≤5s. If slower, cut tool calls before show day.
- **Constitution rejection mid-demo**: rehearse the path. Either pre-stage a known-good demo trajectory, or use the rejection as a teaching moment ("watch — the Constitution just stopped me").

### Lead-qualifying script (the EMEX conversation)

> "We're picking 5 NZ manufacturers to be founding AI partners this year — full embedded team for 12 months, deploying our stack on your floor and building 1–2 of your AI ambitions end-to-end. Free 1-hour intro call to see if you're a fit. The 5 seats will go in the next 90 days. Want to be on the list?"

Four follow-up questions: (1) what kind of work runs on your floor? (2) how many machines? how variable is the work? (3) what's stopping you from automating it today? (4) want to be on the founding-five shortlist?

## 4. The 90-day post-EMEX track

**Goal: 5 founding AI partners signed by 2026-10-31, each at NZ$200k for year 1.**

### Funnel and conversion targets

```
50+ qualified EMEX conversations
   → 25–30 free 1-hour diagnostic calls (June 2026, ~50% conv)
   → 8–12 paid 1-day on-site workshops @ NZ$10–15k each (July–Aug, ~40% conv)
   → 5 founding partnerships @ NZ$200k/yr (Aug–Oct signings, ~50% conv)
```

The paid workshop is the lowest-effort qualifier that also pays for itself. NZ$10–15k for one day is enough that only serious buyers commit, but cheap enough that mid-market COOs/CFOs can sign without board approval. The deliverable is a 12-page partnership scope doc — that *is* the sales artefact for the NZ$200k decision.

### Year-1 partnership deliverable (NZ$200k)

| Phase | Months | Ships |
|---|---|---|
| Foundations | 1–3 | ShopOS deployed on customer floor (machines, tools, transactions, kiosks, gauges). Hone NL search live. Decision ledger configured for their compliance regime. |
| Initiative 1 | 3–7 | One named AI capability scoped in the workshop — e.g. predictive scrap on a machine class, autonomous kitting on a cell, vision-based QA station. Citizenry on real hardware. SmolVLA fine-tuned on customer data if applicable. |
| Initiative 2 | 7–10 | Second initiative, or scale Initiative 1 across more cells. |
| Cadence | 1–12 | Weekly ops working session, monthly C-suite steering, same-business-day Slack/Teams SLA, executive briefing decks, decision-ledger-derived audit reports. |
| Renewal | 11–12 | Outcomes review. Year-2 scope at NZ$200–300k with expansion. |

### Pipeline economics (year 1)

| Line | Revenue (NZ) |
|---|---|
| 5 × NZ$200k partnership ARR (founding cohort) | $1,000,000 |
| 8 × NZ$12.5k workshops from EMEX-immediate funnel | $100,000 |
| Workshop tail from non-EMEX inbound + partner referrals | $0–$200,000 |
| Government consulting (Takutai-Moana, MBIE) — capped runway | $200,000–$400,000 |
| **Total year-1 revenue** | **$1.3–1.7M** |

### Parallel build tracks

1. **v2 IP harvest into citizenry + Hone (4–6 weeks, mostly Bradley):** decision ledger, 4-tier gating, episodic/semantic/procedural memory, MCP-server-per-citizen refactor, Quin-agent companion shape. Then archive `quintinity-v2`.
2. **Partnership delivery playbook (8–10 weeks, both):** standard MSA, SOW, IP terms; weekly cadence template; executive deck template; decision-ledger-to-audit-report pipeline; on-call SLA spec. NZ commercial lawyer bakes the contracts once. Repeated 5+ times — every hour spent making the playbook repeatable saves 10 hours per partnership.
3. **Reference materials:** anonymised Accord case study (publish on sign-off), 1-page partnership outline, founding-five microsite, 5–10 minute partnership pitch video.

### Hiring trigger

- Sign 3 partnerships → hire one full-stack TS engineer + one robotics tech in Q4 2026.
- Sign 5 → add ML engineer in Q1 2027.
- Until partnership 3 is paper-signed: stay 2–3 deep + contractors. Hiring before signed revenue is the indie killer.

### Government consulting

Explicitly the airbag while partnerships convert. Cap at 1 day/week per person across team. NZ$200–400k of additional runway, zero product roadmap influence.

## 5. The 12-month horizon (April 2027)

**Position:** *Quintinity — your AI team for manufacturing.*

### What's real by then

- 5 founding partners running, 1–2 in renewal conversation.
- Year-1 ARR: NZ$1.0–1.2M (stagger-dependent on partnership start dates).
- Government consulting steady at NZ$200–400k, capped.
- Workshop revenue: NZ$100–300k total across EMEX cohort + non-EMEX inbound + partner referrals.
- **Total year-1 revenue: NZ$1.3–1.7M.**

### What exists technically (because partnerships forced it)

- Citizenry refactored, MCP-native per citizen, in production at 3+ sites.
- Hone (Claude diagnostics) mature, with 5+ shops' data shaping it.
- Decision ledger battle-tested in real audit/compliance contexts.
- 1–2 bespoke fine-tuned SmolVLA policies (kitting, sorting, QA) running in customer cells. **Layer C — the data flywheel — finally turns.**
- Hailo-8L perception citizen on Pi.
- Quin-agent productised as 1–2 Anthropic Skills (`quintinity-shop-operator`, `quintinity-fleet-orchestrator`) — distributed via Claude apps. Free, drives mindshare, contributes to standards positioning.

### Team

4–6 people: Bradley + Philippe + 1 full-stack + 1 robotics tech + part-time ML + part-time sales/CS.

### Concentration risk

5 customers = each is 20% of ARR. Mitigations:
- Multi-year contracts in year-2 renewals (discount in exchange for 2-year commitment).
- Land partner #6 by Q2 2027 even at lower price. Diversification beats ARPU at this stage.

### Standards-play decision (revisited at 12 months, not now)

If 5 shipping partnerships exist and Anthropic has not shipped a robotics-flavoured MCP, **then** publish the Citizen-MCP spec under a permissive license, write foundation-style governance, let it propagate. Until then, hold as internal IP that strengthens the partnership pitch.

### Revenue mix target by month 12

70% partnerships, 15% workshops + ad-hoc engagements, 15% government consulting. No grants. No research-forever revenue. Profitable by design.

## 6. The 3-year horizon (April 2029)

Three viable end-states — Quintinity picks based on what year 2 reveals; do not lock in now:

| End-state | Shape | Revenue (NZ) | Team | Commit when |
|---|---|---|---|---|
| **A. NZ/AU AI partner of record for mid-market manufacturing** | 15–25 partners across NZ + AU, deeply embedded, NZ$300–500k each, multi-year contracts. High-touch services-and-product hybrid. | $5–10M ARR | 15–25 | Default if year 2 expansions land cleanly |
| **B. ShopOS as productised SaaS, partnerships as upsell** | 50+ ShopOS subscribers @ NZ$30–80k/yr, top 10–15 graduate to partnership tier @ $200–400k. Better margins, less concentration. | $3–6M ARR + better margins | 12–20 | If year 2 reveals strong product-led demand without the partnership |
| **C. Acquisition exit to a global manufacturing platform** | Hexagon, Siemens, PTC, Rockwell, or Anthropic-adjacent enterprise AI buyer. Quintinity becomes their NZ/APAC arm or their "auditable AI" line. | One-time $15–40M | Founders out in 18–36 months | Only if a strategic comes in year 2–3 with a real number |

### The data flywheel that turns by year 3

SmolVLA-class policies fine-tuned across 10+ NZ shops produce a manufacturing-policy library nobody else has. Even if Quintinity stays small, the dataset and trained models are an asset class — sellable to AI labs, licensable to OEMs, or used as a moat against new entrants.

### Standards positioning by year 3

One of:
1. Citizen-MCP spec published as open standard, multi-vendor implementations, Quintinity as canonical maintainer.
2. Absorbed into Anthropic's official protocol if they ship one (a tailwind, not a threat — Quintinity becomes the leading implementer either way).
3. Stays internal IP if neither happens.

All three are fine. Do not bet on (1) before year 2 evidence.

### Geographic reach by year 3

Australia (Sydney/Melbourne mid-market manufacturing is 5× NZ's size, same regulatory frame, same buyers). Maybe Singapore as APAC test bed. Do **not** go to US/EU before year 4 — different regulators, different buyers, different sales cycle. Stay where the Accord reference travels.

## 7. Kill list — what we retire and when

**Immediate (this week):**
- Archive `Quintinity/tabflow-guard`, `Quintinity/full-bloom-build`, `Quintinity/Duran-Playground`, `Quintinity/ubiquitous-fortnight`.
- Archive `BradleyFestraets/az-acs-demo`, `BradleyFestraets/K2-Workflow-API`.

**Post-EMEX (June 2026):**
- Begin v2 IP harvest into citizenry + Hone (4–6 weeks).

**After IP harvest (~August 2026):**
- Archive `Quin-AI-Assistant/quintinity-v2` main branch. Mark superseded.

**By 2026-10-31 (inside citizenry):**
- Prune unwired biological subsystems (genome, will, soul, mycelium, immune memory, emotional state). Anything not observably driving citizen behaviour gets removed. Ship the prune as a confident statement, not a quiet deletion.

**By 2026-09-30:**
- Decide on `Crowdiant-AI`: spin out, sell, or pause.

**Q4 2026:**
- Archive the four `tab-runner-*` repos once methodology is internalised in Quintinity's prompt-authoring guide.

**Continuous policy from now on:**
- Any repo with no commits in 90 days gets archived. Quarterly review.
- Government consulting capped at 1 day/week per person across team. Renew contracts only if cap holds.

## 8. Risks, kill criteria, and the positioning manifesto

### Top 6 risks (ranked by impact × probability)

| # | Risk | Prob | Impact | Mitigation |
|---|---|---|---|---|
| 1 | First partnership delivers late on Initiative 1 | High | High | Aggressive scope discipline in workshop scope-doc. Weekly steering with named owner. Refuse Initiative 2 expansion until Initiative 1 ships in production with traced decisions. |
| 2 | Founder/team burnout from 5 simultaneous engagements | High if unmanaged | High | Hard cap of 5 partners until headcount catches up. Forced 2-week break per founder per year, rostered. Customer SLA explicitly "same business day", not 24/7. |
| 3 | Accord case-study disclosure delayed | High | Medium | Parallel-track sign-off conversation starting now. Generic anonymised numbers ready by 2026-05-15. |
| 4 | Concentration risk from 5-customer base | Always present | High | Multi-year contracts in year-2 renewal (discount for 2-year commitment). Land partner #6 by Q2 2027 even at lower price. |
| 5 | EMEX hardware fails on-stand | Low w/ prep | High | Boxed spare triplet (SO-101 + Pi + XIAO) under the table. Recovery script rehearsed. Cell 2 demo loop short enough that a reset isn't catastrophic. |
| 6 | Anthropic ships robotics-flavoured MCP / agent framework before Quintinity does | Medium | Low–Medium (actually a tailwind) | Don't position against Anthropic; position as the leading implementer on top of them. Citizenry's signed-multicast layer remains valuable regardless. |

### Kill criteria — dated triggers that force a strategy review

| Trigger | Date | Action |
|---|---|---|
| <2 partnerships signed | 2026-12-31 | Pricing, segment, or positioning is wrong. Stop signing more workshops; do strategy retro before booking Q1 2027 work. |
| First partnership's Initiative 1 not in production | Month 7 of engagement | Engineering capacity is the constraint, not sales. Hire ahead of plan, or cap at 3 partners not 5. |
| Government consulting >25% of revenue in any quarter | quarterly review | It's eating the product roadmap. Cut clients before extending contracts. |
| Any partnership NPS <50 at month-6 review | rolling | Executive sponsor visit, root-cause within 30 days, refund or restructure if unfixable. |
| Founder takes >2 unplanned sick days, or skips a steering meeting unprepared | rolling | Forced 2-week stand-down. No exceptions. |

### Positioning manifesto — seven non-negotiables

1. We are NZ manufacturing's AI team. We are not a SaaS vendor.
2. Every decision is auditable. Every action is approved. Every robot is signed.
3. Five partners only — we trade scale for delivery quality, by design.
4. Profitable from year 1. No grants, no pre-revenue investment, no research-forever revenue.
5. Edge-first, cloud-aware. Citizens execute locally; Claude reasons globally.
6. Open protocols when proven, closed delivery while it ships. We win on integration, not lock-in.
7. Ethics is the moat, not the marketing.

## 9. Anthropic frontier capability map (summary)

Full research preserved at `~/linux-usb/docs/superpowers/research/2026-04-27-anthropic-frontier-capabilities.md` — capability-by-capability map of Managed Agents, MCP, Computer Use, Code Execution, Files, Memory, Extended Thinking, Prompt Caching, Batch, Skills, Tool Use, Streaming, Subagents, Workbench.

### EMEX-critical (29 days)

- **Claude Managed Agents** — Anthropic-hosted agent runtime (April 2026). Define agent (model, system prompt, tools, MCP servers, skills), spawn sessions, stream responses. Eliminates self-hosted agent loop. Replaces the existing `nl-search-service.ts` pattern in Hone. **Priority: critical.**
- **Tool use (strict + parallel)** — schema-guaranteed responses, multiple tools in one turn. Used in Cell 1 and Cell 3. **Priority: critical.**
- **Streaming + adaptive thinking** — visible reasoning during demo. Builds credibility with shop operators and exec visitors. **Priority: critical.**

### 90-day adoption

- **MCP Connector** — for Cell 3 bridge. Defer the full citizen-MCP refactor to August.
- **Prompt Caching** — cost control as Hone usage scales. Add post-EMEX.
- **Code Execution** — for ad-hoc data analysis Claude requests during diagnostic.

### 12-month bet

- **Subagents + multi-agent Teams** — hierarchical delegation in fleet orchestration.
- **Memory Stores (research preview at time of writing)** — org-wide cross-customer learning.
- **Skills** — productise Hone+citizenry as `quintinity-shop-operator` and `quintinity-fleet-orchestrator` Skills, distribute via Claude apps.
- **Files API + Citations** — compliance and auditability hardening.

### Protocol alignment recommendation (the user's question)

**Coexist + bridge, not replace.** Citizenry's 7-message protocol does what MCP does not: presence detection (multicast heartbeat with TTL), peer-to-peer discovery, signed governance (Constitution-signed amendments), gossip consensus. MCP does what citizenry does not: rich tool schemas, OAuth, prompt + resource types, streaming tool results, integration with Claude reasoning.

**Each citizen exposes an HTTP MCP server that wraps its local capabilities.** Managed Agents discover citizens via the MCP server, call tools, which internally invoke citizenry actions. This preserves citizenry's decentralisation while letting cloud agents orchestrate. Best of both worlds: fleet autonomy + cloud intelligence.

**Should v2's 92 MCP tools become an Anthropic Skill?** Yes, post-IP-harvest. Productise as `quintinity-shop-operator` (read-only diagnostic) and `quintinity-fleet-orchestrator` (write-capable, gated by 4-tier action gating). Distribute via Claude apps; partnership customers consume via Claude API.

## 10. Glossary

- **citizenry** — Quintinity's decentralised robotics OS in `~/linux-usb/citizenry/`. Each piece of hardware is a "citizen" with its own Ed25519 identity advertising capabilities and bidding on tasks via the 7-message protocol.
- **citizen** — an autonomous agent within the citizenry mesh. Examples: GovernorCitizen (Surface), ManipulatorCitizen (Pi/Jetson), CameraCitizen (XIAO ESP32S3), LeaderCitizen, PolicyCitizen.
- **Constitution** — a signed governance document broadcast via the GOVERN message. Carries Articles (immutable safety rules), Laws (mutable policy tunables), and ServoLimits (hardware caps). Verified and persisted by every citizen.
- **Hone** — the AI/diagnostics layer of TDM (NL search, Claude-powered scrap analysis, predictive reorder).
- **MCP (Model Context Protocol)** — Anthropic's open protocol for exposing tools, resources, and prompts to a Claude session. HTTP/SSE or stdio transport.
- **ShopOS** — Quintinity's umbrella name for TDM + Hone + (future) robotics, marketed as a unified shop-floor operating system.
- **TDM (Tool Data Management)** — Quintinity's production shop-floor system, deployed at Accord Precision. Tracks tools, transactions, scrap, inventory, purchase orders.
- **Quin-agent** — the companion AI agent shape, originally in `quintinity-v2`, harvested into Hone post-EMEX.
- **SmolVLA** — Hugging Face's 450M-parameter Vision-Language-Action policy, planned as the first PolicyCitizen in citizenry.

## 11. Sources

- `~/linux-usb/` — citizenry codebase, surveyed 2026-04-27.
- `Quintinity/pcrottet-tool-data-management` — TDM/Hone/ShopOS, surveyed 2026-04-27. EMEX pitch already designed at `docs/superpowers/specs/2026-04-19-emex-shopos-pitch-design.md`.
- `Quin-AI-Assistant/quintinity-v2` — Robot OS v2, surveyed 2026-04-27. 5.9MB TypeScript, paused since 2026-02-17.
- `Quintinity/quintinity-ledger`, `Quintinity/Takutai-Moana-v2`, `Quintinity/MBIE-Determinations`, plus four Lovable experiments — surveyed 2026-04-27.
- `BradleyFestraets/tab-runner-*` (×4), `Crowdiant-AI`, `az-acs-demo`, `K2-Workflow-API`, plus three forks (lerobot, cosmos-dataset-search, digital-twins-for-fluid-simulation) — surveyed 2026-04-27.
- Anthropic platform documentation (April 2026): Managed Agents overview, MCP Connector, Computer Use, Code Execution, Files, Memory Tool, Extended Thinking, Prompt Caching, Batch Processing, Agent Skills, Tool Use Overview.
- EMEX 2026 confirmed dates: 26–28 May 2026, Auckland Showgrounds (https://emex.co.nz).

---

*End of design. Implementation plan to follow via `superpowers:writing-plans`.*
