# TSA KPI Dashboard

Sistema de métricas de performance do time TSA (Technical Solutions Architects) — TestBox.
Mede 3 KPIs para os membros ativos do squad **Raccoons** usando dados do **Linear API** + Google Sheets (backlog histórico congelado).

- **Owner:** Thiago Rodrigues (TSA Lead)
- **Versão:** v3.3 (2026-04-16, KPI External-only gate)

---

## A rotina do ícone "KPI Dashboard" (o "portal")

Quando o ícone do desktop é clicado, o seguinte acontece:

```
KPI Dashboard.lnk          (atalho Windows)
       │
       ▼
kpi_publish.bat            (scripts/kpi/kpi_publish.bat)
       │
       ▼
pythonw kpi_tray.py        (system tray icon — sem janela CMD)
       │
       ├── HTTP server local porta 8080  → http://localhost:8080/KPI_DASHBOARD.html
       ├── ngrok tunnel público           → https://<seu-subdominio>.ngrok-free.dev/KPI_DASHBOARD.html
       └── Auto-refresh weekdays 09:00   (puxa Linear API + rebuild)
```

O tray icon expõe um menu:

```
Open Dashboard                    ← abre URL ngrok
Open Local                        ← abre localhost:8080
─────────────────
Refresh & Rebuild (Linear API)    ← pipeline completo (~35s)
Quick Rebuild (cached data)       ← só rebuild do HTML (<1s)
─────────────────
Last refresh: HH:MM              ← timestamp dinâmico
HTTP: OK  |  ngrok: OK           ← status ao vivo
─────────────────
Exit
```

---

## Pipeline de dados (4+1 steps)

```
Step 1: refresh_linear_cache.py
    Linear GraphQL API → fetch issues por assigneeId + creatorId (paginação 100/page)
    Output: scripts/_kpi_all_members.json (~7MB)
        ↓
Step 2: merge_opossum_data.py
    Merge Linear cache + Sheets backlog congelado
    Aplica D.LIE19 (excluir parents) + D.LIE23 (ownership)
    Output: scripts/_dashboard_data.json (~500 records)
        ↓
Step 3: normalize_data.py
    Fix dates, unifica customers, normaliza categories, recalcula perf labels
    Output: scripts/_dashboard_data.json (limpo)
        ↓
Step 4: build_html_dashboard.py
    Gera HTML self-contained (~2800 linhas, ~1MB)
    Output: ~/Downloads/KPI_DASHBOARD.html
        ↓
Step 5 (opcional): upload_dashboard_drive.py
    Upload para Google Drive
```

---

## 3 KPIs

| # | Nome | Fórmula | Alvo | Status |
|---|------|---------|------|--------|
| KPI 1 | ETA Accuracy | On Time / (On Time + Late) | >90% | ATIVO |
| KPI 2 | Implementation Velocity | Avg(Delivery − Start) | <28 dias | ATIVO |
| KPI 3 | Implementation Reliability | Done sem Rework / Total Done | >90% | NÃO ATIVO (aguardando labels de rework) |

KPIs usam apenas tickets **External** (clientes reais). Internal é excluído via `getKPIFiltered()` — fix crítico de 2026-04-16.

---

## Instalação (Windows)

### Pré-requisitos
- **Python 3.10+** com `pythonw.exe` no `PATH` (instalador oficial: marcar "Add Python to PATH")
- **ngrok** ([download](https://ngrok.com/download)) com subdomínio reservado (free tier OK)
- **LINEAR_API_KEY** ([Linear Settings → API → Personal API keys](https://linear.app/settings/api))

### Setup
```powershell
# 1. Clone
git clone https://github.com/thiagotbx123/tsa-kpi-dashboard.git
cd tsa-kpi-dashboard

# 2. Dependências Python
pip install -r scripts/kpi/requirements.txt

# 3. Variáveis de ambiente
copy .env.example .env
# Edite .env e preencha LINEAR_API_KEY (e opcionalmente Google Drive / ngrok)

# 4. Build inicial (sem precisar de API key, usa dados commitados)
python scripts/kpi/orchestrate.py --build-only

# 5. Abrir o dashboard
start "" "%USERPROFILE%\Downloads\KPI_DASHBOARD.html"
```

### Atalho de desktop (opcional)
1. Botão direito no Desktop → Novo → Atalho
2. Local: `<repo>\scripts\kpi\kpi_publish.bat`
3. Ícone: `<repo>\scripts\kpi\kpi_dashboard.ico`
4. Propriedades → Executar: **Minimizada** (evita flash de CMD)

Duplo-clique → tray icon aparece, dashboard servido em http://localhost:8080.

---

## Como rodar

### Pipeline completo (precisa LINEAR_API_KEY)
```bash
python scripts/kpi/orchestrate.py
```

### Pular refresh da API (usar cache)
```bash
python scripts/kpi/orchestrate.py --skip-refresh
```

### Só rebuild do HTML (mais rápido)
```bash
python scripts/kpi/orchestrate.py --build-only
```

### Steps individuais
```bash
python scripts/kpi/refresh_linear_cache.py    # 1. Puxa Linear API
python scripts/kpi/merge_opossum_data.py       # 2. Merge dados
python scripts/kpi/normalize_data.py           # 3. Normaliza
python scripts/kpi/build_html_dashboard.py     # 4. Gera HTML
python scripts/kpi/upload_dashboard_drive.py   # 5. Upload Drive (opcional)
```

### XLSX executivo
```bash
python scripts/kpi/build_waki_dashboard.py
# Output: ~/Downloads/RACCOONS_KPI_DASHBOARD_v2.xlsx
```

### Preview local sem tray
```bash
python scripts/kpi/serve_kpi.py                # http://localhost:8787
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

## Estrutura

```
tsa-kpi-dashboard/
├── README.md                       ← este arquivo
├── .env.example                    ← template de credenciais
├── .gitignore
├── scripts/
│   ├── _kpi_all_members.json       ← cache Linear (regenerável)
│   ├── _dashboard_data.json        ← dataset merged
│   ├── _kpi_data_complete.json     ← Sheets backlog CONGELADO
│   ├── _db_data.json               ← DB_Data export CONGELADO
│   └── kpi/
│       ├── orchestrate.py          ← entry point do pipeline
│       ├── refresh_linear_cache.py ← Step 1
│       ├── merge_opossum_data.py   ← Step 2
│       ├── normalize_data.py       ← Step 3
│       ├── build_html_dashboard.py ← Step 4 (~2800 linhas template)
│       ├── upload_dashboard_drive.py ← Step 5
│       ├── build_waki_dashboard.py ← XLSX alternativo
│       ├── team_config.py          ← SINGLE SOURCE OF TRUTH dos membros
│       ├── serve_kpi.py            ← HTTP server standalone
│       ├── kpi_tray.py             ← system tray + ngrok
│       ├── kpi_publish.bat         ← shortcut Windows (portável)
│       ├── kpi_dashboard.ico       ← ícone customizado
│       ├── requirements.txt
│       ├── CLAUDE.md               ← documentação técnica completa
│       ├── KPI_PLAYBOOK_FOR_CODA.md ← playbook publicado no Coda
│       ├── tests/
│       │   └── test_kpi_calculations.py
│       └── variants/               ← 10 variações de visualização
│           ├── build_v1_executive.py
│           ├── build_v2_radar.py
│           └── ... (v3-v10)
```

---

## Squads e membros

### Raccoons (5 ativos no KPI)
- Thiago Rodrigues
- Carlos Guilherme Matos de Almeida da Silva
- Alexandra Lacerda
- Diego Cavalli
- Gabrielle Cupello

### Opossum (removidos do KPI em 2026-04-09)
- Thaís Linzmaier
- Yasmim Arsego

Edite `scripts/kpi/team_config.py` para alterar o roster — esse arquivo é a **única fonte de verdade**.

---

## Decisões arquiteturais

| Decisão | Motivo |
|---------|--------|
| Linear = source of truth | Sheets congelado como backlog histórico |
| Zero tolerância On Time | `delivery <= dueDate` (sem buffer de dias) |
| First In Review/Done = delivery | Mais preciso que `completedAt` |
| Parent tickets excluídos | Subtasks contam o trabalho real (D.LIE19) |
| Original assignee = owner em review | Implementor mantém crédito quando reassigned (D.LIE23) |
| HTML self-contained | Funciona offline, fácil de compartilhar |
| Atomic JSON writes | `.tmp` + `os.replace()` previne corrupção |
| Custom week calc (W1=1-7) | Alinhado com formato do time, NÃO ISO week |
| Rework = label-only | Histórico Done→In Progress dava false positives (fix 2026-04-13) |
| Default segment = ALL, KPIs = External-only | `getKPIFiltered()` separa audit table de KPIs (fix 2026-04-16) |

---

## Issues conhecidos

1. **Thais: Low KPI Measurability** — 79% das issues sem `dueDate` no Linear
2. **Spreadsheet Date Anomalies** — ~13 outliers (2019, durações negativas) mantidos
3. **KPI 3 (Reliability)** — não ativo até labels de rework serem adotadas no Linear
4. **ngrok URL hardcoded como fallback** — pendente mover 100% para `.env` (F-A07-02)
5. **Audit findings pendentes** — 12 itens documentados em `scripts/kpi/CLAUDE.md`

---

## Documentação técnica completa

Veja `scripts/kpi/CLAUDE.md` para:
- Detalhes das 11 regras D.LIE (Data Integrity)
- 14 regras de audit (H1-H14, M3-M15, etc.)
- State ID mappings dos times Opossum/Raccoons no Linear
- Customer mapping completo
- Date conventions
- Edge cases conhecidos

---

## Licença / Uso

Projeto interno TestBox. Não distribuir externamente.
