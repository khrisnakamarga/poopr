# Poopr

Poopr is a mobile-first web app for quick poop logging, personal poop statistics, group dashboards, leaderboards, and invite-code groups.

## Stack

- Frontend: React, TypeScript, Vite, Recharts, Lucide icons
- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL-compatible models
- Local database: SQLite by default for quick development
- Production target: Azure Container Apps, Azure Database for PostgreSQL Flexible Server, Azure Container Registry, Key Vault, Application Insights

## Local Development

Start the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

The frontend expects the API at `http://localhost:8000` unless `VITE_API_BASE_URL` is set.

## Auth

The backend accepts an `X-User-Email` header and auto-provisions a local profile for development. In production, users sign in with Google OAuth and the backend protects API requests with a signed session cookie.

## Production Google Sign-In

Production uses Poopr's backend-owned Google OAuth flow behind the public frontend Container App. Azure Container Apps built-in auth should stay disabled so `/.auth/login/google/callback` can be proxied to the FastAPI callback.

Create a Google OAuth web client and add this authorized redirect URI:

```text
https://<your-container-app-host>/.auth/login/google/callback
```

For the current production app, print the exact redirect URI with:

```powershell
.\infra\enable-google-auth.ps1 -PrintRedirectUriOnly
```

After creating the Google OAuth client, configure Azure:

```powershell
$env:GOOGLE_CLIENT_ID = "<google-oauth-client-id>"
$env:GOOGLE_CLIENT_SECRET = "<google-oauth-client-secret>"
.\infra\enable-google-auth.ps1
```

The backend exchanges the Google authorization code, validates the ID token, sets a signed `poopr_session` cookie, and auto-provisions the user's profile from the Google email claim.

## Repo Layout

- `frontend/`: mobile-first browser application
- `backend/`: FastAPI API, domain models, migrations, tests
- `infra/`: Azure Bicep starter infrastructure
- `docs/`: architecture notes and operating assumptions

