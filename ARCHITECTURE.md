# Cafe Buddy AI — Application Architecture
### Comprehensive Technical Overview for Presentation

---

## 1. High-Level System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CAFE BUDDY AI v2.1                                │
│               "The AI-Powered Café Operating System"                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Browser (React SPA)  ◄──── Vite Build ────►  /frontend/dist            │
│        │                                                                 │
│        │  HTTPS + X-Username / X-Role headers                           │
│        ▼                                                                 │
│  FastAPI (Python 3.11)  ◄──── Uvicorn ────►  Port 8000                 │
│        │                                                                 │
│        ├── data/roles.json   (RBAC store)                               │
│        ├── data/audit.jsonl  (Audit trail)                              │
│        └── models/*.pkl      (XGBoost / LogReg pre-trained models)      │
│                                                                          │
│  Deployment: Railway.app (Linux container, 1 vCPU, 512 MB RAM)          │
│  Domain:     aicafebuddy.com (Cloudflare CDN)                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer          | Technology                                  | Version   |
|----------------|---------------------------------------------|-----------|
| Frontend       | React + TypeScript                          | 18.x      |
| Routing        | React Router DOM                            | 6.x       |
| Styling        | Tailwind CSS                                | 3.x       |
| Icons          | Lucide React                                | 0.x       |
| Build          | Vite                                        | 5.x       |
| Backend        | FastAPI + Python                            | 0.111 / 3.11 |
| ASGI Server    | Uvicorn                                     | 0.30      |
| ML Models      | XGBoost, Scikit-learn, NLTK                 | latest    |
| Data Format    | JSON (roles/users), JSONL (audit), XLSX (uploads) |      |
| Testing        | pytest + httpx (ASGITransport)              |           |
| Load Testing   | Locust                                      | 2.x       |
| Deployment     | Railway.app                                 |           |

---

## 3. 5-Layer Intelligence Architecture

The system is designed as 5 progressive intelligence layers:

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 5 — AUTO-PILOT (Autonomous Café OS)              │
│  XGBoost demand forecasting, price optimisation,         │
│  automatic decisions, real-time alerts                   │
├─────────────────────────────────────────────────────────┤
│  LAYER 4 — DECISION ENGINE                              │
│  AI-driven recommendations: pricing, staffing,          │
│  menu optimisation, marketing promotions                 │
├─────────────────────────────────────────────────────────┤
│  LAYER 3 — AI / ML INTELLIGENCE                         │
│  Revenue forecasting, customer segmentation,            │
│  cross-sell association rules, sentiment NLP            │
├─────────────────────────────────────────────────────────┤
│  LAYER 2 — DATA ENGINEERING                             │
│  ETL pipelines, data quality scoring, trend analysis,   │
│  platform breakdown, daily aggregations                 │
├─────────────────────────────────────────────────────────┤
│  LAYER 1 — DATA COLLECTION                              │
│  Excel upload (POS, Financial, Customer, Reviews, Menu),│
│  column auto-detection, validation, normalization        │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Frontend Architecture

### 4.1 Component Tree

```
App.tsx
├── AuthProvider (Context — user, login, logout, hasPermission)
│   └── BrowserRouter
│       ├── /login          → PublicRoute → Login.tsx
│       └── PrivateLayout   → SidebarProvider
│           ├── Sidebar.tsx (RBAC-filtered navigation)
│           │   ├── NAV_ITEMS (9 items, filtered by permission)
│           │   └── Admin section (role_management + audit_logs)
│           ├── Header.tsx  (clock, user badge, sign-out)
│           └── [Page routes — all PermissionRoute guarded]
│               ├── /                  → Dashboard.tsx
│               ├── /data-collection   → DataCollection.tsx
│               ├── /data-engineering  → DataEngineering.tsx
│               ├── /ai-intelligence   → AIMLIntelligence.tsx
│               ├── /decision-engine   → DecisionEngine.tsx
│               ├── /cafe-os           → CafeOS.tsx
│               ├── /chatbot           → Chatbot.tsx
│               ├── /peer-comparison   → PeerComparison.tsx
│               ├── /notifications     → WhatsAppNotifications.tsx
│               ├── /role-management   → RoleManagement.tsx
│               └── /audit             → AuditLog.tsx
└── ErrorBoundary (catches render crashes → "Clear session" button)
```

### 4.2 Key Frontend Patterns

| Pattern              | Implementation                                               |
|----------------------|--------------------------------------------------------------|
| Global auth state    | `AuthContext` — `user`, `hasPermission()`, `isAdmin()`       |
| Permission-gated routes | `PermissionRoute` component → redirects to `/` if denied |
| API calls            | `apiFetch()` — auto-appends `X-Username` + `X-Role` headers  |
| Crash recovery       | `ErrorBoundary` in `main.tsx` — clear session + reload       |
| Sidebar visibility   | Filtered by `hasPermission()` at render time                 |

### 4.3 Auth localStorage Format

```json
{
  "username":    "admin",
  "full_name":   "Admin User",
  "role_id":     "admin",
  "role":        "Admin",
  "permissions": ["dashboard", "upload_data", "reports", "...", "audit_logs"],
  "token":       "demo-token-admin"
}
```

---

## 5. Backend Architecture

### 5.1 Module Structure

```
backend/
├── main.py              — FastAPI app, all 40+ endpoints, audit middleware
├── role_store.py        — RBAC store (roles + users → data/roles.json)
├── audit_store.py       — Audit log store (data/audit.jsonl, in-memory cache)
├── data_store.py        — Shared mutable state for uploaded datasets
├── chatbot.py           — Conversational AI router (/api/chat)
├── multi_upload.py      — Multi-dataset upload router
├── sentiment_engine.py  — NLP review analysis (Logistic Regression + TF-IDF)
├── ml_models.py         — XGBoost revenue forecast, cross-sell, dynamic pricing
├── peer_comparison.py   — Market radar competitor analysis
├── cafe_os_models.py    — Layer 5 autonomous actions from XGBoost models
├── data/
│   ├── roles.json       — Persisted roles and users
│   └── audit.jsonl      — Append-only audit trail (JSONL, up to 50K entries)
├── models/
│   ├── demand_forecast_model.pkl
│   ├── item_popularity_model.pkl
│   ├── price_optimization_table.pkl
│   └── sentiment_model.pkl (+ vectorizer, label encoder)
└── tests/
    ├── test_role_store.py    — 89 unit tests
    ├── test_role_api.py      — 58 integration tests
    ├── test_audit_store.py   — 90 unit tests
    ├── test_audit_api.py     — 50 integration tests
    └── test_performance.py   — Performance + load tests
```

### 5.2 Request Lifecycle

```
Browser
  │
  │  apiFetch() adds X-Username header
  ▼
FastAPI (main.py)
  │
  ├── Audit Middleware (every authenticated request)
  │     Reads X-Username, logs path + method + status + duration
  │
  ├── Endpoint Handler (e.g. POST /api/auth/login)
  │     1. Business logic
  │     2. Explicit audit log (action + description)
  │     3. Return JSON response
  │
  └── role_store / audit_store
        Data persisted to data/roles.json and data/audit.jsonl
```

---

## 6. RBAC — Role-Based Access Control

### 6.1 Built-in Roles

| Role      | Permissions (11 total)                                                |
|-----------|-----------------------------------------------------------------------|
| **Admin**     | All 11: dashboard, upload_data, reports, analytics, decision_engine, auto_pilot, chatbot, market_radar, whatsapp_alerts, role_management, **audit_logs** |
| **Sub-Admin** | dashboard, upload_data, reports, analytics, decision_engine, chatbot |
| **Viewer**    | dashboard, reports, market_radar                                      |
| **Custom**    | Any combination assigned by Admin                                     |

### 6.2 Permission Keys

```
dashboard        → Home / Dashboard
upload_data      → Upload My Data
reports          → Reports & Insights
analytics        → Smart Analytics
decision_engine  → What To Do Next
auto_pilot       → Auto-Pilot Mode
chatbot          → Ask Cafe Buddy
market_radar     → Market Radar
whatsapp_alerts  → WhatsApp Alerts
role_management  → Role Management
audit_logs       → Audit Logs          ← NEW
```

### 6.3 Permission Guard Flow

```
User navigates to /audit
     ↓
PermissionRoute checks hasPermission("audit_logs")
     ↓ no
Navigate to /          ← user sees dashboard, no error flash
     ↓ yes
AuditLog.tsx renders   ← full audit view
```

---

## 7. Audit Management System

### 7.1 Audit Entry Structure

```json
{
  "id":          "a3f8c21d",
  "timestamp":   "2026-06-09 14:32:05",
  "username":    "admin",
  "role":        "Admin",
  "module":      "upload_data",
  "module_label":"Upload My Data",
  "action":      "FILE_UPLOAD",
  "description": "Uploaded 'sales_may.xlsx' — 1,240 records, 30 days, 18 items",
  "status":      "success",
  "ip_address":  "49.36.x.x",
  "duration_ms": 312
}
```

### 7.2 Storage Strategy

| Property         | Detail                                              |
|------------------|-----------------------------------------------------|
| Format           | JSONL (JSON Lines) — one object per line            |
| Location         | `data/audit.jsonl`                                  |
| Max on disk      | 50,000 entries (oldest trimmed automatically)       |
| In-memory cache  | Last 5,000 entries in `collections.deque`           |
| Thread safety    | `threading.Lock` on all file writes                 |
| Write speed      | < 2 ms per entry (append-only)                      |
| Read speed       | < 5 ms for 100 entries (from memory)                |

### 7.3 Audit Coverage

| Event                           | Action Key           | Triggered From         |
|---------------------------------|----------------------|------------------------|
| Successful login                | LOGIN                | POST /api/auth/login   |
| Failed login attempt            | LOGIN (error status) | POST /api/auth/login   |
| Logout                          | LOGOUT               | POST /api/auth/logout  |
| Excel file uploaded             | FILE_UPLOAD          | POST /api/upload/excel |
| Data cleared                    | FILE_CLEAR           | DELETE /api/upload/clear |
| Decision approved               | DECISION_APPROVE     | POST /api/layer4/decisions/{id}/approve |
| Decision rejected               | DECISION_REJECT      | POST /api/layer4/decisions/{id}/reject  |
| Role created                    | ROLE_CREATE          | POST /api/roles        |
| Role updated                    | ROLE_UPDATE          | PUT /api/roles/{id}    |
| Role deleted                    | ROLE_DELETE          | DELETE /api/roles/{id} |
| User created                    | USER_CREATE          | POST /api/users        |
| User updated                    | USER_UPDATE          | PUT /api/users/{id}    |
| User deleted                    | USER_DELETE          | DELETE /api/users/{id} |
| Peer analysis run               | PEER_ANALYSIS        | POST /api/peers/analyze |
| Audit log viewed                | AUDIT_VIEW           | GET /api/audit/logs    |
| Audit exported                  | EXPORT               | GET /api/audit/export  |

### 7.4 Audit Log API Endpoints

```
GET  /api/audit/logs    — paginated + filterable log viewer
GET  /api/audit/stats   — today's stats, module breakdown, hourly chart
GET  /api/audit/export  — CSV download (streamed)
GET  /api/audit/modules — metadata (module list, action types)
```

---

## 8. API Endpoint Catalog

### Authentication

| Method | Path              | Description               |
|--------|-------------------|---------------------------|
| POST   | /api/auth/login   | Validate credentials, return permissions |
| POST   | /api/auth/logout  | Log out (audit + session) |

### Role Management

| Method | Path                    | Description              |
|--------|-------------------------|--------------------------|
| GET    | /api/roles              | List all roles + labels  |
| POST   | /api/roles              | Create custom role       |
| PUT    | /api/roles/{role_id}    | Update role              |
| DELETE | /api/roles/{role_id}    | Delete custom role       |
| GET    | /api/users              | List all users           |
| POST   | /api/users              | Create user              |
| PUT    | /api/users/{username}   | Update user              |
| DELETE | /api/users/{username}   | Delete non-system user   |

### Audit

| Method | Path                  | Description               |
|--------|-----------------------|---------------------------|
| GET    | /api/audit/logs       | Paginated + filtered logs |
| GET    | /api/audit/stats      | Aggregated stats          |
| GET    | /api/audit/export     | CSV download              |
| GET    | /api/audit/modules    | Module/action metadata    |

### Data Upload

| Method | Path                  | Description               |
|--------|-----------------------|---------------------------|
| POST   | /api/upload/excel     | Upload POS / financial XLSX |
| GET    | /api/upload/status    | Check upload status       |
| DELETE | /api/upload/clear     | Revert to demo data       |

### Intelligence Layers

| Method | Path                              | Layer | Description         |
|--------|-----------------------------------|-------|---------------------|
| GET    | /api/dashboard/overview           | —     | KPI summary         |
| GET    | /api/layer1/summary               | L1    | Data collection     |
| GET    | /api/layer1/platforms             | L1    | Platform breakdown  |
| POST   | /api/layer1/sales                 | L1    | Manual entry        |
| GET    | /api/layer2/pipeline-status       | L2    | ETL pipeline        |
| GET    | /api/layer2/processed-data        | L2    | Aggregated sales    |
| GET    | /api/layer2/insights              | L2    | Per-dataset insights|
| GET    | /api/layer3/forecast              | L3    | Revenue forecast    |
| GET    | /api/layer3/recommendations       | L3    | Product recs        |
| GET    | /api/layer3/segmentation          | L3    | Customer segments   |
| GET    | /api/layer3/market-insights       | L3    | Market benchmarks   |
| GET    | /api/layer4/decisions             | L4    | AI decisions        |
| POST   | /api/layer4/decisions/{id}/approve| L4    | Approve decision    |
| POST   | /api/layer4/decisions/{id}/reject | L4    | Reject decision     |
| GET    | /api/layer5/autonomous-actions    | L5    | Autopilot actions   |
| GET    | /api/layer5/kpis                  | L5    | KPI metrics         |
| GET    | /api/layer5/price-recommendations | L5    | Price optimisation  |
| GET    | /api/layer5/model-status          | L5    | Model health        |

### ML Model Direct Endpoints

| Method | Path                      | Description                |
|--------|---------------------------|----------------------------|
| GET    | /api/ml/forecast          | XGBoost 7-day forecast     |
| GET    | /api/ml/platform-forecast | Per-platform forecast      |
| GET    | /api/ml/peak-hours        | Peak hour analysis         |
| GET    | /api/ml/cancellation-risk | Cancellation risk scoring  |
| GET    | /api/ml/cross-sell        | Association rules          |
| GET    | /api/ml/dynamic-pricing   | Price suggestions          |
| GET    | /api/ml/model-comparison  | Model performance table    |

### Sentiment & Chatbot

| Method | Path                   | Description              |
|--------|------------------------|--------------------------|
| POST   | /api/chat              | AI chatbot query         |
| GET    | /api/sentiment/overview| Sentiment stats          |

### Peer Comparison

| Method | Path                      | Description             |
|--------|---------------------------|-------------------------|
| GET    | /api/peers/cities         | Available cities        |
| GET    | /api/peers/areas          | Areas for city          |
| GET    | /api/peers/competitors    | Competitor list         |
| GET    | /api/peers/live-search    | Live competitor search  |
| POST   | /api/peers/analyze        | AI peer analysis        |

---

## 9. ML Models

### 9.1 Model Inventory

| Model                        | Algorithm              | Purpose                           |
|------------------------------|------------------------|-----------------------------------|
| demand_forecast_model.pkl    | XGBoost Regressor      | Daily revenue forecast (7 days)   |
| item_popularity_model.pkl    | XGBoost Classifier     | Item demand by daypart            |
| price_optimization_table.pkl | Pre-computed table     | Optimal price per item            |
| sentiment_model.pkl          | Logistic Regression    | Positive / negative review scoring|
| sentiment_vectorizer.pkl     | TF-IDF Vectorizer      | Feature extraction for sentiment  |
| sentiment_label_encoder.pkl  | Label Encoder          | Class mapping for sentiment       |

### 9.2 Fallback Strategy

```
POS Data ≥ 14 days?
    YES → XGBoost forecast (P95 accuracy ~88%)
    NO  → Weekday-Average heuristic (accuracy ~65%)

Sentiment model present?
    YES → Logistic Regression (avg confidence ~87%)
    NO  → Keyword matching fallback

XGBoost models present?
    YES → Autonomous actions from models
    NO  → Placeholder alert (graceful degradation)
```

---

## 10. Data Flow

### 10.1 Upload → Analysis Flow

```
User uploads sales.xlsx
        ↓
POST /api/upload/excel
        ↓
_parse_excel_bytes()
    ↓ column auto-detection (30+ aliases per field)
    ↓ validation + skipping bad rows
        ↓
data_store._pos_data populated
        ↓
audit_store.log_action(FILE_UPLOAD)
        ↓
All analytics endpoints now return live data:
  /api/layer2/processed-data    — real daily revenue
  /api/layer3/forecast          — XGBoost / weekday heuristic
  /api/layer4/decisions         — data-driven recommendations
  /api/layer5/autonomous-actions — automated decisions
```

### 10.2 Login → Permission Flow

```
POST /api/auth/login {username, password}
        ↓
role_store.authenticate()
    ↓ lookup user → get role → get permissions[]
        ↓
Return: {username, full_name, role_id, role, permissions[], token}
        ↓
Frontend: localStorage.setItem("cafe_buddy_auth", {...})
        ↓
AuthContext.loadUser() → permissions[]
        ↓
Sidebar renders filtered nav items
PermissionRoute guards each page
```

---

## 11. Test Coverage Summary

| Test File                  | Tests | Coverage Area                        |
|----------------------------|-------|--------------------------------------|
| test_role_store.py         | 89    | RBAC store unit tests                |
| test_role_api.py           | 58    | Role/User API integration + regression |
| test_audit_store.py        | 90    | Audit store unit tests               |
| test_audit_api.py          | 50    | Audit API integration + regression   |
| test_performance.py        | 15    | Load + performance benchmarks        |
| test_ml_models.py (existing)| 20+  | ML model tests                       |
| **Total**                  | **322+** | Full coverage across RBAC + Audit  |

### Performance Targets (met)

| Metric                    | Target    | Actual (typical) |
|---------------------------|-----------|-----------------|
| audit_store write speed   | < 2 ms    | ~0.3 ms         |
| 100 concurrent requests   | P95 < 500 ms | ~80 ms P95   |
| 500 concurrent requests   | error < 1% | 0%             |
| 1000-user burst           | < 60 s    | ~8 s            |
| 1000 audit writes         | < 5 s     | ~0.5 s          |

---

## 12. Security Considerations

| Area                    | Implementation                                     |
|-------------------------|----------------------------------------------------|
| Authentication          | Username / password stored in roles.json (demo mode) |
| Authorization           | Permission-based RBAC, server-side check on every write |
| Audit trail             | Immutable JSONL append, all admin actions logged   |
| System roles            | `is_system: True` prevents deletion of admin/sub_admin/viewer |
| System users            | admin + owner cannot be deleted via API            |
| Admin permissions       | role_management + audit_logs always retained for admin role |
| Frontend crash recovery | ErrorBoundary clears stale localStorage            |
| Stale auth detection    | loadUser() rejects missing permissions array       |
| CORS                    | Allow-All for demo; restrict to domain in production |

---

## 13. Deployment Architecture

```
GitHub (snehamaheshwari/Cafe-Buddy-AI)
        │
        │  git push
        ▼
Railway.app (auto-deploy on push)
        │
        ├── Build: pip install -r requirements.txt
        │          cd frontend && npm install && npm run build
        │
        ├── Start: uvicorn main:app --host 0.0.0.0 --port $PORT
        │
        ├── Persistent Volume: /app/backend/data/
        │     roles.json     (RBAC config)
        │     audit.jsonl    (audit trail)
        │
        └── Cloudflare → aicafebuddy.com (HTTPS, CDN)
```

---

## 14. File Count & Code Size (approx.)

| Area          | Files | Approx Lines |
|---------------|-------|--------------|
| Backend core  | 10    | ~5,000       |
| Backend tests | 5     | ~600         |
| Frontend pages| 11    | ~4,500       |
| Frontend utils| 3     | ~250         |
| Locustfile    | 1     | ~150         |
| **Total**     | **30** | **~10,500** |

---

*Cafe Buddy v2.1 — Built with FastAPI + React + XGBoost + RBAC + Audit Management*
*Architecture document generated: 2026-06-09*
