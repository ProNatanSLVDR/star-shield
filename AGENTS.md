# Repository Guidelines

## Project Structure & Module Organization
- `starshield/`: core project settings, URLs, middleware, shared services.
- `apps/private/`: auth-required features (`auths`, `dashboard`, `payments`).
- `apps/public/`: public review/routing flows.
- `apps/tasks_api/`: separate Django Ninja service for background task endpoints.
- `components/`: reusable `django-components`; `templates/` and `static/`: shared UI assets.
- `tests/` plus `apps/**/tests/`: project and app test suites. Keep French domain naming (for example `Etablissement`).

## Architecture Notes
- Two services run from one codebase: web app (`starshield/settings.py`) and tasks API (`apps/tasks_api/settings.py`).
- In dashboard/public flows, use `starshield_render()` (not plain `render()`).
- Use `from starshield.logger import logger`; follow existing decorators/middleware patterns.

## Build, Test, and Development Commands
- Run Python/Django tooling inside the devcontainer.
- `python manage.py runserver`: Start local web app.
- `python manage.py test`: Run full tests.
- `python manage.py test tests.test_review_views -v 2`: Run a focused test module.
- `python manage.py makemigrations`: Generate migrations when models change.
- Do not run `python manage.py migrate` in normal contributor workflow.
- `ruff check --fix .` and `ruff format .`: Lint/format Python.
- `djlint --lint .` and `djlint --reformat .`: Lint/format templates.

## Coding Style & Naming Conventions
- Follow existing Django patterns and keep solutions simple.
- Python style: 4 spaces, line length `120`, double quotes.
- Template style: line length `80` via djlint.
- Naming: `snake_case` for functions/vars/modules, `CamelCase` for classes, `test_*` for tests.
- Add error handling around external API calls and log context (IDs).
- Split complex conditions into readable intermediate checks.

## HTMX & Template Patterns
- Use `request.htmx` to return full pages vs partials.
- Partial templates should end with `_partial.html`.
- Modal targets: `#dynamicModal .modal-content` (primary) and `#dynamicModal2 .modal-content` (secondary).
- Use `hx-swap="morph:innerHTML"` and `hx_triggers` for refresh events (`close-modal`, `{resource}-updated`).
- Keep using `messages.success/error(...)`; middleware handles HTMX toast transport.

## Component Usage
- Check `components/` before writing custom HTML.
- Use `{% component %}` syntax and read each component `.py` for supported params.
- Prefer default slot content; only use named `{% slot %}` blocks when necessary.

## Testing Guidelines
- Framework: Django `TestCase` with `factory_boy` factories from `tests/factories.py`.
- Place tests in `tests/test_*.py` or app-local `tests/` packages.
- Add/adjust tests for behavior changes, especially routing, payments, and review filtering.
- Run both targeted and full-suite tests before opening a PR.
- Always run lint/format checks on modified files before considering work complete.

## Commit & Pull Request Guidelines
- Recent history favors short imperative commit titles (often French), sometimes `Fix`/`Bugfix`.
- Avoid `wip` commits in shared branches; squash or rewrite before merge.
- PRs should include scope, impacted apps, test evidence (`python manage.py test`, `ruff check .`), and screenshots for UI changes.
- Link related issues/tasks and call out migration or env-var changes explicitly.

## Feature Documentation
- For major features/behavior changes, add or update a markdown doc near the feature.
- Keep docs concise: behavior/flow, design rationale, and user-facing specs. Do this last.

## Security & Configuration Tips
- Local development reads env vars from `.devcontainer/dev.env` via `manage.py`.
- Never commit secrets; use environment variables for Stripe, Google OAuth, and API keys.
- Use `prod.manage.py` only for production-configuration operations.
