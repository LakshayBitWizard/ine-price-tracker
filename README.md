# Watchboard · INE Product Price Tracker

A reliable, full-stack product price and stock monitoring application built for the **INE Software Engineer Intern Assignment**. The system continuously monitors products from the hosted mock store ([demo.inelabteamdev.com](https://demo.inelabteamdev.com/)), extracts dynamic prices protected by interactive hover challenges, and maintains an honest history of all price changes and scrape outcomes.

---

## 🌐 Live Deployment Links

- **Live Frontend Dashboard**: [https://ine-price-tracker-lake.vercel.app/](https://ine-price-tracker-lake.vercel.app/) *(Deployed on Vercel)*
- **Live Backend API**: [https://ine-price-tracker-sr7i.onrender.com](https://ine-price-tracker-sr7i.onrender.com) *(Deployed on Render)*
- **API Health Check**: [https://ine-price-tracker-sr7i.onrender.com/api/db-check/](https://ine-price-tracker-sr7i.onrender.com/api/db-check/)
- **Database**: Supabase PostgreSQL
- **Mock Storefront (Target)**: [https://demo.inelabteamdev.com/](https://demo.inelabteamdev.com/)

---

## 🌟 Features

- **Live Storefront Search**: Search products across the mock store by partial or full name with resilient multi-pass catalog lookup.
- **Automated 2-Hour Scraping Schedule**: Configured for unattended cron scraping via external trigger (`cron-job.org`).
- **Resilient Dynamic Scraper**: Automated headless Chromium browser via Playwright that handles:
  - Cookie consent banners
  - Dynamic cursor movement and dwell-time simulation for anti-bot hover traps
  - Retries with exponential backoff on intermittent errors or rate limits
  - Detection of store page structural shifts
- **Honest Scrape Logging**: Per-product audit logs tracking every scrape attempt, HTTP status code, response time in ms, retry counts, and errors. Failures are never hidden.
- **Interactive Price History & Analytics**: Responsive charts, KPI stat cards, and stock status trends.
- **Observable Headed Run**: Built-in CLI command (`python manage.py scrape_products --all --headed`) for recording and visual auditing.

---

## 🛠 Tech Stack

- **Frontend**: React.js (Vite), Vanilla CSS design system with glassmorphism aesthetics — deployed on **Vercel**
- **Backend**: Python / Django 5 + Django REST Framework + Gunicorn — deployed on **Render**
- **Database**: PostgreSQL on **Supabase**
- **Browser Automation**: Playwright (Chromium)
- **Scheduler**: cron-job.org (external webhook trigger avoiding free-tier cold sleep)

---

## 📋 Architecture & Scraping Schedule

Free-tier backends sleep after 15 minutes of inactivity. Rather than running a fragile in-process background loop:
1. **External Webhook Trigger**: `cron-job.org` issues a secure authenticated `POST` request to `/api/cron/scrape/` every **2 hours** (`0 */2 * * *`).
2. **Bearer Token Authentication**: Uses `CRON_SECRET` header to ensure only authorized triggers execute sweeps.
3. **Due-Product Queue**: Products whose `last_scrape_at + scrape_interval_minutes <= now()` are scraped sequentially.
4. **Instant Manual Sweeps**: Users can also click **"Scrape now"** on any product in the dashboard for real-time verification.

---

## 🔐 Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | Supabase Postgres connection string (URI) | `postgresql://postgres:pass@db.xyz.supabase.co:5432/postgres` |
| `DJANGO_SECRET_KEY` | Secret key for Django | `your-secret-key` |
| `DJANGO_DEBUG` | Enable debug mode | `false` (in production) |
| `DJANGO_ALLOWED_HOSTS` | Allowed hostnames | `*` or `ine-backend.onrender.com,localhost` |
| `DJANGO_MANAGE_TABLES` | Let Django run migrations | `false` (tables created via `schema.sql`) |
| `CORS_ALLOWED_ORIGINS` | Permitted frontend origins | `https://your-frontend.vercel.app` |
| `STORE_BASE_URL` | INE Mock Store base URL | `https://demo.inelabteamdev.com` |
| `CRON_SECRET` | Secret token for external cron webhook | `your-random-cron-secret` |
| `SCRAPER_MAX_ATTEMPTS`| Max retry attempts per scrape | `3` |
| `SCRAPER_TIMEOUT_MS`  | Playwright locator / page timeout | `30000` |
| `SCRAPER_SLOW_MO_MS`  | Delay between browser actions (headed) | `120` |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
|---|---|---|
| `VITE_API_BASE_URL` | URL of the deployed Render backend | `https://ine-tracker-backend.onrender.com` |

---

## 🚀 Local Development Setup

### 1. Database Setup
Execute [`supabase/schema.sql`](supabase/schema.sql) in the Supabase SQL Editor.

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium

# Copy and fill environment variables
cp .env.example .env

# Run server
python manage.py runserver
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Dashboard is available at `http://localhost:5173`.

---

## 🎥 Observable Headed Run (Screen Recording)

To watch the browser navigate, dismiss cookies, move the mouse over the price container to satisfy the dwell-time check, click "Reveal price", and extract data:

```bash
cd backend
python manage.py scrape_products --all --headed
```

---

## 📄 License & Attribution
Created for the INE Software Engineer Intern Assignment.
Mock storefront provided by INE: `https://demo.inelabteamdev.com/`.
