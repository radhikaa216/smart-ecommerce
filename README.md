# Smart E-Commerce Platform

A full-stack e-commerce application with a React storefront, FastAPI customer API, Django administration, MySQL persistence, Redis/Celery background processing, Stripe Checkout, Auth0 authentication, and SMTP email delivery.

The current local setup runs the application services in Docker and connects them to MySQL Server on Windows. A fully Docker-based MySQL setup is also supported.

New to the project? Read the [complete beginner-friendly application handbook](APPLICATION_HANDBOOK.md) for every UI, API, database, Auth0, Stripe, Redis, Celery, SMTP, webhook, and Django Admin flow.

## Implemented features

- Product catalog with search, category filters, sorting, product details, stock status, and images
- Customer registration and sign-in using local credentials, Auth0, or both
- Persistent cart with server-side product and price validation
- Checkout with 30-minute transactional stock reservations
- Stripe Checkout in test mode and an offline demo-payment mode
- Idempotent Stripe webhook handling and immutable order-item snapshots
- Customer order history and real-time notifications over WebSockets
- Django administration for products, categories, users, orders, payments, and status changes
- Product-image upload from Django Admin
- Sales dashboard, low-stock reporting, and CSV/PDF exports
- Celery tasks for transactional email and expired-stock release
- Authenticated SMTP delivery with delivery logging
- Shared MySQL tables across Django ORM and FastAPI SQLAlchemy models
- Automated backend and frontend tests plus a Postman collection

## Architecture

```mermaid
flowchart LR
    Browser[React storefront] --> API[FastAPI API]
    Admin[Django Admin and dashboard] --> DB[(MySQL)]
    API --> DB
    API --> Redis[(Redis)]
    Django[Django application] --> DB
    Django --> Redis
    Redis --> Worker[Celery worker]
    Beat[Celery beat] --> Redis
    Worker --> SMTP[SMTP provider]
    Stripe[Stripe test mode] --> API
```

### Components and their use

| Component | Technology | Purpose | Default address |
|---|---|---|---|
| Storefront | React 19, TypeScript, Vite | Catalog, authentication, cart, checkout, orders, and notifications | `http://localhost:5173` |
| Customer API | FastAPI, SQLAlchemy | Authentication, catalog, cart, checkout, orders, Stripe webhooks, and WebSockets | `http://localhost:8000` |
| Administration | Django | Database migrations, administration, analytics, reports, and demo-data seeding | `http://localhost:8001` |
| Celery worker | Celery | Sends transactional emails and executes queued background work | Internal service |
| Celery beat | Celery | Schedules expired stock-reservation cleanup every minute | Internal service |
| Redis | Redis | Celery broker/results and real-time notification pub/sub | `localhost:6379` |
| Database | MySQL 8 | Permanent application data shared by Django and FastAPI | Windows `localhost:3306` or Docker host port `3307` |
| Stripe | Stripe Checkout | Test payments and signed payment webhooks | External test service |
| SMTP | Gmail or another SMTP provider | Order confirmations, payment failures, and status emails | External service |

## Repository layout

```text
database/          Readable SQL schema snapshot
django_admin/      Django models, migrations, admin, dashboard, reports, and Celery tasks
fastapi_backend/   Customer-facing REST and WebSocket API
frontend/          React storefront
media/             Local product uploads; generated and not committed
postman/           API collection and local environment
docker-compose.yml Local service orchestration
.env.example       Environment-variable template without real secrets
```

## Prerequisites

Required:

- Docker Desktop with Docker Compose
- Git
- MySQL Server 8 on Windows when using the current Windows MySQL configuration

Optional integrations:

- A Stripe account in test mode and Stripe CLI
- An Auth0 development tenant
- SMTP credentials, such as a Gmail account with an App Password

Node.js and Python are needed only when running services directly outside Docker.

## Environment configuration

Create the local environment file from the template:

```powershell
Copy-Item .env.example .env
```

Never commit `.env`; it contains database passwords, API keys, and other secrets.

### Option A: Windows MySQL Server (current setup)

Create or select a MySQL 8 database named `smart_ecommerce` and a user with full privileges on it. Because Django and FastAPI run inside Docker, use `host.docker.internal` rather than `localhost`:

```env
DB_HOST=host.docker.internal
DB_PORT=3306
DB_NAME=smart_ecommerce
DB_USER=your_windows_mysql_user
DB_PASSWORD=your_windows_mysql_password
DATABASE_URL=
```

`DATABASE_URL` must be empty or removed. FastAPI gives it precedence over the individual `DB_*` settings; leaving the Docker connection URL there would make FastAPI connect to the wrong database.

Ensure Windows MySQL accepts TCP connections from Docker and that Windows Firewall permits the configured MySQL port. The MySQL container declared in Compose may still start because it is part of the dependency graph, but the application uses Windows MySQL whenever `DB_HOST=host.docker.internal`.

### Option B: Docker MySQL

For a fully containerized database, use the defaults represented by `.env.example`:

```env
DB_HOST=mysql
DB_PORT=3306
DB_NAME=smart_ecommerce
DB_USER=smart_ecommerce
DB_PASSWORD=replace_me
DATABASE_URL=mysql+pymysql://smart_ecommerce:replace_me@mysql:3306/smart_ecommerce

MYSQL_DATABASE=smart_ecommerce
MYSQL_USER=smart_ecommerce
MYSQL_PASSWORD=replace_me
MYSQL_ROOT_PASSWORD=replace_me
MYSQL_HOST_PORT=3307
```

The application connects to port `3306` inside the Docker network. MySQL Workbench connects from Windows through `localhost:3307`.

## Run the application

From PowerShell in the repository root:

```powershell
docker compose up --build
```

To run in the background:

```powershell
docker compose up -d --build
docker compose ps
```

During startup, Django automatically:

1. Applies committed migrations.
2. Runs the idempotent `seed_demo` command.
3. Starts the development server on port `8001`.

The seed command creates demo products and these accounts if they do not already exist:

| Use | Email | Password |
|---|---|---|
| Storefront customer | `customer@example.com` | `customer123` |
| Django administrator | `admin@example.com` | `admin123` |

These credentials are for local development only. Change or disable them before exposing the application to another network.

### Verify the services

| Page or endpoint | URL |
|---|---|
| Storefront | `http://localhost:5173` |
| FastAPI health | `http://localhost:8000/health` |
| FastAPI Swagger UI | `http://localhost:8000/docs` |
| Django Admin | `http://localhost:8001/admin/` |
| Analytics dashboard | `http://localhost:8001/dashboard/` |
| Sales CSV | `http://localhost:8001/reports/sales.csv` |
| Sales PDF | `http://localhost:8001/reports/sales.pdf` |

The Django dashboard and reports require a staff or administrator login.

## How each application area is used

### React storefront

- `/` displays and filters the product catalog.
- `/products/:slug` displays product details and quantity selection.
- `/login` provides local login/registration and Auth0 login when enabled.
- `/cart` manages authenticated customer cart items.
- `/checkout/success` completes demo checkout or handles the Stripe return.
- `/orders` displays the authenticated customer?s order history.
- `/notifications` displays stored notifications and receives live updates.

### FastAPI

All customer endpoints use the `/api/v1` prefix:

| Area | Main endpoints |
|---|---|
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Catalog | `GET /categories`, `GET /products`, `GET /products/{slug}` |
| Cart | `GET /cart`, `POST /cart/items`, `PATCH /cart/items/{id}`, `DELETE /cart/items/{id}` |
| Checkout | `POST /checkout/create-session`, `POST /checkout/demo-complete/{order_number}` |
| Orders | `GET /orders` |
| Notifications | `GET /notifications`, `POST /notifications/read-all`, `WS /ws/notifications` |
| Stripe webhook | `POST /checkout/stripe/webhook` |

FastAPI owns customer-facing workflows but does not create database tables. Its SQLAlchemy models map to the schema owned by Django migrations.

### Django

Django is responsible for:

- The canonical data model and migrations
- Customer, staff, and administrator records in the shared `users` table
- Product/category management and product-image uploads
- Order, payment, and order-status administration
- Analytics, low-stock information, and report exports
- Demo-data seeding
- Email templates and Celery task definitions

### Redis, Celery worker, and Celery beat

- Redis carries Celery tasks and publishes user-notification events.
- The Celery worker sends transactional email outside the API request cycle.
- Celery beat runs `release_expired_stock` every minute.
- Expired checkout reservations return stock and mark the associated order as failed/cancelled when appropriate.

## Authentication modes

### Local authentication

Use local email/password login only:

```env
AUTH_MODE=local
VITE_AUTH_MODE=local
```

FastAPI issues an application JWT after successful login.

### Hybrid authentication

Allow both local credentials and Auth0 Universal Login:

```env
AUTH_MODE=hybrid
VITE_AUTH_MODE=hybrid
```

Configure these Auth0 values in `.env`:

```env
VITE_AUTH0_DOMAIN=your-tenant.region.auth0.com
VITE_AUTH0_CLIENT_ID=your_spa_client_id
VITE_AUTH0_AUDIENCE=https://api.smart-ecommerce.local
AUTH0_DOMAIN=your-tenant.region.auth0.com
AUTH0_AUDIENCE=https://api.smart-ecommerce.local
```

In Auth0, configure `http://localhost:5173` as an allowed callback URL, logout URL, and web origin. The API access token must contain the user?s email and profile fields, normally added by a Post-Login Action under the `https://smart-ecommerce.local/` claim namespace.

### Auth0-only authentication

```env
AUTH_MODE=auth0
VITE_AUTH_MODE=auth0
```

Local login and registration are hidden in this mode.

Restart the frontend and FastAPI after changing authentication settings:

```powershell
docker compose up -d --force-recreate frontend fastapi
```

## Checkout and payments

### Offline demo checkout

```env
STRIPE_DEMO_MODE=true
```

This exercises order creation, stock reservation, payment-state transitions, email tasks, and notifications without calling Stripe.

### Stripe test mode

```env
STRIPE_DEMO_MODE=false
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_replace_me
STRIPE_SECRET_KEY=sk_test_replace_me
STRIPE_WEBHOOK_SECRET=whsec_replace_me
STRIPE_CURRENCY=inr
```

Install and authenticate Stripe CLI, then forward test webhooks:

```powershell
stripe listen --forward-to localhost:8000/api/v1/checkout/stripe/webhook
```

Copy the CLI-provided `whsec_...` secret into `.env`, then recreate FastAPI:

```powershell
docker compose up -d --force-recreate fastapi
```

Use test keys and Stripe test cards only. The application does not store card details.

## Transactional email

Configure an authenticated SMTP provider in `.env`. For Gmail:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=your_google_app_password
SMTP_TIMEOUT_SECONDS=15
EMAIL_FROM_ADDRESS=sender@gmail.com
EMAIL_FROM_NAME=Smart Ecommerce
```

Use a Google App Password instead of the normal account password. Restart services that send or queue mail:

```powershell
docker compose up -d --force-recreate django celery celery-beat fastapi
```

Delivery attempts are recorded in the `email_delivery_logs` table.

## Database and migrations

Django migrations are the executable schema source of truth. `database/schema.sql` is a readable schema snapshot; FastAPI models must remain compatible with the Django-managed tables.

Run migrations manually:

```powershell
docker compose exec django python manage.py migrate
```

After intentionally changing Django models:

```powershell
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
```

Commit intentional migration files so every environment can reproduce the schema.

Re-run the idempotent demo seed:

```powershell
docker compose exec django python manage.py seed_demo
```

Product uploads are stored under `media/`, which is mounted into the Django container and excluded from Git.

## Tests and validation

Run the FastAPI tests:

```powershell
docker compose run --rm fastapi pytest -q
```

Run the Django tests:

```powershell
docker compose run --rm django python manage.py test
```

Django creates a temporary database named `test_smart_ecommerce`. The configured MySQL user must have permission to create and delete that test database. If necessary, grant test-database privileges using an administrative MySQL account and a host matching your setup:

```sql
GRANT ALL PRIVILEGES ON `test_smart_ecommerce`.* TO 'your_windows_mysql_user'@'%';
FLUSH PRIVILEGES;
```

Run frontend tests and the production build:

```powershell
docker compose run --rm frontend npm test -- --run
docker compose run --rm frontend npm run build
```

Run Django?s configuration check:

```powershell
docker compose exec django python manage.py check
```

## Common Docker commands

```powershell
# View status
docker compose ps

# Follow all logs
docker compose logs -f

# Follow one service
docker compose logs -f fastapi

# Rebuild and restart changed services
docker compose up -d --build

# Stop services while preserving database volumes
docker compose down
```

Avoid `docker compose down -v` unless you intentionally want to delete Docker-managed MySQL and frontend volumes.

## Troubleshooting

### FastAPI connects to the old Docker database

Clear or remove `DATABASE_URL` and confirm:

```env
DB_HOST=host.docker.internal
```

Then recreate FastAPI:

```powershell
docker compose up -d --force-recreate fastapi
```

### Windows MySQL connection is refused

- Confirm MySQL Server is running and listening on port `3306`.
- Confirm the MySQL user may connect from Docker, not only from `localhost`.
- Check Windows Firewall rules for the MySQL port.
- Test the same credentials in MySQL Workbench.

### Django tests cannot create the test database

Grant the configured MySQL user privileges on `test_smart_ecommerce`, then rerun the tests.

### Changes to `.env` do not appear

Environment variables are read when containers are created. Recreate the affected services with `docker compose up -d --force-recreate ...`.

### Email is queued but not delivered

Check worker logs and SMTP values:

```powershell
docker compose logs -f celery
```

## Security notes

- Keep `.env`, database dumps, uploads, and generated exports out of Git.
- Use only Stripe test keys in local development.
- Replace demo credentials and development secrets before network exposure.
- Auth0 JWT issuer, audience, signature, and expiry are validated by FastAPI.
- Prices and totals are calculated on the server.
- Stock updates use database transactions and row locking.
- Stripe webhook signatures are validated and event IDs are processed idempotently.
- Order items retain product/price snapshots for historical accuracy.
- Card data is handled by Stripe and is never stored by this application.
