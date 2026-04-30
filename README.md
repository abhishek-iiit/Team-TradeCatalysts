# Team TradeCatalysts (SalesCatalyst)

SalesCatalyst is a full-stack lead-to-deal workflow platform for sales teams.  
It combines campaign and lead management, AI-assisted communication drafts, outreach tracking, and deal/meeting management in one system.

## Tech Stack

- **Frontend:** React + Vite + Tailwind CSS
- **Backend:** Django + Django REST Framework + JWT auth
- **Database:** PostgreSQL (default, configurable via `DATABASE_URL`)
- **Async Jobs:** Django Q2
- **Integrations:** Volza, Lusha, Gemini, Gmail/SMTP, Twilio (optional/env-driven)

## Repository Structure

```text
.
├── FE/   # React frontend
├── BE/   # Django backend API
└── docs/ # Additional project docs
```

## Prerequisites

- **Node.js** 20+ (with npm)
- **Python** 3.11+
- **PostgreSQL** 14+ (or use SQLite for quick local setup)

## Local Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd Team-TradeCatalysts
```

### 2. Backend setup (`BE/`)

```bash
cd BE
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `BE/.env` with your values.

Minimum required for local dev:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://localhost:5432/salescatalyst
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

If you want a no-Postgres quick setup, use SQLite:

```env
DATABASE_URL=sqlite:///db.sqlite3
```

Run migrations and start backend:

```bash
python manage.py migrate
python manage.py runserver 8000
```

Optional: start async worker (recommended for task/background flows):

```bash
python manage.py qcluster
```

Backend runs at: **http://localhost:8000**

### 3. Frontend setup (`FE/`)

Open a new terminal:

```bash
cd FE
npm install
npm run dev
```

Frontend runs at: **http://localhost:5173**

`FE/vite.config.js` proxies `/api` requests to `http://localhost:8000`, so frontend and backend work together locally out of the box.

## Common Commands

### Backend (`BE/`)

```bash
# run backend tests
pytest

# start Django shell
python manage.py shell

# create admin user
python manage.py createsuperuser
```

### Frontend (`FE/`)

```bash
# lint
npm run lint

# production build
npm run build

# preview build
npm run preview
```

## API Surface (High Level)

- `api/auth/*` → authentication (`signup`, `login`, `refresh`, `logout`, `me`, email settings)
- `api/products`, `api/campaigns`, `api/stage-configs`
- `api/leads`, `api/dashboard`
- `api/inbox`
- `api/ai-drafts`
- `api/deals`, `api/meetings`
- `api/trade-data/preview`, `api/trade-data/import`, `api/trade-data/explore`

## Environment Variables

Core and optional variables used across backend:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `SENDER_COMPANY_NAME`
- `GEMINI_API_KEY`, `GMAIL_OAUTH_CREDENTIALS_JSON`
- `VOLZA_API_KEY`, `LUSHA_API_KEY`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`

Use `BE/.env.example` as the starting template.

## Notes

- `manage.py` defaults to `config.settings.local`.
- CORS is configured for local frontend (`localhost:5173`).
- Media uploads are served from `BE/media/` in development.
