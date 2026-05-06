"""Scrum Reality Check — honest 3-way gap analysis.

For each scrum post in the last ~8 weeks, extract every (project, task, ETA)
line and try to match it against Linear. Produce metrics for:

  - DUPLICATION: % of Slack items that already exist in Linear with same ETA
  - LAG:         % of Slack items whose ETA is stale vs Linear's current ETA
  - GHOST:       % of Slack items with no Linear counterpart (Slack-only)
  - BLIND:       % of Linear activity (updates this week) that never hit Slack

Output: scrum_reality_check.md (human report) + .json (raw findings)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re, difflib
from collections import defaultdict, Counter
from datetime import datetime, date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, '..')
SLACK_JSON = os.path.join(SCRIPT_DIR, 'scrum_30d.json')
LINEAR = os.path.join(ROOT, '_kpi_all_members.json')
OUT_MD = os.path.join(SCRIPT_DIR, 'scrum_reality_check.md')
OUT_JSON = os.path.join(SCRIPT_DIR, 'scrum_reality_check.json')


def load_slack():
    d = json.load(open(SLACK_JSON, encoding='utf-8'))
    return d.get('messages', {}).get('matches', [])


def load_linear():
    return json.load(open(LINEAR, encoding='utf-8'))


ETA_RX = re.compile(r'ETA[: ]*\s*(\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?)', re.I)
DO_RX = re.compile(r'Do[:\s]+(.+?)(?:ETA|:|$)', re.I)
PROJECT_RX = re.compile(r'^(?:\s*)([A-Z][\w .&()\[\]\/-]{2,40})(?=\n|\s*Current Focus|\s*•)', re.M)
LINEAR_URL_RX = re.compile(r'linear\.app/testbox/issue/([A-Z]{2,5}-\d+)')
CIRCLE_RX = re.compile(r':(large_green_circle|large_yellow_circle|red_circle|white_check_mark|black_small_square):')


def parse_slack_post(text):
    """Extract structured items from a Daily Agenda post."""
    items = []
    lines = text.split('\n')
    current_project = None

    for line in lines:
        line_stripped = line.strip()
        # Detect project header lines: line that is not a bullet, contains Latin letters only,
        # is short (<=40 chars), not starting with "• " "Do:" ":black_" "[Daily"
        if re.match(r'^[A-Z][\w &.()\[\]/-]{2,40}\s*$', line_stripped) and \
           not line_stripped.startswith(('•', 'Do:', 'ETA', '[Daily', 'References', 'Blockers', 'Current Focus')):
            current_project = line_stripped
            continue
        # bullet items
        if 'Do:' in line or 'DO:' in line:
            # extract task text
            task_part = re.split(r'Do:|DO:', line, maxsplit=1)[-1]
            # ETA
            eta_match = ETA_RX.search(task_part)
            eta = eta_match.group(1) if eta_match else None
            # Linear IDs
            linear_ids = LINEAR_URL_RX.findall(line)
            # status circle
            circle = CIRCLE_RX.findall(line)
            # strip task
            task_clean = re.sub(r'ETA[: ]*\s*\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?', '', task_part)
            task_clean = re.sub(r':\w+:', '', task_clean)
            task_clean = re.sub(r'<[^>]+\|([^>]+)>', r'\1', task_clean)
            task_clean = re.sub(r'<[^>]+>', '', task_clean)
            task_clean = task_clean.strip(' :.-*')[:140]
            items.append({
                'project': current_project,
                'task': task_clean,
                'eta': eta,
                'linear_ids': linear_ids,
                'circles': circle,
                'raw': line_stripped[:200],
            })
    return items


def norm_project(name):
    if not name:
        return ''
    n = name.lower()
    n = re.sub(r'[\[\]()]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    # aliases
    aliases = {
        'qbo': 'quickbooks',
        'qbo wfs': 'wfs',
        'qbo (wfs)': 'wfs',
        'quickbooks wfs': 'wfs',
        'quickbooks (wfs)': 'wfs',
        'workforce solutions': 'wfs',
        'wfs workforce solutions': 'wfs',
        'intuit quickbooks': 'quickbooks',
        'gong implementation': 'gong',
        'peopleai': 'people.ai',
        'people.ai integration': 'people.ai',
        'gem integration': 'gem',
        'tropic implementation': 'tropic',
        'tabs integration': 'tabs',
        'brevo integration': 'brevo',
        'siteimprove': 'siteimprove',
        'gainsight': 'staircase',
        'gainsight staircase ai integration': 'staircase',
        'staircase': 'staircase',
    }
    return aliases.get(n, n)


def match_to_linear(slack_item, linear_issues, tsa_user):
    """Try to find a Linear counterpart. Returns (match_type, linear_issue|None).
    match_type: 'linear_id' | 'fuzzy_title' | 'project_only' | 'none'
    """
    # 1. Direct linear ID
    for lid in slack_item['linear_ids']:
        hit = next((i for i in linear_issues if i['id'] == lid), None)
        if hit:
            return 'linear_id', hit

    # 2. Fuzzy title within same project + assignee
    task = slack_item['task'].lower()
    if len(task) < 10:
        return 'none', None

    candidates = [
        i for i in linear_issues
        if (i.get('assignee', '').lower().startswith(tsa_user.lower())
            or tsa_user.lower() in i.get('assignee', '').lower())
    ]
    # prune by project match
    slack_proj = norm_project(slack_item.get('project') or '')
    if slack_proj:
        proj_matched = [i for i in candidates
                        if slack_proj in norm_project(i.get('project', ''))]
        if proj_matched:
            candidates = proj_matched

    best, best_ratio = None, 0.0
    for i in candidates:
        title = (i.get('title') or '').lower()
        ratio = difflib.SequenceMatcher(None, task, title).ratio()
        # bonus for word overlap
        task_words = set(re.findall(r'\w{4,}', task))
        title_words = set(re.findall(r'\w{4,}', title))
        if task_words and title_words:
            overlap = len(task_words & title_words) / max(len(task_words), 1)
            ratio = max(ratio, overlap)
        if ratio > best_ratio:
            best_ratio = ratio
            best = i

    if best_ratio >= 0.55:
        return 'fuzzy_title', best
    if slack_proj and any(slack_proj in norm_project(i.get('project', '')) for i in candidates):
        return 'project_only', None
    return 'none', None


def compute_eta_mismatch(slack_eta, linear_issue):
    """Returns (matches, slack_iso, linear_iso) — bool + the two dates."""
    if not slack_eta:
        return None, None, None
    lin_due = linear_issue.get('dueDate') if linear_issue else None
    # normalize slack eta: could be 04-10, 04/10, 04-10-26, etc.
    parts = re.split(r'[-/]', slack_eta)
    try:
        if len(parts) == 2:
            m, d = map(int, parts)
            y = date.today().year
        elif len(parts) == 3:
            a, b, c = map(int, parts)
            if a > 31:
                y, m, d = a, b, c
            else:
                m, d = a, b
                y = 2000 + c if c < 100 else c
        else:
            return None, None, lin_due
        slack_iso = date(y, m, d).isoformat()
    except Exception:
        return None, None, lin_due
    if not lin_due:
        return None, slack_iso, None
    return slack_iso == lin_due, slack_iso, lin_due


def main():
    slack_msgs = load_slack()
    linear = load_linear()

    # Only process Raccoons TSAs for apples-to-apples with KPI config
    from team_config import KPI_MEMBERS
    name_by_short = {
        'alexandra': 'Alexandra Lacerda',
        'carlos': 'Carlos',
        'diego': 'Diego Cavalli',
        'gabrielle': 'Gabrielle Cupello',
        'thiago': 'Thiago Rodrigues',
        'thais': 'Thaís',
        'yasmim': 'Yasmim',
    }

    findings = []
    total_items = 0
    stats = Counter()
    etas_matched = 0
    etas_mismatched = 0
    etas_missing_in_linear = 0

    # Snapshot: Linear tickets touched in last 14 days
    cutoff = (datetime.now() - timedelta(days=14)).isoformat()
    recently_touched = [
        i for i in linear
        if i.get('updatedAt', '') > cutoff
        and i.get('status') not in ('Done', 'Canceled', 'Duplicate')
        and i.get('assigneeId') in KPI_MEMBERS
    ]

    # For BLIND spots: which Linear issues were updated but NEVER mentioned in Slack posts?
    all_slack_linear_ids = set()

    for msg in slack_msgs:
        user = msg.get('username', '')
        if user not in name_by_short:
            continue
        text = msg.get('text', '')
        if '[Daily Agenda' not in text:
            continue
        items = parse_slack_post(text)
        for it in items:
            for lid in it['linear_ids']:
                all_slack_linear_ids.add(lid)
            total_items += 1
            mt, lin = match_to_linear(it, linear, user)
            stats[mt] += 1

            # ETA comparison
            eta_result = None
            if it['eta'] and lin:
                matches, slack_iso, lin_iso = compute_eta_mismatch(it['eta'], lin)
                if matches is True:
                    etas_matched += 1
                    eta_result = 'match'
                elif matches is False:
                    etas_mismatched += 1
                    eta_result = 'mismatch'
                else:
                    eta_result = 'unparseable'
            elif it['eta'] and not lin:
                etas_missing_in_linear += 1
                eta_result = 'no_linear'

            findings.append({
                'tsa': user,
                'post_ts': msg.get('ts'),
                'project': it['project'],
                'task': it['task'],
                'eta_slack': it['eta'],
                'linear_ids': it['linear_ids'],
                'match_type': mt,
                'linear_id': lin['id'] if lin else None,
                'linear_title': lin.get('title', '')[:100] if lin else None,
                'linear_due': lin.get('dueDate') if lin else None,
                'linear_status': lin.get('status') if lin else None,
                'eta_comparison': eta_result,
            })

    # BLIND SPOTS: tickets touched in Linear recently, but never mentioned in Slack scrum
    blind = [
        i for i in recently_touched
        if i['id'] not in all_slack_linear_ids
    ]

    # Segment posted items: task vs strategic
    # Heuristic: if task matches very common "fix / update / prep / align / investigate" = task-level noise
    noise_verbs = {'fix', 'update', 'prep', 'prepare', 'align', 'investigate',
                   'create', 'validate', 'review', 'check', 'run', 'monitor',
                   'ingest', 'build', 'keep', 'continue', 'mapping', 'document',
                   'share', 'organize', 'finish'}
    task_level = 0
    milestone_level = 0
    for f in findings:
        t = (f['task'] or '').lower()
        first_word = t.split()[0] if t.split() else ''
        if first_word in noise_verbs:
            task_level += 1
        else:
            milestone_level += 1

    summary = {
        'total_slack_items_last_90d': total_items,
        'slack_posts_analyzed': sum(1 for m in slack_msgs if '[Daily Agenda' in m.get('text', '')),
        'match_breakdown': dict(stats),
        'match_rate': {
            'linear_id_direct': round(stats.get('linear_id', 0) / max(total_items, 1) * 100, 1),
            'fuzzy_title': round(stats.get('fuzzy_title', 0) / max(total_items, 1) * 100, 1),
            'project_only_no_ticket': round(stats.get('project_only', 0) / max(total_items, 1) * 100, 1),
            'no_linear_equivalent': round(stats.get('none', 0) / max(total_items, 1) * 100, 1),
        },
        'eta_quality': {
            'matched': etas_matched,
            'mismatched_with_linear': etas_mismatched,
            'eta_slack_only_no_linear_due': etas_missing_in_linear,
        },
        'task_vs_milestone_level': {
            'task_level_items': task_level,
            'milestone_level_items': milestone_level,
        },
        'blind_spots': {
            'linear_tickets_touched_14d_not_in_slack': len(blind),
            'total_linear_touched_14d': len(recently_touched),
            'pct_blind': round(len(blind) / max(len(recently_touched), 1) * 100, 1),
        },
    }

    out = {
        'generated_at': datetime.now().isoformat(),
        'summary': summary,
        'findings': findings,
        'blind_sample': [
            {
                'id': b['id'], 'title': b['title'][:100],
                'assignee': b.get('assignee', ''),
                'project': b.get('project', ''),
                'status': b.get('status', ''),
                'updatedAt': b.get('updatedAt'),
                'dueDate': b.get('dueDate'),
                'url': b['url'],
            }
            for b in sorted(blind, key=lambda x: x.get('updatedAt', ''), reverse=True)[:30]
        ],
    }

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSaved: {OUT_JSON}")


if __name__ == '__main__':
    main()
