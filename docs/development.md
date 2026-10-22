# Working on Poopr

This guide is for editing the app yourself. Commands use Windows PowerShell. You can run the app locally without an Azure account, Google OAuth credentials, or Docker.

## First-time setup

Install Git, Python 3.12 or newer, and Node.js 22.12 or newer in the 22.x series (the frontend container also uses Node 22). Use an editor such as VS Code. Check your installation in a new terminal:

```powershell
git --version
python --version
node --version
npm --version
```

If you already have the project locally, open that folder. Otherwise:

```powershell
git clone https://github.com/khrisnakamarga/poopr.git
cd poopr
```

Open two terminals in the project folder. Keep both running while developing.

In terminal 1, install and start the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

These commands use the virtual environment directly, so you do not need to activate it or change PowerShell's execution policy. The migration command creates the local SQLite database at `backend/poopr.db`.

In terminal 2, install and start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open the address printed by Vite, normally `http://localhost:5173`. The backend health endpoint is `http://localhost:8000/health`; interactive API documentation is at `http://localhost:8000/docs`.

On later visits, only run the Uvicorn and Vite commands in their respective folders. Run `npm ci` again when the frontend lockfile changes, reinstall Python dependencies when `pyproject.toml` changes, and run `alembic upgrade head` when new migrations arrive. Stop either server with Ctrl+C.

## Try it before editing

1. Create a log and check History and Reports.
2. Open Profile and change your display name.
3. Create a group and generate an invite code.
4. Use a different development email in Profile, then join with the code to test another member's view.

Local mode defaults to `demo@poopr.local`. The browser remembers the selected email in local storage under `poopr.email`. The API provisions a user/profile on first use. This email switcher is a development convenience, not a real sign-in mechanism.

## Where to make changes

Paths below are relative to the repository root.

| What you want to change | Start here |
| --- | --- |
| Text, forms, navigation, and screens | `frontend/src/App.tsx` |
| Colors, spacing, layout, mobile styling | `frontend/src/styles.css` |
| Browser API calls and response types | `frontend/src/api.ts` |
| App mounting and render-error screen | `frontend/src/main.tsx` |
| Browser test | `frontend/src/App.test.tsx` |
| Creating, listing, updating, deleting logs | `backend/app/routers/poop_logs.py` |
| Profile updates | `backend/app/routers/profile.py` |
| Groups, invitations, dashboards | `backend/app/routers/groups.py` |
| Personal reports and statistics | `backend/app/routers/reports.py`, `backend/app/services/stats.py` |
| API field types and validation | `backend/app/schemas.py` |
| Database tables and relationships | `backend/app/models.py` |
| Database schema migrations | `backend/alembic/versions/` |
| Current user and access dependencies | `backend/app/deps.py` |
| Google login and signed sessions | `backend/app/routers/auth.py`, `backend/app/session.py` |
| Backend settings and route registration | `backend/app/core.py`, `backend/app/main.py` |
| Backend tests | `backend/tests/test_api.py` |
| Container routing | `frontend/nginx.conf.template` |
| Azure setup/deployment | `infra/` |

`App.tsx` currently contains `App`, `LogView`, `HistoryView`, `ReportsView`, `GroupsView`, and `ProfileView`. Search for a visible label or one of these function names to find a screen. Navigation is React state (`view`), rather than separate page URLs.

## How a change travels through the app

For a new log, `LogView` calls `api.createLog()` in `api.ts`. That sends JSON to `POST /api/v1/poop-logs`. FastAPI validates it with `PoopLogCreate`, resolves the current user, and stores a SQLAlchemy `PoopLog`. The route also adds activity entries for the user's groups. The UI then refreshes its data.

There are three separate descriptions of a field to keep aligned: the database model, the Python request/response schemas, and the TypeScript types. Changing only one will not automatically update the others.

## Common edits

### Change text or styling

For a first edit, find `Mobile-first poop stats` in `App.tsx` and change the text. Save and check the browser; Vite reloads the UI automatically. For its appearance, find `.eyebrow` in `styles.css`. Check both a narrow phone-sized viewport and a desktop viewport. A text or CSS edit does not require a database migration.

### Change a validation limit

For example, the notes length limit is defined in `PoopLogCreate` in `schemas.py`. When changing a limit:

1. Update the backend validation and inspect the corresponding model for storage constraints.
2. Search `App.tsx` for the input and keep its restrictions/help text consistent.
3. Add a backend test for an accepted value and a rejected value at the boundary.
4. Try the form and confirm API errors are understandable in the browser.

### Add a stored field

1. Add the column in `backend/app/models.py`, deciding whether existing rows may have no value or need a default.
2. Add it to the appropriate create/update/read schemas in `schemas.py`.
3. From `backend`, generate a migration against your up-to-date local development database:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Add field to poop logs"
   ```

4. Read the generated file in `alembic/versions/`. Check defaults, existing rows, and the downgrade operation. Autogeneration needs review; SQLite may require Alembic batch operations for some table alterations. Add a new migration instead of editing an already-applied one.
5. Apply it locally with `alembic upgrade head` using the same Python command prefix.
6. Update the corresponding types/payload in `frontend/src/api.ts`, then add the input/display in `App.tsx`.
7. Test saving and reloading the field, including an older record without it.

Backend tests create tables directly in an in-memory SQLite database. They do not prove your migration works, so also apply the migration to a disposable local database. Production uses PostgreSQL; database-specific changes need verification there too.

### Add an API operation

Follow a nearby handler in `backend/app/routers/`. Add request/response schemas as needed and a matching method in `frontend/src/api.ts`. If you create a new router module, register it in `backend/app/main.py`. Use `/docs` to inspect and try the resulting API.

Keep reads and writes scoped to the current user; group operations must verify membership. Add tests using two different users to check that one cannot access the other's private data. Existing examples are in `backend/tests/test_api.py`.

The API already has PATCH and DELETE log routes, although `api.ts` currently exposes only listing and creation. Also, `PoopLogUpdate` currently inherits the create schema: its PATCH route requires `occurred_at` and applies defaults for omitted optional fields. Account for that behavior if adding an edit form.

## Local settings

Defaults work without any environment files. For overrides, create `backend/.env` and/or `frontend/.env`. Both are ignored by Git. Run backend commands from `backend`, because its `.env` and SQLite paths are relative to the working directory.

Example `backend/.env`:

```dotenv
DATABASE_URL=sqlite:///./poopr.db
CORS_ORIGINS=http://localhost:5173
AUTH_MODE=dev
APP_BASE_URL=http://localhost:5173
```

Example `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_AUTH_MODE=dev
```

Restart the relevant server after changing environment settings. Vite embeds `VITE_*` values in the browser build; these values must never contain secrets. Production uses `easy_auth` as the auth mode name even though Google sign-in is handled by the backend. See the [README](../README.md#production-google-sign-in) and [architecture notes](architecture.md) for that flow.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Could not reach the API / failed fetch | Check the backend terminal and `/health`; verify `VITE_API_BASE_URL`. |
| CORS error in browser console | Use `localhost` consistently. Match `CORS_ORIGINS` to the exact frontend origin, including the port. If Vite selected 5174, update the setting and restart the backend. |
| `no such table` or missing column | From `backend`, run the migration command; confirm `DATABASE_URL` points to the expected local database. |
| Python module not found | Use `.venv\Scripts\python.exe` from `backend` and install `".[dev]"` into that environment. |
| PowerShell blocks `npm.ps1` | Use `npm.cmd` in place of `npm` in the examples. |
| Unexpected login redirect locally | Check both auth modes are `dev`, then restart both servers. |
| Old or unexpected local user | Check the Profile email and the browser's `poopr.email` local-storage value. |
| UI fails after an edit | Read the Vite terminal and browser developer console; inspect failed requests in the Network tab. |

Local data persists in `backend/poopr.db`; restarting servers does not clear it. For a fresh local database, stop the backend, rename that file as a backup, run migrations, and restart. First verify that you are using the default SQLite URL, not an external database.

## Local changes versus the live app

Saving files affects your local servers. Committing and pushing puts code on GitHub. Neither action itself runs the Azure deployment scripts; this repository currently has no GitHub Actions deployment workflow.

The scripts in `infra/` change Azure resources and settings. In particular, `deploy-production.ps1` generates a database password and generates a session secret when none is supplied, so review its behavior before using it against existing resources. You do not need it for ordinary local edits. Use the [contribution guide](../CONTRIBUTING.md) to validate and share your changes first.
