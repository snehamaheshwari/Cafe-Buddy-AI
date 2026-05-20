# ☕ Cafe Buddy — AI Café Operating System

A full-stack AI product for intelligent café management — built with FastAPI (Python) + React (TypeScript).

---

## Project Structure

```
cafe-buddy/
├── backend/              # FastAPI Python backend
│   ├── main.py           # App entry point + all API routes
│   ├── chatbot.py        # AI chatbot with ML model integration
│   ├── multi_upload.py   # Data upload & parsing (POS, Financial, Customer, Menu, Reviews)
│   ├── ml_models.py      # ML forecasting, peak hours, cross-sell, cancellation risk
│   ├── sentiment_engine.py # TF-IDF + Linear SVM review sentiment analysis
│   ├── data_store.py     # In-memory data store with file persistence
│   ├── requirements.txt  # Python dependencies
│   └── tests/            # Unit tests (pytest)
├── frontend/             # React + TypeScript + Vite frontend
│   ├── src/
│   │   ├── pages/        # All page components
│   │   ├── components/   # Shared UI components
│   │   └── lib/api.ts    # Typed API client
│   ├── package.json
│   └── vite.config.ts
├── scripts/              # PM2 process management scripts
└── ecosystem.config.js   # PM2 config for all services
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | python.org |
| Node.js | 18+ | nodejs.org |
| npm | 9+ | bundled with Node |

---

## Local Setup (Development)

### 1. Clone the repository

```bash
git clone https://github.com/devstringx-technologies/capstoneaiproject.git
cd capstoneaiproject
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

### 3. Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

> The frontend proxies all `/api/*` calls to `localhost:8000` automatically (configured in `vite.config.ts`).

---

## Production Setup (Windows + PM2)

Used to keep the app running 24/7 on the host machine.

### Install PM2 globally

```bash
npm install -g pm2
```

### Start all services

```bash
cd capstoneaiproject

# Build frontend first
cd frontend && npm install && npm run build && cd ..

# Start backend + tunnel via PM2
npx pm2 start ecosystem.config.js
npx pm2 save
npx pm2 startup
```

### Useful PM2 commands

```bash
npx pm2 status               # Check all processes
npx pm2 restart cafe-backend # Restart backend
npx pm2 logs cafe-backend    # View backend logs
npx pm2 restart all          # Restart everything
```

---

## Environment & Configuration

No `.env` file is required for local development. All config is in code.

For WhatsApp notifications (optional):
- Create a free account at [green-api.com](https://green-api.com)
- Enter your `Instance ID` and `API Token` in the app's WhatsApp Alerts page

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React |
| Backend | FastAPI, Uvicorn, Pandas, scikit-learn, openpyxl |
| ML Models | Random Forest, Ridge Regression, FP-Growth, Linear SVC + TF-IDF |
| Process Manager | PM2 |
| Tunnel | localtunnel (cafebuddy-ai.loca.lt) |

---

## Features

- **Upload My Data** — Upload Excel/CSV files for Sales (POS), Financial, Customer CRM, Menu, and Reviews
- **Reports & Insights** — Auto-generated charts and summaries from uploaded data
- **Smart Analytics** — ML-powered forecasting, peak hour analysis, cross-sell recommendations, cancellation risk
- **Decision Engine** — AI-generated action items with approve/reject workflow
- **Auto-Pilot Mode** — Autonomous actions and live KPI tracking
- **Ask Cafe Buddy** — AI chatbot with real ML model integration
- **WhatsApp Alerts** — Daily café summary sent to WhatsApp via Green API

---

## Login Credentials (Demo)

| Username | Password |
|----------|----------|
| admin | admin123 |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "feat: your description"`
3. Push: `git push origin feature/your-feature`
4. Open a Pull Request on GitHub
