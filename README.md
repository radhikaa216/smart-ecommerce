# Smart E-Commerce Platform

A production-style, local office project using React, FastAPI, Django, MySQL, Redis, Celery, Stripe test mode, Auth0 development authentication, and authenticated SMTP email.

## What is implemented

- Responsive React storefront with catalog filters, product details, cart, checkout, orders, and notifications
- Local email/password demo mode and configurable Auth0 mode
- FastAPI catalog, cart, order, Stripe Checkout, webhook, and WebSocket APIs
- Server-side pricing and transactional stock reservations
- Idempotent Stripe webhook event storage
- Django product, inventory, customer, order, and payment administration
- Local product-image upload through Django Admin
- Sales dashboard, low-stock alerts, CSV export, and PDF export
- Redis/Celery email and reservation-expiry jobs
- Authenticated SMTP delivery to real recipient inboxes
- MySQL schema, Django migrations, automated tests, and Postman collection

## Prerequisites

The recommended setup only needs:

- Docker Desktop with Docker Compose
- A Stripe account in test mode for the real payment demonstration
- An Auth0 development tenant for the Auth0 demonstration
- SMTP credentials, such as a Gmail address and App Password, for real email delivery

Node.js and Python are only needed when running services outside Docker.

## Quick start

From PowerShell in the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Alternatively run `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1`.

Open:

| Service | URL |
|---|---|
| Storefront | http://localhost:5173 |
| FastAPI documentation | http://localhost:8000/docs |
| Django Admin | http://localhost:8001/admin/ |
| Analytics dashboard | http://localhost:8001/dashboard/ |

Local demo accounts are created idempotently at startup:

- Storefront: `customer@example.com` / `customer123`
- Django Admin: `admin` / `admin123`

Change these credentials if the project is ever made accessible beyond localhost.

## Local checkout modes

The default `.env.example` uses `STRIPE_DEMO_MODE=true`. It exercises order creation, stock reservation, payment-state transitions, email tasks, and notifications without contacting Stripe.

For actual Stripe test mode:

1. Set `STRIPE_DEMO_MODE=false`.
2. Add `pk_test_...` and `sk_test_...` keys to `.env`.
3. Install and authenticate Stripe CLI.
4. Start webhook forwarding:

```powershell
stripe listen --forward-to localhost:8000/api/v1/checkout/stripe/webhook
```

5. Copy the displayed `whsec_...` value into `STRIPE_WEBHOOK_SECRET` and restart FastAPI.

No live keys, KYC, bank details, or public endpoint are needed.

## Auth modes

Local mode is the default and makes the project immediately demonstrable:

```env
AUTH_MODE=local
VITE_AUTH_MODE=local
```

To demonstrate Auth0:

1. Create an Auth0 Single Page Application.
2. Create an Auth0 API with audience `https://api.smart-ecommerce.local`.
3. Add `http://localhost:5173` to callback, logout, and web-origin URLs.
4. Enable the database, Google, and—if available—Facebook connections.
5. Set both auth modes to `auth0` and fill in the Auth0 variables in `.env`.
6. Restart the frontend and FastAPI services.

## Email

Celery sends transactional messages through the authenticated SMTP provider configured in `.env`. For Gmail:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=your_google_app_password
EMAIL_FROM_ADDRESS=sender@gmail.com
```

Use a Google App Password rather than the account password. Keep credentials only in the ignored `.env` file; never add them to `.env.example` or commit them. After changing SMTP settings, recreate the mail-producing services:

```powershell
docker compose up -d --force-recreate django celery celery-beat
```

## Database ownership

Django migrations are the executable schema source of truth. [`database/schema.sql`](database/schema.sql) is the readable SQL deliverable. FastAPI SQLAlchemy models map to the same tables but never create or migrate them.

Useful commands:

```powershell
docker compose run --rm django python manage.py migrate
docker compose run --rm django python manage.py seed_demo
docker compose run --rm fastapi pytest
docker compose run --rm django python manage.py test
docker compose run --rm frontend npm test -- --run
```

## Repository layout

```text
frontend/          React storefront
fastapi_backend/   Customer-facing APIs
django_admin/      Schema migrations, admin, analytics, reports, Celery tasks
database/          MySQL schema snapshot
postman/           API collection and local environment
docs/              Architecture and implementation plan
```

## Security design demonstrated locally

- JWT issuer/audience/signature/expiry validation in Auth0 mode
- Password hashing in local demo mode
- Role checks and protected customer resources
- Server-owned prices and totals
- Row locking for stock reservations
- Stripe webhook signature validation and event idempotency
- No stored card data
- CORS restricted to the configured frontend
- Secrets loaded from ignored environment files
- Admin audit/history models and immutable order item snapshots

See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) for milestone scope and manual responsibilities.
