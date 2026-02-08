# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Starshield is a Django-based SaaS for managing online reviews. Businesses generate QR codes that route customers to a rating page — positive ratings redirect to Google Reviews, negative ones are captured internally. Additional features: roulette wheel gamification, Google My Business integration, Stripe subscriptions, AI-generated review responses.

The app is in French (fr-fr, Europe/Paris timezone). Model names and some code comments are in French (e.g., "Etablissement" = business establishment).

## Environment

This project uses **devcontainers**. Python, Django, djlint, and other tools run inside the container — never try to run commands that require the Python environment locally (e.g., `python manage.py`, `djlint`, `ruff`). They will always fail.

## Commands (run inside devcontainer only)

```bash
# Run dev server
python manage.py runserver

# Lint Python (auto-fixes)
ruff check --fix .
ruff format .

# Lint templates
djlint --lint .
djlint --reformat .

# Make migrations (NEVER run migrate)
python manage.py makemigrations

# Collect static
python manage.py collectstatic --noinput
```

**Important:** Never run `python manage.py migrate`. Only `makemigrations` is allowed.

Always run `ruff check` and `ruff format` on modified Python files before completing a task — but only inside the devcontainer.

## Architecture

### Two Separate Django Applications

The project runs as **two independent services** from the same codebase:

1. **Web App** (`starshield/settings.py`) — The main Django app serving the dashboard, public pages, and auth. Uses `manage.py` (DJANGO_CONFIGURATION=Dev).

2. **Tasks API** (`apps/tasks_api/settings.py`) — A separate Django Ninja API for background task processing. Has its own `wsgi.py`, `urls.py`, `settings.py`. Inherits from main settings but strips web-specific middleware (CSRF, HTMX, login-required). In production, Cloud Tasks sends HTTP requests to this service. Routes are at `/v1/` via `NinjaAPI`.

### Settings System

Uses `django-configurations` (not standard Django settings). Settings classes: `Base` → `Dev`/`Prod`. Accessed via `DJANGO_CONFIGURATION` env var. The Tasks API settings extend the main settings via multiple inheritance.

### App Organization

- `apps/private/` — Requires authentication (auths, dashboard, payments)
- `apps/public/` — No auth required (reviews, roulette, routing)
- `apps/tasks_api/` — Internal API, no public access

### Key Patterns

**Rendering:** Use `starshield_render()` from `apps/private/dashboard/render.py` instead of Django's `render()`. It handles page context and HX-Trigger headers for HTMX.

**Logging:** Use `from starshield.logger import logger` — centralized logger under the "starshield" namespace.

**Decorators** (`starshield/decorators.py`):
- `@google_gmb_connected_required` — Ensures valid Google credentials
- `@selected_etablissement_required` — Ensures an etablissement is selected in session
- `@unselect_etablissement` — Clears selected etablissement

**Middleware:**
- `EtablissementMiddleware` — Attaches `request.etablissement` from session
- `CustomMessageMiddleware` — Sends Django messages via `X-Messages` header for HTMX compatibility

**Auth:** Custom user model (`auths.User`) with email-based auth. Uses django-allauth with Google social login. `LoginRequiredMiddleware` is globally applied — public views must explicitly opt out.

### Frontend

- **HTMX + django-htmx** for dynamic interactions (partial page updates, modals)
- **Bootstrap** for CSS
- **django-components** for reusable UI components in `components/` directory (button, card, table, review, spinwheel, etc.)
- Partial templates use `_partial.html` suffix
- Modals target `#dynamicModal .modal-content` (or `#dynamicModal2` for nested)
- Swap strategy: `hx-swap="morph:innerHTML"` with idiomorph

### Components

Always check `components/` for existing components before writing custom HTML. Use `{% component %}` tag syntax. Review each component's `.py` file for available parameters.

### Payments

Stripe subscriptions managed per-establishment via `apps/private/payments/`. Webhook handlers in `webhooks.py`.

## Code Style

- Line length: 120 chars (ruff)
- Double quotes for strings
- Prefer simplicity — never overcomplicate
- Catch errors for external API calls, include context (user IDs, object IDs) in error messages
- Break down complex `if` conditions for readability
- Template line length: 80 chars (djlint)
