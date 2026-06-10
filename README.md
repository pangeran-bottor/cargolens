# CargoLens — AI-Powered Logistics Analytics Dashboard

Analytics dashboard + natural-language interface over a logistics dataset:
KPIs and charts, NL questions answered by deterministic tools routed through
an LLM orchestrator, and basic demand forecasting with inventory
recommendations.

> Full README (setup, architecture, AI approach, assumptions, limitations)
> is written at the end of development — this is a stub during the build.

## Quick start (dev)

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev   # http://localhost:3000
```

Environment variables: see `.env.example`.
