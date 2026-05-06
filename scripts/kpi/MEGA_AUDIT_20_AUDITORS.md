# MEGA AUDIT: 20-Auditor KPI Dashboard Review
**Date:** 2026-03-22 | **Pipeline:** refresh → merge → normalize → build_html
**Dataset:** 498 records, 7 TSA members, Dec 2025 – Mar 2026
**Status:** REPORT ONLY — NO CHANGES APPLIED

---

## Executive Summary

20 auditors (10 technical + 10 perspective-based) examined the entire KPI pipeline and dashboard end-to-end. The audit uncovered **4 CRITICAL**, **18 HIGH**, **15 MEDIUM**, and **8 LOW** findings across code, data, UX, process, and narrative integrity.

### The 3 Most Dangerous Findings

1. **KPI3 (Reliability) is a phantom metric.** Zero rework labels exist across 498 records. "100% ON TARGET" is displayed to stakeholders when the measurement instrument doesn't exist. (Auditors #9, A, B, C, F, H, I)

2. **91% of "On Time" tasks are trivially correct** — ETA was set equal to delivery date (likely filled in retroactively). The headline "83% accuracy" measures logging discipline, not estimation quality. Linear-sourced members (Thais, Yasmim) are penalized for having honest, non-gameable data. (Auditors A, C, D, F, I)

3. **`isCoreWeek` expires in 9 days** (hardcoded to Dec 2025 – Mar 2026 in 12+ files). After March 31, the dashboard freezes silently — no new data appears, no error is shown. (Auditors #3, #9, H, J)

---

## WAVE 1: Technical Auditors (#1–#10)

### Auditor #1 — Data Integrity Specialist

| # | Sev | Finding | File:Line |
|---|-----|---------|-----------|
| 1.1 | CRITICAL | Partial pagination saved as complete — if API fails on page 2+, partial data overwrites full cache | `refresh_linear_cache.py:100-107,186` |
| 1.2 | CRITICAL | Non-atomic writes — `open(path,'w')` truncates to 0 bytes before writing; crash = total data loss | `merge_opossum.py:247`, `normalize.py:205` |
| 1.3 | HIGH | Delete-and-rebuild with no count validation — merge destroys THAIS/YASMIM records unconditionally, even if replacement set is smaller | `merge_opossum.py:30` |
| 1.4 | HIGH | No concurrency protection — two scripts running on same JSON = silent data corruption | All 4 scripts |
| 1.5 | HIGH | `_raccoons_thais.json` guard checks `raccoons_issues` count (full team) instead of `raccoons_thais` count (filtered) | `refresh_linear_cache.py:204` |
| 1.6 | MEDIUM | `</script>` injection via raw JSON in HTML template — `__DATA__` placeholder replaced via string substitution | `build_html_dashboard.py:1010` |
| 1.7 | MEDIUM | `except: pass` swallows all errors silently including KeyboardInterrupt | `normalize_data.py:178` |
| 1.8 | MEDIUM | Year-inference for short dates depends on when script runs, not on data context | `normalize_data.py:66-68,159-160` |
| 1.9 | MEDIUM | Canceled tasks with `perf=Overdue` from spreadsheet (9 records) — normalize doesn't recalculate | data |
| 1.10 | LOW | Description truncated at 500 chars with no indicator | `refresh_linear_cache.py:124` |
| 1.11 | LOW | Raw JSON string read (no validation) — malformed JSON produces broken HTML silently | `build_html_dashboard.py:10-11` |

### Auditor #2 — KPI Formula Validator (from previous session)

| # | Sev | Finding |
|---|-----|---------|
| 2.1 | HIGH | Member card accuracy = `onTime/(onTime+late+overdue)` but KPI1 = `onTime/(onTime+late)` — two different numbers for the same person | `build_html_dashboard.py:697 vs :343` |
| 2.2 | MEDIUM | 9 Canceled tasks show `perf=Overdue` from spreadsheet data — inflates "overdue" counts on member cards |

### Auditor #3 — Date/Time Logic (from previous session)

| # | Sev | Finding |
|---|-----|---------|
| 3.1 | HIGH | Year inference bug for future ETAs — short dates like "15-Mar" get wrong year depending on run month | `normalize_data.py:66-68` |
| 3.2 | HIGH | `isCoreWeek` hardcoded to Dec 2025 – Mar 2026, expires in 9 days | `build_html_dashboard.py:293` |

### Auditor #4 — API & Security (from previous session)

| # | Sev | Finding |
|---|-----|---------|
| 4.1 | HIGH | Partial data guard only checks `len == 0` — fails if API returns partial pages | `refresh_linear_cache.py:186` |
| 4.2 | HIGH | Authorization header uses raw key (no `Bearer` prefix) — may fail with strict proxies | `refresh_linear_cache.py:36` |
| 4.3 | HIGH | Pagination failure saves incomplete data as if complete | `refresh_linear_cache.py:154-156` |

### Auditor #5 — Classification & Categorization

| # | Sev | Finding |
|---|-----|---------|
| 5.1 | HIGH | OPO-97 Spike record: `customer=""`, `category="External"`, `demandType="Internal"` — triple inconsistency | data |
| 5.2 | HIGH | 21 records have `category=External` but `customer=""` — phantom external work with no attribution | data |
| 5.3 | MEDIUM | 200 records have real client names but `category=Internal` — "Internal" is overloaded (no-client vs self-initiated) | data |
| 5.4 | MEDIUM | 9 records: `category=External` + `demandType≠External(Customer)` (8 Incidents + 1 Spike) — schema inconsistency | data |
| 5.5 | MEDIUM | Gainsight→Staircase mapping is execution-order dependent (merge says "Gainsight", normalize renames to "Staircase") | `normalize.py:106` vs `merge.py:93` |
| 5.6 | LOW | Substring matching in `extract_customer` — "Archery" would match "Archer", "GemStone" would match "Gem" | `merge_opossum.py:98` |
| 5.7 | LOW | Two separate `demandType` schemes coexist: spreadsheet has 7 values, Linear has only 2 | data |

### Auditor #6 — Frontend Rendering (from previous session)

| # | Sev | Finding |
|---|-----|---------|
| 6.1 | HIGH | CDN failure for Chart.js/SheetJS cascades to break entire dashboard (no local fallback) | `build_html_dashboard.py:267-268` |
| 6.2 | HIGH | Chart destroy ordering — destroying before null check | JS in `build_html_dashboard.py` |

### Auditor #7 — Security & Resilience (from previous session)

| # | Sev | Finding |
|---|-----|---------|
| 7.1 | CRITICAL | `</script>` in task titles breaks out of inline script context — XSS if titles contain HTML/JS | `build_html_dashboard.py:1010` |
| 7.2 | HIGH | No backup before overwriting `_dashboard_data.json` | `merge_opossum.py:247` |
| 7.3 | HIGH | No HTTP timeout on Linear API calls — script hangs indefinitely on network issues | `refresh_linear_cache.py:99` |
| 7.4 | HIGH | XSS: `esc()` function applied inconsistently — some values injected into HTML without escaping | `build_html_dashboard.py` |

### Auditor #8 — Performance & Scale (from previous session)

| # | Sev | Finding |
|---|-----|---------|
| 8.1 | LOW | At 498 records, performance is fine. At 2000+ records, inline JSON in HTML will cause browser lag | `build_html_dashboard.py` |

### Auditor #9 — Business Logic Validator

| # | Sev | Finding |
|---|-----|---------|
| 9.1 | CRITICAL | KPI3 is non-functional — 0 rework labels across 498 records, shows "100% ON TARGET" | `merge_opossum.py:205`, dashboard |
| 9.2 | HIGH | KPI2 uses `startedAt` (In Progress) but Waki specified "atribuição" (assignment) — different metric for Linear vs spreadsheet members | `build_html_dashboard.py:349` |
| 9.3 | HIGH | Default "External" segment hides 3 of 7 members — Carlos (133 tasks) shows only 9 in default view | `build_html_dashboard.py:310` |
| 9.4 | HIGH | No ETA exclusion renders KPI1 meaningless for small samples — Yasmim shows 100% on 3 tasks | data |
| 9.5 | MEDIUM | Trend chart bars show ETA breakdown on ALL tabs, even velocity and reliability where they're semantically wrong | `build_html_dashboard.py:577-594` |
| 9.6 | MEDIUM | "On Track" tasks excluded from KPI1 can make mid-sprint accuracy misleadingly high | `merge_opossum.py:143` |

### Auditor #10 — Data Quality Analyst

| # | Sev | Finding |
|---|-----|---------|
| 10.1 | CRITICAL | `startedAt` empty for 91% of records (450/498) — KPI2 is unmeasurable for 5/7 members | data |
| 10.2 | HIGH | THAIS ETA coverage at 48% (22/46) — KPI1 unreliable, sample too small | data |
| 10.3 | HIGH | 25 unparseable date strings ("TBD", "N/A", "-") still in eta/delivery fields | data |
| 10.4 | HIGH | 86 records (17%) have no customer — customer-level KPIs have a blind spot | data |
| 10.5 | MEDIUM | "B.B.C." vs "B.B.C" status split (4+4 records) — not normalized | data |
| 10.6 | MEDIUM | 49 records in 14 duplicate groups (9.8%) — especially Alexandra's 13× "Winter Release" | data |
| 10.7 | MEDIUM | 5 GABI records with `weekRange` year=2019 instead of 2025 | data |
| 10.8 | LOW | 5 records with empty `week`, 4 with empty `dateAdd` — invisible to time-series analysis | data |
| 10.9 | LOW | Rework field is 100% empty across all 498 records — feature is dead | data |

---

## WAVE 2: Perspective-Based Auditors (A–J)

### Auditor A — Waki (The Requesting Manager)
*"Do I trust these numbers enough to make decisions?"*

| Rating | Finding |
|--------|---------|
| TRUST-BREAKING | **91% of "On Time" tasks are trivially correct** (ETA=Delivery, filled retroactively). Real estimation accuracy for the whole team is far below 83%. The XLSX version computes "Real Accuracy" excluding trivials — the HTML doesn't. |
| TRUST-BREAKING | **KPI3 at 100% is a credibility landmine.** If I show this to my boss and they ask "zero rework across 372 tasks?", the conversation derails into explaining broken metrics. |
| TRUST-BREAKING | **Two measurement systems on one leaderboard.** Spreadsheet people (5) self-report dates retroactively. Linear people (2) have honest system-tracked dates. Comparing them side-by-side is unfair. |
| CONCERNING | Thais shows worst accuracy (37.5%) but has the most honest data. The dashboard punishes transparency. |
| CONCERNING | No "ETA Coverage" metric visible — I can't see who is hiding behind "No ETA" exclusions. |
| CONCERNING | No "Data Confidence" indicator per person (the XLSX version has this; the HTML doesn't). |
| NICE-TO-HAVE | Show sample size (n) next to every percentage. "83% (n=8)" reads very differently from "83% (n=91)". |

**Verdict:** "I would NOT show this to my boss in its current form."

---

### Auditor B — CRO (Demanding Executive)
*"Are we delivering for our clients on time?"*

| Rating | Finding |
|--------|---------|
| DEAL-BREAKER | **No actionable output.** No "clients at risk" alert, no prioritized risk list, no "what to do next." |
| NEEDS WORK | **Client KPI table buried at the bottom.** Tropic at 38% accuracy should be a red banner at the top, not a hidden row. |
| NEEDS WORK | **No week-over-week delta.** KPI pills show 4-month average, not current trajectory. |
| NEEDS WORK | **21 External tasks with no customer assigned** — 12% data quality gap. |
| NEEDS WORK | **Targets (90%/28d/90%) have no documented justification.** Are they SLA-bound? Aspirational? |
| ACCEPTABLE | External/Internal toggle defaults to External (correct for CRO). |
| ACCEPTABLE | Trend charts with target lines are well-designed. |

**Verdict:** "Well-built engineering dashboard for a team lead. NOT an executive dashboard."

---

### Auditor C — Thaís (Person Being Measured)
*"Is this fair to me?"*

| Rating | Finding |
|--------|---------|
| UNFAIR | **Dual-source comparison is invalid.** My Linear data is honest (forward-looking ETAs). Spreadsheet members fill ETA=delivery retroactively (88-96% trivial). I have 25% trivial. |
| UNFAIR | **Sub-task penalty.** I have 23 sub-tasks (50% of my records). Nobody else has sub-tasks. Sub-tasks without individual ETAs inflate my "No ETA" count. |
| UNFAIR | **Week assignment from `createdAt` is wrong.** My tasks show in weeks I wasn't working on them. `startedAt` exists for 22 of my 46 tasks — the code uses it for KPI2 but not for the heatmap. |
| QUESTIONABLE | My accuracy (37.5%) is based on 8 measurable tasks. Gabi's (88%) is based on 43 — but 38 of hers are trivial (ETA=delivery). My data is actually more informative. |
| QUESTIONABLE | Customer extraction regex uses `re.match` (start of string only) — at least one of my `[Gainsight]` tasks is misclassified as Internal because the bracket isn't at position 0. |
| ACCEPTABLE | Velocity calculation does use `startedAt` when available (correct). |

**Verdict:** "The dashboard measures logging discipline, not implementation quality."

---

### Auditor D — Skeptical Data Analyst
*"Where does the data lie?"*

| # | Rating | Finding |
|---|--------|---------|
| LIE #1 | CRITICAL | **Reliability KPI is always 100%.** Zero `rework:implementation` labels exist across 498 records. The metric measures label discipline, not code quality. It's a measurement void displayed as a perfect score. |
| LIE #2 | CRITICAL | **Overdue excluded from accuracy denominator — THIAGO inflated +17.9pp.** KPI1 formula is `OnTime/(OnTime+Late)`, dropping Overdue tasks. THIAGO has 11 Overdue tasks hidden by the core period filter. If included: accuracy drops from ~83% to ~65%. |
| LIE #3 | HIGH | **81% of THIAGO's "On Time" tasks are zero-day** (ETA == Delivery date). These are retroactively filled — the spreadsheet member records delivery, then copies the same date to ETA. This is not estimation, it's bookkeeping. |
| LIE #4 | HIGH | **Core period hides 11 Overdue tasks for THIAGO.** `isCoreWeek` filters to Dec 2025–Mar 2026. Tasks with ETAs before December (still open) are excluded from the dashboard entirely. They don't appear as Overdue — they simply vanish. |
| LIE #5 | HIGH | **Two completely different measurement systems compared on equal footing.** Spreadsheet data (5 members): manually curated, retroactive, ETA=Delivery common. Linear data (2 members): system-tracked, forward-looking ETAs, honest timestamps. Comparing them is statistically invalid. |
| LIE #6 | HIGH | **19/31 YASMIM tasks counted in wrong week.** `createdAt` used for week assignment, but 57–59 day gaps between creation and `startedAt` are common. Tasks show in December when work didn't begin until February. |
| LIE #7 | HIGH | **Normalize fixes dates but never recalculates `perf`.** When `normalize_data.py` corrects a corrupted ETA from a sentence to blank, it sets `perf='No ETA'`. But when it fixes a short date like "11-Fev" → "2026-02-11", it doesn't re-evaluate whether the task was On Time or Late with the corrected date. Ghost labels persist. |
| LIE #8 | MEDIUM | **52 duplicate records inflate counts.** 14 duplicate groups detected (49 records, 9.8%). Alexandra alone has 13× "Winter Release" entries. These inflate task counts, distort heatmap density, and double-count On Time/Late classifications. |
| LIE #9 | MEDIUM | **Default filter hides 64% of data.** The dashboard opens on "External" segment, which contains only ~180 of 498 records. Three members (Carlos, Alexandra, Diego) have most of their work tagged Internal — they appear nearly empty in the default view. |
| LIE #10 | MEDIUM | **On Hold tasks penalized as Overdue.** 8 "B.B.C." (Blocked By Client) tasks with past-due ETAs show as Overdue. The team member can't control client-side blockers, but the dashboard treats these as personal failures. |
| LIE #11 | LOW | **Small denominators create statistical noise masquerading as signal.** YASMIM: 100% accuracy on n=3 measurable tasks. THAIS: 37.5% on n=8. The dashboard shows both as equally authoritative percentages with identical visual weight. A coin flip could produce YASMIM's result. |
| LIE #12 | LOW | **"No ETA" is not random — it correlates with task difficulty (survivorship bias).** Complex tasks are less likely to get ETAs (hard to estimate). By excluding "No ETA" from accuracy, the KPI only measures easy-to-estimate work. The hard tasks that define team capability are invisible. |

**Core thesis:** "The dashboard doesn't contain a single fabricated number. Every calculation is technically correct given its inputs. But the combination of selective denominators, retroactive dates, measurement voids displayed as perfection, and incompatible data sources creates a narrative that is *directionally wrong*. The team appears to be performing at 83% accuracy with 100% reliability. The honest reading is: accuracy is unknown (contaminated by retroactive ETAs), reliability is unmeasured (no labels), and velocity is incomparable across members (different time semantics)."

---

### Auditor E — New Team Member
*"What is this? How do I use it?"*

| Rating | Finding |
|--------|---------|
| LOST | **No documentation exists.** No README in `/kpi/`, no onboarding guide, no explanation of data sources. |
| LOST | **Color legend is invisible.** Heat scale thresholds (≥90%=green, ≥75%=light green, etc.) are only in the JS source code. |
| LOST | **"W.1", "W.2" format unexplained.** Custom week-of-month scheme not documented anywhere in the UI. |
| CONFUSED | **"Raccoons KPI Dashboard" title** — dashboard covers 2 teams (Raccoons + Opossum) but names only one. |
| CONFUSED | **"WIP" badge on Activity tab** — no explanation of what's unfinished or when it will be ready. |
| CONFUSED | **"---" values ambiguous** — means "data not available" but could be read as "not applicable" or "zero." |
| CONFUSED | **No guidance on what I need to do** to be tracked properly (set dueDates? fill a spreadsheet? use labels?). |
| CLEAR | KPI pills with target badges are intuitive (green=good, red=bad). |
| CLEAR | Member cards give a quick per-person summary. |

**Verdict:** "I would need a 1-page guide to use this dashboard. Without it, it's anxiety-inducing."

---

### Auditor F — Devil's Advocate
*"This entire dashboard is fundamentally flawed."*

| Attack | Verdict |
|--------|---------|
| **Activity ≠ Value.** 50 small tasks on time > 1 critical project late. No task weighting. | **VALID.** No complexity, revenue, or priority weighting exists. |
| **Incompatible data sources.** Manual spreadsheets (curated) vs Linear API (raw). Apples vs oranges. | **VALID.** 91% trivial rate in spreadsheet cohort proves this. |
| **Normalize.py is a confession of bad data.** 10+ fix rules = broken data collection. | **VALID.** Fixes symptoms, not the disease. |
| **Hardcoded period = ticking time bomb.** Must edit code every 4 months. | **VALID.** Found in 12+ files across 10+ scripts. |
| **"No ETA" exclusion REWARDS not setting ETAs.** Fewer ETAs = fewer chances to be late = higher accuracy. | **VALID.** Goodhart's Law in action. |
| **No client importance weighting.** $500K contract = internal cleanup task. | **VALID.** No revenue or priority data. |
| **Rework label dependency.** If nobody labels rework, KPI3 is always 100%. | **VALID.** Zero labels in 498 records proves this. |
| **Only 2 teams fetched.** Cross-team work is invisible. | **VALID.** Only Opossum + Raccoons. |
| **Red cells = public shaming.** Damages psychological safety. | **PARTIALLY VALID.** Heatmap design is inherently comparative. |
| **Engineering cost vs decision value.** 1000+ lines for a frozen 4-month snapshot. | **PARTIALLY VALID.** Infrastructure is solid; the period limitation is the issue. |

---

### Auditor G — Product Manager
*"UX, information architecture, storytelling"*

| Area | Rating | Finding |
|------|--------|---------|
| Info Hierarchy | NEEDS ITERATION | All 3 KPI pills equal size — ETA Accuracy (the #1 metric) should be the "hero" |
| Narrative Flow | NEEDS ITERATION | Member cards interrupt summary→detail flow; customer table outside tab system |
| Discoverability | SHIP-BLOCKING | Critical info hidden behind hover-only tooltips; formula, color legend, task details all require hover; inaccessible on touch devices |
| Color System | NEEDS ITERATION | Header green = data green — creates "everything looks healthy" bias |
| Empty States | NEEDS ITERATION | No minimum-N threshold — 1 task = "100%" displayed with same confidence as 50 tasks |
| Mobile | NEEDS ITERATION | Single `@media(900px)` breakpoint; heatmap requires horizontal scroll; tooltips inaccessible on touch |
| Export/Share | NEEDS ITERATION | No URL-based state; no deep linking; no PDF export |

**Top 5 PM Improvements (by impact/effort):**
1. URL hash state for shareable filtered views (~20 lines JS)
2. Visible methodology line under each KPI pill (~15 lines HTML)
3. Hero treatment for ETA Accuracy (CSS `2fr 1fr 1fr`)
4. Click-to-filter on person names in heatmap (~30 lines JS)
5. Minimum-N threshold for percentages (~10 lines JS)

---

### Auditor H — Operations Auditor
*"Who runs this? When? What breaks?"*

| # | Sev | Finding |
|---|-----|---------|
| H.1 | CRITICAL | **Bus factor = 1.** Thiago runs everything manually. No runbook, no cron, no CI/CD. |
| H.2 | CRITICAL | **83% of data is frozen.** Spreadsheet records (413/498) come from a one-time export that never refreshes. Only 2/7 members get fresh data on pipeline runs. |
| H.3 | HIGH | **No refresh schedule defined.** No calendar reminder, no Slack notification, no recurring ticket. |
| H.4 | HIGH | **Core period hardcoded in 12+ locations** across 10+ files. Must find-and-replace all for Q2. |
| H.5 | HIGH | **New member onboarding requires updating 5+ systems** (Linear, Sheets, `PERSON_MAP`, `PEOPLE` list, variant scripts) — no checklist. |
| H.6 | MEDIUM | **No staleness warning.** Footer shows build date but no "data is X days old" banner. |
| H.7 | MEDIUM | **Linear label discipline uncontrolled.** No SOP for when/who applies `rework:implementation`. |
| H.8 | LOW | Data in git (good) but no pre-write backup or atomic writes. |

---

### Auditor I — Narrative Integrity Analyst
*"What story is this telling? Is it honest?"*

| Rating | Finding |
|--------|---------|
| MISLEADING | **KPI1 denominator drops 32% of all tasks.** 160/498 records excluded (Overdue, No ETA, No Delivery Date, N/A, On Track). The "83% accuracy" is measured on the easy-to-measure subset. |
| MISLEADING | **KPI3 "100% ON TARGET" is the absence of measurement, not evidence of quality.** Displayed with a green badge that conveys false confidence. |
| MISLEADING | **Thais's "bad" numbers may reflect honest data.** The dashboard punishes the person with the most transparent data source. Red cells next to her name are indistinguishable from poor performance. |
| INCOMPLETE | **No "WHY" anywhere.** Dashboard shows WHAT happened but not WHY (no annotations, no context, no notes). |
| INCOMPLETE | **No capacity context.** Carlos (133 tasks) vs Yasmim (31 tasks) shown on same grid — no indication of workload or complexity. |
| INCOMPLETE | **No client risk signaling.** Tropic at 38% accuracy is hidden in the middle of a table. |
| INCOMPLETE | **Premature metrics danger.** If measurement improves (more Linear adoption, rework labels used), numbers will DROP. Dashboard has no mechanism to explain "numbers went down because measurement got better." |

**Core problem:** "Every individual number is technically correct. But the visual hierarchy — green badges, 'ON TARGET' labels — tells a story of a high-performing team. The real story is a partially measurable team with significant data quality gaps."

---

### Auditor J — Product Strategist
*"What should this become in 6 months?"*

**Current Maturity:** Late Prototype / Early MVP

**6-Month Roadmap:**

| Month | Focus | Key Deliverables |
|-------|-------|-----------------|
| 1 | Automation | `orchestrate.py` wrapper, Task Scheduler daily run, auto-upload, rolling time window |
| 2 | Intelligence | Slack alerts, automated rework detection, SLA compliance (data already cached), overdue aging |
| 3 | Unification | All 7 members on Linear, retire spreadsheet as data source, simplify pipeline to 3 steps |
| 4 | Distribution | Weekly Slack digest, URL hash for shareable views |
| 5 | Depth | Capacity model, cross-period comparison, webhook-driven refresh |
| 6 | Polish | Archive 10 variant dashboards, consolidate builders, write runbook, evaluate SQLite |

**#1 Strategic Priority:** Migrate all 7 TSA members to Linear (eliminates the dual-source problem that causes 80% of the audit findings).

---

## CONSOLIDATED FINDING MATRIX

### CRITICAL (4 findings)

| ID | Finding | Auditors |
|----|---------|----------|
| C1 | **KPI3 is non-functional** — 0 rework labels, shows "100% ON TARGET" | #9, A, B, C, F, H, I |
| C2 | **Partial pagination overwrites complete cache** — API error on page 2+ saves partial data | #1, #4 |
| C3 | **Non-atomic writes** — crash during `json.dump` = total data loss (truncate then write) | #1, #7 |
| C4 | **91% of records lack `startedAt`** — KPI2 is unmeasurable for 5/7 members | #10 |

### HIGH (18 findings)

| ID | Finding | Auditors |
|----|---------|----------|
| H1 | `isCoreWeek` hardcoded, expires in 9 days, found in 12+ files | #3, #9, H, J |
| H2 | Member card accuracy formula ≠ KPI1 formula (includes Overdue vs doesn't) | #2, #9 |
| H3 | 91% trivial rate — ETA=Delivery filled retroactively, inflates accuracy | A, C, F, I |
| H4 | Bus factor = 1, no runbook, no automation, no schedule | H |
| H5 | 83% of data is frozen — spreadsheet records never re-pulled in pipeline | H |
| H6 | Delete-and-rebuild in merge with no count validation | #1 |
| H7 | No concurrency protection on shared JSON | #1 |
| H8 | Raccoons cache guard checks wrong variable | #1 |
| H9 | `</script>` injection via raw JSON in HTML template | #1, #7 |
| H10 | No backup before overwriting `_dashboard_data.json` | #1, #7 |
| H11 | No HTTP timeout on Linear API calls | #7 |
| H12 | CDN failure cascades to break entire dashboard | #6 |
| H13 | 21 External records with blank customer | #5, #10, B |
| H14 | THAIS ETA coverage at 48% — KPI1 unreliable for her | #10, C |
| H15 | 25 unparseable date strings still in data | #10 |
| H16 | KPI2 uses `startedAt` (Linear) vs `dateAdd` (spreadsheet) — incomparable | #9, C |
| H17 | New member onboarding requires 5+ system updates, no checklist | H |
| H18 | Spike record triple inconsistency (External + Internal + empty customer) | #5 |

### MEDIUM (15 findings)

| ID | Finding | Auditors |
|----|---------|----------|
| M1 | Year-inference for short dates depends on run date | #1, #3 |
| M2 | `except: pass` swallows all errors silently | #1 |
| M3 | 9 Canceled tasks with `perf=Overdue` | #1, #2 |
| M4 | 200 records: real client + Internal category (overloaded semantics) | #5 |
| M5 | 9 records: External category + non-External demandType | #5 |
| M6 | Gainsight→Staircase mapping is execution-order dependent | #5 |
| M7 | Trend chart bars show ETA breakdown on all tabs (semantically wrong for velocity/reliability) | #9 |
| M8 | "B.B.C." vs "B.B.C" status split (8 records) | #10 |
| M9 | 49 records in 14 duplicate groups (9.8%) | #10 |
| M10 | 5 GABI records with weekRange year=2019 | #10 |
| M11 | No staleness warning for viewers | H |
| M12 | Default External view hides 3 of 7 members | #9 |
| M13 | On Track exclusion makes mid-sprint accuracy misleadingly high | #9 |
| M14 | External/Internal toggle enables cherry-picking with no guidance on "recommended view" | I |
| M15 | No minimum sample size threshold — 1 task = "100%" displayed with full confidence | G, #9, I |

### LOW (8 findings)

| ID | Finding |
|----|---------|
| L1 | Description truncated at 500 chars with no indicator |
| L2 | Raw JSON read with no validation before HTML injection |
| L3 | Substring matching in `extract_customer` — latent false positive risk |
| L4 | Two separate `demandType` schemes (7 values for spreadsheet, 2 for Linear) |
| L5 | `date_add` parameter in `calc_perf` is never used (dead code) |
| L6 | At 498 records, scale is fine; at 2000+ inline JSON will cause browser lag |
| L7 | 5 records with empty `week`/`dateAdd` — invisible to time-series |
| L8 | Encoding `errors='replace'` on stdout masks data issues |

---

## PERSPECTIVE SYNTHESIS: What Multiple Auditors Agree On

### 7/10 perspective auditors flagged the same #1 issue:
> **The dual-source problem (spreadsheet vs Linear) makes cross-person comparison unfair and metrics unreliable.**

### 6/10 flagged:
> **KPI3 at "100%" with zero data points is actively misleading — remove it or label it "NOT ACTIVE".**

### 5/10 flagged:
> **No documentation, no runbook, no onboarding guide — the dashboard is opaque to anyone who didn't build it.**

### 4/10 flagged:
> **Client-centric view should be primary, not buried — a CRO cares about Tropic at 38%, not which week Carlos had a red cell.**

### 3/10 flagged:
> **Sample size must be visible — "100% (n=3)" is not the same as "100% (n=50)" but the dashboard treats them identically.**

---

## TOP 10 RECOMMENDATIONS (Prioritized)

| # | Action | Effort | Impact | Fixes |
|---|--------|--------|--------|-------|
| 1 | **Make `isCoreWeek` dynamic** (rolling 4 months or data-driven) — extract to single config | 4 hours | CRITICAL | H1 |
| 2 | **Mark KPI3 as "NOT ACTIVE"** or remove green badge until rework labels are in use | 30 min | CRITICAL | C1 |
| 3 | **Add atomic writes** (write to `.tmp`, then `os.replace`) across all JSON outputs | 2 hours | CRITICAL | C3 |
| 4 | **Add pagination completeness check** — if `hasNextPage=true` but loop broke, refuse to save | 1 hour | CRITICAL | C2 |
| 5 | **Align member card formula with KPI1** — both should use `onTime/(onTime+late)` | 30 min | HIGH | H2 |
| 6 | **Create `orchestrate.py`** wrapper + schedule via Task Scheduler | 4 hours | HIGH | H4, H5 |
| 7 | **Add minimum-N threshold** — cells with <3 measured tasks show count instead of % | 1 hour | HIGH | M15 |
| 8 | **Add sample size (n) and data source badge** to member cards and heatmap | 2 hours | HIGH | H3, H14, H16 |
| 9 | **Sanitize JSON injection** — use `json.dumps()` + proper escaping instead of `str.replace` | 1 hour | HIGH | H9 |
| 10 | **Write a 1-page KPI Dashboard Guide** (data sources, formulas, color legend, what to do) | 2 hours | HIGH | E findings |

---

## APPENDIX: Auditor Coverage Matrix

| File | #1 | #2 | #3 | #4 | #5 | #6 | #7 | #8 | #9 | #10 | A | B | C | D | E | F | G | H | I | J |
|------|----|----|----|----|----|----|----|----|----|----|---|---|---|---|---|---|---|---|---|---|
| refresh_linear_cache.py | ✓ | | | ✓ | | | ✓ | | | | | | | | | ✓ | | ✓ | | ✓ |
| merge_opossum_data.py | ✓ | | | | ✓ | | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| normalize_data.py | ✓ | | ✓ | | ✓ | | | | | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| build_html_dashboard.py | ✓ | ✓ | ✓ | | | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| _dashboard_data.json | ✓ | | | | ✓ | | | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | ✓ | |
| Process/Operations | | | | | | | | | | | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |

---

*Report generated 2026-03-22 (Auditor D updated same day). 20 auditors, 57+ unique findings, 0 changes applied.*
