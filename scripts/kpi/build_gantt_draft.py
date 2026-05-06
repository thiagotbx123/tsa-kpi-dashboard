"""Build TSA Gantt Chart — STANDALONE DRAFT (deprecated).

NOTE: The Gantt chart is now embedded in the main KPI Dashboard
(build_html_dashboard.py, panel-gantt tab). This standalone version
is kept for reference but may diverge from the embedded version.
For production use, always use the embedded Gantt via the main dashboard.

Layout:
- Rows grouped by Customer (collapsible)
- Customer header row: summary bar spanning earliest→latest task
- Expanded: individual task bars with ticket links
- X-axis: day columns, scrollable
- Filters: Person, Period, Status

Usage: python build_gantt_draft.py
Output: ~/Downloads/KPI_GANTT.html
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, re
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '_dashboard_data.json')
OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'KPI_GANTT.html')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    data_raw = json.load(f)

records = []
for r in data_raw:
    start = r.get('startedAt') or r.get('dateAdd') or ''
    if not start or start < '2025-01-01':
        continue
    if r.get('status') == 'Canceled':
        continue
    records.append(r)

data_json = json.dumps(records, ensure_ascii=False)
data_json_safe = re.sub(r'</(script)', r'<\\/\1', data_json, flags=re.IGNORECASE)
build_date = datetime.now().strftime('%Y-%m-%d %H:%M')

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
<title>Gantt Chart</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI','Inter',system-ui,sans-serif;background:#f1f5f9;color:#1e293b}}

.header{{background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
.header h1{{font-size:1.05em;font-weight:700;letter-spacing:.3px}}
.header .sub{{font-size:.7em;color:#94a3b8;margin-top:2px}}
.header .stats{{font-size:.72em;color:#a7f3d0}}

.controls{{padding:10px 24px;background:#fff;border-bottom:1px solid #e2e8f0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.controls label{{font-size:.72em;color:#64748b;font-weight:600}}
.controls select{{padding:5px 10px;border:1px solid #e2e8f0;border-radius:6px;font-size:.78em;background:#fff;cursor:pointer}}

.gantt-wrap{{padding:16px 24px;overflow:auto;max-height:calc(100vh - 130px)}}
.gantt-canvas{{position:relative;min-width:100%}}

/* Timeline month header */
.tl-months{{display:flex;position:sticky;top:0;z-index:21;background:#fff;border-bottom:2px solid #e2e8f0}}
.tl-months .tl-label-col{{min-width:320px;max-width:320px;position:sticky;left:0;z-index:25;background:#0f172a;padding:6px 12px;display:flex;align-items:center;box-shadow:4px 0 8px rgba(0,0,0,.15)}}
.tl-months .tl-label-col span{{color:#94a3b8;font-size:.72em;font-weight:600}}
.tl-month-cell{{display:flex;align-items:center;justify-content:center;font-size:.75em;font-weight:700;color:#1e293b;background:#f8fafc;border-right:2px solid #e2e8f0;padding:4px 0}}

/* Timeline day header */
.tl-header{{display:flex;position:sticky;top:28px;z-index:20;background:#fff;border-bottom:1px solid #e2e8f0}}
.tl-header .tl-label-col{{min-width:320px;max-width:320px;position:sticky;left:0;z-index:25;background:#f1f5f9;padding:2px 12px;display:flex;align-items:center;box-shadow:4px 0 8px rgba(0,0,0,.08)}}
.tl-header .tl-label-col span{{color:#94a3b8;font-size:.6em}}
.tl-days{{display:flex}}
.tl-day{{min-width:8px;max-width:8px;text-align:center;font-size:.5em;color:#94a3b8;padding:1px 0;border-right:1px solid #f1f5f9}}
.tl-day.weekend{{background:#f1f5f9;color:#cbd5e1}}
.tl-day.month-start{{border-left:2px solid #cbd5e1}}
.tl-day.today-col{{background:#fef2f2;color:#dc2626;font-weight:700}}

/* Rows */
.g-row{{display:flex;border-bottom:1px solid #e8ecf1;min-height:30px;align-items:stretch}}
.g-row:hover{{background:#f8fafc}}

/* Label column — frozen panel with shadow */
.g-label{{min-width:320px;max-width:320px;position:sticky;left:0;z-index:10;background:#fff;display:flex;align-items:center;padding:0 8px;border-right:2px solid #cbd5e1;box-shadow:4px 0 8px rgba(0,0,0,.06)}}
.g-row:hover .g-label{{background:#f8fafc}}

/* Customer group header */
.g-group{{background:#f8fafc;border-bottom:2px solid #e2e8f0;cursor:pointer;user-select:none}}
.g-group:hover{{background:#e2e8f0}}
.g-group .g-label{{background:#f8fafc;font-weight:700;font-size:.82em;gap:8px;box-shadow:4px 0 8px rgba(0,0,0,.06)}}
.g-group:hover .g-label{{background:#e2e8f0}}
.g-group .g-arrow{{font-size:.65em;color:#64748b;transition:transform .2s;width:14px;text-align:center}}
.g-group.open .g-arrow{{transform:rotate(90deg)}}
.g-group .g-count{{font-size:.65em;color:#94a3b8;font-weight:400;margin-left:4px}}
.g-group .g-badges{{display:flex;gap:4px;margin-left:auto;margin-right:4px}}
.g-group .g-badge{{font-size:.6em;padding:1px 6px;border-radius:8px;font-weight:600}}

/* Task row */
.g-task .g-label{{font-size:.72em;color:#475569;padding-left:28px;gap:6px}}
.g-task .g-label a{{color:#2563eb;text-decoration:none;font-weight:600;font-size:.95em}}
.g-task .g-label a:hover{{text-decoration:underline}}
.g-task .g-label .g-tname{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px}}
.g-task .g-label .g-person{{font-size:.85em;color:#94a3b8;margin-left:auto;white-space:nowrap}}
.g-task.hidden{{display:none}}

/* Bar area */
.g-bars{{display:flex;position:relative;flex:1;min-height:28px}}
.g-cell{{min-width:8px;border-right:1px solid #f8fafc00}}
.g-cell.weekend{{background:#f8fafc}}
.g-cell.month-start{{border-left:1px solid #e2e8f0}}

.bar{{position:absolute;top:4px;height:20px;border-radius:4px;min-width:6px;cursor:pointer;transition:filter .12s;z-index:2;box-shadow:0 1px 4px rgba(0,0,0,.12)}}
.bar:hover{{filter:brightness(1.15);box-shadow:0 2px 8px rgba(0,0,0,.2)}}
.bar-done{{background:linear-gradient(90deg,#059669,#34d399)}}
.bar-late{{background:linear-gradient(90deg,#dc2626,#f87171)}}
.bar-active{{background:linear-gradient(90deg,#2563eb,#60a5fa)}}
.bar-noeta{{background:linear-gradient(90deg,#94a3b8,#cbd5e1)}}
.bar-blocked{{background:linear-gradient(90deg,#d97706,#fbbf24)}}
.bar-projected{{border:2px dashed #94a3b8;background:#94a3b815;top:6px;height:16px}}
.bar-summary{{background:linear-gradient(90deg,#1e40af33,#3b82f633);border-radius:4px;top:5px;height:18px;border:1px solid #3b82f644}}

.today-marker{{position:absolute;top:0;bottom:0;width:2px;background:#dc2626;z-index:3;pointer-events:none;opacity:.8}}
.month-line{{position:absolute;top:0;bottom:0;width:1px;background:#cbd5e1;z-index:1;pointer-events:none;opacity:.5}}

/* Tooltip */
.tip{{display:none;position:fixed;z-index:1000;background:#1e293bee;color:#e2e8f0;padding:12px 16px;border-radius:8px;font-size:.78em;line-height:1.7;max-width:400px;pointer-events:none;box-shadow:0 8px 24px rgba(0,0,0,.3);backdrop-filter:blur(4px)}}
.tip b{{color:#93c5fd}}.tip .tl{{color:#94a3b8;font-size:.9em}}.tip .tg{{color:#34d399}}.tip .tr{{color:#f87171}}.tip .tb{{color:#60a5fa}}

.legend{{padding:8px 24px;display:flex;gap:14px;font-size:.7em;color:#64748b;background:#fff;border-top:1px solid #e2e8f0;flex-wrap:wrap}}
.legend span{{display:flex;align-items:center;gap:4px}}
.legend i{{display:inline-block;width:14px;height:10px;border-radius:2px}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Gantt Chart</h1>
    <div class="sub">Task timelines by customer &middot; {build_date}</div>
  </div>
  <div class="stats" id="stats"></div>
</div>

<div class="controls">
  <label>Person</label>
  <select id="fPerson"><option value="ALL">All People</option></select>
  <label>Status</label>
  <select id="fStatus">
    <option value="ALL">All</option>
    <option value="active">Active Only</option>
  </select>
  <label>Customer</label>
  <select id="fCustomer"><option value="ALL">All Customers</option></select>
  <label>Demand</label>
  <select id="fCategory">
    <option value="ALL">All</option>
    <option value="External">External</option>
    <option value="Internal">Internal</option>
  </select>
  <label>View</label>
  <select id="fView">
    <option value="ALL">All Tasks</option>
    <option value="implementing">Active Implementations</option>
  </select>
  <label>Period</label>
  <select id="fPeriod">
    <option value="3m">Last 3 Months</option>
    <option value="1m">Last Month</option>
    <option value="6m" selected>Last 6 Months</option>
    <option value="all">All Time</option>
  </select>
</div>

<div class="legend">
  <span><i style="background:linear-gradient(90deg,#059669,#34d399)"></i> On Time</span>
  <span><i style="background:linear-gradient(90deg,#dc2626,#f87171)"></i> Late</span>
  <span><i style="background:linear-gradient(90deg,#2563eb,#60a5fa)"></i> Active</span>
  <span><i style="background:linear-gradient(90deg,#d97706,#fbbf24)"></i> Blocked</span>
  <span><i style="background:linear-gradient(90deg,#94a3b8,#cbd5e1)"></i> No ETA</span>
  <span><i style="border:2px dashed #94a3b8;background:#94a3b822"></i> Projected</span>
  <span style="color:#dc2626;font-weight:700">| Today</span>
</div>

<div class="gantt-wrap" id="wrap">
  <div class="gantt-canvas" id="canvas"></div>
</div>

<div class="tip" id="tip"></div>

<script>
const RAW={data_json_safe};
const TODAY=new Date().toISOString().slice(0,10);
/* Dynamic day width: fit visible range nicely */
const DAY_W=8;

function pd(s){{if(!s||s.length<10)return null;return new Date(s.slice(0,10)+'T12:00:00Z')}}
function db(a,b){{return Math.round((b-a)/864e5)}}
function esc(s){{return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')}}

const tip=document.getElementById('tip');
function showTip(e,html){{tip.innerHTML=html;tip.style.display='block';const r=tip.getBoundingClientRect();let x=e.clientX+14,y=e.clientY-10;if(x+r.width>innerWidth)x=e.clientX-r.width-14;if(y+r.height>innerHeight)y=e.clientY-r.height-10;if(y<0)y=8;tip.style.left=x+'px';tip.style.top=y+'px'}}
function hideTip(){{tip.style.display='none'}}
document.getElementById('wrap').addEventListener('scroll',hideTip);

// Populate filters
const ppl=[...new Set(RAW.map(r=>r.tsa||''))].filter(Boolean).sort();
ppl.forEach(p=>{{const o=document.createElement('option');o.value=p;o.textContent=p;document.getElementById('fPerson').appendChild(o)}});
const custs=[...new Set(RAW.map(r=>r.customer).filter(Boolean))].sort();
custs.forEach(c=>{{const o=document.createElement('option');o.value=c;o.textContent=c;document.getElementById('fCustomer').appendChild(o)}});
const statuses=[...new Set(RAW.map(r=>r.status).filter(Boolean))].sort();
statuses.forEach(s=>{{const o=document.createElement('option');o.value=s;o.textContent=s;document.getElementById('fStatus').appendChild(o)}});

function getFiltered(){{
  const person=document.getElementById('fPerson').value;
  const status=document.getElementById('fStatus').value;
  const customer=document.getElementById('fCustomer').value;
  const category=document.getElementById('fCategory').value;
  const view=document.getElementById('fView').value;
  const period=document.getElementById('fPeriod').value;
  let cutoff=null;
  if(period!=='all'){{const d=new Date();d.setMonth(d.getMonth()-(period==='1m'?1:period==='3m'?3:6));cutoff=d.toISOString().slice(0,10)}}

  /* For "implementing" view: find customers that have active tasks, then show ALL tasks for those customers */
  let activeCustomers=null;
  if(view==='implementing'){{
    activeCustomers=new Set();
    RAW.forEach(r=>{{
      if(['In Progress','In Review','Production QA','Ready to Deploy'].includes(r.status)&&r.customer)activeCustomers.add(r.customer);
    }});
  }}

  return RAW.filter(r=>{{
    if(person!=='ALL'&&r.tsa!==person)return false;
    if(status==='active'&&(r.status==='Done'||r.status==='Canceled'))return false;
    if(status!=='ALL'&&status!=='active'&&r.status!==status)return false;
    if(customer!=='ALL'&&r.customer!==customer)return false;
    if(category!=='ALL'&&r.category!==category)return false;
    if(activeCustomers&&!activeCustomers.has(r.customer))return false;
    const s=r.startedAt||r.dateAdd||'';
    const e=r.delivery||r.eta||'';
    if(cutoff&&(s||'9999')<cutoff&&(e||'9999')<cutoff)return false;
    return true;
  }});
}}

function barCls(r){{
  if(r.perf==='Blocked'||r.status==='B.B.C')return'bar-blocked';
  if(r.status==='Done')return r.perf==='Late'?'bar-late':'bar-done';
  if(['In Progress','In Review','Production QA','Ready to Deploy','Paused'].includes(r.status))return'bar-active';
  return'bar-noeta';
}}

function tipHtml(r){{
  const cls=r.perf==='On Time'?'tg':r.perf==='Late'?'tr':r.status==='In Progress'?'tb':'tl';
  const s=pd(r.startedAt||r.dateAdd),e=pd(r.delivery||r.eta);
  const dur=s&&e?db(s,e):null;
  return`<b>${{esc(r.focus||'')}}</b>${{r.customer?' ['+esc(r.customer)+']':''}}<br>`+
    `<span class="tl">Person:</span> ${{esc(r.tsa||'')}}<br>`+
    `<span class="tl">Status:</span> <span class="${{cls}}">${{esc(r.status||'')}}</span> &middot; <span class="${{cls}}">${{esc(r.perf||'')}}</span><br>`+
    `<span class="tl">Start:</span> ${{esc(r.startedAt||r.dateAdd||'\\u2014')}} &middot; <span class="tl">ETA:</span> ${{esc(r.eta||'\\u2014')}} &middot; <span class="tl">Done:</span> ${{esc(r.delivery||'\\u2014')}}<br>`+
    (dur!==null?`<span class="tl">Duration:</span> ${{dur}}d<br>`:'')+
    (r.ticketId?`<span class="tl">Ticket:</span> ${{esc(r.ticketId||'')}}`:'');
}}

function render(){{
  const data=getFiltered();

  // Date range
  let minD=TODAY,maxD=TODAY;
  data.forEach(r=>{{
    const s=r.startedAt||r.dateAdd||'';
    const e=r.delivery||r.eta||s;
    if(s&&s<minD)minD=s;if(e&&e>maxD)maxD=e;if(s&&s>maxD)maxD=s;
  }});
  const sd=pd(minD),ed=pd(maxD);
  if(!sd||!ed)return;
  sd.setDate(sd.getDate()-5);ed.setDate(ed.getDate()+10);
  const totalDays=db(sd,ed)+1;

  // Build day index
  const days=[];
  for(let i=0;i<totalDays;i++){{const d=new Date(sd);d.setDate(d.getDate()+i);days.push(d)}}
  function dayIdx(dateStr){{const d=pd(dateStr);if(!d)return-1;return db(sd,d)}}

  // Group by customer
  const groups={{}};
  data.forEach(r=>{{
    const c=r.customer||'No Customer';
    if(!groups[c])groups[c]=[];
    groups[c].push(r);
  }});
  // Sort groups by task count desc
  const sortedGroups=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length);

  // Timeline: Month row (wide, readable) + Day row (tiny numbers)
  const mNames=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  // Build month spans
  const months=[];
  let curM=-1,curY=-1,curCount=0;
  days.forEach(d=>{{
    if(d.getMonth()!==curM||d.getFullYear()!==curY){{
      if(curCount>0)months.push({{label:mNames[curM]+' '+curY,days:curCount}});
      curM=d.getMonth();curY=d.getFullYear();curCount=0;
    }}
    curCount++;
  }});
  if(curCount>0)months.push({{label:mNames[curM]+' '+curY,days:curCount}});

  // Month header
  let html='<div class="tl-months"><div class="tl-label-col"><span>Customer / Task</span></div>';
  months.forEach(m=>{{
    html+=`<div class="tl-month-cell" style="min-width:${{m.days*DAY_W}}px;max-width:${{m.days*DAY_W}}px">${{m.label}}</div>`;
  }});
  html+='</div>';

  // Day header
  html+='<div class="tl-header"><div class="tl-label-col"><span></span></div><div class="tl-days">';
  days.forEach(d=>{{
    const ds=d.toISOString().slice(0,10);
    const dow=d.getDay();
    const isWe=dow===0||dow===6;
    const isMs=d.getDate()===1;
    const isToday=ds===TODAY;
    let cls=isWe?'tl-day weekend':'tl-day';
    if(isMs)cls+=' month-start';
    if(isToday)cls+=' today-col';
    const label=(d.getDate()%7===1||d.getDate()===1)?d.getDate():'';
    html+=`<div class="${{cls}}" style="min-width:${{DAY_W}}px;max-width:${{DAY_W}}px">${{label}}</div>`;
  }});
  html+='</div></div>';

  // Pre-compute month divider positions
  const monthDividers=[];
  days.forEach((d,i)=>{{if(d.getDate()===1)monthDividers.push(i)}});
  function monthLines(){{return monthDividers.map(i=>`<div class="month-line" style="left:${{i*DAY_W}}px"></div>`).join('')}}

  // Groups
  sortedGroups.forEach(([cust,tasks])=>{{
    // Sort tasks by start date
    tasks.sort((a,b)=>(a.startedAt||a.dateAdd||'z').localeCompare(b.startedAt||b.dateAdd||'z'));

    // Group stats
    const done=tasks.filter(t=>t.status==='Done').length;
    const active=tasks.filter(t=>['In Progress','In Review','Todo','Paused','Production QA'].includes(t.status)).length;
    const late=tasks.filter(t=>t.perf==='Late').length;
    const onTime=tasks.filter(t=>t.perf==='On Time').length;

    // Summary bar range
    let gMin=null,gMax=null;
    tasks.forEach(t=>{{
      const s=t.startedAt||t.dateAdd||'';
      const e=t.delivery||t.eta||s;
      if(s&&(!gMin||s<gMin))gMin=s;
      if(e&&(!gMax||e>gMax))gMax=e;
    }});
    const gStartIdx=dayIdx(gMin);
    const gEndIdx=dayIdx(gMax);
    const gLen=Math.max(1,gEndIdx-gStartIdx+1);

    // Customer header row
    const gid='grp_'+cust.replace(/[^a-zA-Z0-9]/g,'_');
    html+=`<div class="g-row g-group" data-grp="${{gid}}" onclick="toggleGroup(this)">`;
    html+=`<div class="g-label">`;
    html+=`<span class="g-arrow">&#9654;</span>`;
    html+=`<span>${{esc(cust)}}</span>`;
    html+=`<span class="g-count">${{tasks.length}}</span>`;
    html+=`<div class="g-badges">`;
    if(onTime)html+=`<span class="g-badge" style="background:#d1fae5;color:#065f46">${{onTime}} ok</span>`;
    if(late)html+=`<span class="g-badge" style="background:#fee2e2;color:#991b1b">${{late}} late</span>`;
    if(active)html+=`<span class="g-badge" style="background:#dbeafe;color:#1e40af">${{active}} active</span>`;
    html+=`</div></div>`;

    // Summary bar area with month dividers
    html+=`<div class="g-bars" style="min-width:${{totalDays*DAY_W}}px">`;
    html+=monthLines();
    if(gStartIdx>=0){{
      html+=`<div class="bar bar-summary" style="left:${{gStartIdx*DAY_W}}px;width:${{gLen*DAY_W}}px"></div>`;
    }}
    const tIdx=dayIdx(TODAY);
    if(tIdx>=0&&tIdx<totalDays)html+=`<div class="today-marker" style="left:${{tIdx*DAY_W}}px"></div>`;
    html+=`</div></div>`;

    // Task rows (hidden by default) — sub-group by person, show name once
    let lastPerson='';
    tasks.sort((a,b)=>{{const pc=(a.tsa||'').localeCompare(b.tsa||'');return pc!==0?pc:(a.startedAt||a.dateAdd||'z').localeCompare(b.startedAt||b.dateAdd||'z')}});
    tasks.forEach(t=>{{
      const s=t.startedAt||t.dateAdd||'';
      const e=t.delivery||t.eta||'';
      let si=dayIdx(s),ei=dayIdx(e||s);
      si=Math.max(0,Math.min(si,totalDays-1));
      ei=Math.max(0,Math.min(ei,totalDays-1));
      const len=Math.max(1,ei-si+1);
      const cls=barCls(t);
      const isProj=!t.delivery&&t.eta&&t.status!=='Done';
      const bCls=cls+(isProj?' bar-projected':'');
      const tHtml=tipHtml(t);
      const focusTxt=t.focus||'';

      html+=`<div class="g-row g-task hidden" data-grp="${{gid}}">`;
      // Label
      html+=`<div class="g-label">`;
      if(t.ticketUrl&&t.ticketUrl.startsWith('http'))html+=`<a href="${{esc(t.ticketUrl)}}" target="_blank">${{esc(t.ticketId||'')}}</a>`;
      else if(t.ticketId)html+=`<span>${{esc(t.ticketId)}}</span>`;
      html+=`<span class="g-tname" title="${{esc(focusTxt)}}">${{esc(focusTxt.length>40?focusTxt.slice(0,38)+'...':focusTxt)}}</span>`;
      const showPerson=(t.tsa||'')!==lastPerson;
      lastPerson=t.tsa||'';
      if(showPerson)html+=`<span class="g-person">${{esc(t.tsa||'')}}</span>`;
      html+=`</div>`;

      // Bar area with month dividers
      html+=`<div class="g-bars" style="min-width:${{totalDays*DAY_W}}px">`;
      html+=monthLines();
      if(si<=totalDays&&ei>=0){{
        html+=`<div class="bar ${{bCls}}" style="left:${{si*DAY_W}}px;width:${{len*DAY_W}}px"
          onmouseenter="showTip(event,this.dataset.tip)"
          onmousemove="showTip(event,this.dataset.tip)"
          onmouseleave="hideTip()"
          data-tip="${{esc(tHtml)}}"></div>`;
      }}
      html+=`</div></div>`;
    }});
  }});

  document.getElementById('canvas').innerHTML=html;

  // Stats
  const done=data.filter(r=>r.status==='Done').length;
  const active=data.filter(r=>['In Progress','In Review','Todo','Paused'].includes(r.status)).length;
  document.getElementById('stats').innerHTML=`${{data.length}} tasks &middot; ${{done}} done &middot; ${{active}} active &middot; ${{sortedGroups.length}} customers`;
}}

function toggleGroup(el){{
  el.classList.toggle('open');
  const gid=el.dataset.grp;
  document.querySelectorAll(`.g-task[data-grp="${{gid}}"]`).forEach(r=>r.classList.toggle('hidden'));
}}

let _renderTimer=null;
function debouncedRender(){{clearTimeout(_renderTimer);_renderTimer=setTimeout(render,150)}}
['fPerson','fStatus','fCustomer','fCategory','fView','fPeriod'].forEach(id=>document.getElementById(id).addEventListener('change',debouncedRender));
render();
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f'Gantt saved: {OUTPUT}')
print(f'Size: {len(HTML)//1024}KB')
print(f'Records: {len(records)}')
