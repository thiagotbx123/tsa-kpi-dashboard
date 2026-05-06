"""Refresh Linear cache files with LIVE data from Linear API.

Fetches all KPI team member issues into _kpi_all_members.json.
Must be run before merge_opossum_data.py to ensure KPI data is current.

Usage: python kpi/refresh_linear_cache.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, requests, shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
ROOT = os.path.join(SCRIPT_DIR, '..')
ENV_PATH = os.path.join(ROOT, '..', '.env')

# Load API key
api_key = None
for env_file in [ENV_PATH, os.path.join(ROOT, '.env')]:
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip().startswith('LINEAR_API_KEY='):
                    api_key = line.strip().split('=', 1)[1].split('#')[0].strip()
                    break
    if api_key:
        break

if not api_key:
    print("ERROR: LINEAR_API_KEY not found in .env")
    sys.exit(1)

HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': api_key,
}
API_URL = 'https://api.linear.app/graphql'
HTTP_TIMEOUT = 30  # H11: timeout to prevent hanging

# Team IDs
OPOSSUM_TEAM_ID = 'b3fb1317-885c-47a0-b87d-85a77252d994'
RACCOONS_TEAM_ID = '5a021b9f-bb1a-49fa-ad3b-83422c46c357'

# ALL KPI team members — imported from shared config (M14)
from team_config import KPI_MEMBERS

# Query by team (legacy — still used for completeness)
QUERY_TEAM = """
query($teamId: ID!, $cursor: String) {
  issues(
    filter: { team: { id: { eq: $teamId } } }
    first: 100
    after: $cursor
    orderBy: createdAt
  ) {
    pageInfo { hasNextPage endCursor }
    nodes {
      identifier
      title
      description
      url
      branchName
      createdAt
      updatedAt
      archivedAt
      completedAt
      dueDate
      startedAt
      slaStartedAt
      slaMediumRiskAt
      slaHighRiskAt
      slaBreachesAt
      slaType
      state { name }
      labels { nodes { name } }
      creator { name id }
      assignee { name id }
      project { name id }
      projectMilestone { name id }
      parent { identifier }
      team { name id key }
      estimate
      comments(first: 5, orderBy: createdAt) {
        nodes {
          createdAt
          user { name id }
        }
      }
      history(first: 200) {
        nodes {
          createdAt
          fromStateId
          toStateId
          fromDueDate
          toDueDate
          fromAssignee { id name }
          toAssignee { id name }
          actor { name id }
        }
      }
    }
  }
}
"""

# Query by assignee — fetch ALL issues for a person across ALL teams
QUERY_PERSON = """
query($assigneeId: ID!, $cursor: String) {
  issues(
    filter: { assignee: { id: { eq: $assigneeId } } }
    first: 100
    after: $cursor
    orderBy: createdAt
  ) {
    pageInfo { hasNextPage endCursor }
    nodes {
      identifier
      title
      description
      url
      branchName
      createdAt
      updatedAt
      archivedAt
      completedAt
      dueDate
      startedAt
      slaStartedAt
      slaMediumRiskAt
      slaHighRiskAt
      slaBreachesAt
      slaType
      state { name }
      labels { nodes { name } }
      creator { name id }
      assignee { name id }
      project { name id }
      projectMilestone { name id }
      parent { identifier }
      team { name id key }
      estimate
      comments(first: 5, orderBy: createdAt) {
        nodes {
          createdAt
          user { name id }
        }
      }
      history(first: 200) {
        nodes {
          createdAt
          fromStateId
          toStateId
          fromDueDate
          toDueDate
          fromAssignee { id name }
          toAssignee { id name }
          actor { name id }
        }
      }
    }
  }
}
"""

# Query by creator — catch tickets created by KPI member but reassigned elsewhere
QUERY_CREATOR = """
query($creatorId: ID!, $cursor: String) {
  issues(
    filter: { creator: { id: { eq: $creatorId } } }
    first: 100
    after: $cursor
    orderBy: createdAt
  ) {
    pageInfo { hasNextPage endCursor }
    nodes {
      identifier
      title
      description
      url
      branchName
      createdAt
      updatedAt
      archivedAt
      completedAt
      dueDate
      startedAt
      slaStartedAt
      slaMediumRiskAt
      slaHighRiskAt
      slaBreachesAt
      slaType
      state { name }
      labels { nodes { name } }
      creator { name id }
      assignee { name id }
      project { name id }
      projectMilestone { name id }
      parent { identifier }
      team { name id key }
      estimate
      comments(first: 5, orderBy: createdAt) {
        nodes {
          createdAt
          user { name id }
        }
      }
      history(first: 200) {
        nodes {
          createdAt
          fromStateId
          toStateId
          fromDueDate
          toDueDate
          fromAssignee { id name }
          toAssignee { id name }
          actor { name id }
        }
      }
    }
  }
}
"""


def atomic_write_json(path, data):
    """C3: Write JSON atomically — write to .tmp then os.replace."""
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def parse_issue_node(node):
    """F08: Shared parser — extract all fields from a Linear issue node."""
    estimate = node.get('estimate')
    pm = node.get('projectMilestone')
    project = node.get('project')
    parent = node.get('parent')
    labels_raw = node.get('labels', {}).get('nodes', [])
    desc_raw = (node.get('description') or '')
    desc = desc_raw[:2000] + ('...' if len(desc_raw) > 2000 else '')  # L1: truncation indicator

    # Parse comments (last 5, for needs-response detection)
    comments_raw = node.get('comments', {}).get('nodes', [])
    comments = []
    for c in comments_raw:
        comments.append({
            'createdAt': c.get('createdAt', ''),
            'userId': c.get('user', {}).get('id', '') if c.get('user') else '',
            'userName': c.get('user', {}).get('name', '') if c.get('user') else '',
        })

    history_raw = node.get('history', {}).get('nodes', [])
    history = []
    for h in history_raw:
        history.append({
            'createdAt': h.get('createdAt', ''),
            'fromStateId': h.get('fromStateId'),
            'toStateId': h.get('toStateId'),
            'fromDueDate': h.get('fromDueDate'),
            'toDueDate': h.get('toDueDate'),
            'actorName': h.get('actor', {}).get('name', '') if h.get('actor') else '',
            'actorId': h.get('actor', {}).get('id', '') if h.get('actor') else '',
            'fromAssigneeId': h.get('fromAssignee', {}).get('id', '') if h.get('fromAssignee') else '',
            'toAssigneeId': h.get('toAssignee', {}).get('id', '') if h.get('toAssignee') else '',
            'fromAssigneeName': h.get('fromAssignee', {}).get('name', '') if h.get('fromAssignee') else '',
            'toAssigneeName': h.get('toAssignee', {}).get('name', '') if h.get('toAssignee') else '',
        })

    return {
        'id': node['identifier'],
        'title': node.get('title', ''),
        'description': desc,
        'projectMilestone': {'id': pm['id'], 'name': pm['name']} if pm else None,
        'estimate': {'value': estimate, 'name': f"{estimate} Points"} if estimate else None,
        'url': node.get('url', ''),
        'gitBranchName': node.get('branchName', ''),
        'createdAt': node.get('createdAt', ''),
        'updatedAt': node.get('updatedAt', ''),
        'archivedAt': node.get('archivedAt'),
        'completedAt': node.get('completedAt'),
        'dueDate': node.get('dueDate'),
        'startedAt': node.get('startedAt'),
        'slaStartedAt': node.get('slaStartedAt'),
        'slaMediumRiskAt': node.get('slaMediumRiskAt'),
        'slaHighRiskAt': node.get('slaHighRiskAt'),
        'slaBreachesAt': node.get('slaBreachesAt'),
        'slaType': node.get('slaType', ''),
        'status': node.get('state', {}).get('name', ''),
        'labels': [l['name'] for l in labels_raw],
        'createdBy': node.get('creator', {}).get('name', '') if node.get('creator') else '',
        'createdById': node.get('creator', {}).get('id', '') if node.get('creator') else '',
        'assignee': node.get('assignee', {}).get('name', '') if node.get('assignee') else '',
        'assigneeId': node.get('assignee', {}).get('id', '') if node.get('assignee') else '',
        'project': project['name'] if project else '',
        'projectId': project['id'] if project else '',
        'parentId': parent['identifier'] if parent else None,
        'team': node.get('team', {}).get('name', '') if node.get('team') else '',
        'teamId': node.get('team', {}).get('id', '') if node.get('team') else '',
        'history': history,
        'comments': comments,
    }


def fetch_issues_by_query(query_template, var_name, person_id, person_name):
    """Generic fetch using any query template with pagination.
    C2: Returns (issues, complete) tuple — complete=False if pagination broke mid-way."""
    all_issues = []
    cursor = None
    complete = False
    page = 0
    while True:
        page += 1
        variables = {var_name: person_id}
        if cursor:
            variables['cursor'] = cursor
        try:
            resp = requests.post(API_URL, headers=HEADERS,
                                 json={'query': query_template, 'variables': variables},
                                 timeout=HTTP_TIMEOUT)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"    ERROR: {e}")
            break
        if resp.status_code != 200:
            print(f"    ERROR: API returned {resp.status_code}: {resp.text[:200]}")
            break
        data = resp.json()
        if 'errors' in data:
            print(f"    ERROR: {data['errors'][0].get('message', '')}")
            break
        issues_data = data['data']['issues']
        nodes = issues_data['nodes']
        for node in nodes:
            all_issues.append(parse_issue_node(node))
        if not issues_data['pageInfo']['hasNextPage']:
            complete = True
            break
        cursor = issues_data['pageInfo']['endCursor']
    if not complete:
        print(f"    WARNING: fetch incomplete for {person_name} — results may be partial")
    return all_issues, complete


print(f"=== Linear Cache Refresh — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

# Fetch ALL issues per KPI team member — by assignee AND by creator
all_kpi_issues = []
fetch_warnings = []
seen_ids = set()

print("Fetching issues per person (assignee + creator, all teams)...")
for uid, name in sorted(KPI_MEMBERS.items(), key=lambda x: x[1]):
    # Fetch by current assignee
    issues_assigned, ok1 = fetch_issues_by_query(QUERY_PERSON, 'assigneeId', uid, name)
    # Fetch by creator (catches tickets reassigned outside the team)
    issues_created, ok2 = fetch_issues_by_query(QUERY_CREATOR, 'creatorId', uid, name)

    # Merge and dedup
    combined = list(issues_assigned)
    local_ids = {i['id'] for i in combined}
    extra_from_creator = 0
    for iss in issues_created:
        if iss['id'] not in local_ids:
            combined.append(iss)
            local_ids.add(iss['id'])
            extra_from_creator += 1

    new_count = 0
    for iss in combined:
        if iss['id'] not in seen_ids:
            all_kpi_issues.append(iss)
            seen_ids.add(iss['id'])
            new_count += 1
    with_due = sum(1 for i in combined if i.get('dueDate'))
    teams = set(i.get('team', '?') for i in combined)
    extra_note = f" +{extra_from_creator} from creator" if extra_from_creator else ""
    fetch_status = 'OK' if ok1 and ok2 else 'PARTIAL'
    if fetch_status == 'PARTIAL':
        fetch_warnings.append(name)
    print(f"  {name}: {len(combined)} issues ({new_count} new, {with_due} with dueDate{extra_note}) — teams: {', '.join(sorted(teams))} — {fetch_status}")

if fetch_warnings:
    print(f"\n  WARNING: Partial fetch for: {', '.join(fetch_warnings)} — data may be incomplete")
print(f"\nTotal unique KPI issues: {len(all_kpi_issues)}")

# A12: Per-person minimum check — warn if any KPI member has 0 issues (possible API issue)
for uid, name in KPI_MEMBERS.items():
    count = sum(1 for i in all_kpi_issues if i.get('assigneeId') == uid or i.get('createdById') == uid)
    if count == 0:
        print(f"  WARNING: {name} has 0 issues in fetch — possible API issue")

# Save unified KPI cache
kpi_path = os.path.join(ROOT, '_kpi_all_members.json')
raccoons_compat_path = os.path.join(ROOT, '_raccoons_kpi.json')
if len(all_kpi_issues) == 0:
    print(f"  ERROR: 0 KPI issues found — possible API permission issue or team ID change")
    sys.exit(1)
else:
    # Check for dramatic count drop (possible API failure)
    if os.path.exists(kpi_path):
        try:
            with open(kpi_path, 'r', encoding='utf-8') as f:
                old_count = len(json.load(f))
            if len(all_kpi_issues) < old_count * 0.5:
                print(f"  CRITICAL: New count ({len(all_kpi_issues)}) is <50% of previous ({old_count}). Skipping save to protect data.")
                sys.exit(1)
        except (json.JSONDecodeError, IOError, ValueError):
            pass
    atomic_write_json(kpi_path, all_kpi_issues)
    atomic_write_json(raccoons_compat_path, all_kpi_issues)  # backward compat
    print(f"  Saved: {kpi_path} ({len(all_kpi_issues)} issues)")

# Summary
print(f"\n=== Refresh complete ===")
print(f"  Total KPI issues: {len(all_kpi_issues)} (across all teams)")
for uid, name in sorted(KPI_MEMBERS.items(), key=lambda x: x[1]):
    count = sum(1 for i in all_kpi_issues if i.get('assigneeId') == uid)
    print(f"    {name}: {count}")
print(f"\nNext: run 'python kpi/merge_opossum_data.py' then 'python kpi/build_html_dashboard.py'")
