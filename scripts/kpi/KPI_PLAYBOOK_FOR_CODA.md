# TSA KPI Playbook — Complete Guide

> Version 3.0 | Last updated: 2026-04-13 | Dashboard: v3.2 (audit-hardened + UX fixes) | Author: Thiago Rodrigues

> This document is the single source of truth for understanding, operating, and interpreting the three TSA KPIs. It is designed for the Coda Solutions Central and covers strategic, operational, and executive perspectives. Every person on the team — from individual contributor to leadership — should be able to read this document and understand exactly how their daily work translates into measurable outcomes.

## OVERVIEW

The TSA (Technical Solutions Architecture) team measures performance through three Key Performance Indicators that together capture the health of customer implementation delivery. These KPIs are not vanity metrics. They are operational instruments that answer three fundamental questions about how we deliver work.

ETA Accuracy answers the question: "Do we deliver when we say we will?" This is the most critical KPI because it directly reflects our credibility with customers and internal stakeholders. When a TSA commits to a delivery date, that date becomes a promise. ETA Accuracy measures how often we keep that promise.

Customer Onboarding (Implementation Velocity) answers the question: "How fast do we deliver?" Speed matters because customers are waiting to see value from TestBox. The faster we move from ticket start to delivery, the sooner customers get what they need. This KPI measures the average number of days between when work begins and when it reaches review or completion.

Implementation Reliability answers the question: "Do we deliver it right the first time?" Rework is expensive. When a task that was marked as Done gets reopened because something was missed or broken, it costs the team time and erodes trust. This KPI measures the percentage of completed work that stays completed without being reopened.

- Team: Raccoons (5 members — Thiago, Carlos, Alexandra, Diego, Gabi)
- Data source: Linear (sole source of truth for all KPI calculations)
- Historical backlog: Google Sheets (frozen archive — excluded from all KPI calculations)
- Dashboard: Self-contained HTML file (~990KB), auto-refreshed daily at 09:00 via system tray
- Dashboard URL: Published via ngrok with basic auth (kpi:raccoons2026) and shared with stakeholders
- System tray: Desktop icon provides "Refresh & Rebuild (Linear API)" for full pipeline and "Quick Rebuild (cached data)" for instant rebuilds, with Windows toast notifications on completion

## KPI 1 — ETA ACCURACY

> "Do we deliver when we say we will?"

### Strategic Purpose

ETA Accuracy is the flagship KPI for the TSA team. It measures the percentage of tickets that were delivered on or before their committed due date. This metric is a direct reflection of planning maturity, workload management, and communication quality. A team that consistently delivers on time has strong estimation skills, manageable workloads, and clear communication with stakeholders about what is feasible.

From a leadership perspective, ETA Accuracy at or above 90 percent signals a healthy team that can be trusted with commitments. Below 80 percent indicates systemic issues that need investigation — either the team is overcommitted, estimates are unrealistic, or external blockers are not being surfaced early enough.

### Target

- Goal: Greater than 90 percent
- Pass: 90 percent or above (green badge on dashboard)
- Warning: 80 to 89 percent (yellow badge)
- Fail: Below 80 percent (red badge)

### Formula

```
ETA Accuracy = On Time / (On Time + Late) × 100
```

If no tickets have a final On Time or Late determination (denominator is zero), the dashboard displays N/A for ETA Accuracy. This typically happens when all tickets are still in progress, paused, or lack a dueDate.

Only tickets with BOTH a due date (ETA) and a delivery date are included in the calculation. Tickets without a due date, tickets that are not started, and tickets that are canceled are excluded entirely. This ensures the metric only measures actionable commitments. Additionally, tickets currently In Progress whose dueDate has passed are counted as Late even without a delivery date — this ensures accountability for overdue work. You cannot avoid a Late classification by simply not delivering.

IMPORTANT: The system compares delivery against the ORIGINAL ETA (the first dueDate ever committed), not the current dueDate. If you set a dueDate of January 15 and later change it to January 30, the system still measures against January 15. The rationale is that KPI 1 measures estimation accuracy — how well you predicted the delivery date the first time. Changing the ETA after the fact does not change the original commitment. If no ETA change is recorded in the ticket history, the current dueDate is used as the original.

### What Counts as "On Time"

A ticket is On Time when its delivery date is on or before its due date PLUS a 1 business-day tolerance buffer (D.LIE27, introduced 2026-04-24). The delivery date is not simply the Linear completedAt timestamp. The system uses activity-based detection from the ticket's history to find the first moment the ticket transitioned to In Review or Done status. This is more accurate because a ticket might sit in review for days before being formally closed.

- On Time: deliveryDate is on or before (original ETA + 1 business day). Weekends are skipped — if ETA is Friday, delivery Monday is still On Time; delivery Tuesday is Late. Same-day or earlier always counts as On Time.
- Late: deliveryDate is more than 1 business day after the original ETA.

Rationale: the buffer absorbs trivial end-of-day / timezone / next-morning handoffs without crediting real slippage. Two or more business days late still counts as Late.

### What Gets Excluded from KPI 1

Several categories of tickets are excluded from the ETA Accuracy calculation because they are not actionable commitments.

- No ETA (External only, D.LIE26 introduced 2026-04-24): Tickets WITHOUT a dueDate set in Linear AND whose category is External(Customer). These are external commitments with no promise date — not measurable, but still visible in the "No ETA" bucket so TSAs can prioritize setting ETAs.
- N/A for Internal-without-ETA (D.LIE26): Internal or non-customer tickets without a dueDate are classified N/A instead of "No ETA". Rationale: Internal work (improvements, standardizations, ops) is not a customer-facing commitment, so missing ETAs there are not a KPI miss.
- Not Started: Tickets in Backlog, Todo, or Triage status that have no dueDate. Work has not begun, so measuring delivery timing is meaningless.
- Canceled: Tickets with status Canceled or Duplicate. Work was abandoned, not delivered.
- Blocked By Customer (B.B.C): Tickets whose status field is B.B.C (or variants: B.B.C., BBC, bbc). The system normalizes all variants to "B.B.C" and excludes them from the KPI calculation with a "Blocked" performance label. Note: B.B.C is detected via the status field, not via labels. In Linear, if the team uses a custom status for blocked-by-customer, it must match one of these variants to be recognized. Alternatively, the Paused status can be used, which gets an "On Hold" label.
- Paused / On Hold: Tickets with status Paused or On Hold are excluded from the on-time/late calculation entirely. They receive an "On Hold" performance label. Use this when a ticket is blocked but not specifically by a customer.
- N/A: Catch-all for tickets that cannot be meaningfully categorized (missing data, parsing errors).
- Admin-Closed (Pattern 1): Tickets marked Done that were never started — no startedAt, no deliveryDate, no inReviewDate. These are typically bulk closures or migrations. Auto-classified as On Time if they have an ETA, or N/A if they do not.
- Admin-Closed (Pattern 2 — Migrated): Tickets marked Done where createdAt equals dueDate (same day), with no In Review step, no startedAt, and at most one ETA change. These are tickets that were already delivered in the spreadsheet era and merely closed in Linear for tracking. Same classification: On Time if ETA exists, N/A otherwise.
- Parent Tickets with Subtasks: When a ticket has child tickets, the parent is excluded from KPI. Only the subtasks (where real work happens) are measured. The parent ticket is coordination, not delivery.

### How a Ticket Enters KPI 1

For a ticket to be counted in ETA Accuracy, the following conditions must all be true.

- The ticket has an assignee who is a KPI team member (Thiago, Carlos, Alexandra, Diego, or Gabi)
- The ticket has a dueDate set in Linear (this is the ETA commitment)
- The ticket has reached a terminal state (Done or In Review) OR is currently in progress with an overdue ETA
- The ticket is not a parent ticket with subtasks
- The ticket is not Canceled, Duplicate, B.B.C, or Paused

### Linear Ticket Requirements for KPI 1

When creating or managing a ticket in Linear, the following fields directly impact KPI 1.

- dueDate (CRITICAL): This is the ETA. Without it, the ticket is invisible to KPI 1. Every ticket that represents a real delivery commitment must have a dueDate. Set this at the time the work is planned, not after delivery.
- Assignee: The ticket must be assigned to a KPI team member. Unassigned tickets are not tracked.
- Status transitions: The system tracks when a ticket moves to In Review or Done via Linear's history. The first such transition becomes the deliveryDate.
- Status (for B.B.C): If the ticket's status is set to B.B.C (or variants B.B.C., BBC, bbc), it will be excluded from the on-time/late calculation entirely. Note: this is a status-level check, not a label-level check. In the current Linear workflow, the practical equivalent is moving the ticket to Paused status, which also excludes it.
- Labels: The label "rework:implementation" is used for KPI 3. Labels like B.B.C exist in historical spreadsheet data but are not commonly used as labels in Linear.

### Operational Checklist for KPI 1

- When you accept a ticket: Set a realistic dueDate immediately. Do not leave it blank.
- When your estimate changes: Update the dueDate in Linear. The system tracks ETA changes and records both the original and final ETA.
- When you finish work: Move the ticket to In Review. This timestamp becomes your delivery date.
- When you are blocked by a customer: Move the ticket to Paused status. This gives it an "On Hold" performance label and excludes it from the on-time/late calculation. If your Linear workflow has a custom B.B.C status, that also works. Do NOT simply add a label — the system checks the status field, not labels, for this exclusion.
- When a ticket is no longer needed: Move it to Canceled. It will be excluded from KPI 1 entirely.

### How ETA Accuracy Appears on the Dashboard

The dashboard shows ETA Accuracy in several views.

- KPI Strip (top): Shows the team-wide percentage, the sample size (n), and a pass/fail badge.
- Member Cards: Each person's card shows their individual On Time percentage, Late percentage, accuracy percentage, and ETA coverage (how many of their tickets have a dueDate).
- ETA Accuracy Heatmap: A grid of Person × Week showing green (on time) and red (late) cells. This makes patterns visible — for example, a person who is consistently late in the third week of the month may be overcommitted during that period.

### Common Pitfalls

- Setting dueDate after delivery (retroactive ETA): The system detects this pattern. If dueDate equals deliveryDate and there is only one ETA change in history, the ticket is flagged as retroactiveEta. This is gaming the metric and should be avoided. The dashboard computes a separate "Organic Accuracy" metric in the Insights tab that excludes retroactive ETAs, showing the "true" accuracy alongside the total accuracy and the inflation gap between them. This makes ETA gaming visible to leadership.
- Not setting dueDate at all: This is the most common issue. Tickets without dueDate are invisible to KPI 1. Low ETA coverage (shown on member cards) means the metric is based on a small sample and may not be reliable.
- Using completedAt instead of activity-based delivery: The system does NOT use Linear's completedAt as the delivery date. It uses the first transition to In Review or Done from the ticket's history. This is more accurate but means that manually setting completedAt without a status transition will not count.
- Setting overly conservative dueDates: While not flagged by the system, setting a dueDate far beyond the expected delivery (e.g., 90 days for a 5-day task) guarantees On Time but makes the ETA meaningless. Leadership should review velocity alongside accuracy — a person who is 100 percent on time but averages 45 days per ticket may be padding estimates.

## KPI 2 — IMPLEMENTATION VELOCITY

> "How fast do we deliver?" — Also referred to as "Customer Onboarding" speed in stakeholder contexts, though this metric specifically measures ticket-level implementation time, not the full customer onboarding lifecycle.

### Strategic Purpose

Implementation Velocity measures the average time between when work starts and when it is delivered. This is the speed metric. While ETA Accuracy measures whether we deliver on time, Velocity measures how long the delivery actually takes. A team can be 100 percent on time but take 60 days per ticket, which would indicate overly conservative estimates.

From a leadership perspective, Velocity at or below 28 days indicates healthy throughput. Above 28 days suggests bottlenecks — either tickets are too large, handoffs between team members are slow, or work is being paused and resumed repeatedly.

### Target

- Goal: Less than 28 days average
- Pass: 28 days or fewer (green badge)
- Warning: 29 to 42 days (yellow badge)
- Fail: Above 42 days (red badge)

### Formula

```
Implementation Velocity = Average(deliveryDate - startedAt) across all completed tickets
```

For each completed ticket, the system calculates the number of calendar days between the startedAt date (when work began in Linear) and the deliveryDate (when the ticket first reached In Review or Done status).

### What Gets Measured

Only tickets that have BOTH a start date and a delivery date are included. This naturally filters to tickets where actual work was performed and completed.

- startedAt: The date when Linear recorded the ticket as started. This is set automatically by Linear when the ticket moves from Todo/Backlog to In Progress.
- deliveryDate: The date of the first transition to In Review or Done, extracted from the ticket's history. EXCEPTION: if rework was detected (the ticket went Done then back to In Progress and then Done again), the LAST Done date is used instead. This ensures the final delivery is what gets measured after a rework cycle.

### What Gets Excluded from KPI 2

- Tickets without startedAt: If Linear has no record of when work began, velocity cannot be calculated.
- Tickets without deliveryDate: If the ticket has not reached In Review or Done, there is no delivery to measure.
- Canceled and Duplicate tickets: Abandoned work is not measured.
- Parent tickets with subtasks: Same rule as KPI 1 — only the subtasks count.
- B.B.C and Paused tickets are implicitly excluded because they have not reached Done or In Review status, so they lack the required delivery data.

### Linear Ticket Requirements for KPI 2

- startedAt: This is set automatically by Linear when you move a ticket to In Progress. Make sure you move tickets to In Progress when you actually start working, not later.
- Status transitions: Moving to In Review or Done creates the delivery timestamp. Do this promptly when work is complete.
- Assignee: Same as KPI 1 — must be assigned to a KPI team member.

### Operational Checklist for KPI 2

- When you start working on a ticket: Move it to In Progress in Linear immediately. Do not batch-update multiple tickets later.
- When you finish the implementation: Move to In Review right away. The time between In Progress and In Review is your velocity.
- When you need to pause work: Consider moving to Paused status. This does not stop the clock (velocity still counts calendar days), but it makes the reason visible.
- Keep tickets small: Large tickets with many subtasks inflate velocity. Break work into deliverable chunks.

### How Velocity Appears on the Dashboard

- KPI Strip (top): Shows the team-wide average in days, with a pass/fail badge.
- Execution Time Chart: A bar chart showing average velocity per person. This makes it easy to identify who is consistently fast and who may need support.
- Member Cards: Each card shows the person's average velocity for the filtered period.

### Reviewer Delay

The dashboard also tracks reviewer delay — the time between In Review and Done. This is not a KPI itself, but it surfaces a common bottleneck. When the team average reviewer delay is high, it means tickets sit in review too long before being closed.

## KPI 3 — IMPLEMENTATION RELIABILITY

> "Do we deliver it right the first time?"

### Strategic Purpose

Implementation Reliability measures the percentage of completed work that stays completed without being reopened. When a ticket is marked Done and then moved back to In Progress (or Todo, or Backlog), it means something was missed, broken, or incomplete. This is rework, and it is expensive. It wastes time, delays other work, and signals quality issues.

From a leadership perspective, Reliability at or above 90 percent means the team produces high-quality work. Below 85 percent indicates that review processes may need strengthening, acceptance criteria may be unclear, or testing is insufficient.

### Current Status

IMPORTANT: KPI 3 is currently marked as NOT ACTIVE on the dashboard. This is because the rework labeling convention is still being adopted by the team. The metric is being tracked passively but is not yet used for performance evaluation. Once consistent use of the "rework:implementation" label is confirmed across the team, KPI 3 will be activated.

### Target (when activated)

- Goal: Greater than 90 percent
- Pass: 90 percent or above (green badge)
- Warning: 85 to 89 percent (yellow badge)
- Fail: Below 85 percent (red badge)

### Formula

```
Implementation Reliability = (Done without Rework) / (Total Done) × 100
```

A ticket is counted as "Done with Rework" if it has the label "rework:implementation" applied in Linear. This is the sole trigger for rework classification.

IMPORTANT: Prior versions of the system also used automatic history-based detection (flagging tickets that transitioned from Done back to In Progress/Todo/Backlog). This was removed because it produced false positives — for example, a TSA accidentally marking a ticket as Done and reverting it within minutes would be incorrectly flagged as rework. The current system requires explicit, intentional labeling. The history-based transition data is still collected internally for diagnostic purposes but does NOT affect the rework KPI calculation.

### What Counts as Rework

Rework is defined exclusively by the presence of the "rework:implementation" label on the ticket. This label should be applied when a ticket that was genuinely completed needs to be reopened because something was missed, broken, or incomplete.

The following are NOT rework.

- Accidental status changes: Marking a ticket as Done and quickly reverting it (e.g., within minutes) is a human error, not rework. Do NOT apply the rework label in this case.
- Reassignment during In Review: When person A finishes implementation and reassigns to person B for review, this is normal workflow, not rework.
- Status changes within active states: Moving from In Progress to Todo and back is task management, not rework.
- Cancellation after completion: Moving from Done to Canceled is a decision, not rework.

### Linear Ticket Requirements for KPI 3

- Label "rework:implementation" (REQUIRED): This is the sole trigger for marking a ticket as rework. Apply this label when a genuinely completed ticket needs to be reopened due to defects or incomplete work. Without this label, a ticket will NOT be counted as rework regardless of its status history.
- Acceptance criteria: While not tracked by the system, clear acceptance criteria on tickets reduce rework by ensuring both the implementor and reviewer agree on what "done" means before work begins.

### Operational Checklist for KPI 3

- Before moving to Done: Verify the work meets acceptance criteria. Test thoroughly. A ticket should only reach Done when you are confident it will stay Done.
- When rework is needed: Move the ticket back to In Progress AND apply the "rework:implementation" label. Do not create a new ticket for the same work. The label is what triggers the rework classification — without it, the reopened ticket will not be counted as rework.
- Review what caused rework: After fixing the issue, note what was missed. This information helps the team improve review processes.

### How Reliability Appears on the Dashboard

- KPI Strip (top): Shows the team-wide reliability percentage with a NOT ACTIVE badge (currently).
- Reliability Tab: A log of all rework events, showing which tickets were reopened and when. This tab is available for inspection even though the KPI is not yet active.
- Member Cards: When activated, each card will show the person's individual reliability percentage.

## THE TICKET LIFECYCLE — FROM CREATION TO KPI

> Complete data flow from the moment a ticket is created in Linear through to its appearance on the KPI dashboard.

### Phase 1 — Ticket Creation in Linear

When a TSA creates or is assigned a ticket in Linear, the following fields are set (or should be set) at creation time.

- Title: Should follow the convention [CustomerName] Description. The bracket prefix is how the system identifies which customer the ticket belongs to. Example: [Gong] Fix data pipeline for contacts. If there is no bracket prefix, the system falls back to the Linear project name and then labels to identify the customer.
- Assignee: Must be one of the five KPI team members. Unassigned tickets are invisible to the KPI system.
- Due Date: The ETA. This is the single most important field for KPI 1. Set it at creation or as soon as the work is planned.
- Status: Typically starts as Todo or Backlog. The status progression is what the system tracks for velocity and rework.
- Project: Associates the ticket with a customer project. Used as fallback for customer identification when the title has no bracket prefix.
- Labels: Optional but impactful. "rework:implementation" marks rework for KPI 3. Note: B.B.C exclusion works via the status field, not labels — see Operational Checklist for KPI 1.

### Phase 2 — Work in Progress

When a TSA begins working on the ticket.

- Move status to In Progress: This sets the startedAt timestamp in Linear, which is the start of the velocity clock for KPI 2.
- The ticket is now visible as "active" on the dashboard. It appears in the member's active count and in the Scrum Panel tab for standup reports.
- If the ticket has a dueDate, it is now being tracked for on-time delivery (KPI 1). If the current date passes the dueDate while the ticket is still In Progress, it becomes Late.

### Phase 3 — Delivery

When the implementation is complete.

- Move status to In Review: This is the recommended flow. Moving to In Review creates the deliveryDate for KPI 2 (velocity) and is the timestamp used for on-time/late determination in KPI 1.
- Alternatively, move directly to Done: This also creates a delivery timestamp, but skipping In Review means there is no review step recorded.
- The system records the first transition to In Review or Done as the delivery date. If the ticket goes through both, the earlier date (In Review) is used.

### Phase 4 — Review and Closure

During review.

- If someone else is assigned as reviewer: The system detects this reassignment. The original implementor retains "ownership" for KPI purposes. The reviewer's work does not count against the implementor's velocity.
- Move to Done: The ticket is now complete. KPI 1 determines On Time or Late. KPI 2 records the velocity. The ticket appears in the Done count on the member's card.

### Phase 5 — Rework (if applicable)

If the ticket needs to be reopened.

- Move from Done back to In Progress AND apply the "rework:implementation" label: The label is what triggers the rework classification. Without it, reopening a ticket does not count as rework. This was changed from the previous behavior (which detected rework automatically from status transitions) to eliminate false positives from accidental status changes.
- When the fix is complete, move back to In Review and then Done: The system uses the last Done date (not the first) when rework is detected, ensuring the final delivery is what gets measured.

### Phase 6 — Data Pipeline

The KPI system processes tickets through a four-step automated pipeline. It runs daily at 09:00 (weekdays) via auto-refresh, and can be triggered manually via the system tray icon at any time.

- Step 1 — Refresh Linear Cache: Fetches all issues for the five KPI team members from the Linear GraphQL API. Queries by both assignee and creator to catch reassigned tickets. Saves to a unified JSON cache (~1177 issues across all teams).
- Step 2 — Merge Data: Combines the Linear cache with the frozen Sheets backlog (backlog is preserved for historical reference but excluded from KPI calculations). Deduplicates tickets. Applies ownership logic (original assignee retains ownership when reassigned during review). Extracts history-based fields (deliveryDate, originalEta, reviewer delay). Rework detection is label-based only (checks for "rework:implementation" label).
- Step 3 — Normalize: Fixes data quality issues (date formats, customer name normalization, category classification). Recalculates all performance labels using the activity-based formula. Detects and handles admin-closed tickets.
- Step 4 — Build Dashboard: Generates the self-contained HTML dashboard (~990KB) with all charts, tables, and interactive filters. Copies to serve directory for immediate availability via local HTTP and ngrok.

The system tray provides two manual options: "Refresh & Rebuild (Linear API)" runs the full 4-step pipeline including fresh data from the API (~30s), while "Quick Rebuild (cached data)" skips Step 1 and rebuilds from the existing cache (<1s). Both send a Windows toast notification on completion.

## DATA INTEGRITY RULES

> These rules ensure the KPI calculations are accurate and fair. Each rule is coded with a D.LIE identifier for traceability back to the codebase.

### Original ETA as Baseline (calc_perf_with_history)

The system uses the ORIGINAL ETA — the first dueDate ever committed for a ticket — as the baseline for the on-time/late comparison. The fallback chain is: originalEta (first ETA from history) then finalEta (current/last dueDate from history) then eta (raw dueDate field). Changing a dueDate after the initial commitment does not change what the system measures against. This is by design: the KPI measures the accuracy of the initial estimate.

### Ticket Ownership (D.LIE23)

When a ticket is reassigned during or after In Review, the original assignee (the implementor) retains ownership for KPI purposes. The system identifies the original assignee by scanning the ticket's history — the first person ever assigned to the ticket is the owner. If the history shows a fromAssigneeId on the first assignment event, that person is the original owner. This prevents the reviewer from being penalized for the implementor's delivery timing.

### Delivery Date (D.LIE14)

The delivery date is NOT the Linear completedAt field. It is the timestamp of the first transition to In Review or Done, extracted from the ticket's full history. This is more accurate because completedAt may be set days after the actual delivery if the reviewer takes time to close the ticket. When rework is detected, the delivery date switches to the LAST Done date (not the first) to reflect the final delivery after the rework cycle.

### Admin-Close Detection (D.LIE15)

Two patterns are detected and auto-classified. Pattern 1: ticket is Done but has no startedAt, no deliveryDate, and no inReviewDate — a pure admin close. Pattern 2: ticket is Done, createdAt equals dueDate (same day), no In Review step, no startedAt, and at most 1 ETA change — a spreadsheet migration that was closed in Linear. Both patterns get classified as On Time (if ETA exists) or N/A (if no ETA). This prevents bulk-closed tickets from inflating the Late count.

### Parent Ticket Exclusion (D.LIE19)

Parent tickets that have subtasks are excluded from all KPIs. The parent is a coordination artifact. The subtasks contain the real work. Counting both would double-count effort.

### Blocked By Customer (D.LIE10)

Tickets with status B.B.C (or variants: B.B.C., BBC, bbc, Blocked) are excluded from the on-time/late calculation. The delay is outside the TSA's control. IMPORTANT: this is a STATUS-level check, not a label-level check. In the current Linear workflow, the practical equivalent is the Paused status, which also gets excluded (as "On Hold").

### Rework Detection (D.LIE20, D.LIE21)

Rework is detected exclusively through the "rework:implementation" label in Linear. The previous automatic detection (based on Done → In Progress status transitions) was removed due to false positives — accidental status changes (e.g., marking Done and reverting within minutes) were incorrectly classified as rework.

The history-based transition data (Done → In Progress/Todo/Backlog) is still collected for diagnostic/audit purposes and is available in the data as `reworkDetected`, but it does NOT set the `rework` field or affect any KPI calculation.

Reassignment at In Review remains normal workflow — implementor hands off to reviewer. A reassignment where fromAssigneeId differs from toAssigneeId after the In Review date is flagged as reassignedInReview (normal), not rework.

### Sheets Deduplication (D.LIE22)

When a ticket exists in both the frozen Google Sheets backlog and the Linear cache, the Linear version replaces the Sheets version. This prevents double-counting tickets that were migrated from Sheets to Linear.

### Retroactive ETA Detection

If a ticket's dueDate exactly matches its deliveryDate and there is only one ETA change in history, the system flags it as retroactiveEta. This means the date was likely set after delivery to appear On Time. The flag is visible in the data for auditing but does not currently change the KPI calculation.

### ETA Coverage (D.LIE12)

Each member card on the dashboard shows ETA Coverage — the percentage of their ACTIVE tickets (In Progress, In Review, Production QA, Blocked, Refinement, Ready to Deploy, B.B.C) that have a dueDate set. This is a real-time snapshot of the person's current active workload, not a historical metric filtered by week. Low coverage means the TSA has active work without committed ETAs, which reduces KPI 1 visibility. The team target is greater than 80 percent ETA coverage.

IMPORTANT: ETA Coverage is calculated from ALL active Linear tickets for the person, regardless of which week or month filter is selected on the dashboard. It excludes spreadsheet data and uses the raw dataset. If a TSA adds ETAs to their tickets in Linear, the change will appear on the dashboard after the next refresh (daily at 09:00 or manual via tray icon).

## STATUS FLOW AND KPI IMPACT

> Visual mapping of Linear statuses to KPI behavior.

```
Triage ──→ Backlog ──→ Todo ──→ In Progress ──→ In Review ──→ Done
  │           │          │          │                │           │
  │           │          │          │                │           ├─→ KPI 1: On Time or Late
  │           │          │          │                │           ├─→ KPI 2: Velocity recorded
  │           │          │          │                │           └─→ KPI 3: Clean (no rework)
  │           │          │          │                │
  │           │          │          │                └─→ deliveryDate captured (first transition here)
  │           │          │          │
  │           │          │          └─→ startedAt captured (velocity clock starts)
  │           │          │
  └───────────┴──────────┘─→ No ETA + these statuses = "Not Started" (excluded)

Done ──→ In Progress (reopened) + label "rework:implementation" = REWORK (KPI 3)
Done ──→ In Review ──→ Done (re-review) = normal, not rework
Done ──→ Canceled = N/A (decision, not rework)
In Review ──→ In Progress (review rejection) = NOT rework, deliveryDate unchanged

Canceled / Duplicate = excluded from all KPIs (N/A)
Paused / On Hold = excluded from on-time/late (On Hold label)
B.B.C (status) = excluded from on-time/late (Blocked label)
```

### Performance Label Assignment

Each ticket receives exactly one performance label based on this priority chain.

- Canceled or Duplicate status: N/A
- B.B.C or Blocked status: Blocked
- Paused or On Hold status: On Hold
- No ETA + Not Started status (Triage/Backlog/Todo): Not Started
- No ETA + any other status + category=External: No ETA (D.LIE26)
- No ETA + any other status + category=Internal (or empty): N/A (D.LIE26)
- Admin-Closed (Pattern 1 or 2): On Time (if ETA exists), N/A (if no ETA)
- Has deliveryDate: On Time (if delivery ≤ original ETA + 1 business day) or Late (D.LIE27)
- Has inReviewDate but no deliveryDate: On Time or Late based on inReviewDate vs ETA + 1 business day (D.LIE27)
- In Progress with ETA in the past: Late
- In Progress with ETA in the future: On Track

## CLASSIFICATION RULES

> How tickets are categorized as External (customer work) or Internal.

### Customer Identification

The system identifies customers through a priority chain.

- First: Title bracket prefix. [Gong] Fix pipeline extracts customer Gong.
- Second: Linear project name. If the title has no brackets, the project is mapped to a customer.
- Third: Labels. If neither title nor project identifies a customer, labels like QBO, Gong, Archer are checked.

### External vs Internal

- External: Any ticket associated with a real customer (QuickBooks, Gong, Archer, Apollo, Bill, CurbWaste, etc.). These are customer-facing implementation work.
- Internal: Tickets associated with TestBox operations, tooling, improvements, and non-customer work (TBX, Waki, Routine, General, DE Team, etc.).

The dashboard allows filtering by category (All, External, Internal) and by specific customer. This lets stakeholders focus on the metrics most relevant to their context.

## READING THE DASHBOARD

> A guide for interpreting each section of the KPI dashboard.

### Filters

The dashboard has three filter controls that dynamically recalculate all KPIs and charts.

- Person filter: Show data for a specific team member or "All" for the full team.
- Month filter: Restrict to a specific calendar month based on the ticket's dateAdd (creation date).
- Segment filter: All (everything), External (customer-facing work only), or Internal (tooling, operations, non-customer work).

All three filters are AND-combined. Selecting "Alexandra" + "March" + "External" shows only Alexandra's external customer tickets created in March.

### Week Format

The heatmap uses a custom week format: YY-MM W.N where W1 covers days 1-7, W2 covers 8-14, W3 covers 15-21, W4 covers 22-28, and W5 covers 29-31. This is NOT ISO week numbering. Each row in the heatmap shows Person and Date Range (Monday-Friday of that week).

### KPI Strip (Top Bar)

The three KPI cells at the top show the team-wide metrics with real-time calculation based on the current filter selection (person, month, segment). Each cell shows the metric value, sample size (n), and a colored badge (pass/warn/fail).

### Member Cards Tab

Individual performance cards for each team member. Each card shows total tickets, active tickets, completed tickets, On Time count, Late count, accuracy percentage, ETA coverage, and a breakdown by status. The colors (green, yellow, red) on each card correspond to the same pass/warn/fail thresholds as the KPIs.

### ETA Accuracy Heatmap

A Person by Week grid showing green cells (on time) and red cells (late). This visualization makes temporal patterns visible. Look for consistent late columns (a specific week where many people were late, suggesting an event or overcommitment) or consistent late rows (a specific person who may need support).

### Execution Time Chart

Bar chart showing average velocity per person. Lower bars are better. This is the visual representation of KPI 2.

### Reliability Tab

Log of rework events. Currently marked NOT ACTIVE but data is being collected. When activated, this tab will show which tickets were reopened, when, and by whom.

### Team Activity Heatmap

Volume of tasks per person per week. This is not a KPI but provides context. A person with high volume and high accuracy is performing well. A person with high volume and low accuracy may be overloaded.

### Scrum Panel Tab

Pre-formatted standup text organized by customer, with copy-to-clipboard functionality. This tab shows ALL tickets (both Internal and External) for each TSA from Linear — it is intentionally unfiltered by category so that the full workload is visible for standup purposes. The Scrum Panel is for daily operations and does not directly affect KPI calculations, but it reflects the complete workload that feeds into them.

### Insights Tab

The Insights tab provides deeper analytical views including Organic Accuracy — a variant of ETA Accuracy that excludes tickets flagged as retroactiveEta. This surfaces how much of the team's on-time percentage is attributable to ETAs that were set after delivery. Key elements:

- Total Accuracy vs Organic Accuracy per person, with the inflation gap between them.
- A configurable "retroactive mode" selector (any retroactive, post-delivery changes only, 2+ ETA changes) to tune what counts as gaming.
- Trend analysis showing accuracy slopes over configurable week windows.
- Late streak detection for consecutive weeks with high late percentages.

If Organic Accuracy is significantly lower than Total Accuracy, it indicates systematic ETA inflation that should be addressed.

### Gantt Chart

Timeline visualization showing actual vs projected delivery for implementation projects. This provides a project-level view that complements the ticket-level KPIs.

## QUICK REFERENCE TABLE

> Summary of all three KPIs for fast lookup.

| Attribute | KPI 1 — ETA Accuracy | KPI 2 — Impl. Velocity | KPI 3 — Impl. Reliability |
|---|---|---|---|
| Question answered | Do we deliver on time? | How fast do we deliver? | Do we deliver it right? |
| Formula | On Time / (On Time + Late) | Avg(delivery - start) days | Done without rework / Total Done |
| Target | Greater than 90% | Less than 28 days | Greater than 90% |
| Warning threshold | 80-89% | 29-42 days | 85-89% |
| Fail threshold | Below 80% | Above 42 days | Below 85% |
| Status | ACTIVE | ACTIVE | NOT ACTIVE |
| Key Linear field | dueDate | startedAt, status transitions | Label rework:implementation (sole trigger) |
| Excluded | No ETA, Canceled, B.B.C (status), Paused, Parent tickets, Not Started, Admin-Closed | No startedAt, No deliveryDate, Canceled, Parent tickets | Canceled, Parent tickets |
| Dashboard view | Heatmap, Member Cards, KPI Strip | Execution Time Chart, KPI Strip | Reliability Tab, KPI Strip |

## GLOSSARY

- ETA: Estimated Time of Arrival. In this context, the dueDate field in Linear — the date by which a ticket is committed to be delivered.
- Original ETA: The first dueDate ever set for a ticket, extracted from the ticket's history. This is what KPI 1 compares against, not the current dueDate. If no ETA change exists in history, the current dueDate is used.
- Delivery Date: The date when a ticket first reached In Review or Done status, extracted from the ticket's history. Not the same as Linear's completedAt field. When rework is detected, the LAST Done date is used instead.
- On Time: A ticket where deliveryDate is on or before the original ETA.
- Late: A ticket where deliveryDate is after the original ETA.
- On Track: A ticket currently in progress whose ETA has not yet passed.
- On Hold: Performance label for tickets in Paused or On Hold status. Excluded from KPI calculations.
- B.B.C (Blocked By Customer): A status value (not a label) indicating the ticket is waiting on customer action. Excluded from the on-time/late calculation. Detected via the status field with variants: B.B.C, B.B.C., BBC, bbc, Blocked.
- Rework: A ticket explicitly marked with the "rework:implementation" label in Linear, indicating the work was incomplete or defective and needed to be reopened. Previous versions also used automatic history-based detection (Done → In Progress transitions), but this was removed due to false positives from accidental status changes.
- ETA Coverage: The percentage of a person's tickets that have a dueDate set. Higher coverage means more reliable KPI 1 calculations. Team target: greater than 80 percent.
- Retroactive ETA: A dueDate that was set after delivery, typically matching the delivery date exactly with at most 1 ETA change in history. Flagged as potentially gaming the metric. The dashboard uses this flag to compute Organic Accuracy (excluding these tickets) in the Insights tab.
- Organic Accuracy: ETA Accuracy calculated excluding tickets flagged as retroactiveEta. Shown in the Insights tab alongside total accuracy to reveal ETA inflation. The gap between Total and Organic accuracy is the inflation percentage.
- Admin-Closed: A ticket marked Done without ever being started (Pattern 1) or a migrated ticket where createdAt equals dueDate with no real work activity (Pattern 2). Auto-classified as On Time or N/A.
- Parent Ticket: A Linear ticket that has subtasks (child tickets). Excluded from all KPIs because the real work lives in the subtasks.
- Velocity: The number of calendar days between startedAt and deliveryDate for a completed ticket. Uses calendar days, not business days.
- Reviewer Delay: The number of days between In Review and Done. Not a KPI, but tracked as a quality signal. Displayed on the dashboard.
- Pipeline: The automated four-step process (Refresh, Merge, Normalize, Build) that transforms Linear data into the KPI dashboard. Runs daily at 09:00 on weekdays.
- NOT ACTIVE: A KPI status indicating the metric is being tracked passively but not yet used for performance evaluation. Currently applies to KPI 3 (Reliability) until consistent use of the rework:implementation label is confirmed across the team.
- State ID: Internal Linear identifier for workflow statuses. Each team has unique state IDs for the same status names. The system maps IDs to names using a hardcoded table.

## KNOWN LIMITATIONS

> Current system constraints that affect data accuracy.

- Cross-team tickets: If a KPI member is assigned a ticket on a team other than Raccoons (e.g., a shared or company-wide team), the ticket IS fetched and tracked. However, the state IDs for that team may not be recognized, meaning delivery dates and rework detection may not work correctly. The system prints a warning for unknown state IDs during processing.
- Calendar days: Velocity (KPI 2) is measured in calendar days, not business days. A ticket started on Friday and delivered on Monday shows 3 days, even though only 1 business day elapsed. Weekends and holidays are not excluded.
- Rework label adoption: KPI 3 relies exclusively on the "rework:implementation" label. Automatic history-based detection (Done → In Progress) was removed to eliminate false positives. If the team does not apply the label when reopening tickets, rework will not be detected. Similarly, if rework is addressed by creating a new ticket instead of reopening the original, it will not be tracked.
- ETA coverage variability: Some members may have low ETA coverage (few tickets with dueDate), making their KPI 1 percentage statistically unreliable. There is no minimum threshold enforced.
- Spreadsheet backlog: Historical data from Google Sheets is frozen and completely excluded from all KPI calculations. It is retained in the dataset for historical reference only (128 records). All KPI metrics, heatmaps, member cards, and charts use exclusively Linear data. The Scrum Panel also filters to Linear-only data.
- Reviewer delay is tracked but NOT a KPI: The time between In Review and Done is measured and displayed but does not factor into any KPI calculation.

## OPEN QUESTIONS

- When will KPI 3 (Implementation Reliability) be activated? The rework:implementation label is now the sole detection method. KPI 3 will be activated once consistent labeling is confirmed across the team. Currently, 5 tickets have this label (1 Carlos, 4 Diego) — adoption is growing.
- Should ETA Coverage have a minimum threshold for KPI 1 to be considered valid? For example, if a person has only 4 tickets with dueDate out of 50, their accuracy percentage may not be meaningful.
- Should retroactive ETAs be excluded from KPI 1 entirely, or just flagged? Currently they are flagged but still counted as On Time.
- Should velocity exclude weekends and holidays? Currently it uses calendar days, which means a ticket started on Friday and delivered on Monday shows as 3 days even though only 1 business day elapsed.
- Should there be a minimum ticket count threshold per person per period for the KPIs to be reported? Small sample sizes can produce misleading percentages.
