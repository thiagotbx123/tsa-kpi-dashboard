"""
VARIANT 4: Week-over-Week Evolution Dashboard
Generates a self-contained HTML dashboard with percentage evolution analysis of TSA KPIs.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import re
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# --- Config ---
DATA_PATH = Path(r"C:\Users\adm_r\Tools\TSA_CORTEX\scripts\_dashboard_data.json")
OUTPUT_PATH = Path(r"C:\Users\adm_r\Downloads\DASH_V4_EVOLUTION.html")
PEOPLE = ["ALEXANDRA", "CARLOS", "DIEGO", "GABI", "THIAGO", "THAIS", "YASMIM"]
CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"

# --- Load & Filter ---
with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

def parse_week(week_str):
    m = re.match(r"(\d{2})-(\d{2})\s+W\.(\d+)", week_str)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def in_core_period(week_str):
    pw = parse_week(week_str)
    if not pw:
        return False
    y, mo, _ = pw
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

def week_sort_key(week_str):
    pw = parse_week(week_str)
    if not pw:
        return (99, 99, 99)
    return pw

def safe_date(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None

def month_label(y, m):
    names = {12: "Dec", 1: "Jan", 2: "Feb", 3: "Mar"}
    yr = 2000 + y
    return f"{names.get(m, str(m))} {yr}"

data = [r for r in raw if in_core_period(r.get("week", ""))]

# --- Get sorted unique weeks ---
all_weeks = sorted(set(r["week"] for r in data if parse_week(r["week"])), key=week_sort_key)

# --- Group data by (person, week) ---
pw_data = defaultdict(list)  # (person, week) -> [records]
for r in data:
    tsa = r.get("tsa", "")
    week = r.get("week", "")
    if tsa in PEOPLE and parse_week(week):
        pw_data[(tsa, week)].append(r)

# --- Compute KPIs per (person, week) ---
# KPI 1: ETA Accuracy = On Time / (On Time + Late). None if denominator = 0.
# KPI 2: Avg Duration = avg(delivery - dateAdd) for Done tasks with valid dates & dur >= 0. None if no tasks.
# KPI 3: Implementation Reliability = On Time / (On Time + Late + Overdue). None if denominator = 0.

def compute_kpis(records):
    on_time = sum(1 for r in records if r.get("perf") == "On Time")
    late = sum(1 for r in records if r.get("perf") == "Late")
    overdue = sum(1 for r in records if r.get("perf") == "Overdue")

    # KPI 1
    denom1 = on_time + late
    kpi1 = (on_time / denom1 * 100) if denom1 > 0 else None

    # KPI 2
    durations = []
    for r in records:
        if r.get("status") == "Done":
            da = safe_date(r.get("dateAdd", ""))
            dd = safe_date(r.get("delivery", ""))
            if da and dd:
                dur = (dd - da).days
                if dur >= 0:
                    durations.append(dur)
    kpi2 = (sum(durations) / len(durations)) if durations else None

    # KPI 3
    denom3 = on_time + late + overdue
    kpi3 = (on_time / denom3 * 100) if denom3 > 0 else None

    return {"eta_accuracy": kpi1, "avg_duration": kpi2, "impl_reliability": kpi3}

# Build KPI matrix: person -> week -> kpis
kpi_matrix = {p: {} for p in PEOPLE}
team_kpi = {}

for p in PEOPLE:
    for w in all_weeks:
        recs = pw_data.get((p, w), [])
        if recs:
            kpi_matrix[p][w] = compute_kpis(recs)
        else:
            kpi_matrix[p][w] = {"eta_accuracy": None, "avg_duration": None, "impl_reliability": None}

# Team-level KPIs per week
for w in all_weeks:
    all_recs = []
    for p in PEOPLE:
        all_recs.extend(pw_data.get((p, w), []))
    team_kpi[w] = compute_kpis(all_recs) if all_recs else {"eta_accuracy": None, "avg_duration": None, "impl_reliability": None}

# --- Week-over-week percentage change ---
def pct_change_series(values):
    """Given a list of (week, value_or_None), return list of (week, pct_change_or_None)."""
    result = []
    prev = None
    for w, v in values:
        if v is not None and prev is not None and prev != 0:
            change = ((v - prev) / abs(prev)) * 100
            result.append((w, round(change, 1)))
        else:
            result.append((w, None))
        if v is not None:
            prev = v
    return result

# --- 3-week rolling average ---
def rolling_avg(values, window=3):
    """Given list of (week, value_or_None), return rolling avg."""
    result = []
    buffer = []
    for w, v in values:
        if v is not None:
            buffer.append(v)
        if len(buffer) > window:
            buffer.pop(0)
        if buffer:
            result.append((w, round(sum(buffer) / len(buffer), 1)))
        else:
            result.append((w, None))
    return result

# --- Linear regression slope for trend ---
def lin_reg_slope(values):
    """Simple linear regression slope from list of numeric values (ignoring None)."""
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    n = len(pts)
    if n < 2:
        return None
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0
    return (n * sxy - sx * sy) / denom

# --- Trend direction based on last 4 weeks ---
def trend_direction(person, kpi_key):
    """Returns arrow and descriptor based on slope of last 4 weeks."""
    vals = []
    for w in all_weeks[-4:]:
        v = kpi_matrix[person][w].get(kpi_key)
        vals.append(v)
    slope = lin_reg_slope(vals)
    if slope is None:
        return ("&mdash;", "No data", "#94a3b8")
    # For avg_duration, lower is better, so invert
    if kpi_key == "avg_duration":
        slope = -slope
    if slope > 2:
        return ("&uarr;", "Improving", "#22c55e")
    elif slope < -2:
        return ("&darr;", "Declining", "#ef4444")
    else:
        return ("&rarr;", "Stable", "#3b82f6")

# --- Month-over-month comparison ---
months = []  # (y, m) sorted
month_set = set()
for w in all_weeks:
    pw = parse_week(w)
    if pw:
        month_set.add((pw[0], pw[1]))
months = sorted(month_set)

def month_avg(person, kpi_key, y, m):
    """Average KPI for a person in a given month."""
    vals = []
    for w in all_weeks:
        pw = parse_week(w)
        if pw and pw[0] == y and pw[1] == m:
            v = kpi_matrix[person][w].get(kpi_key)
            if v is not None:
                vals.append(v)
    return round(sum(vals) / len(vals), 1) if vals else None

mom_data = {}
for p in PEOPLE:
    mom_data[p] = {}
    for kpi in ["eta_accuracy", "avg_duration", "impl_reliability"]:
        mom_data[p][kpi] = {}
        for y, m in months:
            mom_data[p][kpi][(y, m)] = month_avg(p, kpi, y, m)

# --- Momentum score: weighted recent performance (exponential decay) ---
def momentum_score(person, kpi_key):
    """More recent weeks count more. Weight = 2^(i/n) where i is position from start."""
    vals_with_weight = []
    for i, w in enumerate(all_weeks):
        v = kpi_matrix[person][w].get(kpi_key)
        if v is not None:
            weight = 2 ** (i / max(len(all_weeks) - 1, 1))
            vals_with_weight.append((v, weight))
    if not vals_with_weight:
        return None
    weighted_sum = sum(v * w for v, w in vals_with_weight)
    weight_sum = sum(w for _, w in vals_with_weight)
    return round(weighted_sum / weight_sum, 1) if weight_sum > 0 else None

# --- Acceleration: is rate of change improving or worsening? ---
def acceleration(person, kpi_key):
    """Slope of the pct_change series (second derivative)."""
    raw_vals = [(w, kpi_matrix[person][w].get(kpi_key)) for w in all_weeks]
    pct = pct_change_series(raw_vals)
    pct_vals = [v for _, v in pct if v is not None]
    if len(pct_vals) < 3:
        return None
    # Slope of pct changes
    slope = lin_reg_slope(pct_vals)
    if slope is None:
        return None
    if kpi_key == "avg_duration":
        slope = -slope
    return round(slope, 2)

# --- Best trajectory / Needs attention ---
def find_extremes(kpi_key):
    best_person = None
    best_delta = -999
    worst_person = None
    worst_delta = 999

    for p in PEOPLE:
        vals = [kpi_matrix[p][w].get(kpi_key) for w in all_weeks[-4:]]
        valid = [v for v in vals if v is not None]
        if len(valid) < 2:
            continue
        delta = valid[-1] - valid[0]
        if kpi_key == "avg_duration":
            delta = -delta  # Lower is better
        if delta > best_delta:
            best_delta = delta
            best_person = p
        if delta < worst_delta:
            worst_delta = delta
            worst_person = p

    return (best_person, round(best_delta, 1)), (worst_person, round(worst_delta, 1))

# --- Prepare chart data structures ---
kpi_defs = [
    ("eta_accuracy", "ETA Accuracy", "%", "> 90%"),
    ("avg_duration", "Avg Duration", "days", "< 28d"),
    ("impl_reliability", "Impl. Reliability", "%", "> 85%"),
]

# For team line charts: raw values and rolling avg
team_chart_data = {}
for kpi_key, _, _, _ in kpi_defs:
    raw_vals = [(w, team_kpi[w].get(kpi_key)) for w in all_weeks]
    team_chart_data[kpi_key] = {
        "raw": [v for _, v in raw_vals],
        "rolling": [v for _, v in rolling_avg(raw_vals, 3)],
        "pct_change": [v for _, v in pct_change_series(raw_vals)],
    }

# Per-person pct_change for line charts
person_pct_data = {}
for p in PEOPLE:
    person_pct_data[p] = {}
    for kpi_key, _, _, _ in kpi_defs:
        raw_vals = [(w, kpi_matrix[p][w].get(kpi_key)) for w in all_weeks]
        person_pct_data[p][kpi_key] = [v for _, v in pct_change_series(raw_vals)]

# Person rolling averages
person_rolling_data = {}
for p in PEOPLE:
    person_rolling_data[p] = {}
    for kpi_key, _, _, _ in kpi_defs:
        raw_vals = [(w, kpi_matrix[p][w].get(kpi_key)) for w in all_weeks]
        person_rolling_data[p][kpi_key] = [v for _, v in rolling_avg(raw_vals, 3)]

# --- Build HTML ---
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TSA CORTEX - Week-over-Week Evolution</title>
<script src="{CHART_JS_CDN}"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #ffffff;
    color: #1e293b;
    padding: 24px;
    line-height: 1.5;
}}
.header {{
    text-align: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid #e2e8f0;
}}
.header h1 {{
    font-size: 28px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.5px;
}}
.header .subtitle {{
    color: #64748b;
    font-size: 14px;
    margin-top: 4px;
}}
.callout-row {{
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
}}
.callout {{
    flex: 1;
    padding: 14px 18px;
    border-radius: 10px;
    border-left: 4px solid;
    font-size: 13px;
}}
.callout-green {{ background: #f0fdf4; border-color: #22c55e; }}
.callout-red {{ background: #fef2f2; border-color: #ef4444; }}
.callout-blue {{ background: #eff6ff; border-color: #3b82f6; }}
.callout strong {{ font-size: 14px; }}
.grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}}
.grid-full {{ grid-column: 1 / -1; }}
.card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.card h2 {{
    font-size: 16px;
    font-weight: 600;
    color: #334155;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #f1f5f9;
}}
.card h2 .badge {{
    font-size: 11px;
    font-weight: 500;
    background: #eff6ff;
    color: #3b82f6;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 8px;
    vertical-align: middle;
}}
canvas {{ max-height: 380px; }}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
th {{
    text-align: left;
    padding: 8px 10px;
    background: #f8fafc;
    color: #475569;
    font-weight: 600;
    border-bottom: 2px solid #e2e8f0;
    white-space: nowrap;
}}
td {{
    padding: 7px 10px;
    border-bottom: 1px solid #f1f5f9;
    color: #334155;
}}
tr:hover td {{ background: #f8fafc; }}
.trend-up {{ color: #22c55e; font-weight: 700; }}
.trend-down {{ color: #ef4444; font-weight: 700; }}
.trend-stable {{ color: #3b82f6; font-weight: 700; }}
.delta-pos {{ color: #22c55e; font-weight: 600; }}
.delta-neg {{ color: #ef4444; font-weight: 600; }}
.delta-zero {{ color: #94a3b8; }}
.momentum-high {{ background: #f0fdf4; }}
.momentum-low {{ background: #fef2f2; }}
.section-label {{
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    margin: 32px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}}
.footer {{
    text-align: center;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #e2e8f0;
    color: #94a3b8;
    font-size: 12px;
}}
</style>
</head>
<body>

<div class="header">
    <h1>Week-over-Week Evolution</h1>
    <div class="subtitle">TSA CORTEX &mdash; Momentum, Trends &amp; Trajectory Analysis &mdash; Dec 2025 - Mar 2026 &mdash; {len(data)} records, {len(all_weeks)} weeks</div>
</div>
"""

# --- Callout highlights ---
for kpi_key, kpi_name, _, _ in kpi_defs:
    (bp, bd), (wp, wd) = find_extremes(kpi_key)
    sign_b = "+" if bd >= 0 else ""
    sign_w = "+" if wd >= 0 else ""
    unit = "pp" if kpi_key != "avg_duration" else "d"
    html += f"""<div class="callout-row">
    <div class="callout callout-green">
        <strong>{kpi_name} &mdash; Best Trajectory</strong><br>
        {bp or 'N/A'}: {sign_b}{bd}{unit} over last 4 weeks
    </div>
    <div class="callout callout-red">
        <strong>{kpi_name} &mdash; Needs Attention</strong><br>
        {wp or 'N/A'}: {sign_w}{wd}{unit} over last 4 weeks
    </div>
</div>
"""

html += """<div class="grid">
"""

# --- KPI WoW % Change Charts (team level) ---
for kpi_key, kpi_name, unit, target in kpi_defs:
    chart_id = f"teamPct_{kpi_key}"
    html += f"""<div class="card">
    <h2>{kpi_name} &mdash; WoW % Change <span class="badge">Team</span></h2>
    <canvas id="{chart_id}"></canvas>
</div>
"""

# --- KPI Raw + Rolling Avg Charts (team level) ---
for kpi_key, kpi_name, unit, target in kpi_defs:
    chart_id = f"teamRaw_{kpi_key}"
    html += f"""<div class="card">
    <h2>{kpi_name} &mdash; Raw + 3W Rolling Avg <span class="badge">Target: {target}</span></h2>
    <canvas id="{chart_id}"></canvas>
</div>
"""

# --- Trend direction table ---
html += """<div class="card grid-full">
    <h2>Trend Direction per Person <span class="badge">Last 4 Weeks Linear Regression</span></h2>
    <table>
        <thead>
            <tr>
                <th>Person</th>
"""
for _, kpi_name, _, _ in kpi_defs:
    html += f"                <th>{kpi_name} Trend</th>\n"
html += """                <th>Momentum (ETA Acc.)</th>
                <th>Momentum (Reliability)</th>
                <th>Acceleration (ETA Acc.)</th>
            </tr>
        </thead>
        <tbody>
"""

for p in PEOPLE:
    html += f"            <tr><td><strong>{p}</strong></td>\n"
    for kpi_key, _, _, _ in kpi_defs:
        arrow, desc, color = trend_direction(p, kpi_key)
        css_class = "trend-up" if "Improving" in desc else ("trend-down" if "Declining" in desc else "trend-stable")
        html += f'                <td class="{css_class}">{arrow} {desc}</td>\n'
    # Momentum scores
    for kpi_key in ["eta_accuracy", "impl_reliability"]:
        ms = momentum_score(p, kpi_key)
        if ms is not None:
            css = "momentum-high" if ms >= 80 else ("momentum-low" if ms < 50 else "")
            html += f'                <td class="{css}">{ms}%</td>\n'
        else:
            html += '                <td class="delta-zero">N/A</td>\n'
    # Acceleration
    acc = acceleration(p, "eta_accuracy")
    if acc is not None:
        css_a = "delta-pos" if acc > 0 else ("delta-neg" if acc < 0 else "delta-zero")
        sign = "+" if acc > 0 else ""
        html += f'                <td class="{css_a}">{sign}{acc}</td>\n'
    else:
        html += '                <td class="delta-zero">N/A</td>\n'
    html += "            </tr>\n"

html += """        </tbody>
    </table>
</div>
"""

# --- Month-over-Month Comparison Table ---
html += """<div class="card grid-full">
    <h2>Month-over-Month Comparison <span class="badge">Averages &amp; Deltas</span></h2>
    <table>
        <thead>
            <tr>
                <th>Person</th>
                <th>KPI</th>
"""
for y, m in months:
    html += f"                <th>{month_label(y, m)}</th>\n"
# Delta columns between consecutive months
for i in range(1, len(months)):
    prev_label = month_label(*months[i - 1])
    curr_label = month_label(*months[i])
    html += f"                <th>&Delta; {curr_label}</th>\n"
html += """            </tr>
        </thead>
        <tbody>
"""

for p in PEOPLE:
    for kpi_key, kpi_name, unit, _ in kpi_defs:
        html += f"            <tr><td><strong>{p}</strong></td><td>{kpi_name}</td>\n"
        vals = []
        for y, m in months:
            v = mom_data[p][kpi_key].get((y, m))
            vals.append(v)
            display = f"{v}{unit}" if v is not None else "N/A"
            html += f"                <td>{display}</td>\n"
        # Deltas
        for i in range(1, len(vals)):
            if vals[i] is not None and vals[i - 1] is not None and vals[i - 1] != 0:
                delta = round(vals[i] - vals[i - 1], 1)
                # For duration, negative delta is good
                if kpi_key == "avg_duration":
                    css = "delta-pos" if delta < 0 else ("delta-neg" if delta > 0 else "delta-zero")
                else:
                    css = "delta-pos" if delta > 0 else ("delta-neg" if delta < 0 else "delta-zero")
                sign = "+" if delta > 0 else ""
                html += f'                <td class="{css}">{sign}{delta}</td>\n'
            else:
                html += '                <td class="delta-zero">&mdash;</td>\n'
        html += "            </tr>\n"

html += """        </tbody>
    </table>
</div>

</div><!-- grid -->

<div class="footer">
    Generated by TSA CORTEX &mdash; Week-over-Week Evolution (V4) &mdash; """ + now_str + """
</div>

<script>
"""

# --- Embed data ---
person_colors_js = {
    "ALEXANDRA": "#3b82f6",
    "CARLOS": "#8b5cf6",
    "DIEGO": "#06b6d4",
    "GABI": "#f59e0b",
    "THIAGO": "#10b981",
    "THAIS": "#ec4899",
    "YASMIM": "#f97316"
}

html += f"const PEOPLE = {json.dumps(PEOPLE)};\n"
html += f"const allWeeks = {json.dumps(all_weeks)};\n"
html += f"const teamChartData = {json.dumps(team_chart_data)};\n"
html += f"const personPctData = {json.dumps(person_pct_data)};\n"
html += f"const personRollingData = {json.dumps(person_rolling_data)};\n"
html += f"const personColors = {json.dumps(person_colors_js)};\n"

# Also embed raw person KPI values for the raw+rolling charts
person_raw_data = {}
for p in PEOPLE:
    person_raw_data[p] = {}
    for kpi_key, _, _, _ in kpi_defs:
        person_raw_data[p][kpi_key] = [kpi_matrix[p][w].get(kpi_key) for w in all_weeks]
html += f"const personRawData = {json.dumps(person_raw_data)};\n"

html += """
const kpiDefs = [
    {key: 'eta_accuracy', name: 'ETA Accuracy', unit: '%', target: 90, targetDir: 'above'},
    {key: 'avg_duration', name: 'Avg Duration', unit: 'days', target: 28, targetDir: 'below'},
    {key: 'impl_reliability', name: 'Impl. Reliability', unit: '%', target: 85, targetDir: 'above'},
];

// --- Team WoW % Change Charts ---
kpiDefs.forEach(kpi => {
    const ctx = document.getElementById('teamPct_' + kpi.key).getContext('2d');
    const pctData = teamChartData[kpi.key].pct_change;

    const datasets = [{
        label: 'Team WoW % Change',
        data: pctData,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: pctData.map(v => {
            if (v === null) return '#94a3b8';
            if (kpi.key === 'avg_duration') return v < 0 ? '#22c55e' : (v > 0 ? '#ef4444' : '#3b82f6');
            return v > 0 ? '#22c55e' : (v < 0 ? '#ef4444' : '#3b82f6');
        }),
        pointBorderColor: '#fff',
        pointBorderWidth: 1,
        spanGaps: true,
        borderWidth: 2
    }];

    // Add per-person lines (thinner, semi-transparent)
    PEOPLE.forEach(p => {
        datasets.push({
            label: p,
            data: personPctData[p][kpi.key],
            borderColor: personColors[p] + '80',
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 1,
            spanGaps: true,
            hidden: true
        });
    });

    new Chart(ctx, {
        type: 'line',
        data: { labels: allWeeks, datasets: datasets },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Segoe UI', size: 10 }, usePointStyle: true, padding: 8 }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            if (ctx.raw === null) return ctx.dataset.label + ': N/A';
                            const sign = ctx.raw > 0 ? '+' : '';
                            return ctx.dataset.label + ': ' + sign + ctx.raw + '%';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Segoe UI', size: 9 }, maxRotation: 45 }
                },
                y: {
                    title: { display: true, text: '% Change', font: { family: 'Segoe UI', size: 11 } },
                    grid: { color: '#f1f5f9' },
                    ticks: {
                        callback: function(v) { return (v > 0 ? '+' : '') + v + '%'; }
                    }
                }
            }
        }
    });
});

// --- Team Raw + Rolling Avg Charts ---
kpiDefs.forEach(kpi => {
    const ctx = document.getElementById('teamRaw_' + kpi.key).getContext('2d');

    const datasets = [{
        label: 'Team (raw)',
        data: teamChartData[kpi.key].raw,
        borderColor: '#94a3b8',
        backgroundColor: 'transparent',
        tension: 0.2,
        pointRadius: 3,
        borderWidth: 1.5,
        borderDash: [4, 4],
        spanGaps: true,
    }, {
        label: 'Team (3W rolling)',
        data: teamChartData[kpi.key].rolling,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.06)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        borderWidth: 2.5,
        spanGaps: true,
    }];

    // Target line
    const annotation = {
        label: 'Target',
        data: allWeeks.map(() => kpi.target),
        borderColor: kpi.targetDir === 'above' ? '#22c55e80' : '#ef444480',
        backgroundColor: 'transparent',
        borderDash: [8, 4],
        borderWidth: 1.5,
        pointRadius: 0,
        spanGaps: true,
    };
    datasets.push(annotation);

    // Per-person rolling (hidden by default)
    PEOPLE.forEach(p => {
        datasets.push({
            label: p + ' (rolling)',
            data: personRollingData[p][kpi.key],
            borderColor: personColors[p],
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 1.5,
            spanGaps: true,
            hidden: true
        });
    });

    new Chart(ctx, {
        type: 'line',
        data: { labels: allWeeks, datasets: datasets },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Segoe UI', size: 10 }, usePointStyle: true, padding: 8 }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            if (ctx.raw === null) return ctx.dataset.label + ': N/A';
                            return ctx.dataset.label + ': ' + ctx.raw + kpi.unit;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Segoe UI', size: 9 }, maxRotation: 45 }
                },
                y: {
                    title: { display: true, text: kpi.unit, font: { family: 'Segoe UI', size: 11 } },
                    grid: { color: '#f1f5f9' },
                    beginAtZero: kpi.key === 'avg_duration'
                }
            }
        }
    });
});
</script>

</body>
</html>
"""

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Saved: {OUTPUT_PATH}")
