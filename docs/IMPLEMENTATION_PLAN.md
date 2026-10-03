# Smart E-Commerce Local Implementation Plan

## 1. Scope and interpretation of "production style"

This office assignment will run entirely on a developer machine and will not be deployed to a production environment. "Production style" therefore means that the code will use clean service boundaries, environment-based configuration, migrations, validation, authorization, transactions, idempotent payment handling, background jobs, logging, automated tests, and documentation.

It does not require AWS/Azure/GCP, a public domain, production DNS, Kubernetes, a cloud database, object storage, live Stripe payments, or a live email provider.

Stripe and Auth0 remain external development services because the assignment explicitly asks for those integrations. Stripe will remain in test mode and Auth0 will use localhost callback URLs. All application data and supporting services will run locally.

## 2. Local technology stack

- Customer frontend: React with TypeScript and Vite
- Styling: Tailwind CSS
- Customer API: FastAPI
- Administration: Django and Django Admin with custom analytics pages
- Database: MySQL 8
- Schema ownership: Django migrations; FastAPI uses matching SQLAlchemy models
- Background jobs: Celery
- Job broker and WebSocket event distribution: local Redis
- Authentication: Auth0 development tenant
- Payments: Stripe Checkout in test mode
- Email demonstration: local Mailpit SMTP server and browser inbox
- Product images: local `media/` directory
- Charts: Chart.js
- Reports: CSV and PDF generated locally
- Local orchestration: Docker Compose

## 3. Local architecture

```text
React :5173
   |
   +---- FastAPI :8000 ---- MySQL :3306
   |          |                 |
   |          +---- Redis :6379 |
   |                    |       |
   |                 Celery ----+
   |                    |
   |                 Mailpit :1025
   |                    |
   |             Mail UI :8025
   |
   +---- Django Admin :8001 ---- local media/

External development-only services:
- Auth0 tenant for login and JWTs
- Stripe test environment for checkout
```

MySQL is the permanent source of truth. Redis contains only temporary job/event data. Mailpit captures emails locally and does not deliver them to real addresses.

## 4. Application responsibilities

### React

- Registration/login entry points through Auth0
- Responsive product catalog and product detail pages
- Search, category, price, and popularity filters
- Cart and checkout screens
- Order history and order tracking
- Notification centre and WebSocket updates
- Payment success/failure pages

### FastAPI

- JWT validation and current-user synchronization
- Product browsing APIs
- Cart and checkout APIs
- Stripe Checkout Session creation
- Stripe webhook verification and processing
- Customer order APIs
- Notification and WebSocket APIs
- OpenAPI documentation

### Django

- MySQL models and migrations
- User and role administration
- Category, product, inventory, and image management
- Order management and status updates
- Analytics dashboard
- CSV/PDF exports
- Audit log views

### Celery and Redis

- Send emails outside the API request
- Release expired stock reservations
- Generate longer reports
- Distribute notification events across WebSocket workers

Both services run locally in Docker; no managed Redis service is required.

## 5. Delivery phases

### Phase 1: Local foundation

Implementation:

- Preserve and review the existing FastAPI skeleton.
- Create the React and Django applications.
- Add Docker Compose services for MySQL, Redis, Mailpit, FastAPI, Django, React, and Celery.
- Add `.env.example`, health checks, structured logging, formatting, and test commands.
- Convert the baseline SQL design into Django models and migrations.
- Add demo-data seed commands.

Acceptance: the complete local environment starts using documented commands and all health checks pass.

### Phase 2: Catalog and admin

Implementation:

- Category, product, product-image, and inventory models.
- Django Admin CRUD, search, filters, validation, and local image uploads.
- FastAPI catalog endpoints with pagination, filters, sorting, and search.
- Responsive React catalog and product detail pages.

Acceptance: products entered in Django appear in React through FastAPI.

### Phase 3: Auth0 and roles

Implementation:

- Auth0 React SDK configuration.
- Login, logout, callback, protected routes, and authenticated API calls.
- FastAPI RS256 JWT validation using issuer, audience, expiry, and Auth0 signing keys.
- Local user profile synchronization.
- Customer, staff, and admin permission enforcement.
- Authorization tests.

Acceptance: email/password login and configured social login work on localhost, and unauthorized actions are rejected.

### Phase 4: Cart and inventory

Implementation:

- Cart add, update, remove, and clear operations.
- Server-side price and stock validation.
- Address capture and checkout preview.
- Transactional stock reservation and automatic expiration.
- Concurrency test for two customers attempting to buy the last unit.

Acceptance: a cart cannot purchase unavailable stock or use a manipulated client price.

### Phase 5: Stripe test checkout and orders

Implementation:

- Pending order creation.
- Server-side Stripe Checkout Session creation.
- Internal order ID stored in Stripe metadata.
- Local webhook forwarding using Stripe CLI.
- Signature verification and duplicate-event protection.
- Success, failure, expiry, cancellation, and refund state handling.
- Stock consumption/release and order history.

Acceptance: Stripe test cards complete the checkout, and replaying a webhook does not duplicate payment or stock changes.

### Phase 6: Local email and real-time notifications

Implementation:

- Notification records for payment and order events.
- Authenticated WebSocket endpoint with Redis Pub/Sub.
- Celery email tasks using local Mailpit SMTP.
- HTML and plain-text templates for confirmation, payment failure, shipping, delivery, cancellation, and refund.
- Email attempt/status logging.

Acceptance: the React notification centre updates in real time and emails appear at `http://localhost:8025`.

### Phase 7: Analytics and reports

Implementation:

- Total sales, revenue trends, average order value, order-status counts, top products, and low-stock queries.
- Chart.js dashboard with date and status filters.
- CSV and PDF exports using the same filters.
- Staff/admin permissions and audit entries.

Acceptance: dashboard values agree with the underlying orders and exported reports.

### Phase 8: Testing and office deliverables

Implementation:

- Unit tests for pricing, status transitions, stock, and permissions.
- API integration tests for FastAPI and Django.
- Stripe signature/idempotency tests.
- WebSocket and Celery task tests.
- React component tests and an end-to-end purchase test.
- Postman collection and environment.
- Setup, architecture, API, usage, testing, and troubleshooting documentation.
- Demo accounts, seed data, screenshots, and a demo script/video checklist.

Acceptance: the application can be set up on another office machine from the README and the entire demo flow can be completed locally.

## 6. Stripe test-mode plan

Implementation work:

- Checkout Session endpoint and React redirect.
- Server-calculated totals; client-provided totals are never trusted.
- Verified webhook endpoint at `/api/v1/payments/stripe/webhook`.
- Idempotent event storage and transactional order/stock updates.
- Test cards and failure scenarios documented in the demo guide.

Manual work required:

1. Create or use a Stripe account with test mode enabled.
2. Copy the test publishable key and test secret key into the local `.env` file.
3. Install Stripe CLI, sign in, and forward events to the local webhook during demonstrations.
4. Copy the CLI-generated `whsec_...` webhook secret into `.env`.
5. Confirm the demonstration currency, shipping fee, tax rule, and refund rule.

Not required: account activation for live payments, business KYC, bank details, live API keys, or a public webhook endpoint.

## 7. Auth0 localhost plan

Implementation work:

- React provider and authenticated API client.
- FastAPI token verification and permission dependencies.
- Local user synchronization and role checks.
- Authentication tests and setup screenshots/instructions.

Manual work required:

1. Create or use an Auth0 development tenant.
2. Create a Single Page Application for React.
3. Create an Auth0 API with an audience such as `https://api.smart-ecommerce.local`.
4. Add `http://localhost:5173` to allowed callback URLs, logout URLs, and web origins.
5. Enable the Auth0 username/password database connection.
6. Enable the available Google development connection.
7. Configure Facebook only if a Facebook developer application is available; otherwise the implementation and setup documentation will be included and email/Google login will be demonstrated.
8. Enable RBAC and create customer, staff, and admin roles/permissions.
9. Put the Auth0 domain, SPA client ID, and API audience in `.env`.

Not required: a custom Auth0 domain, production callback URLs, or production social-provider verification.

## 8. Local email plan

Mailpit replaces SendGrid for this non-deployed assignment. It behaves like an SMTP server, captures every outgoing email, and displays it in a local browser inbox.

Implementation work:

- SMTP configuration pointing to `mailpit:1025` inside Docker.
- Celery delivery and retry flow.
- Branded HTML/plain-text templates.
- Email logs and failure tests.

Manual work required:

- Provide a store name, support email text, logo, and brand colors.
- Open `http://localhost:8025` during the demo to show received messages.

Not required: SendGrid account, real email API key, sender/domain verification, DNS records, SPF, DKIM, or DMARC.

## 9. Local images and files

Product images will be saved under a local `media/` directory and served by Django during the demonstration. Generated CSV/PDF reports will be downloaded directly or written to a local exports directory.

Not required: S3, Cloudinary, access keys, buckets, or CDN configuration.

## 10. Manual responsibility summary

| Item | Required from project owner |
|---|---|
| Local tooling | Install Docker Desktop; Git is recommended |
| Business rules | Confirm store name, INR/other currency, shipping, tax, cancellation, and refund rules |
| Branding | Logo, colors, support text, and sample products/images |
| Auth0 | Development tenant, SPA/API registrations, localhost URLs, connections, roles, and public configuration |
| Stripe | Test keys, Stripe CLI login, webhook forwarding, and test-mode configuration |
| Email | No account setup; inspect messages in local Mailpit UI |
| Database/Redis | No account setup; both run locally through Docker Compose |
| Images | No account setup; files remain in local media storage |
| Deployment | None |

## 11. Items intentionally excluded

- Cloud hosting and managed services
- Production domains, SSL certificates, DNS, and CDN
- AWS S3/SES, Azure, or GCP resources
- Live Stripe payments and KYC
- Live outbound email and sender-domain authentication
- Production monitoring/on-call systems
- Kubernetes and infrastructure-as-code
- Real shipping-carrier integration

The code will keep provider interfaces and environment configuration clean enough that cloud services could be added later, but those services are outside this assignment.

## 12. Immediate starting point

No vendor secrets are needed for the foundation and catalog phases. Work can begin with local Docker services, Auth0 placeholders, mocked Stripe responses in automated tests, and seeded sample products. Real Auth0 development values and Stripe test keys are needed only when their respective integration phases are demonstrated.
