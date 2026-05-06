"""Build V9 — Waterfall & Impact Analysis Dashboard."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'DASH_V9_WATERFALL.html')

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
<title>Impact Analysis — Who Moves the Needle?</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#f8fafc;--white:#fff;--border:#e2e8f0;--text:#1e293b;
  --dim:#64748b;--green:#16a34a;--red:#dc2626;--blue:#2563eb;
  --green-bg:#f0fdf4;--red-bg:#fef2f2;--blue-bg:#eff6ff;
  --yellow:#d97706;--yellow-bg:#fffbeb;
}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);padding:24px 32px;min-height:100vh;font-size:15px;line-height:1.5}

.header{background:linear-gradient(135deg,#1e293b 0%,#334155 100%);color:#fff;padding:24px 32px;border-radius:12px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between}
.header h1{font-size:1.5em;font-weight:800;letter-spacing:-.02em}
.header .sub{font-size:.82em;color:#94a3b8;margin-top:4px}
.header .badge{background:rgba(255,255,255,.12);padding:6px 14px;border-radius:8px;font-size:.78em;color:#cbd5e1}

.kpi-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:24px}
.kpi-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:16px 20px}
.kpi-card .label{font-size:.72em;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:4px}
.kpi-card .value{font-size:1.8em;font-weight:800}
.kpi-card .target{font-size:.72em;color:var(--dim);margin-top:2px}
.kpi-card .status{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.68em;font-weight:700;margin-top:4px}
.status-pass{background:var(--green-bg);color:var(--green)}
.status-fail{background:var(--red-bg);color:var(--red)}

.section{background:var(--white);border:1px solid var(--border);border-radius:10px;margin-bottom:20px;overflow:hidden}
.section .title{padding:16px 20px;font-size:.95em;font-weight:700;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
.section .title .icon{font-size:1.1em}
.section .body{padding:20px}

.chart-row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.chart-box{position:relative;height:340px}

table{width:100%;border-collapse:collapse;font-size:.85em}
th,td{padding:10px 14px;text-align:center;border-bottom:1px solid var(--border)}
th{background:#f1f5f9;font-weight:600;color:var(--dim);font-size:.78em;text-transform:uppercase;letter-spacing:.3px}
td{font-weight:500}
.cell-pos{color:var(--green);font-weight:700}
.cell-neg{color:var(--red);font-weight:700}
.cell-name{text-align:left;font-weight:700}
.highlight-row{background:#fefce8}

.impact-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}
.impact-card{border:2px solid var(--border);border-radius:10px;padding:14px 18px;text-align:center}
.impact-card.positive{border-color:var(--green);background:var(--green-bg)}
.impact-card.negative{border-color:var(--red);background:var(--red-bg)}
.impact-card .kpi-name{font-size:.72em;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:6px}
.impact-card .person{font-size:1.1em;font-weight:800;margin-bottom:2px}
.impact-card .delta{font-size:.88em;font-weight:700}

.cumulative-box{position:relative;height:380px;margin-top:8px}
.volume-box{position:relative;height:340px;margin-top:8px}

.footer{text-align:center;padding:16px;color:var(--dim);font-size:.75em;margin-top:12px}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Impact Analysis &mdash; Who Moves the Needle?</h1>
    <div class="sub">Waterfall contribution analysis &bull; Dec 2025 &ndash; Mar 2026</div>
  </div>
  <div class="badge" id="recordCount"></div>
</div>

<div class="kpi-strip" id="kpiStrip"></div>

<div class="section">
  <div class="title"><span class="icon">&#9632;</span> Waterfall Charts &mdash; Individual Contribution to Team KPIs</div>
  <div class="body">
    <div class="chart-row">
      <div class="chart-box"><canvas id="waterfall1"></canvas></div>
      <div class="chart-box"><canvas id="waterfall2"></canvas></div>
      <div class="chart-box"><canvas id="waterfall3"></canvas></div>
    </div>
  </div>
</div>

<div class="section">
  <div class="title"><span class="icon">&#9650;</span> What-If Analysis &mdash; Team KPI Without Each Person</div>
  <div class="body">
    <table id="whatIfTable">
      <thead>
        <tr>
          <th style="text-align:left">Remove Person</th>
          <th>ETA Accuracy</th>
          <th>&Delta; ETA</th>
          <th>Faster Impl. (days)</th>
          <th>&Delta; Impl.</th>
          <th>Reliability</th>
          <th>&Delta; Reliability</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="title"><span class="icon">&#11044;</span> Impact Matrix &mdash; Biggest Positive &amp; Negative Impact per KPI</div>
  <div class="body">
    <div class="impact-grid" id="impactMatrix"></div>
  </div>
</div>

<div class="section">
  <div class="title"><span class="icon">&#9650;</span> Cumulative On-Time Contributions by Week</div>
  <div class="body">
    <div class="cumulative-box"><canvas id="cumulativeChart"></canvas></div>
  </div>
</div>

<div class="section">
  <div class="title"><span class="icon">&#9679;</span> Task Volume vs KPI Impact &mdash; Weighted Analysis</div>
  <div class="body">
    <div class="volume-box"><canvas id="volumeChart"></canvas></div>
  </div>
</div>

<div class="footer">Generated by TSA CORTEX &bull; V9 Waterfall &amp; Impact Analysis</div>

<script>
const DATA = """ + data_json + r""";

const PEOPLE = ['ALEXANDRA','CARLOS','DIEGO','GABI','THAIS','THIAGO','YASMIM'];
const COLORS = {
  ALEXANDRA:'#2563eb',CARLOS:'#16a34a',DIEGO:'#d97706',GABI:'#7c3aed',
  THAIS:'#dc2626',THIAGO:'#0891b2',YASMIM:'#db2777'
};
const WK_RE = /(\d{2})-(\d{2})\s+W\.(\d+)/;

function parseWeek(w){const m=WK_RE.exec(w);if(!m)return null;return{y:+m[1],mo:+m[2],wn:+m[3]};}
function weekSortKey(w){const p=parseWeek(w);if(!p)return'';return String(p.y).padStart(2,'0')+String(p.mo).padStart(2,'0')+String(p.wn).padStart(2,'0');}
function dateDiffDays(a,b){if(!a||!b)return null;const da=new Date(a),db=new Date(b);const diff=(db-da)/(1000*60*60*24);return diff;}

// ---- KPI Calculations ----
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
  return{eta,reliability,avgDur,onTime,late,overdue,durCount,totalDur};
}

// Team KPIs
const teamKPI = calcKPIs(DATA);
document.getElementById('recordCount').textContent = DATA.length + ' records in period';

// Per-person KPIs
const personKPIs = {};
PEOPLE.forEach(p=>{
  personKPIs[p] = calcKPIs(DATA.filter(r=>r.tsa===p));
});

// ---- KPI Strip ----
function fmtPct(v){return v!==null?(v*100).toFixed(1)+'%':'N/A';}
function fmtDays(v){return v!==null?v.toFixed(1)+' days':'N/A';}
const kpiDefs = [
  {name:'ETA Accuracy',val:teamKPI.eta,target:.9,fmt:fmtPct,unit:'Target: >90%'},
  {name:'Faster Implementations',val:teamKPI.avgDur!==null?1:null,raw:teamKPI.avgDur,target:28,fmt:fmtDays,unit:'Target: <28 days',invert:true},
  {name:'Impl. Reliability',val:teamKPI.reliability,target:.85,fmt:fmtPct,unit:'Target: >85%'}
];
const strip = document.getElementById('kpiStrip');
kpiDefs.forEach(k=>{
  const card = document.createElement('div');
  card.className='kpi-card';
  let val,pass;
  if(k.invert){
    val=k.raw;pass=val!==null&&val<k.target;
  } else {
    val=k.val;pass=val!==null&&val>=k.target;
  }
  const display = k.invert?fmtDays(k.raw):fmtPct(k.val);
  card.innerHTML=`<div class="label">${k.name}</div><div class="value">${display}</div><div class="target">${k.unit}</div><div class="status ${pass?'status-pass':'status-fail'}">${pass?'ON TARGET':'BELOW TARGET'}</div>`;
  strip.appendChild(card);
});

// ---- Waterfall Charts ----
function buildWaterfall(canvasId, kpiName, teamVal, personVals, fmt, isInvert){
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');

  // Calculate deviations from team average
  const validPeople = PEOPLE.filter(p=>personVals[p]!==null);
  const teamAvg = teamVal;
  if(teamAvg===null) return;

  // Waterfall: start bar = team avg, then each person's delta, final bar = team value
  const labels = ['Team Avg', ...PEOPLE, 'Result'];
  const bases = [];
  const deltas = [];
  const colors = [];

  let running = teamAvg;
  bases.push(0);
  deltas.push(teamAvg);
  colors.push('#94a3b8');

  PEOPLE.forEach(p=>{
    const pv = personVals[p];
    if(pv===null){
      bases.push(running);
      deltas.push(0);
      colors.push('#cbd5e1');
    } else {
      const delta = pv - teamAvg;
      const contribution = delta / PEOPLE.length; // weighted contribution
      if(contribution>=0){
        bases.push(running);
        deltas.push(contribution);
        colors.push('#16a34a');
      } else {
        bases.push(running + contribution);
        deltas.push(Math.abs(contribution));
        colors.push('#dc2626');
      }
      running += contribution;
    }
  });

  bases.push(0);
  deltas.push(running);
  colors.push('#2563eb');

  const multiply = isInvert ? 1 : 100;
  const suffix = isInvert ? '' : '%';

  new Chart(ctx, {
    type:'bar',
    data:{
      labels:labels,
      datasets:[
        {label:'Base',data:bases.map(v=>+(v*multiply).toFixed(2)),backgroundColor:'transparent',borderWidth:0,barPercentage:.7},
        {label:'Value',data:deltas.map(v=>+(v*multiply).toFixed(2)),backgroundColor:colors,borderWidth:0,borderRadius:3,barPercentage:.7}
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{
        title:{display:true,text:kpiName,font:{size:14,weight:'bold',family:'Segoe UI'},color:'#1e293b'},
        legend:{display:false},
        tooltip:{
          callbacks:{
            label:function(ctx){
              if(ctx.datasetIndex===0) return '';
              const idx=ctx.dataIndex;
              const total=bases[idx]*multiply+deltas[idx]*multiply;
              return idx===0||idx===labels.length-1
                ? kpiName+': '+total.toFixed(1)+suffix
                : 'Delta: '+(deltas[idx]*multiply>0?'+':'')+deltas[idx].toFixed(2)+suffix+' (Running: '+total.toFixed(1)+suffix+')';
            }
          }
        }
      },
      scales:{
        x:{stacked:true,grid:{display:false},ticks:{font:{size:10,family:'Segoe UI'},maxRotation:45}},
        y:{stacked:true,grid:{color:'#f1f5f9'},ticks:{callback:v=>v.toFixed(0)+suffix,font:{size:10}},
          min:0,
          suggestedMax:isInvert?Math.max(...Object.values(personVals).filter(v=>v!==null))*1.3*multiply:100
        }
      }
    }
  });
}

const personETA={},personDur={},personRel={};
PEOPLE.forEach(p=>{
  const k=personKPIs[p];
  personETA[p]=k.eta;
  personDur[p]=k.avgDur;
  personRel[p]=k.reliability;
});

buildWaterfall('waterfall1','ETA Accuracy',teamKPI.eta,personETA,fmtPct,false);
buildWaterfall('waterfall2','Faster Implementations (days)',teamKPI.avgDur,personDur,fmtDays,true);
buildWaterfall('waterfall3','Implementation Reliability',teamKPI.reliability,personRel,fmtPct,false);

// ---- What-If Table ----
const tbody = document.querySelector('#whatIfTable tbody');
// Team baseline row
const baseRow = document.createElement('tr');
baseRow.className='highlight-row';
baseRow.innerHTML=`<td class="cell-name" style="color:var(--blue)">TEAM (Baseline)</td><td><b>${fmtPct(teamKPI.eta)}</b></td><td>-</td><td><b>${fmtDays(teamKPI.avgDur)}</b></td><td>-</td><td><b>${fmtPct(teamKPI.reliability)}</b></td><td>-</td>`;
tbody.appendChild(baseRow);

PEOPLE.forEach(p=>{
  const without = DATA.filter(r=>r.tsa!==p);
  const wk = calcKPIs(without);
  const dEta = wk.eta!==null&&teamKPI.eta!==null ? (wk.eta-teamKPI.eta)*100 : null;
  const dDur = wk.avgDur!==null&&teamKPI.avgDur!==null ? wk.avgDur-teamKPI.avgDur : null;
  const dRel = wk.reliability!==null&&teamKPI.reliability!==null ? (wk.reliability-teamKPI.reliability)*100 : null;

  const fmtDelta = (v,invert)=>{
    if(v===null) return '<span style="color:var(--dim)">N/A</span>';
    const good = invert ? v<0 : v>0;
    const cls = good?'cell-pos':'cell-neg';
    const sign = v>0?'+':'';
    return `<span class="${cls}">${sign}${v.toFixed(1)}${invert?' days':'pp'}</span>`;
  };

  const tr = document.createElement('tr');
  tr.innerHTML=`<td class="cell-name">${p}</td><td>${fmtPct(wk.eta)}</td><td>${fmtDelta(dEta,false)}</td><td>${fmtDays(wk.avgDur)}</td><td>${fmtDelta(dDur,true)}</td><td>${fmtPct(wk.reliability)}</td><td>${fmtDelta(dRel,false)}</td>`;
  tbody.appendChild(tr);
});

// ---- Impact Matrix ----
const impactDiv = document.getElementById('impactMatrix');
const kpiList = [
  {name:'ETA Accuracy',key:'eta',inv:false},
  {name:'Faster Impl.',key:'avgDur',inv:true},
  {name:'Reliability',key:'reliability',inv:false}
];

kpiList.forEach(kpi=>{
  // Find biggest positive & negative impact (who, when removed, changes team KPI most)
  let bestPos={person:null,delta:0},bestNeg={person:null,delta:0};
  PEOPLE.forEach(p=>{
    const without = DATA.filter(r=>r.tsa!==p);
    const wk = calcKPIs(without);
    let delta;
    if(kpi.inv){
      delta = teamKPI[kpi.key]!==null&&wk[kpi.key]!==null ? teamKPI[kpi.key]-wk[kpi.key] : 0; // positive means removing them speeds up (their removal reduces avg days = they were slow)
    } else {
      delta = teamKPI[kpi.key]!==null&&wk[kpi.key]!==null ? wk[kpi.key]-teamKPI[kpi.key] : 0;
    }
    // If removing person IMPROVES team KPI, that person has negative impact
    // If removing person WORSENS team KPI, that person has positive impact
    if(delta < bestNeg.delta) bestNeg = {person:p, delta};
    if(delta > bestPos.delta) bestPos = {person:p, delta};
  });

  // bestNeg.delta < 0 means removing them worsens KPI => they have POSITIVE impact
  // bestPos.delta > 0 means removing them improves KPI => they have NEGATIVE impact
  const posCard = document.createElement('div');
  posCard.className='impact-card positive';
  const posP = bestNeg.person || 'N/A';
  const posDelta = bestNeg.delta!==null ? (kpi.inv ? bestNeg.delta.toFixed(1)+' days' : (bestNeg.delta*100).toFixed(1)+'pp') : '';
  posCard.innerHTML=`<div class="kpi-name">${kpi.name} &mdash; Most Positive</div><div class="person">${posP}</div><div class="delta">Removing them worsens KPI by ${posDelta}</div>`;
  impactDiv.appendChild(posCard);

  const negCard = document.createElement('div');
  negCard.className='impact-card negative';
  const negP = bestPos.person || 'N/A';
  const negDelta = bestPos.delta!==null ? (kpi.inv ? bestPos.delta.toFixed(1)+' days' : (bestPos.delta*100).toFixed(1)+'pp') : '';
  negCard.innerHTML=`<div class="kpi-name">${kpi.name} &mdash; Most Negative</div><div class="person">${negP}</div><div class="delta">Removing them improves KPI by ${negDelta}</div>`;
  impactDiv.appendChild(negCard);
});

// ---- Cumulative On-Time Contributions ----
(function(){
  const weeks = [...new Set(DATA.map(r=>r.week))].filter(w=>WK_RE.test(w)).sort((a,b)=>weekSortKey(a).localeCompare(weekSortKey(b)));

  const datasets = PEOPLE.map(p=>{
    let cum = 0;
    const vals = weeks.map(w=>{
      cum += DATA.filter(r=>r.tsa===p&&r.week===w&&r.perf==='On Time').length;
      return cum;
    });
    return {
      label:p,
      data:vals,
      fill:true,
      backgroundColor:COLORS[p]+'33',
      borderColor:COLORS[p],
      borderWidth:1.5,
      pointRadius:0,
      tension:.3
    };
  });

  new Chart(document.getElementById('cumulativeChart').getContext('2d'),{
    type:'line',
    data:{labels:weeks,datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'top',labels:{font:{size:11,family:'Segoe UI'},boxWidth:12,padding:10}},title:{display:false}},
      scales:{
        x:{grid:{display:false},ticks:{font:{size:9},maxRotation:45}},
        y:{stacked:true,grid:{color:'#f1f5f9'},title:{display:true,text:'Cumulative On-Time Tasks',font:{size:11}}}
      },
      interaction:{mode:'index',intersect:false}
    }
  });
})();

// ---- Task Volume vs KPI Impact (Bubble) ----
(function(){
  const bubbleData = PEOPLE.map(p=>{
    const k = personKPIs[p];
    const count = DATA.filter(r=>r.tsa===p).length;
    const etaPct = k.eta!==null ? k.eta*100 : 0;
    const relPct = k.reliability!==null ? k.reliability*100 : 0;
    return {
      label:p,
      data:[{x:count, y:etaPct, r:Math.max(relPct/6,4)}],
      backgroundColor:COLORS[p]+'99',
      borderColor:COLORS[p],
      borderWidth:2
    };
  });

  new Chart(document.getElementById('volumeChart').getContext('2d'),{
    type:'bubble',
    data:{datasets:bubbleData},
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{
        legend:{position:'top',labels:{font:{size:11,family:'Segoe UI'},boxWidth:12}},
        title:{display:true,text:'X: Task Count | Y: ETA Accuracy % | Bubble Size: Reliability %',font:{size:11,weight:'normal',family:'Segoe UI'},color:'#64748b',padding:{bottom:8}},
        tooltip:{
          callbacks:{
            label:function(ctx){
              const d=ctx.raw;
              return ctx.dataset.label+': '+d.x+' tasks, ETA '+d.y.toFixed(1)+'%, Reliability '+(d.r*6).toFixed(0)+'%';
            }
          }
        }
      },
      scales:{
        x:{title:{display:true,text:'Task Volume',font:{size:11}},grid:{color:'#f1f5f9'}},
        y:{title:{display:true,text:'ETA Accuracy %',font:{size:11}},grid:{color:'#f1f5f9'},min:0,max:105}
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
