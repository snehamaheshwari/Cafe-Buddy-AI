# ☕ Cafe Buddy AI

> **An end-to-end AI-powered café intelligence platform** — transforms raw sales, menu, customer, and review data into actionable insights, ML-driven decisions, and real-time AI assistance.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-aicafebuddy.com-brightgreen?style=for-the-badge)](https://aicafebuddy.com)
[![Deploy on Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet?style=for-the-badge&logo=railway)](https://railway.app)
[![GitHub Repo](https://img.shields.io/badge/Repo-snehamaheshwari%2FCafe--Buddy--AI-black?style=for-the-badge&logo=github)](https://github.com/snehamaheshwari/Cafe-Buddy-AI)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)](https://react.dev)

---

## 📌 Table of Contents

1. [What Is Cafe Buddy AI?](#1-what-is-cafe-buddy-ai)
2. [Feature Modules](#2-feature-modules)
3. [Technology Stack](#3-technology-stack)
4. [ML Models & AI Engines](#4-ml-models--ai-engines)
5. [Data Flow](#5-data-flow)
6. [RBAC & Security](#6-rbac--security)
7. [Project Structure](#7-project-structure)
8. [Local Development](#8-local-development)
9. [Deployment (Railway)](#9-deployment-railway)
10. [API Reference](#10-api-reference)
11. [Environment Variables](#11-environment-variables)
12. [Login Credentials (Demo)](#12-login-credentials-demo)

---

## 1. What Is Cafe Buddy AI?

Cafe Buddy AI is a **full-stack SaaS intelligence platform for café owners and managers**. It ingests data from five independent channels (POS exports, menu catalogues, customer records, online reviews, financial reports), runs ML models and AI analytics on that data, and surfaces results through an intuitive role-gated dashboard.

**Core capabilities:**
- Upload your café data → the system learns your specific patterns
- ML-driven revenue forecasts, dynamic pricing, and cross-sell recommendations on *your* items
- AI generates data-driven decisions; you approve/reject → approved ones flow to AI-Powered Execution
- Claude-powered AI chatbot that understands your uploaded data context
- Competitive Market Radar comparing your café against 100+ real Indian café competitors
- Full RBAC (role-based access) with audit logging on every user action

---

## 2. Feature Modules

The platform is organised into **11 role-gated modules** across the café intelligence pipeline:

### 📊 Dashboard (Home)
Real-time KPIs computed entirely from uploaded data:
- Revenue, Orders, Average Ticket, Gross Margin % with period-over-period change
- Platform split chart (Zomato / Swiggy / Dine-in / others)
- Peak Hours heatmap by day-of-week × hour
- XGBoost 30-day revenue forecast with ±15% confidence band
- Falls back to animated mock data when no upload is present

### 📥 Upload My Data
Five independent upload channels, each with a **Download CSV Template** button:

| Dataset | Key Columns | Used By |
|---------|-------------|---------|
| **POS Sales** | order_id, item_name, bill_amount, cost, date, hour, platform, discount | All ML models, KPIs, Decision Engine |
| **Financial** | date, revenue, expense, profit, tax | Dashboard KPIs |
| **Customer** | customer_id, name, visits, lifetime_spend, segment | Customer Segmentation |
| **Reviews** | review_text, rating, date, platform | Sentiment Engine |
| **Menu** | item, base_price, category, season, veg/non-veg, SKU | Dynamic Pricing filter |

Features: append / replace mode, live record count, column auto-detection with 30+ alias mappings per field.

### 🔧 Reports & Insights (Data Engineering)
- Automatic column normalisation across 30+ header aliases per field
- Data quality summary: row counts, missing values, date range
- Platform & category breakdowns with bar charts
- Pre-built insight cards: top/bottom revenue items, margin leaders, high-volume SKUs

### 🤖 Smart Analytics (AI / ML Intelligence)
Seven ML-powered sections driven by uploaded data:

| Section | Model | Input |
|---------|-------|-------|
| Revenue Forecast | XGBoost (600 trees, MAPE 7.83%) | Uploaded POS |
| Platform Forecast | Ridge regressors per platform | Uploaded POS |
| Peak Hour Classifier | Random Forest | Uploaded POS |
| Cancellation Risk | XGBoost classifier | Uploaded POS |
| Cross-sell Recommendations | Apriori (lift ≥ 1.5, conf ≥ 5%) | Uploaded POS + pre-trained rules |
| Dynamic Pricing Suggestions | Margin-tier analysis | Uploaded POS + Menu |
| Model Comparison | Accuracy / MAPE table | All models |

**Dynamic Pricing** — fully data-driven, no hardcoding:
- `margin ≥ 55%` → **Increase +8%** (very healthy margin)
- `margin 40–55%` → **Increase +5%** (solid margin)
- `margin 25–40%` → **Hold** (price is near-optimal)
- `margin < 25%` → **Review** (cost audit needed — shows reason)
- Items absent from the uploaded menu catalogue are excluded

### 🧠 What To Do Next (Decision Engine)
- Auto-generates decisions from live POS analytics (no hardcoded values)
- Decision categories: Pricing, Inventory, Marketing, Operations, Staffing
- One-click Approve / Reject with confirmation dialog
- Approved decisions flow to AI-Powered Execution

### ⚡ AI-Powered Execution
- Lists approved decisions from the Decision Engine
- Supplemented by XGBoost model action alerts
- Full action log with timestamps and source attribution

### 💬 Ask Cafe Buddy (AI Chatbot)
- Streaming responses via Claude API (Anthropic)
- Falls back to smart analytics engine when no API key is set
- Context-aware: reads uploaded POS / review data before answering
- DuckDuckGo live web search for competitor and festival queries
- Indian festival calendar (2026) with menu and promo ideas per festival

### 🔍 Market Radar (Peer Comparison)
- Pre-loaded competitor database: 10 Indian cities, 30+ areas, 100+ cafés
- Live DuckDuckGo search for up-to-date competitor info
- AI-powered competitive analysis via Claude API
- Radar chart: 6-dimension score (rating, value, variety, delivery, ambience, social presence)

### 📱 WhatsApp Alerts
- Green API integration for WhatsApp Business notifications
- Pre-built templates: daily revenue digest, low-stock alert, peak hour reminder
- Preview before sending

### 👥 Role Management (RBAC)
Three built-in non-deletable roles:

| Role | Permissions |
|------|-------------|
| `admin` | All 11 modules including Role Management & Audit Logs |
| `sub_admin` | Dashboard, Data, Analytics, Decisions, Chatbot, Market Radar |
| `viewer` | Dashboard only |

Admin can create custom roles with granular per-feature toggles. Persisted to `data/roles.json`.

### 📋 Audit Log
- Every authenticated action logged (HTTP middleware + explicit calls)
- Columns: Timestamp, User, Role, Module, Action, Status, Duration (ms), IP
- Filter by module / status, CSV export, full-text search
- Persisted to `data/audit_log.json` on the Railway volume

---

## 3. Technology Stack

### Backend
| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.104.1 | REST API framework, 50+ routes |
| Uvicorn | 0.24.0 | ASGI server |
| Pydantic | 2.5.0 | Request/response validation |
| Pandas | 2.1.4 | Data processing & Excel/CSV parsing |
| Scikit-learn | ≥1.3.0 | Ridge regression, Random Forest, Logistic Regression |
| XGBoost | ≥1.7.0 | Revenue forecast & cancellation risk |
| NLTK | ≥3.8.0 | NLP tokenisation & stopword removal |
| Joblib | ≥1.3.0 | XGBoost model serialisation |
| OpenPyXL | 3.1.2 | Excel file parsing |
| Anthropic SDK | ≥0.34.0 | Claude AI chatbot & Market Radar analysis |
| DuckDuckGo Search | ≥6.0.0 | Live web search in chatbot & peer comparison |

### Frontend
| Package | Version | Purpose |
|---------|---------|---------|
| React | 18.2 | UI framework |
| TypeScript | 5.3 | Type safety |
| Vite | 5.0 | Build tool & dev server |
| React Router | 6.20 | SPA routing + permission guards |
| Recharts | 2.10 | Charts (line, bar, radar, heatmap) |
| Tailwind CSS | 3.3 | Utility-first styling |
| Lucide React | 0.294 | Icon set |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerisation | Docker (2-stage: Node 18 Alpine → Python 3.11 slim) |
| Hosting | Railway (auto-deploy from GitHub `main` branch) |
| Persistent storage | Railway Volume at `/app/backend/data` |
| Domain | `aicafebuddy.com` (Railway custom domain) |
| Code versioning | GitHub (`snehamaheshwari/Cafe-Buddy-AI`) |

---

## 4. ML Models & AI Engines

All model files live in `backend/models/`:

```
backend/models/
├── xgboost_model.joblib         XGBoost revenue forecast
│                                600 trees | MAPE 7.83% | MAE ₹5,153 | RMSE ₹6,064
│                                Trained on 100K CafeBuddy transactions
│
├── cross_sell_rules.pkl         Apriori association rules
│                                1698 total rules; 8 qualify at lift≥1.5, conf≥5%
│                                Top rule: Masala Omelette → Lemonade (lift 2.08)
│
├── sentiment_model.pkl          Logistic Regression sentiment classifier
├── tfidf_vectorizer.pkl         TF-IDF vectoriser for review text
├── label_encoder.pkl            Negative | Neutral | Positive label mapping
│
├── demand_forecast_model.pkl    Item-level demand forecaster
├── item_popularity_model.pkl    Item popularity scorer
├── price_optimisation_table.csv Base elasticity reference table
├── model_card_heenu.json        Model metadata and evaluation card
└── xgb_insights/                XGBoost SHAP feature importance data
```

### Sentiment Analysis Pipeline
```
Review text
  → NLTK tokenise + stopword removal
  → TF-IDF vectorise (tfidf_vectorizer.pkl)
  → Logistic Regression predict (sentiment_model.pkl)
  → Confidence score + Negative / Neutral / Positive label
  → Aspect extraction across 5 dimensions:
      Food & Menu | Service | Ambiance | Price/Value | Wait Time
  → NPS score + keyword cloud + sentiment trend over time
```

### Revenue Forecast Pipeline
```
Uploaded POS data
  → Aggregate daily revenue totals
  → Compute lag features (7-day, 14-day, 28-day lags)
  → Compute rolling mean + rolling std features
  → XGBoost inference (xgboost_model.joblib)
  → Scale output to café's actual revenue range
  → 30-day forecast + ±15% confidence band
```

### Cross-sell Recommendation Pipeline
```
Apriori model (1698 rules)
  → Apply quality gates: lift ≥ 1.5 AND confidence ≥ 0.05 (5%)
  → Filter: both antecedent AND consequent present in uploaded POS items
  → Sort by lift descending → return top 10
  → Fallback (no menu match): mine co-occurrence from POS order_id groups
      (items sharing the same order_id = bought together)
  → Fallback also applies lift ≥ 1.5, conf ≥ 0.05 gates
```

---

## 5. Data Flow

```
OWNER uploads data
       │
       ▼
POST /api/upload/{type}
       │
       ├─ Validate column headers (30+ alias mappings per field)
       ├─ Normalise rows → [{date, item_name, revenue, cost, qty, ...}]
       ├─ Persist to /app/backend/data/{type}.json (Railway Volume)
       └─ Return record count + field mapping summary
       │
       ▼
GET /api/dashboard/overview
       │
       ├─ _calc_kpis(pos_data)      ← period-over-period splits from POS
       ├─ XGBoost forecast          ← lag/rolling features → inference
       ├─ platform_breakdown()      ← group by platform, sum revenue
       └─ peak_hours()              ← group by hour × weekday
       │
       ▼
GET /api/ml/dynamic-pricing
       │
       ├─ Load menu_data (_menu_data)     ← menu catalogue filter
       ├─ Load pos_data  (_pos_data)      ← actual sales
       ├─ Aggregate POS by item           ← revenue, cost, quantity, dates
       ├─ Skip items not in menu          ← menu_item_set filter
       ├─ Compute margin from real data   ← (rev - cost) / rev
       ├─ Assign tier: Increase/Hold/Review
       └─ Return up to 15 suggestions sorted by impact
       │
       ▼
GET /api/layer4/decisions
       │
       ├─ _generate_decisions(pos_data)  ← derived from uploaded analytics
       ├─ Merge with _decision_overrides ← approved/rejected state
       └─ Return decision list with status
       │
POST /api/layer4/decisions/{id}/approve
       │
       ├─ Store in _decision_overrides["approved"]
       ├─ Log to audit_store
       └─ Decision appears in /api/layer5/autonomous-actions
```

---

## 6. RBAC & Security

### Authentication
- Session stored in `localStorage` as `{username, role, permissions[]}`
- `GET /api/auth/me` re-validates session on every page load and tab focus
- `X-Username` and `X-Role` headers injected by `apiFetch.ts` wrapper on every request

### Permission Gates
- **Backend**: `role_store.py` checks permission arrays before sensitive writes
- **Frontend**: `<PermissionRoute feature="...">` in `App.tsx` redirects to `/` if permission absent
- **Audit middleware**: every authenticated non-polling request logged with user, role, action, HTTP status, duration

### Permission Keys
```
dashboard         upload_data       reports           analytics
decision_engine   auto_pilot        chatbot           market_radar
whatsapp_alerts   role_management   audit_logs
```

### Storage
All user/role data persisted to `data/roles.json` on the Railway Volume — survives deploys and container restarts.

---

## 7. Project Structure

```
cafe-buddy/
│
├── Dockerfile                     2-stage build: Node 18 (React) + Python 3.11 (API)
├── railway.toml                   Railway: dockerfile builder + restart-on-failure policy
├── .dockerignore                  Excludes node_modules, dist, __pycache__, .env, data/
│
├── backend/
│   ├── main.py                    FastAPI app entry point — 50+ REST routes, audit middleware
│   ├── ml_models.py               All ML inference: XGBoost, Apriori, RF, Ridge, pricing logic
│   ├── data_store.py              Shared mutable state + JSON persistence helpers
│   ├── multi_upload.py            5-dataset upload router (POS/Financial/Customer/Reviews/Menu)
│   ├── sentiment_engine.py        LR sentiment model, TF-IDF, aspect analysis, NPS computation
│   ├── chatbot.py                 Claude API streaming chatbot + DuckDuckGo web search
│   ├── peer_comparison.py         Competitor DB (100+ cafés) + live search + AI analysis
│   ├── role_store.py              RBAC: role definitions, permissions, user management
│   ├── audit_store.py             Audit log: write events, query, export CSV
│   ├── cafe_os_models.py          Decision Engine action models and CafeOS helpers
│   ├── requirements.txt           Python dependencies
│   │
│   ├── models/                    Pre-trained ML model files
│   │   ├── xgboost_model.joblib   Primary revenue forecast model
│   │   ├── cross_sell_rules.pkl   Apriori association rules (1698 rules)
│   │   ├── sentiment_model.pkl    Logistic Regression sentiment classifier
│   │   ├── tfidf_vectorizer.pkl   TF-IDF vectoriser
│   │   ├── label_encoder.pkl      Sentiment label encoder
│   │   ├── demand_forecast_model.pkl
│   │   ├── item_popularity_model.pkl
│   │   ├── price_optimisation_table.csv
│   │   ├── model_card_heenu.json
│   │   └── xgb_insights/         SHAP feature importance
│   │
│   ├── data/                      Runtime data (Railway Volume mount point)
│   │   ├── pos.json               Uploaded POS data
│   │   ├── financial.json         Uploaded financial data
│   │   ├── customer.json          Uploaded customer data
│   │   ├── reviews.json           Uploaded review data
│   │   ├── menu.json              Uploaded menu catalogue
│   │   ├── roles.json             RBAC roles and users
│   │   └── audit_log.json         Full audit trail
│   │
│   └── tests/                     39 unit tests across all modules
│       ├── test_no_hardcoding.py  Verifies no hardcoded KPI/decision values
│       ├── test_ml_models.py      ML model inference tests
│       ├── test_data_store.py     Persistence layer tests
│       ├── test_sentiment.py      Sentiment engine tests
│       ├── test_upload.py         Upload parsing + alias detection
│       └── ...
│
└── frontend/
    ├── src/
    │   ├── App.tsx                Routing + PermissionRoute guards + auth wrappers
    │   ├── context/
    │   │   ├── AuthContext.tsx    User session, hasPermission(), /api/auth/me polling
    │   │   └── SidebarContext.tsx Sidebar open/close state
    │   ├── lib/
    │   │   └── api.ts             Typed API client (auth, upload, ml, templates, peers)
    │   ├── utils/
    │   │   └── apiFetch.ts        Fetch wrapper injecting X-Username / X-Role headers
    │   ├── components/
    │   │   ├── Sidebar.tsx        Navigation — RBAC-aware (hides unauthorised items)
    │   │   ├── Header.tsx         Top bar with user info and logout
    │   │   └── StatCard.tsx       Reusable KPI card with trend arrow
    │   └── pages/
    │       ├── Dashboard.tsx      KPIs, forecast chart, platform breakdown
    │       ├── DataCollection.tsx 5-section upload UI with template download per type
    │       ├── DataEngineering.tsx Data quality, column map, insight cards
    │       ├── AIMLIntelligence.tsx 7 ML sections: forecast, pricing, cross-sell, etc.
    │       ├── DecisionEngine.tsx Data-driven decisions with approve / reject
    │       ├── CafeOS.tsx         AI-Powered Execution action feed
    │       ├── Chatbot.tsx        Streaming AI chat interface
    │       ├── PeerComparison.tsx Competitor radar chart + AI analysis
    │       ├── WhatsAppNotifications.tsx
    │       ├── RoleManagement.tsx Full RBAC admin UI
    │       └── AuditLog.tsx       Filterable audit trail with CSV export
    ├── package.json
    └── vite.config.ts             /api proxy → backend:8000 in dev mode
```

---

## 8. Local Development

### Prerequisites
- Node.js 18+, Python 3.11+, Git

### Setup

```bash
# 1. Clone
git clone https://github.com/snehamaheshwari/Cafe-Buddy-AI.git
cd Cafe-Buddy-AI

# 2. Backend
cd backend
pip install -r requirements.txt
python -m nltk.downloader stopwords punkt punkt_tab
uvicorn main:app --reload --port 8000
# → http://localhost:8000   API docs: http://localhost:8000/docs

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173  (proxies /api/* to localhost:8000)
```

### Enable Claude AI Chatbot (optional)
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```
Without this key the chatbot runs in smart analytics mode — no external API calls.

### Run Tests
```bash
cd backend
pytest tests/ -v    # 39 tests
```

---

## 9. Deployment (Railway)

### How It Works
1. Push code to **`main`** branch on GitHub
2. Railway detects the push via webhook (auto-deploy is enabled in Settings → Source)
3. Docker 2-stage build:
   - **Stage 1** — `node:18-alpine` installs npm dependencies, runs `vite build`
   - **Stage 2** — `python:3.11-slim` installs pip dependencies, copies backend + React `dist/`
4. Container starts: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Railway Volume at `/app/backend/data` preserves all uploaded data across deploys

### Deploying

```bash
# Always push to BOTH branches — master is your working branch, main triggers Railway
git push origin master           # update working branch
git push origin master:main      # triggers Railway auto-deploy via GitHub webhook
```

### Railway Dashboard
Project: https://railway.com/project/95fbec78-3b19-402f-9c7e-48b3a20294d4

---

## 10. API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login (username + password) |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/me` | Validate current session |

### Data Upload & Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload/pos` | Upload POS sales CSV/Excel |
| POST | `/api/upload/financial` | Upload financial data |
| POST | `/api/upload/customer` | Upload customer data |
| POST | `/api/upload/reviews` | Upload review data |
| POST | `/api/upload/menu` | Upload menu catalogue |
| GET | `/api/templates/{type}` | Download CSV template (`pos`/`financial`/`customer`/`reviews`/`menu`) |

### Analytics & ML
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/overview` | KPIs + XGBoost forecast + platform split |
| GET | `/api/ml/forecast` | 30-day revenue forecast |
| GET | `/api/ml/dynamic-pricing` | Item pricing (Increase / Hold / Review) |
| GET | `/api/ml/cross-sell` | Apriori cross-sell rules (lift ≥ 1.5) |
| GET | `/api/ml/peak-hours` | Peak hour heatmap |
| GET | `/api/ml/cancellation-risk` | Cancellation risk by platform |
| GET | `/api/ml/platform-forecast` | Per-platform revenue forecast |
| GET | `/api/sentiment/overview` | Sentiment scores, NPS, aspect breakdown |

### Decision Engine & Execution
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/layer4/decisions` | List data-driven decisions |
| POST | `/api/layer4/decisions/{id}/approve` | Approve a decision |
| POST | `/api/layer4/decisions/{id}/reject` | Reject a decision |
| GET | `/api/layer5/autonomous-actions` | Approved decisions + AI model actions feed |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/roles` | List all roles and permissions |
| POST | `/api/roles` | Create custom role |
| GET | `/api/users` | List all users |
| POST | `/api/users` | Create new user |
| GET | `/api/audit` | Query audit log |
| GET | `/api/peers/competitors` | Competitor data for city/area |
| POST | `/api/peers/analyze` | AI competitive analysis (Claude) |
| POST | `/api/chatbot/chat` | Streaming AI chat (Server-Sent Events) |

---

## 11. Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Optional | Enables Claude AI chatbot + Market Radar AI analysis |
| `PORT` | Auto (Railway) | Uvicorn listen port (Railway injects this) |
| `DATA_DIR` | Optional | Override `/app/backend/data` for custom volume path |

---

## 12. Login Credentials (Demo)

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin — full access |
| `owner` | `owner123` | Admin — full access |

---

## 📄 License

Private project — © 2026 Cafe Buddy AI. All rights reserved.
