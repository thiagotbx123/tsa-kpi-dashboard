"""Build TSA KPI Dashboard V5 — Task Outcome Composition."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V5_COMPOSITION.html')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data_json = f.read()

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V5 — Task Outcome Composition</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#f8fafc;color:#1b1b1b;padding:24px 36px;min-height:100vh;font-size:15px;line-height:1.5}

.header{background:#1b1b1b;color:#fff;padding:20px 28px;border-radius:10px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between}
.header h1{font-size:1.35em;font-weight:700}
.header .sub{font-size:.82em;color:#9ca3af}

.section{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:20px 24px;margin-bottom:20px}
.section h2{font-size:1em;font-weight:700;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.section h2 .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.section .desc{font-size:.78em;color:#6b7280;margin-bottom:14px}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}

.chart-box{position:relative;width:100%;height:400px}
.chart-box.tall{height:500px}
.chart-box.short{height:320px}
.chart-box.donut{height:350px;max-width:400px;margin:0 auto}

.legend-row{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0 8px;justify-content:center}
.legend-item{display:flex;align-items:center;gap:5px;font-size:.76em;color:#6b7280}
.legend-swatch{width:12px;height:12px;border-radius:3px;flex-shrink:0}

.summary-strip{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:20px}
.summary-card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:10px 14px;text-align:center}
.summary-card .label{font-size:.68em;color:#6b7280;text-transform:uppercase;font-weight:600;letter-spacing:.3px}
.summary-card .val{font-size:1.5em;font-weight:800;line-height:1.3}

@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}.summary-strip{grid-template-columns:repeat(3,1fr)}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>V5 — Task Outcome Composition</h1>
    <div class="sub">100% stacked analysis: where are the problems?</div>
  </div>
  <div class="sub" id="periodLabel"></div>
</div>

<div class="summary-strip" id="summaryStrip"></div>

<div class="legend-row" id="globalLegend"></div>

<div class="section">
  <h2><span class="dot" style="background:#2563eb"></span> Per-Person Outcome Breakdown</h2>
  <div class="desc">100% stacked horizontal bars — proportion of each outcome per team member</div>
  <div class="chart-box tall"><canvas id="chartPerson"></canvas></div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#7c3aed"></span> Weekly Team Composition</h2>
  <div class="desc">100% stacked vertical bars — how the team-wide outcome mix changes each week</div>
  <div class="chart-box tall"><canvas id="chartWeekly"></canvas></div>
</div>

<div class="grid2">
  <div class="section">
    <h2><span class="dot" style="background:#059669"></span> Overall Distribution</h2>
    <div class="desc">Team-wide outcome donut</div>
    <div class="chart-box donut"><canvas id="chartDonut"></canvas></div>
  </div>
  <div class="section">
    <h2><span class="dot" style="background:#dc2626"></span> Internal vs External</h2>
    <div class="desc">Same breakdown split by category</div>
    <div class="chart-box"><canvas id="chartIntExt"></canvas></div>
  </div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#f59e0b"></span> Customer On-Time Rates</h2>
  <div class="desc">Which customers have the worst on-time performance? Sorted worst to best. Only customers with 3+ tasks shown.</div>
  <div class="chart-box tall"><canvas id="chartCustomer"></canvas></div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#9333ea"></span> Demand Type KPI Comparison</h2>
  <div class="desc">Internal vs External(Customer) and other demand types — KPI side by side</div>
  <div class="chart-box"><canvas id="chartDemand"></canvas></div>
</div>

<script>
const RAW = __DATA__;

// --- Week filter: core period Dec 2025 - Mar 2026 ---
const WK_RE = /(\d{2})-(\d{2})\s+W\.(\d+)/;
function parseWeek(w) {
  const m = w.match(WK_RE);
  if (!m) return null;
  const y = parseInt(m[1]), mo = parseInt(m[2]), wn = parseInt(m[3]);
  return {y, mo, wn, sort: y*10000 + mo*100 + wn};
}
function inPeriod(w) {
  const p = parseWeek(w);
  if (!p) return false;
  return (p.y === 25 && p.mo >= 12) || (p.y === 26 && p.mo <= 3);
}

const DATA = RAW.filter(r => inPeriod(r.week));

// --- Constants ---
const PERF_ORDER = ['On Time', 'Late', 'Overdue', 'No ETA', 'On Track', 'No Delivery Date', 'N/A'];
const COLORS = {
  'On Time': '#059669',
  'Late': '#dc2626',
  'Overdue': '#f59e0b',
  'No ETA': '#9ca3af',
  'On Track': '#3b82f6',
  'No Delivery Date': '#d1d5db',
  'N/A': '#e5e7eb'
};
const OTHER_COLOR = '#d1d5db';
const PEOPLE = ['ALEXANDRA','CARLOS','DIEGO','GABI','THIAGO','THAIS','YASMIM'];

// --- Helpers ---
function countPerf(arr) {
  const c = {};
  PERF_ORDER.forEach(p => c[p] = 0);
  arr.forEach(r => { c[r.perf] = (c[r.perf] || 0) + 1; });
  return c;
}
function pct(n, d) { return d ? Math.round(n / d * 1000) / 10 : 0; }

// --- Summary strip ---
(function() {
  const counts = countPerf(DATA);
  const total = DATA.length;
  const strip = document.getElementById('summaryStrip');
  const items = [
    {label: 'Total Tasks', val: total, color: '#1b1b1b'},
    {label: 'On Time', val: counts['On Time'], color: '#059669'},
    {label: 'Late', val: counts['Late'], color: '#dc2626'},
    {label: 'Overdue', val: counts['Overdue'], color: '#f59e0b'},
    {label: 'On Track', val: counts['On Track'], color: '#3b82f6'},
    {label: 'No ETA', val: counts['No ETA'], color: '#9ca3af'}
  ];
  items.forEach(it => {
    const d = document.createElement('div');
    d.className = 'summary-card';
    d.innerHTML = '<div class="label">' + it.label + '</div><div class="val" style="color:' + it.color + '">' + it.val + '</div>';
    strip.appendChild(d);
  });
})();

// --- Global legend ---
(function() {
  const leg = document.getElementById('globalLegend');
  PERF_ORDER.forEach(p => {
    const d = document.createElement('div');
    d.className = 'legend-item';
    d.innerHTML = '<div class="legend-swatch" style="background:' + (COLORS[p] || OTHER_COLOR) + '"></div>' + p;
    leg.appendChild(d);
  });
})();

// --- Period label ---
(function() {
  const weeks = [...new Set(DATA.map(r => r.week))].filter(w => parseWeek(w)).sort((a, b) => parseWeek(a).sort - parseWeek(b).sort);
  document.getElementById('periodLabel').textContent = DATA.length + ' tasks | ' + weeks[0] + ' to ' + weeks[weeks.length - 1];
})();

// ============ CHART 1: Per-Person 100% stacked horizontal ============
(function() {
  const datasets = PERF_ORDER.map(perf => ({
    label: perf,
    data: PEOPLE.map(person => {
      const tasks = DATA.filter(r => r.tsa === person);
      const total = tasks.length;
      const count = tasks.filter(r => r.perf === perf).length;
      return total ? Math.round(count / total * 1000) / 10 : 0;
    }),
    backgroundColor: COLORS[perf] || OTHER_COLOR,
    borderWidth: 0,
    borderSkipped: false
  }));
  new Chart(document.getElementById('chartPerson'), {
    type: 'bar',
    data: { labels: PEOPLE, datasets },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { stacked: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } },
        y: { stacked: true, grid: { display: false } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const person = PEOPLE[ctx.dataIndex];
              const tasks = DATA.filter(r => r.tsa === person);
              const count = tasks.filter(r => r.perf === ctx.dataset.label).length;
              return ctx.dataset.label + ': ' + ctx.raw + '% (' + count + '/' + tasks.length + ')';
            }
          }
        }
      }
    }
  });
})();

// ============ CHART 2: Weekly 100% stacked vertical ============
(function() {
  const weeks = [...new Set(DATA.map(r => r.week))].filter(w => parseWeek(w)).sort((a, b) => parseWeek(a).sort - parseWeek(b).sort);
  const datasets = PERF_ORDER.map(perf => ({
    label: perf,
    data: weeks.map(wk => {
      const tasks = DATA.filter(r => r.week === wk);
      const total = tasks.length;
      const count = tasks.filter(r => r.perf === perf).length;
      return total ? Math.round(count / total * 1000) / 10 : 0;
    }),
    backgroundColor: COLORS[perf] || OTHER_COLOR,
    borderWidth: 0
  }));
  new Chart(document.getElementById('chartWeekly'), {
    type: 'bar',
    data: { labels: weeks, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 45 } },
        y: { stacked: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const wk = weeks[ctx.dataIndex];
              const tasks = DATA.filter(r => r.week === wk);
              const count = tasks.filter(r => r.perf === ctx.dataset.label).length;
              return ctx.dataset.label + ': ' + ctx.raw + '% (' + count + '/' + tasks.length + ')';
            }
          }
        }
      }
    }
  });
})();

// ============ CHART 3: Overall donut ============
(function() {
  const counts = countPerf(DATA);
  const total = DATA.length;
  new Chart(document.getElementById('chartDonut'), {
    type: 'doughnut',
    data: {
      labels: PERF_ORDER,
      datasets: [{
        data: PERF_ORDER.map(p => counts[p]),
        backgroundColor: PERF_ORDER.map(p => COLORS[p] || OTHER_COLOR),
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '55%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 14, usePointStyle: true, pointStyle: 'rectRounded', font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => ctx.label + ': ' + ctx.raw + ' (' + pct(ctx.raw, total) + '%)'
          }
        }
      }
    }
  });
})();

// ============ CHART 4: Internal vs External ============
(function() {
  const categories = ['Internal', 'External'];
  const datasets = PERF_ORDER.map(perf => ({
    label: perf,
    data: categories.map(cat => {
      const tasks = DATA.filter(r => r.category === cat);
      const total = tasks.length;
      const count = tasks.filter(r => r.perf === perf).length;
      return total ? Math.round(count / total * 1000) / 10 : 0;
    }),
    backgroundColor: COLORS[perf] || OTHER_COLOR,
    borderWidth: 0
  }));
  new Chart(document.getElementById('chartIntExt'), {
    type: 'bar',
    data: { labels: categories, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const cat = categories[ctx.dataIndex];
              const tasks = DATA.filter(r => r.category === cat);
              const count = tasks.filter(r => r.perf === ctx.dataset.label).length;
              return ctx.dataset.label + ': ' + ctx.raw + '% (' + count + '/' + tasks.length + ')';
            }
          }
        }
      }
    }
  });
})();

// ============ CHART 5: Customer on-time rates ============
(function() {
  const custMap = {};
  DATA.forEach(r => {
    const c = r.customer && r.customer.trim() ? r.customer.trim() : '(none)';
    if (!custMap[c]) custMap[c] = { total: 0, onTime: 0, late: 0, overdue: 0 };
    custMap[c].total++;
    if (r.perf === 'On Time') custMap[c].onTime++;
    if (r.perf === 'Late') custMap[c].late++;
    if (r.perf === 'Overdue') custMap[c].overdue++;
  });
  // Filter to 3+ tasks, sort by on-time rate ascending (worst first)
  let customers = Object.entries(custMap).filter(([, v]) => v.total >= 3);
  customers.sort((a, b) => (a[1].onTime / a[1].total) - (b[1].onTime / b[1].total));
  const labels = customers.map(([k, v]) => k + ' (' + v.total + ')');
  const dsOnTime = customers.map(([, v]) => pct(v.onTime, v.total));
  const dsLate = customers.map(([, v]) => pct(v.late, v.total));
  const dsOverdue = customers.map(([, v]) => pct(v.overdue, v.total));
  const dsOther = customers.map(([, v]) => Math.round((100 - pct(v.onTime, v.total) - pct(v.late, v.total) - pct(v.overdue, v.total)) * 10) / 10);

  new Chart(document.getElementById('chartCustomer'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'On Time', data: dsOnTime, backgroundColor: '#059669', borderWidth: 0 },
        { label: 'Late', data: dsLate, backgroundColor: '#dc2626', borderWidth: 0 },
        { label: 'Overdue', data: dsOverdue, backgroundColor: '#f59e0b', borderWidth: 0 },
        { label: 'Other', data: dsOther, backgroundColor: '#d1d5db', borderWidth: 0 }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { stacked: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } },
        y: { stacked: true, grid: { display: false }, ticks: { font: { size: 11 } } }
      },
      plugins: {
        legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'rectRounded', padding: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => ctx.dataset.label + ': ' + ctx.raw + '%'
          }
        }
      }
    }
  });
})();

// ============ CHART 6: Demand Type KPI comparison ============
(function() {
  const demandTypes = [...new Set(DATA.map(r => r.demandType))].filter(Boolean).sort();

  function calcKpis(tasks) {
    const onTime = tasks.filter(r => r.perf === 'On Time').length;
    const late = tasks.filter(r => r.perf === 'Late').length;
    const overdue = tasks.filter(r => r.perf === 'Overdue').length;
    const etaAcc = (onTime + late) > 0 ? Math.round(onTime / (onTime + late) * 1000) / 10 : 0;
    const reliability = (onTime + late + overdue) > 0 ? Math.round(onTime / (onTime + late + overdue) * 1000) / 10 : 0;

    // Avg implementation days
    let durations = [];
    tasks.forEach(r => {
      if (r.status === 'Done' && r.delivery && r.dateAdd && r.delivery !== '' && r.dateAdd !== '') {
        const d1 = new Date(r.dateAdd), d2 = new Date(r.delivery);
        const diff = (d2 - d1) / 86400000;
        if (diff >= 0) durations.push(diff);
      }
    });
    const avgDays = durations.length ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length * 10) / 10 : null;
    return { etaAcc, reliability, avgDays, count: tasks.length };
  }

  const kpis = demandTypes.map(dt => ({ dt, ...calcKpis(DATA.filter(r => r.demandType === dt)) }));
  kpis.sort((a, b) => b.count - a.count);

  const labels = kpis.map(k => k.dt + ' (' + k.count + ')');

  new Chart(document.getElementById('chartDemand'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'ETA Accuracy %',
          data: kpis.map(k => k.etaAcc),
          backgroundColor: '#2563eb',
          borderWidth: 0
        },
        {
          label: 'Reliability %',
          data: kpis.map(k => k.reliability),
          backgroundColor: '#059669',
          borderWidth: 0
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } }
      },
      plugins: {
        legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'rectRounded', padding: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            afterLabel: ctx => {
              const k = kpis[ctx.dataIndex];
              return k.avgDays !== null ? 'Avg Speed: ' + k.avgDays + ' days' : 'Avg Speed: N/A';
            }
          }
        }
      }
    }
  });
})();
</script>
</body>
</html>"""

html = HTML.replace('__DATA__', data_json)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Saved: {OUTPUT}')
