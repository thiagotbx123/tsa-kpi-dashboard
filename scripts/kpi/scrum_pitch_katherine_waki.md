# Scrum of Scrums → Milestone Health Digest

_A proposal to remove duplicate reporting while improving stakeholder visibility._

**Author:** Thiago Rodrigues  ·  **Audience:** Katherine Lu, Waki  ·  **Date:** 2026-04-17

---

## The problem (data-driven)

Based on analysis of **1,073 messages** posted to `#scrum-of-scrums` over the last 90 days:

| Metric | Current state |
|---|---|
| Posts per TSA per week | ~5 (daily) |
| Avg post length | 20–60 lines |
| Avg time per TSA to write | 10–15 min/day |
| Weekly team hours spent re-typing Linear content | **~5 hours** |
| Milestones with an "Impact" / "Why it matters" statement | **0 out of 28** |
| Stakeholder questions of the type *"what's the current ETA?"* | ~4 per week (measured via Slack search) |

**Root cause:** The daily post is a **task-level re-render of Linear**. It was built for a time when visibility was low. Linear is now our source of truth, but the report never evolved.

---

## What we agreed in our last sync

> 1. Linear = source of truth. Secondary reports should reference, not duplicate.
> 2. Report at the **milestone** level (on track / at risk), not task level.
> 3. Emphasize the **"why"** — impact on the customer / project.
> 4. Keep the same narrative across stakeholders.

## What I'm proposing

Replace the current daily agenda with an **automated Milestone Health Digest** posted 2× a week (Tue + Fri) to `#scrum-of-scrums`, plus an ad-hoc 🔴 alert when anything flips to "at risk".

### Sample (real data, generated today from Linear)

```
📊 Scrum of Scrums — Milestone Health Digest
2026-04-17 · source of truth: Linear

Team rollup: 🔴 2 at risk · 🟡 3 watch · 🟢 18 on track · ✅ 5 shipped (14d)

👤 Carlos  ·  🔴 1  🟢 1  ✅ 2
🔴 Gong  (At Risk)
   12 open / 88 total  ·  2 overdue  ·  next due 2026-03-20
   Why it matters: Gong customer retention — blocks sandbox self-service for sales team.
   Signal: 2 overdue (-28d worst)
   └─ RAC-352 [In Progress] Gong - Deals & Forecast — due 2026-03-20
   └─ RAC-744 [In Progress] Gong - Financial Story First Ingestion — due 2026-04-16

👤 Diego  ·  🔴 1  🟡 1  🟢 6  ✅ 2
🔴 [TSA] Diego Internal  (At Risk)
   5 open / 6 total  ·  1 overdue
   Signal: 1 overdue (-7d worst)
   └─ RAC-715 [Todo] Brevo — due 2026-04-10
```

One card per milestone. No re-typing of task lists. Click-through to Linear for details.

### Why this addresses each of our agreements

| Your principle | How the digest delivers |
|---|---|
| Linear = source of truth | Every card links to Linear; numbers come from the API, not from memory |
| Milestone-level status | One card = one milestone (or project when no milestone is set) |
| "Why it matters" | Every card carries a one-sentence impact statement (currently derived from a curated map; in shadow mode we'll read it from each Linear project's `description` under an `Impact:` line) |
| Same narrative across stakeholders | The same MD/Slack/HTML output can be shared with you, Waki, CS, or execs — no rewrites |
| Avoid duplicated work | TSAs no longer re-type anything. They only keep Linear clean (which they already do) |

---

## How it works

```
Linear GraphQL API  ──▶  milestone_health_engine.py  ──▶  scrum_digest_builder.py  ──▶  Slack post
                         (classify red/yellow/green)      (MD + Slack + HTML)
```

Both scripts are **already written** and live in `TSA_CORTEX/scripts/kpi/`:

- `milestone_health_engine.py` — reads the existing KPI cache, groups by `(TSA, project, milestone)`, applies clear health rules
- `scrum_digest_builder.py` — renders 3 artifacts: Markdown report, Slack-ready post, HTML preview

### Health classification rules (deterministic, auditable)

| Status | Rule |
|---|---|
| 🔴 **At Risk** | Has overdue issue OR any issue in `Blocked` / `Blocked Internal` |
| 🟡 **Watch** | `Blocked by Customer` / `Paused` issues present, OR earliest due ≤3d and >30% open |
| 🟢 **On Track** | Otherwise |
| ✅ **Shipped** | 0 open + ≥1 closed in last 14d |

### A real finding the current report misses today

Running the engine against today's Linear data surfaces **3 overdue items in 2 TSAs** that are not flagged in the current scrum posts because they're buried in task-level walls of text:

- Carlos — `RAC-352 Gong - Deals & Forecast` — **28 days overdue**
- Carlos — `RAC-744 Gong - Financial Story First Ingestion` — 1 day overdue
- Diego — `RAC-715 Brevo` — 7 days overdue

This is exactly the kind of signal the digest format promotes to the top.

---

## Rollout plan (3 sprints)

| Sprint | What runs | Stakeholder check |
|---|---|---|
| **S1** (weeks 1–2) | Digest posts in **shadow mode** (alongside the current daily agenda). No behavior change for the team. | Katherine + Waki review digest quality |
| **S2** (weeks 3–4) | Digest becomes the primary; daily agenda becomes optional (only for 🔴 items) | Gayathri / Josh confirm visibility is equal or better |
| **S3** (week 5+) | Daily agenda is discontinued. Gayathri gets a permanent Linear dashboard link alongside the digest. | Retrospective with the TSA team |

## Success metrics (already instrumented)

| KPI | Baseline | Target |
|---|---|---|
| Weekly lines posted in `#scrum-of-scrums` | ~750 | **≤150** |
| Minutes/TSA/week on scrum reporting | ~60 | **≤15** |
| % of active milestones with "Impact" statement | 0% | **100%** |
| Stakeholder "what's the current ETA?" pings | ~4/week | **≤1/week** |
| % of overdue items flagged within 24h | Unknown | **100%** |

---

## What I need from you

1. **Katherine** — confirm the format matches the narrative you want to see (one-sentence impact + link to Linear)
2. **Waki** — decide the right cadence (I'm proposing Tue + Fri 09:00 BRT)
3. **Both** — green-light shadow mode for 2 weeks so we validate on live data before retiring the current format

If approved, I can have shadow mode live this week. The full shadow phase costs us nothing (both formats run in parallel), and at the end we'll have 2 weeks of side-by-side data to decide.

---

### Appendix — files produced today for your review

- `scrum_digest.md` — Markdown version (readable in any editor or GitHub)
- `scrum_digest_slack.txt` — copy-paste-ready into `#scrum-of-scrums`
- `scrum_digest_preview.html` — self-contained HTML with color coding
- `_milestone_health.json` — raw data behind the digest (audit trail)

All four were generated from **live Linear data at 2026-04-17 09:19 BRT**.
