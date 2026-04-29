---
task_id: T42
purpose: Four rehearsed backup plans for at-show failure modes during the EMEX 2026 triptych demo.
format: 1 page per failure mode (4 modes total), each <=200 words. Print double-sided A4, fold in stand desk drawer.
placeholders:
  - "{{POST-SHOW NOTE: A — what we changed about the hot-swap procedure after the show}}"
  - "{{POST-SHOW NOTE: B — MCP timeout root cause and fix}}"
  - "{{POST-SHOW NOTE: C — Claude API outage handling lessons}}"
  - "{{POST-SHOW NOTE: D — Constitution rejection — visitor responses captured}}"
last_updated: 2026-04-29
---

# Backup plans for at-show failures

Print A4 double-sided, one mode per page. Keep folded in the front-of-stand drawer. The person on demo runs the response; the person on iPad keeps engaging the visitor.

---

## A. Arm jam (Cell 2)

**Trigger.** Follower SO-101 stalls mid-trajectory. Servo goes silent or LED turns red. Visible mechanical bind, audible servo whine, or the arm freezes mid-motion for >2 seconds.

**Rehearsed response.** Say to the visitor: *"The Constitution just caught a torque limit — give me 30 seconds to clear it."* Power-cycle the follower from the stand-side switch. If it comes back, re-home and resume. If it doesn't come back inside 60 seconds, run the hot-swap procedure (see T23 — *procedure doc to be authored, reference forward*) and switch to the spare follower under the bench. Keep narrating: *"This is exactly why we hot-swap — the audit trail follows the citizen, not the hardware."*

**Recovery time target.** 30 seconds for power-cycle recovery. 8 minutes for full hot-swap.

**Escalation.** If the spare also fails or hot-swap exceeds 10 minutes, switch the cell to the 60-second video loop and pivot visitor conversation to Cells 1 and 3.

**Lessons captured.** {{POST-SHOW NOTE: A — what we changed about the hot-swap procedure after the show}}

---

## B. MCP timeout (Cell 3)

**Trigger.** Cell 3 bridge orchestrator hangs for more than 5 seconds on any of: TDM tool call, citizen tool call, or approval-gate tap. The end-to-end loop budget is 5 seconds — anything longer breaks the demo's credibility.

**Rehearsed response.** Say to the visitor: *"The bridge is taking too long — let me show you the loop on video while we reset."* Hit the demo-cancel hotkey on the laptop, switch the Cell 3 monitor to the 60-second video loop, and keep the visitor's attention on Cell 1 or Cell 2. Don't try to debug live. After the visitor moves on, restart the orchestrator from the bench laptop; check the next visitor before resuming live demo.

**Recovery time target.** 10 seconds to switch to video loop. 2 minutes to restart orchestrator and re-validate.

**Escalation.** If the orchestrator times out three times in one hour, leave Cell 3 on the video loop for the rest of that session. Resume next session after a clean restart and a bench dry-run.

**Lessons captured.** {{POST-SHOW NOTE: B — MCP timeout root cause and fix}}

---

## C. Claude API down

**Trigger.** Anthropic API returns 5xx, hangs, or rate-limits across multiple cells simultaneously. Cells 1 and 3 will both fail; Cell 2 (replay-only) keeps working. Check status.anthropic.com on the bench tablet to confirm.

**Rehearsed response.** Be honest. Say to the visitor: *"Anthropic is having a moment — here's what it does when it's up."* Switch Cells 1 and 3 to their pre-recorded demo videos. Don't pretend it's working. Honesty here is on-brand: every decision traced, including the one where the upstream provider went down. Keep Cell 2 live and lead with it. Continue qualifying conversations as normal.

**Recovery time target.** 30 seconds to switch both cells to video. Resume live demos within 2 minutes of API recovery.

**Escalation.** If the outage exceeds 60 minutes, send the on-stand person to grab lunch — there's no point burning energy waiting. Recheck status every 15 minutes from the bench.

**Lessons captured.** {{POST-SHOW NOTE: C — Claude API outage handling lessons}}

---

## D. Constitution rejection mid-demo

**Trigger.** Cell 2 or Cell 3 governor refuses a proposed action — the citizen broadcasts a REJECT in response to a PROPOSE, the arm doesn't move, the LED goes amber. Most likely cause: a torque cap or geometry constraint the demo trajectory just nudged.

**Rehearsed response.** This is a feature, not a failure. Say to the visitor: *"Watch — the Constitution just stopped me. That's the whole point. Let me show you why."* Open the governor CLI on the side tablet, point at the rule that fired, walk the visitor through the signed amendment that put it there. Then either (a) tap the safe-mode amendment to relax the cap and re-run, or (b) leave the rule in place and pick up the demo on the next pass. Either is on-message.

**Recovery time target.** Zero — the rejection is part of the demo. Don't apologise for it.

**Escalation.** If the same rule fires repeatedly inside one demo loop, switch Cell 2 to a known-safe pre-rehearsed trajectory for the rest of that session. Tighten the test trajectory overnight.

**Lessons captured.** {{POST-SHOW NOTE: D — Constitution rejection — visitor responses captured}}
