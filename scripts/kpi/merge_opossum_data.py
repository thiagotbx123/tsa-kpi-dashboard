"""Merge Linear data for ALL KPI team members into _dashboard_data.json.

Sources:
  - _kpi_all_members.json: Unified cache of all KPI member issues from Linear API
  - Spreadsheet data stays as historical backlog (not replaced for members now in Linear)

Usage: python kpi/merge_opossum_data.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re
from datetime import datetime, timedelta
from collections import Counter

SCRIPT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '_dashboard_data.json')
OPOSSUM_CACHE = os.path.join(SCRIPT_DIR, '..', '_opossum_raw.json')
RACCOONS_KPI_CACHE = os.path.join(SCRIPT_DIR, '..', '_raccoons_kpi.json')
RACCOONS_THAIS_CACHE = os.path.join(SCRIPT_DIR, '..', '_raccoons_thais.json')  # backward compat
OUTPUT_PATH = DATA_PATH

# Workflow State IDs → Names (for decoding history entries)
STATE_NAMES = {
    # Opossum team states
    'c88c5a3a-2203-4a15-9801-51befb603c39': 'Triage',
    '828cf5f3-d5f2-40d7-bc5b-4512e37171f0': 'Backlog',
    '7d5ad714-3623-4ebf-8a6b-fb6cca398643': 'Todo',
    'c867261b-81c1-4b69-8f2b-0bfc836a3407': 'In Progress',
    '3f6d0e12-8224-4329-954f-e9146816732f': 'In Review',
    '9315b082-63b4-4e74-a759-1c7b1403a2f8': 'Done',
    'e3d6167b-3328-42cd-9e22-d6ca18f003f3': 'Canceled',
    'fe43e265-1b90-4dc1-b8c5-bc6946dc6545': 'Duplicate',
    # Raccoons team states
    'ccc98f62-bc2a-475a-bcc8-0cdf0c81f8fc': 'Triage',
    '0a00ef8b-f3e2-4b1b-8413-1961c91fe495': 'Backlog',
    'ab5844ed-4edd-4d84-99fc-34ab37859486': 'Todo',
    '8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b': 'In Progress',
    '89e4c72d-57aa-4774-8cf0-b00ee103d17c': 'In Review',
    '6e10418c-81fe-467d-aed3-d4c75577d16e': 'Done',
    '97ef043e-ccb7-4e2a-b75b-7542ef198abc': 'Canceled',
    'bfe7e0e1-d403-4897-996a-5f839305e9e8': 'Duplicate',
    'c7a6728a-dee7-4e2b-a60f-476e699d4b54': 'Paused',
}

# Terminal/delivery states
DELIVERY_STATES = {'In Review', 'Done'}

# A19: Accumulate unknown state IDs across all extract_history_fields calls
_all_unknown_state_ids = set()


def extract_history_fields(issue):
    """Extract activity-based dates from issue history.

    Returns dict with:
      deliveryDate: date when status FIRST moved to In Review or Done
      originalEta: first dueDate ever set (from history)
      finalEta: current/last dueDate
      reviewerDelay: days between In Review → Done (if applicable)
      etaChanges: number of times dueDate was changed
      inReviewDate: date when status moved to In Review (if applicable)
      statusChangedAt: date of the LAST transition to the current status
    """
    history = issue.get('history', [])
    current_status = issue.get('status', '')
    result = {
        'deliveryDate': None,
        'originalEta': None,
        'finalEta': issue.get('dueDate') or None,
        'reviewerDelay': None,
        'etaChanges': 0,
        'inReviewDate': None,
        'statusChangedAt': None,
        'reworkDetected': False,
        'reassignedInReview': False,
        'reviewAssignee': None,
        'originalAssigneeId': None,    # First person assigned to this ticket
        'originalAssigneeName': None,
        'lastActorId': None,           # Actor of the most recent history event
        'lastActorName': None,
    }

    if not history:
        return result

    # Sort history by createdAt ascending
    sorted_history = sorted(history, key=lambda h: h.get('createdAt', ''))

    # Track first delivery date (In Review or Done)
    first_delivery_date = None
    in_review_date = None
    done_date = None

    # A19: Use module-level set so unknown IDs accumulate across all calls (summary printed after loop)
    for h in sorted_history:
        state_id = h.get('toStateId', '')
        to_state = STATE_NAMES.get(state_id, '')
        if not to_state and state_id:
            _all_unknown_state_ids.add(state_id)
        ts = h.get('createdAt', '')[:10]

        # Track last transition to current status (for age-in-status on all statuses)
        # Match by name when known, or track last state change for unknown teams
        if state_id and ts:
            if to_state == current_status:
                result['statusChangedAt'] = ts
            elif not to_state:
                # Unknown team state — track the last state transition as best guess
                result['_lastStateChangeAt'] = ts

        # Track first time moved to In Review or Done
        if to_state in DELIVERY_STATES and first_delivery_date is None and ts:
            first_delivery_date = ts

        if to_state == 'In Review' and in_review_date is None and ts:
            in_review_date = ts

        if to_state == 'Done' and ts:
            done_date = ts  # last Done date

        # D.LIE20: Detect rework — Done → In Progress means task was reopened
        from_state = STATE_NAMES.get(h.get('fromStateId', ''), '')
        if from_state == 'Done' and to_state in ('In Progress', 'Todo', 'Backlog'):
            result['reworkDetected'] = True

        # D.LIE23: Track original assignee (first person ever assigned).
        # History is sorted oldest-first. The FIRST event that touches assignee fields
        # tells us who was there before the reassignment.
        # - If fromAssigneeId is set: this is a reassignment. The fromAssignee IS the
        #   original (they were assigned before this event moved the ticket to someone else).
        # - If fromAssigneeId is absent: this is the initial assignment (no prior assignee),
        #   so toAssigneeId is the original.
        if h.get('toAssigneeId') and result['originalAssigneeId'] is None:
            if h.get('fromAssigneeId'):
                result['originalAssigneeId'] = h['fromAssigneeId']
                result['originalAssigneeName'] = h.get('fromAssigneeName', '')
            else:
                result['originalAssigneeId'] = h['toAssigneeId']
                result['originalAssigneeName'] = h.get('toAssigneeName', '')

        # D.LIE21: Detect reassignment at/after In Review
        # When person A moves to In Review and reassigns to person B,
        # person A delivered (delivery = In Review date), person B is now the reviewer
        if h.get('toAssigneeId') and h.get('fromAssigneeId') and h['toAssigneeId'] != h['fromAssigneeId']:
            # Was this reassignment after In Review?
            if in_review_date and ts >= in_review_date:
                result['reassignedInReview'] = True
                result['reviewAssignee'] = h['toAssigneeId']

        # Track dueDate changes
        if h.get('toDueDate') is not None:
            result['etaChanges'] += 1
            # The first toDueDate in history is the original ETA
            if result['originalEta'] is None:
                # fromDueDate of the first change = original, or toDueDate if no from
                if h.get('fromDueDate'):
                    result['originalEta'] = h['fromDueDate']
                else:
                    result['originalEta'] = h['toDueDate']

    # Last actor: who made the most recent history event
    if sorted_history:
        last_event = sorted_history[-1]
        result['lastActorId'] = last_event.get('actorId', '')
        result['lastActorName'] = last_event.get('actorName', '')
        result['lastActorDate'] = last_event.get('createdAt', '')[:10]

    # A32c: When rework detected, use the LAST Done date (not first delivery date)
    if result['reworkDetected'] and done_date:
        result['deliveryDate'] = done_date
    else:
        result['deliveryDate'] = first_delivery_date
    result['inReviewDate'] = in_review_date

    # Fallback for unknown-team statuses: use last state change date
    if result['statusChangedAt'] is None and result.get('_lastStateChangeAt'):
        result['statusChangedAt'] = result['_lastStateChangeAt']
    result.pop('_lastStateChangeAt', None)

    # If no originalEta found in history, use current dueDate
    if result['originalEta'] is None:
        result['originalEta'] = result['finalEta']

    # Calculate reviewer delay (days between In Review → Done)
    if in_review_date and done_date:
        try:
            d_review = datetime.strptime(in_review_date, '%Y-%m-%d')
            d_done = datetime.strptime(done_date, '%Y-%m-%d')
            delay = (d_done - d_review).days
            if delay > 0:
                result['reviewerDelay'] = delay
        except ValueError:
            pass

    return result


# ── Load existing dashboard data ──
try:
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        existing = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print(f"No existing data at {DATA_PATH} — starting fresh")
    existing = []

# H6: Count existing Linear-sourced records before removing
old_linear = {}
for r in existing:
    if r.get('source') == 'linear':
        tsa = r.get('tsa', '?')
        old_linear[tsa] = old_linear.get(tsa, 0) + 1

# Keep spreadsheet records for ALL members (historical backlog)
# Remove ONLY Linear-sourced records (will be rebuilt from fresh API data)
existing = [r for r in existing if r.get('source') != 'linear']
print(f"Existing records (spreadsheet backlog): {len(existing)}")
if old_linear:
    print(f"  Removed Linear records: {old_linear}")

# ── Load unified KPI issues (all members, all teams) ──
import time as _time
KPI_ALL_PATH = os.path.join(SCRIPT_DIR, '..', '_kpi_all_members.json')
issues = []
for cache_path in [KPI_ALL_PATH, RACCOONS_KPI_CACHE, OPOSSUM_CACHE]:
    if os.path.exists(cache_path):
        cache_age = _time.time() - os.path.getmtime(cache_path)
        if cache_age > 86400:  # 24 hours
            print(f"  WARNING: Cache is {cache_age/3600:.0f}h old — consider running refresh_linear_cache.py")
        with open(cache_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        print(f"Linear issues loaded: {len(loaded)} from {os.path.basename(cache_path)}")
        # Deduplicate
        seen_ids = {i.get('id') for i in issues}
        for iss in loaded:
            if iss.get('id') not in seen_ids:
                issues.append(iss)
                seen_ids.add(iss.get('id'))
        break
if not issues:
    print(f"No Linear cache found — skipping")
print(f"Total Linear issues: {len(issues)}")


# ── Helper: compute week string from date ──
def date_to_week(date_str):
    """Convert YYYY-MM-DD to 'YY-MM W.N' format."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
    except ValueError:
        return None
    y = dt.year % 100
    m = dt.month
    day = dt.day
    # Custom week: W1=days 1-7, W2=8-14, W3=15-21, W4=22-28, W5=29-31. NOT ISO week.
    wn = (day - 1) // 7 + 1
    return f"{y:02d}-{m:02d} W.{wn}"


def week_range(date_str):
    """Compute week range string like '01/05 - 01/09/2026'."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
    except ValueError:
        return ""
    monday = dt - timedelta(days=dt.weekday())
    friday = monday + timedelta(days=4)
    return f"{monday.strftime('%m/%d')} - {friday.strftime('%m/%d/%Y')}"


def extract_customer(title):
    """Extract customer from [brackets] in title. Uses shared CUSTOMER_MAP."""
    m = re.match(r'\[([^\]]+)\]', title)
    if m:
        cust = m.group(1).strip()
        cust_lower = cust.lower().strip()
        if cust_lower in CUSTOMER_MAP:
            return CUSTOMER_MAP[cust_lower] or ''
        return cust
    return ''


def map_status(linear_status):
    """Map Linear status — preserve original names for accurate KPI calculation."""
    mapping = {
        'Done': 'Done',
        'In Progress': 'In Progress',
        'In Review': 'In Review',
        'Todo': 'Todo',
        'Backlog': 'Backlog',
        'Canceled': 'Canceled',
        'Triage': 'Triage',
        'Paused': 'Paused',
        'Duplicate': 'Canceled',
    }
    return mapping.get(linear_status, linear_status)


def _placeholder_perf(status):
    """A30-003: Lightweight placeholder — normalize_data.py is the single authority for perf calc.
    This only sets obvious non-calculated statuses; everything else gets '' for normalize to handle."""
    if status == 'Canceled':
        return PERF_NA
    if status in ('B.B.C', 'Blocked'):
        return PERF_BLOCKED
    if status in ('Paused', 'On Hold'):
        return PERF_ON_HOLD
    return ''


def determine_category(customer, title):
    """Determine Internal vs External.
    External = ticket belongs to a real customer implementation.
    Internal = everything else (TestBox product, tooling, ops)."""
    if not customer or customer in ('Internal', ''):
        # No customer name — check title for customer brackets
        if re.match(r'\[(Gem|Gong|QBO|Archer|Brevo|Mailchimp|Tabs|Tropic|WFS|Siteimprove|Apollo|People\.ai|Bill|BILL|CallRail)', title):
            return 'External'
        return 'Internal'
    if customer in REAL_CUSTOMERS:
        return 'External'
    return 'Internal'


def _compute_last_touch(hist_fields, comments):
    """Determine who last touched the ticket: compare history actor date vs last comment date."""
    last_hist_id = hist_fields.get('lastActorId', '')
    last_hist_name = hist_fields.get('lastActorName', '')
    last_hist_date = hist_fields.get('lastActorDate', '')

    last_comment_date = ''
    last_comment_id = ''
    last_comment_name = ''
    if comments:
        sorted_comments = sorted(comments, key=lambda c: c.get('createdAt', ''))
        if sorted_comments:
            last_c = sorted_comments[-1]
            last_comment_date = last_c.get('createdAt', '')[:10]
            last_comment_id = last_c.get('userId', '')
            last_comment_name = last_c.get('userName', '')

    # Date-aware: whoever acted MORE RECENTLY is the lastActor
    if last_comment_id and last_comment_date >= (last_hist_date or ''):
        winner_id = last_comment_id
        winner_name = last_comment_name
    else:
        winner_id = last_hist_id
        winner_name = last_hist_name

    return {
        'lastActorId': winner_id,
        'lastActorName': winner_name,
        'lastCommentById': last_comment_id,
        'lastCommentByName': last_comment_name,
        'lastCommentDate': last_comment_date,
    }


# ── Convert Linear issues to dashboard records ──
from team_config import (PERSON_MAP, PERSON_MAP_BY_ID, CUSTOMER_MAP,
                         PROJECT_TO_CUSTOMER, LABEL_TO_CUSTOMER, REAL_CUSTOMERS,
                         PERF_NA, PERF_BLOCKED, PERF_ON_HOLD)
LINEAR_TSA_NAMES = set(PERSON_MAP.values())

# D.LIE19: Identify parent tickets (have subtasks) — exclude from KPI
# Only count subtasks (the real work), not the parent (coordination)
parent_ids_with_children = set()
for iss in issues:
    pid = iss.get('parentId')
    if pid:
        parent_ids_with_children.add(pid)
print(f"Parents with subtasks (excluded from KPI): {len(parent_ids_with_children)}")

new_records = []
skipped_parents = 0
reassigned_to_original = 0
review_delivery_adjusted = 0
for iss in issues:
    # Skip parent tickets that have subtasks
    if iss.get('id') in parent_ids_with_children:
        skipped_parents += 1
        continue

    # Extract history fields first (need originalAssigneeId)
    hist_fields = extract_history_fields(iss)

    # D.LIE23: Ownership logic — who does this ticket belong to?
    # Rule: Current assignee is the owner UNLESS the ticket was reassigned
    # at/after In Review (D.LIE24 — "lent" to a reviewer, implementor still owns it).
    #   1. If reassigned during/after In Review → original assignee (implementor) owns it
    #   2. Otherwise → current assignee owns it (reassignment = real handoff)
    creator_id = iss.get('createdById', '')
    current_assignee = iss.get('assignee', '')
    current_id = iss.get('assigneeId', '')
    original_id = hist_fields.get('originalAssigneeId')

    owner_id = None
    if hist_fields.get('reassignedInReview') and original_id:
        # Reassigned at/after In Review — implementor (original) still owns it
        # KNOWN LIMITATION (P3): In A→B→C chains where B implements and C reviews,
        # originalAssigneeId=A (not B). This edge case is rare (~0 tickets currently)
        # and would require tracking "assignee at time of In Review" to fix properly.
        owner_id = original_id
    else:
        # Normal case — current assignee is the real owner
        owner_id = current_id

    if owner_id and owner_id in PERSON_MAP_BY_ID:
        tsa = PERSON_MAP_BY_ID[owner_id]
        if owner_id != current_id:
            reassigned_to_original += 1
    else:
        # Owner not in KPI team — try current assignee as fallback
        tsa = PERSON_MAP.get(current_assignee)

    if not tsa:
        continue

    title = iss.get('title', '')
    created = iss.get('createdAt', '')[:10] if iss.get('createdAt') else ''
    due = iss.get('dueDate') or ''
    completed = iss.get('completedAt', '')[:10] if iss.get('completedAt') else ''
    started_at = iss.get('startedAt', '')[:10] if iss.get('startedAt') else ''
    status = map_status(iss.get('status', ''))
    customer = extract_customer(title)
    # D.LIE18: Fallback to Linear project name when title has no [bracket] customer
    if not customer and iss.get('project'):
        proj_lower = iss['project'].lower().strip()
        customer = PROJECT_TO_CUSTOMER.get(proj_lower, iss['project'])
    if not customer:
        for lbl in iss.get('labels', []):
            if lbl in LABEL_TO_CUSTOMER:
                customer = LABEL_TO_CUSTOMER[lbl]
                break
    category = determine_category(customer, title)

    # D.LIE16: Use ETA (dueDate) for week assignment — places the task in the week
    # it was supposed to be delivered, which is what the KPI measures.
    # Falls back to startedAt, then createdAt if no ETA is set.
    week_date = due[:10] if due and len(due) >= 10 else (started_at if started_at else created)
    week = date_to_week(week_date)
    wrange = week_range(week_date)

    # A24: weekByStart — week when work actually started (for activity heatmap).
    # Uses startedAt (Linear's started date) or dateAdd (creation date) as fallback.
    # This is separate from `week` (which is ETA-based) so charts can choose either.
    start_week_date = started_at if started_at else created
    week_by_start = date_to_week(start_week_date)
    wrange_by_start = week_range(start_week_date)

    # D.LIE24+D.LIE25: In Review = implementor delivered.
    # When a ticket moves to In Review, the implementor's delivery date is the
    # In Review date — regardless of whether it was reassigned or not.
    # "In Review" means "I finished my part" for the owner.
    effective_delivery = completed
    if hist_fields.get('inReviewDate') and status in ('In Review', 'Done'):
        effective_delivery = hist_fields['inReviewDate']
        review_delivery_adjusted += 1

    perf = _placeholder_perf(status)

    # hist_fields already extracted above (for originalAssigneeId)

    # M5: Customer work = External regardless of type
    if category == 'External' and customer:
        demand = "External(Customer)"
    else:
        demand = "Internal"

    ticket_id = iss.get('id', '')
    ticket_url = iss.get('url', '')
    parent_id = iss.get('parentId', '') or ''
    pm = iss.get('projectMilestone')
    milestone = pm.get('name', '') if pm else ''

    # Detect rework: ONLY via label (D.LIE20 history kept for diagnostics only)
    raw_labels = iss.get('labels', [])
    label_names = [l.lower() if isinstance(l, str) else (l.get('name', '').lower() if isinstance(l, dict) else '') for l in raw_labels]
    has_rework_label = 'rework:implementation' in label_names
    has_rework = 'yes' if has_rework_label else ''

    # Construct URL from ID if missing
    if ticket_id and not ticket_url:
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]
        ticket_url = f"https://linear.app/testbox/issue/{ticket_id}/{slug}"

    record = {
        'tsa': tsa,
        'week': week or '',
        'weekRange': wrange,
        'focus': title,
        'status': status,
        'demandType': demand,
        'category': category,
        'customer': customer if customer != 'Internal' else '',
        'dateAdd': created,
        'eta': due,
        'delivery': effective_delivery,
        'perf': perf,
        'ticketId': ticket_id,
        'ticketUrl': ticket_url,
        'source': 'linear',
        'milestone': milestone,
        'parentId': parent_id,
        # Detect retroactive ETA: dueDate matches delivery exactly AND ticket is Done
        # This flags tickets where ETA was set after-the-fact (not a real commitment)
        'retroactiveEta': 'yes' if (status == 'Done' and due and effective_delivery
            and due[:10] == effective_delivery[:10]
            and hist_fields['etaChanges'] <= 1) else '',
        'rework': has_rework,
        'startedAt': started_at,
        'deliveryDate': hist_fields['deliveryDate'] or '',
        'originalEta': hist_fields['originalEta'] or '',
        'finalEta': hist_fields['finalEta'] or '',
        'reviewerDelay': hist_fields['reviewerDelay'],
        'etaChanges': hist_fields['etaChanges'],
        'inReviewDate': hist_fields['inReviewDate'] or '',
        'statusChangedAt': hist_fields['statusChangedAt'] or '',
        'reassignedInReview': hist_fields.get('reassignedInReview', False),
        'reviewAssignee': hist_fields.get('reviewAssignee', ''),
        'weekByStart': week_by_start or '',
        'weekRangeByStart': wrange_by_start,
        'updatedAt': (iss.get('updatedAt', '')[:10] if iss.get('updatedAt') else ''),
        'createdById': creator_id,
        'assigneeId': current_id,
        'assigneeName': current_assignee,
        # Last touch: compare last history actor vs last commenter — most recent wins
        **_compute_last_touch(hist_fields, iss.get('comments', [])),
    }
    new_records.append(record)

print(f"\nNew Linear records: {len(new_records)} (skipped {skipped_parents} parents, {reassigned_to_original} attributed to original assignee, {review_delivery_adjusted} delivery adjusted to In Review date)")

# A19: Summary of unknown state IDs encountered across all issues
if _all_unknown_state_ids:
    print(f"\n  WARNING: {len(_all_unknown_state_ids)} unknown state IDs encountered — update STATE_NAMES")
    for sid in sorted(_all_unknown_state_ids):
        print(f"    {sid}")

# H6: Validate counts per person
for tsa_name in sorted(LINEAR_TSA_NAMES):
    new_count = len([r for r in new_records if r['tsa'] == tsa_name])
    old_count = old_linear.get(tsa_name, 0)
    print(f"  {tsa_name}: {old_count} → {new_count}")
    if old_count > 0 and new_count < old_count * 0.5:
        print(f"    WARNING: {tsa_name} count dropped >50%! Check data source.")

# Stats per person
for tsa_name in sorted(LINEAR_TSA_NAMES):
    recs = [r for r in new_records if r['tsa'] == tsa_name]
    if recs:
        perfs = Counter(r['perf'] for r in recs)
        print(f"  {tsa_name}: {len(recs)} records — {dict(perfs)}")

# History analysis summary
has_delivery = [r for r in new_records if r.get('deliveryDate')]
has_eta_changes = [r for r in new_records if r.get('etaChanges', 0) > 0]
has_reviewer_delay = [r for r in new_records if r.get('reviewerDelay') is not None]
print(f"\n  History analysis:")
print(f"    Issues with deliveryDate (In Review/Done from history): {len(has_delivery)}")
print(f"    Issues with ETA changes: {len(has_eta_changes)}")
print(f"    Issues with reviewer delay (In Review → Done gap): {len(has_reviewer_delay)}")
if has_reviewer_delay:
    avg_delay = sum(r['reviewerDelay'] for r in has_reviewer_delay) / len(has_reviewer_delay)
    print(f"    Average reviewer delay: {avg_delay:.1f} days")

# ── Merge ──
merged = existing + new_records
print(f"\nMerged total: {len(merged)}")

# P5: Data integrity checkpoint — warn if record count drops >5%
_prev_count = sum(old_linear.values()) + len(existing) if old_linear else 0
if _prev_count > 0 and len(merged) < _prev_count * 0.95:
    print(f"  WARNING: Record count dropped from {_prev_count} to {len(merged)} ({len(merged)/_prev_count*100:.0f}%) — possible data loss")

# C3: Atomic write
tmp_path = OUTPUT_PATH + '.tmp'
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, OUTPUT_PATH)
print(f"Saved: {OUTPUT_PATH}")
