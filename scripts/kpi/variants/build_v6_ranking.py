"""Build TSA KPI Dashboard V6 — Ranking & Benchmarking."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V6_RANKING.html')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data_json = f.read()

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V6 — Ranking & Benchmarking</title>
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

.chart-box{position:relative;width:100%;height:380px}
.chart-box.tall{height:440px}
.chart-box.short{height:300px}

/* Ranking Table */
.rank-table{width:100%;border-collapse:collapse;font-size:.88em;margin-top:8px}
.rank-table th{background:#f3f4f6;padding:10px 14px;text-align:left;font-weight:700;font-size:.78em;text-transform:uppercase;letter-spacing:.4px;color:#6b7280;border-bottom:2px solid #e5e7eb}
.rank-table td{padding:10px 14px;border-bottom:1px solid #f3f4f6}
.rank-table tr:hover td{background:#f8fafc}
.rank-table .rank-1{background:#fef9c3}
.rank-table .rank-2{background:#f3f4f6}
.rank-table .rank-3{background:#fff7ed}
.medal{font-size:1.1em;margin-right:4px}
.score-bar{display:inline-block;height:8px;border-radius:4px;vertical-align:middle;margin-right:6px}

/* Gap pills */
.gap-pos{color:#059669;font-weight:700;font-size:.85em}
.gap-neg{color:#dc2626;font-weight:700;font-size:.85em}
.gap-zero{color:#6b7280;font-size:.85em}

@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Raccoons Team Ranking</h1>
    <div class="sub">Who's best? Ranked comparison with team benchmarks.</div>
  </div>
  <div class="sub" id="periodLabel"></div>
</div>

<div class="grid3">
  <div class="section">
    <h2><span class="dot" style="background:#2563eb"></span> KPI 1: ETA Accuracy</h2>
    <div class="desc">On Time / (On Time + Late). Target: >90%</div>
    <div class="chart-box short"><canvas id="chartKpi1"></canvas></div>
  </div>
  <div class="section">
    <h2><span class="dot" style="background:#059669"></span> KPI 2: Avg Speed (days)</h2>
    <div class="desc">Avg(delivery - dateAdd) for Done tasks. Target: <28 days</div>
    <div class="chart-box short"><canvas id="chartKpi2"></canvas></div>
  </div>
  <div class="section">
    <h2><span class="dot" style="background:#7c3aed"></span> KPI 3: Reliability</h2>
    <div class="desc">On Time / (On Time + Late + Overdue). Target: >85%</div>
    <div class="chart-box short"><canvas id="chartKpi3"></canvas></div>
  </div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#f59e0b"></span> Composite Score & Overall Ranking</h2>
  <div class="desc">Weighted: ETA Accuracy 35% + Speed 30% + Reliability 35%. Speed is normalized (lower = better).</div>
  <div class="chart-box"><canvas id="chartComposite"></canvas></div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#1b1b1b"></span> Ranking Table</h2>
  <div class="desc">Full breakdown with medal awards and gap analysis</div>
  <div id="rankTableContainer"></div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#dc2626"></span> Gap Analysis</h2>
  <div class="desc">Distance from target for each KPI (positive = above target, negative = below)</div>
  <div class="chart-box tall"><canvas id="chartGap"></canvas></div>
</div>

<div class="section">
  <h2><span class="dot" style="background:#9333ea"></span> Month-by-Month Rank Evolution</h2>
  <div class="desc">How each person's composite rank changed over the months</div>
  <div class="chart-box tall"><canvas id="chartEvolution"></canvas></div>
</div>

<script>
const RAW = __DATA__;

// --- Week filter ---
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
function monthLabel(y, mo) {
  const names = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return names[mo] + ' ' + (y < 50 ? '20' + y : '19' + y);
}

const DATA = RAW.filter(r => inPeriod(r.week));
const PEOPLE = ['ALEXANDRA','CARLOS','DIEGO','GABI','THIAGO','THAIS','YASMIM'];
const PERSON_COLORS = {
  ALEXANDRA: '#2563eb', CARLOS: '#059669', DIEGO: '#dc2626', GABI: '#f59e0b',
  THIAGO: '#7c3aed', THAIS: '#ec4899', YASMIM: '#0891b2'
};

// --- Period label ---
(function() {
  const weeks = [...new Set(DATA.map(r => r.week))].filter(w => parseWeek(w)).sort((a, b) => parseWeek(a).sort - parseWeek(b).sort);
  document.getElementById('periodLabel').textContent = DATA.length + ' tasks | ' + weeks[0] + ' to ' + weeks[weeks.length - 1];
})();

// --- KPI Calculation ---
function calcKpis(tasks) {
  const onTime = tasks.filter(r => r.perf === 'On Time').length;
  const late = tasks.filter(r => r.perf === 'Late').length;
  const overdue = tasks.filter(r => r.perf === 'Overdue').length;
  const etaAcc = (onTime + late) > 0 ? onTime / (onTime + late) * 100 : null;
  const reliability = (onTime + late + overdue) > 0 ? onTime / (onTime + late + overdue) * 100 : null;

  let durations = [];
  tasks.forEach(r => {
    if (r.status === 'Done' && r.delivery && r.dateAdd && r.delivery !== '' && r.dateAdd !== '') {
      const d1 = new Date(r.dateAdd), d2 = new Date(r.delivery);
      const diff = (d2 - d1) / 86400000;
      if (diff >= 0) durations.push(diff);
    }
  });
  const avgDays = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : null;
  return { etaAcc, avgDays, reliability, count: tasks.length };
}

// --- Per-person KPIs ---
const personKpis = {};
PEOPLE.forEach(p => {
  personKpis[p] = calcKpis(DATA.filter(r => r.tsa === p));
});

// Team averages
const teamKpis = calcKpis(DATA);

// --- Sort helpers ---
function rankBy(key, ascending) {
  const entries = PEOPLE.map(p => ({ person: p, val: personKpis[p][key] })).filter(e => e.val !== null);
  entries.sort((a, b) => ascending ? a.val - b.val : b.val - a.val);
  return entries;
}

// --- Targets ---
const TARGET_ETA = 90;
const TARGET_SPEED = 28;
const TARGET_REL = 85;

// --- Medal helper ---
function medal(rank) {
  if (rank === 1) return '\ud83e\udd47';
  if (rank === 2) return '\ud83e\udd48';
  if (rank === 3) return '\ud83e\udd49';
  return '';
}

// ============ CHART: KPI 1 - ETA Accuracy ============
(function() {
  const sorted = rankBy('etaAcc', false); // higher is better
  const labels = sorted.map((e, i) => medal(i + 1) + ' ' + e.person);
  const vals = sorted.map(e => Math.round(e.val * 10) / 10);
  const colors = sorted.map(e => PERSON_COLORS[e.person]);

  new Chart(document.getElementById('chartKpi1'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: vals,
        backgroundColor: colors,
        borderWidth: 0,
        borderRadius: 4,
        barThickness: 28
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: {
          beginAtZero: true, max: 100,
          ticks: { callback: v => v + '%' },
          grid: { color: '#f3f4f6' }
        },
        y: { grid: { display: false } }
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ctx.raw + '%' } },
        annotation: undefined
      }
    },
    plugins: [{
      id: 'targetLine',
      afterDraw(chart) {
        const xScale = chart.scales.x;
        const x = xScale.getPixelForValue(TARGET_ETA);
        const ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = '#dc2626';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(x, chart.chartArea.top);
        ctx.lineTo(x, chart.chartArea.bottom);
        ctx.stroke();
        // Team avg
        const xAvg = xScale.getPixelForValue(teamKpis.etaAcc);
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(xAvg, chart.chartArea.top);
        ctx.lineTo(xAvg, chart.chartArea.bottom);
        ctx.stroke();
        // Labels
        ctx.fillStyle = '#dc2626';
        ctx.font = '10px Segoe UI';
        ctx.fillText('Target ' + TARGET_ETA + '%', x + 4, chart.chartArea.top + 12);
        ctx.fillStyle = '#6b7280';
        ctx.fillText('Avg ' + Math.round(teamKpis.etaAcc * 10) / 10 + '%', xAvg + 4, chart.chartArea.top + 24);
        ctx.restore();
      }
    }]
  });
})();

// ============ CHART: KPI 2 - Speed (lower = better) ============
(function() {
  const sorted = rankBy('avgDays', true); // lower is better
  const labels = sorted.map((e, i) => medal(i + 1) + ' ' + e.person);
  const vals = sorted.map(e => Math.round(e.val * 10) / 10);
  const colors = sorted.map(e => PERSON_COLORS[e.person]);

  new Chart(document.getElementById('chartKpi2'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: vals,
        backgroundColor: colors,
        borderWidth: 0,
        borderRadius: 4,
        barThickness: 28
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: {
          beginAtZero: true,
          ticks: { callback: v => v + 'd' },
          grid: { color: '#f3f4f6' }
        },
        y: { grid: { display: false } }
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ctx.raw + ' days' } }
      }
    },
    plugins: [{
      id: 'targetLineSpeed',
      afterDraw(chart) {
        const xScale = chart.scales.x;
        const x = xScale.getPixelForValue(TARGET_SPEED);
        const ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = '#dc2626';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(x, chart.chartArea.top);
        ctx.lineTo(x, chart.chartArea.bottom);
        ctx.stroke();
        const xAvg = xScale.getPixelForValue(teamKpis.avgDays);
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(xAvg, chart.chartArea.top);
        ctx.lineTo(xAvg, chart.chartArea.bottom);
        ctx.stroke();
        ctx.fillStyle = '#dc2626';
        ctx.font = '10px Segoe UI';
        ctx.fillText('Target ' + TARGET_SPEED + 'd', x + 4, chart.chartArea.top + 12);
        ctx.fillStyle = '#6b7280';
        ctx.fillText('Avg ' + Math.round(teamKpis.avgDays * 10) / 10 + 'd', xAvg + 4, chart.chartArea.top + 24);
        ctx.restore();
      }
    }]
  });
})();

// ============ CHART: KPI 3 - Reliability ============
(function() {
  const sorted = rankBy('reliability', false); // higher is better
  const labels = sorted.map((e, i) => medal(i + 1) + ' ' + e.person);
  const vals = sorted.map(e => Math.round(e.val * 10) / 10);
  const colors = sorted.map(e => PERSON_COLORS[e.person]);

  new Chart(document.getElementById('chartKpi3'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: vals,
        backgroundColor: colors,
        borderWidth: 0,
        borderRadius: 4,
        barThickness: 28
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: {
          beginAtZero: true, max: 100,
          ticks: { callback: v => v + '%' },
          grid: { color: '#f3f4f6' }
        },
        y: { grid: { display: false } }
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ctx.raw + '%' } }
      }
    },
    plugins: [{
      id: 'targetLineRel',
      afterDraw(chart) {
        const xScale = chart.scales.x;
        const x = xScale.getPixelForValue(TARGET_REL);
        const ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = '#dc2626';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(x, chart.chartArea.top);
        ctx.lineTo(x, chart.chartArea.bottom);
        ctx.stroke();
        const xAvg = xScale.getPixelForValue(teamKpis.reliability);
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(xAvg, chart.chartArea.top);
        ctx.lineTo(xAvg, chart.chartArea.bottom);
        ctx.stroke();
        ctx.fillStyle = '#dc2626';
        ctx.font = '10px Segoe UI';
        ctx.fillText('Target ' + TARGET_REL + '%', x + 4, chart.chartArea.top + 12);
        ctx.fillStyle = '#6b7280';
        ctx.fillText('Avg ' + Math.round(teamKpis.reliability * 10) / 10 + '%', xAvg + 4, chart.chartArea.top + 24);
        ctx.restore();
      }
    }]
  });
})();

// ============ COMPOSITE SCORE ============
// Normalize speed: 0 days = 100, TARGET_SPEED days = target baseline, higher days = lower score
// Formula: speedScore = max(0, 100 - (avgDays / TARGET_SPEED) * 100) ... but we want <28 = good
// Use: speedScore = max(0, (1 - avgDays / (TARGET_SPEED * 2)) * 100) capped at 100
function speedScore(avgDays) {
  if (avgDays === null) return null;
  const s = Math.max(0, (1 - avgDays / (TARGET_SPEED * 2)) * 100);
  return Math.min(100, s);
}

const composites = PEOPLE.map(p => {
  const k = personKpis[p];
  const eta = k.etaAcc !== null ? k.etaAcc : 0;
  const spd = speedScore(k.avgDays);
  const rel = k.reliability !== null ? k.reliability : 0;
  const spdVal = spd !== null ? spd : 0;
  const score = eta * 0.35 + spdVal * 0.30 + rel * 0.35;
  return { person: p, eta, spd: spdVal, rel, score: Math.round(score * 10) / 10 };
});
composites.sort((a, b) => b.score - a.score);

(function() {
  const labels = composites.map((e, i) => medal(i + 1) + ' ' + e.person);
  const vals = composites.map(e => e.score);
  const colors = composites.map(e => PERSON_COLORS[e.person]);

  new Chart(document.getElementById('chartComposite'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Composite Score',
        data: vals,
        backgroundColor: colors,
        borderWidth: 0,
        borderRadius: 4,
        barThickness: 32
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { beginAtZero: true, max: 100, ticks: { callback: v => v }, grid: { color: '#f3f4f6' } },
        y: { grid: { display: false } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: ctx => {
              const c = composites[ctx.dataIndex];
              return 'ETA: ' + Math.round(c.eta * 10) / 10 + '% | Speed: ' + Math.round(c.spd * 10) / 10 + ' | Rel: ' + Math.round(c.rel * 10) / 10 + '%';
            }
          }
        }
      }
    },
    plugins: [{
      id: 'teamAvgComposite',
      afterDraw(chart) {
        const avg = composites.reduce((s, c) => s + c.score, 0) / composites.length;
        const xScale = chart.scales.x;
        const x = xScale.getPixelForValue(avg);
        const ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = '#6b7280';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(x, chart.chartArea.top);
        ctx.lineTo(x, chart.chartArea.bottom);
        ctx.stroke();
        ctx.fillStyle = '#6b7280';
        ctx.font = '10px Segoe UI';
        ctx.fillText('Team Avg ' + Math.round(avg * 10) / 10, x + 4, chart.chartArea.top + 12);
        ctx.restore();
      }
    }]
  });
})();

// ============ RANKING TABLE ============
(function() {
  // Ranks per KPI
  const etaRank = rankBy('etaAcc', false).map((e, i) => ({ ...e, rank: i + 1 }));
  const speedRank = rankBy('avgDays', true).map((e, i) => ({ ...e, rank: i + 1 }));
  const relRank = rankBy('reliability', false).map((e, i) => ({ ...e, rank: i + 1 }));

  function getRank(list, person) {
    const e = list.find(x => x.person === person);
    return e ? e.rank : '-';
  }
  function getVal(list, person) {
    const e = list.find(x => x.person === person);
    return e ? Math.round(e.val * 10) / 10 : '-';
  }

  let html = '<table class="rank-table">';
  html += '<thead><tr><th>Rank</th><th>Person</th><th>ETA Acc. (rank)</th><th>Speed days (rank)</th><th>Reliability (rank)</th><th>Composite</th></tr></thead><tbody>';

  composites.forEach((c, i) => {
    const rank = i + 1;
    const rowClass = rank <= 3 ? ' class="rank-' + rank + '"' : '';
    const m = medal(rank);
    const eR = getRank(etaRank, c.person);
    const eV = getVal(etaRank, c.person);
    const sR = getRank(speedRank, c.person);
    const sV = getVal(speedRank, c.person);
    const rR = getRank(relRank, c.person);
    const rV = getVal(relRank, c.person);

    html += '<tr' + rowClass + '>';
    html += '<td style="font-weight:700;font-size:1.1em;text-align:center">' + m + ' #' + rank + '</td>';
    html += '<td style="font-weight:700">' + c.person + '</td>';
    html += '<td>' + eV + '% <span style="color:#9ca3af;font-size:.8em">(#' + eR + ')</span></td>';
    html += '<td>' + sV + 'd <span style="color:#9ca3af;font-size:.8em">(#' + sR + ')</span></td>';
    html += '<td>' + rV + '% <span style="color:#9ca3af;font-size:.8em">(#' + rR + ')</span></td>';
    html += '<td><span class="score-bar" style="width:' + Math.round(c.score) + 'px;background:' + PERSON_COLORS[c.person] + '"></span><strong>' + c.score + '</strong></td>';
    html += '</tr>';
  });

  html += '</tbody></table>';
  document.getElementById('rankTableContainer').innerHTML = html;
})();

// ============ GAP ANALYSIS ============
(function() {
  const labels = PEOPLE;
  const etaGaps = PEOPLE.map(p => {
    const v = personKpis[p].etaAcc;
    return v !== null ? Math.round((v - TARGET_ETA) * 10) / 10 : 0;
  });
  const speedGaps = PEOPLE.map(p => {
    const v = personKpis[p].avgDays;
    // Negative gap means OVER target (bad), positive means under target (good)
    return v !== null ? Math.round((TARGET_SPEED - v) * 10) / 10 : 0;
  });
  const relGaps = PEOPLE.map(p => {
    const v = personKpis[p].reliability;
    return v !== null ? Math.round((v - TARGET_REL) * 10) / 10 : 0;
  });

  new Chart(document.getElementById('chartGap'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'ETA Accuracy gap (pp)',
          data: etaGaps,
          backgroundColor: etaGaps.map(v => v >= 0 ? '#059669' : '#dc2626'),
          borderWidth: 0,
          borderRadius: 3
        },
        {
          label: 'Speed gap (days to target)',
          data: speedGaps,
          backgroundColor: speedGaps.map(v => v >= 0 ? '#2563eb' : '#f59e0b'),
          borderWidth: 0,
          borderRadius: 3
        },
        {
          label: 'Reliability gap (pp)',
          data: relGaps,
          backgroundColor: relGaps.map(v => v >= 0 ? '#7c3aed' : '#ec4899'),
          borderWidth: 0,
          borderRadius: 3
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false } },
        y: {
          grid: { color: '#f3f4f6' },
          ticks: { callback: v => (v > 0 ? '+' : '') + v }
        }
      },
      plugins: {
        legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'rectRounded', padding: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.raw;
              const sign = v > 0 ? '+' : '';
              const unit = ctx.datasetIndex === 1 ? ' days' : ' pp';
              return ctx.dataset.label + ': ' + sign + v + unit;
            }
          }
        }
      }
    },
    plugins: [{
      id: 'zeroLine',
      afterDraw(chart) {
        const yScale = chart.scales.y;
        const y = yScale.getPixelForValue(0);
        const ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = '#1b1b1b';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(chart.chartArea.left, y);
        ctx.lineTo(chart.chartArea.right, y);
        ctx.stroke();
        ctx.restore();
      }
    }]
  });
})();

// ============ MONTH-BY-MONTH RANK EVOLUTION ============
(function() {
  // Get distinct months from weeks
  const monthSet = new Set();
  DATA.forEach(r => {
    const p = parseWeek(r.week);
    if (p) monthSet.add(p.y * 100 + p.mo);
  });
  const months = [...monthSet].sort();
  const monthLabels = months.map(m => {
    const y = Math.floor(m / 100), mo = m % 100;
    return monthLabel(y, mo);
  });

  // For each month, compute composite rank per person
  const evolutionData = {};
  PEOPLE.forEach(p => { evolutionData[p] = []; });

  months.forEach(m => {
    const y = Math.floor(m / 100), mo = m % 100;
    const monthTasks = DATA.filter(r => {
      const p = parseWeek(r.week);
      return p && p.y === y && p.mo === mo;
    });

    const monthComposites = PEOPLE.map(person => {
      const tasks = monthTasks.filter(r => r.tsa === person);
      const k = calcKpis(tasks);
      const eta = k.etaAcc !== null ? k.etaAcc : 0;
      const spd = speedScore(k.avgDays);
      const rel = k.reliability !== null ? k.reliability : 0;
      const spdVal = spd !== null ? spd : 0;
      const score = eta * 0.35 + spdVal * 0.30 + rel * 0.35;
      return { person, score, hasTasks: tasks.length > 0 };
    }).filter(c => c.hasTasks);

    monthComposites.sort((a, b) => b.score - a.score);

    PEOPLE.forEach(person => {
      const idx = monthComposites.findIndex(c => c.person === person);
      evolutionData[person].push(idx >= 0 ? idx + 1 : null);
    });
  });

  const datasets = PEOPLE.map(p => ({
    label: p,
    data: evolutionData[p],
    borderColor: PERSON_COLORS[p],
    backgroundColor: PERSON_COLORS[p],
    tension: 0.3,
    pointRadius: 5,
    pointHoverRadius: 7,
    borderWidth: 2.5,
    fill: false,
    spanGaps: true
  }));

  new Chart(document.getElementById('chartEvolution'), {
    type: 'line',
    data: { labels: monthLabels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false } },
        y: {
          reverse: true,
          min: 1,
          max: PEOPLE.length,
          ticks: {
            stepSize: 1,
            callback: v => '#' + v
          },
          grid: { color: '#f3f4f6' },
          title: { display: true, text: 'Rank (1 = best)', font: { size: 11 } }
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { usePointStyle: true, pointStyle: 'circle', padding: 14, font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: ctx => ctx.dataset.label + ': #' + ctx.raw
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
