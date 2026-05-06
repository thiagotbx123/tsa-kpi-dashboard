"""Build V7 — Scatter & Correlation Analysis Dashboard."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V7_SCATTER.html')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# ── Filter core period ──────────────────────────────────────────────
def in_core(week):
    m = re.match(r'(\d{2})-(\d{2})\s+W\.(\d+)', week)
    if not m:
        return False
    y, mo = int(m.group(1)), int(m.group(2))
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

data = [r for r in raw_data if in_core(r['week'])]

# ── People + colors ─────────────────────────────────────────────────
PEOPLE = ['ALEXANDRA','CARLOS','DIEGO','GABI','THIAGO','THAIS','YASMIM']
COLORS = {
    'ALEXANDRA':'#8b5cf6','CARLOS':'#f59e0b','DIEGO':'#10b981',
    'GABI':'#ec4899','THIAGO':'#3b82f6','THAIS':'#ef4444','YASMIM':'#06b6d4'
}

# ── Compute KPIs per person ─────────────────────────────────────────
def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d')
    except Exception:
        return None

person_stats = {}
for p in PEOPLE:
    tasks = [r for r in data if r['tsa'] == p]
    on_time = sum(1 for r in tasks if r['perf'] == 'On Time')
    late = sum(1 for r in tasks if r['perf'] == 'Late')
    overdue = sum(1 for r in tasks if r['perf'] == 'Overdue')

    eta_acc = round(on_time / (on_time + late) * 100, 1) if (on_time + late) > 0 else 0
    reliability = round(on_time / (on_time + late + overdue) * 100, 1) if (on_time + late + overdue) > 0 else 0

    durations = []
    done_tasks_detail = []
    for r in tasks:
        if r['status'] == 'Done':
            d_add = parse_date(r.get('dateAdd',''))
            d_del = parse_date(r.get('delivery',''))
            if d_add and d_del:
                dur = (d_del - d_add).days
                if dur >= 0:
                    durations.append(dur)
                    done_tasks_detail.append({
                        'focus': r['focus'],
                        'dateAdd': r['dateAdd'],
                        'delivery': r['delivery'],
                        'duration': dur,
                        'perf': r['perf'],
                        'customer': r.get('customer','')
                    })

    avg_dur = round(sum(durations)/len(durations), 1) if durations else None

    person_stats[p] = {
        'total': len(tasks),
        'on_time': on_time,
        'late': late,
        'overdue': overdue,
        'eta_acc': eta_acc,
        'reliability': reliability,
        'avg_duration': avg_dur,
        'durations': durations,
        'done_tasks': done_tasks_detail
    }

# ── Outlier tasks (duration > 60 days) ──────────────────────────────
outliers = []
for p in PEOPLE:
    for t in person_stats[p]['done_tasks']:
        if t['duration'] > 60:
            outliers.append({**t, 'tsa': p})
outliers.sort(key=lambda x: x['duration'], reverse=True)

# ── Build JS data objects ────────────────────────────────────────────
# Chart 1: Accuracy vs Reliability bubble
bubble_data = []
for p in PEOPLE:
    s = person_stats[p]
    bubble_data.append({
        'label': p,
        'x': s['eta_acc'],
        'y': s['reliability'],
        'r': max(4, min(30, s['total'] / 3)),
        'total': s['total'],
        'color': COLORS[p]
    })

# Chart 2: Volume vs Quality
vol_qual = []
for p in PEOPLE:
    s = person_stats[p]
    vol_qual.append({
        'label': p,
        'x': s['total'],
        'y': s['eta_acc'],
        'color': COLORS[p]
    })

# Chart 3: Duration scatter over time (each done task)
duration_dots = []
for p in PEOPLE:
    for t in person_stats[p]['done_tasks']:
        duration_dots.append({
            'tsa': p,
            'x': t['dateAdd'],
            'y': t['duration'],
            'perf': t['perf'],
            'focus': t['focus'][:60],
            'color': '#10b981' if t['perf'] == 'On Time' else '#ef4444'
        })

# Chart 4: Quadrant (Speed vs Accuracy)
quadrant_data = []
for p in PEOPLE:
    s = person_stats[p]
    if s['avg_duration'] is not None:
        quadrant_data.append({
            'label': p,
            'x': s['avg_duration'],
            'y': s['eta_acc'],
            'color': COLORS[p]
        })

js_bubble = json.dumps(bubble_data)
js_volqual = json.dumps(vol_qual)
js_durdots = json.dumps(duration_dots)
js_quadrant = json.dumps(quadrant_data)
js_outliers = json.dumps(outliers[:20])
js_colors = json.dumps(COLORS)
js_people = json.dumps(PEOPLE)

# Team averages for reference lines
team_eta = round(sum(person_stats[p]['eta_acc'] for p in PEOPLE)/len(PEOPLE), 1)
team_rel = round(sum(person_stats[p]['reliability'] for p in PEOPLE)/len(PEOPLE), 1)
all_durs = []
for p in PEOPLE:
    all_durs.extend(person_stats[p]['durations'])
team_avg_dur = round(sum(all_durs)/len(all_durs), 1) if all_durs else 0

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V7 Scatter & Correlation Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #ffffff; color: #1b1b1b;
  padding: 24px 32px; min-height: 100vh;
}}
.header {{
  background: #0f172a; color: #fff; padding: 20px 28px; border-radius: 10px;
  margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;
}}
.header h1 {{ font-size: 1.35em; font-weight: 700; }}
.header .sub {{ font-size: 0.82em; color: #94a3b8; }}
.legend {{
  display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px;
  padding: 12px 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
}}
.legend-item {{
  display: flex; align-items: center; gap: 6px; font-size: 0.82em; font-weight: 600;
}}
.legend-dot {{
  width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;
}}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
.card {{
  background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.card.full {{ grid-column: 1 / -1; }}
.card h2 {{
  font-size: 0.92em; font-weight: 700; color: #334155;
  margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
}}
.card .desc {{ font-size: 0.75em; color: #94a3b8; margin-bottom: 12px; }}
.chart-wrap {{ position: relative; width: 100%; }}
.chart-wrap.tall {{ height: 380px; }}
.chart-wrap.short {{ height: 300px; }}

/* Outlier table */
.outlier-table {{ width: 100%; border-collapse: collapse; font-size: 0.82em; }}
.outlier-table th {{
  background: #f1f5f9; color: #64748b; font-weight: 600; text-transform: uppercase;
  font-size: 0.72em; letter-spacing: 0.5px; padding: 8px 12px; text-align: left;
  border-bottom: 2px solid #e2e8f0;
}}
.outlier-table td {{
  padding: 7px 12px; border-bottom: 1px solid #f1f5f9;
}}
.outlier-table tr:hover td {{ background: #f8fafc; }}
.badge {{
  display: inline-block; font-size: 0.72em; font-weight: 700;
  padding: 2px 8px; border-radius: 12px;
}}
.badge-on {{ background: #dcfce7; color: #15803d; }}
.badge-late {{ background: #fee2e2; color: #dc2626; }}
.badge-overdue {{ background: #fef3c7; color: #d97706; }}
.badge-person {{
  display: inline-block; font-size: 0.72em; font-weight: 700;
  padding: 2px 8px; border-radius: 12px; color: #fff;
}}

/* KPI summary row */
.kpi-row {{
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
}}
.kpi-box {{
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 14px 16px; text-align: center;
}}
.kpi-box .val {{ font-size: 1.5em; font-weight: 800; }}
.kpi-box .lbl {{ font-size: 0.72em; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }}
.kpi-box .meta {{ font-size: 0.7em; color: #94a3b8; margin-top: 2px; }}

/* Quadrant labels */
.q-label {{
  position: absolute; font-size: 0.68em; font-weight: 600; color: #94a3b8;
  pointer-events: none; text-transform: uppercase; letter-spacing: 0.3px;
}}

footer {{
  text-align: center; font-size: 0.72em; color: #94a3b8; margin-top: 32px; padding: 16px 0;
  border-top: 1px solid #e2e8f0;
}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>V7 -- Scatter & Correlation Analysis</h1>
    <div class="sub">TSA Team Performance | Dec 2025 -- Mar 2026 | {len(data)} records in core period</div>
  </div>
  <div style="text-align:right">
    <div class="sub">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    <div class="sub">Team Avg: ETA Acc {team_eta}% | Reliability {team_rel}% | Duration {team_avg_dur}d</div>
  </div>
</div>

<div class="legend" id="personLegend"></div>

<div class="kpi-row" id="kpiRow"></div>

<div class="grid">
  <!-- Chart 1: Accuracy vs Reliability Bubble -->
  <div class="card">
    <h2>Accuracy vs Reliability</h2>
    <div class="desc">X = ETA Accuracy % | Y = Implementation Reliability % | Size = task count. Do accuracy and reliability correlate?</div>
    <div class="chart-wrap tall">
      <canvas id="chart1"></canvas>
    </div>
  </div>

  <!-- Chart 2: Volume vs Quality -->
  <div class="card">
    <h2>Volume vs Quality</h2>
    <div class="desc">X = Total tasks | Y = ETA Accuracy %. Does doing more tasks hurt quality?</div>
    <div class="chart-wrap tall">
      <canvas id="chart2"></canvas>
    </div>
  </div>

  <!-- Chart 3: Duration Over Time -->
  <div class="card full">
    <h2>Task Duration Over Time</h2>
    <div class="desc">Each dot = one Done task. X = date added | Y = duration (days). Green = On Time, Red = Late/Overdue. Are we getting faster?</div>
    <div class="chart-wrap tall">
      <canvas id="chart3"></canvas>
    </div>
  </div>

  <!-- Chart 4: Speed vs Accuracy Quadrant -->
  <div class="card full">
    <h2>Quadrant Analysis: Speed vs Accuracy</h2>
    <div class="desc">X = Avg Duration (days, lower = faster) | Y = ETA Accuracy %. Four quadrants: Fast+Accurate (star), Fast+Inaccurate (risky), Slow+Accurate (reliable), Slow+Inaccurate (needs help).</div>
    <div class="chart-wrap tall" style="position:relative;">
      <canvas id="chart4"></canvas>
    </div>
  </div>

  <!-- Outlier Table -->
  <div class="card full">
    <h2>Outlier Tasks (Duration > 60 days)</h2>
    <div class="desc">Tasks with unusually long durations that may indicate blockers, scope creep, or tracking issues.</div>
    <div id="outlierTable"></div>
  </div>
</div>

<footer>TSA CORTEX -- V7 Scatter & Correlation Analysis Dashboard</footer>

<script>
const PEOPLE = {js_people};
const COLORS = {js_colors};
const bubbleData = {js_bubble};
const volQualData = {js_volqual};
const durationDots = {js_durdots};
const quadrantData = {js_quadrant};
const outliers = {js_outliers};
const TEAM_ETA = {team_eta};
const TEAM_REL = {team_rel};
const TEAM_DUR = {team_avg_dur};

// ── Build legend ──
const legendEl = document.getElementById('personLegend');
PEOPLE.forEach(p => {{
  const d = document.createElement('div');
  d.className = 'legend-item';
  d.innerHTML = '<span class="legend-dot" style="background:'+COLORS[p]+'"></span>' + p;
  legendEl.appendChild(d);
}});

// ── Build KPI summary boxes ──
const kpiRow = document.getElementById('kpiRow');
const kpiDefs = [
  {{ val: TEAM_ETA + '%', lbl: 'Team ETA Accuracy', meta: 'Target > 90%', color: TEAM_ETA >= 90 ? '#059669' : '#dc2626' }},
  {{ val: TEAM_REL + '%', lbl: 'Team Reliability', meta: 'Target > 85%', color: TEAM_REL >= 85 ? '#059669' : '#dc2626' }},
  {{ val: TEAM_DUR + 'd', lbl: 'Team Avg Duration', meta: 'Target < 28d', color: TEAM_DUR <= 28 ? '#059669' : '#dc2626' }},
  {{ val: outliers.length, lbl: 'Outlier Tasks', meta: 'Duration > 60 days', color: outliers.length === 0 ? '#059669' : '#d97706' }}
];
kpiDefs.forEach(k => {{
  const box = document.createElement('div');
  box.className = 'kpi-box';
  box.innerHTML = '<div class="val" style="color:'+k.color+'">'+k.val+'</div><div class="lbl">'+k.lbl+'</div><div class="meta">'+k.meta+'</div>';
  kpiRow.appendChild(box);
}});

// ── Tooltip defaults ──
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 12;

// ── Chart 1: Accuracy vs Reliability Bubble ──
new Chart(document.getElementById('chart1'), {{
  type: 'bubble',
  data: {{
    datasets: bubbleData.map(d => ({{
      label: d.label,
      data: [{{ x: d.x, y: d.y, r: d.r }}],
      backgroundColor: d.color + '99',
      borderColor: d.color,
      borderWidth: 2
    }}))
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      tooltip: {{
        callbacks: {{
          label: ctx => {{
            const ds = ctx.dataset;
            const pt = ctx.raw;
            const bd = bubbleData.find(b => b.label === ds.label);
            return ds.label + ': Acc=' + pt.x + '%, Rel=' + pt.y + '%, Tasks=' + (bd ? bd.total : '');
          }}
        }}
      }},
      legend: {{ display: false }},
      annotation: undefined
    }},
    scales: {{
      x: {{
        title: {{ display: true, text: 'ETA Accuracy %', font: {{ weight: '600' }} }},
        min: 0, max: 100,
        grid: {{ color: '#f1f5f9' }}
      }},
      y: {{
        title: {{ display: true, text: 'Implementation Reliability %', font: {{ weight: '600' }} }},
        min: 0, max: 100,
        grid: {{ color: '#f1f5f9' }}
      }}
    }}
  }}
}});

// ── Chart 2: Volume vs Quality Scatter ──
new Chart(document.getElementById('chart2'), {{
  type: 'scatter',
  data: {{
    datasets: volQualData.map(d => ({{
      label: d.label,
      data: [{{ x: d.x, y: d.y }}],
      backgroundColor: d.color,
      borderColor: d.color,
      pointRadius: 8,
      pointHoverRadius: 11
    }}))
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      tooltip: {{
        callbacks: {{
          label: ctx => ctx.dataset.label + ': ' + ctx.raw.x + ' tasks, ' + ctx.raw.y + '% accuracy'
        }}
      }},
      legend: {{ display: false }}
    }},
    scales: {{
      x: {{
        title: {{ display: true, text: 'Number of Tasks', font: {{ weight: '600' }} }},
        grid: {{ color: '#f1f5f9' }}
      }},
      y: {{
        title: {{ display: true, text: 'ETA Accuracy %', font: {{ weight: '600' }} }},
        min: 0, max: 100,
        grid: {{ color: '#f1f5f9' }}
      }}
    }}
  }}
}});

// ── Chart 3: Duration Over Time ──
(function() {{
  // Group by perf category
  const onTimeDots = durationDots.filter(d => d.perf === 'On Time');
  const lateDots = durationDots.filter(d => d.perf !== 'On Time');

  new Chart(document.getElementById('chart3'), {{
    type: 'scatter',
    data: {{
      datasets: [
        {{
          label: 'On Time',
          data: onTimeDots.map(d => ({{ x: d.x, y: d.y, focus: d.focus, tsa: d.tsa }})),
          backgroundColor: '#10b98166',
          borderColor: '#10b981',
          pointRadius: 5,
          pointHoverRadius: 8
        }},
        {{
          label: 'Late / Overdue',
          data: lateDots.map(d => ({{ x: d.x, y: d.y, focus: d.focus, tsa: d.tsa }})),
          backgroundColor: '#ef444466',
          borderColor: '#ef4444',
          pointRadius: 5,
          pointHoverRadius: 8
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        tooltip: {{
          callbacks: {{
            label: ctx => {{
              const pt = ctx.raw;
              return pt.tsa + ': ' + pt.focus + ' (' + pt.y + 'd)';
            }}
          }}
        }},
        legend: {{ position: 'top', labels: {{ usePointStyle: true, pointStyle: 'circle' }} }}
      }},
      scales: {{
        x: {{
          type: 'time',
          time: {{ unit: 'week', displayFormats: {{ week: 'MMM dd' }} }},
          title: {{ display: true, text: 'Date Added', font: {{ weight: '600' }} }},
          grid: {{ color: '#f1f5f9' }}
        }},
        y: {{
          title: {{ display: true, text: 'Duration (days)', font: {{ weight: '600' }} }},
          grid: {{ color: '#f1f5f9' }},
          beginAtZero: true
        }}
      }}
    }}
  }});
}})();

// ── Chart 4: Quadrant — Speed vs Accuracy ──
(function() {{
  // Compute medians for quadrant lines
  const xs = quadrantData.map(d => d.x).sort((a,b) => a - b);
  const ys = quadrantData.map(d => d.y).sort((a,b) => a - b);
  const medX = xs.length ? xs[Math.floor(xs.length/2)] : 10;
  const medY = ys.length ? ys[Math.floor(ys.length/2)] : 50;
  const maxX = Math.max(...xs, 30) + 5;
  const maxY = 100;

  const chart4 = new Chart(document.getElementById('chart4'), {{
    type: 'scatter',
    data: {{
      datasets: quadrantData.map(d => ({{
        label: d.label,
        data: [{{ x: d.x, y: d.y }}],
        backgroundColor: d.color,
        borderColor: d.color,
        pointRadius: 10,
        pointHoverRadius: 14,
        pointStyle: 'circle'
      }}))
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        tooltip: {{
          callbacks: {{
            label: ctx => ctx.dataset.label + ': Avg ' + ctx.raw.x + 'd, Acc ' + ctx.raw.y + '%'
          }}
        }},
        legend: {{ display: false }}
      }},
      scales: {{
        x: {{
          title: {{ display: true, text: 'Avg Duration (days) -- lower = faster', font: {{ weight: '600' }} }},
          reverse: true,
          min: 0,
          max: maxX,
          grid: {{ color: '#f1f5f9' }}
        }},
        y: {{
          title: {{ display: true, text: 'ETA Accuracy %', font: {{ weight: '600' }} }},
          min: 0, max: maxY,
          grid: {{ color: '#f1f5f9' }}
        }}
      }}
    }},
    plugins: [{{
      id: 'quadrantLines',
      afterDraw(chart) {{
        const ctx = chart.ctx;
        const xScale = chart.scales.x;
        const yScale = chart.scales.y;
        const xPixel = xScale.getPixelForValue(medX);
        const yPixel = yScale.getPixelForValue(medY);

        ctx.save();
        ctx.strokeStyle = '#94a3b8';
        ctx.lineWidth = 1;
        ctx.setLineDash([6, 4]);

        // Vertical line at median X
        ctx.beginPath();
        ctx.moveTo(xPixel, yScale.top);
        ctx.lineTo(xPixel, yScale.bottom);
        ctx.stroke();

        // Horizontal line at median Y
        ctx.beginPath();
        ctx.moveTo(xScale.left, yPixel);
        ctx.lineTo(xScale.right, yPixel);
        ctx.stroke();

        ctx.setLineDash([]);

        // Quadrant labels
        ctx.font = '600 11px Segoe UI, sans-serif';
        ctx.fillStyle = '#10b981';
        ctx.textAlign = 'center';
        // Top-left = Fast + Accurate (star) — since X is reversed, left=fast
        const tlX = (xScale.right + xPixel) / 2;
        const tlY = (yScale.top + yPixel) / 2;
        ctx.fillText('FAST + ACCURATE', tlX, tlY - 4);
        ctx.font = '400 10px Segoe UI, sans-serif';
        ctx.fillText('(Star Performer)', tlX, tlY + 10);

        // Top-right = Slow + Accurate (reliable)
        ctx.font = '600 11px Segoe UI, sans-serif';
        ctx.fillStyle = '#3b82f6';
        const trX = (xScale.left + xPixel) / 2;
        const trY = (yScale.top + yPixel) / 2;
        ctx.fillText('SLOW + ACCURATE', trX, trY - 4);
        ctx.font = '400 10px Segoe UI, sans-serif';
        ctx.fillText('(Reliable)', trX, trY + 10);

        // Bottom-left = Fast + Inaccurate (risky)
        ctx.font = '600 11px Segoe UI, sans-serif';
        ctx.fillStyle = '#f59e0b';
        const blX = (xScale.right + xPixel) / 2;
        const blY = (yPixel + yScale.bottom) / 2;
        ctx.fillText('FAST + INACCURATE', blX, blY - 4);
        ctx.font = '400 10px Segoe UI, sans-serif';
        ctx.fillText('(Risky)', blX, blY + 10);

        // Bottom-right = Slow + Inaccurate (needs help)
        ctx.font = '600 11px Segoe UI, sans-serif';
        ctx.fillStyle = '#ef4444';
        const brX = (xScale.left + xPixel) / 2;
        const brY = (yPixel + yScale.bottom) / 2;
        ctx.fillText('SLOW + INACCURATE', brX, brY - 4);
        ctx.font = '400 10px Segoe UI, sans-serif';
        ctx.fillText('(Needs Help)', brX, brY + 10);

        ctx.restore();
      }}
    }}]
  }});
}})();

// ── Outlier table ──
(function() {{
  const container = document.getElementById('outlierTable');
  if (outliers.length === 0) {{
    container.innerHTML = '<p style="color:#94a3b8;font-size:0.85em;padding:12px;">No outlier tasks found (all durations <= 60 days).</p>';
    return;
  }}
  let html = '<table class="outlier-table"><thead><tr><th>Person</th><th>Task</th><th>Customer</th><th>Date Added</th><th>Delivered</th><th>Duration</th><th>Perf</th></tr></thead><tbody>';
  outliers.forEach(o => {{
    const perfClass = o.perf === 'On Time' ? 'badge-on' : o.perf === 'Late' ? 'badge-late' : 'badge-overdue';
    html += '<tr>';
    html += '<td><span class="badge-person" style="background:' + COLORS[o.tsa] + '">' + o.tsa + '</span></td>';
    html += '<td>' + o.focus + '</td>';
    html += '<td>' + (o.customer || '-') + '</td>';
    html += '<td>' + o.dateAdd + '</td>';
    html += '<td>' + o.delivery + '</td>';
    html += '<td style="font-weight:700;">' + o.duration + 'd</td>';
    html += '<td><span class="badge ' + perfClass + '">' + o.perf + '</span></td>';
    html += '</tr>';
  }});
  html += '</tbody></table>';
  container.innerHTML = html;
}})();
</script>

<!-- Chart.js date adapter for time axis -->
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<script>
// Re-render chart 3 after adapter loads, if needed
// The adapter script must be loaded AFTER chart.js but the chart was already created.
// We need to re-create chart3 now that the adapter is available.
(function() {{
  const onTimeDots = {json.dumps([d for d in duration_dots if d['perf'] == 'On Time'])};
  const lateDots = {json.dumps([d for d in duration_dots if d['perf'] != 'On Time'])};

  const canvas = document.getElementById('chart3');
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();

  new Chart(canvas, {{
    type: 'scatter',
    data: {{
      datasets: [
        {{
          label: 'On Time',
          data: onTimeDots.map(d => ({{ x: d.x, y: d.y, focus: d.focus, tsa: d.tsa }})),
          backgroundColor: '#10b98166',
          borderColor: '#10b981',
          pointRadius: 5,
          pointHoverRadius: 8
        }},
        {{
          label: 'Late / Overdue',
          data: lateDots.map(d => ({{ x: d.x, y: d.y, focus: d.focus, tsa: d.tsa }})),
          backgroundColor: '#ef444466',
          borderColor: '#ef4444',
          pointRadius: 5,
          pointHoverRadius: 8
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        tooltip: {{
          callbacks: {{
            label: ctx => {{
              const pt = ctx.raw;
              return pt.tsa + ': ' + pt.focus + ' (' + pt.y + 'd)';
            }}
          }}
        }},
        legend: {{ position: 'top', labels: {{ usePointStyle: true, pointStyle: 'circle' }} }}
      }},
      scales: {{
        x: {{
          type: 'time',
          time: {{ unit: 'week', displayFormats: {{ week: 'MMM dd' }} }},
          title: {{ display: true, text: 'Date Added', font: {{ weight: '600' }} }},
          grid: {{ color: '#f1f5f9' }}
        }},
        y: {{
          title: {{ display: true, text: 'Duration (days)', font: {{ weight: '600' }} }},
          grid: {{ color: '#f1f5f9' }},
          beginAtZero: true
        }}
      }}
    }}
  }});
}})();
</script>

</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Saved: {OUTPUT}")
