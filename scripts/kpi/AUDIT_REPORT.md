# KPI Dashboard — Data Audit Report

**Date**: 2026-03-18
**Scope**: TSA Waki KPI Dashboard (3 indicators, 7 members, Dec 2025 — Mar 2026)

---

## Data Sources

| Source | Members | Records | Method |
|--------|---------|---------|--------|
| Google Sheets (TSA_Tasks_Consolidate) | Alexandra, Carlos, Diego, Gabi, Thiago | 414 | DB_Data tab extraction |
| Linear — Opossum team | Thais, Yasmim | 75 | API query, full team |
| Linear — Raccoons team | Thais (only) | 3 | API query, filtered by assignee |
| **TOTAL** | **7** | **492** | |

## KPI Measurability per Person

| Person | Total | KPI1 Measurable | KPI2 Measurable | KPI3 Measurable | Data Quality |
|--------|-------|-----------------|-----------------|-----------------|--------------|
| Alexandra | 61 | 43 (70%) | 43 (70%) | 46 (75%) | GOOD |
| Carlos | 133 | 104 (78%) | 105 (79%) | 121 (91%) | GOOD |
| Diego | 44 | 31 (70%) | 31 (70%) | 34 (77%) | GOOD |
| Gabi | 61 | 36 (59%) | 39 (64%) | 42 (69%) | MODERATE |
| Thiago | 115 | 85 (74%) | 85 (74%) | 95 (83%) | GOOD |
| **Thais** | **47** | **4 (9%)** | **20 (43%)** | **7 (15%)** | **LOW** |
| **Yasmim** | **31** | **10 (32%)** | **11 (35%)** | **12 (39%)** | **MODERATE** |

## Known Issues

### 1. THAIS — Low KPI Measurability (CRITICAL)
- **Problem**: 37/47 issues (79%) have NO dueDate in Linear
- **Impact**: KPI1 accuracy based on 4 tasks only, KPI3 on 7 tasks — statistically unreliable
- **Root cause**: Opossum team does not consistently set due dates
- **Fix**: Set dueDates on existing Linear issues for Thais
- **KPI2 is OK**: 20 tasks have both dateAdd and delivery date

### 2. YASMIM — Moderate Sample Size
- **Problem**: 8/31 issues (26%) have no dueDate
- **Impact**: KPI1 based on 10 tasks, KPI3 on 12 — borderline reliable
- **Recommendation**: Continue using, but note low confidence

### 3. Spreadsheet Date Anomalies (Existing Data)
These come from the source spreadsheet and were NOT introduced by our processing:

| Issue | Person | Detail |
|-------|--------|--------|
| 2563-day duration | Gabi | dateAdd=2019-12-12 (wrong year), delivery=2026-12-18 |
| 365-day durations (x3) | Gabi, Carlos | Likely year typos (2025 → 2026 or vice versa) |
| Negative durations (x5) | Carlos | delivery before dateAdd — data entry errors |
| Negative durations (x4) | Diego | delivery 3 days before dateAdd |
| Negative duration (x1) | Gabi | delivery 5 days before dateAdd |
| 6 empty-week records | Carlos, Gabi, Thiago | No dateAdd in spreadsheet |

**Decision**: Left as-is. These are source data issues. Cleaning them requires manual verification with the team. The dashboard shows them transparently.

### 4. Week Assignment Methodology Difference
- **Spreadsheet members**: Week from DB_Data tab (manually assigned by Waki)
- **Linear members (Thais, Yasmim)**: Week computed from `createdAt` date
- **Impact**: Minor — at most 1 week difference in some edge cases
- **Recommendation**: Acceptable for now. When all data moves to Linear, unify to a single method.

### 5. Parent + Sub-Issue Counting
- Both parent issues AND sub-issues are counted for Thais (27 parents, 20 subs) and Yasmim (6 parents, 25 subs)
- This matches the spreadsheet methodology where each row = 1 task regardless of hierarchy
- **No change needed**

### 6. Unassigned Opossum Issues (37 of 113)
- Not counted in anyone's KPIs — correct behavior
- Mostly Backlog/Todo/Canceled items
- **No action needed** unless these get assigned

### 7. Diego's Opossum Issue (OPO-116)
- 1 issue assigned to Diego in Opossum team, but Diego's data comes from the spreadsheet
- Not double-counted; it's simply invisible in the dashboard
- **Low risk**: 1 issue out of Diego's 44 total

## Assumptions Made

| # | Assumption | Risk | Mitigation |
|---|-----------|------|------------|
| 1 | `createdAt` = dateAdd for Linear issues | LOW | Linear has no separate "date added" field; createdAt is the closest equivalent |
| 2 | 7-day tolerance for "On Time" | LOW | Matches the spreadsheet KPI Guide (S9 formula) |
| 3 | Customer extracted from `[brackets]` in title | LOW | Covers 95%+ of Opossum issues; verified manually |
| 4 | `In Review` mapped to `In Progress` | LOW | Both represent active work |
| 5 | `Backlog` and `Triage` mapped to `To do` | LOW | Both represent unstarted work |
| 6 | `completedAt` = delivery date | MEDIUM | Some issues might be marked done before actual delivery |

## Files Inventory

| File | Purpose | Size |
|------|---------|------|
| `_dashboard_data.json` | Merged dataset (492 records) | ~195KB |
| `_opossum_raw.json` | Cached Opossum Linear issues | ~85KB |
| `_raccoons_thais.json` | Cached Raccoons issues for Thais | ~1KB |
| `_kpi_data_complete.json` | Fresh extraction from 4 spreadsheet tabs | ~170KB |
| `_db_data.json` | DB_Data tab export (439 records) | ~134KB |
| `kpi/build_html_dashboard.py` | HTML dashboard generator (v2) | ~12KB |
| `kpi/build_waki_dashboard.py` | XLSX dashboard generator | ~15KB |
| `kpi/merge_opossum_data.py` | Linear → dashboard merge script | ~6KB |
| `kpi/kpi_auth.py` | Google OAuth + sheet IDs | ~2KB |

## Recommendations

1. **Immediate**: Set dueDates on Thais's Linear issues (37 missing)
2. **Short-term**: Establish SOP requiring dueDate on all Opossum issues
3. **Medium-term**: Migrate spreadsheet members to Linear-only tracking (single source of truth)
4. **Clean data**: Review the 13 outlier/negative duration records with the team
5. **Automate**: Schedule weekly dashboard regeneration pulling fresh data from both sources
