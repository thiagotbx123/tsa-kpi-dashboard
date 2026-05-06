# TSA KPI Dashboard

Sistema de métricas de performance do time TSA (Technical Solutions Architects) — TestBox.
Mede 3 KPIs para os membros ativos do squad **Raccoons** usando dados do **Linear API** + Google Sheets (backlog histórico congelado).

- **Owner:** Thiago Rodrigues (TSA Lead)
- **Versão:** v3.3 (2026-04-16, KPI External-only gate)

---

## Como o dashboard é servido

```
GitHub (main)
     │   push / merge
     ▼
GitHub Actions (.github/workflows/deploy.yml)
     │   SSH → ec2-user@<EC2_HOST>
     ▼
deploy/deploy.sh            (idempotent: pull, deps, restart units)
     │
     ▼
EC2 (Amazon Linux 2023)
     ├── nginx :80                          ──────────►  http://<ec2-ip>/KPI_DASHBOARD.html
     │       proxies all traffic to ↓
     ├── tsa-kpi.service                     (serve_kpi.py @ 127.0.0.1:8787)
     │       serves /, /KPI_DASHBOARD.html, POST /refresh
     └── tsa-kpi-refresh.timer               (weekdays 12:00 UTC = 09:00 BRT)
             ↓
         tsa-kpi-refresh.service             (orchestrate.py — full pipeline)
             ↓
         /opt/tsa-kpi/output/KPI_DASHBOARD.html
```

Ciclo completo:
1. Push para `main` no GitHub.
2. GHA conecta via SSH na EC2 e roda `deploy/deploy.sh`.
3. Script faz `git pull`, atualiza deps, recopia units, faz `daemon-reload`, reinicia o servidor HTTP, dispara um rebuild one-shot.
4. Timer continua rodando o pipeline diariamente em background.

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
    Output: $KPI_OUTPUT_DIR/KPI_DASHBOARD.html (default ~/Downloads)
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

## Desenvolvimento local (qualquer SO)

Pré-requisitos: Python 3.10+, `git`. **LINEAR_API_KEY** é opcional — sem ela, use `--build-only` com os dados commitados.

```bash
git clone https://github.com/thiagotbx123/tsa-kpi-dashboard.git
cd tsa-kpi-dashboard

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r scripts/kpi/requirements.txt

cp .env.example .env               # opcional, se for rodar pipeline completo
# edite .env e preencha LINEAR_API_KEY

# Rebuild rápido a partir do cache commitado:
python scripts/kpi/orchestrate.py --build-only

# Preview no navegador (http://localhost:8787):
python scripts/kpi/serve_kpi.py
```

### Comandos úteis

```bash
# Pipeline completo (precisa LINEAR_API_KEY)
python scripts/kpi/orchestrate.py

# Pular refresh da API (usar cache)
python scripts/kpi/orchestrate.py --skip-refresh

# Steps individuais
python scripts/kpi/refresh_linear_cache.py     # 1. Linear API
python scripts/kpi/merge_opossum_data.py        # 2. Merge
python scripts/kpi/normalize_data.py            # 3. Normaliza
python scripts/kpi/build_html_dashboard.py      # 4. Gera HTML
python scripts/kpi/upload_dashboard_drive.py    # 5. Upload Drive (opcional)

# XLSX executivo
python scripts/kpi/build_waki_dashboard.py

# Testes
pytest scripts/kpi/tests/test_kpi_calculations.py
```

---

## Deploy em produção (EC2)

A app vive em uma EC2 t3.micro (Amazon Linux 2023). Deploy é automatizado via GitHub Actions a cada merge em `main`. Bootstrap inicial é manual (uma vez).

### Bootstrap (uma vez por máquina)

SSH na EC2 e rode o instalador:
```bash
ssh -i ~/.ssh/kpi-app-key.pem ec2-user@<ec2-public-ip>
sudo dnf install -y git
sudo git clone https://github.com/thiagotbx123/tsa-kpi-dashboard.git /opt/tsa-kpi
bash /opt/tsa-kpi/deploy/install.sh
```

O script `install.sh`:
- Instala `nginx`, `python3`, `python3-pip`, `git`
- Cria venv em `/opt/tsa-kpi/.venv`, instala deps
- Copia systemd units (`tsa-kpi.service`, `tsa-kpi-refresh.service`, `tsa-kpi-refresh.timer`)
- Copia config do nginx (`/etc/nginx/conf.d/tsa-kpi.conf`)
- Faz build inicial com dados cacheados

Depois adicione a API key e habilite os services:
```bash
sudo -u ec2-user tee /opt/tsa-kpi/.env <<'EOF'
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
sudo chmod 600 /opt/tsa-kpi/.env

sudo systemctl enable --now tsa-kpi.service
sudo systemctl enable --now tsa-kpi-refresh.timer
```

Verifique:
```bash
sudo systemctl status tsa-kpi.service
sudo systemctl list-timers tsa-kpi-refresh.timer
curl -I http://localhost/KPI_DASHBOARD.html
```

Dashboard fica acessível em `http://<ec2-public-ip>/KPI_DASHBOARD.html`.

### GitHub Actions secrets

Em `Settings → Secrets and variables → Actions`, adicione:

| Secret | Valor |
|--------|-------|
| `EC2_HOST` | IP público (ou hostname) da EC2 |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | Conteúdo da chave privada `kpi-app-key.pem` (toda a chave incluindo `-----BEGIN/END-----`) |

A partir do próximo merge em `main`, o workflow `Deploy to EC2` faz: SSH → roda `deploy/deploy.sh` → rebuild → restart.

### Troubleshooting

```bash
# Logs do server
sudo journalctl -u tsa-kpi.service -f

# Logs do refresh
sudo journalctl -u tsa-kpi-refresh.service -n 200

# Disparar refresh manual
sudo systemctl start tsa-kpi-refresh.service

# Validar config nginx
sudo nginx -t

# Próxima execução agendada
sudo systemctl list-timers tsa-kpi-refresh.timer
```

---

## Estrutura

```
tsa-kpi-dashboard/
├── README.md
├── .env.example
├── .gitignore
├── .github/workflows/
│   └── deploy.yml                  ← GHA: SSH deploy on merge to main
├── deploy/
│   ├── install.sh                  ← bootstrap one-time na EC2
│   ├── deploy.sh                   ← chamado pelo GHA a cada deploy
│   ├── nginx.conf                  ← reverse proxy 80 → 8787
│   ├── tsa-kpi.service             ← systemd: serve_kpi.py
│   ├── tsa-kpi-refresh.service     ← systemd: orchestrate.py (one-shot)
│   └── tsa-kpi-refresh.timer       ← systemd: weekdays 12:00 UTC
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
│       ├── serve_kpi.py            ← HTTP server (porta 8787)
│       ├── requirements.txt
│       ├── CLAUDE.md               ← documentação técnica completa
│       ├── KPI_PLAYBOOK_FOR_CODA.md ← playbook publicado no Coda
│       ├── tests/
│       │   └── test_kpi_calculations.py
│       └── variants/               ← 10 variações de visualização (build_v1..v10.py)
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
| Deploy: GHA SSH → systemd | Sem dependências de laptops; 1 servidor; rebuild diário automatizado |

---

## Issues conhecidos

1. **Thais: Low KPI Measurability** — 79% das issues sem `dueDate` no Linear
2. **Spreadsheet Date Anomalies** — ~13 outliers (2019, durações negativas) mantidos
3. **KPI 3 (Reliability)** — não ativo até labels de rework serem adotadas no Linear
4. **HTTPS** — v1 serve apenas HTTP. Adicionar Let's Encrypt + domínio quando disponível.
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
