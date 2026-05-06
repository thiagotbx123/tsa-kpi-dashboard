"""
VARIANT 3: Statistical Deep Dive Dashboard
Generates a self-contained HTML dashboard with statistical analysis of TSA team performance.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import re
import math
from pathlib import Path
from datetime import datetime

# --- Config ---
DATA_PATH = Path(r"C:\Users\adm_r\Tools\TSA_CORTEX\scripts\_dashboard_data.json")
OUTPUT_PATH = Path(r"C:\Users\adm_r\Downloads\DASH_V3_STATISTICAL.html")
PEOPLE = ["ALEXANDRA", "CARLOS", "DIEGO", "GABI", "THIAGO", "THAIS", "YASMIM"]
CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"

# --- Load & Filter ---
with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

def in_core_period(week_str):
    m = re.match(r"(\d{2})-(\d{2})\s+W\.(\d+)", week_str)
    if not m:
        return False
    y, mo = int(m.group(1)), int(m.group(2))
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

def parse_week(week_str):
    """Returns (year, month, weeknum) or None."""
    m = re.match(r"(\d{2})-(\d{2})\s+W\.(\d+)", week_str)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def week_sort_key(week_str):
    parsed = parse_week(week_str)
    if not parsed:
        return (99, 99, 99)
    return parsed

def safe_date(s):
    """Parse YYYY-MM-DD date, return datetime or None."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None

data = [r for r in raw if in_core_period(r.get("week", ""))]

# --- Compute durations ---
# duration = (delivery - dateAdd) in days, only for Done tasks with valid dates and duration >= 0
durations_by_person = {p: [] for p in PEOPLE}
task_durations = []  # (tsa, focus, duration, dateAdd, delivery, week)

for r in data:
    tsa = r.get("tsa", "")
    if tsa not in PEOPLE:
        continue
    if r.get("status", "") != "Done":
        continue
    d_add = safe_date(r.get("dateAdd", ""))
    d_del = safe_date(r.get("delivery", ""))
    if not d_add or not d_del:
        continue
    dur = (d_del - d_add).days
    if dur < 0:
        continue
    durations_by_person[tsa].append(dur)
    task_durations.append({
        "tsa": tsa,
        "focus": r.get("focus", ""),
        "duration": dur,
        "dateAdd": r.get("dateAdd", ""),
        "delivery": r.get("delivery", ""),
        "week": r.get("week", "")
    })

# --- Statistical helpers ---
def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)

def mean(vals):
    return sum(vals) / len(vals) if vals else 0

def median(vals):
    return percentile(sorted(vals), 50) if vals else 0

def std_dev(vals):
    if len(vals) < 2:
        return 0
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))

# --- Compute stats per person ---
stats = {}
for p in PEOPLE:
    vals = sorted(durations_by_person[p])
    n = len(vals)
    if n == 0:
        stats[p] = {"count": 0, "mean": 0, "median": 0, "std": 0, "p25": 0, "p75": 0, "p95": 0, "min": 0, "max": 0, "cv": 0}
        continue
    m = mean(vals)
    s = std_dev(vals)
    stats[p] = {
        "count": n,
        "mean": round(m, 1),
        "median": round(median(vals), 1),
        "std": round(s, 1),
        "p25": round(percentile(vals, 25), 1),
        "p75": round(percentile(vals, 75), 1),
        "p95": round(percentile(vals, 95), 1),
        "min": vals[0],
        "max": vals[-1],
        "cv": round((s / m) * 100, 1) if m > 0 else 0
    }

# --- Box plot data (min, Q1, median, Q3, max) ---
box_data = {}
for p in PEOPLE:
    vals = sorted(durations_by_person[p])
    if not vals:
        box_data[p] = [0, 0, 0, 0, 0]
    else:
        box_data[p] = [
            vals[0],
            round(percentile(vals, 25), 1),
            round(percentile(vals, 50), 1),
            round(percentile(vals, 75), 1),
            vals[-1]
        ]

# --- Histogram buckets ---
buckets = [(0, 7), (8, 14), (15, 28), (29, 42), (43, 60), (61, 9999)]
bucket_labels = ["0-7d", "8-14d", "15-28d", "29-42d", "43-60d", "60+d"]

hist_by_person = {p: [0] * len(buckets) for p in PEOPLE}
hist_total = [0] * len(buckets)

for td in task_durations:
    d = td["duration"]
    for i, (lo, hi) in enumerate(buckets):
        if lo <= d <= hi:
            hist_by_person[td["tsa"]][i] += 1
            hist_total[i] += 1
            break

# --- Perf distribution per person ---
perf_categories = ["On Time", "Late", "Overdue", "No ETA", "No Delivery Date", "N/A", "On Track"]
perf_dist = {p: {c: 0 for c in perf_categories} for p in PEOPLE}
for r in data:
    tsa = r.get("tsa", "")
    perf = r.get("perf", "")
    if tsa in PEOPLE and perf in perf_categories:
        perf_dist[tsa][perf] += 1

# --- Outlier detection: duration > mean + 2*std ---
outliers = []
for td in task_durations:
    p = td["tsa"]
    s = stats[p]
    if s["count"] < 2:
        continue
    threshold = s["mean"] + 2 * s["std"]
    if td["duration"] > threshold:
        outliers.append({
            "tsa": td["tsa"],
            "focus": td["focus"],
            "duration": td["duration"],
            "threshold": round(threshold, 1),
            "dateAdd": td["dateAdd"],
            "delivery": td["delivery"],
            "week": td["week"]
        })

outliers.sort(key=lambda x: x["duration"], reverse=True)

# --- Build HTML ---
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TSA CORTEX - Statistical Deep Dive</title>
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
    margin-bottom: 32px;
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
.grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}}
.grid-full {{
    grid-column: 1 / -1;
}}
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
canvas {{ max-height: 400px; }}
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
tr:hover td {{
    background: #f8fafc;
}}
.cv-bar {{
    display: inline-block;
    height: 8px;
    border-radius: 4px;
    vertical-align: middle;
    margin-left: 6px;
}}
.outlier-tag {{
    display: inline-block;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 6px;
    font-weight: 600;
}}
.outlier-high {{ background: #fef2f2; color: #dc2626; }}
.outlier-med {{ background: #fffbeb; color: #d97706; }}
.kpi-row {{
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
}}
.kpi-box {{
    flex: 1;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}}
.kpi-box .value {{
    font-size: 28px;
    font-weight: 700;
    color: #1e40af;
}}
.kpi-box .label {{
    font-size: 12px;
    color: #64748b;
    margin-top: 2px;
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
    <h1>Statistical Deep Dive</h1>
    <div class="subtitle">TSA CORTEX &mdash; Distribution, Percentiles &amp; Variance Analysis &mdash; Dec 2025 - Mar 2026 &mdash; {len(data)} records, {len(task_durations)} with measurable duration</div>
</div>

<!-- KPI Summary -->
<div class="kpi-row">
    <div class="kpi-box">
        <div class="value">{round(mean([d['duration'] for d in task_durations]), 1) if task_durations else 0}d</div>
        <div class="label">Team Mean Duration</div>
    </div>
    <div class="kpi-box">
        <div class="value">{round(median([d['duration'] for d in task_durations]), 1) if task_durations else 0}d</div>
        <div class="label">Team Median Duration</div>
    </div>
    <div class="kpi-box">
        <div class="value">{round(std_dev([d['duration'] for d in task_durations]), 1) if len(task_durations) >= 2 else 0}d</div>
        <div class="label">Team Std Deviation</div>
    </div>
    <div class="kpi-box">
        <div class="value">{len(outliers)}</div>
        <div class="label">Outliers Detected</div>
    </div>
</div>

<div class="grid">

<!-- Box Plot -->
<div class="card grid-full">
    <h2>Execution Time Distribution per Person <span class="badge">Box Plot</span></h2>
    <canvas id="boxPlot" height="100"></canvas>
</div>

<!-- Histogram -->
<div class="card">
    <h2>Duration Histogram <span class="badge">Team Aggregate</span></h2>
    <canvas id="histogram"></canvas>
</div>

<!-- Perf Distribution -->
<div class="card">
    <h2>Performance Outcome Distribution <span class="badge">Stacked %</span></h2>
    <canvas id="perfDist"></canvas>
</div>

<!-- Coefficient of Variation -->
<div class="card">
    <h2>Coefficient of Variation <span class="badge">Consistency Ranking</span></h2>
    <canvas id="cvChart"></canvas>
</div>

<!-- Histogram per person -->
<div class="card">
    <h2>Duration Histogram by Person <span class="badge">Stacked</span></h2>
    <canvas id="histPerson"></canvas>
</div>

<!-- Statistical Table -->
<div class="card grid-full">
    <h2>Statistical Summary Table <span class="badge">Execution Time in Days</span></h2>
    <table>
        <thead>
            <tr>
                <th>Person</th>
                <th>N</th>
                <th>Mean</th>
                <th>Median</th>
                <th>Std Dev</th>
                <th>P25</th>
                <th>P75</th>
                <th>P95</th>
                <th>Min</th>
                <th>Max</th>
                <th>CV%</th>
                <th>Consistency</th>
            </tr>
        </thead>
        <tbody>
"""

# Sort by CV ascending (most consistent first)
sorted_people = sorted(PEOPLE, key=lambda p: stats[p]["cv"])
for p in sorted_people:
    s = stats[p]
    cv = s["cv"]
    if cv == 0:
        bar_color = "#94a3b8"
        bar_w = 5
        rank_label = "N/A"
    elif cv <= 60:
        bar_color = "#22c55e"
        bar_w = max(5, min(cv, 100))
        rank_label = "High"
    elif cv <= 100:
        bar_color = "#eab308"
        bar_w = max(5, min(cv, 100))
        rank_label = "Medium"
    else:
        bar_color = "#ef4444"
        bar_w = 100
        rank_label = "Low"
    html += f"""            <tr>
                <td><strong>{p}</strong></td>
                <td>{s['count']}</td>
                <td>{s['mean']}</td>
                <td>{s['median']}</td>
                <td>{s['std']}</td>
                <td>{s['p25']}</td>
                <td>{s['p75']}</td>
                <td>{s['p95']}</td>
                <td>{s['min']}</td>
                <td>{s['max']}</td>
                <td>{cv}%</td>
                <td><span class="cv-bar" style="width:{bar_w}px;background:{bar_color}"></span> {rank_label}</td>
            </tr>
"""

html += """        </tbody>
    </table>
</div>

<!-- Outlier Table -->
<div class="card grid-full">
    <h2>Outlier Detection <span class="badge">&gt; Mean + 2&sigma;</span></h2>
"""

if outliers:
    html += """    <table>
        <thead>
            <tr>
                <th>Person</th>
                <th>Task</th>
                <th>Week</th>
                <th>Date Added</th>
                <th>Delivered</th>
                <th>Duration</th>
                <th>Threshold</th>
                <th>Excess</th>
            </tr>
        </thead>
        <tbody>
"""
    for o in outliers:
        excess = round(o["duration"] - o["threshold"], 1)
        severity = "outlier-high" if excess > 20 else "outlier-med"
        focus_display = o["focus"][:60] + "..." if len(o["focus"]) > 60 else o["focus"]
        html += f"""            <tr>
                <td><strong>{o['tsa']}</strong></td>
                <td>{focus_display}</td>
                <td>{o['week']}</td>
                <td>{o['dateAdd']}</td>
                <td>{o['delivery']}</td>
                <td><strong>{o['duration']}d</strong></td>
                <td>{o['threshold']}d</td>
                <td><span class="outlier-tag {severity}">+{excess}d</span></td>
            </tr>
"""
    html += """        </tbody>
    </table>
"""
else:
    html += "    <p style='color:#64748b; padding: 16px;'>No outliers detected (all durations within Mean + 2&sigma;).</p>\n"

html += """</div>

</div><!-- grid -->

<div class="footer">
    Generated by TSA CORTEX &mdash; Statistical Deep Dive (V3) &mdash; """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """
</div>

<script>
"""

# --- Embed data for charts ---
html += f"const PEOPLE = {json.dumps(PEOPLE)};\n"
html += f"const boxData = {json.dumps({p: box_data[p] for p in PEOPLE})};\n"
html += f"const histTotal = {json.dumps(hist_total)};\n"
html += f"const histByPerson = {json.dumps({p: hist_by_person[p] for p in PEOPLE})};\n"
html += f"const bucketLabels = {json.dumps(bucket_labels)};\n"
html += f"const perfDist = {json.dumps({p: {c: perf_dist[p][c] for c in perf_categories} for p in PEOPLE})};\n"
html += f"const perfCategories = {json.dumps(perf_categories)};\n"
html += f"const cvValues = {json.dumps({p: stats[p]['cv'] for p in PEOPLE})};\n"
html += f"const statsData = {json.dumps(stats)};\n"

html += """
const personColors = {
    'ALEXANDRA': '#3b82f6',
    'CARLOS': '#8b5cf6',
    'DIEGO': '#06b6d4',
    'GABI': '#f59e0b',
    'THIAGO': '#10b981',
    'THAIS': '#ec4899',
    'YASMIM': '#f97316'
};

const personColorsBg = {
    'ALEXANDRA': 'rgba(59,130,246,0.15)',
    'CARLOS': 'rgba(139,92,246,0.15)',
    'DIEGO': 'rgba(6,182,212,0.15)',
    'GABI': 'rgba(245,158,11,0.15)',
    'THIAGO': 'rgba(16,185,129,0.15)',
    'THAIS': 'rgba(236,72,153,0.15)',
    'YASMIM': 'rgba(249,115,22,0.15)'
};

const perfColors = {
    'On Time': '#22c55e',
    'Late': '#f59e0b',
    'Overdue': '#ef4444',
    'No ETA': '#94a3b8',
    'No Delivery Date': '#cbd5e1',
    'N/A': '#e2e8f0',
    'On Track': '#3b82f6'
};

// --- Box Plot (horizontal floating bars) ---
(function() {
    const ctx = document.getElementById('boxPlot').getContext('2d');

    // For each person, we draw:
    // 1. A thin bar from min to max (whisker)
    // 2. A thicker bar from Q1 to Q3 (box)
    // 3. A line at median

    const datasets = [];

    // Whiskers (min to max) - thin
    datasets.push({
        label: 'Range (Min-Max)',
        data: PEOPLE.map(p => {
            const d = boxData[p];
            return { x: [d[0], d[4]], y: p };
        }).map(item => item.x),
        backgroundColor: 'rgba(148,163,184,0.3)',
        borderColor: '#94a3b8',
        borderWidth: 1,
        borderSkipped: false,
        barPercentage: 0.3,
        categoryPercentage: 0.8,
    });

    // Box (Q1 to Q3) - thicker
    datasets.push({
        label: 'IQR (Q1-Q3)',
        data: PEOPLE.map(p => {
            const d = boxData[p];
            return [d[1], d[3]];
        }),
        backgroundColor: PEOPLE.map(p => personColors[p] + '40'),
        borderColor: PEOPLE.map(p => personColors[p]),
        borderWidth: 2,
        borderSkipped: false,
        barPercentage: 0.7,
        categoryPercentage: 0.8,
    });

    // Median markers - scatter overlay
    datasets.push({
        label: 'Median',
        type: 'scatter',
        data: PEOPLE.map((p, i) => ({
            x: boxData[p][2],
            y: i
        })),
        backgroundColor: '#0f172a',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 6,
        pointStyle: 'rectRot',
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: PEOPLE,
            datasets: datasets
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { font: { family: 'Segoe UI', size: 11 }, usePointStyle: true, padding: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const p = PEOPLE[ctx.dataIndex];
                            const d = boxData[p];
                            if (ctx.datasetIndex === 2) return 'Median: ' + d[2] + 'd';
                            if (ctx.datasetIndex === 1) return 'Q1: ' + d[1] + 'd, Q3: ' + d[3] + 'd';
                            return 'Min: ' + d[0] + 'd, Max: ' + d[4] + 'd';
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Execution Time (days)', font: { family: 'Segoe UI', size: 12 } },
                    grid: { color: '#f1f5f9' }
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { family: 'Segoe UI', size: 12, weight: '600' } }
                }
            }
        }
    });
})();

// --- Histogram (team aggregate) ---
(function() {
    const ctx = document.getElementById('histogram').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bucketLabels,
            datasets: [{
                label: 'Tasks',
                data: histTotal,
                backgroundColor: '#3b82f6',
                borderColor: '#2563eb',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = histTotal.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ctx.raw + ' tasks (' + pct + '%)';
                        }
                    }
                }
            },
            scales: {
                y: {
                    title: { display: true, text: 'Count', font: { family: 'Segoe UI', size: 12 } },
                    grid: { color: '#f1f5f9' },
                    beginAtZero: true
                },
                x: {
                    title: { display: true, text: 'Duration Bucket', font: { family: 'Segoe UI', size: 12 } },
                    grid: { display: false }
                }
            }
        }
    });
})();

// --- Perf Distribution (stacked bar, proportions) ---
(function() {
    const ctx = document.getElementById('perfDist').getContext('2d');
    const datasets = perfCategories.map(cat => ({
        label: cat,
        data: PEOPLE.map(p => {
            const total = Object.values(perfDist[p]).reduce((a, b) => a + b, 0);
            return total > 0 ? parseFloat(((perfDist[p][cat] / total) * 100).toFixed(1)) : 0;
        }),
        backgroundColor: perfColors[cat],
        borderWidth: 0,
        borderRadius: 2
    }));

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: PEOPLE,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Segoe UI', size: 10 }, usePointStyle: true, padding: 10 }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            return ctx.dataset.label + ': ' + ctx.raw + '%';
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false },
                    ticks: { font: { family: 'Segoe UI', size: 10 } }
                },
                y: {
                    stacked: true,
                    max: 100,
                    title: { display: true, text: '%', font: { family: 'Segoe UI', size: 12 } },
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });
})();

// --- Coefficient of Variation ---
(function() {
    const ctx = document.getElementById('cvChart').getContext('2d');
    const sorted = [...PEOPLE].sort((a, b) => cvValues[a] - cvValues[b]);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted,
            datasets: [{
                label: 'CV%',
                data: sorted.map(p => cvValues[p]),
                backgroundColor: sorted.map(p => {
                    const cv = cvValues[p];
                    if (cv === 0) return '#94a3b8';
                    if (cv <= 60) return '#22c55e';
                    if (cv <= 100) return '#eab308';
                    return '#ef4444';
                }),
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const p = sorted[ctx.dataIndex];
                            const s = statsData[p];
                            return 'CV: ' + ctx.raw + '% (Mean: ' + s.mean + 'd, Std: ' + s.std + 'd)';
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Coefficient of Variation (%)', font: { family: 'Segoe UI', size: 12 } },
                    grid: { color: '#f1f5f9' },
                    beginAtZero: true
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { family: 'Segoe UI', size: 12, weight: '600' } }
                }
            }
        }
    });
})();

// --- Histogram per person (stacked) ---
(function() {
    const ctx = document.getElementById('histPerson').getContext('2d');
    const datasets = PEOPLE.map(p => ({
        label: p,
        data: histByPerson[p],
        backgroundColor: personColors[p],
        borderWidth: 0,
        borderRadius: 2
    }));

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bucketLabels,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Segoe UI', size: 10 }, usePointStyle: true, padding: 10 }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false },
                    title: { display: true, text: 'Duration Bucket', font: { family: 'Segoe UI', size: 12 } }
                },
                y: {
                    stacked: true,
                    title: { display: true, text: 'Count', font: { family: 'Segoe UI', size: 12 } },
                    grid: { color: '#f1f5f9' },
                    beginAtZero: true
                }
            }
        }
    });
})();
</script>

</body>
</html>
"""

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Saved: {OUTPUT_PATH}")
