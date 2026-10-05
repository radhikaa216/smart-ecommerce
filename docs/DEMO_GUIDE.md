# Office Demonstration Guide

## Preparation

1. Copy `.env.example` to `.env`.
2. Keep `AUTH_MODE=local`, `VITE_AUTH_MODE=local`, and `STRIPE_DEMO_MODE=true` for an offline demonstration.
3. Run `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1`.
4. Wait for MySQL health checks and Django migrations to finish.
5. Open the storefront and Django Admin URLs from the README. Configure SMTP credentials in `.env` if you will demonstrate real email delivery.

## Suggested demonstration flow

1. Open the responsive storefront and show search, category, price sorting, and stock labels.
2. Sign in as `customer@example.com` using password `customer123`.
3. Add products to the cart and change quantities.
4. Begin checkout and explain that prices and stock are revalidated on FastAPI.
5. Complete local demo checkout and open order history.
6. Verify the confirmation email in the recipient inbox and show the successful Celery task log.
7. Sign in to Django Admin with `admin@example.com` / `admin123`.
8. Add/edit a product and upload an image from the local machine.
9. Update an order status and return to the React notification screen.
10. Open the analytics dashboard and export CSV/PDF reports.
11. Open FastAPI Swagger documentation and the supplied Postman collection.

## Stripe test-mode variant

For a real Stripe test demonstration, set `STRIPE_DEMO_MODE=false`, provide test keys, and run:

```powershell
stripe listen --forward-to localhost:8000/api/v1/checkout/stripe/webhook
```

Use a Stripe-documented test card on the Stripe-hosted page. No real funds are moved.

## Auth0 variant

After completing the localhost Auth0 dashboard steps in the README, switch both auth-mode variables to `auth0`, restart FastAPI and React, and demonstrate Universal Login. Local and Auth0 modes use the same application APIs and authorization boundary.

## Talking points

- Django migrations own the schema; FastAPI maps the same tables.
- MySQL stores permanent state; Redis stores transient queues/events.
- Celery isolates email and expiry jobs from API response time.
- Payment success comes from a verified, idempotent webhookÃ¢â‚¬â€not a browser redirect.
- Order items snapshot product name/SKU/price so history remains correct after catalog changes.
- Stock is reserved transactionally and returned when checkout expires.
