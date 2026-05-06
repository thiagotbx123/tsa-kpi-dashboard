"""Milestone Health Engine — Scrum of Scrums v2

Aggregates Linear issues into (TSA, project, milestone) buckets and
computes a health status (green/yellow/red) per bucket.

Input:   ../_kpi_all_members.json  (produced by refresh_linear_cache.py)
Output:  _milestone_health.json    (feed for scrum_digest_builder.py)

Health rules:
  RED    = has overdue issue  (dueDate < today AND status not in closed)
         | status == 'Blocked' or 'Blocked Internal'
  YELLOW = status == 'Blocked by Customer'
         | 'Paused'
         | earliest dueDate within 3 days AND >30% of issues still open
  GREEN  = otherwise

Usage:  python kpi/milestone_health_engine.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json
from collections import defaultdict
from datetime import datetime, date, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, '..')
CACHE = os.path.join(ROOT, '_kpi_all_members.json')
OUT = os.path.join(SCRIPT_DIR, '_milestone_health.json')

sys.path.insert(0, SCRIPT_DIR)
from team_config import KPI_MEMBERS

OPEN_STATES = {
    'In Progress', 'Refinement', 'Todo', 'Triage', 'Production QA',
    'Needs Review', 'In Review', 'Blocked by Customer', 'Waiting On Release',
    'Blocked', 'Ready for deploy', 'Refined', 'Blocked Internal',
    'Staging QA', 'Ready for Team Grooming', 'Paused', 'Backlog',
}
CLOSED_STATES = {'Done', 'Canceled', 'Duplicate'}
RED_STATES = {'Blocked', 'Blocked Internal'}
YELLOW_STATES = {'Blocked by Customer', 'Paused'}


def parse_due(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None


def classify_bucket(issues, today):
    """Returns dict with status, reasons[], metrics."""
    open_issues = [i for i in issues if i.get('status') in OPEN_STATES]
    closed_issues = [i for i in issues if i.get('status') in CLOSED_STATES]
    total = len(issues)

    overdue = []
    soon = []
    earliest_due = None
    state_counts = defaultdict(int)

    for i in open_issues:
        state_counts[i.get('status', '')] += 1
        due = parse_due(i.get('dueDate'))
        if due:
            delta = (due - today).days
            if delta < 0:
                overdue.append((delta, i))
            elif delta <= 3:
                soon.append((delta, i))
            if earliest_due is None or due < earliest_due:
                earliest_due = due

    reasons = []
    status = 'green'

    if overdue:
        status = 'red'
        reasons.append(f"{len(overdue)} overdue ({min(d for d,_ in overdue)}d worst)")

    blocked_int = sum(1 for i in open_issues if i.get('status') in RED_STATES)
    if blocked_int:
        status = 'red'
        reasons.append(f"{blocked_int} blocked internally")

    if status != 'red':
        blocked_cust = sum(1 for i in open_issues if i.get('status') in YELLOW_STATES)
        if blocked_cust:
            status = 'yellow'
            reasons.append(f"{blocked_cust} blocked by customer / paused")

    if status == 'green' and soon:
        pct_open = len(open_issues) / total if total else 0
        if pct_open > 0.3:
            status = 'yellow'
            reasons.append(f"{len(soon)} due in ≤3d, {int(pct_open*100)}% still open")

    return {
        'status': status,
        'reasons': reasons,
        'metrics': {
            'total': total,
            'open': len(open_issues),
            'closed': len(closed_issues),
            'overdue': len(overdue),
            'soon': len(soon),
            'earliest_due': earliest_due.isoformat() if earliest_due else None,
            'state_counts': dict(state_counts),
        },
        'open_issues': [{
            'id': i['id'],
            'title': i.get('title', ''),
            'url': i.get('url', ''),
            'status': i.get('status', ''),
            'dueDate': i.get('dueDate'),
            'updatedAt': i.get('updatedAt'),
            'labels': i.get('labels', []),
        } for i in open_issues],
        'recent_done': _recent_done(closed_issues, today),
    }


def _recent_done(issues, today, days=14):
    from datetime import timedelta
    cutoff = (today - timedelta(days=days)).isoformat()
    out = []
    for i in issues:
        c = i.get('completedAt')
        if c and c[:10] >= cutoff:
            out.append({
                'id': i['id'],
                'title': i.get('title', ''),
                'completedAt': c,
            })
    return out


def derive_impact(project_name, milestone_name, bucket_status):
    """Pragmatic placeholder impact statement.
    PRODUCTION: should read from Linear project.description 'Impact:' line.
    This draft uses a mapping so we can ship a shadow-mode digest today.
    """
    IMPACT_MAP = {
        'Quickbooks Implementation': 'Intuit release train — delay slips GA date for all QBO stories.',
        'QBO': 'QuickBooks demo fidelity — affects buyer conversion in Intuit pipeline.',
        '[WFS] Workforce Solutions': 'Intuit WFS deal — SOW lock gates $55K+ ARR implementation.',
        'Gong': 'Gong customer retention — blocks sandbox self-service for sales team.',
        'Gong Implementation': 'Gong partner demo enablement — GTM alignment risk if slipped.',
        'Mailchimp': 'Mailchimp adoption tracking — feeds QBR narrative with customer.',
        'Siteimprove': 'Siteimprove content blueprint — unblocks accessibility demo story.',
        '[Gem] Integration': 'Gem recruiting demo — pre-sales pipeline readiness.',
        '[People.ai] Integration': 'People.ai churn prevention — Phase 1 is renewal-critical.',
        '[Zuper] Integration': 'Zuper field-service demo — new logo onboarding.',
        '[Tabs] Integration': 'Tabs renewal story design — 3 demo scenarios feed customer validation.',
        '[Tropic] Implementation': 'Tropic data quality — avoid demo incidents during instance testing.',
        '[Brevo] Integration': 'Brevo sandbox reliability — customer-reported incidents active.',
        '[Gainsight] Staircase AI Integration': 'Staircase AI renewals — SFDC sync impacts customer reporting.',
        '[SiteImprove] Integration': 'Siteimprove demo flow — accessibility story scope.',
        'Archer': 'Archer GRC demo — Domain-by-domain data ingestion.',
        '[Internal] TSA Operations': 'TSA ops enablement — dashboards, automation, knowledge systems.',
        'Bill': 'Bill implementation scoping — $50K+ fintech account in scope phase.',
        'Outreach Integration': 'Outreach sales-engagement demo — Task Force priority.',
        'Staircase': 'Staircase data operations — customer-visible data corrections.',
        'Apollo': 'Apollo demo environment — sales intelligence use-case.',
        '[Monarch] Integration': 'Monarch AP/AR demo — integration hardening.',
    }
    base = IMPACT_MAP.get(project_name, f'{project_name} project health.')
    return base


def main():
    data = json.load(open(CACHE, encoding='utf-8'))
    today = date.today()

    # Group by (assigneeId, project, milestone_name)
    buckets = defaultdict(list)
    for i in data:
        aid = i.get('assigneeId')
        if aid not in KPI_MEMBERS:
            continue
        proj = i.get('project') or '(no project)'
        mi = (i.get('projectMilestone') or {}).get('name')
        key = (aid, i.get('assignee', ''), proj, mi)
        buckets[key].append(i)

    results = []
    for (aid, aname, proj, mi), issues in buckets.items():
        # Skip buckets with zero open AND nothing completed in last 14d
        open_count = sum(1 for i in issues if i.get('status') in OPEN_STATES)
        if open_count == 0:
            from datetime import timedelta
            cutoff = (today - timedelta(days=14)).isoformat()
            recent = [i for i in issues
                      if i.get('completedAt') and i['completedAt'][:10] >= cutoff]
            if not recent:
                continue

        cls = classify_bucket(issues, today)
        if open_count == 0 and cls['metrics']['closed'] > 0:
            cls['status'] = 'done'
            cls['reasons'] = [f"{cls['metrics']['closed']} shipped"]

        results.append({
            'tsa_id': aid,
            'tsa_name': aname,
            'project': proj,
            'milestone': mi,
            'unit': 'milestone' if mi else 'project',
            'impact': derive_impact(proj, mi, cls['status']),
            **cls,
        })

    # Sort: by TSA, then red > yellow > green > done, then by open count desc
    order = {'red': 0, 'yellow': 1, 'green': 2, 'done': 3}
    results.sort(key=lambda r: (r['tsa_name'], order.get(r['status'], 9), -r['metrics']['open']))

    out = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'date': today.isoformat(),
        'total_buckets': len(results),
        'by_status': {s: sum(1 for r in results if r['status'] == s) for s in ('red', 'yellow', 'green', 'done')},
        'buckets': results,
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"Milestone Health Engine — {today}")
    print(f"  Total buckets: {out['total_buckets']}")
    print(f"  By status: {out['by_status']}")
    print(f"  Output: {OUT}")


if __name__ == '__main__':
    main()
