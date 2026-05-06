"""
VARIANT 2: Radar Profile Dashboard
Generates a self-contained HTML file with radar/spider charts per person and team overlay.
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
OUTPUT_PATH = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V2_RADAR.html')

# --- Load data ---
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# --- Filter core period ---
def is_core_period(week_str):
    m = re.match(r'(\d{2})-(\d{2})\s+W\.(\d+)', week_str)
    if not m:
        return False
    y, mo = int(m.group(1)), int(m.group(2))
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

data = [r for r in raw_data if is_core_period(r.get('week', ''))]

PEOPLE = ['ALEXANDRA', 'CARLOS', 'DIEGO', 'GABI', 'THIAGO', 'THAIS', 'YASMIM']

PERSON_COLORS = {
    'ALEXANDRA': '#8b5cf6',
    'CARLOS': '#f59e0b',
    'DIEGO': '#10b981',
    'GABI': '#ec4899',
    'THIAGO': '#3b82f6',
    'THAIS': '#ef4444',
    'YASMIM': '#06b6d4',
}

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

def speed_score(avg_days):
    """Invert: 28d=100%, 56d=0%. Clamp 0-100."""
    if avg_days is None:
        return None
    score = max(0, min(100, (56 - avg_days) / (56 - 0) * 100))
    # More precisely: 28d -> 100%, 56d -> 0%
    # linear: score = (56 - days) / (56 - 28) * 100 but clamped
    # Actually: at 28d => (56-28)/28*100 = 100. at 56d => 0/28*100 = 0. at 0d => 56/28*100=200 => clamp 100
    score = (56 - avg_days) / 28 * 100
    return max(0, min(100, score))

# --- Per-person KPIs ---
person_kpis = {}
for person in PEOPLE:
    recs = [r for r in data if r['tsa'] == person]
    eta = calc_eta_accuracy(recs)
    days = calc_avg_implementation_days(recs)
    rel = calc_reliability(recs)
    spd = speed_score(days)
    person_kpis[person] = {
        'eta_accuracy': eta if eta is not None else 0,
        'avg_days': days,
        'speed_score': spd if spd is not None else 0,
        'reliability': rel if rel is not None else 0,
        'total_tasks': len(recs),
        'eta_raw': eta,
        'speed_raw': spd,
        'reliability_raw': rel,
    }

# --- Team averages ---
def safe_avg(values):
    valid = [v for v in values if v is not None]
    return (sum(valid) / len(valid)) if valid else 0

team_eta = safe_avg([person_kpis[p]['eta_raw'] for p in PEOPLE])
team_speed = safe_avg([person_kpis[p]['speed_raw'] for p in PEOPLE])
team_rel = safe_avg([person_kpis[p]['reliability_raw'] for p in PEOPLE])
team_days = calc_avg_implementation_days(data)

# --- Insights ---
def balance_score(p):
    """Std dev of 3 KPIs - lower = more balanced."""
    vals = [person_kpis[p]['eta_accuracy'], person_kpis[p]['speed_score'], person_kpis[p]['reliability']]
    mean = sum(vals) / 3
    variance = sum((v - mean) ** 2 for v in vals) / 3
    return variance ** 0.5

def composite_score(p):
    return (person_kpis[p]['eta_accuracy'] + person_kpis[p]['speed_score'] + person_kpis[p]['reliability']) / 3

most_balanced = min(PEOPLE, key=balance_score)
most_balanced_composite = composite_score(most_balanced)

# Most specialized: highest balance_score (most variance) but also determine which is strong/weak
most_specialized = max(PEOPLE, key=balance_score)
spec_kpis = {
    'ETA Accuracy': person_kpis[most_specialized]['eta_accuracy'],
    'Speed': person_kpis[most_specialized]['speed_score'],
    'Reliability': person_kpis[most_specialized]['reliability'],
}
spec_strong = max(spec_kpis, key=spec_kpis.get)
spec_weak = min(spec_kpis, key=spec_kpis.get)

# Top performer (highest composite)
top_performer = max(PEOPLE, key=composite_score)
top_score = composite_score(top_performer)

# Most improved area
insights_text = []
insights_text.append(f"Most balanced: {most_balanced.title()} (composite {most_balanced_composite:.0f}%, std dev {balance_score(most_balanced):.1f})")
insights_text.append(f"Most specialized: {most_specialized.title()} (strong on {spec_strong} at {spec_kpis[spec_strong]:.0f}%, weak on {spec_weak} at {spec_kpis[spec_weak]:.0f}%)")
insights_text.append(f"Top overall performer: {top_performer.title()} (composite score {top_score:.0f}%)")

# Build JSON data for Chart.js
def rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'

# Build datasets for main radar
main_datasets = []
for person in PEOPLE:
    color = PERSON_COLORS[person]
    kpi = person_kpis[person]
    main_datasets.append({
        'label': person.title(),
        'data': [
            round(kpi['eta_accuracy'], 1),
            round(kpi['speed_score'], 1),
            round(kpi['reliability'], 1),
        ],
        'borderColor': color,
        'backgroundColor': rgba(color, 0.08),
        'borderWidth': 2,
        'pointRadius': 4,
        'pointBackgroundColor': color,
        'fill': True,
    })

# Team average dataset (dashed)
main_datasets.append({
    'label': 'Team Average',
    'data': [round(team_eta, 1), round(team_speed, 1), round(team_rel, 1)],
    'borderColor': '#6B7280',
    'backgroundColor': 'rgba(107,114,128,0.05)',
    'borderWidth': 2,
    'borderDash': [6, 4],
    'pointRadius': 0,
    'fill': True,
})

# Target zone dataset
main_datasets.append({
    'label': 'Target Zone',
    'data': [90, 100, 85],
    'borderColor': 'rgba(5,150,105,0.35)',
    'backgroundColor': 'rgba(5,150,105,0.06)',
    'borderWidth': 1,
    'borderDash': [3, 3],
    'pointRadius': 0,
    'fill': True,
})

main_datasets_json = json.dumps(main_datasets)

# Individual mini datasets
mini_charts_data = {}
for person in PEOPLE:
    color = PERSON_COLORS[person]
    kpi = person_kpis[person]
    datasets = [
        {
            'label': person.title(),
            'data': [
                round(kpi['eta_accuracy'], 1),
                round(kpi['speed_score'], 1),
                round(kpi['reliability'], 1),
            ],
            'borderColor': color,
            'backgroundColor': rgba(color, 0.2),
            'borderWidth': 2,
            'pointRadius': 4,
            'pointBackgroundColor': color,
            'fill': True,
        },
        {
            'label': 'Team Avg',
            'data': [round(team_eta, 1), round(team_speed, 1), round(team_rel, 1)],
            'borderColor': '#D1D5DB',
            'backgroundColor': 'rgba(209,213,219,0.08)',
            'borderWidth': 1,
            'borderDash': [4, 4],
            'pointRadius': 0,
            'fill': True,
        },
        {
            'label': 'Target',
            'data': [90, 100, 85],
            'borderColor': 'rgba(5,150,105,0.25)',
            'backgroundColor': 'rgba(5,150,105,0.04)',
            'borderWidth': 1,
            'borderDash': [3, 3],
            'pointRadius': 0,
            'fill': True,
        },
    ]
    mini_charts_data[person] = json.dumps(datasets)

now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
period_str = f"{ALL_WEEKS[0]} to {ALL_WEEKS[-1]}" if ALL_WEEKS else "N/A"

# --- Build legend HTML (pre-built to avoid f-string quoting issues) ---
legend_items_html = ''
for p in PEOPLE:
    c = PERSON_COLORS[p]
    legend_items_html += f'<div class="legend-item"><span class="legend-dot" style="background:{c}"></span>{p.title()}</div>\n'

insights_list_html = ''.join(f'<li>{i}</li>' for i in insights_text)

# --- Build mini card HTML ---
mini_cards_html = ''
for person in PEOPLE:
    color = PERSON_COLORS[person]
    kpi = person_kpis[person]
    eta_display = f"{kpi['eta_accuracy']:.0f}%" if kpi['eta_raw'] is not None else "N/A"
    spd_display = f"{kpi['speed_score']:.0f}%" if kpi['speed_raw'] is not None else "N/A"
    rel_display = f"{kpi['reliability']:.0f}%" if kpi['reliability_raw'] is not None else "N/A"
    days_display = f"{kpi['avg_days']:.0f}d" if kpi['avg_days'] is not None else "N/A"
    comp = composite_score(person)
    canvas_id = f"radar_{person.lower()}"

    mini_cards_html += f'''
    <div class="mini-card">
        <div class="mini-header" style="border-left: 4px solid {color}">
            <div class="mini-name">{person.title()}</div>
            <div class="mini-composite">Composite: {comp:.0f}%</div>
        </div>
        <div class="mini-canvas-wrap">
            <canvas id="{canvas_id}" width="240" height="240"></canvas>
        </div>
        <div class="mini-stats">
            <div class="mini-stat"><span class="mini-stat-label">ETA Acc.</span><span class="mini-stat-val">{eta_display}</span></div>
            <div class="mini-stat"><span class="mini-stat-label">Speed</span><span class="mini-stat-val">{spd_display} ({days_display})</span></div>
            <div class="mini-stat"><span class="mini-stat-label">Reliability</span><span class="mini-stat-val">{rel_display}</span></div>
            <div class="mini-stat"><span class="mini-stat-label">Tasks</span><span class="mini-stat-val">{kpi['total_tasks']}</span></div>
        </div>
    </div>'''

# --- Build Chart.js init scripts for mini charts ---
mini_scripts = ''
for person in PEOPLE:
    canvas_id = f"radar_{person.lower()}"
    mini_scripts += f'''
    new Chart(document.getElementById('{canvas_id}'), {{
        type: 'radar',
        data: {{
            labels: ['ETA Accuracy', 'Speed Score', 'Reliability'],
            datasets: {mini_charts_data[person]}
        }},
        options: {{
            responsive: false,
            scales: {{
                r: {{
                    min: 0,
                    max: 100,
                    ticks: {{ stepSize: 25, display: false }},
                    pointLabels: {{ font: {{ size: 10, family: "'Segoe UI'" }}, color: '#6B7280' }},
                    grid: {{ color: 'rgba(0,0,0,0.06)' }},
                    angleLines: {{ color: 'rgba(0,0,0,0.06)' }},
                }}
            }},
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{ enabled: true }}
            }},
            elements: {{
                line: {{ tension: 0.1 }}
            }}
        }}
    }});
    '''

# --- Build HTML ---
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TSA Radar Profile</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #F9FAFB;
    color: #1B1B1B;
    line-height: 1.5;
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
    max-width: 1300px;
    margin: 0 auto;
    padding: 32px 48px;
}}
/* Main Radar */
.main-radar-section {{
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 32px;
    margin-bottom: 32px;
    text-align: center;
}}
.main-radar-section h2 {{
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
    text-align: left;
}}
.main-radar-section .section-desc {{
    font-size: 13px;
    color: #6B7280;
    margin-bottom: 20px;
    text-align: left;
}}
.main-canvas-wrap {{
    display: flex;
    justify-content: center;
    align-items: center;
}}
/* Legend below main chart */
.legend-row {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 16px;
    margin-top: 16px;
}}
.legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    color: #374151;
}}
.legend-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
}}
.legend-line {{
    width: 20px;
    height: 0;
    border-top: 2px dashed;
    flex-shrink: 0;
}}
/* Mini cards grid */
.mini-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
}}
.mini-card {{
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    overflow: hidden;
}}
.mini-header {{
    padding: 14px 18px;
    background: #FAFAFA;
    border-bottom: 1px solid #F3F4F6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.mini-name {{
    font-size: 16px;
    font-weight: 700;
    color: #1B1B1B;
}}
.mini-composite {{
    font-size: 12px;
    font-weight: 600;
    color: #6B7280;
    background: #F3F4F6;
    padding: 2px 10px;
    border-radius: 100px;
}}
.mini-canvas-wrap {{
    display: flex;
    justify-content: center;
    padding: 12px 0 4px;
}}
.mini-stats {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    border-top: 1px solid #F3F4F6;
}}
.mini-stat {{
    padding: 8px 14px;
    border-bottom: 1px solid #F3F4F6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.mini-stat:nth-child(odd) {{
    border-right: 1px solid #F3F4F6;
}}
.mini-stat-label {{
    font-size: 11px;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}}
.mini-stat-val {{
    font-size: 13px;
    font-weight: 700;
    color: #1B1B1B;
}}
/* Insights */
.insights-box {{
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 32px;
}}
.insights-box h3 {{
    font-size: 14px;
    font-weight: 700;
    color: #2563EB;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.insights-box ul {{
    list-style: none;
    padding: 0;
}}
.insights-box li {{
    font-size: 14px;
    color: #374151;
    padding: 6px 0;
    border-bottom: 1px solid #F3F4F6;
}}
.insights-box li:last-child {{ border-bottom: none; }}
.insights-box li::before {{
    content: "\\25C6";
    color: #2563EB;
    margin-right: 8px;
    font-size: 10px;
}}
/* Axis legend */
.axis-legend {{
    display: flex;
    justify-content: center;
    gap: 32px;
    margin-top: 12px;
    font-size: 12px;
    color: #6B7280;
}}
.axis-legend span {{
    font-weight: 600;
    color: #374151;
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
@media (max-width: 800px) {{
    .container {{ padding: 20px; }}
    .header {{ padding: 20px; }}
    .mini-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>TSA Radar Profile</h1>
    <div class="subtitle">Core Period: {period_str} &middot; {len(data)} tasks &middot; {len(PEOPLE)} team members</div>
</div>
<div class="container">

<!-- Main Radar -->
<div class="main-radar-section">
    <h2>Team Radar Overlay</h2>
    <div class="section-desc">All team members overlaid on a single radar. Axes: ETA Accuracy (0-100%), Speed Score (inverted: 28d=100%, 56d=0%), Reliability (0-100%). Dashed gray = team average. Green zone = target.</div>
    <div class="main-canvas-wrap">
        <canvas id="mainRadar" width="560" height="560"></canvas>
    </div>
    <div class="legend-row">
        {legend_items_html}
        <div class="legend-item"><span class="legend-line" style="border-color:#6B7280"></span>Team Average</div>
        <div class="legend-item"><span class="legend-line" style="border-color:rgba(5,150,105,0.5)"></span>Target Zone</div>
    </div>
    <div class="axis-legend">
        <div><span>ETA Accuracy</span> target &gt;90%</div>
        <div><span>Speed Score</span> 28d=100%, 56d=0%</div>
        <div><span>Reliability</span> target &gt;85%</div>
    </div>
</div>

<!-- Insights -->
<div class="insights-box">
    <h3>Profile Insights</h3>
    <ul>
        {insights_list_html}
    </ul>
</div>

<!-- Mini Radar Cards -->
<h2 style="font-size:20px;font-weight:700;margin-bottom:16px;">Individual Profiles</h2>
<div class="mini-grid">
    {mini_cards_html}
</div>

</div>

<div class="footer">
    Generated on {now_str} &middot; TSA CORTEX Radar Profile v2 &middot; Data: {len(data)} records across {len(ALL_WEEKS)} weeks
</div>

<script>
// Main Radar
new Chart(document.getElementById('mainRadar'), {{
    type: 'radar',
    data: {{
        labels: ['ETA Accuracy', 'Speed Score', 'Reliability'],
        datasets: {main_datasets_json}
    }},
    options: {{
        responsive: false,
        scales: {{
            r: {{
                min: 0,
                max: 100,
                ticks: {{
                    stepSize: 20,
                    font: {{ size: 11, family: "'Segoe UI'" }},
                    color: '#9CA3AF',
                    backdropColor: 'transparent',
                }},
                pointLabels: {{
                    font: {{ size: 14, family: "'Segoe UI'", weight: '600' }},
                    color: '#374151',
                }},
                grid: {{ color: 'rgba(0,0,0,0.07)' }},
                angleLines: {{ color: 'rgba(0,0,0,0.07)' }},
            }}
        }},
        plugins: {{
            legend: {{ display: false }},
            tooltip: {{
                callbacks: {{
                    label: function(ctx) {{
                        return ctx.dataset.label + ': ' + ctx.raw + '%';
                    }}
                }}
            }}
        }},
        elements: {{
            line: {{ tension: 0.1 }}
        }}
    }}
}});

// Mini Radars
{mini_scripts}
</script>
</body>
</html>'''

# --- Write output ---
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Saved: {OUTPUT_PATH}')
