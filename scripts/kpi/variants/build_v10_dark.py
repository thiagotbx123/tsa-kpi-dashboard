"""Build V10 — Dark Analytics Console Dashboard."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V10_DARK.html')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    raw = json.load(f)

# Filter core period: (y==25 and m>=12) or (y==26 and m<=3)
WK_RE = re.compile(r'(\d{2})-(\d{2})\s+W\.(\d+)')
def in_period(w):
    m = WK_RE.match(w)
    if not m:
        return False
    y, mo = int(m.group(1)), int(m.group(2))
    return (y == 25 and mo >= 12) or (y == 26 and mo <= 3)

data = [r for r in raw if in_period(r.get('week', ''))]
data_json = json.dumps(data, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TSA Dark Analytics Console</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0f172a;--surface:#1e293b;--surface2:#334155;--border:#475569;
  --text:#e2e8f0;--dim:#94a3b8;--muted:#64748b;
  --accent:#3b82f6;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--cyan:#06b6d4;--purple:#a855f7;--pink:#ec4899;--orange:#f97316;
}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);padding:16px 20px;min-height:100vh;font-size:14px;line-height:1.4}
.mono{font-family:'JetBrains Mono',monospace}

/* Top Bar */
.top-bar{display:flex;align-items:center;justify-content:space-between;padding:12px 20px;background:var(--surface);border:1px solid var(--border);border-radius:10px;margin-bottom:16px}
.top-bar .brand{display:flex;align-items:center;gap:10px}
.top-bar .brand .dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.top-bar .brand h1{font-size:1.1em;font-weight:700;color:var(--text);letter-spacing:-.01em}
.top-bar .meta{font-size:.75em;color:var(--dim);display:flex;gap:16px;align-items:center}
.top-bar .meta .tag{background:var(--surface2);padding:3px 10px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:.9em}

/* Gauge Row */
.gauge-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:16px}
.gauge-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;display:flex;flex-direction:column;align-items:center}
.gauge-card .label{font-size:.7em;color:var(--dim);text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:8px}
.gauge-canvas{width:160px;height:90px}
.gauge-card .val{font-family:'JetBrains Mono',monospace;font-size:1.6em;font-weight:700;margin-top:-4px}
.gauge-card .target-line{font-size:.7em;color:var(--muted);margin-top:2px}

/* Main Layout */
.main-layout{display:grid;grid-template-columns:1fr 280px;gap:16px;margin-bottom:16px}

/* Person Cards Grid */
.cards-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.cards-grid.row2{grid-template-columns:repeat(3,1fr);margin-top:10px}

.person-card{background:var(--surface);border:2px solid var(--border);border-radius:10px;padding:14px;position:relative;transition:border-color .2s}
.person-card.card-green{border-color:var(--green)}
.person-card.card-yellow{border-color:var(--yellow)}
.person-card.card-red{border-color:var(--red)}
.person-card .top-row{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.95em;flex-shrink:0;color:#fff}
.person-card .name{font-weight:700;font-size:.9em;flex:1}
.person-card .trend{font-size:1em;margin-left:auto}
.person-card .task-badge{position:absolute;top:10px;right:12px;background:var(--surface2);color:var(--dim);padding:2px 8px;border-radius:12px;font-size:.68em;font-family:'JetBrains Mono',monospace;font-weight:600}
.kpi-row{display:flex;gap:6px;margin-bottom:4px;align-items:center}
.kpi-row .kpi-label{font-size:.65em;color:var(--muted);width:50px;text-transform:uppercase;letter-spacing:.3px;flex-shrink:0}
.kpi-row .kpi-val{font-family:'JetBrains Mono',monospace;font-size:.82em;font-weight:600;width:48px;text-align:right;flex-shrink:0}
.spark-bar{flex:1;height:6px;background:var(--surface2);border-radius:3px;overflow:hidden;position:relative}
.spark-bar .fill{height:100%;border-radius:3px;transition:width .3s}

/* Side Panel */
.side-panel{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;max-height:calc(100vh - 280px);overflow-y:auto}
.side-panel .panel-title{font-size:.72em;color:var(--dim);text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.insight{padding:8px 10px;border-left:3px solid var(--border);margin-bottom:8px;font-size:.78em;line-height:1.4;background:rgba(255,255,255,.02);border-radius:0 6px 6px 0}
.insight.alert{border-left-color:var(--red);background:rgba(239,68,68,.06)}
.insight.trend{border-left-color:var(--cyan);background:rgba(6,182,212,.06)}
.insight.target{border-left-color:var(--yellow);background:rgba(234,179,8,.06)}
.insight.good{border-left-color:var(--green);background:rgba(34,197,94,.06)}
.insight .tag{font-family:'JetBrains Mono',monospace;font-size:.85em;font-weight:700;margin-right:4px}
.insight .tag-alert{color:var(--red)}
.insight .tag-trend{color:var(--cyan)}
.insight .tag-target{color:var(--yellow)}
.insight .tag-good{color:var(--green)}

/* Timeline */
.timeline-section{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px}
.timeline-section .title{font-size:.72em;color:var(--dim);text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:12px}
.timeline-box{position:relative;height:320px}

.footer{text-align:center;padding:12px;color:var(--muted);font-size:.7em;font-family:'JetBrains Mono',monospace}

/* Scrollbar */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
</style>
</head>
<body>

<div class="top-bar">
  <div class="brand">
    <span class="dot"></span>
    <h1>TSA Analytics Console</h1>
  </div>
  <div class="meta">
    <span>Dec 2025 &ndash; Mar 2026</span>
    <span class="tag" id="recCount"></span>
    <span class="tag">v10</span>
  </div>
</div>

<div class="gauge-row">
  <div class="gauge-card">
    <div class="label">ETA Accuracy</div>
    <canvas class="gauge-canvas" id="gauge1"></canvas>
    <div class="val" id="gaugeVal1"></div>
    <div class="target-line">Target &gt;90%</div>
  </div>
  <div class="gauge-card">
    <div class="label">Faster Implementations</div>
    <canvas class="gauge-canvas" id="gauge2"></canvas>
    <div class="val" id="gaugeVal2"></div>
    <div class="target-line">Target &lt;28 days</div>
  </div>
  <div class="gauge-card">
    <div class="label">Impl. Reliability</div>
    <canvas class="gauge-canvas" id="gauge3"></canvas>
    <div class="val" id="gaugeVal3"></div>
    <div class="target-line">Target &gt;85%</div>
  </div>
</div>

<div class="main-layout">
  <div>
    <div class="cards-grid" id="cardsRow1"></div>
    <div class="cards-grid row2" id="cardsRow2"></div>
  </div>
  <div class="side-panel" id="sidePanel">
    <div class="panel-title">Live Insights Feed</div>
  </div>
</div>

<div class="timeline-section">
  <div class="title">KPI Timeline &mdash; Weekly Trend (All 3 KPIs)</div>
  <div class="timeline-box"><canvas id="timelineChart"></canvas></div>
</div>

<div class="footer">TSA CORTEX &bull; Dark Analytics Console &bull; V10</div>

<script>
const DATA = """ + data_json + r""";

const PEOPLE = ['ALEXANDRA','CARLOS','DIEGO','GABI','THAIS','THIAGO','YASMIM'];
const COLORS = {
  ALEXANDRA:'#3b82f6',CARLOS:'#22c55e',DIEGO:'#f97316',GABI:'#a855f7',
  THAIS:'#ef4444',THIAGO:'#06b6d4',YASMIM:'#ec4899'
};
const WK_RE = /(\d{2})-(\d{2})\s+W\.(\d+)/;

function parseWeek(w){const m=WK_RE.exec(w);if(!m)return null;return{y:+m[1],mo:+m[2],wn:+m[3]};}
function weekSortKey(w){const p=parseWeek(w);if(!p)return'';return String(p.y).padStart(2,'0')+String(p.mo).padStart(2,'0')+String(p.wn).padStart(2,'0');}
function dateDiffDays(a,b){if(!a||!b)return null;const da=new Date(a),db=new Date(b);const diff=(db-da)/(1000*60*60*24);return diff;}

function calcKPIs(records){
  let onTime=0,late=0,overdue=0,totalDur=0,durCount=0;
  records.forEach(r=>{
    if(r.perf==='On Time')onTime++;
    if(r.perf==='Late')late++;
    if(r.perf==='Overdue')overdue++;
    if(r.status==='Done'&&r.dateAdd&&r.delivery){
      const d=dateDiffDays(r.dateAdd,r.delivery);
      if(d!==null&&d>=0){totalDur+=d;durCount++;}
    }
  });
  const eta=(onTime+late)>0?onTime/(onTime+late):null;
  const reliability=(onTime+late+overdue)>0?onTime/(onTime+late+overdue):null;
  const avgDur=durCount>0?totalDur/durCount:null;
  return{eta,reliability,avgDur,onTime,late,overdue,durCount};
}

const teamKPI = calcKPIs(DATA);
document.getElementById('recCount').textContent = DATA.length+' records';

const personKPIs = {};
PEOPLE.forEach(p=>{personKPIs[p]=calcKPIs(DATA.filter(r=>r.tsa===p));});

// ---- Gauge Charts (half doughnut) ----
function buildGauge(canvasId, valId, value, maxVal, target, isInvert, suffix){
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');

  let pct, displayVal;
  if(isInvert){
    // For days: lower is better. Gauge shows how close to 0 (maxVal = worst case)
    pct = value!==null ? Math.max(0, 1 - value/maxVal) : 0;
    displayVal = value!==null ? value.toFixed(1)+'d' : 'N/A';
  } else {
    pct = value!==null ? value : 0;
    displayVal = value!==null ? (value*100).toFixed(1)+'%' : 'N/A';
  }

  const pass = isInvert ? (value!==null && value < target) : (value!==null && value >= target);
  const color = pass ? '#22c55e' : '#ef4444';

  new Chart(ctx, {
    type:'doughnut',
    data:{
      datasets:[{
        data:[pct, 1-pct],
        backgroundColor:[color, '#1e293b'],
        borderWidth:0
      }]
    },
    options:{
      circumference:180,
      rotation:270,
      cutout:'75%',
      responsive:false,
      maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{enabled:false}}
    }
  });

  const el = document.getElementById(valId);
  el.textContent = displayVal;
  el.style.color = color;
}

buildGauge('gauge1','gaugeVal1',teamKPI.eta,1,.9,false,'%');
buildGauge('gauge2','gaugeVal2',teamKPI.avgDur,60,28,true,'d');
buildGauge('gauge3','gaugeVal3',teamKPI.reliability,1,.85,false,'%');

// ---- Person Cards ----
function buildPersonCards(){
  const row1 = document.getElementById('cardsRow1');
  const row2 = document.getElementById('cardsRow2');

  PEOPLE.forEach((p, i) => {
    const k = personKPIs[p];
    const count = DATA.filter(r=>r.tsa===p).length;

    // Determine card border color
    let belowCount = 0;
    if(k.eta!==null && k.eta < .9) belowCount++;
    if(k.avgDur!==null && k.avgDur >= 28) belowCount++;
    if(k.reliability!==null && k.reliability < .85) belowCount++;
    const borderClass = belowCount===0?'card-green':belowCount===1?'card-yellow':'card-red';

    // Trend: compare first half vs second half
    const weeks = [...new Set(DATA.filter(r=>r.tsa===p).map(r=>r.week))].filter(w=>WK_RE.test(w)).sort((a,b)=>weekSortKey(a).localeCompare(weekSortKey(b)));
    const mid = Math.floor(weeks.length/2);
    const firstHalf = DATA.filter(r=>r.tsa===p && weeks.slice(0,mid).includes(r.week));
    const secondHalf = DATA.filter(r=>r.tsa===p && weeks.slice(mid).includes(r.week));
    const k1 = calcKPIs(firstHalf), k2 = calcKPIs(secondHalf);
    let trend = '&#8594;'; // flat
    if(k1.eta!==null && k2.eta!==null){
      if(k2.eta > k1.eta + .03) trend = '&#9650;';
      else if(k2.eta < k1.eta - .03) trend = '&#9660;';
    }
    const trendColor = trend.includes('9650')?'var(--green)':trend.includes('9660')?'var(--red)':'var(--dim)';

    const card = document.createElement('div');
    card.className = `person-card ${borderClass}`;

    const etaPct = k.eta!==null ? (k.eta*100).toFixed(0) : 0;
    const durVal = k.avgDur!==null ? Math.min(k.avgDur, 60) : 0;
    const durDisplay = k.avgDur!==null ? k.avgDur.toFixed(0)+'d' : 'N/A';
    const relPct = k.reliability!==null ? (k.reliability*100).toFixed(0) : 0;

    const etaColor = k.eta!==null&&k.eta>=.9?'var(--green)':'var(--red)';
    const durColor = k.avgDur!==null&&k.avgDur<28?'var(--green)':'var(--red)';
    const relColor = k.reliability!==null&&k.reliability>=.85?'var(--green)':'var(--red)';

    card.innerHTML = `
      <div class="task-badge">${count}</div>
      <div class="top-row">
        <div class="avatar" style="background:${COLORS[p]}">${p[0]}</div>
        <div class="name">${p}</div>
        <div class="trend" style="color:${trendColor}">${trend}</div>
      </div>
      <div class="kpi-row">
        <span class="kpi-label">ETA</span>
        <span class="kpi-val mono" style="color:${etaColor}">${k.eta!==null?(k.eta*100).toFixed(1)+'%':'N/A'}</span>
        <div class="spark-bar"><div class="fill" style="width:${etaPct}%;background:${etaColor}"></div></div>
      </div>
      <div class="kpi-row">
        <span class="kpi-label">IMPL</span>
        <span class="kpi-val mono" style="color:${durColor}">${durDisplay}</span>
        <div class="spark-bar"><div class="fill" style="width:${Math.min(100,durVal/60*100).toFixed(0)}%;background:${durColor}"></div></div>
      </div>
      <div class="kpi-row">
        <span class="kpi-label">REL</span>
        <span class="kpi-val mono" style="color:${relColor}">${k.reliability!==null?(k.reliability*100).toFixed(1)+'%':'N/A'}</span>
        <div class="spark-bar"><div class="fill" style="width:${relPct}%;background:${relColor}"></div></div>
      </div>
    `;

    if(i < 4) row1.appendChild(card);
    else row2.appendChild(card);
  });
}
buildPersonCards();

// ---- Side Panel Insights ----
function buildInsights(){
  const panel = document.getElementById('sidePanel');
  const insights = [];

  // Alerts: reliability or ETA below threshold
  PEOPLE.forEach(p=>{
    const k = personKPIs[p];
    if(k.reliability!==null && k.reliability < .5){
      insights.push({type:'alert',text:`<span class="tag tag-alert">ALERT</span> ${p} reliability at ${(k.reliability*100).toFixed(0)}%`});
    }
    if(k.eta!==null && k.eta < .7){
      insights.push({type:'alert',text:`<span class="tag tag-alert">ALERT</span> ${p} ETA accuracy at ${(k.eta*100).toFixed(0)}%`});
    }
    if(k.avgDur!==null && k.avgDur > 40){
      insights.push({type:'alert',text:`<span class="tag tag-alert">ALERT</span> ${p} avg implementation ${k.avgDur.toFixed(0)} days (target <28)`});
    }
  });

  // Trends: compare halves
  const weeks = [...new Set(DATA.map(r=>r.week))].filter(w=>WK_RE.test(w)).sort((a,b)=>weekSortKey(a).localeCompare(weekSortKey(b)));
  const mid = Math.floor(weeks.length/2);
  PEOPLE.forEach(p=>{
    const firstHalf = DATA.filter(r=>r.tsa===p && weeks.slice(0,mid).includes(r.week));
    const secondHalf = DATA.filter(r=>r.tsa===p && weeks.slice(mid).includes(r.week));
    const k1 = calcKPIs(firstHalf), k2 = calcKPIs(secondHalf);
    if(k1.eta!==null && k2.eta!==null){
      const diff = (k2.eta - k1.eta)*100;
      if(diff > 5){
        insights.push({type:'trend',text:`<span class="tag tag-trend">TREND</span> ${p} improving +${diff.toFixed(0)}pp this half`});
      } else if(diff < -5){
        insights.push({type:'alert',text:`<span class="tag tag-alert">TREND</span> ${p} declining ${diff.toFixed(0)}pp this half`});
      }
    }
  });

  // Team target checks
  if(teamKPI.eta!==null){
    const diff = (teamKPI.eta - .9)*100;
    if(diff < 0){
      insights.push({type:'target',text:`<span class="tag tag-target">TARGET</span> Team ETA Accuracy ${Math.abs(diff).toFixed(1)}pp below target`});
    } else {
      insights.push({type:'good',text:`<span class="tag tag-good">TARGET</span> Team ETA Accuracy ${diff.toFixed(1)}pp above target`});
    }
  }
  if(teamKPI.avgDur!==null){
    if(teamKPI.avgDur >= 28){
      insights.push({type:'target',text:`<span class="tag tag-target">TARGET</span> Team avg implementation ${teamKPI.avgDur.toFixed(1)}d (target <28)`});
    } else {
      insights.push({type:'good',text:`<span class="tag tag-good">TARGET</span> Team avg implementation ${teamKPI.avgDur.toFixed(1)}d &mdash; on target`});
    }
  }
  if(teamKPI.reliability!==null){
    const diff = (teamKPI.reliability - .85)*100;
    if(diff < 0){
      insights.push({type:'target',text:`<span class="tag tag-target">TARGET</span> Team Reliability ${Math.abs(diff).toFixed(1)}pp below target`});
    } else {
      insights.push({type:'good',text:`<span class="tag tag-good">TARGET</span> Team Reliability ${diff.toFixed(1)}pp above target`});
    }
  }

  // Top performer
  let bestETA = {p:null,v:0};
  PEOPLE.forEach(p=>{
    const k=personKPIs[p];
    if(k.eta!==null && k.eta > bestETA.v){bestETA={p,v:k.eta};}
  });
  if(bestETA.p){
    insights.push({type:'good',text:`<span class="tag tag-good">TOP</span> ${bestETA.p} leads ETA accuracy at ${(bestETA.v*100).toFixed(1)}%`});
  }

  // Volume insight
  const counts = PEOPLE.map(p=>({p,c:DATA.filter(r=>r.tsa===p).length})).sort((a,b)=>b.c-a.c);
  insights.push({type:'trend',text:`<span class="tag tag-trend">VOLUME</span> ${counts[0].p} highest workload (${counts[0].c} tasks), ${counts[counts.length-1].p} lowest (${counts[counts.length-1].c})`});

  // Sort: alerts first, then trends, then targets, then good
  const order = {alert:0,trend:1,target:2,good:3};
  insights.sort((a,b)=>(order[a.type]||9)-(order[b.type]||9));

  insights.forEach(ins=>{
    const div = document.createElement('div');
    div.className = `insight ${ins.type}`;
    div.innerHTML = ins.text;
    panel.appendChild(div);
  });
}
buildInsights();

// ---- Timeline Chart ----
(function(){
  const weeks = [...new Set(DATA.map(r=>r.week))].filter(w=>WK_RE.test(w)).sort((a,b)=>weekSortKey(a).localeCompare(weekSortKey(b)));

  const etaData=[], durData=[], relData=[];
  weeks.forEach(w=>{
    const wData = DATA.filter(r=>r.week===w);
    const k = calcKPIs(wData);
    etaData.push(k.eta!==null ? +(k.eta*100).toFixed(1) : null);
    durData.push(k.avgDur!==null ? +k.avgDur.toFixed(1) : null);
    relData.push(k.reliability!==null ? +(k.reliability*100).toFixed(1) : null);
  });

  new Chart(document.getElementById('timelineChart').getContext('2d'),{
    type:'line',
    data:{
      labels:weeks,
      datasets:[
        {
          label:'ETA Accuracy %',
          data:etaData,
          borderColor:'#3b82f6',
          backgroundColor:'rgba(59,130,246,.08)',
          fill:true,
          tension:.3,
          borderWidth:2,
          pointRadius:3,
          pointBackgroundColor:'#3b82f6',
          yAxisID:'y'
        },
        {
          label:'Reliability %',
          data:relData,
          borderColor:'#22c55e',
          backgroundColor:'rgba(34,197,94,.08)',
          fill:true,
          tension:.3,
          borderWidth:2,
          pointRadius:3,
          pointBackgroundColor:'#22c55e',
          yAxisID:'y'
        },
        {
          label:'Avg Duration (days)',
          data:durData,
          borderColor:'#f97316',
          backgroundColor:'rgba(249,115,22,.08)',
          fill:true,
          tension:.3,
          borderWidth:2,
          pointRadius:3,
          pointBackgroundColor:'#f97316',
          yAxisID:'y2'
        }
      ]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{
          position:'top',
          labels:{color:'#94a3b8',font:{size:11,family:'Segoe UI'},boxWidth:12,padding:14}
        },
        tooltip:{
          backgroundColor:'#1e293b',
          borderColor:'#475569',
          borderWidth:1,
          titleColor:'#e2e8f0',
          bodyColor:'#94a3b8',
          titleFont:{family:'Segoe UI',size:12,weight:'bold'},
          bodyFont:{family:'JetBrains Mono',size:11}
        }
      },
      scales:{
        x:{
          grid:{color:'rgba(71,85,105,.3)'},
          ticks:{color:'#64748b',font:{size:9,family:'Segoe UI'},maxRotation:45}
        },
        y:{
          position:'left',
          grid:{color:'rgba(71,85,105,.3)'},
          ticks:{color:'#94a3b8',font:{size:10,family:'JetBrains Mono'},callback:v=>v+'%'},
          min:0,max:105,
          title:{display:true,text:'Percentage',color:'#64748b',font:{size:10}}
        },
        y2:{
          position:'right',
          grid:{drawOnChartArea:false},
          ticks:{color:'#f97316',font:{size:10,family:'JetBrains Mono'},callback:v=>v+'d'},
          min:0,
          title:{display:true,text:'Days',color:'#f97316',font:{size:10}}
        }
      }
    }
  });
})();

</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f'Saved: {OUTPUT}')
