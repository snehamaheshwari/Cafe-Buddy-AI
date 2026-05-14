---
title: Cafe Buddy
emoji: ☕
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# ☕ Cafe Buddy — AI Café Operating System

A full 5-layer AI product prototype for intelligent café management.

## Architecture

| Layer | Name | Purpose |
|-------|------|---------|
| 1 | Data Collection | POS, Zomato, Swiggy, Weather, Feedback |
| 2 | Data Engineering | ETL pipelines, data quality, aggregation |
| 3 | AI / ML Intelligence | Demand forecasting, segmentation, affinity |
| 4 | Decision Engine | Actionable recommendations with approve/reject |
| 5 | Autonomous Café OS | Semi-automatic execution, live KPIs, action log |

## Quick Start

### 1. Backend (Python FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React
- **Backend**: FastAPI, Pydantic, Uvicorn
- **Charts**: Recharts (Area, Line, Bar, Pie, Composed)
- **Navigation**: React Router v6

## Features by Layer

### Layer 1 — Data Collection
- Live data source status (POS, Zomato, Swiggy, Weather, Feedback)
- Revenue breakdown by platform
- Sales entry form
- Inventory status with low-stock alerts

### Layer 2 — Data Engineering
- ETL pipeline status table (running / completed)
- Data quality score meters (completeness, accuracy, consistency, timeliness)
- Processed daily revenue trend
- Category revenue breakdown

### Layer 3 — AI / ML Intelligence
- 7-day demand forecast with confidence intervals (LSTM + XGBoost)
- Customer segmentation pie chart (4 segments)
- Price elasticity table with optimal pricing
- Product affinity / frequently bought together
- High potential vs low performer analysis

### Layer 4 — Decision Engine
- AI-generated decisions: pricing, inventory, marketing, staffing, menu
- Priority badges: critical / high / medium / low
- Confidence score bars
- One-click Approve / Reject workflow
- Filter by status

### Layer 5 — Autonomous Café OS
- System health dashboard (models active, revenue impact, alerts)
- Live KPI metrics with trend indicators
- Autonomous actions feed (auto-executed, scheduled, alerts)
- Sense → Decide → Act & Learn explanation

## Extending This Prototype

1. **Real data**: Replace mock data in `backend/main.py` with actual DB queries
2. **ML models**: Integrate real scikit-learn / PyTorch models for forecasting
3. **Auth**: Add JWT authentication
4. **Notifications**: Wire up push notifications for critical alerts
5. **Zomato/Swiggy API**: Connect real platform webhooks for live order data
