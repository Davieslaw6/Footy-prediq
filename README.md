# Football Prediction Platform v2

Full-stack football match prediction app: dark-themed Next.js frontend,
Python/FastAPI backend, XGBoost + Optuna models, PostgreSQL, and a
continuous-learning retraining pipeline.

## What's here

```
backend/
  app/
    main.py
    db/models.py
    db/session.py
    ml/insights.py
    ml/predict_service.py
    ml/feature_lookup.py
    ml/retrain_runner.py
  ml/
    features.py
    train.py
    pipelines/retrain_job.py
  requirements.txt

frontend/
  src/
    app/page.tsx
    app/match/[id]/page.tsx
    components/
      FixtureList.tsx
      MatchHeader.tsx
      PredictionCard.tsx
      RiskBadge.tsx
      InsightBox.tsx
    types/prediction.ts
  package.json

docker-compose.yml
.env.example
```

## Setup

See "Deploying" below for Docker Compose, Vercel/Railway, and local
(no-Docker) instructions.

## Data — what you need to supply

This build ships the full pipeline (schema, feature engineering, training,
serving, retraining) plus the prediction API. Two more pieces still need
your own data/credentials:

1. **Historical training data** — a CSV with columns matching what
   `ml/features.py` expects: `home_team, away_team, kickoff_utc, home_goals,
   away_goals, home_corners, away_corners, home_xg, away_xg, result`.
   Sources like API-Football (paid, has corners/xG) or FBref (free scraping,
   no corners in the free tier) both work — write a small adapter script to
   shape their output into this CSV format.
2. **Daily fixtures** — populate the `matches` table with upcoming fixtures
   (via the same provider). `GET /api/matches/upcoming` reads directly from
   Postgres.

## Odds / bookmaker integrations

There is currently no bookmaker-specific odds API integration in the project.
The prediction endpoint returns model predictions only:

- Winner
- Over/Under Goals
- Over/Under Corners
- Confidence
- Risk
- Prediction call
- Match insight

If an odds provider is added later, it should be implemented as a separate
provider module without coupling the core prediction service to a bookmaker.

## Honest limitations / things to verify before relying on this

- **`feature_lookup.py` recomputes full team history per prediction request.**
  Fine at low-to-moderate traffic; cache rolling state if it becomes a bottleneck.
- **League enum in `db/models.py` lists a handful of leagues explicitly**
  with an `OTHER` catch-all — add leagues as data sources are wired up.
- **The scheduled retrain job is separate from the API process** and is run by
  Docker Compose or a cron/scheduled task.
- **The admin API key is optional.** Set it before public deployment.

## Deploying

### Option A — Docker Compose (single VPS)

```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD, ADMIN_API_KEY, and NEXT_PUBLIC_API_BASE

docker compose up -d --build
```

This starts four services:
- `db` — Postgres 16
- `backend` — FastAPI on port 8000
- `scheduler` — Mon/Thu 06:00 retraining
- `frontend` — Next.js on port 3000

Upload historical CSV data:
```bash
curl -X POST http://your-server:8000/api/admin/training-data/import \
  -H "X-Admin-Key: your-admin-key" \
  -F "file=@matches.csv" -F "tune=false"
```

Then seed at least one upcoming fixture in `matches` and visit
`http://your-server:3000`.

Put the deployment behind a reverse proxy with HTTPS rather than exposing
ports 3000/8000 directly.

### Option B — Vercel frontend + Railway/Render backend + Postgres

1. Deploy `backend/` to Railway or Render with PostgreSQL and set
   `DATABASE_URL`, `ALLOWED_ORIGINS`, and `ADMIN_API_KEY`.
2. Import `frontend/` into Vercel, set its root directory to `frontend/`,
   and set `NEXT_PUBLIC_API_BASE` to the backend URL.
3. Configure scheduled retraining as a separate cron/scheduled service.

### Local development

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/football_predictor
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.
