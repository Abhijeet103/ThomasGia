# PrepGIA

PrepGIA is a Django application for Thomas GIA practice with:

- Django views and templates
- Django static assets in `static/css` and `static/js`
- SQLite database
- Python question-generation pipeline

## Current scope

- Django app skeleton with role-based user model
- Google OAuth-ready authentication flow via `django-allauth`
- Free and paid access model
- One-time full test rule for free users
- Section-wise test support
- Django SEO-friendly server-rendered pages
- SQLite database schema
- Python question generators for all 5 sections
- Export pipeline from SQLite into JSON for question previews

## Project structure

- `backend/`: Django project config and apps
- `templates/`: Django templates
- `static/`: CSS and JS assets
- `lib/`: shared question preview helpers
- `prepgia/schema.py`: SQLite schema and seed helpers
- `prepgia/generators.py`: question generation logic
- `scripts/init_db.py`: database initialization
- `scripts/generate_questions.py`: sample question generation and persistence
- `scripts/export_questions.py`: export generated questions for Next.js consumption

## Django backend

Install backend dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

Run Django:

```bash
PYTHONPATH=. .venv/bin/python manage.py runserver
```

Copy environment variables first:

```bash
cp .env.example .env
```

Important backend endpoints:

- `/accounts/google/login/`
- `/api/auth/session/`
- `/api/auth/google/`
- `/api/billing/status/`
- `/api/billing/checkout/weekly/`
- `/api/billing/stripe/webhook/`
- `/api/tests/sections/`
- `/api/tests/attempts/start/`

## Python data pipeline

Initialize the database:

```bash
PYTHONPATH=. .venv/bin/python scripts/init_db.py
```

Generate sample questions:

```bash
PYTHONPATH=. .venv/bin/python scripts/generate_questions.py --section all --difficulty easy --count 3
```

Export questions for the Next app:

```bash
PYTHONPATH=. .venv/bin/python scripts/export_questions.py
```

## Django pages

Useful routes:

- `/`
- `/practice`
- `/sections`
- `/sections/reasoning`
- `/login`
- `/pricing`
- `/dashboard`

## SEO direction

The Django page structure is set up to support:

- server-rendered marketing pages
- route-level metadata
- section-specific landing pages
- keyword-focused information architecture
- later addition of sitemap, robots, and structured data

## Access rules

- Every new user starts as `free`
- Free users can take the full test only once
- Free users can use section-wise tests
- Paid users can take unlimited full tests
- Paid users can take unlimited section-wise tests
- After purchase, the backend upgrades the role from `free` to `paid`

## Stripe setup

Add these values to `.env`:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_WEEKLY`
- `STRIPE_PRICE_MONTHLY`
- `STRIPE_PRICE_YEARLY`

Local webhook forwarding example:

```bash
stripe listen --forward-to http://127.0.0.1:8000/api/billing/stripe/webhook/
```
