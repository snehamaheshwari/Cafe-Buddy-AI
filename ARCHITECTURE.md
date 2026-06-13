# Cafe Buddy AI — Detailed Architecture

> Full system architecture: data sources, code internals, ML pipeline, deployment, and code versioning.

---

## 1. High-Level System Map

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        CAFE BUDDY AI — FULL SYSTEM ARCHITECTURE                 ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │                         OWNER / USER (Browser)                            │   ║
║  │                                                                            │   ║
║  │   Upload CSV/Excel  ──►  Review charts  ──►  Approve decisions           │   ║
║  │   Assign roles      ──►  Chat with AI   ──►  Export audit log            │   ║
║  └──────────────────────────────┬─────────────────────────────────────────┘   ║
║                                 │  HTTPS  (aicafebuddy.com)                   ║
║  ┌──────────────────────────────▼──────────────────────────────────────────┐   ║
║  │                    REACT FRONTEND  (TypeScript + Vite 5)                  │   ║
║  │                                                                            │   ║
║  │  AuthContext (session + /auth/me polling)                                 │   ║
║  │  PermissionRoute (RBAC gate per page)                                     │   ║
║  │  apiFetch.ts (injects X-Username + X-Role headers)                        │   ║
║  │  api.ts (typed REST client for all endpoints)                             │   ║
║  │                                                                            │   ║
║  │  11 role-gated pages:                                                     │   ║
║  │  Dashboard | DataCollection | DataEngineering | AIMLIntelligence          │   ║
║  │  DecisionEngine | CafeOS | Chatbot | PeerComparison                       │   ║
║  │  WhatsAppNotifications | RoleManagement | AuditLog                        │   ║
║  │                                                                            │   ║
║  │  React 18 · TypeScript 5 · Vite · React Router 6                         │   ║
║  │  Recharts · Tailwind CSS · Lucide React                                   │   ║
║  └──────────────────────────────┬──────────────────────────────────────────┘   ║
║                                 │  JSON REST API  +  SSE streaming             ║
║  ┌──────────────────────────────▼──────────────────────────────────────────┐   ║
║  │                  FASTAPI BACKEND  (Python 3.11 + Uvicorn)                 │   ║
║  │                                                                            │   ║
║  │  main.py (50+ routes, audit middleware)                                   │   ║
║  │  multi_upload.py (5 upload types, column aliasing)                        │   ║
║  │  data_store.py (shared state + JSON persistence)                          │   ║
║  │                                                                            │   ║
║  │  ┌──────────────────────────────────────────────────────────────────┐    │   ║
║  │  │                        ML / AI LAYER                              │    │   ║
║  │  │                                                                    │    │   ║
║  │  │  ml_models.py          sentiment_engine.py    chatbot.py          │    │   ║
║  │  │  ├ XGBoost forecast    ├ Logistic Regression  ├ Claude API (SSE) │    │   ║
║  │  │  ├ Apriori cross-sell  ├ TF-IDF vectoriser    ├ DuckDuckGo      │    │   ║
║  │  │  ├ RF peak hours       ├ NLTK tokenisation    └ Festival cal.   │    │   ║
║  │  │  ├ XGBoost cancel risk ├ Aspect analysis                         │    │   ║
║  │  │  ├ Dynamic pricing     └ NPS + trends         peer_comparison.py │    │   ║
║  │  │  └ Platform Ridge reg.                        ├ Competitor DB    │    │   ║
║  │  │                                               ├ DDG live search  │    │   ║
║  │  │  role_store.py  audit_store.py  cafe_os_models.py                │    │   ║
║  │  └──────────────────────────────────────────────────────────────────┘    │   ║
║  └────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                  ║
║  ┌──────────────────────────────────────────────────────────────────────────┐   ║
║  │                         INFRASTRUCTURE                                    │   ║
║  │                                                                            │   ║
║  │  GitHub (main branch)  ──webhook──►  Railway auto-deploy                 │   ║
║  │    └─► Docker 2-stage build  (Node 18 Alpine → Python 3.11 slim)        │   ║
║  │    └─► Uvicorn on port $PORT  serves FastAPI + React static build       │   ║
║  │    └─► Railway Volume at /app/backend/data  (persistent uploads)        │   ║
║  │  Domain: aicafebuddy.com  ──►  Railway reverse proxy  ──►  Container   │   ║
║  └──────────────────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Data Pipeline (Upload → Insight)

```
OWNER UPLOADS FILE
       │
       ▼
POST /api/upload/{type}     (type = pos | financial | customer | reviews | menu)
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   multi_upload.py / main.py                              │
│                                                                          │
│  1. Read bytes → pandas.read_excel() or read_csv()                      │
│                                                                          │
│  2. Column detection  (30+ aliases per field, 3-pass matching):         │
│       Pass 1 — exact match:  "Revenue" → revenue                        │
│       Pass 2 — fragment:     "Revenue / Total" → revenue               │
│       Pass 3 — leading word: "Item Name / Product" → item_name         │
│                                                                          │
│  3. Row normalisation → [{                                               │
│       date, item_name, category, quantity,                               │
│       price, revenue, cost, platform, order_id, hour                    │
│     }]                                                                   │
│                                                                          │
│  4. Persist to Railway Volume:                                           │
│       data_store.save_dataset("pos", rows, info)                        │
│       → /app/backend/data/pos.json                                       │
│                                                                          │
│  5. Audit log entry: user X uploaded N rows of type Y                   │
└─────────────────────────────────────────────────────────────────────────┘
       │
       ▼
data_store global state updated
  _pos_data · _menu_data · _financial_data · _customer_data · _reviews_data
       │
       ├──► Dashboard KPIs      ← _calc_kpis(pos_data)
       ├──► Revenue Forecast    ← ml_models.revenue_forecast()
       ├──► Dynamic Pricing     ← ml_models.dynamic_pricing_suggestions()
       ├──► Cross-sell          ← ml_models.cross_sell_recommendations()
       ├──► Sentiment           ← sentiment_engine.analyse(reviews_data)
       └──► Decision Engine     ← _generate_decisions(pos_data)
```

---

## 3. ML Models Architecture

```
ALL MODELS ARE LOADED LAZILY  (cached in _cache dict after first load)

┌─────────────────────────────────────────────────────────────────────────┐
│  1. REVENUE FORECAST                                                     │
│                                                                          │
│  File:     xgboost_model.joblib                                         │
│  Type:     XGBoost Regressor — 600 estimators, max_depth=6             │
│  Training: 100,000 CafeBuddy transactions                               │
│  Accuracy: MAPE 7.83%  |  MAE ₹5,153  |  RMSE ₹6,064                  │
│                                                                          │
│  Uploaded POS                                                            │
│    → daily revenue aggregation                                           │
│    → lag features: lag_7, lag_14, lag_28                                │
│    → rolling: roll_mean_7, roll_std_7                                   │
│    → XGBoost predict 30 days forward                                    │
│    → scale to café's actual revenue range                               │
│    → [{date, forecast, lower_bound, upper_bound}]                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  2. CROSS-SELL RECOMMENDATIONS  (Apriori association rules)             │
│                                                                          │
│  File:  cross_sell_rules.pkl                                            │
│  Total rules: 1,698  |  After quality filter: 8                        │
│  Thresholds: lift >= 1.5  AND  confidence >= 0.05 (5%)                 │
│                                                                          │
│  Top rules:                                                              │
│    Masala Omelette → Lemonade           lift=2.08  conf=12.3%          │
│    Belgian Waffle  → Iced Latte          lift=1.83  conf=10.9%          │
│    Choco Lava Cake → Chocolate Brownie   lift=1.56  conf=6.5%           │
│    Belgian Waffle  → Americano           lift=1.52  conf=8.9%           │
│    Hot Chocolate   → Kashmiri Kahwa      lift=1.50  conf=6.9%           │
│                                                                          │
│  Inference:                                                              │
│    Pre-trained rules                                                     │
│      → filter: lift >= 1.5 AND conf >= 0.05                            │
│      → filter: both items in uploaded POS item names (fuzzy match)     │
│      → sort by lift desc → top 10                                       │
│                                                                          │
│  Fallback (when no rules match uploaded items):                          │
│    POS rows grouped by order_id (same bill = bought together)           │
│      → count co-occurrence of every directed item pair                  │
│      → compute support, confidence, lift                                │
│      → same quality gates: lift >= 1.5, conf >= 0.05                   │
│      → sort by lift → top 10                                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  3. DYNAMIC PRICING  (data-driven, no hardcoding)                       │
│                                                                          │
│  Input: uploaded POS + uploaded Menu catalogue                          │
│                                                                          │
│  Step 1 — Build menu item set: {item.lower() for item in menu_data}    │
│  Step 2 — Aggregate POS by item: revenue, cost, qty, n_days            │
│  Step 3 — Menu filter: skip POS items absent from menu catalogue        │
│             (removes deleted/erroneous items like "Diavola")            │
│  Step 4 — Compute from real data:                                       │
│             current_price = menu price (or POS avg revenue/qty)        │
│             margin_pct    = (revenue - cost) / revenue × 100           │
│             daily_qty     = total_qty / n_days                          │
│  Step 5 — Tier assignment (from actual margin):                         │
│             margin >= 55%  → Increase +8%  (very healthy)             │
│             margin 40-55%  → Increase +5%  (solid)                     │
│             margin 25-40%  → Hold           (near-optimal)             │
│             margin <  25%  → Review         (cost audit needed)        │
│               high volume  → "audit ingredient costs"                   │
│               low  volume  → "consider repricing or removal"            │
│  Step 6 — Sort: Increase (by impact) → Hold → Review → top 15          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  4. SENTIMENT ANALYSIS                                                   │
│                                                                          │
│  Files: sentiment_model.pkl · tfidf_vectorizer.pkl · label_encoder.pkl │
│  Type: Logistic Regression + TF-IDF                                     │
│  Labels: Negative | Neutral | Positive                                  │
│                                                                          │
│  Review text                                                             │
│    → NLTK tokenise (punkt) + stopword removal                           │
│    → TF-IDF vectorise (tfidf_vectorizer.pkl)                           │
│    → LR predict + confidence score (sentiment_model.pkl)               │
│    → Label decode (label_encoder.pkl)                                   │
│    → Aspect extraction (5 dimensions):                                  │
│        Food & Menu | Service | Ambiance | Price/Value | Wait Time       │
│    → NPS = %Positive - %Negative                                        │
│    → Keyword frequency cloud                                            │
│    → Sentiment trend (weekly aggregation over time)                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  5. PEAK HOURS                                                           │
│  Uploaded POS → group by (hour × day_of_week) → sum orders             │
│  Output: 7×24 order-density heatmap                                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  6. CANCELLATION RISK  (XGBoost classifier)                             │
│  Input: platform, hour, day, category from uploaded POS                 │
│  Output: risk score per platform + high-risk order flags                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  7. PLATFORM FORECAST  (Ridge regressors per platform)                  │
│  Input: platform-filtered daily revenue from uploaded POS               │
│  Output: 14-day per-platform revenue forecast                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Decision Engine & AI-Powered Execution

```
Uploaded POS data
       │
       ▼
_generate_decisions(pos_data)  in main.py
       │
       ├─ _item_stats(data)         group by item: qty, revenue, cost, margin
       ├─ _platform_breakdown(data) group by platform: revenue, orders, avg_ticket
       ├─ Identify top/bottom items from REAL uploaded data
       │
       ├─ Generate decisions (all values from uploaded data — zero hardcoding):
       │    Pricing    ← top items with actual margin info
       │    Marketing  ← best platform by real revenue
       │    Staffing   ← peak hour from uploaded POS
       │    Inventory  ← high-volume items from real counts
       │    Operations ← low-margin items needing review
       │
       ▼
Decision list  (GET /api/layer4/decisions)
       │
       ▼
Owner reviews in "What To Do Next" page
       │
  ┌────┴────┐
Approve   Reject
  │
  ▼
POST /api/layer4/decisions/{id}/approve
  → _decision_overrides[id] = "approved"
  → audit_store.log_action("decision_approved")
  │
  ▼
GET /api/layer5/autonomous-actions
  → approved decisions + XGBoost model action alerts
  → shown in "AI-Powered Execution" feed
```

---

## 5. Chatbot Architecture

```
POST /api/chatbot/chat  {message: "..."}
       │
       ▼
┌─────────────────────────────────────────────────┐
│              CONTEXT BUILDER                     │
│                                                  │
│  item_stats(pos_data)          top items        │
│  platform_breakdown(pos_data)  platform split   │
│  daily_revenue(pos_data)       revenue trend    │
│  sentiment_engine.get_chat_context()  NPS data  │
│  festival_calendar             upcoming events  │
└─────────────────────────────────────────────────┘
       │
  ANTHROPIC_API_KEY set?
  YES │                    NO
      ▼                     ▼
Claude API (SSE)    Smart Analytics Engine
  claude-3-haiku    (no external calls)
  system prompt =   pattern match message
  café context      → pick relevant block
  injected          → structured response
      │
  DuckDuckGo search needed?
  (competitor / festival query detected)
      │ YES
      ▼
  DDGS().text(query, max_results=5)
  inject results into Claude context
      │
      ▼
StreamingResponse (Server-Sent Events)
  token-by-token streaming to browser
  frontend renders in real-time
```

---

## 6. RBAC & Audit Architecture

```
data/roles.json  (Railway Volume)
{
  "roles": {
    "admin":     { "permissions": [all 11 features], "system": true },
    "sub_admin": { "permissions": [9 features],      "system": true },
    "viewer":    { "permissions": ["dashboard"],     "system": true },
    "<custom>":  { "permissions": [...admin-defined] }
  },
  "users": {
    "admin": { "role": "admin", "system": true },
    "owner": { "role": "admin", "system": true },
    "<any>": { "role": "<role>", "created_at": "..." }
  }
}

Permission check flow:
  Browser request
    → apiFetch.ts adds X-Username + X-Role headers
    → FastAPI route: role_store.has_permission(username, feature)
    → 403 if absent
    → Frontend PermissionRoute also checks locally (no round-trip for nav)

AUDIT SYSTEM  (audit_store.py)

  Automatic (HTTP middleware in main.py):
    All authenticated non-polling requests
    → X-Username, X-Role from headers
    → method, path, status_code, duration_ms, ip_address logged

  Explicit (critical actions):
    data_uploaded · decision_approved · user_created · role_changed

  Storage: data/audit_log.json  (Railway Volume)
  Export:  GET /api/audit?format=csv
```

---

## 7. Deployment & CI/CD Pipeline

```
DEVELOPER LOCAL MACHINE
  Edit code
    └─► git add + git commit
           └─► git push origin master        (working branch)
           └─► git push origin master:main   (triggers Railway deploy)

GITHUB  (snehamaheshwari/Cafe-Buddy-AI)
  Branch: main   ← Railway auto-deploy target (webhook ON)
  Branch: master ← development working branch

RAILWAY  (project: authentic-imagination, service: Cafe-Buddy-AI)

  DOCKER 2-STAGE BUILD  (railway.toml → builder = "dockerfile")

  STAGE 1 — node:18-alpine
    COPY frontend/package*.json
    RUN  npm ci --silent
    COPY frontend/
    RUN  npm run build   → /app/frontend/dist/

  STAGE 2 — python:3.11-slim
    RUN  apt-get install gcc   (pandas/scikit-learn native deps)
    COPY backend/requirements.txt
    RUN  pip install -r requirements.txt
    RUN  python -c "nltk.download(...)"   (punkt, stopwords)
    COPY backend/
    COPY --from=stage1 /app/frontend/dist  /app/frontend/dist
    RUN  mkdir -p /app/backend/data
    CMD  uvicorn main:app --host 0.0.0.0 --port $PORT

  After successful build:
    New container replaces old one
    Railway Volume /app/backend/data re-attached automatically
    Restart policy: on_failure, max 5 retries

LIVE SERVICE
  uvicorn on port 8080
  /api/*       → FastAPI routes
  /api/chatbot/chat → Server-Sent Events
  /*           → React SPA (index.html fallback)
  /assets/*    → Vite static artifacts

  Domain: aicafebuddy.com → Railway proxy → container
```

---

## 8. Frontend Request Lifecycle

```
User navigates to page
       │
       ▼
React Router matches route
       │
       ▼
PermissionRoute checks AuthContext.hasPermission(feature)
  NO  → redirect to "/"
  YES → page component mounts
           │
           ▼
       useEffect → api.ts call
           │
           ▼
       apiFetch.ts:
         fetch(`/api/...`, {
           headers: {
             "X-Username": session.username,   ← for audit logging
             "X-Role":     session.role,        ← for permission checks
           }
         })
           │
           ▼
       FastAPI: audit_middleware logs → route handler → JSON response
           │
           ▼
       React state update → Recharts re-renders charts/tables
```

---

## 9. External Integrations

```
┌──────────────────────────────────────────────────────┐
│  Anthropic Claude API                                  │
│  Used by: chatbot.py + peer_comparison.py             │
│  Model:   claude-3-haiku  (streaming)                 │
│  Auth:    ANTHROPIC_API_KEY env var (Railway Vars)    │
│  Fallback: smart analytics mode if key absent         │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  DuckDuckGo Search (DDGS)                             │
│  Used by: chatbot.py + peer_comparison.py             │
│  Trigger: competitor / festival / market queries      │
│  No API key required                                   │
│  Fallback: pre-loaded competitor database             │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Green API (WhatsApp Business)                        │
│  Used by: WhatsAppNotifications page                  │
│  Auth:    idInstance + apiTokenInstance (user-input)  │
│  No server-side key needed                            │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  GitHub (snehamaheshwari/Cafe-Buddy-AI)               │
│  Branches: main (deploy target) · master (dev)        │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Railway                                               │
│  Project: authentic-imagination                       │
│  Volume:  cafe-buddy-ai-volume → /app/backend/data    │
└──────────────────────────────────────────────────────┘
```

---

## 10. Data Persistence Model

```
Railway Volume mounted at: /app/backend/data/

File               Contents
─────────────────────────────────────────────────────────────────────────
pos.json           {data: [{order_id, item_name, bill_amount, cost,
                     date, hour, platform, discount, ...}], info: {...}}
financial.json     {data: [{date, revenue, expense, profit}], info: {}}
customer.json      {data: [{customer_id, name, visits, spend}], info: {}}
reviews.json       {data: [{review_text, rating, date}], info: {}}
menu.json          {data: [{item, base_price, category, season}], info:{}}
roles.json         {roles: {...}, users: {...}}
audit_log.json     [{timestamp, username, module, action, status, ...}]

All files survive container restart and new deployments.
Volume is only lost if manually deleted (never happens automatically).

In-memory state (reloaded from Volume on startup):
  data_store._pos_data        loaded from pos.json
  data_store._menu_data       loaded from menu.json
  data_store._financial_data  loaded from financial.json
  data_store._customer_data   loaded from customer.json
  data_store._reviews_data    loaded from reviews.json
  main._decision_overrides    in-memory only (resets on deploy)
```

---

*Last updated: June 2026 | aicafebuddy.com*
