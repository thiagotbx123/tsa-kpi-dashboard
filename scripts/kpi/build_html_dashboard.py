# Architecture note: This file generates a self-contained HTML dashboard.
# The HTML/CSS/JS is embedded as a raw string for single-file deployment.
# Structure: CSS (lines ~45-270) | HTML (270-440) | JS (440-2080)
# To lint JS independently, extract the <script> block to a temp file.

"""Build Raccoons KPI HTML Dashboard v3 — audit-hardened version.

Changes from v2:
  - H1: Dynamic isCoreWeek (data-driven, no hardcoded period)
  - H2: Member card accuracy aligned with KPI1 formula
  - H9: Sanitized JSON injection (no XSS via </script>)
  - H12: CDN fallback with inline Chart.js error handling
  - H14/M15: Sample size (n) displayed next to percentages
  - C1: KPI3 marked as NOT ACTIVE until rework labels are in use
  - M7: Tab-specific trend chart bars
  - M11: Data staleness warning
  - M12: Default segment = All (was External)
  - D.LIE10: B.B.C tasks excluded from Overdue
  - D.LIE12: ETA Coverage metric on member cards
  - L2: JSON validation before injection

Usage: python kpi/build_html_dashboard.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os, json, datetime

SCRIPT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(SCRIPT_DIR, '..', '_dashboard_data.json')

# Import team config for KPI_IDS injection
from team_config import PERSON_MAP_BY_ID, OUTPUT_DIR
KPI_IDS_JSON = json.dumps(list(PERSON_MAP_BY_ID.keys()))
OUTPUT = os.path.join(OUTPUT_DIR, 'KPI_DASHBOARD.html')

# L2: Validate JSON before processing
try:
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data_raw = json.load(f)
    data_json = json.dumps(data_raw, ensure_ascii=True)
except json.JSONDecodeError as e:
    print(f"ERROR: Malformed JSON in {DATA_PATH}: {e}")
    sys.exit(1)

# Load implementation timeline data
TIMELINE_PATH = os.path.join(SCRIPT_DIR, 'implementation_timeline.json')
try:
    with open(TIMELINE_PATH, 'r', encoding='utf-8') as f:
        timeline_raw = json.load(f)
    timeline_json = json.dumps(timeline_raw, ensure_ascii=True)
except (FileNotFoundError, json.JSONDecodeError):
    timeline_raw = []
    timeline_json = '[]'

# H9: Sanitize JSON for safe inline injection — escape </script> sequences
data_json_safe = data_json.replace('</script>', '<\\/script>').replace('</Script>', '<\\/Script>')
timeline_json_safe = timeline_json.replace('</script>', '<\\/script>').replace('</Script>', '<\\/Script>')

# M11: Record build timestamp for staleness detection
build_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
# A37-002: Use API cache file mtime as "last refresh" indicator instead of build date
_kpi_cache = os.path.join(SCRIPT_DIR, '..', '_kpi_all_members.json')
if os.path.exists(_kpi_cache):
    _cache_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(_kpi_cache))
    api_refresh_date = _cache_mtime.strftime('%Y-%m-%d %H:%M')
else:
    api_refresh_date = 'unknown'
# Find the most recent dateAdd in data for staleness comparison (only past/present dates)
data_dates = [r.get('dateAdd', '') for r in data_raw
              if r.get('dateAdd', '') and len(r.get('dateAdd', '')) >= 10 and r['dateAdd'][:10] <= build_date[:10]]
latest_data_date = max(data_dates) if data_dates else build_date

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KPI Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#f8fafc;--white:#fff;--border:#d1d5db;--text:#1b1b1b;
  --dim:#6b7280;--light:#9ca3af;--accent:#2563eb;
  --green:#059669;--green-bg:#ecfdf5;--green-l:#d1fae5;
  --red:#dc2626;--red-bg:#fef2f2;--red-l:#fee2e2;
  --yellow:#d97706;--yellow-bg:#fffbeb;--yellow-l:#fef3c7;
  --blue:#2563eb;--blue-bg:#eff6ff;--blue-l:#dbeafe;
  --gray-bg:#f3f4f6;--gray-l:#e5e7eb;
}
body{font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);padding:28px 40px;min-height:100vh;font-size:15px;line-height:1.5}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;background:linear-gradient(135deg,#064e3b,#065f46,#047857);color:#fff;padding:18px 28px;border-radius:10px}
.header h1{font-size:1.4em;font-weight:700;color:#fff}
.header .linear-link{display:inline-flex;align-items:center;gap:6px;color:#fff;font-size:.78em;text-decoration:none;padding:5px 12px;border-radius:6px;background:#5E6AD2;border:1px solid #7B83E8;transition:all .15s;margin-top:4px}
.header .linear-link:hover{background:#4B55B8;color:#fff;border-color:#9BA1F0}
.header .linear-link svg{width:14px;height:14px;fill:currentColor}
.header .tbx-logo{height:44px;transition:opacity .15s}
.header .tbx-logo:hover{opacity:.85}
.filters{display:flex;gap:8px;align-items:center;margin-bottom:20px;flex-wrap:wrap}
.filters label{font-size:.72em;color:#9ca3af;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.filters select{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;padding:5px 10px;border-radius:6px;font-size:.82em;cursor:pointer}
.filters select option{background:#064e3b;color:#fff}
.filters select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 2px rgba(37,99,235,.3)}
.top-strip{display:flex;gap:8px;margin-bottom:18px;align-items:stretch}
.strip-group{display:flex;gap:6px;flex:1;padding:6px;border-radius:10px;background:var(--white);border:1px solid var(--border)}
.strip-group.filters-group{flex:0 0 auto;background:#f0fdf4;border-color:#a7f3d0}
.strip-group.filters-group::before{content:'FILTERS';position:absolute;top:-8px;left:12px;font-size:.5em;font-weight:700;color:#065f46;background:#f0fdf4;padding:0 4px;letter-spacing:1px;display:none}
.strip-group.kpi-group{background:#eff6ff;border-color:#bfdbfe}
.kpi-cell{flex:1;background:transparent;border:1px solid transparent;border-radius:8px;padding:10px 8px;text-align:center;position:relative;cursor:pointer;transition:all .15s}
.kpi-cell:hover{background:#dbeafe;border-color:#93c5fd}
.kpi-cell.kpi-active{border-color:var(--accent);border-width:2px;background:#dbeafe}
.kpi-cell .kc-name{font-size:.65em;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-bottom:2px}
.kpi-cell .kc-val{font-size:1.3em;font-weight:800;line-height:1.3}
.kpi-cell .kc-meta{font-size:.6em;color:var(--dim);margin-top:1px}
.kpi-cell .badge{font-size:.52em;font-weight:700;padding:1px 5px;border-radius:20px;display:inline-block;margin-top:4px}
.badge-pass{background:var(--green-l);color:var(--green)}
.badge-fail{background:var(--red-l);color:var(--red)}
.badge-warn{background:var(--yellow-l);color:var(--yellow)}
.badge-inactive{background:var(--gray-l);color:var(--dim)}
.staleness-banner{padding:8px 16px;border-radius:6px;font-size:.78em;font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.staleness-ok{background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0}
.staleness-warn{background:#fffbeb;color:#92400e;border:1px solid #fde68a}
.staleness-old{background:#fef2f2;color:#991b1b;border:1px solid #fecaca}
.tabs{display:flex;gap:0;margin-bottom:0;border-bottom:2px solid var(--border)}
.tab{padding:12px 24px;font-size:.9em;font-weight:600;color:var(--dim);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s}
.tab:hover{color:var(--text)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-panel{display:none;padding-top:16px}
.tab-panel.active{display:block}
.grid-section{background:var(--white);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:16px}
.grid-section .title{padding:14px 20px;font-size:.9em;font-weight:700;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
.grid-section .title .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.info-btn{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:var(--gray-bg);color:var(--dim);font-size:.7em;font-weight:700;cursor:help;margin-left:4px;border:1px solid var(--border)}
.heatmap{width:100%;border-collapse:collapse;font-size:.88em}
.heatmap th,.heatmap td{padding:9px 12px;text-align:center;white-space:nowrap}
.heatmap thead th{background:var(--gray-bg);font-weight:600;color:var(--dim);font-size:.8em;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid var(--border)}
.heatmap .month-header{background:#eef2ff;color:var(--blue);font-weight:700;font-size:.88em;letter-spacing:.5px;border-bottom:2px solid var(--blue-l);padding:10px 8px;border-left:3px solid var(--accent)}
.heatmap .week-header{background:var(--gray-bg);font-size:.78em;color:var(--dim);padding:7px 8px}
.heatmap .month-first{border-left:3px solid var(--accent)!important}
.heatmap .person-label{text-align:left;font-weight:600;padding-left:16px;background:var(--white);border-right:2px solid var(--border);min-width:120px;font-size:.9em;color:var(--text);position:sticky;left:0;z-index:2}
.heatmap .team-row td{font-weight:800;background:#eef2ff;border-top:3px solid var(--accent);font-size:.92em}
.heatmap .team-row .person-label{background:#eef2ff;color:var(--accent);font-size:.82em;text-transform:uppercase;letter-spacing:.3px;font-weight:800;white-space:normal;line-height:1.3;position:sticky;left:0;z-index:2}
.heatmap td.cell{min-width:60px;font-weight:600;font-size:.9em;border:1px solid var(--gray-l);cursor:default;position:relative;transition:transform .1s}
.heatmap td.cell:hover{transform:scale(1.05);z-index:1;box-shadow:0 2px 8px rgba(0,0,0,.12)}
.heatmap td.total-col{background:#eef2ff!important;font-weight:800;border-left:3px solid var(--accent);font-size:.92em}
.heat-great{background:#d1fae5;color:#065f46}
.heat-good{background:#ecfdf5;color:#059669}
.heat-ok{background:#fefce8;color:#92400e}
.heat-bad{background:#fef2f2;color:#991b1b}
.heat-terrible{background:#fecaca;color:#7f1d1d}
.heat-na{background:var(--white);color:#d5d8dd;font-weight:300;font-size:.75em}
.heat-zero{background:var(--gray-bg);color:var(--light);font-style:italic}
.tooltip{position:fixed;background:linear-gradient(135deg,rgba(15,23,42,.88),rgba(30,41,59,.92));backdrop-filter:blur(8px);color:#fff;padding:14px 18px;border-radius:10px;font-size:.82em;pointer-events:none;z-index:999;max-width:420px;line-height:1.6;box-shadow:0 8px 30px rgba(0,0,0,.4);display:none;border:1px solid rgba(255,255,255,.08)}
.tooltip b{color:#93c5fd}
.tooltip .tip-hdr{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,.12)}
.tooltip .tip-hdr b{font-size:1.05em;color:#60a5fa}
.tooltip .tip-hdr .tip-pct{font-size:1.3em;font-weight:800;color:#fff}
.tooltip .tip-hdr .tip-pct.good{color:#34d399}
.tooltip .tip-hdr .tip-pct.bad{color:#f87171}
.tooltip .tip-hdr .tip-pct.mid{color:#fbbf24}
.tooltip .tip-stats{display:flex;gap:12px;margin:6px 0;font-size:.88em}
.tooltip .tip-stat{text-align:center}
.tooltip .tip-stat b{display:block;font-size:1.1em;color:#fff}
.tooltip .tip-stat span{color:#94a3b8;font-size:.85em}
.tooltip .tip-section{margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.12)}
.tooltip .tip-task{color:#e2e8f0;font-size:.88em;padding:4px 0 4px 10px;border-left:2px solid transparent;margin:2px 0}
.tooltip .tip-task.tip-late{border-left-color:#f87171}
.tooltip .tip-task.tip-ontime{border-left-color:#34d399}
.tooltip .tip-task.tip-overdue{border-left-color:#fbbf24}
.tooltip .tip-task .tip-cust{color:#a78bfa;font-size:.9em;font-weight:600}
.tooltip .tip-task .tip-dates{color:#64748b;font-size:.85em}
.tooltip .tip-task .tip-delay{color:#fbbf24;font-weight:700;font-size:.9em}
.tooltip .tip-label{color:#94a3b8;font-size:.82em;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.detail-panel{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:16px;margin-top:16px}
.detail-panel h3{font-size:.85em;font-weight:700;margin-bottom:8px;color:var(--text)}
.detail-table{width:100%;border-collapse:collapse;font-size:.78em}
.detail-table th{background:var(--gray-bg);padding:6px 10px;text-align:left;font-weight:600;color:var(--dim);font-size:.75em;text-transform:uppercase;letter-spacing:.3px}
.detail-table td{padding:5px 10px;border-bottom:1px solid var(--gray-l)}
.detail-table tr:hover td{background:var(--blue-bg)}
.trend-row{padding:0}
.trend-wrap{padding:16px 20px;border-bottom:1px solid var(--border)}
.trend-wrap h4{font-size:.78em;color:var(--dim);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.trend-wrap canvas{width:100%!important;height:160px!important}
.segment-btn{flex:1;padding:10px 8px;border-radius:8px;font-size:.85em;font-weight:700;color:#065f46;cursor:pointer;transition:all .15s;border:1px solid transparent;background:transparent;letter-spacing:.2px;text-align:center}
.segment-btn:hover{background:#d1fae5;border-color:#a7f3d0}
.segment-btn.active{background:#065f46;color:#fff;border-color:#065f46;box-shadow:0 1px 3px rgba(0,0,0,.15)}
.segment-btn .seg-count{display:block;font-size:.75em;font-weight:400;opacity:.7;margin-top:2px}
.audit-section{background:var(--white);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-top:20px}
.audit-header{display:flex;align-items:center;padding:14px 20px;border-bottom:1px solid var(--border);cursor:pointer;user-select:none;gap:10px}
.audit-header h3{font-size:.9em;font-weight:700;display:flex;align-items:center;gap:8px}
.audit-header .toggle{font-size:.75em;color:var(--dim);transition:transform .2s}
.audit-header.open .toggle{transform:rotate(180deg)}
.audit-tools{display:flex;gap:6px}
.audit-tools button{background:var(--gray-bg);border:1px solid var(--border);border-radius:6px;padding:5px 12px;font-size:.72em;font-weight:600;color:var(--dim);cursor:pointer;transition:all .15s}
.audit-tools button:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
.audit-body{max-height:0;overflow:hidden;transition:max-height .3s ease}
.audit-body.open{max-height:none;overflow-x:auto}
.audit-table{width:100%;border-collapse:collapse;font-size:.75em;font-family:'Consolas','Menlo','Courier New',monospace}
.audit-table th{background:#064e3b;color:#fff;padding:8px 10px;text-align:left;font-weight:600;font-size:.78em;text-transform:uppercase;letter-spacing:.5px;position:sticky;top:0;cursor:pointer;white-space:nowrap}
.audit-table th:hover{background:#047857}
.audit-table th .sort-arrow{margin-left:4px;font-size:.7em;opacity:.5}
.audit-table td{padding:5px 10px;border-bottom:1px solid var(--gray-l);white-space:nowrap}
.audit-table tr:nth-child(even) td{background:#fafbfc}
.audit-table tr:hover td{background:var(--blue-bg)}
.audit-table .perf-on-time{color:var(--green);font-weight:600}
.audit-table .perf-late{color:var(--red);font-weight:600}
.audit-table .perf-on-track{color:#2563eb;font-weight:600}
.audit-table .perf-on-hold{color:#d97706;font-weight:600}
.audit-table .perf-overdue{color:var(--yellow);font-weight:600}
.audit-table .perf-na{color:var(--light)}
.audit-table .perf-not-started{color:#a78bfa;font-weight:500}
.audit-table .rework-yes{color:var(--red);font-weight:700}
.audit-stats{padding:10px 20px;font-size:.72em;color:var(--dim);border-top:1px solid var(--gray-l);display:flex;gap:16px;flex-wrap:wrap}
.member-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:18px}
.member-card{background:var(--white);border:1px solid var(--border);border-radius:8px;padding:12px 14px;position:relative;overflow:hidden;display:flex;flex-direction:column}
.member-card .mc-name{font-weight:700;font-size:.88em;margin-bottom:6px;color:var(--text)}
.member-card .mc-body{flex:1}
.member-card .mc-row{display:flex;justify-content:space-between;font-size:.72em;color:var(--dim);padding:2px 0}
.member-card .mc-row span[title]{cursor:help;border-bottom:1px dotted var(--dim)}
.member-card .mc-row b{color:var(--text)}
.member-card .mc-bar{margin-top:auto;padding-top:8px}
.member-card .mc-bar-track{height:4px;border-radius:2px;background:var(--gray-l);overflow:hidden}
.member-card .mc-bar-inner{height:100%;border-radius:2px;transition:width .3s}
.member-card .mc-alert{position:absolute;top:8px;right:10px;font-size:.65em;font-weight:700;padding:2px 6px;border-radius:10px}
.mc-alert-warn{background:var(--yellow-l);color:var(--yellow)}
.mc-alert-ok{background:var(--green-l);color:var(--green)}
.heat-vol-0{background:var(--white);color:#d5d8dd;font-weight:300;font-size:.75em}
.heat-vol-1{background:#eff6ff;color:var(--blue)}
.heat-vol-2{background:#dbeafe;color:#1d4ed8}
.heat-vol-3{background:#bfdbfe;color:#1e40af}
.heat-vol-4{background:#93c5fd;color:#1e3a8a}
.heat-vol-5{background:#3b82f6;color:#fff}
.footer{text-align:center;margin-top:24px;padding:12px;color:var(--light);font-size:.7em}
.scrum-card{background:var(--white);border:1px solid var(--border);border-radius:10px;overflow:hidden;cursor:pointer;transition:all .15s}
.scrum-card:hover{border-color:var(--accent);box-shadow:0 2px 12px rgba(37,99,235,.12)}
.scrum-card.copied{border-color:#059669;background:#ecfdf5}
.scrum-card .sc-header{padding:12px 16px;background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;display:flex;justify-content:space-between;align-items:center}
.scrum-card .sc-name{font-weight:700;font-size:.95em}
.scrum-card .sc-stats{display:flex;gap:8px;font-size:.7em}
.scrum-card .sc-stats span{padding:2px 8px;border-radius:10px}
.scrum-card .sc-body{padding:12px 16px;font-size:.82em;line-height:1.7;font-family:'Consolas','Menlo',monospace;white-space:pre-wrap;color:#334155;max-height:400px;overflow-y:auto}
.scrum-card .sc-task{padding-left:4px;margin-bottom:4px}
.scrum-card .sc-customer{color:#6366f1;font-weight:700;margin-top:8px;margin-bottom:4px}
.scrum-card .sc-g{color:#059669}.scrum-card .sc-y{color:#d97706}.scrum-card .sc-r{color:#dc2626}
.scrum-card .sc-eta-drift{display:block;padding-left:18px;font-size:.75em;color:#94a3b8;margin-top:-2px;margin-bottom:2px}
.scrum-card .sc-needs-response{display:inline-block;background:#f97316;color:#fff;font-size:.68em;font-weight:700;padding:1px 6px;border-radius:4px;margin-left:4px}
.scrum-card .sc-stale-collapse{color:#94a3b8;font-size:.82em;cursor:pointer;padding:2px 0 2px 8px;user-select:none}
.scrum-card .sc-stale-collapse:hover{color:#64748b}
.scrum-card .sc-copy-hint{text-align:center;padding:6px;font-size:.68em;color:var(--light);border-top:1px solid var(--gray-l)}
.team-report{background:linear-gradient(135deg,#1e1b4b,#312e81);border:2px solid #6366f1;border-radius:12px;overflow:hidden;margin-bottom:16px}
.team-report .tr-header{padding:14px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,.1)}
.team-report .tr-title{color:#fff;font-weight:800;font-size:1em;display:flex;align-items:center;gap:8px}
.team-report .tr-btn{background:#6366f1;color:#fff;border:none;padding:8px 20px;border-radius:8px;font-weight:700;font-size:.82em;cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:6px}
.team-report .tr-btn:hover{background:#818cf8;transform:translateY(-1px)}
.team-report .tr-btn.copied{background:#059669}
.team-report .tr-body{padding:16px 20px;font-size:.8em;line-height:1.7;font-family:'Consolas','Menlo',monospace;white-space:pre-wrap;color:#c7d2fe;max-height:600px;overflow-y:auto}
.team-report .tr-person-hdr{color:#a5b4fc;font-weight:800;font-size:1.05em;margin:12px 0 4px;padding:4px 0;border-bottom:1px solid rgba(165,180,252,.2)}
.team-report .tr-person-hdr:first-child{margin-top:0}
.team-report .tr-summary{padding:10px 20px;background:rgba(255,255,255,.05);border-top:1px solid rgba(255,255,255,.1);display:flex;gap:12px;flex-wrap:wrap;font-size:.75em;color:#a5b4fc}
.team-report .tr-summary span{padding:2px 10px;border-radius:8px;font-weight:600}
@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
/* ── Gantt chart styles (gt- prefix) ───────────── */
.gt-months{display:flex;position:sticky;top:0;z-index:21;background:var(--white);border-bottom:2px solid var(--border)}
.gt-months .gt-label-col{min-width:280px;max-width:280px;position:sticky;left:0;z-index:30;background:#0f172a;padding:6px 12px;display:flex;align-items:center;box-shadow:6px 0 12px rgba(0,0,0,.2)}
.gt-months .gt-label-col span{color:#94a3b8;font-size:.72em;font-weight:600}
.gt-month-cell{display:flex;align-items:center;justify-content:center;font-size:.72em;font-weight:700;color:#1e293b;background:#f8fafc;border-right:2px solid #94a3b8;padding:4px 0}
.gt-header{display:flex;position:sticky;top:28px;z-index:20;background:var(--white);border-bottom:1px solid var(--border)}
.gt-header .gt-label-col{min-width:280px;max-width:280px;position:sticky;left:0;z-index:28;background:#f1f5f9;padding:2px 12px;display:flex;align-items:center;box-shadow:6px 0 12px rgba(0,0,0,.1)}
.gt-header .gt-label-col span{color:#94a3b8;font-size:.6em}
.gt-days{display:flex}
.gt-day{min-width:6px;max-width:6px;text-align:center;font-size:.45em;color:#94a3b8;padding:1px 0;border-right:1px solid #f1f5f9}
.gt-day.gt-weekend{background:#f1f5f9;color:#cbd5e1}
.gt-day.gt-month-start{border-left:2px solid #cbd5e1}
.gt-day.gt-today-col{background:#fef2f2;color:#dc2626;font-weight:700}
.gt-row{display:flex;border-bottom:1px solid #e8ecf1;min-height:28px;align-items:stretch}
.gt-row:hover{background:#f8fafc}
.gt-label{min-width:280px;max-width:280px;position:sticky;left:0;z-index:15;background:var(--white);display:flex;align-items:center;padding:0 8px;border-right:2px solid #cbd5e1;box-shadow:6px 0 12px rgba(0,0,0,.1)}
.gt-row:hover .gt-label{background:#f8fafc}
.gt-group{background:#f8fafc;border-bottom:2px solid var(--border);cursor:pointer;user-select:none}
.gt-group:hover{background:#e2e8f0}
.gt-group .gt-label{background:#f8fafc;font-weight:700;font-size:.82em;gap:8px;box-shadow:6px 0 12px rgba(0,0,0,.1)}
.gt-group:hover .gt-label{background:#e2e8f0}
.gt-group .gt-arrow{font-size:.65em;color:#64748b;transition:transform .2s;width:14px;text-align:center}
.gt-group.gt-open .gt-arrow{transform:rotate(90deg)}
.gt-group .gt-count{font-size:.65em;color:#94a3b8;font-weight:400;margin-left:4px}
.gt-group .gt-badges{display:flex;gap:4px;margin-left:auto;margin-right:4px}
.gt-group .gt-badge{font-size:.6em;padding:1px 6px;border-radius:8px;font-weight:600}
.gt-task .gt-label{font-size:.72em;color:#475569;padding-left:28px;gap:6px}
.gt-task .gt-label a{color:var(--accent);text-decoration:none;font-weight:600;font-size:.95em}
.gt-task .gt-label a:hover{text-decoration:underline}
.gt-task .gt-label .gt-tname{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px}
.gt-task .gt-label .gt-person{font-size:.85em;color:#94a3b8;margin-left:auto;white-space:nowrap}
.gt-task.gt-hidden{display:none}
.gt-bars{display:flex;position:relative;flex:1;min-height:26px}
.gt-cell{min-width:6px;border-right:1px solid #f8fafc00}
.gt-cell.gt-weekend{background:#f8fafc}
.gt-cell.gt-month-start{border-left:1px solid var(--border)}
.gt-bar{position:absolute;top:4px;height:18px;border-radius:4px;min-width:4px;cursor:pointer;transition:filter .12s;z-index:2;box-shadow:0 1px 4px rgba(0,0,0,.12)}
.gt-bar:hover{filter:brightness(1.15);box-shadow:0 2px 8px rgba(0,0,0,.2)}
.gt-bar-done{background:linear-gradient(90deg,#059669,#34d399)}
.gt-bar-late{background:linear-gradient(90deg,#dc2626,#f87171)}
.gt-bar-active{background:linear-gradient(90deg,#2563eb,#60a5fa)}
.gt-bar-noeta{background:linear-gradient(90deg,#94a3b8,#cbd5e1)}
.gt-bar-blocked{background:linear-gradient(90deg,#d97706,#fbbf24)}
.gt-bar-projected{border:2px dashed #94a3b8;background:#94a3b815;top:6px;height:14px}
.gt-bar-summary{background:linear-gradient(90deg,#1e40af33,#3b82f633);border-radius:4px;top:5px;height:16px;border:1px solid #3b82f644}
.gt-today-marker{position:absolute;top:0;bottom:0;width:2px;background:#dc2626;z-index:3;pointer-events:none;opacity:.8}
.gt-month-line{position:absolute;top:0;bottom:0;width:1px;background:#94a3b8;z-index:1;pointer-events:none;opacity:.6}
/* ── Analytics tab styles (an- prefix) ────────── */
.an-section{background:var(--white);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:16px}
.an-section-hdr{padding:14px 20px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:8px;border-bottom:1px solid transparent;transition:all .15s;user-select:none}
.an-section-hdr:hover{background:var(--gray-bg)}
.an-section-hdr.open{border-bottom-color:var(--border)}
.an-section-hdr .toggle{font-size:.6em;transition:transform .2s;color:var(--dim)}
.an-section-hdr.open .toggle{transform:rotate(180deg)}
.an-section-body{padding:16px 20px;overflow-x:auto}
.an-stat-card{background:var(--gray-bg);border:1px solid var(--gray-l);border-radius:10px;padding:12px 18px;text-align:center;min-width:120px}
.an-stat-val{font-size:1.5em;font-weight:800;line-height:1.2}
.an-stat-label{font-size:.7em;color:var(--dim);margin-top:2px;font-weight:500}
.an-health-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.an-health-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:14px;transition:box-shadow .15s}
.an-health-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.08)}
.an-health-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.an-health-name{font-weight:700;font-size:.9em}
.an-health-arrow{font-size:1.4em;font-weight:800}
.an-health-current{font-size:1.8em;font-weight:800;color:var(--accent);margin-bottom:6px}
.an-spark{display:flex;align-items:flex-end;gap:3px;height:36px;margin-bottom:8px}
.an-spark-bar{width:100%;border-radius:2px;min-width:4px;transition:height .3s}
.an-health-meta{margin-bottom:4px}
.an-health-tag{font-size:.72em;font-weight:700;padding:2px 10px;border-radius:10px;display:inline-block}
.an-copy-btn,.an-export-btn{background:linear-gradient(135deg,#1e293b,#334155);color:#fff;border:1px solid #475569;border-radius:8px;padding:8px 18px;font-size:.82em;font-weight:600;cursor:pointer;transition:all .15s;display:inline-flex;align-items:center;gap:8px}
.an-copy-btn:hover,.an-export-btn:hover{background:linear-gradient(135deg,#0f172a,#1e293b);box-shadow:0 2px 8px rgba(0,0,0,.2)}
.an-export-btn{min-width:200px;text-align:left}
@media(max-width:900px){.top-strip{flex-direction:column}.strip-group{flex-direction:row;flex-wrap:wrap}.heatmap{font-size:.7em}.audit-table{font-size:.65em}.an-health-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>KPI Dashboard</h1>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <a href="https://linear.app/testbox/team/RAC/projects" target="_blank" class="linear-link"><svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M2.886 4.18A11.982 11.982 0 0 1 11.99 0C18.624 0 24 5.376 24 12.009c0 3.64-1.62 6.903-4.18 9.105L2.887 4.18ZM1.817 5.626l16.556 16.556c-.524.33-1.075.62-1.65.866L.951 7.277c.247-.575.537-1.126.866-1.65ZM.322 9.163l14.515 14.515c-.71.172-1.443.282-2.195.322L0 11.358a12 12 0 0 1 .322-2.195Zm-.17 4.862 9.823 9.824a12.02 12.02 0 0 1-9.824-9.824Z"/></svg>View in Linear</a>
      <a href="javascript:void(0)" onclick="showGuide()" class="linear-link" style="background:linear-gradient(135deg,#1e293b,#334155);border-color:#475569"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Guide</a>
    </div>
  </div>
  <img src="https://cdn.prod.website-files.com/62f1899cd374937577f36d5f/6529d8cb022a253f2009f59a_testbox.svg" alt="TestBox" class="tbx-logo">
  <div class="filters">
    <label>Month</label><select id="fMonth" style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;padding:5px 10px;border-radius:6px;font-size:.82em;cursor:pointer"><option value="ALL">All</option></select>
    <label>Person</label><select id="fPerson"><option value="ALL">All</option></select>
    <select id="fCategory" style="display:none"><option value="ALL">All</option><option value="Internal">Internal</option><option value="External">External</option></select>
    <button id="btnRefresh" onclick="refreshDashboard()" style="margin-left:12px;background:linear-gradient(135deg,#1e40af,#2563eb);border:1px solid #3b82f6;color:#fff;padding:6px 14px;border-radius:6px;font-size:.78em;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:all .15s;letter-spacing:.3px" onmouseover="this.style.background='linear-gradient(135deg,#1e3a8a,#1d4ed8)'" onmouseout="this.style.background='linear-gradient(135deg,#1e40af,#2563eb)'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>Refresh Data</button>
    <span id="refreshDate" style="font-size:.72em;font-style:italic;color:#a7f3d0;margin-left:6px"></span>
  </div>
</div>

<div id="stalenessBanner"></div>

<div class="top-strip" id="topStrip">
  <div class="strip-group filters-group">
    <button class="segment-btn" data-seg="ALL" style="display:none">All<span class="seg-count" id="segAll"></span></button>
    <button class="segment-btn" data-seg="Internal" style="display:none">Internal<span class="seg-count" id="segInt"></span></button>
    <button class="segment-btn active" data-seg="External">External<span class="seg-count" id="segExt"></span></button>
  </div>
  <div class="strip-group kpi-group">
    <div class="kpi-cell kpi-active" id="kpiCell1" data-tab="accuracy"></div>
    <div class="kpi-cell" id="kpiCell2" data-tab="velocity"></div>
    <div class="kpi-cell" id="kpiCell3" data-tab="reliability"></div>
    <div class="kpi-cell" id="kpiCell4" data-tab="activity"></div>
  </div>
</div>

<div class="member-cards" id="memberCards"></div>

<div class="tabs" id="tabBar">
  <div class="tab active" data-tab="accuracy">ETA Accuracy</div>
  <div class="tab" data-tab="implementation">Customer Onboarding</div>
  <div class="tab" data-tab="reliability">Implementation Reliability</div>
  <div class="tab" data-tab="velocity">Execution Time</div>
  <div class="tab" data-tab="activity">Team Activity</div>
  <div class="tab" data-tab="scrum">Scrum Panel</div>
  <div class="tab" data-tab="insights">Insights</div>
  <div class="tab" data-tab="gantt">Gantt</div>
  <div class="tab" data-tab="analytics">Analytics</div>
</div>

<div class="tab-panel active" id="panel-accuracy">
  <div class="audit-section" style="margin-top:0">
    <div class="audit-header collapse-toggle">
      <span class="toggle">&#9660;</span>
      <h3><span class="dot" style="background:var(--blue);position:relative;top:0"></span>ETA Accuracy<span class="info-btn" onmouseenter="showTip(event,'<b>ETA Accuracy</b><br><span class=tip-label>Formula</span>: On Time / (On Time + Late)<br><span class=tip-label>Target</span>: &gt;90%<br><span class=tip-label>Late</span>: Past ETA — delivered after deadline or not delivered yet<br><span class=tip-label>Not Started</span>: Backlog/Todo/Triage — ETA not applicable<br><span class=tip-label>Excludes</span>: No ETA, Not Started, On Track, Blocked, N/A')" onmouseleave="hideTip()" onclick="event.stopPropagation()">?</span></h3>
    </div>
    <div class="audit-body">
      <div class="trend-wrap" id="trend-accuracy"></div>
      <div style="overflow-x:auto"><table class="heatmap" id="grid-accuracy"></table></div>
    </div>
  </div>
</div>

<div class="tab-panel" id="panel-velocity">
  <div class="audit-section" style="margin-top:0">
    <div class="audit-header collapse-toggle">
      <span class="toggle">&#9660;</span>
      <h3><span class="dot" style="background:var(--yellow);position:relative;top:0"></span>Execution Time<span class="info-btn" onmouseenter="showTip(event,'<b>Avg Execution Time</b><br><span class=tip-label>Formula</span>: Average(Delivery - Start Date)<br><span class=tip-label>Start Date</span>: startedAt (In Progress) or dateAdd as fallback<br><span class=tip-label>Target</span>: &lt;28 days<br><span class=tip-label>Includes</span>: Only Done tasks with both dates<br><br>Measures implementation speed. Lower = faster delivery.')" onmouseleave="hideTip()" onclick="event.stopPropagation()">?</span></h3>
    </div>
    <div class="audit-body">
      <div class="trend-wrap" id="trend-velocity"></div>
      <div style="overflow-x:auto"><table class="heatmap" id="grid-velocity"></table></div>
    </div>
  </div>
</div>

<div class="tab-panel" id="panel-reliability">
  <div class="audit-section" style="margin-top:0">
    <div class="audit-header collapse-toggle">
      <span class="toggle">&#9660;</span>
      <h3><span class="dot" style="background:var(--green);position:relative;top:0"></span>Implementation Reliability <span class="info-btn" onmouseenter="showTip(event,'<b>Implementation Reliability</b><br><span class=tip-label>Formula</span>: Done without Rework / Total Done<br><span class=tip-label>Target</span>: &gt;90%<br><span class=tip-label>Rework</span>: Flagged via rework:implementation label in Linear')" onmouseleave="hideTip()" onclick="event.stopPropagation()">?</span></h3>
    </div>
    <div class="audit-body">
      <div class="trend-wrap" id="trend-reliability"></div>
      <div style="overflow-x:auto"><table class="heatmap" id="grid-reliability"></table></div>
      <div style="margin-top:16px;padding:0 20px">
        <div style="font-weight:700;font-size:.9em;margin-bottom:8px"><span class="dot" style="background:var(--red);position:relative;top:0"></span>Rework Log</div>
        <div id="reworkLog"></div>
      </div>
    </div>
  </div>
</div>

<div class="tab-panel" id="panel-activity">
  <div class="audit-section" style="margin-top:0">
    <div class="audit-header collapse-toggle">
      <span class="toggle">&#9660;</span>
      <h3><span class="dot" style="background:var(--accent);position:relative;top:0"></span>Team Activity<span class="info-btn" onmouseenter="showTip(event,'<b>Task Volume</b><br><span class=tip-label>Shows</span>: Number of tasks per person per week<br><span class=tip-label>Includes</span>: All tasks regardless of status<br><span class=tip-label>Color</span>: Darker = more tasks')" onmouseleave="hideTip()" onclick="event.stopPropagation()">?</span></h3>
    </div>
    <div class="audit-body">
      <div class="trend-wrap" id="trend-activity"></div>
      <div style="overflow-x:auto"><table class="heatmap" id="grid-activity"></table></div>
    </div>
  </div>
</div>

<div class="tab-panel" id="panel-scrum">
  <div class="audit-section" style="margin-top:0">
    <div class="audit-header collapse-toggle">
      <span class="toggle">&#9660;</span>
      <h3><span class="dot" style="background:#8b5cf6;position:relative;top:0"></span>Scrum Panel<span style="font-size:.72em;color:var(--dim);font-weight:400;margin-left:8px">Click any card to copy to clipboard</span></h3>
    </div>
    <div class="audit-body">
      <div id="teamReport" style="padding:16px 20px"></div>
      <div id="scrumCards" style="padding:16px 20px;display:grid;grid-template-columns:repeat(2,1fr);gap:12px"></div>
    </div>
  </div>
</div>

<div class="tab-panel" id="panel-gantt">
  <div style="background:var(--white);border:1px solid var(--border);border-radius:10px;margin-top:0">
    <div class="audit-header collapse-toggle" style="cursor:pointer" id="ganttCollapseHdr">
      <span class="toggle">&#9660;</span>
      <h3><span class="dot" style="background:#0ea5e9;position:relative;top:0"></span>Gantt Chart <span style="font-size:.6em;background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-weight:700">WIP</span></h3>
    </div>
    <div id="ganttCollapseBody" style="display:none">
      <div id="ganttControls" style="padding:10px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <label style="font-size:.72em;color:var(--dim);font-weight:600">Person</label>
        <select id="gtPerson" style="padding:5px 10px;border:1px solid var(--border);border-radius:6px;font-size:.78em;background:var(--white);cursor:pointer">
          <option value="ALL">All People</option>
        </select>
        <label style="font-size:.72em;color:var(--dim);font-weight:600">View</label>
        <select id="gtView" style="padding:5px 10px;border:1px solid var(--border);border-radius:6px;font-size:.78em;background:var(--white);cursor:pointer">
          <option value="ALL">All Tasks</option>
          <option value="implementing">Active Implementations</option>
        </select>
        <label style="font-size:.72em;color:var(--dim);font-weight:600">Customer</label>
        <select id="gtCustomer" style="padding:5px 10px;border:1px solid var(--border);border-radius:6px;font-size:.78em;background:var(--white);cursor:pointer">
          <option value="ALL">All Customers</option>
        </select>
        <label style="font-size:.72em;color:var(--dim);font-weight:600">Demand</label>
        <select id="gtDemand" style="padding:5px 10px;border:1px solid var(--border);border-radius:6px;font-size:.78em;background:var(--white);cursor:pointer">
          <option value="ALL">All</option>
          <option value="External">External</option>
          <option value="Internal">Internal</option>
        </select>
        <label style="font-size:.72em;color:var(--dim);font-weight:600">Status</label>
        <select id="gtStatus" style="padding:5px 10px;border:1px solid var(--border);border-radius:6px;font-size:.78em;background:var(--white);cursor:pointer">
          <option value="ALL">All</option>
          <option value="active">Active Only</option>
        </select>
        <label style="font-size:.72em;color:var(--dim);font-weight:600">Period</label>
        <select id="gtPeriod" style="padding:5px 10px;border:1px solid var(--border);border-radius:6px;font-size:.78em;background:var(--white);cursor:pointer">
          <option value="3m">Last 3 Months</option>
          <option value="1m">Last Month</option>
          <option value="6m" selected>Last 6 Months</option>
          <option value="all">All Time</option>
        </select>
        <span id="gtStats" style="font-size:.72em;color:var(--dim);margin-left:auto"></span>
      </div>
      <div id="ganttWrap" style="overflow:auto;max-height:600px;position:relative">
        <div id="ganttCanvas"></div>
      </div>
      <div id="ganttLegend" style="padding:8px 20px;display:flex;gap:14px;font-size:.7em;color:#64748b;flex-wrap:wrap">
        <span style="display:flex;align-items:center;gap:4px"><i style="display:inline-block;width:14px;height:10px;border-radius:2px;background:linear-gradient(90deg,#059669,#34d399)"></i> On Time</span>
        <span style="display:flex;align-items:center;gap:4px"><i style="display:inline-block;width:14px;height:10px;border-radius:2px;background:linear-gradient(90deg,#dc2626,#f87171)"></i> Late</span>
        <span style="display:flex;align-items:center;gap:4px"><i style="display:inline-block;width:14px;height:10px;border-radius:2px;background:linear-gradient(90deg,#2563eb,#60a5fa)"></i> Active</span>
        <span style="display:flex;align-items:center;gap:4px"><i style="display:inline-block;width:14px;height:10px;border-radius:2px;background:linear-gradient(90deg,#d97706,#fbbf24)"></i> Blocked</span>
        <span style="display:flex;align-items:center;gap:4px"><i style="display:inline-block;width:14px;height:10px;border-radius:2px;background:linear-gradient(90deg,#94a3b8,#cbd5e1)"></i> No ETA</span>
        <span style="display:flex;align-items:center;gap:4px"><i style="display:inline-block;width:14px;height:10px;border-radius:2px;border:2px dashed #94a3b8;background:#94a3b822"></i> Projected</span>
        <span style="color:#dc2626;font-weight:700">| Today</span>
      </div>
    </div>
  </div>
</div>

<div class="tab-panel" id="panel-insights">
  <div style="background:var(--white);border:1px solid var(--border);border-radius:10px;margin-top:0">
    <div class="audit-header" style="cursor:default">
      <h3><span class="dot" style="background:#8b5cf6;position:relative;top:0"></span>Insights <span style="font-size:.6em;background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-weight:700">WIP</span></h3>
    </div>
    <div id="insightsBody" style="padding:16px 20px"></div>
  </div>
</div>

<div class="tab-panel" id="panel-implementation">
  <div style="background:var(--white);border:1px solid var(--border);border-radius:10px;margin-top:0">
    <div class="audit-header" style="cursor:default">
      <h3 style="font-weight:800"><span class="dot" style="background:#059669;position:relative;top:0"></span>Customer Onboarding</h3>
    </div>
    <div id="implementationBody" style="padding:16px 20px"></div>
  </div>
</div>

<div class="tab-panel" id="panel-analytics">
  <div style="background:var(--white);border:1px solid var(--border);border-radius:10px;margin-top:0;padding:0">
    <div style="padding:14px 20px;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--border)">
      <h3 style="font-weight:800;font-size:.95em"><span class="dot" style="background:#f59e0b;position:relative;top:0"></span>Analytics</h3>
      <span style="font-size:.72em;color:var(--dim)">Adjust parameters below — numbers update live</span>
    </div>
    <div style="padding:16px 20px;display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;background:#fefce8;border-bottom:1px solid #fde68a">
      <div style="display:flex;flex-direction:column;gap:4px">
        <label style="font-size:.68em;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Retroactive ETA = ?</label>
        <select id="anRetroMode" style="padding:6px 10px;border:1px solid #fde68a;border-radius:6px;font-size:.82em;background:#fff;cursor:pointer;font-weight:600" onchange="renderAnalytics()">
          <option value="any">Any ETA change</option>
          <option value="post-delivery">Only post-delivery changes</option>
          <option value="multi">2+ ETA changes only</option>
        </select>
        <span style="font-size:.62em;color:#a16207">Defines what counts as "retroactive" for Organic Accuracy</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <label style="font-size:.68em;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Trend Window</label>
        <select id="anTrendWindow" style="padding:6px 10px;border:1px solid #fde68a;border-radius:6px;font-size:.82em;background:#fff;cursor:pointer;font-weight:600" onchange="renderAnalytics()">
          <option value="4">Last 4 weeks</option>
          <option value="6">Last 6 weeks</option>
          <option value="8" selected>Last 8 weeks</option>
          <option value="12">Last 12 weeks</option>
        </select>
        <span style="font-size:.62em;color:#a16207">How many weeks of history for regression analysis</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <label style="font-size:.68em;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Trend Sensitivity</label>
        <select id="anSlopeThreshold" style="padding:6px 10px;border:1px solid #fde68a;border-radius:6px;font-size:.82em;background:#fff;cursor:pointer;font-weight:600" onchange="renderAnalytics()">
          <option value="0.02">Sensitive (&plusmn;2%/wk)</option>
          <option value="0.05" selected>Normal (&plusmn;5%/wk)</option>
          <option value="0.10">Relaxed (&plusmn;10%/wk)</option>
        </select>
        <span style="font-size:.62em;color:#a16207">Threshold to classify improving vs declining</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <label style="font-size:.68em;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Streak Alert</label>
        <select id="anStreakWeeks" style="padding:6px 10px;border:1px solid #fde68a;border-radius:6px;font-size:.82em;background:#fff;cursor:pointer;font-weight:600" onchange="renderAnalytics()">
          <option value="2" selected>2+ weeks &lt;50%</option>
          <option value="3">3+ weeks &lt;50%</option>
          <option value="2_40">2+ weeks &lt;40%</option>
          <option value="3_40">3+ weeks &lt;40%</option>
        </select>
        <span style="font-size:.62em;color:#a16207">When to flag a person for sustained low accuracy</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <label style="font-size:.68em;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Export Format</label>
        <select id="anExportFmt" style="padding:6px 10px;border:1px solid #fde68a;border-radius:6px;font-size:.82em;background:#fff;cursor:pointer;font-weight:600">
          <option value="markdown" selected>Markdown (Slack/GitHub)</option>
          <option value="slack-block">Slack Block Kit JSON</option>
        </select>
        <span style="font-size:.62em;color:#a16207">Output format for copy buttons</span>
      </div>
    </div>
  </div>
  <div id="analyticsBody" style="margin-top:16px"></div>
</div>

<div class="tooltip" id="tooltip"></div>

<div class="audit-section" id="customerKPISection" style="margin-top:20px">
  <div class="audit-header" id="customerKPIToggle">
    <span class="toggle">&#9660;</span>
    <h3><span id="customerKPITitle">KPI by Customer</span><span class="info-btn" id="clientKpiInfo" onclick="event.stopPropagation()">?</span></h3>
  </div>
  <div class="audit-body" id="customerKPIBody">
    <div style="overflow-x:auto"><table class="heatmap" id="customerKPITable"></table></div>
  </div>
</div>

<div class="audit-section" id="auditSection">
  <div class="audit-header" id="auditToggle">
    <span class="toggle">&#9660;</span>
    <h3>Audit Data Table</h3>
    <div style="display:flex;align-items:center;gap:12px;margin-left:auto">
      <div style="display:flex;gap:6px;align-items:center" onclick="event.stopPropagation()">
        <select id="auditFilterPerson" style="background:var(--gray-bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:.72em;font-weight:600;color:var(--dim);cursor:pointer" onchange="renderAuditTable()">
          <option value="ALL">All People</option>
        </select>
        <select id="auditFilterWorkStatus" style="background:var(--gray-bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:.72em;font-weight:600;color:var(--dim);cursor:pointer" onchange="renderAuditTable()">
          <option value="ALL">All Status</option>
        </select>
        <select id="auditFilterPerf" style="background:var(--gray-bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:.72em;font-weight:600;color:var(--dim);cursor:pointer" onchange="renderAuditTable()">
          <option value="ALL">All Performance</option>
          <option value="On Time">On Time</option>
          <option value="Late">Late</option>
          <option value="On Track">On Track</option>
          <option value="No ETA">No ETA</option>
          <option value="Blocked">Blocked</option>
          <option value="N/A">N/A</option>
          <option value="Not Started">Not Started</option>
          <option value="On Hold">On Hold</option>
        </select>
        <select id="auditFilterCustomer" style="background:var(--gray-bg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:.72em;font-weight:600;color:var(--dim);cursor:pointer" onchange="renderAuditTable()">
          <option value="ALL">All Customers</option>
        </select>
      </div>
      <div class="audit-tools">
        <button onclick="event.stopPropagation();downloadXLSX()">&#8681; XLSX</button>
        <button onclick="event.stopPropagation();copyTSV()">&#128203; Copy</button>
      </div>
    </div>
  </div>
  <div class="audit-body" id="auditBody">
    <table class="audit-table" id="auditTable"></table>
    <div class="audit-stats" id="auditStats"></div>
  </div>
</div>


<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/gitbrent/PptxGenJS@3.12.0/dist/pptxgen.bundle.js"></script>
<script>
const RAW = __DATA__;
const TIMELINE = __TIMELINE__;
const BUILD_DATE = '__DATE__';
const LATEST_DATA = '__LATEST_DATA__';
const API_REFRESH = '__API_REFRESH__';

/* ── Helpers ─────────────────────────────────────────── */
function parseWeek(w){const m=w.match(/(\d{2})-(\d{2})\s+W\.(\d+)/);return m?[+m[1],+m[2],+m[3]]:[99,99,99]}
function weekSort(a,b){const[y1,m1,w1]=parseWeek(a),[y2,m2,w2]=parseWeek(b);return y1-y2||m1-m2||w1-w2}
function daysBetween(a,b){if(!a||!b)return null;const d1=new Date(a),d2=new Date(b);if(isNaN(d1)||isNaN(d2))return null;return Math.round((d2-d1)/864e5)}
const MONTH_NAMES=['','JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
function monthLabel(y,m){return(MONTH_NAMES[m]||'?')+' - '+(y<50?'20'+y:'19'+y)}
function fmtWeekPretty(w){const[y,m,wn]=parseWeek(w);if(y===99)return w;return(MONTH_NAMES[m]||'?')+' - '+(y<50?'20'+y:'19'+y)+' W'+wn}

/* H1: Dynamic core period — rolling 4 months from latest data, never includes future weeks */
function isCoreWeek(w){
  const[y,m,wn]=parseWeek(w);
  if(y===99)return false;
  const wy=y<50?2000+y:1900+y;
  const wDate=new Date(wy,m-1,(wn-1)*7+1);
  const today=new Date();
  /* Do not include weeks in the future */
  if(wDate>today)return false;
  /* Rolling 4 months back from today */
  const cutoff=new Date(today.getFullYear(),today.getMonth()-4,1);
  return wDate>=cutoff;
}
const CORE_WEEKS=[...new Set(RAW.map(r=>r.week).filter(w=>w&&isCoreWeek(w)))].sort(weekSort);
const PEOPLE_ALL=[...new Set(RAW.map(r=>r.tsa))].sort();

/* Compute period label for staleness banner */
let PERIOD_LABEL='';
if(CORE_WEEKS.length>0){
  const first=CORE_WEEKS[0],last=CORE_WEEKS[CORE_WEEKS.length-1];
  const[fy,fm]=parseWeek(first),[ly,lm]=parseWeek(last);
  PERIOD_LABEL=monthLabel(fy,fm)+' — '+monthLabel(ly,lm);
}

/* Group weeks by month */
function groupByMonth(weeks){
  const months=[];const seen=new Set();
  weeks.forEach(w=>{
    const[y,m]=parseWeek(w);const key=y+'-'+m;
    if(!seen.has(key)){seen.add(key);months.push({y,m,label:monthLabel(y,m),weeks:[]})}
    months.find(mo=>mo.y===y&&mo.m===m).weeks.push(w);
  });
  return months;
}
const MONTHS=groupByMonth(CORE_WEEKS);

/* M11+A37: Staleness indicator — shows API cache mtime, not build date */
(function(){
  const el=document.getElementById('refreshDate');
  const banner=document.getElementById('stalenessBanner');
  if(banner)banner.style.display='none';
  const refreshLabel=API_REFRESH!=='unknown'?API_REFRESH:BUILD_DATE;
  if(el)el.textContent='Data refreshed: '+refreshLabel+' | Built: '+BUILD_DATE;
})();

/* ── State — M12: default to ALL ──────────────────── */
let state={person:'ALL',category:'ALL',month:'ALL'};
const charts={};

function getFiltered(){
  return RAW.filter(r=>{
    if(r.source==='spreadsheet')return false;
    if(!r.week||!isCoreWeek(r.week))return false;
    if(state.person!=='ALL'&&r.tsa!==state.person)return false;
    if(state.category!=='ALL'&&r.category!==state.category)return false;
    if(state.month!=='ALL'){
      const[y,m]=parseWeek(r.week);
      if(monthLabel(y,m)!==state.month)return false;
    }
    return true;
  });
}
function getKPIFiltered(){
  return RAW.filter(r=>{
    if(r.source==='spreadsheet')return false;
    if(r.category!=='External')return false;
    if(!r.week||!isCoreWeek(r.week))return false;
    if(state.person!=='ALL'&&r.tsa!==state.person)return false;
    if(state.month!=='ALL'){
      const[y,m]=parseWeek(r.week);
      if(monthLabel(y,m)!==state.month)return false;
    }
    return true;
  });
}
function getPeople(){
  if(state.person!=='ALL')return[state.person];
  return PEOPLE_ALL;
}

/* ── Tooltip ────────────────────────────────────────── */
const tip=document.getElementById('tooltip');
function showTip(e,html){
  tip.innerHTML=html;tip.style.display='block';
  const rect=tip.getBoundingClientRect();
  const x=Math.min(e.clientX+14,window.innerWidth-rect.width-20);
  const y=Math.min(e.clientY-10,window.innerHeight-rect.height-20);
  tip.style.left=x+'px';tip.style.top=Math.max(10,y)+'px';
}
function hideTip(){tip.style.display='none'}

function refreshDashboard(){
  const btn=document.getElementById('btnRefresh');
  const orig=btn.innerHTML;
  const pw=prompt('Password required to refresh data:');
  if(pw===null||pw==='') return;
  const headers={'X-Refresh-Password':pw};
  const showWrongPw=()=>{
    btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>Wrong password';
    btn.style.background='linear-gradient(135deg,#991b1b,#dc2626)';btn.style.opacity='1';
    setTimeout(()=>{btn.innerHTML=orig;btn.style.background='linear-gradient(135deg,#1e40af,#2563eb)';btn.disabled=false},3000);
  };
  btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13" style="animation:spin 1s linear infinite"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>Refreshing...';
  btn.disabled=true;btn.style.opacity='.7';
  fetch('/refresh',{method:'POST',headers}).then(r=>{
    if(r.status===401){showWrongPw();return null;}
    return r.json();
  }).then(d=>{
    if(d===null) return;
    if(d.success){
      btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><polyline points="20 6 9 17 4 12"/></svg>Done!';
      btn.style.background='linear-gradient(135deg,#065f46,#059669)';btn.style.opacity='1';
      setTimeout(()=>location.reload(),800);
    } else {
      btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>Error';
      btn.style.background='linear-gradient(135deg,#991b1b,#dc2626)';btn.style.opacity='1';
      setTimeout(()=>{btn.innerHTML=orig;btn.style.background='linear-gradient(135deg,#1e40af,#2563eb)';btn.disabled=false},3000);
    }
  }).catch(()=>{
    /* Server not running — try localhost:8787 in case file:// was opened directly */
    fetch('http://localhost:8787/refresh',{method:'POST',headers}).then(r=>{
      if(r.status===401){showWrongPw();return null;}
      return r.json();
    }).then(d=>{
      if(d===null) return;
      if(d.success){
        btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><polyline points="20 6 9 17 4 12"/></svg>Done! Redirecting...';
        btn.style.background='linear-gradient(135deg,#065f46,#059669)';btn.style.opacity='1';
        setTimeout(()=>{window.location.href='http://localhost:8787'},800);
      } else {
        btn.innerHTML='Error';btn.style.background='linear-gradient(135deg,#991b1b,#dc2626)';btn.style.opacity='1';
        setTimeout(()=>{btn.innerHTML=orig;btn.style.background='linear-gradient(135deg,#1e40af,#2563eb)';btn.disabled=false},3000);
      }
    }).catch(()=>{
      btn.style.opacity='1';btn.disabled=false;
      btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>Server offline';
      btn.style.background='linear-gradient(135deg,#991b1b,#dc2626)';
      navigator.clipboard.writeText('python kpi/serve_kpi.py');
      setTimeout(()=>{btn.innerHTML=orig+' <span style="font-size:.7em;opacity:.8">(start server first)</span>';btn.style.background='linear-gradient(135deg,#1e40af,#2563eb)'},2500);
    });
  });
}

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;').replace(/"/g,'&quot;').replace(/`/g,'&#96;')}

/* ── KPI Calculations ──────────────────────────────── */
function calcAccuracy(rows){
  const ot=rows.filter(r=>r.perf==='On Time').length;
  const lt=rows.filter(r=>r.perf==='Late').length;
  const d=ot+lt; /* H2: On Time / (On Time + Late) — no Overdue concept, past ETA = Late */
  /* Organic accuracy: exclude retroactive ETAs (set after delivery) */
  const orgOt=rows.filter(r=>r.perf==='On Time'&&r.retroactiveEta!=='yes').length;
  const orgLt=rows.filter(r=>r.perf==='Late'&&r.retroactiveEta!=='yes').length;
  const orgD=orgOt+orgLt;
  return{val:d>0?ot/d:null,num:ot,den:d,n:rows.length,late:lt,orgVal:orgD>0?orgOt/orgD:null,orgNum:orgOt,orgDen:orgD};
}
function calcVelocity(rows){
  const durs=rows.filter(r=>r.delivery&&(r.startedAt||r.dateAdd)&&r.status==='Done').map(r=>daysBetween(r.startedAt||r.dateAdd,r.delivery)).filter(d=>d!==null&&d>=0);
  const avg=durs.length>0?durs.reduce((a,b)=>a+b,0)/durs.length:null;
  return{val:avg,n:durs.length,durs};
}
function calcReliability(rows){
  const done=rows.filter(r=>r.status==='Done');
  const total=done.length;
  const reworked=done.filter(r=>r.rework==='yes').length;
  const clean=total-reworked;
  return{val:total>0?clean/total:null,num:clean,den:total,n:rows.length,reworked:reworked};
}

/* Heat classes */
function heatPct(val){
  if(val===null||val===undefined||isNaN(val))return'heat-na';
  if(val>=.9)return'heat-great';if(val>=.75)return'heat-good';
  if(val>=.6)return'heat-ok';if(val>=.4)return'heat-bad';return'heat-terrible';
}
function heatDays(val){
  if(val===null||val===undefined||isNaN(val))return'heat-na';
  if(val<=14)return'heat-great';if(val<=28)return'heat-good';
  if(val<=42)return'heat-ok';if(val<=60)return'heat-bad';return'heat-terrible';
}

/* M15: Format with sample size threshold */
function fmtPct(v,n){
  if(v===null||v===undefined) return '—';
  if(n!==undefined && n===0) return '—';
  return (v*100).toFixed(0)+'%';
}
function fmtDays(v){return(v===null||v===undefined||isNaN(v))?'—':v.toFixed(0)+'d'}

/* ── Tooltip cache ────────────────────────────────── */
const tipCache={};
let tipCounter=0;

/* ── Build heatmap grid ─────────────────────────────── */
function buildGrid(tableId, calcFn, fmtFn, heatFn, tipFn){
  const table=document.getElementById(tableId);
  const data=getKPIFiltered();
  const people=getPeople();
  const months=MONTHS;

  let h1='<tr><th rowspan="2" style="text-align:left;min-width:120px;border-right:2px solid var(--border);background:var(--white);font-size:.72em;color:var(--light);font-weight:500;letter-spacing:.5px;padding-left:16px;position:sticky;left:0;z-index:3">TEAM</th>';
  months.forEach(mo=>{h1+=`<th class="month-header" colspan="${mo.weeks.length}">${mo.label}</th>`});
  h1+='<th class="month-header" rowspan="2" style="border-left:3px solid var(--accent);font-size:.78em;line-height:1.2">OVERALL<br><span style="font-weight:400;font-size:.8em;color:var(--dim)">all weeks</span></th></tr>';

  let h2='<tr>';
  months.forEach(mo=>{
    mo.weeks.forEach((w,i)=>{
      const[,,wn]=parseWeek(w);
      const first=i===0?'border-left:3px solid var(--accent);':'';
      h2+=`<th class="week-header" style="${first}">W${wn}</th>`;
    });
  });
  h2+='</tr>';

  function cell(cls,txt,tipHtml,isFirstOfMonth){
    const id='t'+(tipCounter++);
    tipCache[id]=tipHtml;
    const mf=isFirstOfMonth?' month-first':'';
    return`<td class="cell ${cls}${mf}" data-tip="${id}">${txt}</td>`;
  }

  let bodyRows='';
  people.forEach(person=>{
    let row=`<tr><td class="person-label">${person}</td>`;
    months.forEach(mo=>{
      mo.weeks.forEach((w,i)=>{
        const rows=data.filter(r=>r.tsa===person&&r.week===w);
        const calc=calcFn(rows);
        const v=calc.val;
        const cls=rows.length===0?'heat-na':heatFn(v);
        /* M15: pass sample size for threshold */
        const txt=rows.length===0?'—':fmtFn(v,calc.den!==undefined?calc.den:calc.n);
        row+=cell(cls,txt,tipFn(person,w,calc,rows),i===0);
      });
    });
    const totalRows=data.filter(r=>r.tsa===person);
    const totalCalc=calcFn(totalRows);
    const totalCls=totalRows.length===0?'heat-na':heatFn(totalCalc.val);
    row+=`<td class="cell total-col ${totalCls}">${totalRows.length===0?'—':fmtFn(totalCalc.val,totalCalc.den!==undefined?totalCalc.den:totalCalc.n)}</td>`;
    row+='</tr>';
    bodyRows+=row;
  });

  let teamRow='<tr class="team-row"><td class="person-label">OVERALL<br><span style="font-weight:400;font-size:.75em;color:var(--dim)">all members</span></td>';
  months.forEach(mo=>{
    mo.weeks.forEach((w,i)=>{
      const rows=data.filter(r=>r.week===w);
      const calc=calcFn(rows);
      const cls=rows.length===0?'heat-na':heatFn(calc.val);
      teamRow+=cell(cls,rows.length===0?'—':fmtFn(calc.val,calc.den!==undefined?calc.den:calc.n),tipFn('TEAM',w,calc,rows),i===0);
    });
  });
  const allRows=data;
  const allCalc=calcFn(allRows);
  const allCls=allRows.length===0?'heat-na':heatFn(allCalc.val);
  teamRow+=`<td class="cell total-col ${allCls}">${allRows.length===0?'—':fmtFn(allCalc.val,allCalc.den!==undefined?allCalc.den:allCalc.n)}</td></tr>`;

  /* Replace table node to clear old event listeners */
  const fresh=table.cloneNode(false);
  table.parentNode.replaceChild(fresh,table);
  fresh.innerHTML=`<thead>${h1}${h2}</thead><tbody>${bodyRows}${teamRow}</tbody>`;

  fresh.addEventListener('mouseenter',function(e){
    const td=e.target.closest('td[data-tip]');
    if(td){const html=tipCache[td.dataset.tip];if(html)showTip(e,html)}
  },true);
  fresh.addEventListener('mouseleave',function(e){
    const td=e.target.closest('td[data-tip]');
    if(td)hideTip();
  },true);
  fresh.addEventListener('mousemove',function(e){
    const td=e.target.closest('td[data-tip]');
    if(td&&tip.style.display==='block'){
      const x=Math.min(e.clientX+14,window.innerWidth-tip.offsetWidth-20);
      const y=Math.min(e.clientY-10,window.innerHeight-tip.offsetHeight-20);
      tip.style.left=x+'px';tip.style.top=Math.max(10,y)+'px';
    }
  },true);
}

/* ── Tip helpers ───────────────────────────────────── */
function fmtDate(d){if(!d||d.length<10)return'';const p=d.slice(0,10).split('-');return p[2]+'/'+p[1]}
function tipAccuracy(person,week,calc,rows){
  if(rows.length===0)return`<div class="tip-hdr"><b>${person}</b><span style="color:#64748b">${fmtWeekPretty(week)}</span></div><span class="tip-label">No tasks this week</span>`;
  const pctCls=calc.val===null?'mid':calc.val>=.85?'good':calc.val>=.5?'mid':'bad';
  let html=`<div class="tip-hdr"><b>${person} &middot; ${fmtWeekPretty(week)}</b><span class="tip-pct ${pctCls}">${fmtPct(calc.val,calc.den)}</span></div>`;
  html+=`<div class="tip-stats">`;
  html+=`<div class="tip-stat"><b style="color:#34d399">${calc.num}</b><span>on time</span></div>`;
  html+=`<div class="tip-stat"><b style="color:#f87171">${calc.late||0}</b><span>late</span></div>`;
  html+=`<div class="tip-stat"><b>${calc.den}</b><span>measured</span></div>`;
  html+=`</div>`;
  /* ETA Quality summary for measured tickets */
  const measured=rows.filter(r=>r.perf==='On Time'||r.perf==='Late');
  if(measured.length>0){
    const etaChanged=measured.filter(r=>(r.etaChanges||0)>0).length;
    const etaStable=measured.length-etaChanged;
    const setLater=measured.filter(r=>{const c=r.dateAdd||'';const o=r.originalEta||'';return o&&c&&o.slice(0,10)!==c.slice(0,10)}).length;
    if(etaChanged>0||setLater>0){
      html+=`<div style="font-size:.78em;color:#818cf8;margin-top:3px;padding:2px 0;border-top:1px dashed #334155">`;
      html+=`ETA Quality: <b>${etaStable}</b> stable, <b style="color:#fbbf24">${etaChanged}</b> changed`;
      if(setLater>0)html+=`, <b style="color:#94a3b8">${setLater}</b> set after creation`;
      html+=`</div>`;
    }
  }
  const excluded=rows.filter(r=>r.perf!=='On Time'&&r.perf!=='Late');
  if(excluded.length>0)html+=`<div style="font-size:.8em;color:#64748b;margin-top:2px">${excluded.length} excluded (${[...new Set(excluded.map(r=>r.perf))].join(', ')})</div>`;
  const lateOnes=rows.filter(r=>r.perf==='Late');
  if(lateOnes.length>0){
    html+=`<div class="tip-section"><span class="tip-label">Late</span>`;
    lateOnes.slice(0,5).forEach(r=>{
      const delay=r.eta&&r.delivery?daysBetween(r.eta,r.delivery):null;
      const cust=r.customer?`<span class="tip-cust">${esc(r.customer)}</span> `:'';
      const tid=r.ticketId?`<span style="color:#818cf8;font-size:.85em;font-weight:600">${esc(r.ticketId)}</span> `:'';
      const delayTag=delay!==null&&delay>0?` <span class="tip-delay">+${delay}d late</span>`:(!r.delivery?' <span class="tip-delay" style="color:#f87171">NOT DELIVERED</span>':'');
      /* ETA timeline: show original → final → delivery */
      let timeline='';
      if(r.originalEta&&(r.originalEta||'').slice(0,10)!==(r.eta||'').slice(0,10)){
        timeline=`<span class="tip-dates">ETA: ${fmtDate(r.originalEta)} <span style="color:#fbbf24">→ ${fmtDate(r.eta)}</span> (changed ${r.etaChanges||1}x)${r.delivery?' → Delivered '+fmtDate(r.delivery):''}</span>`;
      } else {
        timeline=r.eta?`<span class="tip-dates">ETA: ${fmtDate(r.eta)}${r.delivery?' → Delivered '+fmtDate(r.delivery):''}</span>`:'';
      }
      html+=`<div class="tip-task tip-late">${tid}${cust}${esc(r.focus.slice(0,45))}${delayTag}<br>${timeline}</div>`;
    });
    if(lateOnes.length>5)html+=`<div style="color:#64748b;font-size:.85em;padding-left:10px">+ ${lateOnes.length-5} more</div>`;
    html+=`</div>`;
  }
  const onTimeOnes=rows.filter(r=>r.perf==='On Time');
  if(onTimeOnes.length>0&&onTimeOnes.length<=5){
    html+=`<div class="tip-section"><span class="tip-label">On time</span>`;
    onTimeOnes.forEach(r=>{
      const cust=r.customer?`<span class="tip-cust">${esc(r.customer)}</span> `:'';
      const tid=r.ticketId?`<span style="color:#818cf8;font-size:.85em;font-weight:600">${esc(r.ticketId)}</span> `:'';
      let timeline='';
      if(r.originalEta&&(r.originalEta||'').slice(0,10)!==(r.eta||'').slice(0,10)){
        timeline=`<br><span class="tip-dates">ETA: ${fmtDate(r.originalEta)} <span style="color:#fbbf24">→ ${fmtDate(r.eta)}</span> (changed ${r.etaChanges||1}x)</span>`;
      }
      html+=`<div class="tip-task tip-ontime">${tid}${cust}${esc(r.focus.slice(0,45))}${timeline}</div>`;
    });
    html+=`</div>`;
  }
  return html;
}
function tipVelocity(person,week,calc,rows){
  if(rows.length===0)return`<div class="tip-hdr"><b>${person}</b><span style="color:#64748b">${fmtWeekPretty(week)}</span></div><span class="tip-label">No tasks this week</span>`;
  if(calc.n===0)return`<div class="tip-hdr"><b>${person} &middot; ${fmtWeekPretty(week)}</b></div>${rows.length} tasks, none with delivery dates`;
  const sorted=[...calc.durs].sort((a,b)=>a-b);
  const med=sorted[Math.floor(sorted.length/2)];
  const min=sorted[0],max=sorted[sorted.length-1];
  let html=`<div class="tip-hdr"><b>${person} &middot; ${fmtWeekPretty(week)}</b><span class="tip-pct">${fmtDays(calc.val)}</span></div>`;
  html+=`<div class="tip-stats">`;
  html+=`<div class="tip-stat"><b>${med}d</b><span>median</span></div>`;
  html+=`<div class="tip-stat"><b>${min}d</b><span>fastest</span></div>`;
  html+=`<div class="tip-stat"><b>${max}d</b><span>slowest</span></div>`;
  html+=`<div class="tip-stat"><b>${calc.n}</b><span>tasks</span></div>`;
  html+=`</div>`;
  const slow=rows.filter(r=>r.delivery&&(r.startedAt||r.dateAdd)&&r.status==='Done').map(r=>({f:r.focus,c:r.customer||'',d:daysBetween(r.startedAt||r.dateAdd,r.delivery),eta:r.eta,del:r.delivery,start:r.startedAt||r.dateAdd})).filter(x=>x.d!==null&&x.d>=0).sort((a,b)=>b.d-a.d);
  if(slow.length>0&&slow[0].d>14){
    html+=`<div class="tip-section"><span class="tip-label">Slowest deliveries</span>`;
    slow.slice(0,4).forEach(x=>{
      const cust=x.c?`<span class="tip-cust">${esc(x.c)}</span> &middot; `:'';
      html+=`<div class="tip-task tip-late">${cust}${esc(x.f.slice(0,45))} <span class="tip-delay">${x.d}d</span><br><span class="tip-dates">${fmtDate(x.start)} → ${fmtDate(x.del)}</span></div>`;
    });
    html+=`</div>`;
  }
  const withStart=rows.filter(r=>r.delivery&&r.startedAt&&r.status==='Done').length;
  const withFallback=rows.filter(r=>r.delivery&&!r.startedAt&&r.dateAdd&&r.status==='Done').length;
  if(withFallback>0) html+=`<div style="font-size:.78em;color:#94a3b8;margin-top:3px;border-top:1px dashed #334155;padding-top:3px">${withStart} with start date, ${withFallback} using creation date (may inflate)</div>`;
  return html;
}
function tipReliability(person,week,calc,rows){
  if(rows.length===0)return`<div class="tip-hdr"><b>${person}</b><span style="color:#64748b">${fmtWeekPretty(week)}</span></div><span class="tip-label">No tasks this week</span>`;
  let html=`<div class="tip-hdr"><b>${person} &middot; ${fmtWeekPretty(week)}</b><span class="tip-pct">${fmtPct(calc.val,calc.den)}</span></div>`;
  html+=`<div class="tip-stats">`;
  html+=`<div class="tip-stat"><b style="color:#34d399">${calc.num}</b><span>clean</span></div>`;
  html+=`<div class="tip-stat"><b style="color:#f87171">${calc.reworked}</b><span>rework</span></div>`;
  html+=`<div class="tip-stat"><b>${calc.den}</b><span>done</span></div>`;
  html+=`</div>`;
  if(calc.reworked===0&&calc.den>0)html+=`<div style="color:#fbbf24;font-size:.85em;margin-top:4px">No rework labels applied yet</div>`;
  return html;
}

/* ── KPI Summary Strip ──────────────────────────────── */
function renderKPIStrip(){
  const data=getKPIFiltered();
  const a=calcAccuracy(data);
  const v=calcVelocity(data);
  const r=calcReliability(data);

  /* C1: Check if rework labels are actually in use (check RAW to include future weeks) */
  const hasReworkData=RAW.some(x=>x.rework==='yes');

  /* Activity KPI */
  const act=calcActivity(data);
  const doneAct=data.filter(x=>x.status==='Done').length;
  const openAct=data.filter(x=>x.status!=='Done'&&x.status!=='Canceled').length;

  const items=[
    {el:'kpiCell1',name:'ETA Accuracy',val:a.val,fmt:v=>fmtPct(v,a.den),target:'>90%',pass:a.val!==null&&a.val>=.9,meta:`${a.num}/${a.den} on time, ${a.late||0} late`},
    {el:'kpiCell2',name:'Avg Execution Time',val:v.val,fmt:fmtDays,target:'<28 days',pass:v.val!==null&&v.val<=28,meta:`${v.n} tasks measured`},
    {el:'kpiCell3',name:'Reliability',val:hasReworkData?r.val:null,fmt:v=>fmtPct(v,r.den),target:'>90%',pass:hasReworkData&&r.val!==null&&r.val>=.9,inactive:!hasReworkData,meta:hasReworkData?`${r.num}/${r.den} clean`:'NOT ACTIVE'},
    {el:'kpiCell4',name:'Team Activity',val:act.val,fmt:fmtCount,pass:true,isActivity:true,meta:`${doneAct} done · ${openAct} open`},
  ];
  items.forEach(i=>{
    const cell=document.getElementById(i.el);
    const badge=i.inactive?'badge-inactive':i.isActivity?'badge-pass':(i.val===null?'badge-warn':(i.pass?'badge-pass':'badge-fail'));
    const badgeTxt=i.inactive?'N/A':i.isActivity?`${doneAct}`:( i.val===null?'—':(i.pass?'ON TARGET':'BELOW'));
    cell.innerHTML=`<div class="kc-name">${i.name}</div>
      <div class="kc-val">${i.inactive?'—':(i.val!==null?i.fmt(i.val):'—')}</div>
      <div class="kc-meta">${i.meta}</div>
      <div class="badge ${badge}">${i.isActivity?'&#10003; '+badgeTxt:badgeTxt}</div>`;
  });
}

/* ── Trend charts — M7: tab-specific bars ──────────── */
function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id]}}

function renderTrend(containerId, calcFn, fmtLabel, color, targetVal, targetLabel, isInverse, barMode){
  const el=document.getElementById(containerId);
  if(typeof Chart==='undefined'){el.innerHTML='<p style="padding:20px;color:var(--dim)">Chart.js not loaded. Charts unavailable.</p>';return}
  const data=getKPIFiltered();

  const teamVals=[];
  /* M7: bar data depends on tab context */
  const bar1=[],bar2=[],bar3=[],bar4=[];
  const bar1Label=barMode==='velocity'?'< 14d':barMode==='reliability'?'Clean':'On Time';
  const bar2Label=barMode==='velocity'?'14-28d':barMode==='reliability'?'Rework':'Late';
  const bar3Label=barMode==='velocity'?'28-60d':barMode==='reliability'?'':'';
  const bar4Label=barMode==='velocity'?'> 60d':barMode==='reliability'?'':'No ETA';
  const bar1Color=barMode==='velocity'?'#34d39988':barMode==='reliability'?'#34d39988':'#34d39988';
  const bar2Color=barMode==='velocity'?'#fbbf2488':barMode==='reliability'?'#f8717188':'#f8717188';
  const bar3Color=barMode==='velocity'?'#fb923c88':'#fbbf2488';
  const bar4Color=barMode==='velocity'?'#ef444488':'#d1d5db88';

  CORE_WEEKS.forEach(w=>{
    const rows=data.filter(r=>r.week===w);
    const teamCalc=calcFn(rows);
    teamVals.push(teamCalc.val!==null?(typeof teamCalc.val==='number'?+teamCalc.val.toFixed(2):teamCalc.val):null);

    if(barMode==='velocity'){
      const durs=rows.filter(r=>r.delivery&&(r.startedAt||r.dateAdd)&&r.status==='Done').map(r=>daysBetween(r.startedAt||r.dateAdd,r.delivery)).filter(d=>d!==null&&d>=0);
      bar1.push(durs.filter(d=>d<14).length);
      bar2.push(durs.filter(d=>d>=14&&d<28).length);
      bar3.push(durs.filter(d=>d>=28&&d<60).length);
      bar4.push(durs.filter(d=>d>=60).length);
    }else if(barMode==='reliability'){
      const done=rows.filter(r=>r.status==='Done');
      bar1.push(done.filter(r=>r.rework!=='yes').length);
      bar2.push(done.filter(r=>r.rework==='yes').length);
    }else{
      bar1.push(rows.filter(r=>r.perf==='On Time').length);
      bar2.push(rows.filter(r=>r.perf==='Late').length);
      bar3.push(0); /* Overdue merged into Late */
      bar4.push(rows.filter(r=>r.perf==='No ETA'||r.perf==='No Delivery Date').length);
    }
  });

  /* Build weekly task lookup for rich tooltips */
  const weekTaskDetail={};
  CORE_WEEKS.forEach((w,i)=>{
    const rows=data.filter(r=>r.week===w);
    weekTaskDetail[i]={
      onTime:rows.filter(r=>r.perf==='On Time').map(r=>({f:r.focus,c:r.customer||''})),
      late:rows.filter(r=>r.perf==='Late').map(r=>({f:r.focus,c:r.customer||'',d:r.eta&&r.delivery?daysBetween(r.eta,r.delivery):null})),
      overdue:[], /* merged into late */
      noEta:rows.filter(r=>r.perf==='No ETA'||r.perf==='No Delivery Date').map(r=>({f:r.focus,c:r.customer||''})),
    };
  });

  const datasets=[];
  datasets.push({type:'bar',label:bar1Label,data:bar1,backgroundColor:bar1Color,borderRadius:2,yAxisID:'yBar',stack:'comp',order:2});
  datasets.push({type:'bar',label:bar2Label,data:bar2,backgroundColor:bar2Color,borderRadius:2,yAxisID:'yBar',stack:'comp',order:2});
  if(bar3Label)datasets.push({type:'bar',label:bar3Label,data:bar3,backgroundColor:bar3Color,borderRadius:2,yAxisID:'yBar',stack:'comp',order:2});
  if(bar4Label)datasets.push({type:'bar',label:bar4Label,data:bar4,backgroundColor:bar4Color,borderRadius:2,yAxisID:'yBar',stack:'comp',order:2});

  datasets.push({type:'line',label:fmtLabel,data:teamVals,borderColor:color,backgroundColor:color+'22',borderWidth:1.5,fill:false,tension:.3,pointRadius:2,pointHoverRadius:5,pointBackgroundColor:color,yAxisID:'yLine',order:1,spanGaps:true});
  /* Target line removed — target is visible in KPI pill badges */

  const mNames=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const weekLabels=CORE_WEEKS.map(w=>{const[,m,wn]=parseWeek(w);return mNames[m]+' W'+wn});

  const canvasId=containerId+'-canvas';
  el.innerHTML=`<h4>Weekly Trend — bars: ${barMode||'ETA'} breakdown · line: ${fmtLabel}</h4><canvas id="${canvasId}"></canvas>`;

  destroyChart(canvasId);
  charts[canvasId]=new Chart(document.getElementById(canvasId),{
    type:'bar',
    data:{labels:weekLabels,datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{display:true,position:'bottom',labels:{color:'#374151',font:{size:11,weight:'500'},boxWidth:10,padding:10,usePointStyle:true}},
        tooltip:{
          enabled:true,backgroundColor:'#1e293bee',titleColor:'#93c5fd',titleFont:{size:12,weight:'700'},
          bodyColor:'#e2e8f0',bodyFont:{size:11},padding:12,cornerRadius:8,boxPadding:4,
          callbacks:{
            title:function(items){if(!items[0])return'';const idx=items[0].dataIndex;return CORE_WEEKS[idx]||'';},
            label:function(ctx){
              if(ctx.raw===null||ctx.raw===undefined)return null;
              const name=ctx.dataset.label;
              if(name===targetLabel)return null;
              if(name===fmtLabel){
                const val=ctx.raw;
                const fmtVal=isInverse?val.toFixed(0)+'d':barMode==='activity'?val:(val*100).toFixed(0)+'%';
                return ` ${fmtLabel}: ${fmtVal}`;
              }
              return ' '+name+': '+ctx.raw;
            },
            afterBody:function(items){
              if(!items[0]||barMode==='velocity'||barMode==='reliability')return'';
              const idx=items[0].dataIndex;
              const wt=weekTaskDetail[idx];if(!wt)return'';
              const lines=[];
              if(wt.late.length>0){
                lines.push('','Late:');
                wt.late.slice(0,4).forEach(t=>{
                  const delay=t.d!==null&&t.d>0?' (+'+t.d+'d)':'';
                  const cust=t.c?' ['+t.c+']':'';
                  lines.push('  '+t.f.slice(0,40)+cust+delay);
                });
                if(wt.late.length>4)lines.push('  ... +'+(wt.late.length-4)+' more');
              }
              if(wt.overdue.length>0){
                lines.push('','Overdue:');
                wt.overdue.slice(0,3).forEach(t=>{
                  const cust=t.c?' ['+t.c+']':'';
                  lines.push('  '+t.f.slice(0,40)+cust);
                });
                if(wt.overdue.length>3)lines.push('  ... +'+(wt.overdue.length-3)+' more');
              }
              return lines.join('\n');
            }
          }
        }
      },
      scales:{
        yBar:{position:'left',stacked:true,ticks:{color:'#6b7280',font:{size:10},stepSize:1},grid:{color:'#e5e7eb88'},title:{display:true,text:'Tasks',color:'#9ca3af',font:{size:10}},beginAtZero:true},
        yLine:{position:'right',ticks:{color:color,font:{size:10},stepSize:isInverse?5:undefined,callback:function(v){return isInverse?v+'d':barMode==='activity'?v:(v*100).toFixed(0)+'%'}},grid:{drawOnChartArea:false},title:{display:true,text:fmtLabel,color:color,font:{size:10}},beginAtZero:true,min:0,max:barMode==='activity'?undefined:(isInverse?undefined:1)},
        x:{stacked:true,ticks:{color:'#6b7280',font:{size:10}},grid:{color:'#f3f4f622'}}
      }
    }
  });
}

/* ── Activity calc ─────────────────────────────────── */
function calcActivity(rows){
  return{val:rows.length,n:rows.length,
    done:rows.filter(r=>r.status==='Done').length,
    open:rows.filter(r=>r.status!=='Done'&&r.status!=='Canceled').length,
    canceled:rows.filter(r=>r.status==='Canceled').length};
}
function fmtCount(v){return(v===null||v===undefined)?'—':v}
function heatVol(val){
  if(val===null||val===undefined||val===0)return'heat-vol-0';
  if(val<=2)return'heat-vol-1';if(val<=4)return'heat-vol-2';
  if(val<=7)return'heat-vol-3';if(val<=12)return'heat-vol-4';return'heat-vol-5';
}
function tipActivity(person,week,calc,rows){
  if(rows.length===0)return`<div class="tip-hdr"><b>${person}</b><span style="color:#64748b">${fmtWeekPretty(week)}</span></div><span class="tip-label">No tasks this week</span>`;
  let html=`<div class="tip-hdr"><b>${person} &middot; ${fmtWeekPretty(week)}</b><span class="tip-pct">${calc.n}</span></div>`;
  html+=`<div class="tip-stats">`;
  html+=`<div class="tip-stat"><b style="color:#34d399">${calc.done}</b><span>done</span></div>`;
  html+=`<div class="tip-stat"><b style="color:#60a5fa">${calc.open}</b><span>open</span></div>`;
  if(calc.canceled>0)html+=`<div class="tip-stat"><b style="color:#94a3b8">${calc.canceled}</b><span>canceled</span></div>`;
  html+=`</div>`;
  if(rows.length<=8){
    html+=`<div class="tip-section"><span class="tip-label">Tasks</span>`;
    rows.forEach(r=>{
      const cls=r.status==='Done'?'tip-ontime':r.status==='Canceled'?'':'tip-late';
      const cust=r.customer?`<span class="tip-cust">${esc(r.customer)}</span> &middot; `:'';
      html+=`<div class="tip-task ${cls}">${cust}${esc(r.focus.slice(0,50))}</div>`;
    });
    html+=`</div>`;
  }
  return html;
}

/* ── Member cards — H2 aligned, H14 sample size, D.LIE12 ETA coverage ── */
function renderMemberCards(){
  const data=getKPIFiltered();
  const people=getPeople();
  const el=document.getElementById('memberCards');

  const cards=people.map(p=>{
    const pr=data.filter(r=>r.tsa===p);
    const done=pr.filter(r=>r.status==='Done').length;
    const open=pr.filter(r=>r.status!=='Done'&&r.status!=='Canceled').length;
    const onTime=pr.filter(r=>r.perf==='On Time').length;
    const late=pr.filter(r=>r.perf==='Late').length;
    const overdue=0; /* merged into Late */
    const noEta=pr.filter(r=>r.perf==='No ETA').length;
    const total=pr.length;
    const donePct=total>0?Math.round(done/total*100):0;

    /* H2: Same formula as KPI1 — On Time / (On Time + Late) */
    const measured=onTime+late;
    const accPct=measured>0?Math.round(onTime/measured*100):null;
    /* Organic accuracy — excludes retroactive ETAs */
    const orgOt=pr.filter(r=>r.perf==='On Time'&&r.retroactiveEta!=='yes').length;
    const orgLt=pr.filter(r=>r.perf==='Late'&&r.retroactiveEta!=='yes').length;
    const orgMeasured=orgOt+orgLt;
    const orgAccPct=orgMeasured>0?Math.round(orgOt/orgMeasured*100):null;

    /* D.LIE12: ETA Coverage — real-time snapshot from RAW (not week-filtered).
       D.LIE26 (2026-04-24): must also restrict to External(Customer) — Internal
       ops tickets (TSA routines, customer overviews, etc) do not require ETAs. */
    const ACTIVE_STATUSES=['In Progress','In Review','Production QA','Blocked','Refinement','Ready to Deploy','B.B.C'];
    const allPersonRaw=RAW.filter(r=>r.source!=='spreadsheet'&&r.tsa===p&&r.category==='External');
    const activeTickets=allPersonRaw.filter(r=>ACTIVE_STATUSES.includes(r.status));
    const activeWithEta=activeTickets.filter(r=>r.eta&&r.eta.length>=10).length;
    const activeTotal=activeTickets.length;
    const etaCov=activeTotal>0?Math.round(activeWithEta/activeTotal*100):100;

    const recent=pr.filter(r=>{const lw=CORE_WEEKS.slice(-2);return lw.includes(r.week)}).length;

    let alert='';
    if(recent===0&&total>0)alert='<span class="mc-alert mc-alert-warn">NO RECENT</span>';
    else if(noEta>total*0.5)alert='<span class="mc-alert mc-alert-warn">'+noEta+' NO ETA</span>';
    else if(accPct!==null&&accPct>=85)alert='<span class="mc-alert mc-alert-ok">ON TRACK</span>';

    const barColor=donePct>=80?'var(--green)':donePct>=50?'var(--yellow)':'var(--red)';

    return`<div class="member-card">${alert}
      <div class="mc-name">${p}</div>
      <div class="mc-body">
        <div class="mc-row"><span title="All tickets assigned to this person in the selected period">Total</span><b>${total}</b></div>
        <div class="mc-row"><span title="Tickets marked as Done. Percentage is Done / Total">Done</span><b>${done} (${donePct}%)</b></div>
        <div class="mc-row"><span title="Active tickets (not Done or Canceled)">Open</span><b>${open}</b></div>
        <div class="mc-row"><span title="Delivered on or before the ETA deadline">On Time</span><b style="color:var(--green)">${onTime}</b></div>
        <div class="mc-row"><span title="Past ETA — delivered after deadline or still not delivered">Late</span><b style="color:${late>0?'var(--red)':'var(--dim)'}">${late}</b></div>
        <div class="mc-row"><span title="On Time / (On Time + Late). Includes retroactive ETAs.${orgAccPct!==null?' Organic (pre-set ETAs only): '+orgAccPct+'% ('+orgOt+'/'+orgMeasured+')':''}">Accuracy</span><b>${accPct!==null?accPct+'%':'—'}</b>${orgAccPct!==null&&orgAccPct!==accPct?'<span style="font-size:.7em;color:#94a3b8;margin-left:4px" title="Organic: only tickets where ETA was set before delivery">('+orgAccPct+'% organic)</span>':''}</div>
        <div class="mc-row"><span title="% of active tickets (In Progress, In Review, Prod QA, Blocked) with ETA set">ETA Coverage</span><b style="color:${activeTotal===0?'var(--dim)':etaCov<80?'var(--yellow)':'var(--dim)'}">${activeTotal===0?'—':etaCov+'% ('+activeWithEta+'/'+activeTotal+')'}</b></div>
      </div>
      <div class="mc-bar"><div class="mc-bar-track"><div class="mc-bar-inner" style="width:${donePct}%;background:${barColor}"></div></div></div>
    </div>`;
  });
  el.innerHTML=cards.join('');
}

/* ── Segment counts ────────────────────────────────── */
function updateSegmentCounts(){
  const base=RAW.filter(r=>r.week&&isCoreWeek(r.week)&&(state.person==='ALL'||r.tsa===state.person));
  document.getElementById('segExt').textContent=' ('+base.filter(r=>r.category==='External').length+')';
  document.getElementById('segInt').textContent=' ('+base.filter(r=>r.category==='Internal').length+')';
  document.getElementById('segAll').textContent=' ('+base.length+')';
}

/* ── KPI by Client ────────────────────────────────── */
const CLIENT_TIP='<b>KPI by Customer</b><br><span class=tip-label>Shows</span>: ETA Accuracy, Avg Execution, Reliability per customer<br><span class=tip-label>Colors</span>: Same heat scale as main grids';
const INTERNAL_CONTEXTS=new Set(['Waki','TBX','Routine','General','Coda','All',"Internal \u2013 Sam's Board Meeting"]);

function renderCustomerKPI(){
  const isInt=state.category==='Internal';
  const isAll=state.category==='ALL';
  const base=RAW.filter(r=>{
    if(!r.week||!isCoreWeek(r.week))return false;
    if(state.person!=='ALL'&&r.tsa!==state.person)return false;
    if(!r.customer)return false;
    if(state.month!=='ALL'){
      const[y,m]=parseWeek(r.week);
      if(monthLabel(y,m)!==state.month)return false;
    }
    if(isAll)return true;
    if(isInt)return r.category==='Internal'&&INTERNAL_CONTEXTS.has(r.customer);
    return r.category==='External';
  });
  document.getElementById('customerKPITitle').textContent=isInt?'KPI by Internal Demand':(isAll?'KPI by Customer / Demand':'KPI by Customer');
  const el=document.getElementById('customerKPITable');
  if(!base.length){el.innerHTML='<tr><td colspan="10" style="padding:20px;text-align:center;color:var(--dim)">No customer data in this view</td></tr>';return}
  const custs=[...new Set(base.map(r=>r.customer))];
  custs.sort((a,b)=>base.filter(r=>r.customer===b).length-base.filter(r=>r.customer===a).length);
  const cols=['Customer','Tasks','Done','On Time','Late','No ETA','ETA Accuracy','Avg Execution','Reliability'];
  let rowIdx=0;
  function kpiRow(label,rows,isTeam){
    const t=rows.length,dn=rows.filter(r=>r.status==='Done').length;
    const ot=rows.filter(r=>r.perf==='On Time').length,lt=rows.filter(r=>r.perf==='Late').length;
    const ne=rows.filter(r=>r.perf==='No ETA').length;
    const ad=ot+lt,acc=ad>0?ot/ad:null;
    const doneRows=rows.filter(r=>r.status==='Done');const rw=doneRows.filter(r=>r.rework==='yes').length;const rd=doneRows.length,rel=rd>0?(rd-rw)/rd:null;
    const ds=rows.filter(r=>r.delivery&&(r.startedAt||r.dateAdd)&&r.status==='Done').map(r=>daysBetween(r.startedAt||r.dateAdd,r.delivery)).filter(d=>d!==null&&d>=0);
    const avg=ds.length>0?ds.reduce((a,b)=>a+b,0)/ds.length:null;
    const cls=isTeam?' class="team-row"':'';
    const bg=isTeam?'':((rowIdx%2===0)?'background:#f9fafb;':'');
    const lbl=isTeam?`<td class="person-label">OVERALL</td>`:`<td class="person-label" style="${bg}">${label}</td>`;
    if(!isTeam)rowIdx++;
    return`<tr${cls}>${lbl}<td style="${bg}">${t}</td><td style="${bg}">${dn}</td><td style="${bg}color:var(--green);font-weight:600">${ot}</td><td style="${bg}color:${lt?'var(--red)':'var(--dim)'}">${lt}</td><td style="${bg}color:${ne?'var(--yellow)':'var(--dim)'}">${ne}</td><td class="cell ${acc!==null?heatPct(acc):'heat-na'}" style="font-weight:700">${fmtPct(acc,ad)}</td><td class="cell ${avg!==null?heatDays(avg):'heat-na'}" style="font-weight:700">${fmtDays(avg)}</td><td class="cell ${rel!==null?heatPct(rel):'heat-na'}" style="font-weight:700">${fmtPct(rel,rd)}</td></tr>`;
  }
  let h='<thead><tr>'+cols.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead>';
  rowIdx=0;
  let b='<tbody>';
  custs.forEach(c=>{b+=kpiRow(c,base.filter(r=>r.customer===c),false)});
  b+=kpiRow('OVERALL',base,true);
  b+='</tbody>';
  el.innerHTML=h+b;
}

/* ── Audit table ──────────────────────────────────── */
let auditSortCol=0, auditSortAsc=true;

function getAuditRows(){
  const fPerson=document.getElementById('auditFilterPerson').value;
  const fWorkStatus=document.getElementById('auditFilterWorkStatus').value;
  const fPerf=document.getElementById('auditFilterPerf').value;
  const fCustomer=document.getElementById('auditFilterCustomer').value;
  let data=getFiltered();
  if(fPerson!=='ALL')data=data.filter(r=>r.tsa===fPerson);
  if(fWorkStatus!=='ALL')data=data.filter(r=>r.status===fWorkStatus);
  if(fPerf!=='ALL')data=data.filter(r=>r.perf===fPerf);
  if(fCustomer!=='ALL')data=data.filter(r=>(r.customer||'')===(fCustomer==='(empty)'?'':fCustomer));
  return data.map((r,i)=>{
    const start=r.startedAt||r.dateAdd;const dur=(r.delivery&&start)?daysBetween(start,r.delivery):null;
    const origEta=r.originalEta||'—';const finalEta=r.eta||'—';const etaChg=r.etaChanges||0;
    return [i+1, r.tsa||'—', r.week||'—', r.ticketId||'—', r.focus||'—', r.status||'—', r.category||'—', r.demandType||'—', r.customer||'—', r.dateAdd||'—', origEta, finalEta, etaChg>0?etaChg+'x':'—', r.delivery||'—', r.perf||'—', r.rework==='yes'?'YES':'—', dur!==null&&dur>=0?dur+'d':'—', r.source||'—', r.ticketUrl||'', r.milestone||'—', r.parentId||'—'];
  });
}
function populateAuditFilters(){
  const selP=document.getElementById('auditFilterPerson');
  const selS=document.getElementById('auditFilterWorkStatus');
  const selC=document.getElementById('auditFilterCustomer');
  const data=getFiltered();
  const curP=selP.value,curS=selS.value,curC=selC.value;

  const people=[...new Set(data.map(r=>r.tsa||''))].filter(Boolean).sort();
  selP.innerHTML='<option value="ALL">All People</option>';
  people.forEach(p=>{selP.innerHTML+=`<option value="${esc(p)}">${esc(p)}</option>`});
  selP.value=curP;

  const statuses=[...new Set(data.map(r=>r.status||''))].filter(Boolean).sort();
  selS.innerHTML='<option value="ALL">All Status</option>';
  statuses.forEach(s=>{selS.innerHTML+=`<option value="${esc(s)}">${esc(s)}</option>`});
  selS.value=curS;

  const custs=[...new Set(data.map(r=>r.customer||''))].sort();
  selC.innerHTML='<option value="ALL">All Customers</option>';
  custs.forEach(c=>{
    const label=c||'(empty)';
    selC.innerHTML+=`<option value="${c?esc(c):'(empty)'}">${esc(label)}</option>`;
  });
  selC.value=curC;
}

const AUDIT_COLS=['#','Person','Week','Ticket','Focus/Task','Status','Category','Demand Type','Customer','Date Added','Original ETA','Final ETA','ETA Changes','Delivery','Performance','Rework','Duration','Source','Ticket URL','Milestone','Parent'];

function perfClass(v){
  if(v==='On Time')return'perf-on-time';if(v==='Late')return'perf-late';if(v==='On Track')return'perf-on-track';if(v==='On Hold')return'perf-on-hold';
  if(v==='Not Started')return'perf-not-started';
  return'perf-na';
}

function renderAuditTable(){
  const rows=getAuditRows();
  rows.forEach((r,i)=>r[0]=i+1);
  const hideCols=new Set([18]);
  rows.sort((a,b)=>{
    let va=a[auditSortCol],vb=b[auditSortCol];
    if(typeof va==='string'&&typeof vb==='string'){va=va.toLowerCase();vb=vb.toLowerCase()}
    if(va<vb)return auditSortAsc?-1:1;if(va>vb)return auditSortAsc?1:-1;return 0;
  });

  const table=document.getElementById('auditTable');
  let thead='<thead><tr>';
  AUDIT_COLS.forEach((c,i)=>{
    if(hideCols.has(i))return;
    const arrow=i===auditSortCol?(auditSortAsc?'&#9650;':'&#9660;'):'';
    thead+=`<th data-col="${i}">${c}<span class="sort-arrow">${arrow}</span></th>`;
  });
  thead+='</tr></thead>';

  let tbody='<tbody>';
  rows.forEach(r=>{
    tbody+='<tr>';
    r.forEach((v,i)=>{
      if(hideCols.has(i))return;
      const cls=i===14?' class="'+perfClass(v)+'"':(i===15&&v==='YES'?' class="rework-yes"':'');
      if(i===3&&r[18]){tbody+=`<td><a href="${esc(r[18])}" target="_blank" style="color:var(--accent);text-decoration:none;font-weight:600">${esc(String(v))}</a></td>`}
      else{tbody+=`<td${cls}>${esc(String(v))}</td>`}
    });
    tbody+='</tr>';
  });
  tbody+='</tbody>';
  table.innerHTML=thead+tbody;

  table.querySelectorAll('th').forEach(th=>{
    th.addEventListener('click',()=>{
      const col=+th.dataset.col;
      if(col===auditSortCol)auditSortAsc=!auditSortAsc;
      else{auditSortCol=col;auditSortAsc=true}
      renderAuditTable();
    });
  });

  const stats=document.getElementById('auditStats');
  const sdata=getFiltered();
  const onTime=sdata.filter(r=>r.perf==='On Time').length;
  const late=sdata.filter(r=>r.perf==='Late').length;
  /* Overdue merged into Late */
  const done=sdata.filter(r=>r.status==='Done').length;
  const open=sdata.filter(r=>r.status!=='Done'&&r.status!=='Canceled').length;
  const reworkCount=sdata.filter(r=>r.rework==='yes').length;
  /* M13: Note about On Track exclusion */
  const onTrack=sdata.filter(r=>r.perf==='On Track').length;
  const personNote=state.person!=='ALL'?` · Filtered by: ${state.person}`:'';
  stats.innerHTML=`<span><b>${rows.length}</b> records</span><span>Done: <b>${done}</b></span><span>Open: <b>${open}</b></span><span style="color:var(--green)">On Time: <b>${onTime}</b></span><span style="color:var(--red)">Late: <b>${late}</b></span><span>On Track: <b>${onTrack}</b> (excluded)</span><span style="color:var(--red)">Rework: <b>${reworkCount}</b></span>${personNote}`;
}

/* ── Export functions ──────────────────────────────── */
function downloadXLSX(){
  if(typeof XLSX==='undefined'){alert('SheetJS not loaded. Export unavailable.');return}
  const rows=getAuditRows();
  rows.forEach((r,i)=>r[0]=i+1);
  const aoa=[AUDIT_COLS,...rows];
  const ws=XLSX.utils.aoa_to_sheet(aoa);
  ws['!cols']=[{wch:5},{wch:14},{wch:12},{wch:12},{wch:45},{wch:12},{wch:11},{wch:18},{wch:25},{wch:12},{wch:12},{wch:12},{wch:10},{wch:12},{wch:13},{wch:8},{wch:10},{wch:12},{wch:55},{wch:25},{wch:12}];
  for(let r=1;r<=rows.length;r++){
    const urlCol=18;const urlCell=XLSX.utils.encode_cell({r:r,c:urlCol});
    const ticketCell=XLSX.utils.encode_cell({r:r,c:3});
    if(ws[urlCell]&&ws[urlCell].v&&ws[urlCell].v.startsWith('http')){
      ws[urlCell].l={Target:ws[urlCell].v,Tooltip:'Open in Linear'};
      if(ws[ticketCell]&&ws[ticketCell].v&&ws[ticketCell].v!=='—'){ws[ticketCell].l={Target:ws[urlCell].v,Tooltip:'Open in Linear'}}
    }
  }
  const wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,'Audit');
  XLSX.writeFile(wb,'KPI_AUDIT_'+new Date().toISOString().slice(0,10)+'.xlsx');
}

function copyTSV(){
  const rows=getAuditRows();
  rows.forEach((r,i)=>r[0]=i+1);
  let tsv=AUDIT_COLS.join('\t')+'\n';
  rows.forEach(r=>{tsv+=r.join('\t')+'\n'});
  navigator.clipboard.writeText(tsv).then(()=>{
    const btn=document.querySelector('.audit-tools button:nth-child(2)');
    const orig=btn.innerHTML;btn.innerHTML='&#10003; Copied!';btn.style.background='var(--green)';btn.style.color='#fff';
    setTimeout(()=>{btn.innerHTML=orig;btn.style.background='';btn.style.color=''},1500);
  });
}

/* ── Dashboard Guide ────────────────────────────────── */
function showGuide(){
  const ov=document.createElement('div');
  ov.id='guideOverlay';
  ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.7);backdrop-filter:blur(4px);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
  ov.onclick=e=>{if(e.target===ov)ov.remove()};
  const box=document.createElement('div');
  box.style.cssText='background:#fff;border-radius:16px;max-width:860px;width:100%;max-height:92vh;overflow-y:auto;box-shadow:0 25px 80px rgba(0,0,0,.35);font-family:Inter,Segoe UI,sans-serif;color:#1e293b;line-height:1.7;font-size:14px';
  const S=`
    .g-hdr{background:linear-gradient(135deg,#064e3b,#065f46,#047857);color:#fff;padding:32px 40px 28px;border-radius:16px 16px 0 0;position:relative;overflow:hidden}
    .g-hdr::after{content:'';position:absolute;top:-40px;right:-40px;width:180px;height:180px;border-radius:50%;background:rgba(255,255,255,.06)}
    .g-hdr::before{content:'';position:absolute;bottom:-60px;left:-20px;width:200px;height:200px;border-radius:50%;background:rgba(255,255,255,.04)}
    .g-hdr h1{font-size:1.6em;font-weight:800;margin:0 0 4px;position:relative}
    .g-hdr p{font-size:.88em;opacity:.8;margin:0;position:relative}
    .g-close{position:absolute;top:16px;right:20px;background:rgba(255,255,255,.15);border:none;color:#fff;font-size:1.3em;width:36px;height:36px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .15s}
    .g-close:hover{background:rgba(255,255,255,.3)}
    .g-body{padding:28px 40px 36px}
    .g-section{margin-bottom:28px;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden}
    .g-section-hdr{display:flex;align-items:center;gap:12px;padding:14px 20px;background:linear-gradient(135deg,#f8fafc,#f1f5f9);border-bottom:1px solid #e2e8f0;cursor:default}
    .g-section-hdr .g-icon{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1em;flex-shrink:0}
    .g-section-hdr h2{font-size:1em;font-weight:700;color:#0f172a;margin:0;flex:1}
    .g-section-hdr .g-tag{font-size:.6em;font-weight:700;padding:2px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:.5px}
    .g-section-body{padding:16px 20px}
    .g-section-body p{margin:0 0 10px;color:#334155}
    .g-section-body ul,.g-section-body ol{margin:6px 0 12px 20px;color:#475569}
    .g-section-body li{margin-bottom:6px}
    .g-section-body li b{color:#0f172a}
    .g-section-body code{background:#f1f5f9;color:#6366f1;padding:1px 6px;border-radius:4px;font-size:.9em;font-weight:600}
    .g-formula{background:linear-gradient(135deg,#eff6ff,#e0e7ff);border:1px solid #c7d2fe;border-radius:8px;padding:12px 16px;margin:10px 0;font-family:monospace;font-size:.92em;color:#4338ca;font-weight:600;text-align:center}
    .g-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}
    .g-grid-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px}
    .g-grid-item b{display:block;font-size:.92em;color:#0f172a;margin-bottom:2px}
    .g-grid-item span{font-size:.8em;color:#64748b}
    .g-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 10px;border-radius:20px;font-size:.78em;font-weight:700;margin:0 3px}
    .g-pipe{display:flex;align-items:center;gap:0;margin:12px 0}
    .g-pipe-step{flex:1;text-align:center;padding:10px 6px;background:#f8fafc;border:1px solid #e2e8f0;position:relative;font-size:.78em}
    .g-pipe-step:first-child{border-radius:8px 0 0 8px}
    .g-pipe-step:last-child{border-radius:0 8px 8px 0}
    .g-pipe-step b{display:block;color:#0f172a;font-size:.95em;margin-bottom:2px}
    .g-pipe-step::after{content:"\\2192";position:absolute;right:-8px;top:50%;transform:translateY(-50%);color:#94a3b8;font-size:1.1em;z-index:1}
    .g-pipe-step:last-child::after{display:none}
    .g-color{display:inline-block;width:14px;height:14px;border-radius:4px;vertical-align:middle;margin-right:6px;border:1px solid rgba(0,0,0,.1)}
    .g-footer{padding:20px 40px;background:#f8fafc;border-top:1px solid #e2e8f0;border-radius:0 0 16px 16px;text-align:center;font-size:.78em;color:#94a3b8}
  `;
  box.innerHTML=`<style>${S}</style>
    <div class="g-hdr">
      <button class="g-close" onclick="document.getElementById('guideOverlay').remove()">&times;</button>
      <h1>KPI Dashboard</h1>
      <p>Complete reference guide — every screen, metric, and interaction explained.</p>
    </div>
    <div class="g-body">

      <!-- 1. CONTROL STRIP -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#ecfdf5;color:#059669">&#9881;</div>
          <h2>Control Strip</h2>
          <span class="g-tag" style="background:#ecfdf5;color:#065f46">Filters + KPIs</span>
        </div>
        <div class="g-section-body">
          <p>The top strip is divided into two groups:</p>
          <div class="g-grid">
            <div class="g-grid-item" style="border-left:3px solid #059669">
              <b>Filters (green group)</b>
              <span><b>All</b> / <b>Internal</b> / <b>External</b> — click to filter every chart, heatmap, member card, and KPI by category. Counts update in real time.</span>
            </div>
            <div class="g-grid-item" style="border-left:3px solid #2563eb">
              <b>KPI Indicators (blue group)</b>
              <span>4 metrics that summarize team performance. <b>Click any KPI to jump to its detailed tab</b> below. The active KPI has a blue highlight.</span>
            </div>
          </div>
          <div class="g-grid" style="grid-template-columns:repeat(4,1fr)">
            <div class="g-grid-item" style="text-align:center">
              <b style="color:#2563eb">ETA Accuracy</b>
              <span>% delivered on or before ETA</span>
            </div>
            <div class="g-grid-item" style="text-align:center">
              <b style="color:#d97706">Execution Time</b>
              <span>Avg days from start to delivery</span>
            </div>
            <div class="g-grid-item" style="text-align:center">
              <b style="color:#6b7280">Reliability</b>
              <span>% without rework needed</span>
            </div>
            <div class="g-grid-item" style="text-align:center">
              <b style="color:#7c3aed">Team Activity</b>
              <span>Total tasks in period</span>
            </div>
          </div>
          <div class="g-formula">ETA Accuracy = On Time / (On Time + Late)<br><span style="font-size:.85em;color:#6366f1;font-weight:400">Late = past ETA (delivered or not). Excludes: On Track, No ETA, Not Started, Blocked (B.B.C), N/A</span><br>
<span style="font-size:.85em;color:#6366f1;font-weight:400">Measured against Original ETA (first deadline set). If the ETA was extended, accuracy is still measured against the original commitment — this reflects prediction quality, not delivery against revised dates.</span></div>
        </div>
      </div>

      <!-- 2. STALENESS BANNER -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#ecfdf5;color:#059669">&#128337;</div>
          <h2>Data Freshness</h2>
          <span class="g-tag" style="background:#dbeafe;color:#1e40af">Auto-detected</span>
        </div>
        <div class="g-section-body">
          <p>The banner below the header shows how recent the data is:</p>
          <div style="display:flex;gap:8px;margin:8px 0 12px">
            <div style="flex:1;padding:8px 12px;border-radius:6px;background:#ecfdf5;border:1px solid #a7f3d0;text-align:center"><b style="color:#065f46;font-size:.85em"><span class="g-color" style="background:#059669"></span>Fresh</b><br><span style="font-size:.72em;color:#065f46">0-3 days</span></div>
            <div style="flex:1;padding:8px 12px;border-radius:6px;background:#fffbeb;border:1px solid #fde68a;text-align:center"><b style="color:#92400e;font-size:.85em"><span class="g-color" style="background:#d97706"></span>Aging</b><br><span style="font-size:.72em;color:#92400e">3-7 days</span></div>
            <div style="flex:1;padding:8px 12px;border-radius:6px;background:#fef2f2;border:1px solid #fecaca;text-align:center"><b style="color:#991b1b;font-size:.85em"><span class="g-color" style="background:#dc2626"></span>Stale</b><br><span style="font-size:.72em;color:#991b1b">&gt; 7 days</span></div>
          </div>
          <p>The <i>period label</i> (e.g. Nov 2025 — Mar 2026) is a <b>rolling 4-month window</b> computed automatically from today's date. No manual configuration needed — it always shows the most relevant time range.</p>
        </div>
      </div>

      <!-- 3. MEMBER CARDS -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#ede9fe;color:#7c3aed">&#128100;</div>
          <h2>Member Cards</h2>
          <span class="g-tag" style="background:#ede9fe;color:#6d28d9">Per-person</span>
        </div>
        <div class="g-section-body">
          <p>One card per team member, showing individual performance at a glance:</p>
          <div class="g-grid">
            <div class="g-grid-item"><b>Total / Done / Open</b><span>Task counts with completion %</span></div>
            <div class="g-grid-item"><b>On Time <span style="color:#059669">(green)</span></b><span>Delivered on or before ETA</span></div>
            <div class="g-grid-item"><b>Late <span style="color:#dc2626">(red)</span></b><span>Past ETA — delivered after deadline or not delivered yet</span></div>
            <div class="g-grid-item"><b>Accuracy</b><span>On Time / (On Time + Late). Hover heatmap cells for detail</span></div>
            <div class="g-grid-item"><b>ETA Coverage</b><span>% of active tasks (In Progress, In Review, Prod QA, Blocked) with ETA set. <span style="color:#d97706">Yellow</span> if &lt; 80%</span></div>
            <div class="g-grid-item"><b>Progress Bar</b><span>Visual completion rate — green &ge; 80%, yellow &ge; 50%, red &lt; 50%</span></div>
          </div>
          <p style="margin-top:12px"><b>Badges:</b>
            <span class="g-badge" style="background:#d1fae5;color:#065f46">ON TRACK</span> accuracy &ge; 85%
            <span class="g-badge" style="background:#fef3c7;color:#92400e">NO RECENT</span> no tasks in last 2 weeks
            <span class="g-badge" style="background:#fef3c7;color:#92400e">X NO ETA</span> &gt; 50% tasks lack ETA
          </p>
        </div>
      </div>

      <!-- 4. TABS -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#dbeafe;color:#2563eb">&#128200;</div>
          <h2>Analysis Tabs</h2>
          <span class="g-tag" style="background:#dbeafe;color:#1e40af">4 views</span>
        </div>
        <div class="g-section-body">
          <p>Each tab provides two synchronized views of the same metric:</p>
          <div class="g-grid">
            <div class="g-grid-item" style="border-left:3px solid #4f46e5">
              <b>Weekly Trend Chart</b>
              <span>Stacked bars show the breakdown per week (On Time vs Late vs No ETA). A line traces the overall metric value across weeks.</span>
              <br><span style="font-size:.78em;color:#6366f1;font-weight:600;margin-top:4px;display:inline-block">Hover any bar for task-level detail: task name, customer, and delay days.</span>
            </div>
            <div class="g-grid-item" style="border-left:3px solid #059669">
              <b>Heatmap Grid</b>
              <span>Person x Week matrix with color-coded cells. Hover any cell for full breakdown including individual task names and statuses.</span>
              <br><span style="font-size:.78em;color:#059669;font-weight:600;margin-top:4px;display:inline-block">Colors: green = good, yellow = warning, red = needs attention.</span>
            </div>
          </div>
          <div class="g-grid" style="grid-template-columns:repeat(4,1fr);margin-top:10px">
            <div class="g-grid-item" style="text-align:center;background:#eef2ff"><b style="color:#4f46e5;font-size:.85em">ETA Accuracy</b><br><span style="font-size:.72em">On Time vs Late</span></div>
            <div class="g-grid-item" style="text-align:center;background:#fffbeb"><b style="color:#b45309;font-size:.85em">Execution Time</b><br><span style="font-size:.72em">&lt;14d / 14-28d / 28-60d / &gt;60d</span></div>
            <div class="g-grid-item" style="text-align:center;background:#ecfdf5"><b style="color:#047857;font-size:.85em">Reliability</b><br><span style="font-size:.72em">Clean vs Rework</span></div>
            <div class="g-grid-item" style="text-align:center;background:#f5f3ff"><b style="color:#7c3aed;font-size:.85em">Team Activity</b><br><span style="font-size:.72em">Task volume per week</span></div>
          </div>
        </div>
      </div>

      <!-- 5. KPI BY CUSTOMER -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#fef3c7;color:#d97706">&#127970;</div>
          <h2>KPI by Customer</h2>
          <span class="g-tag" style="background:#fef3c7;color:#92400e">Drill-down</span>
        </div>
        <div class="g-section-body">
          <p>Table showing per-customer metrics: <b>accuracy</b>, <b>avg execution time</b>, <b>reliability</b>, and <b>task count</b>. Color-coded cells use the same heat scale as the main heatmaps.</p>
          <p>The table automatically switches between <b>External customers</b> and <b>Internal contexts</b> based on the active segment filter.</p>
        </div>
      </div>

      <!-- 6. AUDIT TABLE -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#f1f5f9;color:#475569">&#128203;</div>
          <h2>Audit Data Table</h2>
          <span class="g-tag" style="background:#f1f5f9;color:#475569">Expandable</span>
        </div>
        <div class="g-section-body">
          <p>Click to expand. Full record-level table with <b>19 columns</b>. Click any column header to sort. Two export options in the header:</p>
          <div class="g-grid">
            <div class="g-grid-item"><b>XLSX Export</b><span>Downloads a formatted Excel file with all visible records, hyperlinked ticket IDs</span></div>
            <div class="g-grid-item"><b>Copy TSV</b><span>Copies tab-separated data to clipboard for pasting into spreadsheets</span></div>
          </div>
          <p style="margin-top:10px"><b>Performance Labels:</b></p>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0">
            <span class="g-badge" style="background:#d1fae5;color:#065f46">On Time</span>
            <span class="g-badge" style="background:#fee2e2;color:#991b1b">Late</span>
            <span class="g-badge" style="background:#f3f4f6;color:#6b7280">No ETA</span>
            <span class="g-badge" style="background:#dbeafe;color:#1e40af">On Track</span>
            <span class="g-badge" style="background:#fce7f3;color:#9d174d">Blocked (B.B.C)</span>
            <span class="g-badge" style="background:#ede9fe;color:#7c3aed">Not Started</span>
            <span class="g-badge" style="background:#f3f4f6;color:#9ca3af">N/A (Canceled)</span>
          </div>
          <p style="margin-top:8px;font-size:.88em;color:#64748b">
            <b>Late</b> = ETA passed (delivered after or not delivered yet). <b>No ETA</b> = active work without a due date set. <b>Not Started</b> = ticket in Backlog/Todo/Triage — ETA not applicable yet. <b>B.B.C</b> = Blocked By Customer — excluded from accuracy. <b>On Hold</b> = Paused — excluded from accuracy. <b>N/A</b> = Canceled or not measurable.
          </p>
        </div>
      </div>

      <!-- 7. REWORK LOG -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#fef2f2;color:#dc2626">&#128260;</div>
          <h2>Rework Log</h2>
          <span class="g-tag" style="background:#fef2f2;color:#991b1b">Quality</span>
        </div>
        <div class="g-section-body">
          <p>Lists tickets flagged with the <code>rework:implementation</code> label in Linear. Shows ticket link, person, customer, and delivery date.</p>
          <p>This section feeds the <b>Reliability KPI</b>. When rework labels are applied in Linear, the KPI3 pill activates automatically and starts tracking the clean delivery rate.</p>
        </div>
      </div>

      <!-- 8. DATA PIPELINE -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#e0e7ff;color:#4338ca">&#9881;</div>
          <h2>Data Pipeline</h2>
          <span class="g-tag" style="background:#e0e7ff;color:#3730a3">Technical</span>
        </div>
        <div class="g-section-body">
          <p>The dashboard is generated by a <b>4-step Python pipeline</b>, each step feeding the next:</p>
          <div class="g-pipe">
            <div class="g-pipe-step" style="background:#eef2ff"><b>1. Refresh</b>Linear API &rarr; cache</div>
            <div class="g-pipe-step" style="background:#ecfdf5"><b>2. Merge</b>Linear + spreadsheet</div>
            <div class="g-pipe-step" style="background:#fffbeb"><b>3. Normalize</b>Clean &amp; fix data</div>
            <div class="g-pipe-step" style="background:#fce7f3"><b>4. Build</b>Generate HTML</div>
          </div>
          <p>Run the full pipeline:</p>
          <div class="g-formula" style="background:#1e293b;color:#a5f3fc;border-color:#334155;text-align:left;font-size:.88em">
            <span style="color:#94a3b8">$</span> python kpi/orchestrate.py<br>
            <span style="color:#94a3b8">$</span> python kpi/orchestrate.py --skip-refresh &nbsp;<span style="color:#64748b"># reuse cached API data</span><br>
            <span style="color:#94a3b8">$</span> python kpi/orchestrate.py --build-only &nbsp;&nbsp;<span style="color:#64748b"># rebuild HTML only</span>
          </div>
          <p style="font-size:.85em;color:#64748b">All writes are <b>atomic</b> (write to .tmp, then replace). Pipeline stops on first error. Each step has a 120s timeout.</p>
        </div>
      </div>

      <!-- 9. GLOSSARY -->
      <div class="g-section">
        <div class="g-section-hdr">
          <div class="g-icon" style="background:#f0fdf4;color:#16a34a">&#128218;</div>
          <h2>Glossary</h2>
          <span class="g-tag" style="background:#f0fdf4;color:#166534">Reference</span>
        </div>
        <div class="g-section-body">
          <div class="g-grid">
            <div class="g-grid-item"><b>ETA</b><span>Due date set in Linear — the committed delivery date</span></div>
            <div class="g-grid-item"><b>On Time</b><span>Delivered on or before ETA</span></div>
            <div class="g-grid-item"><b>Late</b><span>Past ETA — delivered after deadline or still not delivered</span></div>
            <div class="g-grid-item"><b>No ETA</b><span>Active work (In Progress/Done) without a due date set</span></div>
            <div class="g-grid-item"><b>Not Started</b><span>Ticket in Backlog/Todo/Triage — ETA not applicable yet</span></div>
            <div class="g-grid-item"><b>On Track</b><span>In progress, ETA is in the future</span></div>
            <div class="g-grid-item"><b>On Hold</b><span>Ticket paused — excluded from accuracy calculation</span></div>
            <div class="g-grid-item"><b>B.B.C</b><span>Blocked By Customer — excluded from accuracy</span></div>
            <div class="g-grid-item"><b>Core Week</b><span>A week within the rolling 4-month window</span></div>
            <div class="g-grid-item"><b>Rework</b><span>Task re-implemented after delivery (rework:implementation label)</span></div>
            <div class="g-grid-item"><b>Velocity</b><span>Days between start (In Progress) and delivery (In Review/Done)</span></div>
            <div class="g-grid-item"><b>Source: Linear</b><span>Live data from Linear API — primary source</span></div>
            <div class="g-grid-item"><b>Source: Spreadsheet</b><span>Historical backlog from CODA/sheets</span></div>
          </div>
        </div>
      </div>

    </div>
    <div class="g-footer">
      KPI Dashboard v3 &middot; Built ${BUILD_DATE} &middot; Team Raccoons &middot; Powered by Linear + Python + Chart.js
    </div>
  `;
  ov.appendChild(box);
  document.body.appendChild(ov);
}

/* ── Render all ─────────────────────────────────────── */
let _renderTimer=null;
function debouncedRender(){clearTimeout(_renderTimer);_renderTimer=setTimeout(render,150)}
function render(){
  /* Keep tipCache across renders — only clear entries for the active tab's grid */
  /* tipCounter continues incrementing to avoid ID collisions between tabs */
  const activeTab=document.querySelector('.tab.active');
  const activeTabName=activeTab?activeTab.dataset.tab:'accuracy';
  /* Always-run: shared across all tabs */
  updateSegmentCounts();
  renderMemberCards();
  renderKPIStrip();
  if(activeTabName!=='gantt'&&activeTabName!=='scrum'){
    populateAuditFilters();
    renderAuditTable();
    renderReworkLog();
  }
  renderCustomerKPI();
  /* Per-tab lazy rendering: only build the currently visible tab */
  if(activeTabName==='accuracy'){
    buildGrid('grid-accuracy',calcAccuracy,fmtPct,heatPct,tipAccuracy);
    renderTrend('trend-accuracy',calcAccuracy,'ETA Accuracy','#4f46e5',.9,'Target 90%',false,'accuracy');
  }
  if(activeTabName==='velocity'){
    buildGrid('grid-velocity',calcVelocity,fmtDays,heatDays,tipVelocity);
    renderTrend('trend-velocity',calcVelocity,'Execution Time','#b45309',28,'Target 28d',true,'velocity');
  }
  if(activeTabName==='reliability'){
    buildGrid('grid-reliability',calcReliability,fmtPct,heatPct,tipReliability);
    renderTrend('trend-reliability',calcReliability,'Reliability','#047857',.9,'Target 90%',false,'reliability');
  }
  if(activeTabName==='activity'){
    buildGrid('grid-activity',calcActivity,fmtCount,heatVol,tipActivity);
    renderTrend('trend-activity',calcActivity,'Task Volume','#4338ca',5,'Avg 5/week',false,'activity');
  }
  if(activeTabName==='scrum'){
    renderScrumCards();
  }
  if(activeTabName==='insights'){
    renderInsights();
  }
  /* Only render Gantt when its tab is active — expensive DOM rebuild */
  const ganttPanel=document.getElementById('panel-gantt');
  if(ganttPanel&&ganttPanel.classList.contains('active'))renderGantt();
}

/* ── Gantt Chart ─────────────────────────────────── */
const GT_DAY_W=6;
const gtCollapsed={};

function gtGetFiltered(){
  const gtPerson=document.getElementById('gtPerson').value;
  const view=document.getElementById('gtView').value;
  const customer=document.getElementById('gtCustomer').value;
  const demand=document.getElementById('gtDemand').value;
  const gtStatus=document.getElementById('gtStatus').value;
  const period=document.getElementById('gtPeriod').value;
  let cutoff=null;
  if(period!=='all'){const d=new Date();d.setMonth(d.getMonth()-(period==='1m'?1:period==='3m'?3:6));cutoff=d.toISOString().slice(0,10)}

  let activeCustomers=null;
  if(view==='implementing'){
    activeCustomers=new Set();
    RAW.forEach(r=>{
      if(['In Progress','In Review','Production QA','Ready to Deploy'].includes(r.status)&&r.customer)activeCustomers.add(r.customer);
    });
  }

  return RAW.filter(r=>{
    const s=r.startedAt||r.dateAdd||'';
    if(!s||s<'2025-01-01')return false;
    if(r.status==='Canceled')return false;
    const pf=gtPerson!=='ALL'?gtPerson:state.person;
    if(pf!=='ALL'&&r.tsa!==pf)return false;
    if(customer!=='ALL'&&r.customer!==customer)return false;
    if(demand!=='ALL'&&r.category!==demand)return false;
    if(gtStatus==='active'&&(r.status==='Done'||r.status==='Canceled'))return false;
    if(gtStatus!=='ALL'&&gtStatus!=='active'&&r.status!==gtStatus)return false;
    if(view==='implementing'&&activeCustomers&&!activeCustomers.has(r.customer))return false;
    const e=r.delivery||r.eta||'';
    if(cutoff&&(s||'9999')<cutoff&&(e||'9999')<cutoff)return false;
    return true;
  });
}

function gtBarCls(r){
  if(r.perf==='Blocked'||r.status==='B.B.C')return'gt-bar-blocked';
  if(r.status==='Done')return r.perf==='Late'?'gt-bar-late':'gt-bar-done';
  if(['In Progress','In Review','Production QA','Ready to Deploy','Paused'].includes(r.status))return'gt-bar-active';
  return'gt-bar-noeta';
}

function gtTipHtml(r){
  const cls=r.perf==='On Time'?'good':r.perf==='Late'?'bad':'mid';
  const s=r.startedAt||r.dateAdd,e=r.delivery||r.eta;
  const dur=(s&&e)?daysBetween(s,e):null;
  let h='<b>'+esc(r.focus||'')+'</b>'+(r.customer?' ['+esc(r.customer)+']':'')+'<br>';
  h+='<span style="color:#94a3b8">Person:</span> '+esc(r.tsa||'')+'<br>';
  h+='<span style="color:#94a3b8">Status:</span> <span class="tip-pct '+cls+'">'+esc(r.status||'')+'</span> · '+esc(r.perf||'')+'<br>';
  h+='<span style="color:#94a3b8">Start:</span> '+esc(s||'\u2014')+' · <span style="color:#94a3b8">ETA:</span> '+esc(r.eta||'\u2014')+' · <span style="color:#94a3b8">Done:</span> '+esc(r.delivery||'\u2014')+'<br>';
  if(dur!==null)h+='<span style="color:#94a3b8">Duration:</span> '+dur+'d<br>';
  if(r.originalEta&&(r.originalEta||'').slice(0,10)!==(r.eta||'').slice(0,10))h+='<span style="color:#818cf8;font-size:.85em">Original ETA: '+esc(r.originalEta)+' &rarr; Final: '+esc(r.eta||'\u2014')+'</span><br>';
  if((r.etaChanges||0)>0)h+='<span style="color:#fbbf24;font-size:.85em">ETA changed '+r.etaChanges+'x</span><br>';
  if(r.ticketId)h+='<span style="color:#94a3b8">Ticket:</span> '+esc(r.ticketId||'');
  return h;
}

function gtToggleGroup(el){
  el.classList.toggle('gt-open');
  const gid=el.dataset.gtgrp;
  if(!gid)return;
  gtCollapsed[gid]=!el.classList.contains('gt-open');
  document.querySelectorAll('.gt-task[data-gtgrp="'+gid+'"]').forEach(r=>r.classList.toggle('gt-hidden'));
}

function renderGantt(){
  const data=gtGetFiltered();
  const todayStr=new Date().toISOString().slice(0,10);

  function pd(s){if(!s||s.length<10)return null;return new Date(s.slice(0,10)+'T12:00:00Z')}
  function db(a,b){return Math.round((b-a)/864e5)}

  /* Date range */
  let minD=todayStr,maxD=todayStr;
  data.forEach(r=>{
    const s=r.startedAt||r.dateAdd||'';
    const e=r.delivery||r.eta||s;
    if(s&&s<minD)minD=s;if(e&&e>maxD)maxD=e;if(s&&s>maxD)maxD=s;
  });
  const sd=pd(minD),ed=pd(maxD);
  if(!sd||!ed){document.getElementById('ganttCanvas').innerHTML='<p style="padding:20px;color:var(--dim)">No data for Gantt chart.</p>';return}
  sd.setDate(sd.getDate()-5);ed.setDate(ed.getDate()+10);
  const totalDays=db(sd,ed)+1;

  /* Build day index */
  const days=[];
  for(let i=0;i<totalDays;i++){const d=new Date(sd);d.setDate(d.getDate()+i);days.push(d)}
  function dayIdx(dateStr){const d=pd(dateStr);if(!d)return-1;return db(sd,d)}

  /* Group by customer */
  const groups={};
  data.forEach(r=>{const c=r.customer||'No Customer';if(!groups[c])groups[c]=[];groups[c].push(r)});
  const sortedGroups=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length);

  /* Month spans */
  const mNames=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const months=[];let curM=-1,curY=-1,curCount=0;
  days.forEach(d=>{
    if(d.getMonth()!==curM||d.getFullYear()!==curY){
      if(curCount>0)months.push({label:mNames[curM]+' '+curY,days:curCount});
      curM=d.getMonth();curY=d.getFullYear();curCount=0;
    }
    curCount++;
  });
  if(curCount>0)months.push({label:mNames[curM]+' '+curY,days:curCount});

  /* Month header */
  let html='<div class="gt-months"><div class="gt-label-col"><span>Customer / Task</span></div>';
  months.forEach(m=>{html+='<div class="gt-month-cell" style="min-width:'+m.days*GT_DAY_W+'px;max-width:'+m.days*GT_DAY_W+'px">'+m.label+'</div>'});
  html+='</div>';

  /* Day header */
  html+='<div class="gt-header"><div class="gt-label-col"><span></span></div><div class="gt-days">';
  days.forEach(d=>{
    const ds=d.toISOString().slice(0,10);
    const dow=d.getDay();const isWe=dow===0||dow===6;const isMs=d.getDate()===1;const isToday=ds===todayStr;
    let cls=isWe?'gt-day gt-weekend':'gt-day';
    if(isMs)cls+=' gt-month-start';if(isToday)cls+=' gt-today-col';
    const label=(d.getDate()%7===1||d.getDate()===1)?d.getDate():'';
    html+='<div class="'+cls+'" style="min-width:'+GT_DAY_W+'px;max-width:'+GT_DAY_W+'px">'+label+'</div>';
  });
  html+='</div></div>';

  /* Month divider positions */
  const monthDividers=[];
  days.forEach((d,i)=>{if(d.getDate()===1)monthDividers.push(i)});
  function mLines(){return monthDividers.map(i=>'<div class="gt-month-line" style="left:'+i*GT_DAY_W+'px"></div>').join('')}

  /* Groups */
  sortedGroups.forEach(([cust,tasks])=>{
    tasks.sort((a,b)=>(a.startedAt||a.dateAdd||'z').localeCompare(b.startedAt||b.dateAdd||'z'));

    const done=tasks.filter(t=>t.status==='Done').length;
    const active=tasks.filter(t=>['In Progress','In Review','Todo','Paused','Production QA'].includes(t.status)).length;
    const late=tasks.filter(t=>t.perf==='Late').length;
    const onTime=tasks.filter(t=>t.perf==='On Time').length;
    const tbd=tasks.filter(t=>!t.eta&&t.status!=='Done'&&t.status!=='Canceled').length;

    /* Summary bar range */
    let gMin=null,gMax=null;
    tasks.forEach(t=>{
      const s=t.startedAt||t.dateAdd||'';const e=t.delivery||t.eta||s;
      if(s&&(!gMin||s<gMin))gMin=s;if(e&&(!gMax||e>gMax))gMax=e;
    });
    const gStartIdx=dayIdx(gMin);const gEndIdx=dayIdx(gMax);
    const gLen=Math.max(1,gEndIdx-gStartIdx+1);

    const gid='gt_'+cust.replace(/[^a-zA-Z0-9]/g,'_');
    const isOpen=!gtCollapsed[gid];

    html+='<div class="gt-row gt-group'+(isOpen?' gt-open':'')+'" data-gtgrp="'+gid+'" onclick="gtToggleGroup(this)">';
    html+='<div class="gt-label">';
    html+='<span class="gt-arrow">&#9654;</span>';
    html+='<span>'+esc(cust)+'</span>';
    html+='<span class="gt-count">'+tasks.length+'</span>';
    html+='<div class="gt-badges">';
    if(onTime)html+='<span class="gt-badge" style="background:#d1fae5;color:#065f46">'+onTime+' ok</span>';
    if(late)html+='<span class="gt-badge" style="background:#fee2e2;color:#991b1b">'+late+' late</span>';
    if(active)html+='<span class="gt-badge" style="background:#dbeafe;color:#1e40af">'+active+' active</span>';
    if(tbd)html+='<span class="gt-badge" style="background:#bfdbfe;color:#1e3a8a">'+tbd+' TBD</span>';
    html+='</div></div>';

    /* Summary bar area */
    html+='<div class="gt-bars" style="min-width:'+totalDays*GT_DAY_W+'px">';
    html+=mLines();
    if(gStartIdx>=0)html+='<div class="gt-bar gt-bar-summary" style="left:'+gStartIdx*GT_DAY_W+'px;width:'+gLen*GT_DAY_W+'px"></div>';
    const tIdx=dayIdx(todayStr);
    if(tIdx>=0&&tIdx<totalDays)html+='<div class="gt-today-marker" style="left:'+tIdx*GT_DAY_W+'px"></div>';
    html+='</div></div>';

    /* Task rows */
    let lastPerson='';
    tasks.sort((a,b)=>{const pc=(a.tsa||'').localeCompare(b.tsa||'');return pc!==0?pc:(a.startedAt||a.dateAdd||'z').localeCompare(b.startedAt||b.dateAdd||'z')});
    tasks.forEach(t=>{
      const s=t.startedAt||t.dateAdd||'';const e=t.delivery||t.eta||'';
      let si=dayIdx(s),ei=dayIdx(e||s);
      si=Math.max(0,Math.min(si,totalDays-1));ei=Math.max(0,Math.min(ei,totalDays-1));
      const len=Math.max(1,ei-si+1);
      const cls=gtBarCls(t);
      const isProj=!t.delivery&&t.eta&&t.status!=='Done';
      const bCls=cls+(isProj?' gt-bar-projected':'');
      const tHtml=gtTipHtml(t);
      const focusTxt=t.focus||'';

      html+='<div class="gt-row gt-task'+(isOpen?'':' gt-hidden')+'" data-gtgrp="'+gid+'">';
      html+='<div class="gt-label">';
      if(t.ticketUrl&&t.ticketUrl.startsWith('http'))html+='<a href="'+esc(t.ticketUrl)+'" target="_blank">'+esc(t.ticketId||'')+'</a>';
      else if(t.ticketId)html+='<span>'+esc(t.ticketId)+'</span>';
      html+='<span class="gt-tname" title="'+esc(focusTxt)+'">'+esc(focusTxt.length>35?focusTxt.slice(0,33)+'...':focusTxt)+'</span>';
      const showPerson=(t.tsa||'')!==lastPerson;lastPerson=t.tsa||'';
      if(showPerson)html+='<span class="gt-person">'+esc(t.tsa||'')+'</span>';
      html+='</div>';

      html+='<div class="gt-bars" style="min-width:'+totalDays*GT_DAY_W+'px">';
      html+=mLines();
      if(si<=totalDays&&ei>=0){
        html+='<div class="gt-bar '+bCls+'" style="left:'+si*GT_DAY_W+'px;width:'+len*GT_DAY_W+'px" onmouseenter="showTip(event,this.dataset.tip)" onmousemove="showTip(event,this.dataset.tip)" onmouseleave="hideTip()" data-tip="'+esc(tHtml)+'"></div>';
      }
      html+='</div></div>';
    });
  });

  document.getElementById('ganttCanvas').innerHTML=html;

  /* Stats */
  const doneC=data.filter(r=>r.status==='Done').length;
  const activeC=data.filter(r=>['In Progress','In Review','Todo','Paused'].includes(r.status)).length;
  document.getElementById('gtStats').innerHTML=data.length+' tasks · '+doneC+' done · '+activeC+' active · '+sortedGroups.length+' customers';

  /* Scroll listener for hiding tooltip */
  const wrap=document.getElementById('ganttWrap');
  wrap.removeEventListener('scroll',hideTip);
  wrap.addEventListener('scroll',hideTip);
}

/* Gantt: populate Customer filter dynamically + Status filter */
(function(){
  const gtCustEl=document.getElementById('gtCustomer');
  const gtStatusEl=document.getElementById('gtStatus');
  const gtPersonEl=document.getElementById('gtPerson');
  if(gtPersonEl){
    PEOPLE_ALL.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;gtPersonEl.appendChild(o)});
  }
  if(gtCustEl){
    const custs=[...new Set(RAW.map(r=>r.customer).filter(Boolean))].sort();
    custs.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;gtCustEl.appendChild(o)});
  }
  if(gtStatusEl){
    const sts=[...new Set(RAW.map(r=>r.status).filter(Boolean))].sort();
    sts.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;gtStatusEl.appendChild(o)});
  }
})();

/* Gantt-specific filter change handlers */
['gtPerson','gtView','gtPeriod','gtCustomer','gtDemand','gtStatus'].forEach(id=>{
  const el=document.getElementById(id);
  if(el)el.addEventListener('change',function(){renderGantt()});
});

/* KPI team member IDs — global, used by Scrum and Insights */
const KPI_IDS=new Set(__KPI_IDS__);

function renderScrumCards(){
  const todayStr=new Date().toISOString().slice(0,10);
  const today=new Date(todayStr);

  /* Split: active (In Progress/In Review/Paused/Todo) + completed today — respects person filter */
  const pf=state.person;
  const SCRUM_ACTIVE=['In Progress','In Review','Paused','Todo','Production QA','Blocked','Refinement','Ready to Deploy','Triage'];
  const active=RAW.filter(r=>r.source==='linear'&&SCRUM_ACTIVE.includes(r.status)&&(pf==='ALL'||r.tsa===pf));
  /* Done in last 48h — on weekends (Sat/Sun) extend back to Friday */
  const todayDate=new Date(todayStr+'T12:00:00');
  const dow=todayDate.getDay();
  const lookbackDays=dow===1?3:dow===0?2:dow===6?1:2; /* Mon→Fri(3d), Sun→Fri(2d), Sat→Fri(1d), weekday→48h(2d) */
  const cutoffDate=new Date(todayDate);cutoffDate.setDate(cutoffDate.getDate()-lookbackDays);
  const cutoffStr=cutoffDate.toISOString().slice(0,10);
  const doneRecent=RAW.filter(r=>r.source==='linear'&&r.status==='Done'&&r.delivery&&r.delivery.slice(0,10)>=cutoffStr&&(pf==='ALL'||r.tsa===pf));

  const people=[...new Set([...active,...doneRecent].map(r=>r.tsa))].sort();
  const el=document.getElementById('scrumCards');
  if(!el)return;

  const fmtD=d=>{if(!d||d.length<10)return'TBD';const p=d.slice(5,10).split('-');return p[0]+'/'+p[1]};

  function taskSignal(t){
    if(t.perf==='Blocked'||t.status==='B.B.C')return'blocked';
    if(t.status==='Paused'||t.status==='On Hold')return'paused';
    if(t.rework==='yes')return'rework';
    /* Todo/Backlog/Triage/Refinement with past ETA = overdue (gray) — not actively at risk */
    if(['Todo','Backlog','Triage','Refinement'].includes(t.status)){
      if(t.eta){try{if(new Date(t.eta)<today)return'overdue'}catch(e){}}
      return'ontrack';
    }
    if(t.perf==='Late')return'atrisk';
    if(t.eta&&t.status!=='Done'){
      try{const eta=new Date(t.eta);if(eta<today)return'atrisk'}catch(e){}
    }
    return'ontrack';
  }
  function slackEmoji(sig){return sig==='blocked'?':red_circle:':sig==='rework'?':recycle:':sig==='atrisk'?':large_yellow_circle:':sig==='overdue'?':white_circle:':sig==='paused'?':pause_button:':':large_green_circle:'}
  function htmlDot(sig){return sig==='blocked'?'🔴':sig==='rework'?'♻️':sig==='atrisk'?'🟡':sig==='overdue'?'⚪':sig==='paused'?'⏸':'🟢'}
  function htmlCls(sig){return sig==='blocked'?'sc-r':sig==='rework'?'sc-y':sig==='atrisk'?'sc-y':sig==='overdue'?'':sig==='paused'?'':'sc-g'}

  /* Needs-response detection: last actor is NOT on our team and ticket is active */
  function needsResponse(t){
    /* Use lastActorId from history, fallback to createdById */
    const actorId=t.lastActorId||t.createdById||'';
    if(!actorId)return false;
    if(KPI_IDS.has(actorId))return false;
    /* Only flag active statuses updated in last 7 days */
    if(!['In Progress','In Review'].includes(t.status))return false;
    if(!t.updatedAt)return false;
    const updated=(t.updatedAt||'').slice(0,10);
    const cutoff=new Date(today);cutoff.setDate(cutoff.getDate()-7);
    if(updated<cutoff.toISOString().slice(0,10))return false;
    return true;
  }

  /* #2: Age-in-status helper */
  function ageDays(dateStr){if(!dateStr)return 0;try{return Math.max(0,Math.floor((today-new Date(dateStr))/864e5))}catch(e){return 0}}
  function ageLabel(t){
    if(t.status==='In Review'&&t.inReviewDate){const d=ageDays(t.inReviewDate);return d>0?` · ${d}d in review`:'';}
    if(t.status==='In Progress'&&t.startedAt){const d=ageDays(t.startedAt);return d>0?` · ${d}d`:'';}
    if(t.status==='Todo'&&t.dateAdd){const d=ageDays(t.dateAdd);return d>14?` · stale ${d}d`:` · ${ageDays(t.dateAdd)}d`;}
    /* Fallback: any other status — use statusChangedAt, then updatedAt, then dateAdd */
    const fallback=t.statusChangedAt||t.updatedAt||t.dateAdd;
    if(fallback){const d=ageDays(fallback);return d>0?` · ${d}d`:'';}
    return'';
  }
  function ageColor(t){
    let d=0;
    if(t.status==='In Review'&&t.inReviewDate)d=ageDays(t.inReviewDate);
    else if(t.status==='In Progress'&&t.startedAt)d=ageDays(t.startedAt);
    else if(t.status==='Todo'&&t.dateAdd)d=ageDays(t.dateAdd);
    else{const fb=t.statusChangedAt||t.updatedAt||t.dateAdd;if(fb)d=ageDays(fb);}
    if(d>14)return'#ef4444';if(d>7)return'#d97706';return'';
  }

  /* Stale Todo detection (>14d since dateAdd) */
  function isStaleTodo(t){
    return t.status==='Todo'&&t.dateAdd&&ageDays(t.dateAdd)>14;
  }

  /* #1: ETA drift helper — compare dates by first 10 chars (YYYY-MM-DD) to avoid timestamp mismatch */
  function sameDate(a,b){return(a||'').slice(0,10)===(b||'').slice(0,10)}
  /* Only show drift when ETA was PUSHED BACK (delayed). Brought forward = merit, no flag */
  function etaWasDelayed(t){return t.etaChanges&&t.etaChanges>0&&t.originalEta&&!sameDate(t.originalEta,t.eta)&&(t.eta||'').slice(0,10)>(t.originalEta||'').slice(0,10)}
  function etaDriftHtml(t){
    if(!etaWasDelayed(t))return'';
    return`<div class="sc-eta-drift">ETA: <span style="text-decoration:line-through">${fmtD(t.originalEta)}</span> <span style="color:#ef4444;font-weight:600">\u2192 ${fmtD(t.eta)} (delayed ${t.etaChanges}x)</span></div>`;
  }
  function etaDriftSlack(t){
    if(!etaWasDelayed(t))return'';
    return`\n    ETA: ${fmtD(t.originalEta)} \u2192 ${fmtD(t.eta)} (delayed ${t.etaChanges}x)`;
  }

  function cleanName(focus,cust){
    let s=focus;
    s=s.replace(/^\[.*?\]\s*/,'');
    if(cust&&s.toLowerCase().startsWith(cust.toLowerCase()))s=s.slice(cust.length).replace(/^\s*[-\u2013\u2014:]\s*/,'');
    return s.slice(0,55)||focus.slice(0,55);
  }

  const cards=people.map(person=>{
    const myActive=active.filter(r=>r.tsa===person);
    const myDone=doneRecent.filter(r=>r.tsa===person);

    /* Group active by customer */
    const byCust={};
    myActive.forEach(t=>{
      const c=t.customer||'General';
      if(!byCust[c])byCust[c]=[];
      byCust[c].push(t);
    });
    /* Group done today by customer */
    const doneByCust={};
    myDone.forEach(t=>{
      const c=t.customer||'General';
      if(!doneByCust[c])doneByCust[c]=[];
      doneByCust[c].push(t);
    });

    let green=0,yellow=0,red=0,overdue=0;
    const tbd=myActive.filter(t=>!t.eta&&t.status!=='Paused').length;
    let needsResponseCount=0;
    myActive.forEach(t=>{
      const sig=taskSignal(t);
      if(sig==='ontrack')green++;
      else if(sig==='overdue')overdue++;
      else if(sig==='paused'){/* counted separately via pausedCount */}
      else if(sig==='atrisk')yellow++;
      else if(sig==='rework'){/* counted separately via reworkCount */}
      else if(sig==='blocked')red++;
      if(needsResponse(t))needsResponseCount++;
    });

    /* Build Slack text */
    let text=`[Daily Agenda \u2013 ${todayStr}]\n`;
    /* Sort: TBD (no ETA) first, then by ETA oldest→newest */
    const sortTasks=arr=>arr.sort((a,b)=>{if(!a.eta&&b.eta)return-1;if(a.eta&&!b.eta)return 1;return(a.eta||'').localeCompare(b.eta||'')});
    /* Sort customers by urgency: most at-risk/blocked first, then by task count */
    const custKeys=Object.keys(byCust).sort((a,b)=>{
      const urgA=byCust[a].filter(t=>{const s=taskSignal(t);return s==='atrisk'||s==='blocked'}).length;
      const urgB=byCust[b].filter(t=>{const s=taskSignal(t);return s==='atrisk'||s==='blocked'}).length;
      if(urgB!==urgA)return urgB-urgA;
      return byCust[b].length-byCust[a].length;
    });
    /* #5: Split active vs paused for Slack */
    const activeCusts={};const pausedList=[];
    custKeys.forEach(cust=>{
      const tasks=byCust[cust]||[];
      const act=tasks.filter(t=>t.status!=='Paused');
      const pau=tasks.filter(t=>t.status==='Paused');
      if(act.length)activeCusts[cust]=act;
      pau.forEach(p=>pausedList.push({...p,_cust:cust}));
    });
    Object.keys(activeCusts).sort((a,b)=>{
      const urgA=activeCusts[a].filter(t=>{const s=taskSignal(t);return s==='atrisk'||s==='blocked'||s==='rework'}).length;
      const urgB=activeCusts[b].filter(t=>{const s=taskSignal(t);return s==='atrisk'||s==='blocked'||s==='rework'}).length;
      if(urgB!==urgA)return urgB-urgA;return activeCusts[b].length-activeCusts[a].length;
    }).forEach(cust=>{
      text+=`\n${cust}\n`;
      sortTasks(activeCusts[cust]).forEach(t=>{
        const name=cleanName(t.focus,cust);
        const age=ageLabel(t);
        const drift=etaDriftSlack(t);
        const tid=t.ticketId?t.ticketId+' ':'';
        text+=`  :black_small_square: [${t.status}${age}] ${tid}${name} ETA:${fmtD(t.eta)} ${slackEmoji(taskSignal(t))}${drift}\n`;
      });
    });
    if(pausedList.length>0){
      text+=`\n\u2014\u2014\u2014 Paused \u2014\u2014\u2014\n`;
      pausedList.forEach(t=>{
        const name=cleanName(t.focus,t._cust);
        text+=`  :pause_button: ${t.ticketId||''} ${name} (${t._cust}) ETA:${fmtD(t.eta)}\n`;
      });
    }
    /* Done today section */
    const allDoneCusts=Object.keys(doneByCust).sort();
    if(allDoneCusts.length>0){
      text+=`\n\u2014\u2014\u2014\u2014 Recently Completed \u2014\u2014\u2014\u2014\n`;
      allDoneCusts.forEach(cust=>{
        doneByCust[cust].forEach(t=>{
          const name=cleanName(t.focus,cust);
          text+=`  :white_check_mark: Done: ${name} (${cust})\n`;
        });
      });
    }

    /* Build HTML preview */
    let html='';
    /* Separate active from paused */
    const htmlActiveCusts={};const htmlPaused=[];
    custKeys.forEach(cust=>{
      const tasks=byCust[cust]||[];
      const act=tasks.filter(t=>t.status!=='Paused');
      const pau=tasks.filter(t=>t.status==='Paused');
      if(act.length)htmlActiveCusts[cust]=act;
      pau.forEach(p=>htmlPaused.push({...p,_cust:cust}));
    });

    /* Unique collapse ID counter */
    let collapseIdx=0;

    /* Active tasks by customer */
    Object.keys(htmlActiveCusts).sort((a,b)=>{
      const urgA=htmlActiveCusts[a].filter(t=>{const s=taskSignal(t);return s==='atrisk'||s==='blocked'||s==='rework'}).length;
      const urgB=htmlActiveCusts[b].filter(t=>{const s=taskSignal(t);return s==='atrisk'||s==='blocked'||s==='rework'}).length;
      if(urgB!==urgA)return urgB-urgA;return htmlActiveCusts[b].length-htmlActiveCusts[a].length;
    }).forEach(cust=>{
      /* Milestone callout */
      const milestones=[...new Set(htmlActiveCusts[cust].map(t=>t.milestone).filter(Boolean))];
      const msBadge=milestones.length?` <span style="color:#6366f1;font-size:.72em;font-weight:400">[${esc(milestones[0])}]</span>`:'';
      html+=`<div class="sc-customer">${esc(cust)}${msBadge}</div>`;

      const sorted=sortTasks(htmlActiveCusts[cust]);
      /* Stale-task collapse: if >3 stale Todo items for this customer, show first 3 then collapse */
      const staleTodos=sorted.filter(t=>isStaleTodo(t));
      const nonStale=sorted.filter(t=>!isStaleTodo(t));
      const showStale=staleTodos.slice(0,3);
      const hiddenStale=staleTodos.slice(3);

      /* Render non-stale tasks first, then stale */
      const renderTask=(t)=>{
        const sig=taskSignal(t);
        const tid=t.ticketId?`<a href="${esc(t.ticketUrl||'')}" target="_blank" style="color:#818cf8;text-decoration:none;font-size:.85em">${esc(t.ticketId)}</a> `:'';
        const name=cleanName(t.focus,cust);
        const age=ageLabel(t);
        const ac=ageColor(t);
        const statusColor=t.status==='In Progress'?'#3b82f6':t.status==='In Review'?'#8b5cf6':t.status==='Todo'?'#94a3b8':t.status==='Rework'?'#f59e0b':'#6b7280';
        const statusStyle=ac?`color:${ac}`:`color:${statusColor}`;
        const rwTag=t.rework==='yes'?`<span style="color:#f59e0b;font-size:.78em;font-weight:700">\u267b\ufe0f </span>`:'';
        /* Needs-response badge */
        const nrBadge=needsResponse(t)?`<span class="sc-needs-response">\u26a0 needs response</span>`:'';
        /* ETA on main line (no drift) or simple ETA */
        const hasDrift=etaWasDelayed(t);
        const etaInline=hasDrift?'':`<span style="color:var(--dim);font-size:.82em"> ETA:${fmtD(t.eta)}</span>`;
        const reviewNote=t.reassignedInReview?` <span style="color:#94a3b8;font-size:.72em">\u21a9 review</span>`:'';
        /* Compute filter tags for badge click filtering */
        const filterTags=[sig];
        if(!t.eta)filterTags.push('noeta');
        if(needsResponse(t))filterTags.push('needsresponse');
        if(t.status==='Paused')filterTags.push('paused');
        let taskHtml=`<div class="sc-task" data-tags="${filterTags.join(',')}">${rwTag}<span style="${statusStyle};font-size:.8em;font-weight:600">[${esc(t.status)}${age}]</span> ${tid}${esc(name)}${etaInline}${nrBadge}${reviewNote} <span class="${htmlCls(sig)}">${htmlDot(sig)}</span></div>`;
        /* ETA drift on second line */
        if(hasDrift)taskHtml+=etaDriftHtml(t);
        return taskHtml;
      };

      nonStale.forEach(t=>{html+=renderTask(t)});
      showStale.forEach(t=>{html+=renderTask(t)});

      /* Collapsed stale todos */
      if(hiddenStale.length>0){
        const cid=`stale_${person}_${collapseIdx++}`;
        const oldestDays=Math.max(...hiddenStale.map(t=>ageDays(t.dateAdd)));
        html+=`<div class="sc-stale-collapse" onclick="(function(e){var d=document.getElementById('${cid}');var a=e.target||e.srcElement;if(d.style.display==='none'){d.style.display='block';a.textContent='\u25be '+a.textContent.slice(2)}else{d.style.display='none';a.textContent='\u25b8 '+a.textContent.slice(2)}})(event)">\u25b8 ${hiddenStale.length} more stale Todo tickets (oldest: ${oldestDays}d)</div>`;
        html+=`<div id="${cid}" style="display:none">`;
        hiddenStale.forEach(t=>{html+=renderTask(t)});
        html+=`</div>`;
      }
    });
    /* Paused section */
    if(htmlPaused.length>0){
      html+=`<div style="border-top:1px dashed #94a3b8;margin:8px 0 4px;position:relative"><span style="position:absolute;top:-8px;left:12px;background:var(--white);padding:0 6px;font-size:.65em;font-weight:600;color:#94a3b8;text-transform:uppercase">Paused</span></div>`;
      htmlPaused.forEach(t=>{
        const tid=t.ticketId?`<a href="${esc(t.ticketUrl||'')}" target="_blank" style="color:#818cf8;text-decoration:none;font-size:.85em">${esc(t.ticketId)}</a> `:'';
        const name=cleanName(t.focus,t._cust);
        html+=`<div class="sc-task" data-tags="paused" style="opacity:.5">\u23f8 ${tid}${esc(name)} <span style="color:var(--dim)">(${esc(t._cust)})</span></div>`;
      });
    }
    /* Done today with strikethrough line */
    if(allDoneCusts.length>0){
      html+=`<div style="border-top:2px dashed var(--green);margin:10px 0 6px;position:relative"><span style="position:absolute;top:-9px;left:12px;background:var(--white);padding:0 8px;font-size:.7em;font-weight:700;color:var(--green);text-transform:uppercase">Recently Completed</span></div>`;
      allDoneCusts.forEach(cust=>{
        doneByCust[cust].forEach(t=>{
          const tid=t.ticketId?`<a href="${esc(t.ticketUrl||'')}" target="_blank" style="color:#818cf8;text-decoration:none;font-size:.85em">${esc(t.ticketId)}</a> `:'';
          const name=cleanName(t.focus,cust);
          const delDate=t.deliveryDate||t.delivery;
          const rvDelay=t.reviewerDelay&&t.reviewerDelay>2?` <span style="color:#d97706;font-size:.78em">review ${t.reviewerDelay}d</span>`:'';
          html+=`<div class="sc-task" data-tags="done" style="text-decoration:line-through;opacity:.6">\u2705 ${tid}${esc(name)} <span style="color:var(--dim)">(${esc(cust)}) ${fmtD(delDate)}</span>${rvDelay}</div>`;
        });
      });
    }

    const reworkCount=myActive.filter(t=>t.rework==='yes').length;
    const pausedCount=myActive.filter(t=>t.status==='Paused').length;
    return{person,active:myActive.length,done:myDone.length,green,yellow,red,overdue,tbd,reworkCount,pausedCount,needsResponseCount,text,html};
  });

  el.innerHTML=cards.map(c=>`
    <div class="scrum-card" onclick="copyScrumCard(this)" data-scrum="${esc(c.text).replace(/"/g,'&quot;')}">
      <div class="sc-header">
        <span class="sc-name">${c.person}</span>
        <div class="sc-stats">
          ${c.done?`<span style="background:#059669;color:#fff;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'done')">${c.done} done</span>`:''}
          <span style="background:#065f46;color:#a7f3d0;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'ontrack')">${c.green} on track</span>
          ${c.yellow?`<span style="background:#92400e;color:#fde68a;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'atrisk')">${c.yellow} at risk</span>`:''}
          ${c.reworkCount?`<span style="background:#92400e;color:#fde68a;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'rework')">${c.reworkCount} rework</span>`:''}
          ${c.red?`<span style="background:#991b1b;color:#fecaca;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'blocked')">${c.red} blocked</span>`:''}
          ${c.needsResponseCount?`<span style="background:#c2410c;color:#fff;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'needsresponse')">${c.needsResponseCount} needs response</span>`:''}
          ${c.tbd?`<span style="background:#1e3a8a;color:#bfdbfe;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'noeta')">${c.tbd} no eta</span>`:''}
          ${c.overdue?`<span style="background:#374151;color:#d1d5db;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'overdue')">${c.overdue} overdue</span>`:''}
          ${c.pausedCount?`<span style="background:#374151;color:#9ca3af;cursor:pointer" onclick="event.stopPropagation();scFilterCard(this,'paused')">${c.pausedCount} paused</span>`:''}
        </div>
      </div>
      <div class="sc-body">${c.html}</div>
      <div class="sc-copy-hint">Click to copy Slack-ready text</div>
    </div>
  `).join('');

  /* ── Team Report (integrated view) ──────────────── */
  const trEl=document.getElementById('teamReport');
  const trCards=cards;
  if(trEl&&trCards.length>1){
    const totActive=trCards.reduce((s,c)=>s+c.active,0);
    const totDone=trCards.reduce((s,c)=>s+c.done,0);
    const totGreen=trCards.reduce((s,c)=>s+c.green,0);
    const totYellow=trCards.reduce((s,c)=>s+c.yellow,0);
    const totRed=trCards.reduce((s,c)=>s+c.red,0);
    const totOverdue=trCards.reduce((s,c)=>s+c.overdue,0);
    const totTbd=trCards.reduce((s,c)=>s+c.tbd,0);
    const totNR=trCards.reduce((s,c)=>s+c.needsResponseCount,0);
    const totRework=trCards.reduce((s,c)=>s+c.reworkCount,0);
    const totPaused=trCards.reduce((s,c)=>s+c.pausedCount,0);

    /* ── KPI calculations for Slack report ── */
    const trPersons=new Set(trCards.map(c=>c.person));
    const kpiRows=RAW.filter(r=>trPersons.has(r.tsa));
    const pctR=(n,d)=>d>0?Math.round(n/d*100):null;
    const trendEmoji=v=>v>5?':chart_with_upwards_trend:':v<-5?':chart_with_downwards_trend:':':arrow_right:';

    const allOt=kpiRows.filter(r=>r.perf==='On Time').length;
    const allLt=kpiRows.filter(r=>r.perf==='Late').length;
    const allMeas=allOt+allLt;
    const allAcc=pctR(allOt,allMeas);
    const oOt=kpiRows.filter(r=>r.perf==='On Time'&&r.retroactiveEta!=='yes').length;
    const oLt=kpiRows.filter(r=>r.perf==='Late'&&r.retroactiveEta!=='yes').length;
    const oMeas=oOt+oLt;
    const oAcc=pctR(oOt,oMeas);
    const gapPct=(allAcc!==null&&oAcc!==null)?allAcc-oAcc:0;

    let slk=`:bar_chart: *TSA Team Report \u2014 Raccoons*\n:calendar: ${todayStr}\n\n`;
    slk+=`:dart: *Overall*\nAccuracy: ${allAcc!==null?allAcc+'%':'\u2014'} (${allOt}/${allMeas}) | Organic: ${oAcc!==null?oAcc+'%':'\u2014'} (${oOt}/${oMeas}) | Gap: +${gapPct}%\n\n`;

    slk+=`:busts_in_silhouette: *Per Person*\n`;
    const perPerson=[...trPersons].sort();
    perPerson.forEach(p=>{
      const pr=kpiRows.filter(r=>r.tsa===p);
      const pot=pr.filter(r=>r.perf==='On Time').length;
      const plt=pr.filter(r=>r.perf==='Late').length;
      const pm=pot+plt;
      const pacc=pctR(pot,pm);
      const poOt=pr.filter(r=>r.perf==='On Time'&&r.retroactiveEta!=='yes').length;
      const poLt=pr.filter(r=>r.perf==='Late'&&r.retroactiveEta!=='yes').length;
      const pom=poOt+poLt;
      const poAcc=pctR(poOt,pom);
      const pg=(pacc!==null&&poAcc!==null)?pacc-poAcc:0;
      slk+=`${p} \u2014 ${pacc!==null?pacc+'%':'\u2014'} | organic ${poAcc!==null?poAcc+'%':'\u2014'} | +${pg}%\n`;
    });

    const lateTickets=kpiRows.filter(r=>r.perf==='Late').sort((a,b)=>(a.tsa||'').localeCompare(b.tsa||''));
    if(lateTickets.length>0){
      slk+=`\n:rotating_light: *Late Tickets (${lateTickets.length})*\n`;
      lateTickets.forEach(t=>{
        const tid=t.ticketId?t.ticketId+' ':'';
        const name=(t.focus||'').slice(0,60);
        slk+=`:red_circle: ${tid}${name} \u2014 ${t.tsa} (ETA: ${fmtD(t.eta)})\n`;
      });
    }

    slk+=`\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n`;
    trCards.forEach(c=>{
      slk+=`:bust_in_silhouette: *${c.person}*\n`;
      slk+=c.text.split('\n').slice(1).join('\n')+'\n';
    });
    slk+=`\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n:traffic_light: *Legend*\n`;
    slk+=`:large_green_circle: On track\n`;
    slk+=`:large_yellow_circle: At risk (past ETA)\n`;
    slk+=`:red_circle: Blocked\n`;
    slk+=`:recycle: Rework\n`;
    slk+=`:white_circle: Overdue (not started)\n`;
    slk+=`:pause_button: Paused\n`;
    window._teamReportSlack=slk;

    let previewHtml='';
    trCards.forEach(c=>{
      previewHtml+=`<div class="tr-person-hdr">${esc(c.person)}</div>`;
      previewHtml+=`<div style="padding-left:4px">${c.html}</div>`;
    });

    trEl.innerHTML=`
      <div class="team-report" id="teamReportCard" onclick="copyTeamReport(event)" style="cursor:pointer">
        <div class="tr-header">
          <div class="tr-title">\ud83d\udcca Team Report \u2014 Raccoons</div>
          <button class="tr-btn" id="trCopyBtn" onclick="copyTeamReport(event)">\ud83d\udccb Copy All for Slack</button>
        </div>
        <div class="tr-body" id="trPreviewBody">${previewHtml}</div>
        <div style="text-align:center;padding:6px;font-size:.68em;color:rgba(255,255,255,.4);border-top:1px solid rgba(255,255,255,.08)">Click anywhere to copy Slack-ready text</div>
      </div>`;
  } else if(trEl){
    trEl.innerHTML='';
  }
}

function scFilterCard(badge,filterTag){
  const card=badge.closest('.scrum-card');
  if(!card)return;
  const tasks=card.querySelectorAll('.sc-task[data-tags]');
  const customers=card.querySelectorAll('.sc-customer');
  const sections=card.querySelectorAll('.sc-eta-drift,.sc-stale-collapse');
  /* Toggle: click same badge again → show all */
  const current=card.dataset.activeFilter||'';
  const isToggleOff=current===filterTag;
  card.dataset.activeFilter=isToggleOff?'':filterTag;
  /* Highlight active badge */
  card.querySelectorAll('.sc-stats span').forEach(s=>{s.style.opacity=isToggleOff||s===badge?'1':'.4'});
  if(isToggleOff){badge.style.opacity='1'}
  /* Expand any collapsed stale sections when filtering */
  if(!isToggleOff&&filterTag!=='all'){
    card.querySelectorAll('[id^="stale_"]').forEach(el=>{el.style.display=''});
  }
  /* Show/hide tasks */
  tasks.forEach(t=>{
    if(isToggleOff||filterTag==='all'){t.style.display='';return}
    const tags=(t.dataset.tags||'').split(',');
    t.style.display=tags.includes(filterTag)?'':'none';
  });
  /* Show/hide customer headers — hide if all tasks under them are hidden */
  customers.forEach(c=>{
    let next=c.nextElementSibling;let anyVisible=false;
    while(next&&!next.classList.contains('sc-customer')&&next.style){
      if(next.classList.contains('sc-task')&&next.style.display!=='none')anyVisible=true;
      next=next.nextElementSibling;
      if(!next||next.tagName==='DIV'&&next.style.borderTop)break;
    }
    c.style.display=(isToggleOff||filterTag==='all')?'':anyVisible?'':'none';
  });
  /* Hide section separators when filtering */
  sections.forEach(s=>{s.style.display=(isToggleOff||filterTag==='all')?'':'none'});
}

function copyScrumCard(el){
  const text=el.dataset.scrum.replace(/&quot;/g,'"').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&#39;/g,"'").replace(/&#96;/g,'`');
  function onOk(){
    el.classList.add('copied');
    const hint=el.querySelector('.sc-copy-hint');
    if(hint)hint.textContent='Copied!';
    setTimeout(()=>{el.classList.remove('copied');if(hint)hint.textContent='Click to copy Slack-ready text'},1500);
  }
  if(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext){
    navigator.clipboard.writeText(text).then(onOk).catch(()=>fallbackCopy(text,onOk));
  } else { fallbackCopy(text,onOk); }
}

function copyTeamReport(evt){
  if(evt)evt.stopPropagation();
  const text=window._teamReportSlack||'';
  if(!text)return;
  function onOk(){
    const btn=document.getElementById('trCopyBtn');
    if(btn){btn.classList.add('copied');btn.textContent='\u2705 Copied!';setTimeout(()=>{btn.classList.remove('copied');btn.textContent='\ud83d\udccb Copy All for Slack'},1800);}
    const card=document.getElementById('teamReportCard');
    if(card){card.style.borderColor='#059669';setTimeout(()=>{card.style.borderColor='#6366f1'},1800);}
  }
  if(navigator.clipboard&&navigator.clipboard.writeText&&window.isSecureContext){
    navigator.clipboard.writeText(text).then(onOk).catch(()=>fallbackCopy(text,onOk));
  } else { fallbackCopy(text,onOk); }
}
function fallbackCopy(text,cb){
  const ta=document.createElement('textarea');
  ta.value=text;ta.style.cssText='position:fixed;left:-9999px;top:0;opacity:0';
  document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');if(cb)cb()}catch(e){alert('Copy failed — please select and Ctrl+C manually')}
  document.body.removeChild(ta);
}

function renderReworkLog(){
  const data=getKPIFiltered();
  const reworkItems=data.filter(r=>r.rework==='yes');
  const el=document.getElementById('reworkLog');
  if(reworkItems.length===0){
    el.innerHTML='<div style="text-align:center;padding:20px 0;color:var(--dim)"><div style="font-size:1.5em;margin-bottom:8px">&#10003;</div><div style="font-size:.88em;font-weight:600">No rework flagged</div><div style="font-size:.78em;color:var(--light);margin-top:4px">When a ticket gets the <span style="background:#fef2f2;color:#dc2626;padding:1px 6px;border-radius:3px;font-weight:600;font-size:.85em">rework:implementation</span> label in Linear, it appears here.</div></div>';
    return;
  }
  let html='<table class="detail-table"><thead><tr><th>Person</th><th>Ticket</th><th>Task</th><th>Customer</th><th>Delivered</th><th>Status</th></tr></thead><tbody>';
  reworkItems.forEach(r=>{
    const link=r.ticketUrl?`<a href="${esc(r.ticketUrl)}" target="_blank" style="color:var(--accent);font-weight:600">${esc(r.ticketId||'—')}</a>`:(r.ticketId||'—');
    html+=`<tr><td>${esc(r.tsa)}</td><td>${link}</td><td>${esc(r.focus.slice(0,50))}</td><td>${esc(r.customer||'—')}</td><td>${r.delivery||'—'}</td><td><span style="color:var(--red);font-weight:600">Rework</span></td></tr>`;
  });
  html+='</tbody></table>';
  html+=`<div style="margin-top:10px;font-size:.72em;color:var(--dim)">${reworkItems.length} ticket${reworkItems.length>1?'s':''} flagged for rework out of ${data.filter(r=>r.status==='Done').length} delivered</div>`;
  el.innerHTML=html;
}

/* ── Insights Tab ──────────────────────────────────── */
function renderInsights(){
  const el=document.getElementById('insightsBody');
  if(!el)return;
  const todayStr=new Date().toISOString().slice(0,10);
  const today=new Date(todayStr);
  const pf=state.person;

  /* Use ALL data (no core-week restriction) but respect person + category filters */
  const cat=state.category;
  const allData=RAW.filter(r=>(pf==='ALL'||r.tsa===pf)&&(cat==='ALL'||r.category===cat));

  /* KPI_IDS is global — defined before renderScrumCards */

  function ageDays(dateStr){if(!dateStr)return 0;try{return Math.max(0,Math.floor((today-new Date(dateStr))/864e5))}catch(e){return 0}}
  function collapsible(id,title,bodyHtml){
    return '<div class="audit-section" style="margin-top:16px"><div class="audit-header collapse-toggle" onclick="this.classList.toggle(\'open\');var b=this.nextElementSibling;if(b)b.classList.toggle(\'open\')"><span class="toggle">&#9660;</span><h3>'+title+'</h3></div><div class="audit-body"><div style="padding:12px 16px;overflow-x:auto">'+bodyHtml+'</div></div></div>';
  }

  let html='';

  /* ── Section 1: Cross-Team Tickets ── */
  const crossTeam=allData.filter(r=>{
    if(!r.createdById||!r.assigneeId)return false;
    if(r.status==='Done')return false;
    return KPI_IDS.has(r.createdById)&&!KPI_IDS.has(r.assigneeId);
  }).sort((a,b)=>ageDays(b.dateAdd)-ageDays(a.dateAdd));

  let s1='<table class="audit-table"><thead><tr><th>Ticket</th><th>Title</th><th>Opened By</th><th>Assigned To</th><th>Customer</th><th>Status</th><th>ETA</th><th>Age</th></tr></thead><tbody>';
  if(crossTeam.length===0){
    s1+='<tr><td colspan="8" style="text-align:center;color:var(--dim);padding:20px">No cross-team tickets found</td></tr>';
  } else {
    crossTeam.forEach(r=>{
      const link=r.ticketUrl?'<a href="'+esc(r.ticketUrl)+'" target="_blank" style="color:var(--accent);font-weight:600">'+esc(r.ticketId||'--')+'</a>':esc(r.ticketId||'--');
      const title=(r.focus||'').length>50?esc(r.focus.slice(0,50))+'...':esc(r.focus||'--');
      const age=ageDays(r.dateAdd);
      const ageCls=age>30?'color:var(--red);font-weight:700':age>14?'color:var(--yellow);font-weight:600':'';
      s1+='<tr><td>'+link+'</td><td title="'+esc(r.focus||'')+'">'+title+'</td><td>'+esc(r.tsa||'--')+'</td><td>External</td><td>'+esc(r.customer||'--')+'</td><td>'+esc(r.status||'--')+'</td><td>'+esc(r.eta||'--')+'</td><td style="'+ageCls+'">'+age+'d</td></tr>';
    });
  }
  s1+='</tbody></table>';
  s1+='<div style="margin-top:8px;font-size:.72em;color:var(--dim)">'+crossTeam.length+' ticket'+(crossTeam.length!==1?'s':'')+' delegated to external teams</div>';
  html+=collapsible('ins-crossteam','Delegated Out &mdash; Tickets opened by TSA for other teams',s1);

  /* ── Section 2: Review Bottleneck ── */
  const reviewPeople=pf!=='ALL'?[pf]:PEOPLE_ALL;
  let s2='<table class="audit-table"><thead><tr><th>Person</th><th>Tickets Reviewed</th><th>Avg Review Time</th><th>Max Review Time</th><th>Currently In Review</th><th>Oldest In Review</th></tr></thead><tbody>';
  reviewPeople.forEach(person=>{
    const personData=RAW.filter(r=>r.tsa===person);
    const reviewed=personData.filter(r=>r.status==='Done'&&(r.reviewerDelay||0)>0);
    const delays=reviewed.map(r=>r.reviewerDelay).filter(d=>d>0);
    const avg=delays.length>0?delays.reduce((a,b)=>a+b,0)/delays.length:0;
    const max=delays.length>0?Math.max(...delays):0;
    const inReview=personData.filter(r=>r.status==='In Review');
    const oldestInReview=inReview.length>0?Math.max(...inReview.map(r=>ageDays(r.inReviewDate||r.startedAt||r.dateAdd))):0;
    const inRevCls=inReview.length>3?'color:var(--red);font-weight:700':inReview.length>1?'color:var(--yellow);font-weight:600':'';
    s2+='<tr><td style="font-weight:600">'+esc(person)+'</td><td>'+reviewed.length+'</td><td>'+avg.toFixed(1)+'d</td><td>'+max.toFixed(0)+'d</td><td style="'+inRevCls+'">'+inReview.length+'</td><td>'+(inReview.length>0?oldestInReview+'d':'--')+'</td></tr>';
  });
  s2+='</tbody></table>';
  html+=collapsible('ins-review','Review Pipeline &mdash; Time in review across team',s2);

  /* ── Section 3: Customer Response Time ── */
  const custMap={};
  allData.forEach(r=>{
    const c=r.customer||'(none)';
    if(!custMap[c])custMap[c]={done:[],waiting:[]};
    if(r.status==='Done'&&r.startedAt&&r.dateAdd){
      const delay=daysBetween(r.dateAdd,r.startedAt);
      if(delay!==null&&delay>=0)custMap[c].done.push(delay);
    }
    if(!r.startedAt&&['Todo','Backlog','Triage'].includes(r.status)){
      custMap[c].waiting.push(r);
    }
  });
  const custEntries=Object.entries(custMap).filter(([,v])=>v.done.length>0).map(([c,v])=>{
    const avg=v.done.reduce((a,b)=>a+b,0)/v.done.length;
    const fastest=Math.min(...v.done);
    const slowest=Math.max(...v.done);
    return{customer:c,tickets:v.done.length,avg,fastest,slowest,waiting:v.waiting.length};
  }).sort((a,b)=>b.avg-a.avg);

  let s3='<table class="audit-table"><thead><tr><th>Customer</th><th>Tickets</th><th>Avg Start Delay</th><th>Fastest</th><th>Slowest</th><th>Currently Waiting</th></tr></thead><tbody>';
  if(custEntries.length===0){
    s3+='<tr><td colspan="6" style="text-align:center;color:var(--dim);padding:20px">No data available</td></tr>';
  } else {
    custEntries.slice(0,25).forEach(e=>{
      const avgCls=e.avg>14?'color:var(--red);font-weight:700':e.avg>7?'color:var(--yellow);font-weight:600':'color:var(--green)';
      const waitCls=e.waiting>0?'color:var(--yellow);font-weight:600':'';
      s3+='<tr><td style="font-weight:600">'+esc(e.customer)+'</td><td>'+e.tickets+'</td><td style="'+avgCls+'">'+e.avg.toFixed(1)+'d</td><td>'+e.fastest+'d</td><td>'+e.slowest+'d</td><td style="'+waitCls+'">'+(e.waiting>0?e.waiting:'--')+'</td></tr>';
    });
  }
  s3+='</tbody></table>';
  html+=collapsible('ins-custresponse','Customer Response &mdash; Time from creation to start',s3);

  /* ── Section 4: Backlog Health ── */
  const BACKLOG_STATUSES=['Backlog','Todo','Triage'];
  const backlog=allData.filter(r=>BACKLOG_STATUSES.includes(r.status));
  const nowDate=new Date();
  const thisWeekStart=new Date(nowDate);thisWeekStart.setDate(thisWeekStart.getDate()-thisWeekStart.getDay());
  const thisMonthStart=new Date(nowDate.getFullYear(),nowDate.getMonth(),1);
  const createdThisWeek=backlog.filter(r=>r.dateAdd&&r.dateAdd.slice(0,10)>=thisWeekStart.toISOString().slice(0,10)).length;
  const createdThisMonth=backlog.filter(r=>r.dateAdd&&r.dateAdd.slice(0,10)>=thisMonthStart.toISOString().slice(0,10)).length;

  const buckets=[
    {label:'< 7 days',min:0,max:7,color:'#d1fae5',count:0},
    {label:'7-14 days',min:7,max:14,color:'#fef9c3',count:0},
    {label:'14-30 days',min:14,max:30,color:'#fed7aa',count:0},
    {label:'30-60 days',min:30,max:60,color:'#fecaca',count:0},
    {label:'> 60 days',min:60,max:9999,color:'#fca5a5',count:0}
  ];
  backlog.forEach(r=>{
    const age=ageDays(r.dateAdd);
    for(const b of buckets){if(age>=b.min&&age<b.max){b.count++;break}}
  });
  const staleCount=backlog.filter(r=>ageDays(r.dateAdd)>30).length;
  const staleRate=backlog.length>0?(staleCount/backlog.length*100).toFixed(0):0;
  const maxBucket=Math.max(1,...buckets.map(b=>b.count));

  let s4='<div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:16px">';
  s4+='<div style="text-align:center;padding:8px 16px;background:var(--blue-bg);border-radius:8px"><div style="font-size:1.5em;font-weight:800;color:var(--accent)">'+backlog.length+'</div><div style="font-size:.72em;color:var(--dim)">Total Backlog</div></div>';
  s4+='<div style="text-align:center;padding:8px 16px;background:var(--green-bg);border-radius:8px"><div style="font-size:1.5em;font-weight:800;color:var(--green)">'+createdThisWeek+'</div><div style="font-size:.72em;color:var(--dim)">Created This Week</div></div>';
  s4+='<div style="text-align:center;padding:8px 16px;background:var(--yellow-bg);border-radius:8px"><div style="font-size:1.5em;font-weight:800;color:var(--yellow)">'+createdThisMonth+'</div><div style="font-size:.72em;color:var(--dim)">Created This Month</div></div>';
  const staleCls=staleRate>40?'var(--red)':staleRate>20?'var(--yellow)':'var(--green)';
  s4+='<div style="text-align:center;padding:8px 16px;background:var(--red-bg);border-radius:8px"><div style="font-size:1.5em;font-weight:800;color:'+staleCls+'">'+staleRate+'%</div><div style="font-size:.72em;color:var(--dim)">Stale Rate (&gt;30d)</div></div>';
  s4+='</div>';
  s4+='<table class="audit-table"><thead><tr><th>Age Bucket</th><th>Count</th><th style="min-width:200px">Distribution</th></tr></thead><tbody>';
  buckets.forEach(b=>{
    const pct=backlog.length>0?(b.count/backlog.length*100).toFixed(0):0;
    const barW=maxBucket>0?(b.count/maxBucket*100).toFixed(0):0;
    s4+='<tr><td style="font-weight:600">'+b.label+'</td><td>'+b.count+' ('+pct+'%)</td><td><div style="background:var(--gray-l);border-radius:4px;height:18px;overflow:hidden"><div style="background:'+b.color+';height:100%;width:'+barW+'%;border-radius:4px;transition:width .3s"></div></div></td></tr>';
  });
  s4+='</tbody></table>';
  html+=collapsible('ins-backlog','Backlog Health &mdash; Age distribution of pending work',s4);

  /* ── Section 5: Prediction Accuracy Trend ── */
  const monthMap={};
  allData.filter(r=>r.status==='Done'&&r.delivery).forEach(r=>{
    const d=r.delivery.slice(0,7);/* YYYY-MM */
    if(!monthMap[d])monthMap[d]={total:0,withEta:0,onTime:0,daysOff:[],stable:0};
    monthMap[d].total++;
    if(r.eta){
      monthMap[d].withEta++;
      if(r.perf==='On Time')monthMap[d].onTime++;
      const diff=daysBetween(r.eta,r.delivery);
      if(diff!==null)monthMap[d].daysOff.push(Math.abs(diff));
      if((r.etaChanges||0)===0)monthMap[d].stable++;
    }
  });
  const monthKeys=Object.keys(monthMap).sort().slice(-6);

  let s5='<table class="audit-table"><thead><tr><th>Month</th><th>Tickets with ETA</th><th>On Time %</th><th>Avg Days Off</th><th>ETA Stability %</th></tr></thead><tbody>';
  if(monthKeys.length===0){
    s5+='<tr><td colspan="5" style="text-align:center;color:var(--dim);padding:20px">No data available</td></tr>';
  } else {
    monthKeys.forEach(mk=>{
      const m=monthMap[mk];
      const onTimePct=m.withEta>0?(m.onTime/m.withEta*100).toFixed(0):'--';
      const avgOff=m.daysOff.length>0?(m.daysOff.reduce((a,b)=>a+b,0)/m.daysOff.length).toFixed(1):'--';
      const stabPct=m.withEta>0?(m.stable/m.withEta*100).toFixed(0):'--';
      const onTimeCls=m.withEta>0&&(m.onTime/m.withEta)>=0.9?'color:var(--green);font-weight:700':m.withEta>0&&(m.onTime/m.withEta)>=0.7?'color:var(--yellow);font-weight:600':m.withEta>0?'color:var(--red);font-weight:600':'';
      s5+='<tr><td style="font-weight:600">'+esc(mk)+'</td><td>'+m.withEta+' / '+m.total+'</td><td style="'+onTimeCls+'">'+onTimePct+(onTimePct!=='--'?'%':'')+'</td><td>'+avgOff+(avgOff!=='--'?'d':'')+'</td><td>'+stabPct+(stabPct!=='--'?'%':'')+'</td></tr>';
    });
  }
  s5+='</tbody></table>';
  html+=collapsible('ins-prediction','Estimation Quality &mdash; Are we getting better at predicting?',s5);

  el.innerHTML=html;
}

/* ── Analytics Tab ─────────────────────────────────── */
function renderAnalytics(){
  const el=document.getElementById('analyticsBody');
  if(!el)return;
  const todayStr=new Date().toISOString().slice(0,10);
  const pf=state.person;const cat=state.category;
  const allData=RAW.filter(r=>(pf==='ALL'||r.tsa===pf)&&(cat==='ALL'||r.category===cat));
  const sortedWeeks=CORE_WEEKS.slice().sort(weekSort);
  const lastWeek=sortedWeeks.length>0?sortedWeeks[sortedWeeks.length-1]:null;
  const prevWeek=sortedWeeks.length>1?sortedWeeks[sortedWeeks.length-2]:null;
  /* Read control panel values */
  const retroMode=(document.getElementById('anRetroMode')||{}).value||'any';
  const trendWin=+(document.getElementById('anTrendWindow')||{}).value||8;
  const slopeT=+(document.getElementById('anSlopeThreshold')||{}).value||0.05;
  const streakCfg=(document.getElementById('anStreakWeeks')||{}).value||'2';
  const streakMinWeeks=+streakCfg.split('_')[0]||2;
  const streakThreshold=(streakCfg.includes('_40')?0.4:0.5);
  function isRetro(r){
    if(retroMode==='any')return r.retroactiveEta==='yes';
    if(retroMode==='post-delivery')return r.retroactiveEta==='yes'&&r.delivery&&r.eta&&r.eta.slice(0,10)!==((r.originalEta||r.eta)||'').slice(0,10);
    if(retroMode==='multi')return(r.etaChanges||0)>=2;
    return r.retroactiveEta==='yes';
  }
  function calcOrgAccuracy(rows){
    const ot=rows.filter(r=>r.perf==='On Time'&&!isRetro(r)).length;
    const lt=rows.filter(r=>r.perf==='Late'&&!isRetro(r)).length;
    const d=ot+lt;return{orgVal:d>0?ot/d:null,orgNum:ot,orgDen:d};
  }
  function anCollapse(id,icon,title,body,open){
    return '<div class="an-section" id="'+id+'"><div class="an-section-hdr'+(open?' open':'')+'" onclick="this.classList.toggle(\'open\');var b=this.nextElementSibling;b.style.display=this.classList.contains(\'open\')?\'block\':\'none\'"><span class="toggle">&#9660;</span><h3>'+icon+' '+title+'</h3></div><div class="an-section-body" style="display:'+(open?'block':'none')+'">'+body+'</div></div>';
  }
  function statCard(val,label,color,big){return '<div class="an-stat-card"'+(big?' style="min-width:180px"':'')+'><div class="an-stat-val" style="'+(big?'font-size:2em;':'')+'color:'+color+'">'+val+'</div><div class="an-stat-label">'+label+'</div></div>'}
  function accColor(v){return v>=.9?'var(--green)':v>=.7?'var(--yellow)':'var(--red)'}
  let html='';
  const modeLabel={any:'any ETA change','post-delivery':'post-delivery changes only',multi:'2+ ETA changes'}[retroMode]||retroMode;
  html+='<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 16px;margin-bottom:16px;font-size:.78em;display:flex;gap:16px;flex-wrap:wrap;align-items:center">';
  html+='<span style="font-weight:700;color:#92400e">Active settings:</span>';
  html+='<span>Retro = <b>'+esc(modeLabel)+'</b></span>';
  html+='<span>Window = <b>'+trendWin+'w</b></span>';
  html+='<span>Sensitivity = <b>&plusmn;'+(slopeT*100).toFixed(0)+'%/wk</b></span>';
  html+='<span>Streak = <b>'+streakMinWeeks+'w &lt;'+(streakThreshold*100)+'%</b></span>';
  html+='</div>';

  /* ── S1: Weekly Digest ── */
  let s1='';
  if(lastWeek){
    const cwData=allData.filter(r=>r.week===lastWeek);
    const pwData=prevWeek?allData.filter(r=>r.week===prevWeek):[];
    const cwA=calcAccuracy(cwData),pwA=calcAccuracy(pwData);
    const delta=(cwA.val!==null&&pwA.val!==null)?(cwA.val-pwA.val):null;
    s1+='<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">';
    s1+=statCard(fmtWeekPretty(lastWeek),'Current Week','var(--accent)',false);
    if(cwA.val!==null)s1+=statCard(fmtPct(cwA.val,cwA.den),'Team Accuracy (n='+cwA.den+')',accColor(cwA.val),false);
    if(delta!==null){const dc=delta>0.05?'var(--green)':delta<-0.05?'var(--red)':'var(--dim)';s1+=statCard((delta>0?'+':'')+(delta*100).toFixed(0)+'%','vs '+fmtWeekPretty(prevWeek),dc,false)}
    s1+=statCard(cwA.late,'Late This Week','var(--red)',false);
    if(cwA.orgVal!==null&&cwA.orgDen>0)s1+=statCard(fmtPct(cwA.orgVal,cwA.orgDen),'Organic (excl. retro)','#8b5cf6',false);
    s1+='</div>';
    s1+='<table class="audit-table"><thead><tr><th>Person</th><th>This Week</th><th>Last Week</th><th>Delta</th><th>Late</th><th>Retro ETA</th></tr></thead><tbody>';
    const people=pf!=='ALL'?[pf]:PEOPLE_ALL;
    people.forEach(p=>{
      const pc=calcAccuracy(cwData.filter(r=>r.tsa===p));
      const pp=calcAccuracy(pwData.filter(r=>r.tsa===p));
      const d=(pc.val!==null&&pp.val!==null)?(pc.val-pp.val):null;
      const ds=d!==null?((d>0?'+':'')+(d*100).toFixed(0)+'%'):'—';
      const dc=d===null?'':d>0.05?'color:var(--green);font-weight:700':d<-0.05?'color:var(--red);font-weight:700':'';
      const rc=cwData.filter(r=>r.tsa===p&&isRetro(r)).length;
      s1+='<tr><td style="font-weight:600">'+esc(p)+'</td><td>'+fmtPct(pc.val,pc.den)+' <span style="font-size:.72em;color:var(--dim)">(n='+pc.den+')</span></td><td>'+fmtPct(pp.val,pp.den)+'</td><td style="'+dc+'">'+ds+'</td><td style="color:var(--red)">'+pc.late+'</td><td style="'+(rc>0?'color:#d97706;font-weight:700':'')+'">'+rc+'</td></tr>';
    });
    s1+='</tbody></table>';
    const lateNow=allData.filter(r=>r.perf==='Late'&&r.status!=='Done'&&r.eta&&r.eta.slice(0,10)<todayStr);
    if(lateNow.length>0){
      s1+='<div style="margin-top:16px;font-weight:700;font-size:.9em;color:var(--red)">&#9888; Late Tickets Requiring Action ('+lateNow.length+')</div>';
      s1+='<table class="audit-table" style="margin-top:8px"><thead><tr><th>Ticket</th><th>Title</th><th>Person</th><th>Customer</th><th>ETA</th><th>Overdue</th></tr></thead><tbody>';
      lateNow.sort((a,b)=>(a.eta||'').localeCompare(b.eta||'')).forEach(r=>{
        const lk=r.ticketUrl?'<a href="'+esc(r.ticketUrl)+'" target="_blank" style="color:var(--accent);font-weight:600">'+esc(r.ticketId||'--')+'</a>':esc(r.ticketId||'--');
        const ti=(r.focus||'').length>50?esc(r.focus.slice(0,50))+'...':esc(r.focus||'--');
        const od=daysBetween(r.eta,todayStr);
        s1+='<tr><td>'+lk+'</td><td title="'+esc(r.focus||'')+'">'+ti+'</td><td>'+esc(r.tsa||'--')+'</td><td>'+esc(r.customer||'--')+'</td><td style="color:var(--red)">'+esc(r.eta||'--')+'</td><td style="color:var(--red);font-weight:700">'+od+'d</td></tr>';
      });
      s1+='</tbody></table>';
    }
    const streaks=[];
    (pf!=='ALL'?[pf]:PEOPLE_ALL).forEach(p=>{
      let c=0;for(let i=sortedWeeks.length-1;i>=0;i--){const a=calcAccuracy(allData.filter(r=>r.tsa===p&&r.week===sortedWeeks[i]));if(a.val!==null&&a.val<streakThreshold&&a.den>=2)c++;else break}
      if(c>=streakMinWeeks)streaks.push({p,c});
    });
    if(streaks.length>0){
      s1+='<div style="margin-top:16px;font-weight:700;font-size:.9em;color:#d97706">&#9888; Accuracy Below '+(streakThreshold*100)+'% for '+streakMinWeeks+'+ Consecutive Weeks</div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">';
      streaks.forEach(s=>{s1+='<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:8px 14px;font-size:.85em"><b>'+esc(s.p)+'</b> — '+s.c+' weeks</div>'});
      s1+='</div>';
    }
    const rTotal=allData.filter(r=>isRetro(r)&&CORE_WEEKS.includes(r.week)).length;
    const rBase=allData.filter(r=>CORE_WEEKS.includes(r.week)&&(r.perf==='On Time'||r.perf==='Late')).length;
    if(rTotal>0)s1+='<div style="margin-top:12px;font-size:.78em;color:var(--dim)">&#128269; '+rTotal+' retroactive ETA change'+(rTotal>1?'s':'')+' detected ('+(rBase>0?(rTotal/rBase*100).toFixed(0):0)+'% of measured) — mode: '+esc(modeLabel)+'</div>';
  } else {
    s1='<div style="color:var(--dim);text-align:center;padding:40px">No week data available</div>';
  }
  s1+='<div style="margin-top:16px;text-align:right"><button class="an-copy-btn" onclick="copyWeeklyDigest()">&#128203; Copy Digest to Clipboard</button></div>';
  html+=anCollapse('an-digest','&#128200;','Weekly Digest &mdash; '+(lastWeek?fmtWeekPretty(lastWeek):'N/A'),s1,true);

  /* ── S2: Organic Accuracy (uses control: retroMode via isRetro) ── */
  let s2='';
  const coreData=allData.filter(r=>r.week&&isCoreWeek(r.week));
  const tAcc=calcAccuracy(coreData);
  const tOrg=calcOrgAccuracy(coreData);
  s2+='<div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:16px">';
  if(tAcc.val!==null)s2+=statCard(fmtPct(tAcc.val,tAcc.den),'Total Accuracy ('+tAcc.num+'/'+tAcc.den+')',accColor(tAcc.val),true);
  if(tOrg.orgVal!==null)s2+=statCard(fmtPct(tOrg.orgVal,tOrg.orgDen),'Organic ('+tOrg.orgNum+'/'+tOrg.orgDen+')','#8b5cf6',true);
  const gap=(tAcc.val!==null&&tOrg.orgVal!==null)?(tAcc.val-tOrg.orgVal):null;
  if(gap!==null)s2+=statCard((gap>0?'+':'')+(gap*100).toFixed(0)+'%','Inflation Gap',Math.abs(gap)<0.05?'var(--green)':'#d97706',true);
  s2+='</div>';
  s2+='<div style="font-size:.78em;color:var(--dim);margin-bottom:12px">Organic excludes tickets flagged as retroactive (' +esc(modeLabel)+').</div>';
  s2+='<table class="audit-table"><thead><tr><th>Person</th><th>Total Accuracy</th><th>Organic Accuracy</th><th>Gap</th><th>Retro Count</th><th>Retro %</th></tr></thead><tbody>';
  (pf!=='ALL'?[pf]:PEOPLE_ALL).forEach(p=>{
    const pRows=coreData.filter(r=>r.tsa===p);
    const pa=calcAccuracy(pRows);
    const po=calcOrgAccuracy(pRows);
    const g=(pa.val!==null&&po.orgVal!==null)?pa.val-po.orgVal:null;
    const rc=pRows.filter(r=>isRetro(r)).length;
    const rp=pa.den>0?(rc/pa.den*100).toFixed(0):'0';
    const gs=g===null?'':'color:'+(Math.abs(g)<0.03?'var(--green)':g>0.1?'var(--red)':'#d97706')+';font-weight:700';
    const ts=pa.val===null?'':'color:'+accColor(pa.val)+';font-weight:700';
    s2+='<tr><td style="font-weight:600">'+esc(p)+'</td><td style="'+ts+'">'+fmtPct(pa.val,pa.den)+' ('+pa.num+'/'+pa.den+')</td><td style="color:#8b5cf6;font-weight:700">'+fmtPct(po.orgVal,po.orgDen)+' ('+po.orgNum+'/'+po.orgDen+')</td><td style="'+gs+'">'+(g!==null?(g>0?'+':'')+(g*100).toFixed(0)+'%':'—')+'</td><td>'+rc+'</td><td>'+rp+'%</td></tr>';
  });
  s2+='</tbody></table>';
  html+=anCollapse('an-organic','&#127793;','Organic Accuracy &mdash; '+esc(modeLabel),s2,false);

  /* ── S3: Trend Radar (uses controls: trendWin, slopeT) ── */
  let s3='';
  const tWeeks=sortedWeeks.slice(-trendWin);
  s3+='<div style="font-size:.78em;color:var(--dim);margin-bottom:16px">Linear regression over last '+tWeeks.length+' weeks. Slope &gt; +'+(slopeT*100).toFixed(0)+'%/wk = improving, &lt; -'+(slopeT*100).toFixed(0)+'% = declining.</div>';
  s3+='<div class="an-health-grid">';
  (pf!=='ALL'?[pf]:PEOPLE_ALL).forEach(p=>{
    const pts=[];
    tWeeks.forEach((w,i)=>{const a=calcAccuracy(allData.filter(r=>r.tsa===p&&r.week===w));if(a.val!==null&&a.den>=1)pts.push({x:i,y:a.val,w,n:a.den})});
    let slope=0,cls='stable',arrow='&#8594;',clr='var(--dim)',proj=null;
    if(pts.length>=3){
      const n=pts.length,sx=pts.reduce((a,v)=>a+v.x,0),sy=pts.reduce((a,v)=>a+v.y,0);
      const sxy=pts.reduce((a,v)=>a+v.x*v.y,0),sxx=pts.reduce((a,v)=>a+v.x*v.x,0);
      const denom=n*sxx-sx*sx;
      if(denom!==0){slope=(n*sxy-sx*sy)/denom;const b=(sy-slope*sx)/n;proj=Math.max(0,Math.min(1,b+slope*tWeeks.length))}
      if(slope>slopeT){cls='improving';arrow='&#8593;';clr='var(--green)'}
      else if(slope<-slopeT){cls='declining';arrow='&#8595;';clr='var(--red)'}
    }
    const latest=pts.length>0?pts[pts.length-1]:null;
    let spark='<div class="an-spark">';
    tWeeks.forEach(w=>{const a=calcAccuracy(allData.filter(r=>r.tsa===p&&r.week===w));if(a.val===null){spark+='<div class="an-spark-bar" style="height:2px;background:var(--gray-l)"></div>'}else{const h=Math.max(4,Math.round(a.val*32));spark+='<div class="an-spark-bar" style="height:'+h+'px;background:'+accColor(a.val)+'"></div>'}});
    spark+='</div>';
    s3+='<div class="an-health-card"><div class="an-health-top"><span class="an-health-name">'+esc(p)+'</span><span class="an-health-arrow" style="color:'+clr+'">'+arrow+'</span></div>';
    s3+='<div class="an-health-current" style="color:'+(latest?accColor(latest.y):'var(--dim)')+'">'+(latest?fmtPct(latest.y,latest.n):'—')+'</div>';
    s3+=spark;
    s3+='<div class="an-health-meta"><span class="an-health-tag" style="background:'+clr+'22;color:'+clr+'">'+cls+'</span>';
    if(proj!==null)s3+=' <span style="font-size:.72em;color:var(--dim)">proj: '+fmtPct(proj,1)+'</span>';
    s3+='</div><div style="font-size:.65em;color:var(--light)">slope: '+(slope*100).toFixed(1)+'%/wk &middot; '+pts.length+' pts</div></div>';
  });
  s3+='</div>';
  html+=anCollapse('an-trends','&#128200;','Trend Radar &mdash; Per-person trajectory',s3,false);

  /* ── S4: Export ── */
  let s4='<div style="display:flex;gap:12px;flex-wrap:wrap">';
  s4+='<button class="an-export-btn" style="background:linear-gradient(135deg,#c2410c,#ea580c);border-color:#ea580c" onclick="generateWeeklyPPT()"><span style="font-size:1.2em">&#127912;</span><div><b>Download Weekly PPT</b><div style="font-size:.72em;color:#fed7aa">PowerPoint for presentation</div></div></button>';
  s4+='<button class="an-export-btn" onclick="copyWeeklyDigest()"><span style="font-size:1.2em">&#128203;</span><div><b>Copy Weekly Digest</b><div style="font-size:.72em;color:#94a3b8">Markdown for Slack</div></div></button>';
  s4+='<button class="an-export-btn" onclick="copyTeamReport()"><span style="font-size:1.2em">&#128202;</span><div><b>Copy Full Report</b><div style="font-size:.72em;color:#94a3b8">All analytics as Markdown</div></div></button>';
  s4+='<button class="an-export-btn" onclick="copyLateTickets()"><span style="font-size:1.2em">&#9888;</span><div><b>Copy Late Tickets</b><div style="font-size:.72em;color:#94a3b8">Action items list</div></div></button>';
  s4+='</div><div id="anExportPreview" style="margin-top:16px;display:none;background:#0f172a;border-radius:8px;padding:16px;font-family:Consolas,monospace;font-size:.78em;color:#e2e8f0;white-space:pre-wrap;max-height:400px;overflow-y:auto"></div>';
  html+=anCollapse('an-export','&#128230;','Export &mdash; Copy &amp; Share',s4,false);

  el.innerHTML=html;
}

function anShowPreview(txt){
  const p=document.getElementById('anExportPreview');
  if(!p)return;p.textContent=txt;p.style.display='block';
  setTimeout(()=>{p.style.display='none'},8000);
}

function copyWeeklyDigest(){
  const sw=CORE_WEEKS.slice().sort(weekSort);
  const lw=sw[sw.length-1],pw=sw.length>1?sw[sw.length-2]:null;
  if(!lw)return;
  const cat=state.category;
  const all=RAW.filter(r=>(cat==='ALL'||r.category===cat));
  const cw=all.filter(r=>r.week===lw),pws=pw?all.filter(r=>r.week===pw):[];
  const ca=calcAccuracy(cw),pa=calcAccuracy(pws);
  const d=(ca.val!==null&&pa.val!==null)?(ca.val-pa.val):null;
  let md='## Weekly KPI Digest — '+fmtWeekPretty(lw)+'\n\n';
  md+='**Team Accuracy:** '+fmtPct(ca.val,ca.den)+' ('+ca.num+'/'+ca.den+')';
  if(d!==null)md+=' | Delta: '+(d>0?'+':'')+(d*100).toFixed(0)+'%';
  md+='\n**Organic:** '+fmtPct(ca.orgVal,ca.orgDen)+' (excl. retro ETA)\n\n';
  md+='| Person | This Week | Last Week | Delta | Late |\n|--------|-----------|-----------|-------|------|\n';
  PEOPLE_ALL.forEach(p=>{
    const pc=calcAccuracy(cw.filter(r=>r.tsa===p));
    const pp=calcAccuracy(pws.filter(r=>r.tsa===p));
    const dd=(pc.val!==null&&pp.val!==null)?(pc.val-pp.val):null;
    md+='| '+p+' | '+fmtPct(pc.val,pc.den)+' | '+fmtPct(pp.val,pp.den)+' | '+(dd!==null?(dd>0?'+':'')+(dd*100).toFixed(0)+'%':'—')+' | '+pc.late+' |\n';
  });
  const late=all.filter(r=>r.perf==='Late'&&r.status!=='Done'&&r.eta);
  if(late.length>0){md+='\n**Late Tickets ('+late.length+'):**\n';late.forEach(r=>{md+='- '+r.ticketId+': '+(r.focus||'')+' — '+r.tsa+' — ETA: '+r.eta+'\n'})}
  navigator.clipboard.writeText(md).then(()=>anShowPreview(md));
}

/* old copyTeamReport (markdown) removed — replaced by Slack version above */

function copyLateTickets(){
  const todayStr=new Date().toISOString().slice(0,10);
  const cat=state.category;
  const late=RAW.filter(r=>(cat==='ALL'||r.category===cat)&&r.perf==='Late'&&r.status!=='Done'&&r.eta&&r.eta.slice(0,10)<todayStr);
  if(late.length===0){anShowPreview('No late tickets found.');return}
  let md='## Late Tickets — Action Required ('+late.length+')\n\n';
  late.sort((a,b)=>(a.tsa||'').localeCompare(b.tsa||'')||(a.eta||'').localeCompare(b.eta||''));
  let curPerson='';
  late.forEach(r=>{
    if(r.tsa!==curPerson){curPerson=r.tsa;md+='\n### '+curPerson+'\n'}
    const od=daysBetween(r.eta,todayStr);
    md+='- [ ] **'+r.ticketId+'** '+(r.focus||'')+' — '+r.customer+' — ETA: '+r.eta+' ('+od+'d overdue)\n';
  });
  navigator.clipboard.writeText(md).then(()=>anShowPreview(md));
}

function generateWeeklyPPT(){
  if(typeof PptxGenJS==='undefined'){alert('PptxGenJS not loaded. Check network.');return}
  const pptx=new PptxGenJS();
  pptx.author='TSA KPI Dashboard';
  pptx.subject='Weekly KPI Review';
  const sw=CORE_WEEKS.slice().sort(weekSort);
  const lw=sw[sw.length-1],pw=sw.length>1?sw[sw.length-2]:null;
  const cat=state.category;
  const all=RAW.filter(r=>(cat==='ALL'||r.category===cat));
  const core=all.filter(r=>r.week&&isCoreWeek(r.week));
  const tAcc=calcAccuracy(core);
  const weekLabel=lw?fmtWeekPretty(lw):'N/A';
  pptx.title='KPI Weekly — '+weekLabel;
  const BG='0F172A',ACC='3B82F6',GRN='22C55E',RED='EF4444',YLW='F59E0B',DIM='94A3B8',WHT='FFFFFF';
  function accHex(v){return v>=.9?GRN:v>=.7?YLW:RED}

  /* ── Slide 1: Title ── */
  let s1=pptx.addSlide();
  s1.background={color:BG};
  s1.addText('KPI Weekly Review',{x:0.6,y:1.0,w:8.8,h:1,fontSize:36,fontFace:'Segoe UI',color:WHT,bold:true});
  s1.addText(weekLabel+'  |  TSA Team  |  '+BUILD_DATE,{x:0.6,y:2.0,w:8.8,h:0.5,fontSize:14,fontFace:'Segoe UI',color:DIM});
  if(tAcc.val!==null){
    s1.addText(fmtPct(tAcc.val,tAcc.den),{x:0.6,y:3.2,w:2.5,h:1,fontSize:48,fontFace:'Segoe UI',color:accHex(tAcc.val),bold:true});
    s1.addText('Team Accuracy ('+tAcc.num+'/'+tAcc.den+')',{x:0.6,y:4.1,w:3,h:0.4,fontSize:12,fontFace:'Segoe UI',color:DIM});
  }

  /* ── Slide 2: Week-over-Week ── */
  if(lw){
    let s2=pptx.addSlide();
    s2.background={color:BG};
    s2.addText('Week-over-Week Comparison',{x:0.6,y:0.3,w:8.8,h:0.6,fontSize:22,fontFace:'Segoe UI',color:WHT,bold:true});
    const cwData=all.filter(r=>r.week===lw);const pwData=pw?all.filter(r=>r.week===pw):[];
    const rows=[['Person','This Week','Last Week','Delta','Late','Trend']];
    const people=PEOPLE_ALL;
    const retroMode=(document.getElementById('anRetroMode')||{}).value||'any';
    const trendWin=+(document.getElementById('anTrendWindow')||{}).value||8;
    const slopeT=+(document.getElementById('anSlopeThreshold')||{}).value||0.05;
    function isRetroP(r){
      if(retroMode==='any')return r.retroactiveEta==='yes';
      if(retroMode==='multi')return(r.etaChanges||0)>=2;
      return r.retroactiveEta==='yes';
    }
    const tWeeks=sw.slice(-trendWin);
    people.forEach(p=>{
      const pc=calcAccuracy(cwData.filter(r=>r.tsa===p));
      const pp=calcAccuracy(pwData.filter(r=>r.tsa===p));
      const d=(pc.val!==null&&pp.val!==null)?pc.val-pp.val:null;
      const ds=d===null?'—':(d>0?'+':'')+(d*100).toFixed(0)+'%';
      const pts=[];tWeeks.forEach((w,i)=>{const a=calcAccuracy(all.filter(r=>r.tsa===p&&r.week===w));if(a.val!==null&&a.den>=1)pts.push({x:i,y:a.val})});
      let trend='stable';
      if(pts.length>=3){const n=pts.length,sx=pts.reduce((a,v)=>a+v.x,0),sy=pts.reduce((a,v)=>a+v.y,0),sxy=pts.reduce((a,v)=>a+v.x*v.y,0),sxx=pts.reduce((a,v)=>a+v.x*v.x,0),dn=n*sxx-sx*sx;if(dn!==0){const sl=(n*sxy-sx*sy)/dn;if(sl>slopeT)trend='improving';else if(sl<-slopeT)trend='declining'}}
      rows.push([p,fmtPct(pc.val,pc.den),fmtPct(pp.val,pp.den),ds,String(pc.late),trend]);
    });
    const colW=[2.2,1.5,1.5,1.2,0.8,1.5];
    s2.addTable(rows,{x:0.4,y:1.1,w:8.7,colW:colW,fontSize:11,fontFace:'Segoe UI',color:WHT,border:{type:'solid',pt:0.5,color:'334155'},rowH:0.38,autoPage:false,
      headerRow:true,headerRowColor:'1E293B',headerRowFontColor:ACC,headerRowFontBold:true});
  }

  /* ── Slide 3: Organic Accuracy ── */
  let s3=pptx.addSlide();
  s3.background={color:BG};
  s3.addText('Organic Accuracy',{x:0.6,y:0.3,w:8.8,h:0.6,fontSize:22,fontFace:'Segoe UI',color:WHT,bold:true});
  s3.addText('Excluding retroactive ETA changes',{x:0.6,y:0.8,w:8.8,h:0.3,fontSize:11,fontFace:'Segoe UI',color:DIM});
  const orgRows=[['Person','Total','Organic','Gap','Retro %']];
  PEOPLE_ALL.forEach(p=>{
    const pRows=core.filter(r=>r.tsa===p);
    const pa=calcAccuracy(pRows);
    const orgOt=pRows.filter(r=>r.perf==='On Time'&&!(r.retroactiveEta==='yes')).length;
    const orgLt=pRows.filter(r=>r.perf==='Late'&&!(r.retroactiveEta==='yes')).length;
    const orgD=orgOt+orgLt;const orgV=orgD>0?orgOt/orgD:null;
    const g=(pa.val!==null&&orgV!==null)?pa.val-orgV:null;
    const rc=pRows.filter(r=>r.retroactiveEta==='yes').length;
    const rp=pa.den>0?(rc/pa.den*100).toFixed(0)+'%':'0%';
    orgRows.push([p,fmtPct(pa.val,pa.den),fmtPct(orgV,orgD),g!==null?(g>0?'+':'')+(g*100).toFixed(0)+'%':'—',rp]);
  });
  s3.addTable(orgRows,{x:0.4,y:1.3,w:8.7,colW:[2.2,1.8,1.8,1.2,1.2],fontSize:11,fontFace:'Segoe UI',color:WHT,border:{type:'solid',pt:0.5,color:'334155'},rowH:0.38,autoPage:false,
    headerRow:true,headerRowColor:'1E293B',headerRowFontColor:'8B5CF6',headerRowFontBold:true});

  /* ── Slide 4: Trend Radar ── */
  let s4p=pptx.addSlide();
  s4p.background={color:BG};
  s4p.addText('Trend Radar',{x:0.6,y:0.3,w:8.8,h:0.6,fontSize:22,fontFace:'Segoe UI',color:WHT,bold:true});
  const trendWinP=+(document.getElementById('anTrendWindow')||{}).value||8;
  const slopeTP=+(document.getElementById('anSlopeThreshold')||{}).value||0.05;
  const tWeeksP=sw.slice(-trendWinP);
  s4p.addText('Linear regression over '+tWeeksP.length+' weeks | Threshold: ±'+(slopeTP*100).toFixed(0)+'%/wk',{x:0.6,y:0.8,w:8.8,h:0.3,fontSize:11,fontFace:'Segoe UI',color:DIM});
  const trendRows=[['Person','Current','Slope','Projected','Status']];
  PEOPLE_ALL.forEach(p=>{
    const pts=[];tWeeksP.forEach((w,i)=>{const a=calcAccuracy(all.filter(r=>r.tsa===p&&r.week===w));if(a.val!==null&&a.den>=1)pts.push({x:i,y:a.val})});
    let slope=0,cls='stable',proj=null;
    if(pts.length>=3){const n=pts.length,sx=pts.reduce((a,v)=>a+v.x,0),sy=pts.reduce((a,v)=>a+v.y,0),sxy=pts.reduce((a,v)=>a+v.x*v.y,0),sxx=pts.reduce((a,v)=>a+v.x*v.x,0),dn=n*sxx-sx*sx;if(dn!==0){slope=(n*sxy-sx*sy)/dn;const b=(sy-slope*sx)/n;proj=Math.max(0,Math.min(1,b+slope*tWeeksP.length))}
      if(slope>slopeTP)cls='IMPROVING';else if(slope<-slopeTP)cls='DECLINING';else cls='STABLE'}
    const latest=pts.length>0?pts[pts.length-1]:null;
    trendRows.push([p,latest?fmtPct(latest.y,1):'—',(slope*100).toFixed(1)+'%/wk',proj!==null?fmtPct(proj,1):'—',cls]);
  });
  s4p.addTable(trendRows,{x:0.4,y:1.3,w:8.7,colW:[2.2,1.5,1.5,1.5,1.5],fontSize:11,fontFace:'Segoe UI',color:WHT,border:{type:'solid',pt:0.5,color:'334155'},rowH:0.38,autoPage:false,
    headerRow:true,headerRowColor:'1E293B',headerRowFontColor:GRN,headerRowFontBold:true});

  /* ── Slide 5: Late Tickets ── */
  const todayStr=new Date().toISOString().slice(0,10);
  const late=all.filter(r=>r.perf==='Late'&&r.status!=='Done'&&r.eta&&r.eta.slice(0,10)<todayStr);
  if(late.length>0){
    let s5=pptx.addSlide();
    s5.background={color:BG};
    s5.addText('Late Tickets — Action Required ('+late.length+')',{x:0.6,y:0.3,w:8.8,h:0.6,fontSize:22,fontFace:'Segoe UI',color:RED,bold:true});
    late.sort((a,b)=>(a.tsa||'').localeCompare(b.tsa||'')||(a.eta||'').localeCompare(b.eta||''));
    const lateRows=[['Ticket','Focus','Person','Customer','ETA','Overdue']];
    late.slice(0,18).forEach(r=>{
      const od=daysBetween(r.eta,todayStr);
      lateRows.push([r.ticketId||'—',(r.focus||'').slice(0,40),r.tsa||'—',r.customer||'—',r.eta||'—',od+'d']);
    });
    s5.addTable(lateRows,{x:0.4,y:1.1,w:9.0,colW:[1.2,2.8,1.3,1.5,1.1,0.8],fontSize:10,fontFace:'Segoe UI',color:WHT,border:{type:'solid',pt:0.5,color:'334155'},rowH:0.35,autoPage:false,
      headerRow:true,headerRowColor:'1E293B',headerRowFontColor:RED,headerRowFontBold:true});
    if(late.length>18)s5.addText('+'+(late.length-18)+' more — see full dashboard',{x:0.6,y:4.8,w:8,h:0.3,fontSize:10,fontFace:'Segoe UI',color:DIM});
  }

  const fname='KPI_Weekly_'+weekLabel.replace(/[^A-Za-z0-9]/g,'_')+'.pptx';
  pptx.writeFile({fileName:fname}).then(()=>{anShowPreview('PPT downloaded: '+fname)});
}

/* ── Init ───────────────────────────────────────────── */
function init(){
  const fp=document.getElementById('fPerson');
  PEOPLE_ALL.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;fp.appendChild(o)});

  /* Populate month filter from available months */
  const fm=document.getElementById('fMonth');
  MONTHS.forEach(mo=>{const o=document.createElement('option');o.value=mo.label;o.textContent=mo.label;fm.appendChild(o)});

  const cki=document.getElementById('clientKpiInfo');
  cki.addEventListener('mouseenter',e=>showTip(e,CLIENT_TIP));
  cki.addEventListener('mouseleave',()=>hideTip());

  document.getElementById('fMonth').addEventListener('change',e=>{state.month=e.target.value;debouncedRender()});
  document.getElementById('fPerson').addEventListener('change',e=>{state.person=e.target.value;debouncedRender()});

  /* M12: Segment bar — default ALL */
  document.querySelectorAll('.segment-btn').forEach(btn=>{
    btn.addEventListener('click',()=>{
      document.querySelectorAll('.segment-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      state.category=btn.dataset.seg;
      document.getElementById('fCategory').value=btn.dataset.seg;
      debouncedRender();
    });
  });
  document.getElementById('fCategory').addEventListener('change',e=>{
    state.category=e.target.value;
    document.querySelectorAll('.segment-btn').forEach(b=>{
      b.classList.toggle('active',b.dataset.seg===state.category);
    });
    debouncedRender();
  });

  /* ── Implementation Timeline Tab ──────────────────── */
  function renderImplementation(){
    const el=document.getElementById('implementationBody');
    if(!el)return;

    /* Parse Mon/YY to a Date for duration calc */
    const MON_MAP={Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
    function parseMonYY(s){
      if(!s)return null;
      const m=s.match(/^([A-Za-z]{3})\/(\d{2})$/);
      if(!m)return null;
      const mo=MON_MAP[m[1]];
      if(mo===undefined)return null;
      return new Date(2000+parseInt(m[2]),mo,1);
    }
    function monthsDiff(a,b){
      if(!a||!b)return null;
      const da=parseMonYY(a),db=parseMonYY(b);
      if(!da||!db)return null;
      return (db.getFullYear()-da.getFullYear())*12+(db.getMonth()-da.getMonth());
    }

    /* Status badge */
    const statusColors={live:'#059669',maintenance:'#0284c7',in_progress:'#d97706',starting:'#7c3aed',stalled:'#dc2626',churned:'#991b1b',pre_sales:'#6b7280',interrupted:'#9f1239'};
    const statusLabels={live:'Live',maintenance:'Maintenance',in_progress:'In Progress',starting:'Starting',stalled:'Stalled',churned:'Churned',pre_sales:'Pre-sales',interrupted:'Interrupted'};
    function badge(st){
      const c=statusColors[st]||'#6b7280';
      const l=statusLabels[st]||st;
      return '<span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:.75em;font-weight:700;color:#fff;background:'+c+'">'+l+'</span>';
    }

    /* Sort: live first, then in_progress, then rest. Within group: by kickoff desc */
    const order={live:0,maintenance:1,in_progress:2,starting:3,interrupted:4,stalled:5,pre_sales:6,churned:7};
    const sorted=[...TIMELINE].sort((a,b)=>{
      const oa=(order[a.status]??9)-(order[b.status]??9);
      if(oa!==0)return oa;
      /* Within same status: oldest kickoff first, no-kickoff last */
      function toNum(s){if(!s)return 9999;const m=s.match(/^([A-Za-z]{3})\/(\d{2})$/);if(!m)return 9999;const mo=MON_MAP[m[1]];return mo!==undefined?(2000+parseInt(m[2]))*100+mo:9999;}
      return toNum(a.kickoff)-toNum(b.kickoff);
    });

    /* Logo domains for favicons */
    const LOGO_DOMAINS={Dixa:'dixa.com',Syncari:'syncari.com',Assignar:'assignar.com',CallRail:'callrail.com',Gong:'gong.io',Brevo:'brevo.com',QuickBooks:'quickbooks.intuit.com',Tropic:'tropicapp.io',Onyx:'onyx.app','People.ai':'people.ai',Tabs:'tabs.inc',Archer:'archerirm.com',Gainsight:'gainsight.com',Siteimprove:'siteimprove.com',Mailchimp:'mailchimp.com',Gem:'gem.com',WFS:'workforce.intuit.com',Apollo:'apollo.io'};
    const TBX_ICON='<img src="https://www.google.com/s2/favicons?domain=testbox.com&sz=32" width="14" height="14" style="border-radius:2px;opacity:.18;vertical-align:middle">';

    /* Compute duration for each */
    sorted.forEach(r=>{
      if(r.kickoff&&r.goLive){
        r._months=monthsDiff(r.kickoff,r.goLive);
      } else if(r.kickoff&&!r.goLive&&['in_progress','starting'].includes(r.status)){
        /* Ongoing — calc from kickoff to now */
        const now=new Date();
        const kd=parseMonYY(r.kickoff);
        if(kd)r._monthsOngoing=(now.getFullYear()-kd.getFullYear())*12+(now.getMonth()-kd.getMonth());
      }
    });

    /* Stats */
    const completed=sorted.filter(r=>r.goLive&&r._months!==null);
    const avgMonths=completed.length>0?Math.round(completed.reduce((s,r)=>s+r._months,0)/completed.length*10)/10:0;
    const fastest=completed.length>0?completed.reduce((a,b)=>a._months<b._months?a:b):null;
    const liveCount=sorted.filter(r=>['live','maintenance'].includes(r.status)).length;
    const inProgCount=sorted.filter(r=>['in_progress','starting'].includes(r.status)).length;
    const intCount=sorted.filter(r=>r.status==='interrupted').length;

    /* TSA Team stats — projects kicked off Sep/25 or later (current team era) */
    /* TSA Team stats — projects kicked off Sep/25 or later (current team era) */
    const TSA_CUTOFF=202508; /* Sep=8 in 0-indexed MON_MAP */
    function kickoffNum(r){if(!r.kickoff)return null;const m=r.kickoff.match(/^([A-Za-z]{3})\/(\d{2})$/);if(!m)return null;const mo=MON_MAP[m[1]];return mo!==undefined?(2000+parseInt(m[2]))*100+mo:null;}
    /* Include WFS (deal Mar/26 but no kickoff yet) */
    const tsaProjects=sorted.filter(r=>{const kn=kickoffNum(r);return(kn&&kn>=TSA_CUTOFF)||(r.customer==='WFS');});
    const tsaCompleted=tsaProjects.filter(r=>r.goLive&&r._months!==null);
    const tsaAvg=tsaCompleted.length>0?Math.round(tsaCompleted.reduce((s,r)=>s+r._months,0)/tsaCompleted.length*10)/10:null;

    let html='';

    /* 3-column layout: table | cards | charts — all bordered sections */
    const stalledCount=sorted.filter(r=>r.status==='stalled').length;
    html+='<div style="display:grid;grid-template-columns:minmax(0,520px) 140px 1fr;gap:0;align-items:stretch;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">';

    /* COL 1: Table */
    function dateCell(val,src){
      if(!val)return '<td style="color:#cbd5e1;text-align:center;padding:3px 4px">—</td>';
      if(src)return '<td style="text-align:center;padding:3px 4px;cursor:help" title="'+esc(src)+'">'+esc(val)+'</td>';
      return '<td style="text-align:center;padding:3px 4px">'+esc(val)+'</td>';
    }
    const th='style="text-align:center;padding:3px 4px;font-size:.64em;text-transform:uppercase;letter-spacing:.03em;color:#64748b;font-weight:600"';
    html+='<div style="padding:8px 10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.76em"><thead><tr style="border-bottom:2px solid #e2e8f0">';
    html+='<th style="text-align:left;padding:3px 4px;font-size:.64em;text-transform:uppercase;letter-spacing:.03em;color:#64748b;font-weight:600">Customer</th>';
    html+='<th '+th+'>Deal</th><th '+th+'>Kickoff</th><th '+th+'>Go-Live</th><th '+th+'>Time</th><th '+th+'>Status</th>';
    html+='</tr></thead><tbody>';
    sorted.forEach((r,i)=>{
      let dur='<span style="color:#cbd5e1">—</span>';
      if(r._months!==null&&r._months!==undefined)dur='<b>'+r._months+'mo</b>';
      else if(r._monthsOngoing)dur='<span style="color:#d97706;font-weight:600">'+r._monthsOngoing+'mo+</span>';
      const dimRow=['churned','interrupted','stalled'].includes(r.status)?'opacity:.45;':'';
      const zebra=i%2===0?'background:#f8fafc;':'';
      html+='<tr style="'+zebra+dimRow+'">';
      const cDom=LOGO_DOMAINS[r.customer];
      const cIcon=cDom?'<img src="https://www.google.com/s2/favicons?domain='+cDom+'&sz=32" width="14" height="14" style="border-radius:2px;vertical-align:middle;margin-right:4px" onerror="this.style.display=\'none\'">':'';
      const msTip=r.milestones?'<span title="'+esc(r.milestones.replace(/\|/g,'\n'))+'" style="cursor:help;font-size:.7em;color:#94a3b8;margin-left:3px;vertical-align:middle">&#9670;</span>':'';
      html+='<td style="padding:2px 4px;font-weight:600;white-space:nowrap">'+cIcon+esc(r.customer)+msTip+'</td>';
      html+=dateCell(r.dealSigned,r.srcDeal);
      html+=dateCell(r.kickoff,r.srcKickoff);
      html+=dateCell(r.goLive,r.srcGoLive);
      html+='<td style="text-align:center;padding:2px 4px">'+dur+'</td>';
      html+='<td style="text-align:center;padding:2px 4px">'+badge(r.status)+'</td>';
      html+='</tr>';
    });
    html+='</tbody></table></div>';

    /* COL 2: Summary cards — bordered left */
    html+='<div style="border-left:1px solid #e2e8f0;padding:6px 5px;display:flex;flex-direction:column;gap:4px;justify-content:space-between;background:#fafbfc">';
    html+='<div style="text-align:center;padding:8px 4px;background:#ecfdf5;border-radius:6px"><div style="font-size:1.2em;font-weight:800;color:#059669">'+liveCount+'</div><div style="font-size:.6em;color:#065f46">Live / Maint.</div></div>';
    html+='<div style="text-align:center;padding:8px 4px;background:#fef3c7;border-radius:6px"><div style="font-size:1.2em;font-weight:800;color:#d97706">'+inProgCount+'</div><div style="font-size:.6em;color:#92400e">In Progress</div></div>';
    html+='<div style="text-align:center;padding:8px 4px;background:#ede9fe;border-radius:6px"><div style="font-size:1.2em;font-weight:800;color:#7c3aed">'+(avgMonths>0?avgMonths+'mo':'—')+'</div><div style="font-size:.6em;color:#5b21b6">Avg Onboarding</div></div>';
    html+='<div style="text-align:center;padding:8px 4px;background:#eef2ff;border-radius:6px"><div style="font-size:1.2em;font-weight:800;color:#4338ca">'+(tsaAvg!==null?tsaAvg+'mo':'—')+'</div><div style="font-size:.6em;color:#3730a3">TSA Team Avg</div><div style="font-size:.5em;color:#6366f1">since Sep/25</div></div>';
    html+='<div style="text-align:center;padding:8px 4px;background:#f0fdf4;border-radius:6px"><div style="font-size:1.2em;font-weight:800;color:#059669">'+(fastest?fastest._months+'mo':'—')+'</div><div style="font-size:.6em;color:#065f46">Fastest ('+(fastest?fastest.customer:'—')+')</div></div>';
    html+='<div style="text-align:center;padding:8px 4px;background:#fff1f2;border-radius:6px"><div style="font-size:1.2em;font-weight:800;color:#9f1239">'+(intCount+stalledCount)+'</div><div style="font-size:.6em;color:#881337">Interrupted / Stalled</div></div>';
    html+='</div>';

    /* COL 3: Three sections stacked — bordered left */
    html+='<div style="border-left:1px solid #e2e8f0;display:flex;flex-direction:column">';

    /* Section 1: Portfolio status as compact table with color dots */
    const statusCounts=[
      {label:'Live',count:sorted.filter(r=>r.status==='live').length,color:'#059669',customers:sorted.filter(r=>r.status==='live').map(r=>r.customer)},
      {label:'Maintenance',count:sorted.filter(r=>r.status==='maintenance').length,color:'#0284c7',customers:sorted.filter(r=>r.status==='maintenance').map(r=>r.customer)},
      {label:'In Progress',count:sorted.filter(r=>['in_progress','starting'].includes(r.status)).length,color:'#d97706',customers:sorted.filter(r=>['in_progress','starting'].includes(r.status)).map(r=>r.customer)},
      {label:'Interrupted',count:intCount,color:'#9f1239',customers:sorted.filter(r=>r.status==='interrupted').map(r=>r.customer)},
      {label:'Stalled',count:stalledCount,color:'#dc2626',customers:sorted.filter(r=>r.status==='stalled').map(r=>r.customer)}
    ].filter(s=>s.count>0);
    /* Two mini-tables side by side */
    html+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:0">';

    /* Left: Portfolio Breakdown */
    html+='<div style="padding:10px 12px">';
    html+='<div style="font-size:.65em;font-weight:700;color:#475569;margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em">By Status</div>';
    statusCounts.forEach(s=>{
      html+='<div style="display:flex;align-items:center;gap:5px;padding:2px 0;font-size:.73em">';
      html+='<span style="width:7px;height:7px;border-radius:50%;background:'+s.color+';flex-shrink:0"></span>';
      html+='<span style="font-weight:600;width:70px">'+s.label+'</span>';
      html+='<span style="font-weight:800;width:16px;text-align:center">'+s.count+'</span>';
      html+='<span style="color:#94a3b8;font-size:.85em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+s.customers.join(', ')+'</span>';
      html+='</div>';
    });
    html+='</div>';

    /* Right: Go-Lives per Year */
    const glByYear={};
    sorted.filter(r=>r.goLive).forEach(r=>{
      const y='20'+r.goLive.slice(4);
      if(!glByYear[y])glByYear[y]={count:0,names:[]};
      glByYear[y].count++;
      glByYear[y].names.push(r.customer);
    });
    const years=Object.keys(glByYear).sort();
    html+='<div style="padding:10px 12px;border-left:1px solid #f1f5f9">';
    html+='<div style="font-size:.65em;font-weight:700;color:#475569;margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em">Go-Lives by Year</div>';
    years.forEach(y=>{
      const d=glByYear[y];
      html+='<div style="display:flex;align-items:center;gap:5px;padding:2px 0;font-size:.73em">';
      html+='<span style="font-weight:700;color:#334155;width:32px">'+y+'</span>';
      html+='<span style="font-weight:800;color:#059669;width:16px;text-align:center">'+d.count+'</span>';
      html+='<span style="color:#64748b;font-size:.85em">'+d.names.join(', ')+'</span>';
      html+='</div>';
    });
    html+='</div>';

    html+='</div>'; /* close 2-col mini grid */

    /* Section 3: Bar chart — onboarding time */
    html+='<div style="padding:10px 14px;border-top:1px solid #e2e8f0;flex:1">';
    html+='<div style="font-size:.68em;font-weight:700;color:#475569;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em">Onboarding Time</div>';
    if(completed.length>0){
      const maxM=Math.max(...completed.map(r=>r._months));
      completed.sort((a,b)=>a._months-b._months);
      completed.forEach(r=>{
        const pct=maxM>0?Math.round(r._months/maxM*100):0;
        const barColor=r._months<=3?'#059669':r._months<=6?'#0284c7':r._months<=12?'#d97706':'#dc2626';
        html+='<div style="display:flex;align-items:center;margin-bottom:4px;gap:5px">';
        html+='<div style="width:72px;font-size:.72em;font-weight:600;text-align:right;color:#334155;white-space:nowrap">'+esc(r.customer)+'</div>';
        html+='<div style="flex:1;background:#f1f5f9;border-radius:3px;height:17px;position:relative">';
        html+='<div style="width:'+Math.max(pct,8)+'%;background:'+barColor+';height:100%;border-radius:3px"></div>';
        html+='<span style="position:absolute;right:5px;top:0;font-size:.68em;font-weight:700;color:#334155;line-height:17px">'+r._months+'mo</span>';
        html+='</div></div>';
      });
    }
    html+='</div>';


    html+='</div>'; /* close col 3 */
    html+='</div>'; /* close 3-col grid */

    /* Audit log — collapsible source table */
    html+='<div style="margin-top:16px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">';
    html+='<div style="padding:8px 14px;background:#f8fafc;cursor:pointer;display:flex;align-items:center;gap:6px;font-size:.76em;font-weight:700;color:#475569" onclick="var b=this.nextElementSibling;var a=this.querySelector(\'.tgl\');if(b.style.display===\'none\'){b.style.display=\'\';a.textContent=\'\\u25BE\'}else{b.style.display=\'none\';a.textContent=\'\\u25B8\'}">';
    html+='<span class="tgl" style="font-size:1.1em">&#9656;</span> Data Sources & Audit Log</div>';
    html+='<div style="display:none">';
    html+='<table style="width:100%;border-collapse:collapse;font-size:.72em">';
    html+='<thead><tr style="border-bottom:2px solid #e2e8f0;background:#f8fafc">';
    html+='<th style="text-align:left;padding:5px 8px;color:#64748b;font-weight:600">Customer</th>';
    html+='<th style="text-align:left;padding:5px 8px;color:#64748b;font-weight:600">Field</th>';
    html+='<th style="text-align:left;padding:5px 8px;color:#64748b;font-weight:600">Value</th>';
    html+='<th style="text-align:left;padding:5px 8px;color:#64748b;font-weight:600">Source & Evidence</th>';
    html+='</tr></thead><tbody>';
    sorted.forEach((r,i)=>{
      const fields=[
        {field:'Deal Signed',val:r.dealSigned,src:r.srcDeal},
        {field:'Kickoff',val:r.kickoff,src:r.srcKickoff},
        {field:'Go-Live',val:r.goLive,src:r.srcGoLive}
      ];
      if(r.milestones){
        r.milestones.split(' | ').forEach(ms=>{
          const mt=ms.match(/^([^:]+):\s*(.+)/);
          if(mt)fields.push({field:'Milestone '+mt[1].trim(),val:'',src:mt[2].trim()});
          else fields.push({field:'Milestone',val:'',src:ms});
        });
      }
      const rowCount=fields.filter(f=>f.val||f.src).length;
      let first=true;
      fields.forEach(f=>{
        if(!f.val&&!f.src)return;
        const zebra=i%2===0?'background:#fafbfc;':'';
        const isMilestone=f.field.startsWith('Milestone');
        html+='<tr style="border-bottom:1px solid #f1f5f9;'+zebra+'">';
        if(first){
          html+='<td style="padding:4px 8px;font-weight:700;vertical-align:top" rowspan="'+rowCount+'">'+esc(r.customer)+'</td>';
          first=false;
        }
        html+='<td style="padding:4px 8px;color:'+(isMilestone?'#7c3aed':'#64748b')+';font-weight:'+(isMilestone?'600':'400')+'">'+f.field+'</td>';
        html+='<td style="padding:4px 8px;font-weight:600">'+(f.val||'—')+'</td>';
        html+='<td style="padding:4px 8px;color:#6b7280;max-width:500px">'+esc(f.src||'No source available')+'</td>';
        html+='</tr>';
      });
    });
    html+='</tbody></table>';
    html+='</div></div>';

    el.innerHTML=html;
  }

  function switchTab(tabName){
    document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===tabName));
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    const panel=document.getElementById('panel-'+tabName);
    panel.classList.add('active');
    document.querySelectorAll('.kpi-cell').forEach(c=>c.classList.toggle('kpi-active',c.dataset.tab===tabName));
    /* Auto-open the collapse inside the active tab */
    const hdr=panel.querySelector('.audit-header');
    const body=panel.querySelector('.audit-body');
    if(hdr&&body&&!body.classList.contains('open')){hdr.classList.add('open');body.classList.add('open')}
    /* Gantt collapse uses display:none (sticky needs no overflow:hidden in ancestors) */
    const gBody=document.getElementById('ganttCollapseBody');
    const gHdr=document.getElementById('ganttCollapseHdr');
    if(tabName==='gantt'&&gBody&&gHdr){gBody.style.display='';gHdr.classList.add('open');renderGantt()}
    /* Insights collapse uses display:none (same as Gantt — for sticky compatibility) */
    if(tabName==='insights'){renderInsights()}
    if(tabName==='implementation'){renderImplementation()}
    if(tabName==='analytics'){renderAnalytics()}
    /* Hide summary sections on Gantt/Scrum/Insights/Implementation/Analytics — show only on KPI tabs */
    const isFullscreen=tabName==='gantt'||tabName==='scrum'||tabName==='insights'||tabName==='implementation'||tabName==='analytics';
    const custSection=document.getElementById('customerKPISection');
    const topStrip=document.getElementById('topStrip');
    const memberCards=document.getElementById('memberCards');
    const auditSec=document.getElementById('auditSection');
    if(custSection)custSection.style.display=isFullscreen?'none':'';
    if(topStrip)topStrip.style.display=isFullscreen?'none':'';
    if(memberCards)memberCards.style.display=isFullscreen?'none':'';
    if(auditSec)auditSec.style.display=isFullscreen?'none':'';
    /* Render the newly active tab */
    render();
  }

  document.querySelectorAll('.tab').forEach(tab=>{
    tab.addEventListener('click',()=>switchTab(tab.dataset.tab));
  });

  /* KPI cells click → switch tab */
  document.querySelectorAll('.kpi-cell').forEach(cell=>{
    cell.addEventListener('click',()=>switchTab(cell.dataset.tab));
  });

  /* Generic collapse toggle for all audit-header elements */
  document.querySelectorAll('.audit-header').forEach(header=>{
    header.addEventListener('click',()=>{
      header.classList.toggle('open');
      const body=header.nextElementSibling;
      if(body&&body.classList.contains('audit-body'))body.classList.toggle('open');
      /* Gantt uses display:none instead of max-height (sticky needs no overflow:hidden) */
      if(body&&body.id==='ganttCollapseBody'){body.style.display=header.classList.contains('open')?'':'none'}
    });
    header.setAttribute('role','button');
    header.setAttribute('tabindex','0');
    header.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();header.click()}});
  });

  render();
}

init();
</script>
</body>
</html>"""

# Inject data and date
html = HTML.replace('__DATA__', data_json_safe).replace('__TIMELINE__', timeline_json_safe).replace('__KPI_IDS__', KPI_IDS_JSON).replace('__DATE__', build_date).replace('__LATEST_DATA__', latest_data_date).replace('__API_REFRESH__', api_refresh_date).replace('${BUILD_DATE}', build_date)

# C3: Atomic write
tmp_path = OUTPUT + '.tmp'
with open(tmp_path, 'w', encoding='utf-8') as f:
    f.write(html)
os.replace(tmp_path, OUTPUT)

print(f'Dashboard saved: {OUTPUT}')
print(f'Size: {len(html)//1024}KB')
print(f'Records: {len(data_raw)} | Core weeks: dynamically computed')
print(f'Build date: {build_date} | Latest data: {latest_data_date}')
