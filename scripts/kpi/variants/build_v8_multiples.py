"""Build V8 — Small Multiples Grid Dashboard (Tufte-inspired)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V8_MULTIPLES.html')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# ── Filter core period ──────────────────────────────────────────────
def parse_week(w):
    m = re.match(r'(\d{2})-(\d{2})\s+W\.(\d+)', w)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def in_core(week):
    parsed = parse_week(week)
    if not parsed:
        return False
    y, mo, _ = parsed
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

def week_sort_key(w):
    parsed = parse_week(w)
    if not parsed:
        return (0, 0, 0)
    return parsed

data = [r for r in raw_data if in_core(r['week'])]

# ── People, weeks, KPIs ─────────────────────────────────────────────
PEOPLE = ['ALEXANDRA', 'CARLOS', 'DIEGO', 'GABI', 'THIAGO', 'THAIS', 'YASMIM']
KPIS = ['ETA Accuracy', 'Avg Duration', 'Reliability']
TARGETS = {'ETA Accuracy': 90, 'Avg Duration': 28, 'Reliability': 85}
# For Avg Duration, lower is better; for the others, higher is better
LOWER_BETTER = {'Avg Duration'}

all_weeks = sorted(set(r['week'] for r in data), key=week_sort_key)

def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d')
    except Exception:
        return None

# ── Compute per-person per-week KPIs (cumulative up to that week) ───
def compute_kpis_for(tasks):
    """Return dict with the three KPIs for a set of tasks."""
    on_time = sum(1 for r in tasks if r['perf'] == 'On Time')
    late = sum(1 for r in tasks if r['perf'] == 'Late')
    overdue = sum(1 for r in tasks if r['perf'] == 'Overdue')

    eta_acc = round(on_time / (on_time + late) * 100, 1) if (on_time + late) > 0 else None
    reliability = round(on_time / (on_time + late + overdue) * 100, 1) if (on_time + late + overdue) > 0 else None

    durations = []
    for r in tasks:
        if r['status'] == 'Done':
            d_add = parse_date(r.get('dateAdd', ''))
            d_del = parse_date(r.get('delivery', ''))
            if d_add and d_del:
                dur = (d_del - d_add).days
                if dur >= 0:
                    durations.append(dur)
    avg_dur = round(sum(durations) / len(durations), 1) if durations else None

    return {
        'ETA Accuracy': eta_acc,
        'Avg Duration': avg_dur,
        'Reliability': reliability
    }

# Build weekly data: for each person, compute KPI using tasks up to and including that week
# We use a rolling window (all tasks from start up to current week) for stable trend
person_week_kpis = {}  # person -> kpi -> [values per week]
for p in PEOPLE + ['TEAM']:
    person_week_kpis[p] = {kpi: [] for kpi in KPIS}

for wi, w in enumerate(all_weeks):
    # Cumulative: all tasks from week 0..wi
    weeks_so_far = set(all_weeks[:wi+1])
    for p in PEOPLE:
        tasks_so_far = [r for r in data if r['tsa'] == p and r['week'] in weeks_so_far]
        kpis = compute_kpis_for(tasks_so_far)
        for kpi in KPIS:
            person_week_kpis[p][kpi].append(kpis[kpi])

    # Team overall
    team_tasks = [r for r in data if r['week'] in weeks_so_far]
    team_kpis = compute_kpis_for(team_tasks)
    for kpi in KPIS:
        person_week_kpis['TEAM'][kpi].append(team_kpis[kpi])

# ── Current (latest) values and overall performance ─────────────────
current_values = {}
overall_status = {}  # 'above' or 'below' target
for p in PEOPLE + ['TEAM']:
    current_values[p] = {}
    overall_status[p] = {}
    for kpi in KPIS:
        vals = [v for v in person_week_kpis[p][kpi] if v is not None]
        cur = vals[-1] if vals else None
        current_values[p][kpi] = cur
        if cur is not None:
            if kpi in LOWER_BETTER:
                overall_status[p][kpi] = 'above' if cur <= TARGETS[kpi] else 'below'
            else:
                overall_status[p][kpi] = 'above' if cur >= TARGETS[kpi] else 'below'
        else:
            overall_status[p][kpi] = 'none'

# ── Composite score per person ──────────────────────────────────────
# Score: average of (value / target) capped at 1.0 for higher-is-better,
#        or (target / value) capped at 1.0 for lower-is-better
def composite_score(person):
    scores = []
    for kpi in KPIS:
        cur = current_values[person][kpi]
        if cur is None or cur == 0:
            scores.append(0)
            continue
        t = TARGETS[kpi]
        if kpi in LOWER_BETTER:
            s = min(t / cur, 1.0) if cur > 0 else 0
        else:
            s = min(cur / t, 1.0)
        scores.append(s)
    return round(sum(scores) / len(scores) * 100, 0) if scores else 0

composites = {p: composite_score(p) for p in PEOPLE + ['TEAM']}

# ── Week labels for axes ────────────────────────────────────────────
week_labels = []
for w in all_weeks:
    parsed = parse_week(w)
    if parsed:
        y, mo, wn = parsed
        month_names = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
                       7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
        week_labels.append(f"{month_names.get(mo,'?')} W{wn}")
    else:
        week_labels.append(w)

# ── Serialize to JSON ────────────────────────────────────────────────
js_data = json.dumps(person_week_kpis)
js_current = json.dumps(current_values)
js_status = json.dumps(overall_status)
js_composites = json.dumps(composites)
js_labels = json.dumps(week_labels)
js_people = json.dumps(PEOPLE)
js_kpis = json.dumps(KPIS)
js_targets = json.dumps(TARGETS)
js_lower_better = json.dumps(list(LOWER_BETTER))

num_weeks = len(all_weeks)
num_records = len(data)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V8 Small Multiples Grid</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: #ffffff; color: #1b1b1b;
  padding: 20px 24px; min-height: 100vh;
}}
.header {{
  background: #0f172a; color: #fff; padding: 16px 24px; border-radius: 8px;
  margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;
}}
.header h1 {{ font-size: 1.2em; font-weight: 700; }}
.header .sub {{ font-size: 0.78em; color: #94a3b8; }}

.subtitle {{
  font-size: 0.82em; color: #64748b; margin-bottom: 16px;
  font-style: italic; text-align: center;
}}

/* Main grid: rows=people+team, cols=KPIs+composite */
.grid-container {{
  display: grid;
  grid-template-columns: 100px repeat(3, 1fr) 72px;
  grid-template-rows: auto;
  gap: 0;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}}

/* Header row */
.grid-header {{
  background: #f1f5f9;
  font-size: 0.72em;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 10px 8px;
  text-align: center;
  border-bottom: 2px solid #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
}}

/* Person name cell */
.person-cell {{
  background: #f8fafc;
  font-size: 0.78em;
  font-weight: 700;
  color: #334155;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  border-right: 1px solid #e2e8f0;
}}
.person-cell.team {{
  background: #0f172a;
  color: #fff;
  font-weight: 800;
  border-top: 2px solid #334155;
}}

/* Sparkline cell */
.spark-cell {{
  padding: 6px 8px;
  border-bottom: 1px solid #e2e8f0;
  border-right: 1px solid #e2e8f0;
  position: relative;
  min-height: 72px;
}}
.spark-cell.above {{ background: #f0fdf4; }}
.spark-cell.below {{ background: #fef2f2; }}
.spark-cell.none {{ background: #f9fafb; }}
.spark-cell.team-cell {{
  border-top: 2px solid #334155;
}}

.spark-value {{
  position: absolute;
  top: 4px;
  right: 6px;
  font-size: 0.92em;
  font-weight: 800;
  color: #1b1b1b;
  z-index: 2;
}}
.spark-value.good {{ color: #059669; }}
.spark-value.bad {{ color: #dc2626; }}
.spark-value.na {{ color: #94a3b8; font-weight: 600; }}

.spark-target {{
  position: absolute;
  bottom: 2px;
  left: 6px;
  font-size: 0.58em;
  color: #94a3b8;
  z-index: 2;
}}

.spark-canvas {{
  width: 100%;
  height: 48px;
  margin-top: 14px;
}}

/* Composite cell */
.comp-cell {{
  padding: 6px 8px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}}
.comp-cell.team-cell {{
  border-top: 2px solid #334155;
}}
.comp-val {{
  font-size: 1.2em;
  font-weight: 800;
}}
.comp-label {{
  font-size: 0.55em;
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.3px;
}}

footer {{
  text-align: center; font-size: 0.7em; color: #94a3b8; margin-top: 20px; padding: 12px 0;
  border-top: 1px solid #e2e8f0;
}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>V8 -- Small Multiples Grid</h1>
    <div class="sub">TSA Team Performance | Dec 2025 -- Mar 2026 | {num_records} records | {num_weeks} weeks</div>
  </div>
  <div style="text-align:right">
    <div class="sub">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    <div class="sub">Edward Tufte-inspired sparkline grid</div>
  </div>
</div>

<div class="subtitle">"At a glance, see every person's trajectory on every KPI"</div>

<div class="grid-container" id="grid"></div>

<footer>TSA CORTEX -- V8 Small Multiples Grid Dashboard | Targets: ETA Accuracy > 90% | Avg Duration < 28d | Reliability > 85%</footer>

<script>
const PEOPLE = {js_people};
const ALL_ROWS = [...PEOPLE, 'TEAM'];
const KPIS = {js_kpis};
const TARGETS = {js_targets};
const LOWER_BETTER = new Set({js_lower_better});
const weekLabels = {js_labels};
const personWeekKpis = {js_data};
const currentValues = {js_current};
const overallStatus = {js_status};
const composites = {js_composites};

Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";

const grid = document.getElementById('grid');

// ── Build header row ──
// Corner cell
const corner = document.createElement('div');
corner.className = 'grid-header';
corner.textContent = 'Person';
grid.appendChild(corner);

KPIS.forEach(kpi => {{
  const h = document.createElement('div');
  h.className = 'grid-header';
  const unit = kpi === 'Avg Duration' ? ' (days)' : ' (%)';
  const target = TARGETS[kpi];
  const dir = LOWER_BETTER.has(kpi) ? '<' : '>';
  h.innerHTML = kpi + '<br><span style="font-weight:400;font-size:0.85em;color:#94a3b8;">Target: ' + dir + ' ' + target + unit + '</span>';
  grid.appendChild(h);
}});

const compH = document.createElement('div');
compH.className = 'grid-header';
compH.textContent = 'Score';
grid.appendChild(compH);

// ── Build rows ──
let canvasId = 0;
const chartConfigs = [];

ALL_ROWS.forEach(person => {{
  const isTeam = person === 'TEAM';

  // Person name cell
  const nameCell = document.createElement('div');
  nameCell.className = 'person-cell' + (isTeam ? ' team' : '');
  nameCell.textContent = person;
  grid.appendChild(nameCell);

  // One sparkline cell per KPI
  KPIS.forEach(kpi => {{
    const cell = document.createElement('div');
    const status = overallStatus[person][kpi];
    cell.className = 'spark-cell ' + status + (isTeam ? ' team-cell' : '');

    // Current value badge
    const curVal = currentValues[person][kpi];
    const valSpan = document.createElement('span');
    if (curVal !== null && curVal !== undefined) {{
      const unit = kpi === 'Avg Duration' ? 'd' : '%';
      valSpan.textContent = curVal + unit;
      const isGood = LOWER_BETTER.has(kpi) ? curVal <= TARGETS[kpi] : curVal >= TARGETS[kpi];
      valSpan.className = 'spark-value ' + (isGood ? 'good' : 'bad');
    }} else {{
      valSpan.textContent = 'N/A';
      valSpan.className = 'spark-value na';
    }}
    cell.appendChild(valSpan);

    // Target label
    const targetSpan = document.createElement('span');
    const dir = LOWER_BETTER.has(kpi) ? '<' : '>';
    targetSpan.className = 'spark-target';
    targetSpan.textContent = 'T:' + dir + TARGETS[kpi];
    cell.appendChild(targetSpan);

    // Canvas
    const cId = 'spark_' + (canvasId++);
    const canvas = document.createElement('canvas');
    canvas.id = cId;
    canvas.className = 'spark-canvas';
    cell.appendChild(canvas);

    grid.appendChild(cell);

    // Store config for later chart creation
    const values = personWeekKpis[person][kpi];
    chartConfigs.push({{ id: cId, values: values, target: TARGETS[kpi], kpi: kpi }});
  }});

  // Composite score cell
  const compCell = document.createElement('div');
  compCell.className = 'comp-cell' + (isTeam ? ' team-cell' : '');
  const score = composites[person];
  const compVal = document.createElement('div');
  compVal.className = 'comp-val';
  compVal.textContent = Math.round(score) + '%';
  compVal.style.color = score >= 80 ? '#059669' : score >= 60 ? '#d97706' : '#dc2626';
  compCell.appendChild(compVal);
  const compLbl = document.createElement('div');
  compLbl.className = 'comp-label';
  compLbl.textContent = 'composite';
  compCell.appendChild(compLbl);
  grid.appendChild(compCell);
}});

// ── Create all sparkline charts ──
chartConfigs.forEach(cfg => {{
  const canvas = document.getElementById(cfg.id);
  if (!canvas) return;

  // Replace nulls with NaN for Chart.js spanGaps
  const chartData = cfg.values.map(v => v === null ? NaN : v);

  new Chart(canvas, {{
    type: 'line',
    data: {{
      labels: weekLabels,
      datasets: [
        {{
          data: chartData,
          borderColor: '#334155',
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 3,
          fill: false,
          tension: 0.3,
          spanGaps: true
        }},
        {{
          // Target line
          data: Array(weekLabels.length).fill(cfg.target),
          borderColor: '#ef4444',
          borderWidth: 1,
          borderDash: [4, 3],
          pointRadius: 0,
          pointHoverRadius: 0,
          fill: false
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          enabled: true,
          mode: 'index',
          intersect: false,
          filter: item => item.datasetIndex === 0,
          callbacks: {{
            title: items => items.length ? items[0].label : '',
            label: ctx => {{
              const v = ctx.raw;
              if (isNaN(v)) return 'N/A';
              const unit = cfg.kpi === 'Avg Duration' ? 'd' : '%';
              return cfg.kpi + ': ' + v + unit;
            }}
          }},
          bodyFont: {{ size: 10 }},
          titleFont: {{ size: 10 }},
          padding: 4
        }}
      }},
      scales: {{
        x: {{
          display: false
        }},
        y: {{
          display: false,
          beginAtZero: cfg.kpi !== 'Avg Duration',
          suggestedMin: cfg.kpi === 'Avg Duration' ? 0 : 0,
          suggestedMax: cfg.kpi === 'Avg Duration' ? undefined : 100
        }}
      }},
      layout: {{ padding: {{ top: 0, bottom: 0, left: 0, right: 0 }} }}
    }}
  }});
}});
</script>

</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Saved: {OUTPUT}")
