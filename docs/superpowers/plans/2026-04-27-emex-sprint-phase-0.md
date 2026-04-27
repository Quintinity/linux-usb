# EMEX 2026 — Phase 0 Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working 3×3m triptych demo at EMEX (26–28 May 2026) that captures 50+ qualified conversations and 30+ booked diagnostic calls toward the founding-five partnership pipeline.

**Architecture:** Three integrated demo cells running in parallel during the show.
- **Cell 1 (left wall):** Existing TDM/Hone web app + a new Quin-agent (Anthropic Managed Agents) running 6 strict-schema tools over anonymised Accord data, with streaming + adaptive thinking visible.
- **Cell 2 (centre wall):** Existing citizenry mesh + SO-101 leader/follower arms + XIAO camera, doing live teleop teach-and-replay on a kit-sort task; Constitution edits via tablet governor CLI.
- **Cell 3 (right wall):** Two thin MCP servers (`tdm-mcp`, `citizen-mcp`) + a Claude session that orchestrates both, with a 4-tier human-approval gate on tablet and decision-ledger entries written for every action.

**Tech stack:**
- **Backend:** Anthropic Managed Agents (April 2026), MCP (Model Context Protocol), Fastify + Drizzle (TDM), Python 3.12 + asyncio (citizenry), PyNaCl (Ed25519), Redis (already deployed).
- **Frontend:** React 18 + Vite + Tailwind + shadcn/ui (TDM existing), one new tablet UI for the approval gate.
- **Hardware:** SO-101 Feetech servo arms ×2 (leader + follower), Pi 5, Surface Pro 7, XIAO ESP32S3 cameras ×2 (one live, one spare), iPad ×3 (lead capture × stand-side × approval gate).
- **Repos involved:** `Quintinity/pcrottet-tool-data-management` (Cell 1), `linux-usb` / citizenry (Cell 2 + Cell 3 servers), Quintinity website (W4).

**Sprint window:** 2026-04-27 → 2026-05-25 rehearsal. Show: 2026-05-26 to 28. Pack-down 2026-05-28 evening.

**Workstreams:**
| # | Stream | Lead | Days | Tasks |
|---|---|---|---|---|
| W0 | Cross-cutting setup | Bradley | 1–2 | T1–T3 |
| W1 | Cell 1 — Quin agent on TDM | Philippe | 5–7 | T4–T15 |
| W2 | Cell 2 — Robot teach-and-replay | Bradley | 8–12 | T16–T24 |
| W3 | Cell 3 — MCP bridge | both | 7–10 | T25–T31 |
| W4 | Physical stand + marketing | contract + Bradley | 14 (parallel) | T32–T40 |
| W5 | Rehearsal + comms + scripts | Bradley | last 5 | T41–T50 |
| W6 | At-show execution | both + helper | 3 days + post | T51–T58 |

**Conventions:**
- Each task lists exact file paths and which repo it lives in (`[TDM]` or `[citizenry]`).
- Software tasks use TDD: failing test → run → implement → run → commit.
- Physical/comms tasks use deliverable checkboxes.
- Commit prefixes: `emex:` for show-specific work, `quin-agent:` for Cell 1, `citizenry:` for Cell 2, `mcp:` for Cell 3.

---

## Workstream W0 — Cross-cutting setup

### Task 1: Anthropic API + Managed Agents enrolment

**Files:**
- Create: `~/linux-usb/docs/emex/secrets.md.gpg` (encrypted notes; not committed)
- Modify: `~/.bashrc` (add `ANTHROPIC_API_KEY` env var; do NOT commit)

- [ ] **Step 1: Enrol in Managed Agents beta**

Visit https://console.anthropic.com → Agents → request beta access. If already enrolled, note the agent-creation endpoint URL and confirm `claude-opus-4-7` is listed as an available model.

- [ ] **Step 2: Provision a dedicated EMEX API key**

Console → Settings → API Keys → "Create key", name it `emex-2026-stand`. Set workspace budget alert at NZ$500 (≈US$300) for the show window.

- [ ] **Step 3: Test with a one-shot call**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-opus-4-7","max_tokens":64,"messages":[{"role":"user","content":"hello"}]}'
```

Expected: HTTP 200 with a content array. If 401 or 403, fix auth before continuing — every other task depends on this.

- [ ] **Step 4: Document the key handling rule**

Write `~/linux-usb/docs/emex/README.md` with one section: "API keys live in env vars and `.env.local` files only — never in git, never in screenshots, never on the stand iPad". Commit the README only.

- [ ] **Step 5: Commit**

```bash
git add docs/emex/README.md
git commit -m "emex: stand-prep README + API-key handling rule"
```

---

### Task 2: Provision EMEX-specific TDM demo VM snapshot

**Files:**
- Modify: `[TDM] scripts/azure/snapshot-for-demo.sh` (create if absent)
- Create: `[TDM] docs/emex/demo-vm.md`

- [ ] **Step 1: Snapshot the live Accord production VM**

```bash
ssh azureuser@20.98.97.132 'sudo systemctl stop tdm-api'
az vm snapshot create -g pcrottet-rg --source-disk tdm-prod-osdisk --name tdm-emex-snapshot
ssh azureuser@20.98.97.132 'sudo systemctl start tdm-api'
```

Total downtime: <60s. Run during NZ overnight when Accord shop is closed.

- [ ] **Step 2: Provision the demo VM from the snapshot**

```bash
az vm create -g pcrottet-rg -n vm-clawdbot-demo \
  --size Standard_D2s_v3 \
  --attach-os-disk tdm-emex-snapshot \
  --public-ip-sku Standard
```

Confirm the demo VM has a different public IP from the production VM.

- [ ] **Step 3: Anonymise Accord-identifying fields in the demo DB**

```bash
ssh azureuser@$DEMO_IP 'sudo -u postgres psql tdm <<SQL
UPDATE machine SET name = "MC-" || id WHERE name ILIKE "%accord%";
UPDATE works_order SET works_order_no = "WO-" || id WHERE works_order_no ILIKE "%accord%";
UPDATE app_user SET first_name = "Operator", last_name = id::text WHERE id <> 1;
SQL'
```

- [ ] **Step 4: Document demo-VM credentials**

Write `[TDM] docs/emex/demo-vm.md`: IP, SSH key location, "DO NOT POINT AT PROD" warning, rollback procedure (drop demo VM, no impact on prod).

- [ ] **Step 5: Commit**

```bash
git add docs/emex/demo-vm.md scripts/azure/snapshot-for-demo.sh
git commit -m "emex: dedicated demo VM provisioning from prod snapshot"
```

---

### Task 3: Lead-capture funnel (form + Slack)

**Files:**
- Create: `~/linux-usb/docs/emex/lead-capture.md`

- [ ] **Step 1: Build the Tally form**

Tally form with 6 fields: Name, Company, Role, Email, Phone, "Want a free 1-hour AI diagnostic call?" (yes/no). 30-second completion target. URL: `https://tally.so/r/quintinity-emex-2026`.

- [ ] **Step 2: Wire form submissions to Slack**

Tally → Integrations → Slack webhook → channel `#emex-2026-leads`. Test with a dummy submission.

- [ ] **Step 3: Set up post-show auto-responder**

In your email client / Mailgun / SendGrid, create a 24h auto-responder that fires on any address captured during the show window: "Thanks for stopping by — we'll be in touch within 5 working days to set up your diagnostic. Meanwhile, here's the founding-five microsite: …".

- [ ] **Step 4: Document the funnel**

Write `docs/emex/lead-capture.md`: Tally URL, Slack channel, auto-responder template, post-show 24h triage rule (every lead gets a personal email within 24h of show close).

- [ ] **Step 5: Commit**

```bash
git add docs/emex/lead-capture.md
git commit -m "emex: lead capture funnel — Tally + Slack + auto-responder"
```

---

## Workstream W1 — Cell 1: Quin agent on TDM (Philippe lead)

> All tasks in this workstream live in repo `Quintinity/pcrottet-tool-data-management` unless prefixed otherwise. Switch repos with `cd ~/path/to/pcrottet-tool-data-management` before starting.

### Task 4: Author Quin-agent system prompt using tab-runner rubric

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/system-prompt.md`
- Create: `[TDM] docs/quin-agent/prompt-rubric.md`

- [ ] **Step 1: Internalise tab-runner rubric**

Read `~/.tab-runner-rubric.md` (or copy from `BradleyFestraets/tab-runner-githubcopilot-ide/tab-runner-ultimate-prompt.md`). Score dimensions: stack-specificity, state-management clarity, zero-setup feasibility, error-handling discipline, persona consistency, tool-use guidance, output-format constraint, hallucination resistance, conversational tone, escalation rules.

- [ ] **Step 2: Write the system prompt**

`packages/api/src/services/quin-agent/system-prompt.md` — ~600 words. Persona: "Quin, an embedded engineering assistant for Accord-style precision shops". Constraints: read-only on shop data; cite job/machine/operator IDs from tool results; default to plain-English with NZ English spelling; never invent figures; always structure responses as Finding → Evidence → Recommendation.

- [ ] **Step 3: Score the prompt against the rubric**

Self-score each dimension out of 10 in `docs/quin-agent/prompt-rubric.md`. Target: ≥9.0 average. Fix any dimension below 8 before continuing.

- [ ] **Step 4: Commit**

```bash
git add packages/api/src/services/quin-agent/system-prompt.md docs/quin-agent/prompt-rubric.md
git commit -m "quin-agent: system prompt + tab-runner rubric scoring (≥9.0)"
```

---

### Task 5: Define 6 strict-schema tool descriptors

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/tools.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/tools.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// packages/api/src/services/quin-agent/tools.test.ts
import { describe, it, expect } from 'vitest';
import { QUIN_TOOLS } from './tools';

describe('QUIN_TOOLS', () => {
  it('exposes exactly 6 tools', () => {
    expect(QUIN_TOOLS).toHaveLength(6);
  });

  it('includes the named diagnostic tools', () => {
    const names = QUIN_TOOLS.map(t => t.name).sort();
    expect(names).toEqual([
      'get_consumption_stats',
      'get_vendor_spend',
      'search_products',
      'search_purchase_orders',
      'search_stock',
      'search_transactions',
    ]);
  });

  it('every tool has strict input_schema', () => {
    for (const t of QUIN_TOOLS) {
      expect(t.input_schema.type).toBe('object');
      expect(t.input_schema.additionalProperties).toBe(false);
      expect(Array.isArray(t.input_schema.required)).toBe(true);
    }
  });
});
```

- [ ] **Step 2: Run test, confirm failure**

```bash
cd ~/path/to/pcrottet-tool-data-management
pnpm --filter @tdm/api test tools
```

Expected: FAIL ("Cannot find module './tools'").

- [ ] **Step 3: Implement the descriptors**

```typescript
// packages/api/src/services/quin-agent/tools.ts
export interface QuinTool {
  name: string;
  description: string;
  input_schema: {
    type: 'object';
    properties: Record<string, unknown>;
    required: string[];
    additionalProperties: false;
  };
}

export const QUIN_TOOLS: QuinTool[] = [
  {
    name: 'search_products',
    description: 'Find tools/components by part number, brand, category, or keyword. Returns up to 25 hits.',
    input_schema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Free-text search across part_no, name, brand' },
        category_id: { type: 'string', description: 'Optional tool_category id' },
        brand_id: { type: 'string', description: 'Optional brand id' },
      },
      required: ['query'],
      additionalProperties: false,
    },
  },
  // ... five more, same shape (search_transactions, search_purchase_orders,
  // search_stock, get_consumption_stats, get_vendor_spend)
];
```

(Define each of the remaining 5 with concrete schemas; refer to existing `nl-search-service.ts` for the underlying queries.)

- [ ] **Step 4: Run test, confirm pass**

```bash
pnpm --filter @tdm/api test tools
```

Expected: PASS, 3/3 assertions.

- [ ] **Step 5: Commit**

```bash
git add packages/api/src/services/quin-agent/tools.ts packages/api/src/services/quin-agent/tools.test.ts
git commit -m "quin-agent: 6 strict-schema tool descriptors with schema test"
```

---

### Task 6: Implement `search_products` handler

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/handlers/search-products.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/handlers/search-products.test.ts`

- [ ] **Step 1: Failing test**

```typescript
// search-products.test.ts
import { describe, it, expect, beforeAll } from 'vitest';
import { searchProducts } from './search-products';
import { db, seedTestData } from '../../../testing/db';

describe('searchProducts', () => {
  beforeAll(async () => { await seedTestData(); });

  it('returns matching products by query', async () => {
    const results = await searchProducts(db, { query: 'endmill' });
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]).toHaveProperty('part_no');
  });

  it('caps results at 25', async () => {
    const results = await searchProducts(db, { query: '' });
    expect(results.length).toBeLessThanOrEqual(25);
  });
});
```

- [ ] **Step 2: Run, confirm failure**

```bash
pnpm --filter @tdm/api test search-products
```

- [ ] **Step 3: Implement**

```typescript
// search-products.ts
import { sql } from 'drizzle-orm';
import type { Database } from '../../../db';

export interface SearchProductsArgs {
  query: string;
  category_id?: string;
  brand_id?: string;
}

export async function searchProducts(db: Database, args: SearchProductsArgs) {
  const q = `%${args.query}%`;
  return db.execute(sql`
    SELECT id, part_no, name, brand_id, tool_category_id
    FROM product
    WHERE (name ILIKE ${q} OR part_no ILIKE ${q})
      ${args.category_id ? sql`AND tool_category_id = ${args.category_id}` : sql``}
      ${args.brand_id ? sql`AND brand_id = ${args.brand_id}` : sql``}
    LIMIT 25
  `);
}
```

- [ ] **Step 4: Run, confirm pass**

- [ ] **Step 5: Commit**

```bash
git add packages/api/src/services/quin-agent/handlers/search-products.ts packages/api/src/services/quin-agent/handlers/search-products.test.ts
git commit -m "quin-agent: search_products handler"
```

---

### Task 7: Implement `search_transactions` handler

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/handlers/search-transactions.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/handlers/search-transactions.test.ts`

Same TDD cycle as Task 6 (failing test → fail → implement → pass → commit).

- [ ] **Step 1: Failing test** — assert that `searchTransactions(db, { mode: 'SCRAP', from: '2026-01-01', to: '2026-04-01' })` returns rows with `mode === 'SCRAP'` and dates inside the window.

- [ ] **Step 2: Implement**

```typescript
export interface SearchTransactionsArgs {
  mode?: 'TAKE'|'RETURN'|'SCRAP'|'REFILL'|'LOAD'|'UNLOAD'|'ADJUST';
  from?: string; to?: string;
  job_machine?: string; job_code?: string; performed_by?: string;
}
export async function searchTransactions(db: Database, args: SearchTransactionsArgs) {
  return db.execute(sql`
    SELECT id, mode, qty, job_machine, job_code, job_operation, performed_by, ts, notes
    FROM transaction
    WHERE 1=1
      ${args.mode ? sql`AND mode = ${args.mode}` : sql``}
      ${args.from ? sql`AND ts >= ${args.from}` : sql``}
      ${args.to ? sql`AND ts <= ${args.to}` : sql``}
      ${args.job_machine ? sql`AND job_machine = ${args.job_machine}` : sql``}
      ${args.job_code ? sql`AND job_code = ${args.job_code}` : sql``}
      ${args.performed_by ? sql`AND performed_by = ${args.performed_by}` : sql``}
    ORDER BY ts DESC LIMIT 50
  `);
}
```

- [ ] **Step 3: Run, confirm pass.**

- [ ] **Step 4: Commit** — `git commit -m "quin-agent: search_transactions handler"`

---

### Task 8: Implement `search_purchase_orders` handler

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/handlers/search-purchase-orders.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/handlers/search-purchase-orders.test.ts`

- [ ] **Step 1: Failing test** — assert filter by status returns only matching status rows.

- [ ] **Step 2: Implement**

```typescript
export interface SearchPurchaseOrdersArgs {
  status?: 'DRAFT'|'SENT'|'PARTIAL'|'RECEIVED';
  vendor_id?: string; from?: string; to?: string;
}
export async function searchPurchaseOrders(db: Database, args: SearchPurchaseOrdersArgs) {
  return db.execute(sql`
    SELECT po.id, po.po_number, po.status, po.total_value, v.name AS vendor_name,
           po.lead_time_days, po.created_at, COUNT(pol.id) AS line_count
    FROM purchase_order po
    LEFT JOIN purchase_order_line pol ON pol.purchase_order_id = po.id
    LEFT JOIN vendor v ON v.id = po.vendor_id
    WHERE 1=1
      ${args.status ? sql`AND po.status = ${args.status}` : sql``}
      ${args.vendor_id ? sql`AND po.vendor_id = ${args.vendor_id}` : sql``}
    GROUP BY po.id, v.name
    ORDER BY po.created_at DESC LIMIT 25
  `);
}
```

- [ ] **Step 3: Run, confirm pass.**

- [ ] **Step 4: Commit** — `git commit -m "quin-agent: search_purchase_orders handler"`

---

### Task 9: Implement `search_stock` handler

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/handlers/search-stock.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/handlers/search-stock.test.ts`

- [ ] **Step 1: Failing test** — `low_stock_only: true` returns only rows where `qty_on_hand <= reorder_min`.

- [ ] **Step 2: Implement**

```typescript
export interface SearchStockArgs {
  product_id?: string; location_id?: string; low_stock_only?: boolean;
}
export async function searchStock(db: Database, args: SearchStockArgs) {
  return db.execute(sql`
    SELECT sb.id, sb.product_id, p.part_no, p.name AS product_name,
           sb.location_id, l.name AS location_name,
           sb.qty_on_hand, sb.qty_checked_out, sb.reorder_min, sb.reorder_max, sb.reorder_critical
    FROM stock_balance sb
    JOIN product p ON p.id = sb.product_id
    JOIN location l ON l.id = sb.location_id
    WHERE 1=1
      ${args.product_id ? sql`AND sb.product_id = ${args.product_id}` : sql``}
      ${args.location_id ? sql`AND sb.location_id = ${args.location_id}` : sql``}
      ${args.low_stock_only ? sql`AND sb.qty_on_hand <= sb.reorder_min` : sql``}
    ORDER BY sb.qty_on_hand ASC LIMIT 50
  `);
}
```

- [ ] **Step 3: Run, confirm pass.**

- [ ] **Step 4: Commit** — `git commit -m "quin-agent: search_stock handler"`

---

### Task 10: Implement `get_consumption_stats` handler

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/handlers/get-consumption-stats.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/handlers/get-consumption-stats.test.ts`

- [ ] **Step 1: Failing test** — given seeded SCRAP transactions, returns avg tool life > 0 for the seeded tool.

- [ ] **Step 2: Implement**

```typescript
export interface GetConsumptionStatsArgs {
  product_id?: string; job_machine?: string; from?: string; to?: string;
}
export async function getConsumptionStats(db: Database, args: GetConsumptionStatsArgs) {
  return db.execute(sql`
    SELECT t.product_id, p.part_no, p.name,
           t.job_machine,
           COUNT(*) FILTER (WHERE t.mode = 'SCRAP') AS total_scrapped,
           AVG((t.notes::jsonb ->> 'tool_life_parts')::numeric) FILTER (WHERE t.mode = 'SCRAP') AS avg_tool_life,
           COUNT(*) FILTER (WHERE t.mode = 'SCRAP')::float
             / NULLIF(COUNT(*) FILTER (WHERE t.mode IN ('TAKE','SCRAP','RETURN')), 0)
           AS scrap_rate
    FROM transaction t JOIN product p ON p.id = t.product_id
    WHERE 1=1
      ${args.product_id ? sql`AND t.product_id = ${args.product_id}` : sql``}
      ${args.job_machine ? sql`AND t.job_machine = ${args.job_machine}` : sql``}
      ${args.from ? sql`AND t.ts >= ${args.from}` : sql``}
      ${args.to ? sql`AND t.ts <= ${args.to}` : sql``}
    GROUP BY t.product_id, p.part_no, p.name, t.job_machine
    ORDER BY total_scrapped DESC LIMIT 25
  `);
}
```

- [ ] **Step 3: Run, confirm pass.**

- [ ] **Step 4: Commit** — `git commit -m "quin-agent: get_consumption_stats handler"`

---

### Task 11: Implement `get_vendor_spend` handler

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/handlers/get-vendor-spend.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/handlers/get-vendor-spend.test.ts`

- [ ] **Step 1: Failing test** — given seeded POs across two vendors, returns rows sorted by total_spend desc.

- [ ] **Step 2: Implement**

```typescript
export interface GetVendorSpendArgs {
  from?: string; to?: string; vendor_id?: string;
}
export async function getVendorSpend(db: Database, args: GetVendorSpendArgs) {
  return db.execute(sql`
    SELECT v.id AS vendor_id, v.name AS vendor_name,
           SUM(po.total_value) AS total_spend,
           COUNT(po.id) AS order_count,
           AVG(po.lead_time_days) AS avg_lead_time
    FROM vendor v JOIN purchase_order po ON po.vendor_id = v.id
    WHERE 1=1
      ${args.from ? sql`AND po.created_at >= ${args.from}` : sql``}
      ${args.to ? sql`AND po.created_at <= ${args.to}` : sql``}
      ${args.vendor_id ? sql`AND v.id = ${args.vendor_id}` : sql``}
    GROUP BY v.id, v.name
    ORDER BY total_spend DESC LIMIT 25
  `);
}
```

- [ ] **Step 3: Run, confirm pass.**

- [ ] **Step 4: Commit** — `git commit -m "quin-agent: get_vendor_spend handler"`

---

### Task 12: Wire Managed Agents + tools + streaming

**Files:**
- Create: `[TDM] packages/api/src/services/quin-agent/agent.ts`
- Create: `[TDM] packages/api/src/routes/quin-chat.ts`
- Test: `[TDM] packages/api/src/services/quin-agent/agent.test.ts`

- [ ] **Step 1: Failing integration test**

```typescript
// agent.test.ts
import { describe, it, expect } from 'vitest';
import { runQuinTurn } from './agent';

describe('runQuinTurn', () => {
  it('streams events and emits a final response', async () => {
    const events: any[] = [];
    await runQuinTurn(
      { messages: [{ role: 'user', content: 'How many drills do we have in stock?' }] },
      (e) => events.push(e),
    );
    expect(events.some(e => e.type === 'tool_use')).toBe(true);
    expect(events.some(e => e.type === 'text')).toBe(true);
  });
});
```

(This test hits the live Anthropic API in CI when `ANTHROPIC_API_KEY` is set; gate with `it.skipIf(!process.env.ANTHROPIC_API_KEY)`.)

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement**

```typescript
// agent.ts
import Anthropic from '@anthropic-ai/sdk';
import { QUIN_TOOLS } from './tools';
import { dispatchTool } from './dispatch';
import { readFileSync } from 'fs';

const client = new Anthropic();
const SYSTEM_PROMPT = readFileSync(
  new URL('./system-prompt.md', import.meta.url),
  'utf8',
);

export async function runQuinTurn(
  ctx: { messages: Anthropic.MessageParam[] },
  onEvent: (e: unknown) => void,
) {
  const stream = client.messages.stream({
    model: 'claude-opus-4-7',
    max_tokens: 4096,
    system: SYSTEM_PROMPT,
    tools: QUIN_TOOLS,
    messages: ctx.messages,
    thinking: { type: 'enabled', budget_tokens: 2048 },
  });

  for await (const evt of stream) {
    onEvent(evt);
    if (evt.type === 'content_block_stop' && evt.content_block?.type === 'tool_use') {
      const result = await dispatchTool(evt.content_block);
      ctx.messages.push({ role: 'user', content: [{ type: 'tool_result', tool_use_id: evt.content_block.id, content: JSON.stringify(result) }] });
      // Recursive turn for tool result handling
      return runQuinTurn(ctx, onEvent);
    }
  }
}
```

- [ ] **Step 4: Implement the dispatch table**

```typescript
// dispatch.ts
import { searchProducts } from './handlers/search-products';
import { searchTransactions } from './handlers/search-transactions';
// ... import the other 4
import { db } from '../../db';

const HANDLERS = {
  search_products: (args: any) => searchProducts(db, args),
  search_transactions: (args: any) => searchTransactions(db, args),
  // ... 4 more
};

export async function dispatchTool(block: { name: string; input: unknown }) {
  const fn = HANDLERS[block.name as keyof typeof HANDLERS];
  if (!fn) throw new Error(`unknown tool: ${block.name}`);
  return fn(block.input);
}
```

- [ ] **Step 5: Implement the streaming HTTP route**

```typescript
// quin-chat.ts
import type { FastifyInstance } from 'fastify';
import { runQuinTurn } from '../services/quin-agent/agent';

export default async function quinChat(app: FastifyInstance) {
  app.post('/api/quin/chat', async (req, reply) => {
    reply.raw.setHeader('Content-Type', 'text/event-stream');
    reply.raw.setHeader('Cache-Control', 'no-cache');
    const { messages } = req.body as { messages: any[] };
    await runQuinTurn({ messages }, (evt) => {
      reply.raw.write(`data: ${JSON.stringify(evt)}\n\n`);
    });
    reply.raw.end();
  });
}
```

- [ ] **Step 6: Run integration test, confirm pass**

```bash
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY pnpm --filter @tdm/api test agent
```

- [ ] **Step 7: Commit**

```bash
git add packages/api/src/services/quin-agent packages/api/src/routes/quin-chat.ts
git commit -m "quin-agent: streaming Managed Agents wrapper + 6-tool dispatch"
```

---

### Task 13: Build QuinChat UI panel with adaptive thinking display

**Files:**
- Create: `[TDM] packages/web/src/components/QuinChat.tsx`
- Create: `[TDM] packages/web/src/components/ThinkingPanel.tsx`
- Test: `[TDM] packages/web/src/components/QuinChat.test.tsx`

- [ ] **Step 1: Failing component test**

```tsx
// QuinChat.test.tsx
import { render, screen } from '@testing-library/react';
import { QuinChat } from './QuinChat';

describe('QuinChat', () => {
  it('renders the input', () => {
    render(<QuinChat />);
    expect(screen.getByPlaceholderText(/ask about your shop/i)).toBeInTheDocument();
  });
  it('renders a thinking panel when streaming', () => {
    render(<QuinChat initialState="thinking" />);
    expect(screen.getByTestId('thinking-panel')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, confirm failure**

- [ ] **Step 3: Implement ThinkingPanel**

```tsx
// ThinkingPanel.tsx
export function ThinkingPanel({ thinking, done }: { thinking: string; done: boolean }) {
  return (
    <div data-testid="thinking-panel"
         className={`rounded border px-3 py-2 text-sm transition-opacity ${done ? 'opacity-50' : 'opacity-100'}`}
         style={{ background: 'oklch(0.18 0.01 250)', color: 'oklch(0.65 0.02 250)' }}>
      <div className="text-xs uppercase tracking-wider mb-1 opacity-70">Reasoning</div>
      <pre className="whitespace-pre-wrap font-sans">{thinking}</pre>
    </div>
  );
}
```

- [ ] **Step 4: Implement QuinChat**

```tsx
// QuinChat.tsx
import { useState } from 'react';
import { ThinkingPanel } from './ThinkingPanel';

export function QuinChat({ initialState }: { initialState?: 'thinking' }) {
  const [messages, setMessages] = useState<Array<{role: string; content: string}>>([]);
  const [thinking, setThinking] = useState(initialState === 'thinking' ? 'Initialising…' : '');
  const [streaming, setStreaming] = useState(initialState === 'thinking');
  const [input, setInput] = useState('');

  async function ask() {
    setStreaming(true); setThinking(''); 
    const userMsg = { role: 'user', content: input };
    setMessages(m => [...m, userMsg]); setInput('');
    const es = new EventSource(`/api/quin/chat?body=${encodeURIComponent(JSON.stringify({ messages: [...messages, userMsg] }))}`);
    let assistantText = '';
    es.onmessage = (e) => {
      const evt = JSON.parse(e.data);
      if (evt.type === 'thinking_delta') setThinking(t => t + evt.delta);
      if (evt.type === 'text_delta') assistantText += evt.delta;
      if (evt.type === 'message_stop') {
        setMessages(m => [...m, { role: 'assistant', content: assistantText }]);
        setStreaming(false); es.close();
      }
    };
  }

  return (
    <div className="flex flex-col gap-3 p-4 max-w-2xl">
      {messages.map((m, i) => (
        <div key={i} className={m.role === 'user' ? 'text-right' : ''}>{m.content}</div>
      ))}
      {streaming && <ThinkingPanel thinking={thinking} done={false} />}
      <textarea placeholder="Ask about your shop…"
                value={input} onChange={e => setInput(e.target.value)}
                className="border rounded p-2"/>
      <button onClick={ask} disabled={streaming} className="bg-blue-600 text-white rounded px-3 py-2">Ask</button>
    </div>
  );
}
```

- [ ] **Step 5: Run, confirm pass**

- [ ] **Step 6: Commit**

```bash
git add packages/web/src/components/QuinChat.tsx packages/web/src/components/ThinkingPanel.tsx packages/web/src/components/QuinChat.test.tsx
git commit -m "quin-agent: chat panel + visible adaptive thinking"
```

---

### Task 14: Diagnostic-ledger (Cell 1) — entry on every recommendation

> **Note:** This is the **diagnostic ledger** — it records read-only AI advice in TDM (Cell 1). The separate **action ledger** in Cell 3 (Task 29) records propose/approve/execute decisions for physical robot actions. Two ledgers, different purposes, both hash-chained, both eventually exportable into the unified "decision ledger" view by year-2 of the strategy.

**Files:**
- Modify: `[TDM] packages/api/src/services/quin-agent/agent.ts`
- Modify: `[TDM] packages/api/src/db/schema.ts` (add `diagnostic_ledger` table)
- Create: `[TDM] packages/api/src/db/migrations/0059_diagnostic_ledger.sql`
- Test: `[TDM] packages/api/src/services/quin-agent/ledger.test.ts`

- [ ] **Step 1: Migration SQL**

```sql
-- migrations/0059_diagnostic_ledger.sql
CREATE TABLE diagnostic_ledger (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  agent_session_id TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  response_hash TEXT NOT NULL,
  prev_hash TEXT NOT NULL DEFAULT '',
  hash TEXT NOT NULL,
  tools_used JSONB NOT NULL DEFAULT '[]',
  user_id TEXT,
  signature TEXT
);
CREATE INDEX idx_diagnostic_ledger_session ON diagnostic_ledger(agent_session_id, ts);
CREATE INDEX idx_diagnostic_ledger_chain ON diagnostic_ledger(prev_hash);
```

- [ ] **Step 2: Failing hash-chain test**

```typescript
import { describe, it, expect } from 'vitest';
import { writeLedgerEntry } from './ledger';

it('chains hashes across consecutive entries', async () => {
  const a = await writeLedgerEntry({ session_id: 's1', prompt: 'p1', response: 'r1', tools_used: [] });
  const b = await writeLedgerEntry({ session_id: 's1', prompt: 'p2', response: 'r2', tools_used: [] });
  expect(b.prev_hash).toBe(a.hash);
  expect(b.hash).not.toBe(a.hash);
});
```

- [ ] **Step 3: Run, confirm failure.**

- [ ] **Step 4: Implement `writeLedgerEntry`** — fetch the most recent ledger entry's `hash` for this session, compute `sha256(prev_hash + prompt_hash + response_hash + tools_used + ts)` as the new entry's hash, insert.

- [ ] **Step 5: Wire into `runQuinTurn` (Task 12)** — write a ledger entry at the end of every assistant turn that produced a final text response.

- [ ] **Step 6: Run, confirm pass.**

- [ ] **Step 7: Commit**

```bash
git add packages/api/src/db/migrations/0059_diagnostic_ledger.sql \
        packages/api/src/services/quin-agent/ledger.ts \
        packages/api/src/services/quin-agent/ledger.test.ts \
        packages/api/src/db/schema.ts \
        packages/api/src/services/quin-agent/agent.ts
git commit -m "quin-agent: hash-chained diagnostic ledger (Cell 1)"
```

---

### Task 15: Cell 1 polish + first-pass demo loop

- [ ] **Step 1: Wire QuinChat into the existing TDM admin web app** at a new route `/quin`. Hide behind `?demo=1` query flag so it doesn't appear in normal admin navigation.

- [ ] **Step 2: Hand-craft a 3-question demo loop** (the script visitors will see if no one's standing at the booth):
  1. "What did we spend on tooling last month?"
  2. "Why is the Mazak scrapping more than the Haas?"
  3. "Should we switch end-mill brands for stainless work?"

  Record loop runs to verify response quality, latency, citation density. If any answer is wrong or weak, refine the system prompt and re-test.

- [ ] **Step 3: Set up a "demo mode" toggle** that pre-loads these 3 questions as suggestion chips above the chat input.

- [ ] **Step 4: Commit + tag**

```bash
git tag emex-cell-1-v1
git commit -m "quin-agent: cell-1 demo loop polish + demo-mode chips"
```

---

## Workstream W2 — Cell 2: Robot teach-and-replay (Bradley lead)

> All tasks live in repo `linux-usb` unless noted. Mostly Python and hardware integration.

### Task 16: Choose demo task and validate hardware

**Files:**
- Create: `~/linux-usb/citizenry/demos/emex/README.md`
- Create: `~/linux-usb/citizenry/demos/emex/task-spec.md`

- [ ] **Step 1: Final task choice**

Recommended: **kit-component sort** — visitor uses the leader arm to pick 4 mixed components (M3 cap-screw, M3 washer, M3 lock-nut, M3 spring) from a parts bin and place each in the correct slot of a foam tray. Repeats nicely, visibly variable, fits SO-101 reach (≤30cm).

Document the choice in `task-spec.md`: parts list with photos, foam-tray dimensions, success criteria (4/4 in correct slots), failure modes, reset procedure.

- [ ] **Step 2: Hardware shakedown**

Run `~/linux-usb/diagnose_arms.py` end-to-end on both leader (Surface) and follower (Pi). Confirm: 60Hz position read, 60Hz position write, no servo errors over a 5-minute hold. If any fails, fix before continuing.

- [ ] **Step 3: Camera shakedown**

Confirm XIAO at `192.168.1.135` streams MJPEG on `:81/stream` continuously for 10 minutes without dropping. Confirm citizenry mesh sees it as ONLINE.

- [ ] **Step 4: Commit**

```bash
git add citizenry/demos/emex/
git commit -m "citizenry: emex demo task spec + hardware shakedown notes"
```

---

### Task 17: Define EMEX Constitution

**Files:**
- Create: `~/linux-usb/citizenry/governance/emex_constitution.json`
- Test: `~/linux-usb/citizenry/governance/test_emex_constitution.py`

- [ ] **Step 1: Failing test**

```python
def test_emex_constitution_loads_and_validates():
    from citizenry.governance import load_constitution
    c = load_constitution('citizenry/governance/emex_constitution.json')
    assert c.articles, "must have at least one Article"
    assert c.servo_limits.max_torque_pct <= 60, "EMEX safety: torque cap"
    assert c.servo_limits.max_voltage <= 7.4, "EMEX safety: voltage cap"
```

- [ ] **Step 2: Run, confirm failure → implement → run, confirm pass.**

The Constitution should:
- Cap servo torque at 60% of rated (visitors near the arm).
- Allow position envelope to tray + bin region only (no swinging into visitor space).
- Allow Governor CLI to relax torque cap to 75% via signed amendment (this is the demo handle).

- [ ] **Step 3: Commit**

```bash
git commit -m "citizenry: EMEX-specific Constitution with safety caps"
```

---

### Task 18: Build kit-sort teleop fixture

**Files:**
- Physical fixture (foam tray, parts bin, cable management)
- Photos in `~/linux-usb/citizenry/demos/emex/fixture/`

- [ ] **Step 1: Cut/source foam tray** — 200×100×20mm with 4 cylindrical pockets (10mm dia × 8mm deep). Hand-cut acceptable; aesthetic matters for video.

- [ ] **Step 2: Source kit components** — bag of 50× M3 cap-screws, 50× M3 washers, 50× M3 lock-nuts, 50× M3 springs. Roughly NZ$30 from local fastener supplier.

- [ ] **Step 3: Bench-mount the leader and follower arms** at exhibitor-friendly visitor reach height (~95cm above stand floor).

- [ ] **Step 4: Photograph and document the fixture** so it can be rebuilt at the venue if anything is damaged in transit.

- [ ] **Step 5: Commit photos**

```bash
git add citizenry/demos/emex/fixture/
git commit -m "citizenry: emex stand fixture — foam tray + kit components"
```

---

### Task 19: Implement teleop episode recording for EMEX task

**Files:**
- Create: `~/linux-usb/citizenry/demos/emex/record_episode.py`
- Test: `~/linux-usb/citizenry/demos/emex/test_record_episode.py`

- [ ] **Step 1: Failing test**

```python
def test_record_episode_writes_v3_dataset(tmp_path):
    from citizenry.demos.emex.record_episode import record
    out = record(duration_s=2, output_dir=tmp_path)
    assert (out / 'episode_0.parquet').exists()
    assert (out / 'video.mp4').exists()
```

- [ ] **Step 2: Run, confirm failure.**

- [ ] **Step 3: Implement** — uses existing `LeRobotDataset` v3 writer; reads leader positions at 60Hz, follower positions at 60Hz, XIAO frames at 30Hz; writes single Parquet + MP4.

- [ ] **Step 4: Run, confirm pass.**

- [ ] **Step 5: Bench-test with full kit-sort run** (manually teleop one full sort, ~45s).

- [ ] **Step 6: Commit**

```bash
git commit -m "citizenry: emex episode recording (LeRobot v3, 60Hz)"
```

---

### Task 20: Implement replay loop with Claude narration

**Files:**
- Create: `~/linux-usb/citizenry/demos/emex/replay_with_narration.py`

- [ ] **Step 1: Replay function** — reads the most recent episode, plays follower positions back at 60Hz. Standard LeRobot replay; ensure servo limits enforced via Constitution.

- [ ] **Step 2: Narration hook** — at episode start, send the episode's Parquet metadata + a thumbnail to Claude with system prompt "Describe what this robot just learned, in 1–2 sentences, for a trade-show audience". Stream the response to the side display.

- [ ] **Step 3: Bench-test narration latency** — must complete within 5s of replay start so it's audible alongside the motion.

- [ ] **Step 4: Commit**

```bash
git commit -m "citizenry: replay with Claude narration overlay"
```

---

### Task 21: Build governor-CLI tablet UI

**Files:**
- Create: `~/linux-usb/citizenry/cli/governor_emex_tablet.py`
- Create: `~/linux-usb/citizenry/cli/governor_emex_web.html` (single-page tablet UI)

- [ ] **Step 1: Web UI with 3 buttons**: "Allow torque 75%", "Restrict torque 50%", "Pause arms". Each button POSTs a signed Constitution amendment to the local citizenry daemon.

- [ ] **Step 2: Show current Constitution state** at the top — current torque cap, current allowed region, last-amend timestamp.

- [ ] **Step 3: Wire to multicast** so visitors see the LED on the follower arm change colour within ~1s of tapping.

- [ ] **Step 4: Run on iPad in stand kiosk mode** (Safari, full-screen, lock-to-app via Guided Access).

- [ ] **Step 5: Commit**

```bash
git commit -m "citizenry: tablet governor CLI for live Constitution edits"
```

---

### Task 22: XIAO camera live preview in stand frame

**Files:**
- Modify: `~/linux-usb/citizenry/demos/emex/stand_display.py`

- [ ] **Step 1: Stand display layout** — full-screen on a 27" monitor: top half = live XIAO MJPEG, bottom half = current Constitution + last 5 episode events (record/replay/amendment).

- [ ] **Step 2: Confirm <100ms camera-to-screen latency.** If higher, drop XIAO resolution to 640×480 or move display to wired HDMI.

- [ ] **Step 3: Commit**

```bash
git commit -m "citizenry: emex stand display — live cam + cita state"
```

---

### Task 23: Backup spare hardware kit

- [ ] **Step 1: Box the spares.** Minimum: 1 spare SO-101 arm (configurable as either leader or follower via Constitution), 1 spare Pi 5 (citizenry image flashed), 1 spare XIAO ESP32S3 (provisioned + WiFi configured), Surface charger, USB-C cables ×3, microSD ×2 (citizenry image), foam tray spare, kit-component spare bag. Ideal: 1 leader-config + 1 follower-config arm if budget allows (~NZ$1,500 each).

- [ ] **Step 2: Document hot-swap procedure** in `docs/emex/hot-swap-procedure.md`. Target: <10 minutes from "primary fails" to "demo running on spares".

- [ ] **Step 3: Commit**

```bash
git add docs/emex/hot-swap-procedure.md
git commit -m "emex: hot-swap procedure for stand hardware failures"
```

---

### Task 24: Rehearse hot-swap recovery

- [ ] **Step 1: Cold rehearsal** — sit at the bench, declare "Pi has died", run the hot-swap procedure with the timer running. Target ≤10 minutes. Repeat until ≤8 minutes 3 times in a row.

- [ ] **Step 2: Document any procedure improvements** discovered during rehearsal back into `hot-swap-procedure.md`.

- [ ] **Step 3: Commit improvements** if any.

---

## Workstream W3 — Cell 3: MCP bridge (Bradley + Philippe)

### Task 25: Implement TDM-MCP server

**Files:**
- Create: `[TDM] packages/api/src/mcp/tdm-mcp-server.ts`
- Create: `[TDM] packages/api/src/mcp/tdm-mcp-server.test.ts`
- Modify: `[TDM] packages/api/package.json` (add `@modelcontextprotocol/sdk` dep)

- [ ] **Step 1: Install MCP SDK**

```bash
cd ~/path/to/pcrottet-tool-data-management
pnpm --filter @tdm/api add @modelcontextprotocol/sdk
```

- [ ] **Step 2: Failing test**

```typescript
it('exposes the 6 quin tools as MCP tools', async () => {
  const server = createTdmMcpServer();
  const tools = await server.listTools();
  expect(tools.tools.map(t => t.name).sort()).toEqual([
    'get_consumption_stats', 'get_vendor_spend', 'search_products',
    'search_purchase_orders', 'search_stock', 'search_transactions',
  ]);
});
```

- [ ] **Step 3: Implement server using MCP SDK + reusing the 6 handlers from Task 6–11.**

- [ ] **Step 4: Run, confirm pass.**

- [ ] **Step 5: Commit**

```bash
git commit -m "mcp: tdm-mcp server wrapping 6 quin tools"
```

---

### Task 26: Implement Citizen-MCP server

**Files:**
- Create: `~/linux-usb/citizenry/mcp/citizen_mcp_server.py`
- Test: `~/linux-usb/citizenry/mcp/test_citizen_mcp_server.py`

- [ ] **Step 1: Install MCP Python SDK**

```bash
cd ~/linux-usb && source ~/lerobot-env/bin/activate
pip install mcp
```

- [ ] **Step 2: Failing test**

```python
def test_citizen_mcp_exposes_three_actions():
    from citizenry.mcp.citizen_mcp_server import build_server
    s = build_server()
    names = sorted(t.name for t in s.list_tools())
    assert names == ['get_status', 'govern_update', 'propose_task']
```

- [ ] **Step 3: Implement** — `get_status` returns presence + emotional state of all known citizens; `propose_task` injects a PROPOSE message into the local mesh; `govern_update` injects a GOVERN amendment.

- [ ] **Step 4: Run, confirm pass.**

- [ ] **Step 5: Commit**

```bash
git commit -m "mcp: citizen-mcp server with 3 mesh actions"
```

---

### Task 27: Build Managed Agents orchestrator

**Files:**
- Create: `~/linux-usb/citizenry/mcp/bridge_orchestrator.py`

- [ ] **Step 1: Define the orchestrator** — uses Anthropic SDK with both MCP servers attached via the MCP Connector. System prompt scoped to: "You bridge the shop data layer (TDM) with the physical execution layer (Citizenry). Always: (1) gather evidence via TDM tools, (2) propose action via Citizen tools, (3) require human approval before any write action."

- [ ] **Step 2: Demo-loop script** — a hand-crafted 4-step interaction: scrap question → TDM lookup → backup-tool propose → approval gate → citizen executes. Capture all 4 steps as ledger entries.

- [ ] **Step 3: End-to-end timing test** — full loop including human tap ≤5s. If slower, profile and cut tools.

- [ ] **Step 4: Commit**

```bash
git commit -m "mcp: bridge orchestrator + emex demo loop script"
```

---

### Task 28: Build 4-tier approval tablet UI

**Files:**
- Create: `~/linux-usb/citizenry/mcp/approval_ui/index.html`
- Create: `~/linux-usb/citizenry/mcp/approval_ui/server.py`

- [ ] **Step 1: Single-page tablet UI** — shows the proposed action ("Stage backup tool: WC-12345 to Mazak pot 3"), the evidence chain (4 ledger entries with hashes), and one big green APPROVE button + small grey REJECT button.

- [ ] **Step 2: Tap = HTTP POST** to the orchestrator's `/approve` endpoint. Orchestrator releases the queued PROPOSE into the mesh.

- [ ] **Step 3: Latency test** — tap-to-arm-motion ≤2s.

- [ ] **Step 4: Run on iPad** in kiosk mode.

- [ ] **Step 5: Commit**

```bash
git commit -m "mcp: 4-tier approval tablet UI"
```

---

### Task 29: Wire decision-ledger writer with hash chain

**Files:**
- Create: `~/linux-usb/citizenry/mcp/ledger.py`
- Test: `~/linux-usb/citizenry/mcp/test_ledger.py`

- [ ] **Step 1: Failing test** for hash-chained sequence (similar to Task 14).

- [ ] **Step 2: Implement** — local SQLite + Ed25519 signature on each entry using the GovernorCitizen's key.

- [ ] **Step 3: Run, confirm pass.**

- [ ] **Step 4: Wire orchestrator (Task 27) to write ledger entries on every TDM read, every PROPOSE, every approval gate decision.**

- [ ] **Step 5: Commit**

```bash
git commit -m "mcp: signed hash-chain decision ledger for bridge"
```

---

### Task 30: End-to-end loop test (≤5s)

- [ ] **Step 1: Wire all three cells together on the bench** — Cell 1 demo VM, Cell 2 arms, Cell 3 orchestrator all running.

- [ ] **Step 2: Run the full demo loop 10 times back-to-back.** Record latency at each stage. Target: TDM query ≤1s, Claude reasoning ≤1.5s, propose ≤0.5s, approval tap-response ≤2s, total ≤5s.

- [ ] **Step 3: If any stage exceeds budget, profile and either (a) cut tools, (b) reduce thinking budget, or (c) pre-warm caches.**

- [ ] **Step 4: Document final latencies in `docs/emex/loop-budget.md`.**

- [ ] **Step 5: Commit**

```bash
git commit -m "emex: end-to-end loop hits ≤5s budget"
```

---

### Task 31: Full triptych dry-run

- [ ] **Step 1: Run all three cells simultaneously for 30 minutes**, doing the demo loop in random orders. Note any cross-cell interference (network contention, shared resource locks, etc.).

- [ ] **Step 2: Fix anything that breaks under simultaneous load.**

- [ ] **Step 3: Tag**

```bash
git tag emex-triptych-v1
git commit -m "emex: full triptych dry-run, all three cells simultaneous"
```

---

## Workstream W4 — Physical stand + marketing (parallel, 14 days)

### Task 32: Confirm stand booking and dimensions

- [ ] **Step 1: Pull EMEX stand contract** — confirm 3×3m, 3 walls, power supply (typically 32A single-phase NZ), network drop (Ethernet + WiFi guest), expected delivery date for stand build.

- [ ] **Step 2: Document in `docs/emex/stand-spec.md`.**

---

### Task 33: Stand design brief to contractor

- [ ] **Step 1: Brief one local NZ stand fitter** (e.g. ExpoNet, Peek Display, Display Solutions) on the 3-cell triptych: 3 walls, 3 monitors flush-mounted, 3 worksurfaces (cells), bench-mount points for arms in cells 1+2, cable channels.

- [ ] **Step 2: Get quote, lead-time, install date.** Decision deadline: 2026-05-04 to allow 3 weeks build.

---

### Task 34: 60-second loop video brief and production

- [ ] **Step 1: Write a 60s shooting script** — 0-15s "live shop data" (Cell 1 mock footage), 15-35s "robot teach-and-replay" (Cell 2 footage), 35-55s "Claude orchestrating with audit trail" (Cell 3 footage), 55-60s logo + URL.

- [ ] **Step 2: Capture footage** at the bench during W2/W3 testing.

- [ ] **Step 3: Edit** (Bradley or contract videographer; aim NZ$1–2k).

- [ ] **Step 4: Loop on a small monitor visible from the aisle.**

---

### Task 35: 1-page leave-behind print

- [ ] **Step 1: Brief** — A4 double-sided, glossy. Front: triptych imagery + headline + 3 bullets ("auditable AI for manufacturing"). Back: founding-five offer + URL + Bradley/Philippe headshots + emails.

- [ ] **Step 2: Design** (Bradley or Canva).

- [ ] **Step 3: Print 200 copies** at a local print shop. Target NZ$200–300.

---

### Task 36: Quintinity website refresh — ShopOS landing page

- [ ] **Step 1: Add `/shopos` route to quintinity.co.nz** with the same triptych narrative + an EMEX teaser banner.

- [ ] **Step 2: Add `/founding-five` page** describing the partnership offer, with 5 visible "founding partner slots" (counter starts at 0/5).

- [ ] **Step 3: Test on mobile** (most stand visitors will scan a QR code from the leave-behind).

---

### Task 37: Founding-five microsite + 5-slot scarcity counter

- [ ] **Step 1: Counter mechanic** — admin updates the counter when each of the 5 partnerships signs. "0/5 reserved" → "1/5 reserved" → … "5/5 — closed for 12 months".

- [ ] **Step 2: Wait-list form** for visitors who want in after 5/5.

---

### Task 38: Lead-capture iPad form (already done in T3)

Verify Task 3 deliverable still works; one iPad on the visitor side of each cell + one at the front of the stand.

---

### Task 39: Stand AV/power/network setup checklist

- [ ] **Step 1: Master checklist** in `docs/emex/setup-checklist.md` — every cable, every adapter, every device, every credential, every URL bookmarked. Goal: full stand ready in ≤2 hours on setup day.

- [ ] **Step 2: Pre-flight test** at the home base 1 week before show — full stand assembled in the garage.

---

### Task 40: Spare hardware/cables/peripherals checklist

- [ ] **Step 1: List** — every item to bring as backup. SO-101 spares (T23), HDMI cables ×3, USB-C cables ×5, ethernet cable ×3, power strips ×2, USB hub, microSD ×2, gaff tape, multimeter, screwdriver kit, cable ties.

---

## Workstream W5 — Rehearsal + comms + scripts (last 5 days)

### Task 41: Author 4-question lead-qualifying script

**Files:**
- Create: `~/linux-usb/docs/emex/lead-qualifying-script.md`

- [ ] **Step 1: Script** —
  1. "What kind of work runs on your floor?" (qualifies segment B/A/C/D)
  2. "How many machines? How variable is the work?" (sizes deal)
  3. "What's stopping you from automating it today?" (find the wedge)
  4. "We're picking 5 NZ manufacturers as founding AI partners this year. Want to be on the shortlist?"

- [ ] **Step 2: Memorise. Practice with one non-customer (friend, family, random shopkeeper) before show.**

---

### Task 42: Document 4 backup plans

- [ ] **Step 1: Each in 1 page in `docs/emex/backup-plans.md`** —
  - Backup A — arm jam: clear, run hot-swap procedure if recurring (T23).
  - Backup B — MCP timeout: skip Cell 3 demo to "video loop only" mode.
  - Backup C — Claude API down: fall back to pre-recorded demo video; tell visitors honestly "Anthropic is having a moment, here's what it does when it's up".
  - Backup D — Constitution rejection: use as a teaching moment ("watch — the Constitution just stopped me. That's the whole point.").

---

### Task 43: 1-page partnership outline

- [ ] **Step 1: Print-ready leave-behind v2** — for visitors who get past the qualifying script. NZ$200k year-1, 12-month engagement, ShopOS deploy + 1-2 AI initiatives + on-call advisory + monthly steering. 5 slots only.

- [ ] **Step 2: Print 50 copies** of this premium version.

---

### Task 44: Pre-show LinkedIn schedule (3 posts)

- [ ] **Step 1: Post 1 (T-14 days)** — "We're at EMEX 2026 stand X42. Come see Quintinity ShopOS — auditable AI for manufacturing, live."
- [ ] **Step 2: Post 2 (T-7 days)** — Triptych-teaser video clip (15s).
- [ ] **Step 3: Post 3 (T-1 day)** — "Tomorrow. Stand X42. Bring your toughest shop-floor question."

Schedule via LinkedIn's native scheduler.

---

### Task 45: Press list outreach

- [ ] **Step 1: Email NZ Manufacturer magazine, Idealog, NBR, RNZ Business** with a 2-paragraph pitch + media-kit URL. Target: 1+ pre-show mention.

---

### Task 46: Full triptych dry-run end-to-end

- [ ] **Step 1: Three full dry-runs** of every visitor scenario: walk-by, qualified-lead conversation, hot-swap-during-demo, Claude-API-down. 90 minutes per scenario, three each = ~9 hours total.

---

### Task 47: Accord case-study sign-off check-in

- [ ] **Step 1: Email Accord exec sponsor 2026-05-08** — "EMEX is in 18 days. Confirm we have your sign-off to use anonymised data + name 'Accord' as our reference customer in the demo? Final go/no-go date 2026-05-15."

- [ ] **Step 2: If go**, update Cell 1 demo to use real Accord name. If no-go, ship anonymised version.

---

### Task 48: Pack-out checklist + transport

- [ ] **Step 1: Checklist** — what goes in the van, in what order, with what padding. Auckland ↔ Wellington (or wherever you're based) drive distance.

- [ ] **Step 2: Insurance** — NZ$5k+ of equipment in the van. Confirm transit insurance covers it.

---

### Task 49: Day-1 setup rehearsal

- [ ] **Step 1: 2026-05-25 (the day before show)** — full setup at the venue. Do NOT skip this; venue surprises are common (different power outlet shapes, no WiFi, restricted access hours).

---

### Task 50: Post-show 24h auto-respond email template

- [ ] **Step 1: Mailgun/SendGrid template** — "Thanks for stopping by Quintinity at EMEX. We'll be in touch within 5 working days. Meanwhile: founding-five microsite [URL]. Best, Bradley & Philippe."

- [ ] **Step 2: Test** by submitting Tally form during W3.

---

## Workstream W6 — At-show + post

### Task 51: Setup day (2026-05-25)

- [ ] All hardware installed by 14:00.
- [ ] All three cells running by 16:00.
- [ ] Full triptych dry-run on the actual stand by 17:00.
- [ ] Sleep early.

---

### Task 52: Show day 1 (2026-05-26, 9:00–17:00)

- [ ] **Open stand 9:00.** Two people on stand at all times: one engaging visitors, one running demo + iPad capture.
- [ ] **Lunch rotation 12:00–13:00.**
- [ ] **End-of-day debrief 17:30** — count leads, note demo failures, fix overnight if possible.

---

### Task 53: Show day 2 (2026-05-27, 9:00–17:00)

Same pattern as day 1. Apply day-1 lessons. Push for higher conversation conversion (target 20+ qualified conversations on the day).

---

### Task 54: Show day 3 (2026-05-28, 9:00–16:00)

Final day. Push qualifying script harder ("seats are filling fast"). Plan for tear-down 16:00–18:00.

---

### Task 55: Tear-down + lead triage

- [ ] **Step 1: Pack-down** by 18:00. Hardware back in van, drive home.
- [ ] **Step 2: Same evening: triage all Tally form submissions.** Tag each: HOT (qualifying-script answered well), WARM (interested but unclear), COLD (just scanning).

---

### Task 56: 24h post-show — assign owners

- [ ] **Step 1: 2026-05-29 morning** — every HOT lead gets an owner (Bradley or Philippe) and a target call date in the next 5 days.

---

### Task 57: Day-2 post-show — personalised follow-ups

- [ ] **Step 1: Send a personalised email to every HOT lead** within 48h. Reference something specific they said at the stand. Propose 2 calendar slots.

---

### Task 58: Week 1 post-show — book first 10 diagnostic calls

- [ ] **Step 1: By 2026-06-04**, have 10+ free 1-hour diagnostic calls booked.

- [ ] **Step 2: Review funnel maths.** If <10 booked, the qualifying script needs revision before the next phase begins. If ≥10, proceed to writing `2026-05-29-post-emex-pipeline.md` plan.

---

## Sprint exit criteria

The Phase 0 sprint is complete when ALL of the following are true:

- [ ] Triptych demo runs end-to-end on the stand for 3 days without irrecoverable failure.
- [ ] 50+ qualified conversations recorded.
- [ ] 30+ booked diagnostic calls in the post-show calendar.
- [ ] 100+ email captures.
- [ ] 0 hardware-loss incidents.
- [ ] 0 security incidents (no API key leaked, no customer data leaked).
- [ ] Decision ledger contains entries for every demo loop visitors triggered (auditability dogfooded).

If criteria miss by ≥30%, run a 1-day retro and write a "what we learned" doc into `docs/emex/post-mortem-2026.md` before starting the post-EMEX pipeline plan.

---

*End of Phase 0 plan. Companion strategy: `~/linux-usb/docs/superpowers/specs/2026-04-27-quintinity-strategy-design.md`.*
