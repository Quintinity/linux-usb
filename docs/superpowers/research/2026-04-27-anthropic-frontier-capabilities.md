Now let me compile the comprehensive frontier agent capabilities map:

---

# Anthropic Frontier Agent Capabilities Map for Quintinity
## Strategic Alignment & Application Guide

**Date:** 2026-04-27  
**Context:** Quintinity (NZ robotics + manufacturing at Accord Precision) has 29 days to EMEX demo (26–28 May 2026). Existing stack: **citizenry** (decentralized robotics OS with 7-message protocol), **TDM/Hone/ShopOS** (production Fastify+React+PostgreSQL with Claude diagnostic), **quintinity-v2** (5.9MB TypeScript "brain" with 92 MCP tools, paused 70 days).

---

## 1. Claude Managed Agents (Anthropic-Hosted Agent Harness)

### (a) What it currently is
Claude Managed Agents is Anthropic's hosted, configurable agent runtime launched April 2026, available in **beta** (generally available for core sessions/tool execution; research preview for outcomes & multi-agent). You define an **agent** (model, system prompt, tools, MCP servers, skills), an **environment** (cloud container with packages, network access, mounted files), then spawn **sessions** (running instances) that receive user events and stream back responses via SSE. Claude autonomously executes tools (bash, file ops, web search/fetch, MCP, code execution, memory) within the container. Sessions persist server-side; you poll for status or stream events. No self-hosted agent loop required—Anthropic owns the orchestration, sandboxing, persistence. Currently supports **agent teams** (multiple Claude instances with shared task list) and **subagents** (single-session delegation). Cost: standard token pricing + infrastructure overhead (TBD beta). Latency: ~5–30s per turn depending on tool load.

### (b) Application for Quintinity
**Use it for: TDM diagnostic and remote shop-floor orchestration at EMEX.** Instead of hosting a Claude-via-API loop in a Fastify microservice (current nl-search-service.ts pattern), define a `tdm-operator` agent with read-only shop tools (search_products, search_transactions, diagnostic_report) and let Claude Managed Agents handle session lifecycle. This eliminates infrastructure burden and gives you built-in memory + compaction. For EMEX demo: create a session per shop-floor visitor, let them ask questions ("`How much scrap in Tool-Life-Item-456 this week?`"), and Claude reasons over transactional data without you managing the agentic loop. Later: if citizens (Jetson/Pi nodes running SmolVLA or tool-life predictors) need to coordinate work via Claude, bind them as MCP servers to a multi-agent session—Managed Agents brokers the protocol translation. **Constraint:** Managed Agents isn't a replacement for **citizenry's UDP multicast + signed governance**—it's a complementary cloud control plane for remote task orchestration and human-facing Q&A.

---

## 2. Model Context Protocol (MCP)

### (a) What it currently is
MCP is a language-agnostic protocol (spec v2025-11-25) for exposing tools, resources, and prompts to Claude. Transports: **stdio** (local, managed by MCP SDK), **HTTP streaming** (Streamable HTTP, requires client implementation), **SSE** (server-sent events, most cloud-friendly). Anthropic's **MCP Connector** (beta, header `mcp-client-2025-11-20`) lets you declare remote MCP servers directly in Messages API: pass `mcp_servers` array (URL, auth token, name) and `tools` array (MCPToolset with allowlist/denylist/per-tool config). Claude can call tools; resources and prompts are **not yet supported** in the Messages API connector. Auth: OAuth Bearer token in `authorization_token` field. Limitations: tools-only (no resources/prompts in the connector); MCP server must be publicly accessible over HTTPS; not on Bedrock/Vertex yet. SDK helpers for TypeScript: `mcpTools()`, `mcpMessages()`, `mcpResourceToContent()`, `mcpResourceToFile()`.

### (b) Application for Quintinity
**Massive relevance.** Quintinity-v2 already has 92 MCP tools + 21 resources—this is the **standard API contract** for agentic context. Current v2 codebase couples MCP definitions tightly to Claude SDK + OpenAI fallback; Managed Agents + MCP Connector will decouple it. **Strategy:** Refactor v2's MCP server to be **detached & HTTP-exposed** (not embedded in Claude calls). Then: (1) Each citizen (Jetson/Pi node) that has observability logic (tool-life prediction, vision anomaly) publishes an HTTP MCP server. (2) citizenry's gossip/registry protocol discovers these servers. (3) A Managed Agent session (TDM Operator, Shop Diagnostician) connects to relevant citizen MCP servers via the Connector. (4) This bridges the 7-message ledger-based governance model to Claude's tool ecosystem. **At EMEX:** Demo a shop visitor asking "`What's the status of Spindle-A?`" → Managed Agent calls MCP tools from live Jetson/Pi citizens → citizen responds with tool results (live video snippet, wear estimate). This is protocol alignment without replacing citizenry.

---

## 3. Computer Use Tool

### (a) What it currently is
Claude can autonomously navigate desktop UIs—screenshot, click, type, drag, scroll, key presses, zoom. Beta (header `computer-use-2025-11-24` for Opus 4.7/4.6/Sonnet 4.6; earlier header `computer-use-2025-01-24` for older models). Requires you to implement a virtual display environment (typically Xvfb + X11 on Linux in a container), capture screenshots as base64 images, translate Claude's actions (left_click at [x,y], type "text", scroll, etc.) into actual OS calls, and return results. Anthropic reference implementation in GitHub: Docker + Mutter + Firefox + tool executors. **Limitations:** latency (seconds per action), vision accuracy issues (coordinate hallucination), unreliable scrolling/spreadsheet interaction, browser-only account creation/social media limitations. **Security risk:** Claude can follow on-screen prompt injections. Mitigations: isolated VM, classifier-based injection detection, human approval gates for high-impact actions.

### (b) Application for Quintinity
**Lower priority for EMEX; medium-term value.** Computer Use shines when Claude needs to navigate a **third-party SaaS or legacy web app** you can't API-integrate. Example: a supplier's web portal for ordering tool-life consumables—Computer Use lets Claude fill forms and place orders autonomously. For **TDM/ShopOS internals,** you already have REST APIs and query tools (nl-search-service.ts), so Computer Use isn't the right fit. **However:** If Quintinity products a **White Label TDM for customers** who have legacy ERP/MES systems, Computer Use can bridge CSV uploads, screenshot-based status checks, or unstructured troubleshooting workflows. **Post-EMEX:** In a 12-month roadmap, Computer Use + vision could let a robot or inspection station visually assess shop floor state (rogue material, spill, collision) and alert humans—but this overlaps with SmolVLA citizen agents, which are more efficient for robotics.

---

## 4. Code Execution Tool

### (a) What it currently is
Claude executes Python and bash in a **sandboxed container** (client or server-side, depending on context). Supports multiple versions: `code_execution_20250825`, `code_execution_20260120`. Input/output file size limits; file persistence within a session or request (not across sessions unless you use Files API). Free when used with web_search or web_fetch. Standard charges otherwise. Pre-installed packages: NumPy, Pandas, Matplotlib, requests, etc. **Not available for arbitrary network calls or package installs** in Managed Agents (only pre-configured deps). On-device execution is possible but typically slower than Anthropic's infrastructure.

### (b) Application for Quintinity
**High immediate value for TDM data analysis.** Current nl-search-service.ts has 6 read-only query tools for search/filter; **Code Execution lets Claude do ad-hoc analysis in-line.** Examples: "`Plot scrap rate vs. spindle temp this week`" → Claude writes Python with Pandas, reads queried CSVs via code execution, returns chart. "`Recommend tool-life renewal priority`" → Claude analyzes transaction data, runs a simple cost-risk ranking, outputs JSON. This eliminates the need for pre-computed dashboard columns. **At EMEX:** A shop operator asks "`Why is Spindle-C failing?`" → Claude reads live sensor logs (via code execution), correlates with maintenance history (read-only DB query tool), plots hypothesis, explains root cause. **Medium-term:** integrate with citizenry—Pi nodes send telemetry via the 7-message protocol → Quin-agent stores in temporary file → Code Execution analyzes and recommends→ citizen receives guidance. **Constraint:** No network access in Managed Agents, so data must arrive via files or pre-uploaded datasets (Files API).

---

## 5. Files API + Citations

### (a) What it currently is
**Files API** (beta, header `files-api-2025-04-14`) uploads files to Anthropic storage, returns a `file_id`, allows reuse across requests without re-uploading. Supports: PDFs, images, plain text, CSV via code execution. Download capability only for files **created by skills or code execution** (not user-uploaded files). Operations: upload, list, retrieve metadata, delete (free); reference in messages (charged as input tokens). **Citations:** When you reference a PDF or document block with `citations: {enabled: true}`, Claude's response includes inline citations pointing to specific document ranges, traceable to source. TTL: files persist until deleted; no automatic expiration. Limits: 500 MB per file, 500 GB per organization. **Not ZDR-eligible** (standard data retention).

### (b) Application for Quintinity
**Critical for compliance + auditability.** Quintinity's manufacturing context (Accord Precision, tool-life management) requires **traceability:** why did Claude recommend retiring Tool-456? Citation blocks let you link Claude's reasoning back to raw data blocks. **Workflow:** (1) Upload shop maintenance logs, sensor calibration PDFs, tool-life curves to Files API once per day. (2) In Managed Agent sessions, reference these files as documents. (3) Claude answers "`When should Tool-X be replaced?`" with citations to specific calibration sections + transaction blocks. (4) Record the decision with file IDs—auditors can replay the exact context Claude saw. **At EMEX:** A customer asks "`How do you justify this maintenance cost?`" → You show the decision log with citations; it's reproducible and defensible. **Integration with citizenry:** Citizens (Jetson/Pi) generate daily telemetry summaries → uploaded to Files API → Managed Agent references them → decision ledger stores file IDs alongside signed Constitution entries. **Post-EMEX:** For product liability / ISO 9001 compliance, this combo (Files API + citations + decision ledger) is a selling point: "auditable agentic maintenance planning."

---

## 6. Memory Tool & Memory Stores

### (a) What it currently is
**Memory Tool** (`memory_20250818`): Client-side primitive that lets Claude create/read/update/delete files in a `/memories` directory. Commands: `view`, `create`, `str_replace`, `insert`, `delete`, `rename`. You implement the backend (filesystem, DB, encrypted storage). Claude automatically checks memory before starting tasks; uses it to persist progress, context, decisions. **Memory Stores** (beta): Anthropic-managed server-side memory for Managed Agents—create memory stores, store/retrieve/delete memories, versioning, archival. Memory Stores are **not yet fully integrated** with core agent sessions (research preview). **Best practice:** Use Memory Tool for explicit, agent-driven memory (Claude decides what to remember); use Memory Stores for system-managed context (episodic summaries, decision logs).

### (b) Application for Quintinity
**Strategic for long-running shop-floor agents and v2 architecture alignment.** Quintinity-v2 already has a **6-layer memory architecture** (episodic, semantic, procedural, social, working, curated). Redesign this to use **Memory Tool** as the implementation: each layer becomes a `/memories/{layer}` directory structure. Example: `/memories/episodic/session-2026-04-27-spindle-failure.md` stores raw event logs; `/memories/semantic/tool-life-curves.json` stores learned patterns. When a Managed Agent spawns a session for a multi-turn diagnostic, it checks memory first: "`Have I seen Tool-456 fail before? What was the root cause?`" With this, diagnostic quality improves per session over time. **Citizen-level memory:** Each citizen (Jetson/Pi) runs locally and can use Memory Tool to persist learning—e.g., SmolVLA agent learns "`Bearing-Y makes a grinding sound before failure`" and records it. **At EMEX:** Run multiple diagnostic sessions with the same agent + persistent memory. Session 1 (9 AM): "`Spindle-A vibration`" → recorded in memory. Session 2 (2 PM): "`Spindle-A grinding`" → Claude checks memory, cross-references, improves hypothesis. **Post-EMEX:** Memory Stores can then hold organization-wide patterns (failure modes across all shops), shared by all agents.

---

## 7. Extended Thinking & Adaptive Thinking

### (a) What it currently is
**Extended Thinking** (manual, `thinking: {type: "enabled", budget_tokens: N}`): Claude outputs a `thinking` content block with step-by-step reasoning before responding. Supported on Claude Sonnet 4.6, Opus 4.5, Opus 4.1, Sonnet 4.5, Haiku 4.5, and older models. **Not** on Opus 4.7 (deprecated in favor of Adaptive). You pay for full thinking tokens (not just summary). Latency penalty: +10–50% depending on budget. **Adaptive Thinking** (recommended): Claude automatically decides when to think and how much (`thinking: {type: "adaptive"}`). Supported on Opus 4.7, 4.6, Sonnet 4.6, Mythos Preview. Returns `thinking` blocks with encrypted signatures (thinking content omitted by default; can request `display: "full"`). Interleaved thinking: Claude can think **between tool calls**, so it reasons about tool results before deciding on the next action (automatic on Opus 4.7+, beta flag for older models).

### (b) Application for Quintinity
**High ROI for diagnostic + decision reasoning.** TDM diagnostic reports are the hero feature; **Adaptive Thinking makes them better.** When Claude is asked "`Why is Tool-456 failing?`", enable adaptive thinking: Claude will reason about causality chains (temperature → expansion → wear → friction → failure) before output. This surfaces multi-step reasoning that builds credibility. **Cost:** Adaptive incurs thinking-token charges, but Opus 4.7 is cheaper than earlier Opus models. **At EMEX:** Diagnostic response with visible thinking (if demoing to technical audience) shows Claude isn't just pattern-matching; it's reasoning. Example output:
```
<thinking>
Step 1: Spindle-A bearing temp > 85°C (threshold 80°C)
Step 2: Check lubrication schedule → last service 6 weeks ago, spec 4 weeks
Step 3: Underlubrication + high temp + observed grinding noise → bearing degradation
Step 4: Cost of emergency replacement >> preventive replacement cost
Conclusion: Schedule replacement within 48 hours
</thinking>

**Recommendation:** Replace Spindle-A bearing. Root cause: lubrication interval overdue.
```
**Interleaved thinking:** When diagnostic calls code_execution (analysis) and tool calls (history lookup), Claude thinks between them. Critical for catching errors in the agent loop (e.g., "`Tool result is inconsistent with my hypothesis—revise reasoning`"). **Post-EMEX:** For 12-month roadmap, combine Adaptive Thinking + Memory Tool to build a **reasoning audit log**—each decision is timestamped with its thinking chain, legally defensible for liability disputes.

---

## 8. Prompt Caching

### (a) What it currently is
**Prompt Caching** optimizes cost + latency by caching prompt prefixes. **Two modes:** (1) **Automatic caching** (recommended for conversations): add `cache_control: {type: "ephemeral"}` at top level; system automatically places breakpoint after last cacheable block. (2) **Explicit breakpoints**: place `cache_control` on individual content blocks (up to 4 breakpoints). **Pricing tiers:**

| Token Type | Cost | TTL |
|-----------|------|-----|
| Base input | 1.0x | N/A |
| 5-min cache write | 1.25x | 5 min (auto-refresh free) |
| 1-hour cache write | 2.0x | 1 hour |
| Cache read/hit | **0.1x** | (within TTL) |

**Example:** 10k-token system prompt + context cached → 90% savings on re-use. **Minimum:** 1024–4096 tokens depending on model. TTL behavior: cache auto-refreshes at no cost within 5-min window; after 5 min, stale hit costs 0.1x. Supported on all current Claude models. **Tool caching:** Place breakpoint on last tool definition; all preceding tools cached together. **Limitation:** Cache breakpoint location is **cumulative hash-based**; moving content slightly can break cache hits (so plan stable prompt structure).

### (b) Application for Quintinity
**Critical cost control for high-volume robot fleet.** Quintinity's constraint: profitable, so token costs matter. **Shop Diagnostician agent example:** System prompt (3k tokens) + TDM schema context (5k tokens) + tool definitions (2k tokens) = 10k **static prefix**. Every user query adds ~100–300 dynamic tokens. **Without caching:** 10,300 tokens per query × 1000 daily queries = **10.3M tokens/day**. **With caching:** 10k cached (first call: 1.25x charge; refreshes free); 300 dynamic tokens × 1000 = 300k new tokens/day. **Savings: ~97%** on recurring queries. **At EMEX:** If demo has 100 shop operators asking questions over 3 days, the cached prompt pays for itself. **Strategy:** Structure system prompt + context so stable knowledge (shop schema, tool-life tables, diagnostic procedures) is cached, dynamic queries (live sensor data, current inventory) are separate inputs. **With Managed Agents:** Cache breakpoint is on the MCP toolset definition, so citizens' tool schemas are cached across sessions. **Post-EMEX:** As fleet scales (10+ shops, 100+ agents), prompt caching becomes the difference between 100k/month vs. 3M/month in API spend.

---

## 9. Batch API

### (a) What it currently is
**Message Batches API** (production, not beta) accepts bulk async requests, processes offline, returns results. You submit JSONL file with array of `messages` requests, poll for status, retrieve results when done. **Typical SLA:** < 1 hour, most finish in minutes. **Pricing:** 50% cost reduction vs. real-time; you lose latency (no immediate response). **Use cases:** evaluations, content moderation, bulk analysis, overnight data processing. **API endpoints:** create batch, list, retrieve, cancel, delete. **Output:** results JSONL with same structure as input, preserving request IDs. **Not ZDR-eligible** (standard data retention policy). Suited for tasks where latency is not critical but cost and throughput matter.

### (b) Application for Quintinity
**Medium-term; not EMEX-critical, but essential post-launch.** Use cases: (1) **Offline policy evaluation:** Batch-process 10k historical failure events with diagnostic agent, tag root causes, build training data for future improvements. (2) **Fleet-wide tagging:** Analyze all transactions from 5 shops this month, categorize each by toolwear/unexpected-failure/normal. (3) **Brand comparison:** Given competitor tool-life data, rank your tools against market. (4) **Predictive maintenance batch:** Each night, process all sensor logs from past 24h in one batch, output CSV of recommended actions by shop. **Cost example:** 1000 diagnostic requests × 5k tokens each = 5M tokens. Real-time: $2.50 (via Opus). Batch API: **$1.25** (50% discount). **Strategy:** Decouple real-time diagnostics (Managed Agents, for EMEX) from bulk analytics (Batch API, overnight). **At EMEX:** Batch API runs offline; demo real-time diagnostics. **Post-EMEX:** Nightly batch to produce the next morning's maintenance plan CSV.

---

## 10. Claude Skills (Anthropic Agent Skills)

### (a) What it currently is
**Agent Skills** are modular capability packages (YAML metadata + SKILL.md + optional resources/code) that Claude can use automatically when relevant. **Three loading levels:** (1) **Metadata** (always in system prompt, ~100 tokens): name, description, trigger condition. (2) **Instructions** (loaded when triggered, up to 5k tokens): procedural knowledge (SKILL.md). (3) **Resources** (on-demand, ~0 context cost): bundled scripts, API docs, templates, executed via bash without loading source into context. **Availability:** Pre-built Skills (PowerPoint, Excel, Word, PDF) available on Claude API + claude.ai. Custom Skills can be uploaded via API (`/v1/skills` endpoints) or created in Claude Code. **Scope:** API Skills shared org-wide; claude.ai Skills are per-user; Claude Code Skills are filesystem-based. **Security:** Skills run in code execution environment with bash access; malicious Skills can leak data or execute harmful commands. **Limit:** You can't download Skills that you uploaded, only skills created by code execution.

### (b) Application for Quintinity
**High strategic value; productization path for v2 + TDM.** Quintinity-v2 is a 5.9MB TypeScript bundle with 92 MCP tools already organized conceptually as specialized agents (Operator, Diagnostician, Setter). **Refactor as Skills:** (1) **TDM Operator Skill:** instructions for navigating shop data (search products, transactions, inventory); bundled scripts for common queries. (2) **Shop Diagnostician Skill:** diagnostic procedures, root-cause frameworks, decision thresholds; bundled sensor-analysis Python. (3) **Robot Setter Skill:** motion planning, calibration workflows, safety checks. Upload these to Anthropic via Skills API. **On Claude API:** Customers can reference your Skills directly in their agents, no reimplementation. **At EMEX:** You demo "`Claude now includes a Quintinity ShopOS skill`"—installed via API, instantly available to any agent. **Post-EMEX:** Offer Skills on Claude's marketplace (if/when Anthropic launches). **Pricing:** Anthropic takes a % of usage; Quintinity gets revenue per query. **Alternative (simpler):** Package v2 as a **Claude Code custom skill** (shared across your internal team + partner shops over SSH). This avoids Anthropic marketplace but requires manual distribution. **Constraint:** Skills don't sync across surfaces (API ≠ claude.ai ≠ Claude Code), so you'll need separate packaging for each.

---

## 11. Tool Use (Parallel, Strict, Structured Outputs)

### (a) What it currently is
**Tool Use Overview:** Claude calls tools you define or Anthropic provides. **Recent improvements:**

- **Parallel tool calls:** Claude can invoke multiple tools in one turn (e.g., call search_products + search_transactions + get_historical_data simultaneously). Faster agent loops.
- **Strict tool use** (`strict: true` on tool definition): Claude's input **always** matches your JSON schema exactly. No fuzzy inference; errors are caught before execution.
- **Structured outputs** / **JSON schema enforcement**: Compatible with tool use; Claude's response is guaranteed to match schema.
- **Tool choice control:** `tool_choice: "auto" | "any" | "tool" | "none"`. E.g., `tool_choice: "any"` forces Claude to use at least one tool; useful for forcing diagnostic mode.
- **Deferred tool loading:** Use `defer_loading: true` in MCP toolsets to hide tool definitions from Claude upfront, then use **Tool Search Tool** to let Claude search for relevant tools on demand (reduces token cost for large tool sets).

Pricing: tool definitions + tool calls are all input tokens (see tool use system prompt overhead: 300–350 tokens per request).

### (b) Application for Quintinity
**Immediate value for TDM agent robustness.** Current nl-search-service.ts has 6 read-only query tools; they're likely loose in schema. **Adopt strict tool use:** tighten JSON schemas, catch errors early. **Parallel tool calls:** when a diagnostic starts, call search_products + search_historical_failures + get_sensor_logs **in parallel**, not sequentially. Agent latency drops from 10s (3 sequential RPC calls) to 3s (1 parallel RPC). **Structured outputs:** Diagnostic reports are JSON with `{recommendation, confidence, reasoning, alternatives}`—enforce schema so downstream systems can parse reliably. **Tool choice:** For the Diagnostician agent, set `tool_choice: "any"` (force it to gather data before opining). **Deferred loading + Tool Search:** If you grow to 50+ MCP tools across citizens, don't load all 50 schemas (5k tokens). Instead: defer load all, include Tool Search Tool, let Claude search "`Show me tools for bearing maintenance`". **At EMEX:** Demo a question that would normally be 3 sequential API calls, but with parallel tool use, it returns in 2 seconds. Users see responsiveness. **Post-EMEX:** As tool set grows, Tool Search becomes essential for cost control.

---

## 12. Streaming + Extended Thinking + Interleaved Thinking

### (a) What it currently is
**Streaming:** SSE (server-sent events) for Messages API; text arrives incrementally in `content_block_delta` events. Reduces perceived latency (TTFT, time-to-first-token is faster). **With extended thinking:** Thinking tokens arrive in `content_block_delta` events with `thinking_delta` type; text arrives after thinking concludes. You can display thinking in real-time or omit it (`display: "omitted"`). **Interleaved thinking** (beta on Opus 4.5+, automatic on Opus 4.7+): Claude thinks, uses a tool, receives result, thinks again, then responds. Streaming + interleaved thinking: model can stream thinking blocks, then a tool_use block, then wait for tool_result, then resume thinking—multiple rounds in one API call. **Cleanest pattern for agents:** Use streaming with `stream_options: {type: "raw"}`, listen for content_block events, accumulate thinking + tool_use blocks, execute tools, send results, continue stream. Anthropic SDK helpers (TypeScript, Python) handle this.

### (b) Application for Quintinity
**Critical for live EMEX demo experience.** Streaming + extended thinking creates **visible reasoning.** Example: shop operator asks "`Why should I replace Tool-456?`"
```
[Stream starts]
thinking: "Temperature is 85°C, spec is 80°C. Lubrication schedule..."
[User sees thinking in real-time, builds confidence]
text: "Recommendation: Replace within 48 hours. Root cause..."
```
vs.
```
[No streaming, 5s wait]
text: "Replace within 48 hours."
[User wonders: did it really reason, or was it lucky?]
```

**At EMEX:** Use streaming + adaptive thinking. Visitor sees Claude's reasoning unfold. If multi-turn (visitor asks follow-up), interleaved thinking between tool calls shows error-correction ("`Oh, I need to check the sensor calibration again`"). This builds credibility. **Implementation:** Use Anthropic TypeScript SDK with built-in streaming helpers; front-end displays thinking in a side panel (gray text), responses in main panel (black text). **Post-EMEX:** For production, decide: (1) Show thinking to end users (transparency), (2) Omit thinking but log it (internal audit), (3) Thinking in extended mode only (expert diagnostics).

---

## 13. Managed Agents: Multi-Agent Orchestration & Subagents

### (a) What it currently is
**Multi-agent patterns in Managed Agents** (research preview): **Agent Teams** (multiple Claude instances, independent contexts, shared task list, direct communication) vs. **Subagents** (single-session main agent spawns child agents, reports results to main). **Orchestrator pattern:** one Claude instance breaks down a task, delegates to specialized subagents, synthesizes results. **Use case differentiation:** Teams for parallel independent work; subagents for sequential hierarchical tasks. **Token economics:** Teams cost more (each agent processes independently); subagents cheaper (single main context, children reuse context). Example: TDM + Shop Diagnostician + Maintenance Scheduler as a Team (all run in parallel); or Orchestrator breaks down "`Optimize tool-life plan for Shop-A`" → delegates to multiple Schedulers for different tool types → synthesizes into one plan. **Status:** Generally available for core sessions; advanced outcomes (self-evaluation, iteration) in research preview.

### (b) Application for Quintinity
**Strategic for scaling beyond EMEX.** For EMEX (29 days), single-agent Managed Agents is enough. **Post-EMEX, for production fleet:** adopt Managed Agents Teams or Orchestrator pattern. **Scenario:** Quintinity launches "QuinBot" for 10 shops. Each shop gets: (1) **Diagnostician agent** (analyzes failures), (2) **Scheduler agent** (creates maintenance plan), (3) **Approver agent** (human-in-the-loop, confirms before execution). Run as a Team: Diagnostician and Scheduler run in parallel, both read live shop data. When done, Approver gate waits for human. This parallelism is faster than sequential. **Alternatively (simpler):** Single Orchestrator Agent: main agent asks questions, delegates to child agents, aggregates. **citizenry integration:** Citizens (Jetson/Pi nodes) can act as **subagents** if they expose MCP servers. Example: "`Shop-Floor Orchestrator (Managed Agent) asks Jetson-Spindle (citizen) for bearing wear → Jetson runs SmolVLA, returns result → Orchestrator synthesizes`". Subagents are the bridge between cloud control plane (Managed Agents) and edge compute (citizenry). **Constraint:** Subagents are still research preview; pilot carefully before production. **Post-EMEX timeline:** Design subagent architecture in H2 2026, pilot in Q1 2027.

---

## 14. Anthropic Workbench / Admin Dashboard / Observability

### (a) What it currently is
**Workbench** (claude.ai, production): hands-on IDE for exploring agents, prompts, skills. **Admin API** (production): programmatic access to organization, workspaces, members, API keys, rate limits. **Usage & Cost API** (production): query organization-wide token usage, costs, per-model breakdowns, exports. **Claude Code Analytics API** (beta): session-level insights (duration, tokens, tools used, success/failure). Limited public dashboards; most observability is via API calls. **No unified SaaS admin panel** (i.e., Datadog-style dashboard) yet; roadmap unclear. For NZ-based teams: standard claude.anthropic.com access, no region-specific hosting.

### (b) Application for Quintinity
**Operational necessity for production fleet.** Use **Usage & Cost API** to track: (1) tokens/day by agent type (Diagnostician vs. Scheduler), (2) cost per shop, (3) cost per query (to set pricing model for white-label). **Reporting:** Weekly cost breakdown to leadership: "`10 shops, 5k queries/day, $500/day API spend, margin 60%`". **Alerts:** Set threshold: if daily spend > $1k, page DevOps. **Claude Code Analytics (future):** Once stable, use to profile agent loop performance: which tools are slow, which agents are efficient. **Constraint:** No multi-region replication; all NZ traffic routes through Anthropic's US infrastructure (latency ~200ms, acceptable for async tasks). If Quintinity expands to APAC, consider caching layer or edge inference (Hailo-8L on Pi as fallback). **EMEX demo:** Don't over-expose costs; focus on capability. Post-EMEX, set up API integrations for cost tracking. **Post-EMEX:** Integrate Usage API into QuinBot customer portal: show each shop operator their monthly cost, token burn, recommendations for optimization. This drives adoption + justifies spend.

---

# Protocol Alignment Recommendation

## Core Question: Should citizenry's 7-message protocol coexist with, layer atop, or be replaced by MCP?

**Answer: Coexist + Bridge, not replace.**

**Why:**

1. **Protocol-level differences are fundamental:**
   - **citizenry:** UDP multicast (239.67.84.90:7770), asynchronous gossip, Ed25519-signed envelopes, presence + heartbeat (liveness detection), **governance by Constitution** (rules encoded in signed messages), 7 message types (HEARTBEAT, DISCOVER, ADVERTISE, PROPOSE, ACCEPT_REJECT, REPORT, GOVERN). Optimized for **decentralized fleet coordination** without a control plane.
   - **MCP:** HTTP/SSE (centralized server), synchronous request-response, tools + resources + prompts, no governance layer, optimized for **context distribution to Claude**. Assumes one Claude instance (or small team) querying many external services.

2. **citizenry does things MCP doesn't:**
   - Presence detection: "Is Jetson-Spindle online? If not, failover to Pi-Backup."
   - Gossip consensus: "All citizens agree Tool-X is failing → collective decision."
   - Signed governance: "Only actions approved by Constitution-signed votes are executed" (legal auditability).
   - Peer-to-peer discovery: Citizens find each other, negotiate roles, no DNS/registry required.

3. **MCP does things citizenry doesn't:**
   - Rich schema for tools (input_schema, descriptions, nested parameters): Claude can reason about tool semantics.
   - Built-in streaming: tool results flow incrementally.
   - OAuth + standardized auth: integrates with third-party SaaS.
   - Prompt + resource types: Claude can access read-only knowledge bases, templates.

**Bridge Architecture:**

```
[Cloud: Managed Agents]
         ↓ (MCP Connector)
[citizen-mcp-server] ← runs on each citizen (Jetson/Pi)
         ↓ (HTTP/SSE)
[Citizen local daemon] ← existing citizenry gossip
         ↓ (UDP multicast)
[Other citizens] ← peer-to-peer discovery
```

Each citizen exposes an **HTTP MCP server** that wraps its local capabilities (SmolVLA inference, sensor readings, tool-life predictors). Managed Agents discover citizens via MCP registry (or static config), call MCP tools, which internally invoke citizenry actions (e.g., "fetch bearing temp" → citizen-mcp-server calls local daemon → daemon reports via 7-message protocol to other peers). This preserves citizenry's decentralization while letting cloud agents (Claude) orchestrate. **Result:** Best of both worlds—fleet autonomy + cloud intelligence.

---

## Could each citizen BE an MCP server?

**Yes, and this is the bridge.**

**Changes needed:**
1. Each citizen adds an **HTTP wrapper** exposing an MCP server (e.g., Go/Rust HTTP listener on port 8080, implements MCP spec).
2. Citizen-MCP-server maps MCP tool calls → citizenry internal calls (bash, local state, 7-message gossip).
3. Managed Agents connect to citizen-mcp-servers via MCP Connector, specifying OAuth token (citizen's Ed25519 public key as bearer token).
4. Demo script: Visitor asks Managed Agent "`Show me Spindle-A status`" → Agent calls MCP tool "`get_spindle_status`" → citizen-mcp-server receives → citizen daemon queries local state + peer gossip → returns bearing temp, run hours, next maintenance → Agent formats response.

**EMEX demo** could be: (1) A Jetson/Pi running citizenry fully (in foreground), (2) A laptop running Managed Agent simulator (Anthropic SDK), (3) Operator asks question → Managed Agent makes MCP calls to Pi → Pi citizen responds with live data → operator sees real-time responsiveness.

---

## Should quintinity-v2's 92 MCP tools + 21 resources be productized as an Anthropic Skill?

**Yes, with caveats.**

**Rationale:**
- v2 is already structured as a domain-specific knowledge base for robotics + tool-life management.
- Packaging as a Skill (SKILL.md + REFERENCE.md + scripts) makes it reusable: any Claude user (via claude.ai, Claude API, Claude Code) can access Quintinity's expertise without reimplementation.
- Skilllets operators ask "`How do I optimize spindle maintenance?`" → Skill is triggered → Claude gets Quintinity's procedures + tools → responds with contextualized advice.

**Implementation path:**
1. Extract v2's 92 tools → organize into `.mcp` descriptors (tool names, schemas, descriptions).
2. Extract v2's system prompt + decision logic → SKILL.md.
3. Extract v2's reference docs (tool-life curves, sensor specs, safety rules) → REFERENCE.md, FORMS.md, SCRIPTS/ (Python utilities).
4. Upload to Anthropic Skills API (`/v1/skills` endpoints) as "`quintinity-advanced-maintenance`".
5. Customers with Claude API access can now reference it: `skill_id: "quintinity-advanced-maintenance"` in agent definitions.

**Distribution options:**
- **Anthropic marketplace** (if/when launches): Quintinity gets % of usage fees.
- **Direct white-label**: Package as custom Skill, embed in QuinBot (you control pricing).
- **Open-source community**: Release as public Skill on GitHub, build brand goodwill.

**Constraint:** Skills don't auto-sync across surfaces. If you want the Skill on Claude.ai + Claude API + Claude Code, you'll need separate packaging. Simplest: upload to API, and separately zip for claude.ai user uploads.

---

## Where does tab-runner fit?

**tab-runner** (Bradley's personal R&D across 4 repos, Jan–Apr 2026): agent-invariant meta-prompts that produce same MVP across Claude, GPT, Copilot, etc. **Scoring: ~9.8/10 on 10 dimensions.**

**Tab-runner's role in Quintinity context:**

Tab-runner is essentially **Skills before Skills were officially shipped**. It's a **prompt engineering methodology** for ensuring quality + consistency across model boundaries. **How to integrate:**

1. **Short-term (EMEX):** Use tab-runner's best practices to refine your Managed Agent system prompts (diagnostic, scheduler, approver). Ensure prompts are Claude-specific (don't try to be GPT-invariant; Claude is your target). Tab-runner's scoring rubric is useful for QA: rate your diagnostic prompt on clarity, tool-use guidance, error handling, etc.

2. **Medium-term:** Quintinity-v2's SKILL.md should be written with tab-runner discipline: clear structure, examples, error cases. This ensures the Skill is robust regardless of future Claude model updates.

3. **Long-term:** If Quintinity ever needs **fallback inference** (Claude unavailable, use local Hailo-8L SmolVLA on Pi), tab-runner's agent-invariant pattern helps: same prompt logic for "`What's the wear estimate?`" works for Claude, local model, or hybrid. Not a priority pre-EMEX, but relevant for resilience post-EMEX.

**Actionable:** Have Bradley review system prompts for your Managed Agents (Diagnostician, Scheduler) using tab-runner's rubric. Budget 1–2 days, cost ~$500 (consulting). **Don't** try to make prompts GPT-compatible; focus on Claude + clarity.

---

## What's the ONE capability to adopt FIRST in 29 days for EMEX?

**Answer: Managed Agents + Tool use (strict + parallel) + Streaming + Adaptive Thinking.**

**Why this combo + not others:**

- **Managed Agents:** Eliminates your agent loop code (nl-search-service.ts) → immediate infrastructure simplification. You focus on tools (shop DB queries) + context (TDM schema), Anthropic handles the rest. Reusable for future agents (Scheduler, Approver).
- **Strict tool use + parallel:** Ensures queries are fast + reliable. Diagnostician asks 3 questions in parallel, not sequentially. Tool responses are schema-guaranteed.
- **Streaming:** User sees response in real-time, not a 5s blank screen. Reduces uncertainty ("Is Claude thinking or did it freeze?").
- **Adaptive thinking:** Diagnostic reasoning is visible (if you choose to show it), builds credibility with shop operators and executives watching the demo.

**Why NOT others:**
- **MCP:** Cool, but integrating citizens requires 2–3 weeks of citizen-mcp-server dev + testing. Citizens can be shown as *future vision*, not EMEX-critical. **Defer to H2 2026.**
- **Computer Use:** No immediate use case for EMEX. **Defer.**
- **Batch API:** Offline only, not interactive. Useful post-EMEX for nightly analytics. **Defer.**
- **Skills:** Productizing v2 as a Skill takes 1–2 weeks of packaging. **Ship as basic Managed Agent first, productize post-EMEX.**
- **Files API:** Nice-to-have for uploads; not blocking. **Defer if tight on time.**
- **Prompt Caching:** Low-hanging fruit, but only matters at scale (100+ simultaneous queries). **Add in H2 2026 when traffic grows.**

**29-day sprint plan:**
- **Week 1 (2026-04-27 to 05-03):** Define Diagnostician agent (system prompt, tools, MCP servers if any).
- **Week 2 (05-04 to 05-10):** Implement tight tool schemas (strict: true), parallel tool calls.
- **Week 3 (05-11 to 05-17):** Integrate Managed Agents SDK (TypeScript), streaming + adaptive thinking, frontend display (gray thinking panel).
- **Week 4 (05-18 to 05-26):** Test with live TDM data, refine responses, dry-run demo.
- **05-26 to 05-28:** EMEX exhibition.

---

## What's the ONE capability that's a 12-month bet (frontier moat)?

**Answer: Managed Agents + Subagents + Citizen-MCP-Bridge + Memory Stores → "Auditable Agentic Fleet"**

**Why this creates a moat:**

**Executive summary:** Combine decision ledger (Constitution-signed) + MCP discovery (citizens auto-register) + Subagents (cloud orchestrates edge) + Memory Stores (org-wide learning) to build **a fleet management system that's transparent, defensible, and continuously improving**. This is not a feature; it's an **architecture** that competitors (MES vendors, ERP incumbents) can't easily replicate because it requires agent-native design from day one.

**Why 12 months:**
- **Q1–Q2 2026:** Current sprint (Managed Agents basics + EMEX).
- **Q2–Q3 2026:** Citizen-MCP bridge (citizens as servers), multi-agent Teams (parallel agents).
- **Q3–Q4 2026:** Subagents (hierarchical delegation), Memory Stores (org-wide learning across shops).
- **Q1 2027:** Compliance + audit (decision ledger + citations integration), white-label licensing.

**Moat mechanics:**

1. **Unique architecture:** No other platform combines **decentralized edge governance (citizenry) + cloud agentic orchestration (Managed Agents) + memory/learning (Memory Stores)**. Traditional MES/ERP vendors think centralized (SQL Server on-prem); cloud-native vendors think stateless (serverless functions). Quintinity's hybrid is novel.

2. **Data lock-in (ethical):** Once 50 shops use QuinBot for maintenance planning + diagnostics, they generate 1M+ decisions + memories in Quintinity's Memory Stores. Switching costs: rebuild all that institutional knowledge. **Ethical** because it's not hiding data; customers see decision ledger + can export.

3. **Efficiency gap:** With Subagents + parallel agents + caching + Batch API for nightly optimization, Quintinity's cost-per-diagnostic will be 10x lower than competitors' (who build monolithic agents). Margins widen, pricing can be competitive.

4. **Regulatory advantage:** Decision ledger + citations + extended thinking chains = auditable maintenance decisions. ISO 9001, equipment liability disputes, worker safety claims—all defensible. Competitors can't match without agents. **Positioning:** "Auditable AI for manufacturing."

**How to bet on it:**
- **Team:** Hire a senior full-stack engineer (node/ML) H2 2026 to architect subagent framework.
- **Infrastructure:** Pilot Memory Stores integration (Managed Agents research preview) with 1–2 internal shops Q3 2026.
- **IP:** Patent the citizen-mcp-bridge architecture (if Anthropic doesn't beat you to it).
- **Go-to-market:** Position QuinBot as "AI that shop floor supervisors trust because they can see the reasoning."

---

## Ethical/Safety Positioning

**Question:** What ethical + safety narrative falls naturally out of these capabilities?

**Answer: "Auditable, Consensual, Continuously-Improving Agentic Manufacturing."**

**Three pillars:**

### 1. **Auditability (Decision Ledger + Citations)**
- Every maintenance decision is recorded with:
  - Who asked (shop operator, system scheduler).
  - What data Claude saw (files, tool calls, MCP responses).
  - What Claude reasoned (thinking blocks via extended thinking).
  - What Claude recommended (decision + confidence + alternatives).
  - When + who approved (human approval gate).
- **Ethics angle:** Shop workers aren't at the mercy of a black-box algorithm; supervisors and auditors can trace why Tool-X was replaced. If there's a dispute ("`Why did you replace it? It looked fine!`"), you have the decision log. **Legal defensibility** = trust.

### 2. **Consent & Human Gates (4-tier action gating in v2)**
- Observe (Claude gathers data).
- Suggest (Claude proposes action).
- Act-with-approval (Claude waits for human sign-off).
- Act-autonomously (only for low-risk tasks, e.g., alerts; high-risk tasks always wait).
- **Ethics angle:** Humans stay in control. Claude amplifies human judgment; doesn't replace it. Workers see the recommendation first, can ask "why" (via extended thinking), then approve. **Empowerment** = trust.

### 3. **Continuous Learning (Memory Stores + Memory Tool)**
- Fleet-wide memory: "This shop's Spindle-A fails due to underlubrication; that shop's Spindle-B fails due to bearing wear." Claude learns from both.
- Feedback loops: Maintenance staff annotate decisions ("Diagnosis was correct" or "We found a different root cause"). Claude internalizes, improves.
- **Ethics angle:** System improves over time; not static. Reduces future mistakes. **Accountability** = trust.

**Positioning statement (for QuinBot):**
> "Auditable AI for manufacturing. Every maintenance decision is traceable, every action approved by humans, every lesson shared across your fleet. We don't replace expert judgment; we amplify it."

**Competitive angle:** Traditional MES/ERP + cloud AI vendors ship opaque optimization. Quintinity ships transparent reasoning + human control + collective learning.

**Regulatory angle:** ISO 9001 (quality management), OSHA (worker safety), product liability—all require documented decision-making. QuinBot **is** the documentation system. Competitor with black-box AI can't pass audit; Quintinity can.

---

# Summary Table: Which Capabilities to Prioritize

| Capability | Priority | EMEX | H1 2027 | Notes |
|---|---|---|---|---|
| **Managed Agents** | 🔴 Critical | ✓ Ship | Core | Foundation for all agents |
| **MCP Connector** | 🟠 High | Demo (future) | ✓ Integrate | Citizen bridge; defer 2 months |
| **Tool Use (strict + parallel)** | 🔴 Critical | ✓ Ship | Core | Fast, reliable queries |
| **Streaming + Adaptive Thinking** | 🔴 Critical | ✓ Ship | Core | Visible reasoning, credibility |
| **Prompt Caching** | 🟡 Medium | ✓ (simple) | ✓ Expand | Cost control, add post-EMEX |
| **Extended Thinking** | 🟠 High | Optional | ✓ Adopt | Diagnostic reasoning depth |
| **Memory Tool** | 🟠 High | Plan | ✓ Integrate | Refactor v2 memory layers |
| **Memory Stores** | 🟡 Medium | N/A | ✓ Pilot | Org-wide learning, research preview |
| **Subagents** | 🟡 Medium | N/A | ✓ Explore | Hierarchical tasks, research preview |
| **Code Execution** | 🟠 High | ✓ (for analysis) | Core | Ad-hoc data analysis |
| **Files API + Citations** | 🟡 Medium | Nice-to-have | ✓ Adopt | Compliance + auditability |
| **Skills** | 🟡 Medium | N/A | ✓ Productize | v2 as reusable Skill post-EMEX |
| **Computer Use** | 🟢 Low | N/A | Explore | Legacy system integration, future |
| **Batch API** | 🟢 Low | N/A | ✓ Use | Nightly bulk analysis, cost savings |
| **Multi-Agent Teams** | 🟡 Medium | N/A | ✓ Pilot | Parallel agents, production at scale |

---

# Concrete Deliverables for Bradley

1. **29-day EMEX sprint:** Managed Agents + 6 strict-schema tools (search_products, search_failures, search_sensors, get_history, analyze_failure, get_maintenance_plan) + streaming + adaptive thinking. **Deadline:** 2026-05-18 (dry-run).

2. **Post-EMEX roadmap document:** Detailed timeline for citizen-MCP bridge (Q2 2026), Subagents pilot (Q3 2026), Memory Stores integration (Q4 2026), white-label Skills (Q1 2027).

3. **Quintinity-v2 refactor plan:** Map 92 tools → MCP contract, refactor system prompt for Citizens + Managed Agents, organize memory layers (episodic/semantic/procedural) as `/memories` structure.

4. **Skill packaging checklist:** SKILL.md structure, REFERENCE.md (tool-life data), FORMS.md (examples), SCRIPTS/ (Python utilities). Ready for upload by 2026-07-01.

5. **Audit/compliance playbook:** Decision ledger schema, citation integration, reasoning log storage, sample audit report for ISO 9001 / product liability scenarios.

---

# Sources

- [Anthropic Introduces Managed Agents to Simplify AI Agent Deployment](https://www.infoq.com/news/2026/04/anthropic-managed-agents/)
- [Anthropic's Engineering Blog: Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents)
- [Claude Managed Agents Deep Dive (DEV Community)](https://dev.to/bean_bean/claude-managed-agents-deep-dive-anthropics-new-ai-agent-infrastructure-2026-3286)
- [Platform Documentation: Claude Managed Agents Overview](https://platform.claude.com/docs/en/managed-agents/overview.md)
- [Platform Documentation: MCP Connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector.md)
- [Platform Documentation: Computer Use Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool.md)
- [Platform Documentation: Code Execution Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool.md)
- [Platform Documentation: Files API](https://platform.claude.com/docs/en/build-with-claude/files.md)
- [Platform Documentation: Memory Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.md)
- [Platform Documentation: Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking.md)
- [Platform Documentation: Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md)
- [Platform Documentation: Batch Processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing.md)
- [Platform Documentation: Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md)
- [Platform Documentation: Tool Use Overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md)
- [Building with Claude Extended Thinking (Medium, Apr 2026)](https://cobusgreyling.medium.com/building-with-claude-extended-thinking-d1a8b3130834)
- [With Claude Managed Agents, Anthropic wants to run your AI agents for you (The New Stack)](https://thenewstack.io/with-claude-managed-agents-anthropic-wants-to-run-your-ai-agents-for-you/)
agentId: a596072b84f803c2e (use SendMessage with to: 'a596072b84f803c2e' to continue this agent)
<usage>total_tokens: 79405
tool_uses: 15
duration_ms: 230263</usage>
