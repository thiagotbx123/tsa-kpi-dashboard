# WAKI KPI Dashboard — CLAUDE.md (Completo para Migracao)

## Sobre o Projeto

**WAKI KPI Dashboard** e o sistema de metricas de performance do time TSA (Technical Solutions Architects) do TestBox.
Mede 3 KPIs para 5 membros ativos do time Raccoons usando dados do Linear API + Google Sheets (backlog historico congelado).
Thais e Yasmim foram REMOVIDAS do KPI (decisao 2026-04-09).

**Owner:** Thiago Rodrigues (TSA Lead)
**Stakeholder:** Waki (Manager)
**Versao atual:** v3.2 (audit-hardened + UX fixes, 2026-04-13)

**IMPORTANTE — Leia `.claude/memory.md` PRIMEIRO para contexto atualizado.**

---

## Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.14+, CLI pipeline com subprocess |
| Frontend | HTML5 self-contained, Chart.js (CDN + fallback), CSS/JS embutido |
| Data Source | Linear GraphQL API (source of truth) + Google Sheets (backlog congelado) |
| Dependencias | `requests>=2.28`, `openpyxl>=3.1`, `pystray` + `PIL` (system tray) |
| Auth | `LINEAR_API_KEY` via `.env` |
| Output | `~/Downloads/KPI_DASHBOARD.html` (self-contained, ~1-2MB) |

---

## Estrutura Fisica do Projeto

O projeto esta **dividido em dois locais**:

### 1. Workspace (metadados + scripts de conveniencia)
```
C:/Users/adm_r/KPI_DASHBOARD/
├── CLAUDE.md                           # ESTE ARQUIVO
├── .claude/
│   └── memory.md                       # Estado persistente entre sessoes
├── preview.bat                         # Atalho Windows
├── run_pipeline.bat                    # Atalho para orchestrate.py
├── run_build_only.bat                  # Atalho --build-only
├── run_xlsx.bat                        # Atalho XLSX
└── sessions/                           # Historico de sessoes
```

### 2. Codigo-fonte (dentro do TSA_CORTEX)
```
C:/Users/adm_r/Tools/TSA_CORTEX/scripts/kpi/
├── orchestrate.py                      # Entry point — roda pipeline completo
├── refresh_linear_cache.py             # Step 1: Linear GraphQL API → cache JSON
├── merge_opossum_data.py               # Step 2: Merge Linear + Sheets + history analysis
├── normalize_data.py                   # Step 3: Data quality (fix dates, categories, perf)
├── build_html_dashboard.py             # Step 4: Gera HTML self-contained (~2800 linhas)
├── build_waki_dashboard.py             # Alternativa XLSX (openpyxl)
├── upload_dashboard_drive.py           # Step 5: Upload Google Drive (opcional)
├── team_config.py                      # SINGLE SOURCE OF TRUTH dos membros
├── serve_kpi.py                        # HTTP server local standalone (porta 8787)
├── kpi_dashboard.ico                   # Icone customizado do desktop shortcut
├── kpi_tray.py                         # System tray icon + ngrok tunnel
├── kpi_publish.bat                     # Shortcut Windows
├── requirements.txt                    # requests>=2.28, openpyxl>=3.1
├── implementation_timeline.json        # Dados de timeline para Gantt
├── tests/
│   └── test_kpi_calculations.py        # Testes unitarios
└── variants/                           # 10 variantes de visualizacao
    ├── build_v1_executive.py
    ├── build_v2_radar.py
    ├── build_v3_statistical.py
    ├── build_v4_evolution.py
    ├── build_v5_composition.py
    ├── build_v6_ranking.py
    ├── build_v7_scatter.py
    ├── build_v8_multiples.py
    ├── build_v9_waterfall.py
    └── build_v10_dark.py
```

### 3. Dados JSON (nivel acima dos scripts)
```
C:/Users/adm_r/Tools/TSA_CORTEX/scripts/
├── _kpi_all_members.json               # Cache Linear unificado (7 membros, ~7MB)
├── _dashboard_data.json                # Dataset merged final (~1.2MB, ~500 records)
├── _opossum_raw.json                   # Cache Opossum team
├── _raccoons_kpi.json                  # Cache Raccoons (compat)
├── _raccoons_thais.json                # Cache cross-team Thais (compat)
├── _kpi_data_complete.json             # Extracao Sheets (backlog congelado)
└── _db_data.json                       # DB_Data tab export
```

### 4. Output
```
~/Downloads/KPI_DASHBOARD.html              # Dashboard HTML principal
~/Downloads/RACCOONS_KPI_DASHBOARD_v2.xlsx  # XLSX executivo
~/Downloads/kpi-serve/kpi_tray.log          # Log do server
~/Downloads/kpi-serve/kpi_tray.pid          # PID (single instance)
```

---

## Caminhos Criticos

| O que | Caminho Absoluto |
|-------|-----------------|
| Scripts KPI | `C:/Users/adm_r/Tools/TSA_CORTEX/scripts/kpi/` |
| Dados JSON | `C:/Users/adm_r/Tools/TSA_CORTEX/scripts/` |
| .env (LINEAR_API_KEY) | `C:/Users/adm_r/Tools/TSA_CORTEX/.env` |
| Dashboard HTML | `C:/Users/adm_r/Downloads/KPI_DASHBOARD.html` |
| Dashboard XLSX | `C:/Users/adm_r/Downloads/RACCOONS_KPI_DASHBOARD_v2.xlsx` |
| Git repo | `C:/Users/adm_r/Tools/TSA_CORTEX/` |

---

## Pipeline de Dados (4+1 steps)

```
Step 1: refresh_linear_cache.py
    Linear GraphQL API → fetch 7 membros (por assigneeId + creatorId)
    Paginacao 100/page com cursor
    HTTP timeout 30s, safeguard de drop >50%
    Output: _kpi_all_members.json (~7MB)
        ↓
Step 2: merge_opossum_data.py
    Merge Linear cache + Sheets backlog congelado
    Deduplica issues, mapeia state IDs → nomes
    extract_history_fields(): deliveryDate, originalEta, rework, ownership
    Aplica D.LIE23 (ownership logic)
    Exclui parent tickets com subtasks (D.LIE19)
    Output: _dashboard_data.json (~500 records)
        ↓
Step 3: normalize_data.py
    Fix dates (2019→2025, short dates → ISO)
    Unifica customers (CUSTOMER_MAP)
    Normaliza categories (Internal/External)
    Normaliza B.B.C. variants
    Recalcula perf labels (On Time/Late/N-A)
    Deduplica Linear vs Sheets (D.LIE22)
    Output: _dashboard_data.json (cleaned)
        ↓
Step 4: build_html_dashboard.py
    Gera HTML self-contained (~2800 linhas de template)
    Chart.js via CDN + fallback
    Sanitiza JSON (H9: escape </script>)
    Injeta KPI_IDS de team_config.py
    Output: ~/Downloads/KPI_DASHBOARD.html
        ↓
Step 5 (opcional): upload_dashboard_drive.py
    Upload para Google Drive compartilhado
```

---

## 3 KPIs

| KPI | Nome | Formula | Alvo | Status |
|-----|------|---------|------|--------|
| **KPI 1** | ETA Accuracy | On Time / (On Time + Late) | >90% | ATIVO |
| **KPI 2** | Implementation Velocity | Avg(Delivery - Start) | <28 dias | ATIVO |
| **KPI 3** | Implementation Reliability | Done sem Rework / Total Done | >90% | NAO ATIVO (aguardando labels de rework) |

### Logica de Calculo
- **On Time**: entregue <= dueDate
- **Late**: entregue > dueDate
- **Not Started / No ETA**: excluidos do KPI 1 (nao acionaveis)
- **B.B.C. (Blocked By Customer)**: excluido de Overdue (D.LIE10)
- **Rework**: detectado quando ticket transiciona Done → In Progress (D.LIE20)
- **Delivery Date**: usa primeira transicao para In Review/Done do historico (nao apenas completedAt)
- **Admin-closed**: detectado e marcado On Time (D.LIE15)
- **Canceled**: sempre N/A (M3)

---

## Membros do Time (team_config.py — SINGLE SOURCE OF TRUTH)

```python
PERSON_MAP = {
    'Thaís Linzmaier': 'THAIS',
    'Yasmim Arsego': 'YASMIM',
    'Thiago Rodrigues': 'THIAGO',
    'Carlos Guilherme Matos de Almeida da Silva': 'CARLOS',
    'Alexandra Lacerda': 'ALEXANDRA',
    'Diego Cavalli': 'DIEGO',
    'Gabrielle Cupello': 'GABI',
}

PERSON_MAP_BY_ID = {
    'a6063009-d822-49f1-a638-6cebfe59e89e': 'THIAGO',
    'b13ca864-e0f4-4ff6-b020-ec3f4491643e': 'CARLOS',
    '19b6975e-3026-450b-bc01-f468ad543028': 'ALEXANDRA',
    '717e7b13-d840-41c0-baeb-444354c8ff91': 'DIEGO',
    'd9745bdb-7138-4345-9303-516aa6e4ec39': 'GABI',
    '0879df15-56d6-477f-944d-df033121641a': 'THAIS',
    'df4a6bcf-c519-469d-bb40-b1a0e93d0041': 'YASMIM',
}
```

**Squads**:
- **Raccoons**: Thiago, Carlos, Alexandra, Diego, Gabi
- **Opossum**: Thais, Yasmim

---

## State ID Mappings (merge_opossum_data.py)

Cada squad tem IDs diferentes para os mesmos estados no Linear:

### Opossum Team
| State ID | Nome |
|----------|------|
| c88c5a3a-2203-4a15-9801-51befb603c39 | Triage |
| 828cf5f3-d5f2-40d7-bc5b-4512e37171f0 | Backlog |
| 7d5ad714-3623-4ebf-8a6b-fb6cca398643 | Todo |
| c867261b-81c1-4b69-8f2b-0bfc836a3407 | In Progress |
| 3f6d0e12-8224-4329-954f-e9146816732f | In Review |
| 9315b082-63b4-4e74-a759-1c7b1403a2f8 | Done |
| e3d6167b-3328-42cd-9e22-d6ca18f003f3 | Canceled |
| fe43e265-1b90-4dc1-b8c5-bc6946dc6545 | Duplicate |

### Raccoons Team
| State ID | Nome |
|----------|------|
| ccc98f62-bc2a-475a-bcc8-0cdf0c81f8fc | Triage |
| 0a00ef8b-f3e2-4b1b-8413-1961c91fe495 | Backlog |
| ab5844ed-4edd-4d84-99fc-34ab37859486 | Todo |
| 8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b | In Progress |
| 89e4c72d-57aa-4774-8cf0-b00ee103d17c | In Review |
| 6e10418c-81fe-467d-aed3-d4c75577d16e | Done |
| 97ef043e-ccb7-4e2a-b75b-7542ef198abc | Canceled |
| bfe7e0e1-d403-4897-996a-5f839305e9e8 | Duplicate |
| c7a6728a-dee7-4e2b-a60f-476e699d4b54 | Paused |

---

## Linear API Details

### Endpoint
```
POST https://api.linear.app/graphql
Authorization: {LINEAR_API_KEY}
```

### Team IDs
- Opossum: `b3fb1317-885c-47a0-b87d-85a77252d994`
- Raccoons: `5a021b9f-bb1a-49fa-ad3b-83422c46c357`

### Queries usadas
- `QUERY_TEAM` — fetch por teamId (legacy, para completude)
- `QUERY_PERSON` — fetch por assigneeId (atribuicoes atuais)
- `QUERY_CREATOR` — fetch por creatorId (pega tickets reassigned)

### Campos extraidos por issue
identifier, title, description (truncado), url, branchName, createdAt, updatedAt, archivedAt, completedAt, dueDate, startedAt, slaStartedAt, slaMediumRiskAt, slaHighRiskAt, slaBreachesAt, slaType, state.name, labels, creator, assignee, project, milestone, comments (ultimos 5), history (completo)

---

## Dashboard HTML (Features)

### Tabs/Views
1. **Member Cards** — Stats pessoais (On Time %, Late %, Accuracy %, ETA coverage)
2. **ETA Accuracy Heatmap** — Pessoa x Semana, cor verde (on-time) / vermelho (late)
3. **Execution Time Chart** — Velocidade media por pessoa (bar chart)
4. **Reliability Tab** — Log de rework (Done → In Progress). Marcado NOT ACTIVE (C1)
5. **Team Activity Heatmap** — Volume de tasks por pessoa por semana
6. **Scrum Copy Tab** — Standup pre-formatado com listas por customer, copy-to-clipboard
7. **Insights Tab** — Observacoes analiticas, data quality notes
8. **Gantt Chart** — Timeline de implementacoes, actual vs projetado

### Filtros
- Por pessoa, categoria (Internal/External), mes
- Segmento: All / Internal / External
- Refresh button para update ao vivo

---

## Regras de Integridade de Dados (D.LIE Rules)

| Regra | Descricao |
|-------|-----------|
| D.LIE7 | Recalculo de perf label baseado em activity data |
| D.LIE10 | B.B.C. excluido de Overdue |
| D.LIE12 | ETA coverage exibido nos member cards |
| D.LIE14 | deliveryDate activity-based para velocity |
| D.LIE15 | Admin-closed detectado e marcado On Time |
| D.LIE17 | Not-started sem ETA = N/A |
| D.LIE19 | Parent tickets com subtasks excluidos |
| D.LIE20 | Rework = Done → In Progress (nao reassignment) |
| D.LIE21 | Reassignment em In Review = review handoff (normal) |
| D.LIE22 | Linear tickets substituem equivalentes do Sheets |
| D.LIE23 | Original assignee owns ticket se reassigned em review |

## Audit Rules (HTML/Build)

| Regra | Descricao |
|-------|-----------|
| H1 | isCoreWeek dinamico (data-driven, sem hardcode) |
| H9 | JSON sanitizado (`</script>` escaped) — previne XSS |
| H12 | CDN fallback para Chart.js com error handling |
| H13 | Clientes reais com category/demandType correto |
| H14/M15 | Sample size (n) exibido com percentuais |
| M3 | Canceled = sempre N/A |
| M5 | Clientes reais devem ser External |
| M6 | Customer mapping unificado (Gainsight = Staircase) |
| M8 | B.B.C. variants normalizados |
| M11 | Data staleness warning (build date vs latest data) |
| M14 | KPI_MEMBERS importado de team_config.py |
| L2 | JSON validation antes de processar |
| C3 | Atomic writes (`.tmp` + `os.replace()`) |
| P5 | Warn se records cair >50% entre refreshes |

---

## Customer Mapping (normalize_data.py)

```python
CUSTOMER_MAP = {
    'qbo': 'QuickBooks', 'quickbooks': 'QuickBooks',
    'intuit quickbooks': 'QuickBooks', 'intuit': 'QuickBooks',
    'qbo-wfs': 'WFS', 'wfs': 'WFS',
    'gong': 'Gong', 'gem': 'Gem', 'mailchimp': 'Mailchimp',
    'people.ai': 'People.ai', 'siteimprove': 'Siteimprove',
    'brevo': 'Brevo', 'archer': 'Archer', 'tropic': 'Tropic',
    'apollo': 'Apollo', 'callrail': 'CallRail',
    'hockeystack': 'HockeyStack', 'staircase': 'Staircase',
    'coda': 'Coda', 'general': 'General', 'outreach': 'Outreach',
    'gainsight': 'Staircase',  # Gainsight IS Staircase
    'tbx': 'TBX', 'tabs': 'Tabs', 'curbwaste': 'CurbWaste',
    'zuper': 'Zuper', 'bill': 'Bill',
}
```

---

## Date Conventions

- Formato ISO: `YYYY-MM-DD`
- Formato de semana: `YY-MM W.N` (ex: `26-03 W.2`)
- Calculo de semana: Custom (W1=dias 1-7, W2=8-14, etc.) — NAO e ISO week
- Range de semana: `MM/DD - MM/DD/YYYY` (Monday-Friday)
- Meses suportados: PT + EN + typos (jan, jab, fev, feb, mar, abr, apr, mai, may, etc.)
- Datas invalidas limpas: `tbd`, `n/a`, `-`, `na`, `none`, ``

---

## Como Rodar

### Pipeline completo (requer LINEAR_API_KEY)
```bash
cd C:/Users/adm_r/Tools/TSA_CORTEX
python scripts/kpi/orchestrate.py
```

### Pular refresh da API (usar cache)
```bash
python scripts/kpi/orchestrate.py --skip-refresh
```

### Somente rebuild do HTML
```bash
python scripts/kpi/orchestrate.py --build-only
```

### Steps individuais
```bash
python scripts/kpi/refresh_linear_cache.py     # 1. Puxa Linear API
python scripts/kpi/merge_opossum_data.py        # 2. Merge dados
python scripts/kpi/normalize_data.py            # 3. Normaliza
python scripts/kpi/build_html_dashboard.py      # 4. Gera HTML
python scripts/kpi/upload_dashboard_drive.py    # 5. Upload Drive (opcional)
```

### XLSX executivo
```bash
python scripts/kpi/build_waki_dashboard.py
```

### Preview local
```bash
python scripts/kpi/serve_kpi.py                # http://localhost:8787
python scripts/kpi/serve_kpi.py --port 9000    # Porta custom
```

### System tray (server + ngrok)
```bash
python scripts/kpi/kpi_tray.py
```

### Testes
```bash
pytest scripts/kpi/tests/test_kpi_calculations.py
```

---

## Environment Variables

### Obrigatorio
```
LINEAR_API_KEY=lin_api_xxxx    # Em C:/Users/adm_r/Tools/TSA_CORTEX/.env
```

### Opcionais
```
GOOGLE_CLIENT_ID=xxx            # Para upload Drive
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REFRESH_TOKEN=xxx
SLACK_USER_TOKEN=xoxp-xxx       # Para integracao Slack
SLACK_USER_ID=U0xxxx
```

---

## Google Sheets (Backlog Historico — CONGELADO)

| Sheet | ID | Uso |
|-------|----|----|
| TSA_Tasks_Consolidate | `1XaJgJCExt_dQ-RBY0eINP-0UCnCH7hYjGC3ibPlluzw` | Fonte DB |
| KPIS Raccoons | `1SPyvjXW9OJ4_CywHqroRwKbSbdGI98O0xxkc4y1Sy9w` | KPI tabs |

**IMPORTANTE**: Sheets e backlog historico congelado. Linear e a source of truth para dados atuais.

---

## Issues Conhecidos

1. **Thais: Low KPI Measurability** — 79% das issues sem dueDate no Linear → KPI1 baseado em ~4 tasks
2. **Yasmim: Moderate Sample Size** — 26% sem dueDate → borderline reliability
3. **Spreadsheet Date Anomalies** — ~13 outliers (datas 2019, duracoes negativas) mantidos como estao
4. **KPI 3 (Reliability)** — NAO ATIVO ate labels de rework serem adotados no Linear
5. **Edge case D.LIE23** — Cadeia A→B→C onde B implementa/C revisa → originalAssigneeId=A (nao B). Precisaria tracking de "assignee at In Review time" (P3)

---

## Decisoes Arquiteturais

| Decisao | Motivo |
|---------|--------|
| Linear = source of truth | Sheets congelado como backlog historico |
| createdAt = dateAdd | Linear nao tem campo separado de "date added" |
| Zero tolerancia On Time | delivery <= dueDate (exato, sem buffer de dias) |
| First In Review/Done = delivery | completedAt e proxy; transicao de history e mais precisa |
| Parent tickets excluidos | Contam subtasks (trabalho real), nao parents (coordenacao) |
| Original assignee = owner em review | Implementor mantem credito quando reassigned para revisao |
| HTML self-contained | Arquivo unico, funciona offline, facil de compartilhar |
| Atomic JSON writes | `.tmp` + `os.replace()` previne corrupcao em crash |
| Chart.js CDN + fallback | Lib leve, padrao, com degradacao graceful |
| Custom week calc (W1=1-7) | NAO usa ISO week (alinhado com formato do time) |

---

## Notas Especificas para Migracao

### Dependencias de Path
- Scripts em `TSA_CORTEX/scripts/kpi/`, dados em `TSA_CORTEX/scripts/` (nivel acima)
- Todos os scripts usam `SCRIPT_DIR` e `os.path.join(SCRIPT_DIR, '..')` para dados
- `.env` buscado em 2 locais: `TSA_CORTEX/.env` e `TSA_CORTEX/scripts/.env`
- Output hardcoded para `~/Downloads/`

### Acoplamentos
- `team_config.py` importado por `refresh_linear_cache.py`, `merge_opossum_data.py`, `build_html_dashboard.py`
- `orchestrate.py` executa scripts via `subprocess.run([PYTHON, script_path])` — nao importa modulos
- `build_html_dashboard.py` injeta JSON inline no HTML via template string (nao usa Jinja2)
- State IDs hardcoded em `merge_opossum_data.py` — acoplado ao Linear workspace especifico

### Dados que Precisam Migrar
- `_kpi_all_members.json` — cache (pode ser regenerado com API key)
- `_dashboard_data.json` — dataset merged (pode ser regenerado)
- `_kpi_data_complete.json` — backlog Sheets CONGELADO (NAO pode ser regenerado, manter)
- `_db_data.json` — DB_Data export (NAO pode ser regenerado, manter)
- `implementation_timeline.json` — dados de Gantt (manter)
- `.env` — API key (sensivel, manter seguro)

### O que NAO migrar
- `_opossum_raw.json`, `_raccoons_kpi.json`, `_raccoons_thais.json` — caches intermediarios, regeneraveis
- `~/Downloads/KPI_DASHBOARD.html` — output, regeneravel
- `~/Downloads/kpi-serve/` — runtime files

### Encoding
- Todos os scripts usam `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` na linha 2
- JSON files sao `utf-8`
- Nomes com acento: "Thaís" (i com acento), "Gabrielle" — encoding precisa ser preservado

---

## Regras de Ouro

1. **Nunca perca contexto** — Sempre leia `.claude/memory.md` primeiro
2. **Pipeline atomico** — Dados JSON usam write-then-rename (C3)
3. **Validacao de contagem** — Warn se records cair >50% entre refreshes (P5)
4. **Dados historicos intocaveis** — Sheets backlog e CONGELADO
5. **team_config.py e o single source of truth** para membros
6. **Sempre rode testes** antes de alterar logica de calculo: `pytest scripts/kpi/tests/`
7. **Nunca hardcode periodos de semana** — use H1 (isCoreWeek dinamico)
8. **JSON sanitizado obrigatorio** — H9 (escape `</script>`)
