"""
VARIANT 1: Executive Scorecard Dashboard
Generates a self-contained HTML file with KPI cards, progress bars, and insights.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import re
from datetime import datetime, date

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT_PATH = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V1_EXECUTIVE.html')

# --- Load data ---
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# --- Filter core period: (y==25 and m>=12) or (y==26 and m<=3) ---
def is_core_period(week_str):
    m = re.match(r'(\d{2})-(\d{2})\s+W\.(\d+)', week_str)
    if not m:
        return False
    y, mo = int(m.group(1)), int(m.group(2))
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

data = [r for r in raw_data if is_core_period(r.get('week', ''))]

PEOPLE = ['ALEXANDRA', 'CARLOS', 'DIEGO', 'GABI', 'THIAGO', 'THAIS', 'YASMIM']

# --- Week sort key ---
def week_sort_key(w):
    m = re.match(r'(\d{2})-(\d{2})\s+W\.(\d+)', w)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

ALL_WEEKS = sorted(set(r['week'] for r in data if is_core_period(r['week'])), key=week_sort_key)

def parse_date(s):
    if not s or s == 'TBD':
        return None
    try:
        return date.fromisoformat(s)
    except:
        return None

# --- KPI Calculations ---
def calc_eta_accuracy(records):
    """On Time / (On Time + Late). With 7-day tolerance applied."""
    on_time = 0
    late = 0
    for r in records:
        eta_d = parse_date(r.get('eta'))
        delivery_d = parse_date(r.get('delivery'))
        if eta_d and delivery_d:
            diff = (delivery_d - eta_d).days
            if diff <= 7:
                on_time += 1
            else:
                late += 1
    total = on_time + late
    return (on_time / total * 100) if total > 0 else None

def calc_avg_implementation_days(records):
    """avg(delivery - dateAdd) for Done tasks with both dates and duration >=0."""
    durations = []
    for r in records:
        if r.get('status') != 'Done':
            continue
        add_d = parse_date(r.get('dateAdd'))
        del_d = parse_date(r.get('delivery'))
        if add_d and del_d:
            dur = (del_d - add_d).days
            if dur >= 0:
                durations.append(dur)
    return (sum(durations) / len(durations)) if durations else None

def calc_reliability(records):
    """On Time / (On Time + Late + Overdue)."""
    on_time = 0
    late = 0
    overdue = 0
    for r in records:
        p = r.get('perf', '')
        if p == 'On Time':
            on_time += 1
        elif p == 'Late':
            late += 1
        elif p == 'Overdue':
            overdue += 1
    total = on_time + late + overdue
    return (on_time / total * 100) if total > 0 else None

# --- Per-person KPIs ---
person_kpis = {}
for person in PEOPLE:
    recs = [r for r in data if r['tsa'] == person]
    person_kpis[person] = {
        'eta_accuracy': calc_eta_accuracy(recs),
        'avg_days': calc_avg_implementation_days(recs),
        'reliability': calc_reliability(recs),
        'total_tasks': len(recs),
    }

# --- Team-level KPIs ---
team_eta = calc_eta_accuracy(data)
team_days = calc_avg_implementation_days(data)
team_reliability = calc_reliability(data)

# --- Trend: compare last 2 weeks ---
def kpis_for_week(week_str):
    recs = [r for r in data if r['week'] == week_str]
    return {
        'eta_accuracy': calc_eta_accuracy(recs),
        'avg_days': calc_avg_implementation_days(recs),
        'reliability': calc_reliability(recs),
    }

last_week = ALL_WEEKS[-1] if len(ALL_WEEKS) >= 1 else None
prev_week = ALL_WEEKS[-2] if len(ALL_WEEKS) >= 2 else None

kpi_last = kpis_for_week(last_week) if last_week else {}
kpi_prev = kpis_for_week(prev_week) if prev_week else {}

def trend_arrow(current, previous, higher_is_better=True):
    """Return arrow and color class."""
    if current is None or previous is None:
        return '&mdash;', 'neutral'
    diff = current - previous
    if abs(diff) < 0.5:
        return '&rarr;', 'neutral'
    if higher_is_better:
        if diff > 0:
            return '&uarr;', 'up'
        else:
            return '&darr;', 'down'
    else:
        if diff < 0:
            return '&uarr;', 'up'
        else:
            return '&darr;', 'down'

eta_arrow, eta_trend = trend_arrow(kpi_last.get('eta_accuracy'), kpi_prev.get('eta_accuracy'))
days_arrow, days_trend = trend_arrow(kpi_last.get('avg_days'), kpi_prev.get('avg_days'), higher_is_better=False)
rel_arrow, rel_trend = trend_arrow(kpi_last.get('reliability'), kpi_prev.get('reliability'))

# --- Traffic light ---
def traffic_light(value, target, yellow_threshold=None):
    if value is None:
        return 'gray'
    if yellow_threshold is None:
        yellow_threshold = target * 0.85
    if value >= target:
        return 'green'
    elif value >= yellow_threshold:
        return 'yellow'
    else:
        return 'red'

def traffic_light_days(value, target=28):
    if value is None:
        return 'gray'
    if value <= target:
        return 'green'
    elif value <= target * 1.5:
        return 'yellow'
    else:
        return 'red'

eta_light = traffic_light(team_eta, 90)
days_light = traffic_light_days(team_days, 28)
rel_light = traffic_light(team_reliability, 85)

# --- Insights ---
insights = []

# Fastest implementer
fastest = None
fastest_days = None
for p in PEOPLE:
    d = person_kpis[p]['avg_days']
    if d is not None and (fastest_days is None or d < fastest_days):
        fastest = p
        fastest_days = d
if fastest:
    insights.append(f"{fastest.title()} is the fastest implementer at {fastest_days:.0f}d avg")

# Slowest implementer
slowest = None
slowest_days = None
for p in PEOPLE:
    d = person_kpis[p]['avg_days']
    if d is not None and (slowest_days is None or d > slowest_days):
        slowest = p
        slowest_days = d
if slowest and slowest != fastest:
    insights.append(f"{slowest.title()} has the longest avg implementation at {slowest_days:.0f}d")

# Highest ETA accuracy
best_eta_person = None
best_eta_val = None
for p in PEOPLE:
    v = person_kpis[p]['eta_accuracy']
    if v is not None and (best_eta_val is None or v > best_eta_val):
        best_eta_person = p
        best_eta_val = v
if best_eta_person:
    insights.append(f"{best_eta_person.title()} leads ETA accuracy at {best_eta_val:.0f}%")

# Lowest reliability
worst_rel_person = None
worst_rel_val = None
for p in PEOPLE:
    v = person_kpis[p]['reliability']
    if v is not None and (worst_rel_val is None or v < worst_rel_val):
        worst_rel_person = p
        worst_rel_val = v
if worst_rel_person:
    # figure out why
    recs = [r for r in data if r['tsa'] == worst_rel_person]
    no_eta_count = sum(1 for r in recs if r['perf'] in ('No ETA', 'N/A'))
    overdue_count = sum(1 for r in recs if r['perf'] == 'Overdue')
    if no_eta_count > overdue_count:
        reason = "missing ETAs"
    else:
        reason = "overdue tasks"
    insights.append(f"{worst_rel_person.title()} has lowest reliability ({worst_rel_val:.0f}%) due to {reason}")

# Most tasks
most_tasks_person = max(PEOPLE, key=lambda p: person_kpis[p]['total_tasks'])
insights.append(f"{most_tasks_person.title()} handled the most tasks ({person_kpis[most_tasks_person]['total_tasks']})")

# --- Build sorted bar data ---
def sorted_people_for_kpi(kpi_key, reverse=True):
    """Return list of (person, value) sorted by value."""
    items = []
    for p in PEOPLE:
        v = person_kpis[p].get(kpi_key)
        items.append((p, v))
    # None values go to end
    with_val = [(p, v) for p, v in items if v is not None]
    without_val = [(p, v) for p, v in items if v is None]
    with_val.sort(key=lambda x: x[1], reverse=reverse)
    return with_val + without_val

eta_sorted = sorted_people_for_kpi('eta_accuracy', reverse=True)
days_sorted = sorted_people_for_kpi('avg_days', reverse=False)  # lower is better
rel_sorted = sorted_people_for_kpi('reliability', reverse=True)

# --- Format helpers ---
def fmt_pct(v):
    if v is None:
        return 'N/A'
    return f'{v:.1f}%'

def fmt_days(v):
    if v is None:
        return 'N/A'
    return f'{v:.1f}d'

# --- Bar HTML generation ---
def bar_color_pct(value, target, higher_is_better=True):
    if value is None:
        return '#9CA3AF'
    if higher_is_better:
        if value >= target:
            return '#059669'
        elif value >= target * 0.85:
            return '#D97706'
        else:
            return '#DC2626'
    else:
        if value <= target:
            return '#059669'
        elif value <= target * 1.5:
            return '#D97706'
        else:
            return '#DC2626'

def gen_bars_pct(sorted_list, target, max_val=100, higher_is_better=True):
    html = ''
    for person, val in sorted_list:
        if val is None:
            width = 0
            display = 'N/A'
            color = '#9CA3AF'
        else:
            width = min(val / max_val * 100, 100)
            display = fmt_pct(val)
            color = bar_color_pct(val, target, higher_is_better)
        html += f'''<div class="bar-row">
            <div class="bar-label">{person.title()}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{width}%;background:{color}"></div>
            </div>
            <div class="bar-value">{display}</div>
        </div>\n'''
    return html

def gen_bars_days(sorted_list, target=28):
    html = ''
    max_days = 80
    for person, val in sorted_list:
        if val is None:
            width = 0
            display = 'N/A'
            color = '#9CA3AF'
        else:
            width = min(val / max_days * 100, 100)
            display = fmt_days(val)
            color = bar_color_pct(val, target, higher_is_better=False)
        html += f'''<div class="bar-row">
            <div class="bar-label">{person.title()}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{width}%;background:{color}"></div>
            </div>
            <div class="bar-value">{display}</div>
        </div>\n'''
    return html

# --- Traffic light dot ---
LIGHT_COLORS = {
    'green': '#059669',
    'yellow': '#D97706',
    'red': '#DC2626',
    'gray': '#9CA3AF',
}

def light_dot(color_name):
    c = LIGHT_COLORS.get(color_name, '#9CA3AF')
    return f'<span class="traffic-dot" style="background:{c}"></span>'

# --- Trend class ---
TREND_STYLES = {
    'up': 'color:#059669;',
    'down': 'color:#DC2626;',
    'neutral': 'color:#9CA3AF;',
}

now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
period_str = f"{ALL_WEEKS[0]} to {ALL_WEEKS[-1]}" if ALL_WEEKS else "N/A"

# --- Build HTML ---
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TSA Executive Scorecard</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #FFFFFF;
    color: #1B1B1B;
    line-height: 1.5;
    padding: 0;
}}
.header {{
    background: #1B1B1B;
    color: #FFFFFF;
    padding: 32px 48px;
}}
.header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}
.header .subtitle {{
    font-size: 14px;
    color: #9CA3AF;
    margin-top: 4px;
}}
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 48px;
}}
/* KPI Cards */
.kpi-cards {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    margin-bottom: 40px;
}}
.kpi-card {{
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 28px;
    background: #FAFAFA;
    position: relative;
}}
.kpi-card .kpi-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
}}
.kpi-card .kpi-title {{
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6B7280;
}}
.traffic-dot {{
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
}}
.kpi-card .kpi-big {{
    font-size: 48px;
    font-weight: 700;
    line-height: 1.1;
    color: #1B1B1B;
}}
.kpi-card .kpi-trend {{
    font-size: 18px;
    font-weight: 600;
    margin-left: 8px;
}}
.kpi-card .kpi-target {{
    font-size: 12px;
    color: #9CA3AF;
    margin-top: 4px;
}}
.kpi-card .kpi-week-compare {{
    font-size: 12px;
    color: #9CA3AF;
    margin-top: 2px;
}}
/* Sections */
.section {{
    margin-bottom: 36px;
}}
.section-title {{
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 16px;
    color: #1B1B1B;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.section-title .target-badge {{
    font-size: 12px;
    font-weight: 500;
    background: #2563EB;
    color: white;
    padding: 2px 10px;
    border-radius: 100px;
}}
/* Bars */
.bar-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}}
.bar-label {{
    width: 100px;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    text-align: right;
}}
.bar-track {{
    flex: 1;
    height: 24px;
    background: #F3F4F6;
    border-radius: 6px;
    overflow: hidden;
}}
.bar-fill {{
    height: 100%;
    border-radius: 6px;
    transition: width 0.5s ease;
}}
.bar-value {{
    width: 60px;
    font-size: 13px;
    font-weight: 600;
    color: #1B1B1B;
}}
/* Insights */
.insights-box {{
    background: #F0F9FF;
    border: 1px solid #BAE6FD;
    border-radius: 10px;
    padding: 20px 28px;
    margin-bottom: 36px;
}}
.insights-box h3 {{
    font-size: 14px;
    font-weight: 700;
    color: #2563EB;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.insights-box ul {{
    list-style: none;
    padding: 0;
}}
.insights-box li {{
    font-size: 14px;
    color: #1E3A5F;
    padding: 4px 0;
    border-bottom: 1px solid #E0F2FE;
}}
.insights-box li:last-child {{
    border-bottom: none;
}}
.insights-box li::before {{
    content: "\\2022";
    color: #2563EB;
    font-weight: bold;
    margin-right: 8px;
}}
/* Footer */
.footer {{
    text-align: center;
    padding: 24px;
    font-size: 12px;
    color: #9CA3AF;
    border-top: 1px solid #E5E7EB;
    margin-top: 20px;
}}
/* Responsive */
@media (max-width: 800px) {{
    .kpi-cards {{ grid-template-columns: 1fr; }}
    .container {{ padding: 20px; }}
    .header {{ padding: 20px; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>TSA Executive Scorecard</h1>
    <div class="subtitle">Core Period: {period_str} &middot; {len(data)} tasks &middot; {len(PEOPLE)} team members</div>
</div>
<div class="container">

<!-- KPI Cards -->
<div class="kpi-cards">
    <div class="kpi-card">
        <div class="kpi-header">
            {light_dot(eta_light)}
            <span class="kpi-title">ETA Accuracy</span>
        </div>
        <div>
            <span class="kpi-big">{fmt_pct(team_eta).replace('%','')}</span><span class="kpi-big" style="font-size:24px">%</span>
            <span class="kpi-trend" style="{TREND_STYLES[eta_trend]}">{eta_arrow}</span>
        </div>
        <div class="kpi-target">Target: &gt;90% &middot; On Time / (On Time + Late)</div>
        <div class="kpi-week-compare">{prev_week or 'N/A'}: {fmt_pct(kpi_prev.get('eta_accuracy'))} &rarr; {last_week or 'N/A'}: {fmt_pct(kpi_last.get('eta_accuracy'))}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-header">
            {light_dot(days_light)}
            <span class="kpi-title">Avg Implementation</span>
        </div>
        <div>
            <span class="kpi-big">{fmt_days(team_days).replace('d','')}</span><span class="kpi-big" style="font-size:24px">d</span>
            <span class="kpi-trend" style="{TREND_STYLES[days_trend]}">{days_arrow}</span>
        </div>
        <div class="kpi-target">Target: &lt;28 days &middot; avg(delivery &minus; dateAdd) for Done</div>
        <div class="kpi-week-compare">{prev_week or 'N/A'}: {fmt_days(kpi_prev.get('avg_days'))} &rarr; {last_week or 'N/A'}: {fmt_days(kpi_last.get('avg_days'))}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-header">
            {light_dot(rel_light)}
            <span class="kpi-title">Implementation Reliability</span>
        </div>
        <div>
            <span class="kpi-big">{fmt_pct(team_reliability).replace('%','')}</span><span class="kpi-big" style="font-size:24px">%</span>
            <span class="kpi-trend" style="{TREND_STYLES[rel_trend]}">{rel_arrow}</span>
        </div>
        <div class="kpi-target">Target: &gt;85% &middot; On Time / (On Time + Late + Overdue)</div>
        <div class="kpi-week-compare">{prev_week or 'N/A'}: {fmt_pct(kpi_prev.get('reliability'))} &rarr; {last_week or 'N/A'}: {fmt_pct(kpi_last.get('reliability'))}</div>
    </div>
</div>

<!-- Insights -->
<div class="insights-box">
    <h3>Auto-generated Insights</h3>
    <ul>
        {''.join(f'<li>{i}</li>' for i in insights)}
    </ul>
</div>

<!-- ETA Accuracy Bars -->
<div class="section">
    <div class="section-title">ETA Accuracy by Person <span class="target-badge">Target &gt;90%</span></div>
    {gen_bars_pct(eta_sorted, target=90, max_val=100, higher_is_better=True)}
</div>

<!-- Avg Implementation Days Bars -->
<div class="section">
    <div class="section-title">Avg Implementation Days by Person <span class="target-badge">Target &lt;28d</span></div>
    {gen_bars_days(days_sorted, target=28)}
</div>

<!-- Reliability Bars -->
<div class="section">
    <div class="section-title">Implementation Reliability by Person <span class="target-badge">Target &gt;85%</span></div>
    {gen_bars_pct(rel_sorted, target=85, max_val=100, higher_is_better=True)}
</div>

</div>

<div class="footer">
    Generated on {now_str} &middot; TSA CORTEX Executive Scorecard v1 &middot; Data: {len(data)} records across {len(ALL_WEEKS)} weeks
</div>
</body>
</html>'''

# --- Write output ---
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Saved: {OUTPUT_PATH}')
